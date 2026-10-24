#!/usr/bin/env python3
"""Resolve repository navigation references for shell commands."""
import argparse
import re
import subprocess
import sys
from pathlib import Path

# Resolve the checkout behind installed symlinks so callers need no PYTHONPATH setup.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from navigation import github
from navigation.commands import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['worktree-branch'])
    parser.add_argument('reference')
    arguments = parser.parse_args()
    print(resolve_worktree_pr_branch(arguments.reference))


def resolve_worktree_pr_branch(reference):
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
    # Resolve a fresh PR head so worktree selection does not depend on cached search results.
    _, head_branch = github.resolve_pr(pr_url)
    if not head_branch:
        raise ValueError(f'Could not resolve PR {reference} to a branch.')
    return head_branch


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        print(f'Navigation: {error}', file=sys.stderr)
        sys.exit(1)
