#!/bin/bash
# Claude Code status line: shows the model, reasoning effort, working directory,
# and current git branch.
# Claude Code pipes a JSON blob with session context to this script on stdin.

input=$(cat)
{
  IFS= read -r dir
  IFS= read -r model
  IFS= read -r effort
} < <(jq -r '.workspace.current_dir // .cwd // "", .model.display_name // "", .effort.level // ""' <<< "$input")
branch=$(git -C "$dir" branch --show-current 2>/dev/null)

dir="${dir/#$HOME/~}"
segments=()
[ -n "$model" ] && segments+=("$model")
[ -n "$effort" ] && segments+=("effort: $effort")
segments+=("$dir")
[ -n "$branch" ] && segments+=("$branch")

output=""
for segment in "${segments[@]}"; do
  output+="${output:+ · }$segment"
done
printf '%s\n' "$output"
