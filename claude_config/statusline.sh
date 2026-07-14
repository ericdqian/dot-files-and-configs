#!/bin/bash
# Claude Code status line: shows the working directory and current git branch.
# Claude Code pipes a JSON blob with session context to this script on stdin.

input=$(cat)
dir=$(jq -r '.workspace.current_dir // .cwd' <<< "$input")
branch=$(git -C "$dir" branch --show-current 2>/dev/null)

dir="${dir/#$HOME/~}"
printf '%s%s\n' "$dir" "${branch:+ · $branch}"
