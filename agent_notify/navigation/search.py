#!/usr/bin/env python3
"""Record observed agent branches and select their live tmux panes."""
import argparse
import hashlib
import json
import os
import re
import shutil
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

OPTION_PREFIX = '@agent_nav_'
PR_PATTERN = re.compile(r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)(?:[/?#].*)?$')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['record', 'link', 'pick', 'preview'])
    parser.add_argument('reference', nargs='?', default='')
    parser.add_argument('--pane', default=os.environ.get('TMUX_PANE', ''))
    parser.add_argument('--client', default='')
    parser.add_argument('--data', default='')
    arguments = parser.parse_args()
    if arguments.action == 'record':
        payload = json.load(sys.stdin)
        for working_directory in observed_directories(payload):
            record_branch(arguments.pane, working_directory)
    elif arguments.action == 'link':
        if not arguments.reference:
            raise ValueError('Supply a branch name or GitHub PR URL to link.')
        if not arguments.pane:
            raise ValueError('Run link inside the agent’s tmux pane, or pass --pane %ID.')
        record_branch(arguments.pane, os.getcwd(), arguments.reference)
    elif arguments.action == 'preview':
        pane_rows_by_id = json.loads(Path(arguments.data).read_text())
        print(format_details(pane_rows_by_id[arguments.reference]))
    else:
        pick_pane(arguments.client)


def observed_directories(payload):
    agent_directory = payload.get('cwd') or os.getcwd()
    tool_input = payload.get('tool_input') or {}
    tool_directory = tool_input.get('workdir') or tool_input.get('cwd')
    if tool_directory and not os.path.isabs(tool_directory):
        tool_directory = os.path.join(agent_directory, tool_directory)
    return list(dict.fromkeys(directory for directory in [agent_directory, tool_directory] if directory))


def record_branch(pane_id, working_directory, reference=''):
    if not pane_id:
        return
    # Remember non-Git directories too, so shell panes need no repeated Git probes.
    run(['tmux', 'set-option', '-p', '-t', pane_id, '@agent_nav_directory', working_directory], check=True)
    repository = repository_identity(run(['git', '-C', working_directory, 'remote', 'get-url', 'origin']))
    branch = run(['git', '-C', working_directory, 'branch', '--show-current'])
    if not repository:
        repository = run(['git', '-C', working_directory, 'rev-parse', '--show-toplevel'])
    if reference:
        if PR_PATTERN.fullmatch(reference):
            repository, branch = resolve_pr(reference)
        else:
            branch = reference
    if not repository or not branch:
        if reference:
            raise ValueError('Run branch links from a Git repository with a named branch.')
        return
    association = {'repository': repository, 'branch': branch}
    if PR_PATTERN.fullmatch(reference):
        association['url'] = reference
    association_identity = json.dumps(association, sort_keys=True)
    option_key = OPTION_PREFIX + hashlib.sha256(association_identity.encode()).hexdigest()
    # Each association owns an option, so overlapping hooks cannot overwrite history.
    run(['tmux', 'set-option', '-p', '-t', pane_id, option_key, json.dumps(association)], check=True)


def repository_identity(remote_url):
    normalized = re.sub(r'^\w+://(?:[^/@]+@)?', '', remote_url.strip())
    normalized = re.sub(r'^git@', '', normalized).replace(':', '/', 1)
    return normalized.removesuffix('.git').rstrip('/').lower()


def resolve_pr(pr_url):
    match = PR_PATTERN.fullmatch(pr_url)
    if not match:
        raise ValueError('Expected a GitHub PR URL.')
    owner, repository_name, number = match.groups()
    pull_request = json.loads(run(['gh', 'api', f'repos/{owner}/{repository_name}/pulls/{number}'], check=True))
    head_repository = pull_request['head']['repo']
    if not head_repository:
        raise ValueError('The PR’s source repository has been deleted; link its branch explicitly.')
    return 'github.com/' + head_repository['full_name'].lower(), pull_request['head']['ref']


def pick_pane(client_name):
    if not shutil.which('fzf'):
        raise ValueError('Install fzf to use the agent window picker.')
    pane_rows = collect_and_record_pane_rows()
    selected = choose_row(pane_rows)
    if not selected:
        return
    if PR_PATTERN.fullmatch(selected):
        repository, branch = resolve_pr(selected)
        matching_rows = [row for row in pane_rows if any(
            association['repository'] == repository and association['branch'] == branch
            for association in row['associations'])]
        if not matching_rows:
            raise ValueError(f'No live pane has recorded {repository} {branch}. Use link to backfill it.')
        selected = format_row(matching_rows[0]) if len(matching_rows) == 1 else choose_row(matching_rows)
        if not selected:
            return
    pane_id = selected.split('\t', 1)[0]
    if not re.fullmatch(r'%\d+', pane_id):
        raise ValueError('No matching pane. Paste a GitHub PR URL, or search an observed branch/window name.')
    # Target this popup’s client explicitly; another client may be active meanwhile.
    client_arguments = ['-c', client_name] if client_name else []
    run(['tmux', 'switch-client', *client_arguments, '-t', pane_id], check=True)
    run(['tmux', 'select-pane', '-t', pane_id], check=True)


def collect_and_record_pane_rows():
    pane_listing = run(['tmux', 'list-panes', '-a', '-F',
                        '#{pane_id}\t#{session_name}\t#{window_name}\t#{window_index}.#{pane_index}\t#{pane_current_path}\t#{@agent_nav_directory}\t#{pane_current_command}'], check=True)
    pane_rows = []
    option_commands = ['tmux']
    for pane_line in pane_listing.splitlines():
        pane_id, session_name, window_name, pane_location, working_directory, inspected_directory, command = pane_line.split('\t', 6)
        if is_feedback_session(session_name):
            continue
        window_label = f'{session_name}:{pane_location} {window_name}'
        pane_rows.append({'pane': pane_id, 'label': window_label, 'command': command,
                          'title': window_name, 'location': f'{session_name}:{pane_location}',
                          'directory': working_directory, 'inspected_directory': inspected_directory, 'associations': []})
        if len(option_commands) > 1:
            option_commands.append(';')
        option_commands.extend(['display-message', '-p', '-t', pane_id, 'agent-pane #{pane_id}', ';',
                                'show-options', '-p', '-t', pane_id])
    if not pane_rows:
        return []
    # One tmux request reads every pane, instead of spawning a client per association.
    pane_rows_by_id = {row['pane']: row for row in pane_rows}
    current_pane_id = ''
    for option_line in run(option_commands).splitlines():
        if option_line.startswith('agent-pane '):
            current_pane_id = option_line.split(' ', 1)[1]
        elif option_line.startswith(OPTION_PREFIX) and not option_line.startswith('@agent_nav_directory '):
            try:
                option_name, association_json = shlex.split(option_line)
                pane_rows_by_id[current_pane_id]['associations'].append(json.loads(association_json))
            except (ValueError, KeyError):
                continue
    for pane_row in pane_rows:
        if pane_row['directory'] == pane_row['inspected_directory']:
            continue
        # Seed each pane directory once; hooks record subsequent branch changes.
        record_branch(pane_row['pane'], pane_row['directory'])
        for option_line in run(['tmux', 'show-options', '-p', '-t', pane_row['pane']]).splitlines():
            if option_line.startswith(OPTION_PREFIX) and not option_line.startswith('@agent_nav_directory '):
                try:
                    option_name, association_json = shlex.split(option_line)
                    pane_row['associations'].append(json.loads(association_json))
                except ValueError:
                    continue
    return pane_rows


def is_feedback_session(session_name):
    # Match the review runner’s session convention, not development window titles.
    return re.fullmatch(r'(?:claude|codex)-pr-\d+-(?:correctness|security|style)(?:-.*)?', session_name) is not None


def choose_row(pane_rows):
    title_width = max([len(row.get('title', row['label'])) for row in pane_rows] + [6])
    location_width = max([len(row.get('location', '')) for row in pane_rows] + [8])
    repository_width = max([len(format_repository_label(row['associations'])) for row in pane_rows] + [10])
    column_widths = (min(title_width, 36), min(location_width, 24), min(repository_width, 36))
    candidates = '\n'.join(format_row(row, column_widths) for row in pane_rows)
    column_header = (f"{'WINDOW':<{column_widths[0]}}  {'PANE':<{column_widths[1]}}  "
                     f"{'PROCESS':<9}  {'REPOSITORY':<{column_widths[2]}}  BRANCHES")
    # The private snapshot lets preview selection stay local, without querying tmux again.
    with tempfile.TemporaryDirectory(prefix='agent-search-') as preview_directory:
        preview_path = Path(preview_directory, 'panes.json')
        preview_path.write_text(json.dumps({row['pane']: row for row in pane_rows}))
        preview_command = shlex.join([sys.executable, str(Path(__file__).resolve()),
                                     'preview', '--data', str(preview_path)]) + ' {1}'
        picker = subprocess.run(['fzf', '--ansi', '--no-multi', '--layout=reverse',
                                 '--delimiter=\t', '--with-nth=2..', '--gap=1', '--highlight-line',
                                 '--color=fg:252,hl:220,fg+:255,bg+:236,hl+:220,pointer:81,prompt:81',
                                 '--prompt=Window / branch / PR > ',
                                 '--header=↑/↓ choose · Enter jump · Esc cancel · Ctrl+/ details\n'
                                          'Search a window or branch, or paste a GitHub PR URL and press Enter.\n\n' + column_header,
                                 '--preview=' + preview_command,
                                 '--preview-window=down,35%,wrap,border-top',
                                 '--bind=enter:accept-or-print-query,ctrl-/:toggle-preview'],
                                input=candidates, text=True, stdout=subprocess.PIPE,
                                env={**os.environ, 'FZF_DEFAULT_OPTS': '', 'FZF_DEFAULT_OPTS_FILE': ''})
    return picker.stdout.strip() if picker.returncode == 0 else ''


def format_row(pane_row, column_widths=(30, 18, 24)):
    title = pane_row.get('title', pane_row['label'])
    location = pane_row.get('location', '')
    branches = list(dict.fromkeys(association['branch'] for association in pane_row['associations']))
    repository_label = format_repository_label(pane_row['associations'])
    process_label = 'claude' if re.fullmatch(r'\d+\.\d+\.\d+', pane_row['command']) else pane_row['command']
    branch_label = ', '.join(branches) or 'No recorded branch'
    # Keep complete titles and branches in the row so fuzzy search loses no history.
    return (f"{pane_row['pane']}\t\033[1;37m{title:<{column_widths[0]}}\033[0m  "
            f"\033[90m{location:<{column_widths[1]}}\033[0m  "
            f"\033[32m{process_label:<9}\033[0m  "
            f"\033[36m{repository_label:<{column_widths[2]}}\033[0m  {branch_label}")


def format_repository_label(associations):
    return ', '.join(dict.fromkeys(association['repository'].removeprefix('github.com/')
                                   for association in associations)) or '—'


def format_details(pane_row):
    detail_lines = [f"\033[1;36m{pane_row.get('title', pane_row['label'])}\033[0m",
                    f"Location  {pane_row.get('location', pane_row['label'])}  ({pane_row['pane']})",
                    f"Process   {pane_row['command']}", f"Directory {pane_row.get('directory', '—')}",
                    '', '\033[1mRecorded branches / PRs\033[0m']
    unique_associations = {json.dumps(association, sort_keys=True): association
                           for association in pane_row['associations']}
    for association in unique_associations.values():
        detail_lines.append(f"  {association['branch']}  \033[90m{association['repository']}\033[0m")
        if association.get('url'):
            detail_lines.append(f"    {association['url']}")
    if not unique_associations:
        detail_lines.append('  No branch recorded yet.')
    return '\n'.join(detail_lines)


def run(command, check=False):
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    if check and result.returncode:
        raise ValueError(result.stderr.strip() or f'{command[0]} failed')
    return result.stdout.strip()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        if len(sys.argv) > 1 and sys.argv[1] == 'record':
            sys.exit(0)  # Navigation must never block an agent lifecycle hook.
        print(f'Agent search: {error}', file=sys.stderr)
        if sys.stdin.isatty():
            input('Press Enter to close…')
        sys.exit(1)
