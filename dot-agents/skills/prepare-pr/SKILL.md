---
name: prepare-pr
description: Draft or refresh a pull request's title and description before creating it, pushing to it, or handing it back to the user. Use when Codex or Claude Code needs to open a new PR or keep an existing one's title/description current, follow the target repo's own PR conventions, and manage the `[coding $MODEL_NAME $SESSION_ID]` primary-worker tag so concurrent sessions or models never collide over PR ownership.
---

# Prepare PR

## Overview

Use this workflow whenever a PR needs to be opened or its title/description brought up to date with the branch's current scope. Two things must both be true of the result: the title and description follow whatever PR conventions the target repo actually has, and the title carries a `[coding $MODEL_NAME $SESSION_ID]` tag that correctly reflects which session is the PR's primary worker.

Multiple sessions — different models, different agents (Codex, Claude Code), or multiple instances of the same one — may end up pushing to the same branch. The tag exists so anyone looking at `gh pr list`/`gh pr view` can tell at a glance who is driving the PR, without opening every commit.

## Workflow

1. **Gather this repo's PR conventions**
   - Read the target repo's own guidance before drafting anything, in this order of precedence: its `AGENTS.md`/`CLAUDE.md` (branch naming, title/description rules), `.github/PULL_REQUEST_TEMPLATE.md`, then `CONTRIBUTING.md`.
   - If none of those specify a body structure, default to a `## Summary` / `## Test plan` body, matching `gh pr create`'s own default template.
   - Carry forward any cross-repo conventions from this dotfiles repo's root `AGENTS.md` that apply regardless of target repo (e.g. `eq/<type>/<description>` branch naming, the mandatory attribution footer).

2. **Determine this session's tag components**
   - `MODEL_NAME`: the specific model driving this session (e.g. `claude-sonnet-5`, `gpt-5.1-codex`) — not just the agent brand, since two sessions on the same coding agent but different models must still be distinguishable.
   - `SESSION_ID`: this run's own session identifier — `$CLAUDE_CODE_SESSION_ID` in Claude Code, or the equivalent value Codex exposes for its session. Never fabricate one; if it truly cannot be read, ask the user rather than guessing.
   - Compose `TAG = [coding $MODEL_NAME $SESSION_ID]`.

3. **Decide primary-worker status**
   - No PR exists yet: this session is primary by default. The title will start with `TAG`.
   - A PR already exists: fetch its current title.
     - No `[coding ...]` tag present: claim primary — prepend `TAG`.
     - Tag present with this session's own `SESSION_ID`: already primary, keep it as-is.
     - Tag present with a different `SESSION_ID` (same or different model/agent): **defer**. Do not touch the existing tag or claim primary. Edit only the rest of the title/description.
       - Reassess only if this session has clearly taken on the bulk of the work. Compare commits on the branch by their `[coding ...]` trailer (see root `AGENTS.md`): count commits per session, and if that's close, compare lines changed instead. Take over only on a clear majority — not a plurality, not a close call.
       - On takeover, replace the old tag with this session's `TAG` and add one short line to the description noting the handover (who, and why, e.g. "Primary worker reassigned: this session has authored the majority of commits since X.") so it is never silent.
       - Never remove or rewrite another session's tag for any other reason.

4. **Draft or update the title and description**
   - Title: `TAG` (only when this session is primary) followed by a concise, human-readable summary of the PR's *current overall* purpose — not just the latest commit.
   - Description: follow the structure identified in step 1. Rewrite stale sections rather than only appending, so the description always matches the PR's actual current scope.
   - Do not repeat the tag inside the body unless the repo's own template has a dedicated metadata/owner field.

5. **Create or update the PR**
   - New PR: `gh pr create --title "..." --body "..."`.
   - Existing PR: `gh pr edit <number> --title "..." --body "..."`.
   - End the description with the attribution footer required for this session.

6. **Report back**
   - State plainly whether this session claimed, kept, deferred on, or took over primary-worker status, and why.
   - Share the final title and a short summary of what the description now says.

## Notes

- This skill governs the PR-level (title) tag only. Commit-level disambiguation is a separate, always-on rule in root `AGENTS.md`: every commit carries its own `[coding $MODEL_NAME $SESSION_ID]` trailer regardless of who currently holds PR-primary status. That trailer is what step 3's takeover comparison reads.
- This is distinct from the `[coding claude COMMIT_HASH]` / `[coding codex COMMIT_HASH]` prefix used by `address-pr-feedback` on PR *comments* — that one identifies which fix commit a reply is about; this one identifies which session is driving the PR as a whole.
