#!/bin/bash
# Surfaces coding-agent attention state in the tmux footer, the WezTerm tab, and
# the macOS Dock, so an agent working in a background window is noticeable when
# it finishes or blocks on input.
#
# Runs as a Claude Code and Codex lifecycle hook; both agents pass their hook
# payload as JSON on stdin. State lives in a tmux per-window user option rather
# than a state directory so it is discarded automatically with the window.

set -uo pipefail

readonly ALERT_APP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/AgentAlert.app"
readonly WEZTERM_BUNDLE_ID='com.github.wez.wezterm'
readonly TMUX_STATE_OPTION='@agent_state'

main() {
  local state
  state="$(resolve_state "$(cat)")"

  # tmux holds the state, so outside tmux only the Dock bounce is meaningful.
  if [ -n "${TMUX_PANE:-}" ]; then
    store_state "$state"
    publish_wezterm_tab_marker
  fi

  case "$state" in
    waiting) is_user_watching || request_dock_attention ;;
    working) cancel_dock_attention ;;
  esac
}

# Collapses the two agents' hook vocabularies into waiting, done, or working.
# SessionStart clears as well as the obvious events, so a window that kept a stale
# marker from a session that died without exiting cleanly resets on reuse.
# Claude Code reports a blocked agent through Notification, distinguished from
# its post-turn idle and completion notices by notification_type; Codex reports
# the same condition as its own PermissionRequest event.
resolve_state() {
  local event notification_type
  {
    IFS= read -r event
    IFS= read -r notification_type
  } < <(jq -r '.hook_event_name // "", .notification_type // ""' <<< "$1")

  case "$event" in
    SessionStart | UserPromptSubmit | SessionEnd) printf 'working' ;;
    PermissionRequest) printf 'waiting' ;;
    Stop) printf 'done' ;;
    Notification)
      case "$notification_type" in
        idle_prompt | agent_completed) printf 'done' ;;
        *) printf 'waiting' ;;
      esac
      ;;
    *) printf 'working' ;;
  esac
}

# Records the state on the agent's tmux window. tmux resolves the option against
# whichever window it is drawing, which is what lets one shared status format
# mark only the windows that are actually pending.
store_state() {
  local window
  window="$(tmux display-message -p -t "$TMUX_PANE" '#{window_id}' 2>/dev/null)"
  [ -n "$window" ] || return 0

  if [ "$1" = working ]; then
    tmux set-option -wu -t "$window" "$TMUX_STATE_OPTION" 2>/dev/null
  else
    tmux set-option -w -t "$window" "$TMUX_STATE_OPTION" "$1" 2>/dev/null
  fi
  tmux refresh-client -S 2>/dev/null
}

# WezTerm shows one tab per tmux client, so the tab marker has to aggregate every
# window rather than describe this one. Writing OSC 1337 straight to the client
# tty deliberately bypasses tmux: tmux's passthrough drops sequences emitted from
# a window that is not currently visible, which is exactly this case.
publish_wezterm_tab_marker() {
  local waiting finished marker tty
  waiting="$(count_windows_in_state waiting)"
  finished="$(count_windows_in_state done)"
  marker="$(format_marker "$waiting" "$finished")"

  tty="$(tmux display-message -p -t "$TMUX_PANE" '#{client_tty}' 2>/dev/null)"
  [ -n "$tty" ] && [ -w "$tty" ] || return 0
  printf '\033]1337;SetUserVar=agent_alert=%s\a' "$(printf '%s' "$marker" | base64)" > "$tty"
}

count_windows_in_state() {
  tmux list-windows -a -F "#{$TMUX_STATE_OPTION}" 2>/dev/null | grep -c "^$1$"
}

# Waiting outranks done, and a count is only worth showing once more than one
# window is pending.
format_marker() {
  local glyph count
  if [ "$1" -gt 0 ]; then
    glyph='!'
    count="$1"
  elif [ "$2" -gt 0 ]; then
    glyph='*'
    count="$2"
  else
    return 0
  fi

  if [ "$count" -gt 1 ]; then
    printf '%s%s' "$glyph" "$count"
  else
    printf '%s' "$glyph"
  fi
}

# Treats the agent as already on screen when its tmux window is the current one
# of an attached session and WezTerm is frontmost, so watching an agent work does
# not bounce the Dock at you. lsappinfo is used instead of System Events because
# it reports the frontmost app without needing accessibility permission.
is_user_watching() {
  local active attached frontmost
  {
    IFS= read -r active
    IFS= read -r attached
  } < <(tmux display-message -p -t "$TMUX_PANE" $'#{window_active}\n#{session_attached}' 2>/dev/null)

  [ "${active:-0}" = 1 ] || return 1
  [ "${attached:-0}" != 0 ] || return 1

  frontmost="$(lsappinfo info -only bundleid "$(lsappinfo front 2>/dev/null)" 2>/dev/null |
    sed -E 's/.*"([^"]*)"$/\1/')"
  [ "$frontmost" = "$WEZTERM_BUNDLE_ID" ]
}

# The helper bounces only while it is alive, so a second instance would add
# nothing and would outlive the first one's timeout.
request_dock_attention() {
  pgrep -f "$ALERT_APP" >/dev/null 2>&1 && return 0
  open -g "$ALERT_APP" 2>/dev/null
}

cancel_dock_attention() {
  pkill -f "$ALERT_APP" 2>/dev/null
  return 0
}

main "$@"
