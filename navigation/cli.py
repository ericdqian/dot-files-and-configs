#!/usr/bin/env python3
"""Resolve repository navigation references for shell commands."""
import argparse
import subprocess
import sys
from pathlib import Path

# Resolve the checkout behind installed symlinks so callers need no PYTHONPATH setup.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from navigation import picker, worktrees


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['worktree-branch', 'pick-worktree', 'query', 'accept'])
    parser.add_argument('reference', nargs='?', default='')
    parser.add_argument('--data', default='')
    parser.add_argument('--selected', default='')
    arguments = parser.parse_args()
    if arguments.action == 'worktree-branch':
        print(worktrees.resolve_worktree_pr_branch(arguments.reference))
    elif arguments.action == 'pick-worktree':
        selected_path = worktrees.pick_worktree(worktrees.worktree_candidates(sys.stdin.read()), arguments.reference)
        if selected_path:
            print(selected_path)
    elif arguments.action == 'query':
        picker.update_query_results(Path(arguments.data), arguments.reference)
    else:
        picker.print_accept_action(Path(arguments.data), arguments.reference, arguments.selected)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        print(f'Navigation: {error}', file=sys.stderr)
        sys.exit(1)
