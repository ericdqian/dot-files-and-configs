#!/usr/bin/env zsh
set -euo pipefail

SCRIPT_PATH="${0:A}"
ZSH_CONFIG_DIR="${SCRIPT_PATH:h}"
WORKTREE_ROOT="${ZSH_CONFIG_DIR:h}"
TEST_ZDOTDIR="$(mktemp -d "${TMPDIR:-/tmp}/dotfiles-zsh-test.XXXXXX")"

cleanup() {
  rm -rf "$TEST_ZDOTDIR"
}

trap cleanup EXIT

{
  printf 'export HISTFILE=%q\n' "$TEST_ZDOTDIR/.zsh_history"
  printf 'export XDG_CACHE_HOME=%q\n' "$TEST_ZDOTDIR/.cache"
  printf 'export ZSH_CACHE_DIR=%q\n' "$TEST_ZDOTDIR/oh-my-zsh-cache"
  printf 'export CLOUDSDK_CONFIG=%q\n' "$TEST_ZDOTDIR/gcloud"
  printf 'export DOTFILE_CONFIG_PATH=%q\n' "$ZSH_CONFIG_DIR"
  printf 'source %q\n' "$ZSH_CONFIG_DIR/general_zsh_config"
  print -r -- ''
  printf 'print -r -- %q\n' "Loaded worktree zsh config from: $WORKTREE_ROOT"
  print -r -- 'print -r -- "EDITOR=$EDITOR VISUAL=$VISUAL"'
  print -r -- 'print -r -- "main keymap: $(bindkey -lL main)"'
  print -r -- 'print -r -- "Ctrl-V binding: $(bindkey '"'"'^V'"'"')"'
  print -r -- 'print -r -- "Type a command, press Ctrl-V, edit it in nvim, then :wq to return. Run exit when done."'
  print -r -- ''
} > "$TEST_ZDOTDIR/.zshrc"

print -r -- "Launching isolated zsh with ZDOTDIR=$TEST_ZDOTDIR"
ZDOTDIR="$TEST_ZDOTDIR" zsh -d -i
