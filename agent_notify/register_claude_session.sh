#!/bin/bash
# Register the live inbox locally so review completion can target a commit's UUID.
set -euo pipefail
umask 077

payload="$(cat)"
session_id="$(jq -er '.session_id | select(type == "string")' <<< "$payload")"
[[ "$session_id" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]] || exit 1
registry="${CLAUDE_SESSION_REGISTRY_DIR:-${HOME}/.local/state/coding-agents/claude-sessions}"
mkdir -p "$registry"

# Atomic replacement refreshes the endpoint on resume without exposing a partial file.
temporary="$(mktemp "$registry/.registration.XXXXXX")"
trap 'rm -f "$temporary"' EXIT
jq -n --arg sessionId "$session_id" \
  --arg messagingSocket "${CLAUDE_CODE_MESSAGING_SOCKET:-}" \
  '{sessionId: $sessionId, messagingSocket: $messagingSocket}' > "$temporary"
mv -f "$temporary" "$registry/$session_id.json"
