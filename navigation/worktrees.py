"""Supply existing worktrees to the shared navigation picker."""
import tempfile
from pathlib import Path

from navigation import github, picker
from navigation.commands import run


def pick_worktree(candidate_lines, query):
    for candidate_line in candidate_lines:
        worktree_path, worktree_branch = candidate_line.split('\t', 1)
        if query and (query in {worktree_path, worktree_branch, 'refs/heads/' + worktree_branch}
                      or str(Path(query).expanduser().resolve()) == worktree_path):
            return worktree_path
    if picker.is_pr_query(query, pr_numbers=True):
        head_branch = resolve_worktree_pr_branch(query)
        matching_path = next((line.split('\t', 1)[0] for line in candidate_lines
                              if line.split('\t', 1)[1] == head_branch), '')
        if not matching_path:
            raise ValueError(f'no local worktree for PR {query} (branch {head_branch})')
        return matching_path
    repository = github.repository_identity(run(['git', 'remote', 'get-url', 'origin']))
    destination_rows = {worktree_path: {'exact_queries': [worktree_path, worktree_branch], 'associations': [
        {'repository': repository, 'branch': worktree_branch, 'source': 'claim'}] if worktree_branch else []}
        for worktree_path, worktree_branch in (line.split('\t', 1) for line in candidate_lines)}
    with tempfile.TemporaryDirectory(prefix='worktree-picker-') as snapshot_directory:
        snapshot_path = Path(snapshot_directory, 'worktrees.json')
        picker.write_snapshot(snapshot_path, destination_rows, candidate_lines,
                              {'pr_numbers': True, 'repository_url': 'https://' + repository,
                               'filter_arguments': ['--delimiter=\t', '--with-nth=1,2'],
                               'missing_destination': 'No local worktree for branch {branch}.'})
        selection = picker.run_picker(snapshot_path, query, ['fzf', '--ansi', '--with-shell=/bin/sh -c',
                                      '--delimiter=\t', '--with-nth=1,2', '--height=40%', '--reverse',
                                      '--prompt=worktree > ', '--header=Search paths / branches or paste a PR number / URL'])
        return selection.stdout.split('\t', 1)[0].rstrip('\n') if selection.returncode == 0 else ''


def resolve_worktree_pr_branch(reference):
    repository_url = run(['gh', 'repo', 'view', '--json', 'url', '--jq', '.url'], check=True)
    _, head_branch = github.resolve_pr(github.pr_reference_url(reference, repository_url))
    if not head_branch:
        raise ValueError(f'Could not resolve PR {reference} to a branch.')
    return head_branch


def worktree_candidates(porcelain_output):
    candidate_lines = []
    for worktree_record in porcelain_output.split('\0\0'):
        worktree_fields = dict(field.split(' ', 1) for field in worktree_record.split('\0') if ' ' in field)
        if 'worktree' in worktree_fields:
            candidate_lines.append(worktree_fields['worktree'] + '\t' + worktree_fields.get('branch', '').removeprefix('refs/heads/'))
    return candidate_lines
