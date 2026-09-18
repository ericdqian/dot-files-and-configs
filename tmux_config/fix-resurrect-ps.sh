#!/bin/sh
set -eu

[ "$(uname -s)" = Darwin ] || exit 0
strategy_file="${1:-$HOME/.tmux/plugins/tmux-resurrect/save_command_strategies/ps.sh}"
[ -f "$strategy_file" ] || exit 0

# Patch the installed plugin because macOS ps -a performs slow terminal-device
# lookups for every scan. Adding -x preserves command arguments and bypasses
# those lookups. Only change the known upstream command; leave other versions alone.
# Related: https://github.com/tmux-plugins/tmux-resurrect/issues/544
if grep -Fq 'ps -ao "ppid,args" |' "$strategy_file"; then
    sed -i '' 's/ps -ao "ppid,args" |/ps -axo "ppid,args" |/' "$strategy_file"
fi
