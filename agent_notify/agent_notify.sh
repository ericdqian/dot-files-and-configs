#!/bin/bash
# Surfaces coding-agent attention state in the tmux footer, the WezTerm tab, and
# the macOS Dock, so an agent working in a background window is noticeable when it
# finishes or blocks on input.
#
# Runs as a Claude Code and Codex lifecycle hook, reading the agent's hook payload
# as JSON on stdin; as a tmux hook in --reviewed mode; and as its own background
# supervisor in --rebounce mode. State lives in a tmux per-window user option
# rather than a state directory, so it is discarded automatically with the window.

set -uo pipefail

readonly SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
readonly ALERT_APP="$(dirname "$SELF")/AgentAlert.app"
readonly WEZTERM_BUNDLE_ID='com.github.wez.wezterm'
readonly STATE_OPTION='@agent_state'
readonly REBOUNCE_INTERVAL_SECONDS=180

main() {
  case "${1:-}" in
    --reviewed) clear_reviewed_marker "${2:-}" ;;
    --rebounce) rebounce_while_agents_wait ;;
    *) apply_hook_payload ;;
  esac
}

# Applies one Claude Code or Codex hook payload, read as JSON on stdin.
apply_hook_payload() {
  local state window attached
  state="$(resolve_state "$(cat)")"

  # A finished turn is only worth flagging if it finished out of sight, otherwise
  # the marker would appear on the window already being read and no later look
  # could clear it. A blocked agent is flagged either way, because that flag
  # stands until the agent is actually answered.
  if [ "$state" = done ] && is_user_watching "${TMUX_PANE:-}"; then
    state=working
  fi

  {
    IFS= read -r window
    IFS= read -r attached
  } < <(tmux display-message -p -t "${TMUX_PANE:-}" $'#{window_id}\n#{session_attached}' 2>/dev/null)

  # Outside tmux there is nothing to mark, and a window in a session with no
  # attached client cannot be seen or reviewed, so a marker there would only
  # inflate a count nobody can clear. A blocked agent still bounces either way,
  # because that needs answering wherever it happens to run.
  if [ -z "$window" ] || [ "${attached:-0}" = 0 ]; then
    [ "$state" = waiting ] && request_dock_attention
    return 0
  fi

  # PostToolUse fires on every tool call, so a state that has not changed must
  # cost nothing beyond the single read that proved it unchanged.
  [ "$(marker_for_state "$state")" != "$(current_marker "$window")" ] || return 0

  store_state "$window" "$state"
  publish_wezterm_tab_marker "$window"

  case "$state" in
    waiting)
      is_user_watching "$TMUX_PANE" || request_dock_attention
      start_rebounce_supervisor
      ;;
    working) cancel_dock_attention ;;
  esac
}

# Collapses the two agents' hook vocabularies into waiting, done, or working.
#
# PostToolUse is what releases a blocked agent: no hook fires when a permission is
# approved, and a tool that has run proves the approval happened, so without it a
# waiting marker would outlive the block and be re-bounced at.
#
# SessionStart clears as well as the obvious events, so a window that kept a stale
# marker from a session that died without exiting cleanly resets on reuse.
resolve_state() {
  local event notification_type
  {
    IFS= read -r event
    IFS= read -r notification_type
  } < <(jq -r '.hook_event_name // "", .notification_type // ""' <<< "$1")

  case "$event" in
    SessionStart | UserPromptSubmit | PostToolUse | SessionEnd) printf 'working' ;;
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

# Treats the agent as already on screen when its tmux window is the current one of
# an attached session and WezTerm is frontmost. lsappinfo is used rather than
# System Events because it reports the frontmost app without needing accessibility
# permission.
is_user_watching() {
  local active attached
  [ -n "$1" ] || return 1
  {
    IFS= read -r active
    IFS= read -r attached
  } < <(tmux display-message -p -t "$1" $'#{window_active}\n#{session_attached}' 2>/dev/null)

  [ "${active:-0}" = 1 ] || return 1
  [ "${attached:-0}" != 0 ] || return 1
  frontmost_is_wezterm
}

frontmost_is_wezterm() {
  local frontmost
  frontmost="$(lsappinfo info -only bundleid "$(lsappinfo front 2>/dev/null)" 2>/dev/null |
    sed -E 's/.*"([^"]*)"$/\1/')"
  [ "$frontmost" = "$WEZTERM_BUNDLE_ID" ]
}

# Working is the absence of a marker, so it maps to the unset option value.
marker_for_state() {
  [ "$1" = working ] || printf '%s' "$1"
}

current_marker() {
  tmux show-options -wqv -t "$1" "$STATE_OPTION" 2>/dev/null
}

# Records the state on the agent's tmux window. tmux resolves the option against
# whichever window it is drawing, which is what lets one shared status format mark
# only the windows that are actually pending.
store_state() {
  if [ "$2" = working ]; then
    tmux set-option -wu -t "$1" "$STATE_OPTION" 2>/dev/null
  else
    tmux set-option -w -t "$1" "$STATE_OPTION" "$2" 2>/dev/null
  fi
  tmux refresh-client -S 2>/dev/null
}

# WezTerm shows one tab per tmux client, so the tab marker has to aggregate every
# window rather than describe one. Writing OSC 1337 straight to the client tty
# deliberately bypasses tmux: tmux's passthrough drops sequences emitted from a
# window that is not currently visible, which is exactly the case worth reporting.
publish_wezterm_tab_marker() {
  local session tty marker
  {
    IFS= read -r session
    IFS= read -r tty
  } < <(tmux display-message -p -t "$1" $'#{session_name}\n#{client_tty}' 2>/dev/null)

  [ -n "$tty" ] && [ -w "$tty" ] || return 0
  marker="$(format_marker \
    "$(count_session_windows_in_state "$session" waiting)" \
    "$(count_session_windows_in_state "$session" done)")"
  printf '\033]1337;SetUserVar=agent_alert=%s\a' "$(printf '%s' "$marker" | base64)" > "$tty"
}

# The tab shows one tmux session, so its marker counts that session alone. A
# server-wide count would fold in detached sessions the tab never displays, which
# for a machine running background review agents is most of them.
count_session_windows_in_state() {
  tmux list-windows -t "$1" -F "#{$STATE_OPTION}" 2>/dev/null | grep -c "^$2$"
}

# The Dock, unlike the tab, speaks for the whole machine: an agent blocked in any
# session still needs answering.
count_all_windows_in_state() {
  tmux list-windows -a -F "#{$STATE_OPTION}" 2>/dev/null | grep -c "^$1$"
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

# The helper bounces only while it is alive, so a second instance would add
# nothing and would outlive the first one's timeout.
request_dock_attention() {
  pgrep -f "$ALERT_APP" >/dev/null 2>&1 && return 0
  open -g "$ALERT_APP" 2>/dev/null
}

# Detached by nohup so the supervisor outlives the hook that started it. One is
# enough: it watches every window, not just this one, and exits by itself.
start_rebounce_supervisor() {
  pgrep -f "$SELF --rebounce" >/dev/null 2>&1 && return 0
  nohup "$SELF" --rebounce >/dev/null 2>&1 &
}

cancel_dock_attention() {
  pkill -f "$ALERT_APP" 2>/dev/null
  return 0
}

# Drops the finished marker from a window that has just been looked at, leaving a
# waiting marker alone: that agent is still blocked, so the flag is still true and
# only answering it should clear it. Runs on every tmux focus change, so it costs
# a single option read in the overwhelmingly common case of nothing to clear.
clear_reviewed_marker() {
  local window="$1"
  [ -n "$window" ] || return 0
  [ "$(current_marker "$window")" = done ] || return 0

  tmux set-option -wu -t "$window" "$STATE_OPTION" 2>/dev/null
  tmux refresh-client -S 2>/dev/null
  publish_wezterm_tab_marker "$window"
}

# Keeps nagging while any agent stays blocked, so a first bounce that went unseen
# is not the only warning. It stays quiet while the blocked window is on screen but
# keeps running, so walking away resumes the reminders.
rebounce_while_agents_wait() {
  while [ "$(count_all_windows_in_state waiting)" -gt 0 ]; do
    sleep "$REBOUNCE_INTERVAL_SECONDS"
    drop_abandoned_markers
    unattended_waiting_exists && request_dock_attention
  done
}

# A session killed hard never fires SessionEnd, so its window would keep a marker
# and be nagged about forever. Rather than matching agent process names, which for
# Claude Code is its version number, this asks the inverse: a window whose panes
# have all fallen back to a shell has no agent left to be waiting for.
drop_abandoned_markers() {
  local window
  while IFS= read -r window; do
    window_runs_something "$window" && continue
    tmux set-option -wu -t "$window" "$STATE_OPTION" 2>/dev/null
    tmux refresh-client -S 2>/dev/null
    publish_wezterm_tab_marker "$window"
  done < <(tmux list-windows -a -F "#{?#{$STATE_OPTION},#{window_id},}" 2>/dev/null | grep .)
  return 0
}

window_runs_something() {
  tmux list-panes -t "$1" -F '#{pane_current_command}' 2>/dev/null |
    grep -qvE '^-?(zsh|bash|sh|fish|login)$'
}

unattended_waiting_exists() {
  local wezterm_front=false active attached state
  frontmost_is_wezterm && wezterm_front=true

  while IFS=: read -r active attached state; do
    [ "$state" = waiting ] || continue
    if [ "$wezterm_front" = true ] && [ "$active" = 1 ] && [ "$attached" != 0 ]; then
      continue
    fi
    return 0
  done < <(tmux list-windows -a -F "#{window_active}:#{session_attached}:#{$STATE_OPTION}" 2>/dev/null)

  return 1
}

main "$@"
