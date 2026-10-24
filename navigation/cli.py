#!/usr/bin/env python3
"""Resolve repository navigation references for shell commands."""
import argparse
import subprocess
import sys
from pathlib import Path

# Resolve the checkout behind installed symlinks so callers need no PYTHONPATH setup.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from navigation import worktrees


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['worktree-branch', 'pick-worktree', 'worktree-query', 'worktree-accept'])
    parser.add_argument('reference', nargs='?', default='')
    parser.add_argument('--data', default='')
    parser.add_argument('--selected', default='')
    arguments = parser.parse_args()
    if arguments.action == 'worktree-branch':
        print(worktrees.resolve_worktree_pr_branch(arguments.reference))
    elif arguments.action == 'pick-worktree':
        selected_path = worktrees.pick_worktree(sys.stdin.read().splitlines(), arguments.reference)
        if selected_path:
            print(selected_path)
    elif arguments.action == 'worktree-query':
        worktrees.update_worktree_query(Path(arguments.data), arguments.reference)
    else:
        worktrees.print_worktree_accept_action(Path(arguments.data), arguments.reference, arguments.selected)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        print(f'Navigation: {error}', file=sys.stderr)
        sys.exit(1)
