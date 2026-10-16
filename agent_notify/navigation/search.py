#!/usr/bin/env python3
"""Record observed agent branches and select their live tmux panes."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

OPTION_PREFIX = '@agent_nav_'
PR_PATTERN = re.compile(r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)(?:[/?#].*)?$')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['record', 'link', 'pick'])
    parser.add_argument('reference', nargs='?', default='')
    parser.add_argument('--pane', default=os.environ.get('TMUX_PANE', ''))
    parser.add_argument('--client', default='')
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
                        '#{pane_id}\t#{session_name}:#{window_index}.#{pane_index} #{window_name}\t#{pane_current_path}\t#{pane_current_command}'], check=True)
    pane_rows = []
    for pane_line in pane_listing.splitlines():
        pane_id, window_label, working_directory, command = pane_line.split('\t', 3)
        # Seed existing windows from their current directory, even before a hook fires.
        record_branch(pane_id, working_directory)
        associations = []
        for option_line in run(['tmux', 'show-options', '-p', '-t', pane_id]).splitlines():
            option_name = option_line.split(' ', 1)[0]
            if option_name.startswith(OPTION_PREFIX):
                association_json = run(['tmux', 'show-options', '-pv', '-t', pane_id, option_name])
                try:
                    associations.append(json.loads(association_json))
                except json.JSONDecodeError:
                    continue
        pane_rows.append({'pane': pane_id, 'label': window_label, 'command': command,
                          'associations': associations})
    return pane_rows


def choose_row(pane_rows):
    candidates = '\n'.join(format_row(row) for row in pane_rows)
    picker = subprocess.run(['fzf', '--no-multi', '--layout=reverse', '--delimiter=\t', '--with-nth=2..',
                             '--prompt=Window / branch / PR > ',
                             '--header=Type to search · paste a GitHub PR URL then Enter · ↑/↓ move · Esc cancel',
                             '--bind=enter:accept-or-print-query'],
                            input=candidates, text=True, stdout=subprocess.PIPE,
                            env={**os.environ, 'FZF_DEFAULT_OPTS': '', 'FZF_DEFAULT_OPTS_FILE': ''})
    return picker.stdout.strip() if picker.returncode == 0 else ''


def format_row(pane_row):
    branch_labels = ' | '.join(f"{association['repository']} {association['branch']} {association.get('url', '')}".strip()
                               for association in pane_row['associations'])
    return f"{pane_row['pane']}\t{pane_row['label']} [{pane_row['command']}]  {branch_labels}"


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
