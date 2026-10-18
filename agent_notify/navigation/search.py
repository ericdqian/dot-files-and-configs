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
    parser.add_argument('action', choices=['open', 'start', 'claim', 'record', 'link', 'pick', 'preview', 'query', 'accept'])
    parser.add_argument('reference', nargs='?', default='')
    parser.add_argument('--pane', default=os.environ.get('TMUX_PANE', ''))
    parser.add_argument('--client', default='')
    parser.add_argument('--data', default='')
    parser.add_argument('--checkout', default='')
    parser.add_argument('--base', default='HEAD')
    parser.add_argument('--agent-session', default=os.environ.get('CODEX_SESSION_ID', os.environ.get('CLAUDE_CODE_SESSION_ID', '')))
    arguments = parser.parse_args()
    if arguments.action == 'open':
        open_picker(arguments.client)
    elif arguments.action == 'start':
        checkout_path = create_agent_worktree(arguments.pane, arguments.reference, arguments.checkout, arguments.base)
        record_branch(arguments.pane, str(checkout_path), source='claim', session_id=arguments.agent_session)
        print(f'Worktree: {checkout_path}\nClaimed branch {arguments.reference} for pane {arguments.pane}. Use this worktree for subsequent work.')
    elif arguments.action == 'claim':
        record_branch(arguments.pane, arguments.checkout or os.getcwd(), arguments.reference,
                      source='claim', session_id=arguments.agent_session)
        print(f'Claim recorded for pane {arguments.pane}.')
    elif arguments.action == 'record':
        payload = json.load(sys.stdin)
        for working_directory in observed_directories(payload):
            record_branch(arguments.pane, working_directory, session_id=payload.get('session_id', ''))
    elif arguments.action == 'link':
        if not arguments.reference:
            raise ValueError('Supply a branch name or GitHub PR URL to link.')
        if not arguments.pane:
            raise ValueError('Run link inside the agent’s tmux pane, or pass --pane %ID.')
        record_branch(arguments.pane, arguments.checkout or os.getcwd(), arguments.reference,
                      source='link', session_id=arguments.agent_session)
    elif arguments.action == 'accept':
        print_accept_action(Path(arguments.data), arguments.reference, arguments.pane)
    elif arguments.action == 'query':
        update_query_results(Path(arguments.data), arguments.reference)
    elif arguments.action == 'preview':
        pane_rows_by_id = json.loads(Path(arguments.data).read_text())
        selected_pane = pane_rows_by_id.get(arguments.reference)
        print(format_details(selected_pane) if selected_pane else
              Path(arguments.data).with_name('status.txt').read_text())
    else:
        pick_pane(arguments.client, arguments.data)


def observed_directories(payload):
    agent_directory = payload.get('cwd') or os.getcwd()
    tool_input = payload.get('tool_input') or {}
    tool_directory = tool_input.get('workdir') or tool_input.get('cwd')
    if tool_directory and not os.path.isabs(tool_directory):
        tool_directory = os.path.join(agent_directory, tool_directory)
    return list(dict.fromkeys(directory for directory in [agent_directory, tool_directory] if directory))


def create_agent_worktree(pane_id, branch, checkout, base):
    if not pane_id or not branch or not checkout:
        raise ValueError('start requires a branch, --checkout PATH, and a tmux pane (--pane %ID outside tmux).')
    if run(['tmux', 'display-message', '-p', '-t', pane_id, '#{pane_id}'], check=True) != pane_id:
        raise ValueError('The target tmux pane no longer exists.')
    checkout_path = Path(checkout).expanduser().resolve()
    existing_branch = run(['git', 'show-ref', '--verify', f'refs/heads/{branch}'])
    # Create a separate checkout without moving, stashing, or changing the shared worktree.
    branch_arguments = [] if existing_branch else ['-b', branch]
    starting_commit = branch if existing_branch else base
    run(['git', 'worktree', 'add', *branch_arguments, '--', str(checkout_path), starting_commit], check=True)
    return checkout_path


def record_branch(pane_id, working_directory, reference='', source='observed', session_id=''):
    if not pane_id:
        if source in {'claim', 'link'}:
            raise ValueError('A claim needs a live tmux pane; pass --pane %ID outside tmux.')
        return
    # Remember non-Git directories too, so shell panes need no repeated Git probes.
    run(['tmux', 'set-option', '-p', '-t', pane_id, '@agent_nav_directory', working_directory], check=True)
    repository = repository_identity(run(['git', '-C', working_directory, 'remote', 'get-url', 'origin']))
    checkout_repository = repository
    current_branch = run(['git', '-C', working_directory, 'branch', '--show-current'])
    branch = current_branch
    checkout_root = run(['git', '-C', working_directory, 'rev-parse', '--show-toplevel'])
    if not repository:
        repository = checkout_root
    if reference:
        if PR_PATTERN.fullmatch(reference):
            repository, branch = resolve_pr(reference)
            if source == 'claim':
                pr_owner, pr_repository, _ = PR_PATTERN.fullmatch(reference).groups()
                base_repository = f'github.com/{pr_owner}/{pr_repository}'.lower()
                if checkout_repository not in {repository, base_repository}:
                    raise ValueError('This worktree belongs to a different repository than the requested PR.')
        else:
            branch = reference
    if source == 'claim' and branch != current_branch:
        raise ValueError(f"This checkout is on {current_branch or 'a detached HEAD'}, not {branch}. Use its dedicated worktree, or link historical work explicitly.")
    if not repository or not branch:
        if reference or source == 'claim':
            raise ValueError('Run branch links from a Git repository with a named branch.')
        return
    association = {'repository': repository, 'branch': branch, 'checkout': checkout_root, 'source': source}
    association_identity = json.dumps(association, sort_keys=True)
    option_key = OPTION_PREFIX + hashlib.sha256(association_identity.encode()).hexdigest()
    previous_association = run(['tmux', 'show-options', '-pqv', '-t', pane_id, option_key])
    if previous_association:
        try:
            previous_url = json.loads(previous_association).get('url')
            if previous_url:
                association['url'] = previous_url
        except ValueError:
            pass
    if PR_PATTERN.fullmatch(reference):
        association['url'] = reference
    if session_id:
        association['agent_session'] = session_id
    # Each association owns an option, so observations cannot overwrite explicit claims.
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


def open_picker(client_name):
    # Route only after tmux has closed the popup and restored its original terminal.
    with tempfile.TemporaryDirectory(prefix='agent-picker-') as selection_directory:
        selection_path = Path(selection_directory, 'selection.txt')
        picker_command = shlex.join([sys.executable, str(Path(__file__).resolve()), 'pick',
                                     '--client', client_name, '--data', str(selection_path)])
        popup_arguments = ['-c', client_name] if client_name else []
        run(['tmux', 'display-popup', *popup_arguments, '-B', '-w', '100%', '-h', '100%',
             '-E', picker_command], check=True, timeout=None)
        if client_name:
            run(['tmux', 'refresh-client', '-t', client_name])
        if selection_path.exists():
            navigate_to_pane(selection_path.read_text(), client_name)


def pick_pane(client_name, selection_path=''):
    if not shutil.which('fzf'):
        raise ValueError('Install fzf to use the agent window picker.')
    pane_rows = collect_and_record_pane_rows()
    selected = choose_row(pane_rows)
    if not selected:
        return
    pane_id = selected.split('\t', 1)[0]
    if not re.fullmatch(r'%\d+', pane_id):
        raise ValueError('No matching pane. Paste a GitHub PR URL, or search an observed branch/window name.')
    if selection_path:
        Path(selection_path).write_text(pane_id)
    else:
        navigate_to_pane(pane_id, client_name)


def navigate_to_pane(pane_id, client_name):
    destination_client, wezterm_pane = find_destination(pane_id, client_name)
    if destination_client is None and wezterm_pane is not None:
        spawn_session_tab(pane_id, wezterm_pane)
        return
    client_arguments = ['-c', destination_client] if destination_client else []
    run(['tmux', 'switch-client', *client_arguments, '-t', pane_id], check=True)
    run(['tmux', 'select-pane', '-t', pane_id], check=True)
    if wezterm_pane:
        focus_wezterm_pane(wezterm_pane)


def spawn_session_tab(pane_id, source_wezterm_pane):
    session_id, socket_path = run(['tmux', 'display-message', '-p', '-t', pane_id,
                                  '#{session_id}\t#{socket_path}'], check=True).split('\t', 1)
    # Select inside the destination session without replacing the source client’s session.
    run(['tmux', 'select-window', '-t', pane_id], check=True)
    run(['tmux', 'select-pane', '-t', pane_id], check=True)
    created_pane_id = run(['wezterm', 'cli', 'spawn', '--window-id', str(source_wezterm_pane['window_id']),
                           '--', 'env', '-u', 'TMUX', '-u', 'TMUX_PANE', 'tmux', '-S', socket_path,
                           'attach-session', '-t', session_id], check=True)
    wezterm_panes = json.loads(run(['wezterm', 'cli', 'list', '--format', 'json'], check=True))
    created_pane = next((pane for pane in wezterm_panes if str(pane['pane_id']) == created_pane_id), None)
    if created_pane:
        focus_wezterm_pane(created_pane)
    else:
        run(['wezterm', 'cli', 'activate-pane', '--pane-id', created_pane_id], check=True)


def focus_wezterm_pane(wezterm_pane):
    # Focus both levels explicitly: the outer tab may differ from the selected split.
    run(['wezterm', 'cli', 'activate-tab', '--tab-id', str(wezterm_pane['tab_id'])], check=True)
    run(['wezterm', 'cli', 'activate-pane', '--pane-id', str(wezterm_pane['pane_id'])], check=True)


def find_destination(pane_id, current_client):
    if not shutil.which('wezterm'):
        return current_client, None
    try:
        destination_session = run(['tmux', 'display-message', '-p', '-t', pane_id, '#{session_name}'], check=True)
        client_listing = run(['tmux', 'list-clients', '-F', '#{client_name}\t#{session_name}'], check=True)
        wezterm_panes = json.loads(run(['wezterm', 'cli', 'list', '--format', 'json'], check=True))
        clients = [line.split('\t', 1) for line in client_listing.splitlines()]
        return select_destination(destination_session, clients, wezterm_panes, current_client)
    except (ValueError, OSError, subprocess.TimeoutExpired):
        return current_client, None


def select_destination(destination_session, clients, wezterm_panes, current_client):
    panes_by_tty = {pane.get('tty_name'): pane for pane in wezterm_panes}
    # Prefer this client when it already displays the session, then another visible client.
    ordered_clients = sorted(clients, key=lambda client: client[0] != current_client)
    for client_name, session_name in ordered_clients:
        if session_name == destination_session and client_name in panes_by_tty:
            return client_name, panes_by_tty[client_name]
    if current_client in panes_by_tty:
        return None, panes_by_tty[current_client]
    return current_client, None


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
    repository_width = max([len(format_repository_label(navigation_associations(row))) for row in pane_rows] + [10])
    column_widths = (min(title_width, 36), min(location_width, 24), min(repository_width, 36))
    candidates = '\n'.join(format_row(row, column_widths) for row in pane_rows)
    column_header = (f"{'WINDOW':<{column_widths[0]}}  {'PANE':<{column_widths[1]}}  "
                     f"{'OWNER':<8}  {'PROCESS':<9}  {'REPOSITORY':<{column_widths[2]}}  BRANCHES")
    # The private snapshot lets preview selection stay local, without querying tmux again.
    with tempfile.TemporaryDirectory(prefix='agent-search-') as preview_directory:
        preview_path = Path(preview_directory, 'panes.json')
        preview_path.write_text(json.dumps({row['pane']: row for row in pane_rows}))
        Path(preview_directory, 'candidates.txt').write_text(candidates)
        query_command = shlex.join([sys.executable, str(Path(__file__).resolve()),
                                   'query', '--data', str(preview_path), '--']) + ' {q}'
        Path(preview_directory, 'status.txt').write_text('No matching destination.')
        query_result_path(preview_path, '').write_text(json.dumps([row['pane'] for row in pane_rows]))
        accept_command = shlex.join([sys.executable, str(Path(__file__).resolve()),
                                    'accept', '--data', str(preview_path)]) + ' --pane {1} -- {q}'
        preview_command = shlex.join([sys.executable, str(Path(__file__).resolve()),
                                     'preview', '--data', str(preview_path)]) + ' {1}'
        picker = subprocess.run(['fzf', '--disabled', '--no-sort', '--ansi', '--no-multi', '--layout=reverse',
                                 '--delimiter=\t', '--with-nth=2..', '--gap=1', '--highlight-line',
                                 '--color=fg:252,hl:220,fg+:255,bg+:236,hl+:220,pointer:81,prompt:81',
                                 '--prompt=Window / branch / PR > ',
                                 '--header=↑/↓ choose · Enter jump · Esc cancel · Ctrl+/ details\n'
                                          'Search a window or branch; paste a PR URL to resolve matching panes.\n\n' + column_header,
                                 '--preview=' + preview_command,
                                 '--preview-window=down,35%,wrap,border-top',
                                 '--bind=enter:transform(' + accept_command + '),ctrl-/:toggle-preview',
                                 '--bind=change:reload(sleep 0.3; exec ' + query_command + ')'],
                                input=candidates, text=True, stdout=subprocess.PIPE,
                                env={**os.environ, 'FZF_DEFAULT_OPTS': '', 'FZF_DEFAULT_OPTS_FILE': ''})
    return picker.stdout.strip() if picker.returncode == 0 else ''


def update_query_results(preview_path, query):
    candidate_lines = preview_path.with_name('candidates.txt').read_text().splitlines()
    pane_rows = list(json.loads(preview_path.read_text()).values())
    try:
        if PR_PATTERN.fullmatch(query.strip()):
            repository, branch = resolve_pr(query.strip())
            matching_panes = {row['pane'] for row in pane_rows if any(
                association['repository'] == repository and association['branch'] == branch
                for association in navigation_associations(row))}
            claimed_panes = {row['pane'] for row in pane_rows if any(
                association.get('source') in {'claim', 'link'} and association['repository'] == repository
                and association['branch'] == branch for association in navigation_associations(row))}
            if claimed_panes:
                matching_panes = claimed_panes
            pr_number = PR_PATTERN.fullmatch(query.strip()).group(3)
            result_lines = [line.replace('\t', f'\t\033[35mPR #{pr_number}\033[0m  ', 1) for line in candidate_lines
                            if line.split('\t', 1)[0] in matching_panes]
            status = (f'No tmux pane has recorded {branch}. Its agent may be outside tmux. '
                      'Link older work explicitly, or clear the URL to search windows.')
        else:
            claimed_panes = {row['pane'] for row in pane_rows if any(
                association.get('source') in {'claim', 'link'} and association['branch'] == query.strip()
                for association in navigation_associations(row))}
            if claimed_panes:
                candidate_lines = [line for line in candidate_lines if line.split('\t', 1)[0] in claimed_panes]
            # Reuse fzf’s ranking while keeping original ANSI rows for presentation.
            filtered_lines = run(['fzf', '--ansi', '--delimiter=\t', '--with-nth=2..', '--filter', query],
                                 input_text='\n'.join(candidate_lines)).splitlines()
            candidates_by_pane_id = {line.split('\t', 1)[0]: line for line in candidate_lines}
            result_lines = [candidates_by_pane_id[line.split('\t', 1)[0]] for line in filtered_lines]
            status = 'No matching windows or branches. Edit your search or paste a GitHub PR URL.'
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        result_lines = []
        status = f'PR lookup failed: {error}. Edit the URL to retry, or search a branch name.'
    # The non-selectable status row and preview explain empty results inside the picker.
    preview_path.with_name('status.txt').write_text(status)
    result_path = query_result_path(preview_path, query)
    temporary_result_path = result_path.with_suffix(f'.{os.getpid()}.tmp')
    temporary_result_path.write_text(json.dumps([line.split('\t', 1)[0] for line in result_lines]))
    os.replace(temporary_result_path, result_path)
    print('\n'.join(result_lines) if result_lines else '!\t' + status.replace('\n', ' '))


def query_result_path(preview_path, query):
    return preview_path.with_name('query-' + hashlib.sha256(query.encode()).hexdigest() + '.json')


def print_accept_action(preview_path, query, selected_pane_id):
    result_path = query_result_path(preview_path, query)
    if result_path.exists() and selected_pane_id in json.loads(result_path.read_text()):
        print('accept')
    else:
        print('change-header(Search updating or no destination. Wait for results, then press Enter.)')


def format_row(pane_row, column_widths=(30, 18, 24)):
    title = pane_row.get('title', pane_row['label'])
    location = pane_row.get('location', '')
    associations = navigation_associations(pane_row)
    branches = list(dict.fromkeys(association['branch'] for association in associations))
    repository_label = format_repository_label(associations)
    ownership_label = 'claimed' if any(association.get('source') in {'claim', 'link'} for association in associations) else 'observed'
    process_label = 'claude' if re.fullmatch(r'\d+\.\d+\.\d+', pane_row['command']) else pane_row['command']
    branch_label = ', '.join(branches) or 'No recorded branch'
    # Keep complete titles and branches in the row so fuzzy search loses no history.
    return (f"{pane_row['pane']}\t\033[1;37m{title:<{column_widths[0]}}\033[0m  "
            f"\033[90m{location:<{column_widths[1]}}\033[0m  "
            f"\033[33m{ownership_label:<8}\033[0m  \033[32m{process_label:<9}\033[0m  "
            f"\033[36m{repository_label:<{column_widths[2]}}\033[0m  {branch_label}")


def navigation_associations(pane_row):
    claims = [association for association in pane_row['associations']
              if association.get('source') in {'claim', 'link'}]
    return claims or pane_row['associations']


def format_repository_label(associations):
    return ', '.join(dict.fromkeys(association['repository'].removeprefix('github.com/')
                                   for association in associations)) or '—'


def format_details(pane_row):
    detail_lines = [f"\033[1;36m{pane_row.get('title', pane_row['label'])}\033[0m",
                    f"Location  {pane_row.get('location', pane_row['label'])}  ({pane_row['pane']})",
                    f"Process   {pane_row['command']}", f"Directory {pane_row.get('directory', '—')}",
                    '', '\033[1mRecorded branches / PRs\033[0m']
    unique_associations = {json.dumps(association, sort_keys=True): association
                           for association in navigation_associations(pane_row)}
    for association in unique_associations.values():
        detail_lines.append(f"  {association['branch']}  \033[90m{association['repository']}\033[0m")
        ownership = 'Explicit ownership' if association.get('source') in {'claim', 'link'} else 'Checkout observation only; no ownership claim'
        detail_lines.append(f'    {ownership}')
        if association.get('checkout'):
            detail_lines.append(f"    Worktree: {association['checkout']}")
        if association.get('agent_session'):
            detail_lines.append(f"    Agent session: {association['agent_session']}")
        if association.get('url'):
            detail_lines.append(f"    {association['url']}")
    if not unique_associations:
        detail_lines.append('  No branch recorded yet.')
    return '\n'.join(detail_lines)


def run(command, check=False, input_text=None, timeout=20):
    # Noninteractive commands must never consume keys intended for the popup or shell.
    input_arguments = {'input': input_text} if input_text is not None else {'stdin': subprocess.DEVNULL}
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=timeout, **input_arguments)
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
