"""Resolve PR references and select existing worktrees."""
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from navigation import github, picker
from navigation.commands import run


def pick_worktree(candidate_lines, query):
    with tempfile.TemporaryDirectory(prefix='worktree-picker-') as snapshot_directory:
        snapshot_path = Path(snapshot_directory, 'candidates.txt')
        snapshot_path.write_text('\n'.join(candidate_lines))
        cli_path = Path(__file__).with_name('cli.py')
        query_command = shlex.join([sys.executable, str(cli_path), 'worktree-query',
                                    '--data', str(snapshot_path), '--']) + ' "$FZF_QUERY"'
        accept_command = shlex.join([sys.executable, str(cli_path), 'worktree-accept',
                                     '--data', str(snapshot_path)]) + ' --selected {1} -- {q}'
        change_command = picker.query_change_command(query_command, snapshot_path, pr_numbers=True)
        load_command = picker.query_change_command(query_command, snapshot_path, pr_numbers=True, on_load=True)
        # fzf owns terminal input while reload commands resolve PR queries from this private snapshot.
        selection = subprocess.run([
            'fzf', '--with-shell=/bin/sh -c', '--delimiter=\t', '--with-nth=1,2',
            '--query=' + query, '--prompt=worktree > ', '--height=40%', '--reverse',
            '--header=Search paths / branches or paste a PR number / URL',
            '--bind=start:transform(' + change_command + ')',
            '--bind=change:transform(' + change_command + ')',
            '--bind=load:transform(' + load_command + ')',
            '--bind=enter:transform(' + accept_command + ')'],
            input='\n'.join(candidate_lines), text=True, stdout=subprocess.PIPE,
            env={**os.environ, 'FZF_DEFAULT_OPTS': '', 'FZF_DEFAULT_OPTS_FILE': ''})
        if selection.returncode == 0 and selection.stdout:
            return selection.stdout.split('\t', 1)[0].rstrip('\n')
        return ''


def update_worktree_query(snapshot_path, query):
    candidate_lines = snapshot_path.read_text().splitlines()
    normalized_query = query.strip()
    try:
        exact_lines = [line for line in candidate_lines if normalized_query in line.split('\t')]
        if exact_lines:
            result_lines = exact_lines
        elif picker.is_pr_query(normalized_query, pr_numbers=True):
            head_branch = resolve_worktree_pr_branch(normalized_query, use_cache=True)
            result_lines = [line for line in candidate_lines if line.split('\t', 1)[1] == head_branch]
            if not result_lines:
                raise ValueError(f'No local worktree for PR {normalized_query} (branch {head_branch})')
        else:
            result_lines = run(['fzf', '--delimiter=\t', '--with-nth=1,2', '--filter', query],
                               input_text='\n'.join(candidate_lines)).splitlines()
        status = 'No matching worktree. Edit your search or paste a PR number / URL.'
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        result_lines = []
        status = f'PR lookup failed: {error}. Edit your search to retry.'
    # Publish validation before fzf can display and accept these results.
    result_path = picker.query_result_path(snapshot_path, query)
    temporary_result_path = result_path.with_suffix(f'.{os.getpid()}.tmp')
    temporary_result_path.write_text(json.dumps([line.split('\t', 1)[0] for line in result_lines]))
    os.replace(temporary_result_path, result_path)
    print('\n'.join(result_lines) if result_lines else '!\t' + status.replace('\n', ' '))


def print_worktree_accept_action(snapshot_path, query, selected_path):
    candidate_paths = [line.split('\t', 1)[0] for line in snapshot_path.read_text().splitlines()]
    live_search = not picker.is_pr_query(query, pr_numbers=True)
    print(picker.accept_action(snapshot_path, query, selected_path, candidate_paths, live_search))


def resolve_worktree_pr_branch(reference, use_cache=False):
    repository_url = run(['gh', 'repo', 'view', '--json', 'url', '--jq', '.url'], check=True)
    if re.fullmatch(r'#?[0-9]+', reference):
        pr_url = f'{repository_url}/pull/{reference.lstrip("#")}'
    else:
        pr_url = github.canonical_pr_url(reference)
        if not pr_url:
            raise ValueError('Expected a GitHub PR number or URL.')
        pr_owner, pr_repository, _ = github.PR_PATTERN.fullmatch(pr_url).groups()
        if github.repository_identity(repository_url) != f'github.com/{pr_owner}/{pr_repository}':
            raise ValueError(f'PR URL does not belong to {repository_url}')
    # Interactive searches share tmux’s cache; explicit command arguments resolve a fresh head.
    if use_cache:
        _, head_branch = github.resolve_and_cache_pr(pr_url)
    else:
        _, head_branch = github.resolve_pr(pr_url)
    if not head_branch:
        raise ValueError(f'Could not resolve PR {reference} to a branch.')
    return head_branch


