---
name: commit-conventions
description: Apply this repo's session-tagging conventions when committing and when drafting or refreshing a pull request's title and description. Use when Codex or Claude Code needs to open a new PR or keep an existing one's title/description current, follow the target repo's own PR conventions, and gauge from commit trailers how much license this session has to rewrite a PR that other sessions have also worked on.
---

# Commit Conventions

## Overview

Use this workflow whenever a PR needs to be opened or its title/description brought up to date with the branch's current scope. The title and description should follow whatever PR conventions the target repo actually has, and — when other sessions have also committed to this branch — should be rewritten only as aggressively as this session's actual share of the work justifies.

Multiple sessions — Claude Code and Codex, or multiple instances of the same one — may end up pushing to the same branch. Every commit carries a `[coding $MODEL_NAME $SESSION_ID]` trailer (see root `AGENTS.md`), which is the only place this tag lives — it is never written into a PR title or description. This skill reads those trailers to tell whether it's safe to substantially rewrite the PR, or whether another session is clearly driving it and edits should stay minimal.

## Workflow

1. **Gather this repo's PR conventions**
   - Read the target repo's own guidance before drafting anything, in this order of precedence: its `AGENTS.md`/`CLAUDE.md` (branch naming, title/description rules), `.github/PULL_REQUEST_TEMPLATE.md`, then `CONTRIBUTING.md`.
   - If none of those specify a body structure, default to a `## Summary` / `## Test plan` body, matching `gh pr create`'s own default template.
   - Carry forward any cross-repo conventions from this dotfiles repo's root `AGENTS.md` that apply regardless of target repo (e.g. `eq/<type>/<description>` branch naming, the mandatory attribution footer).

2. **Tally the branch's commits by session**
   - Determine this session's own tag: `MODEL_NAME` is `claude` or `codex`; `SESSION_ID` is `$CLAUDE_CODE_SESSION_ID` in Claude Code, or the equivalent value Codex exposes. Never fabricate one.
   - Walk the branch's commits since it diverged from the base branch (e.g. `git log <base>..HEAD`) and read each commit's `[coding $MODEL_NAME $SESSION_ID]` trailer.
   - Tally commits into "this session" vs. "other sessions."

3. **Decide how much latitude to take**
   - All commits (or the only commits) are this session's: free to write or rewrite the title and description from scratch, reflecting the branch's current overall scope.
   - Other sessions have commits too:
     - This session is a small minority of the work: make minimal, additive edits. Describe only what this session added; don't restructure the existing title or another session's framing.
     - This session's commits have grown into a clear majority of the branch's work: fine to substantially rewrite the title/description to match current scope, since this session is effectively driving the PR now.
     - When it's close or unclear, default to the minimal-edit path.

4. **Draft or update the title and description**
   - Title: a concise, human-readable summary of the PR's *current overall* purpose — not just the latest commit, and never a `[coding ...]` tag.
   - Description: follow the structure identified in step 1. When rewriting is warranted (step 3), rewrite stale sections rather than only appending, so the description matches the PR's actual current scope. When only minimal edits are warranted, append or touch up rather than restructure.

5. **Create or update the PR**
   - New PR: `gh pr create --title "..." --body "..."`.
   - Existing PR: `gh pr edit <number> --title "..." --body "..."`.
   - End the description with the attribution footer required for this session.

6. **Report back**
   - State the commit tally (this session vs. others) and how much of the title/description was rewritten as a result.
   - Share the final title and a short summary of what the description now says.

## Notes

- The `[coding $MODEL_NAME $SESSION_ID]` trailer is a commit-message convention only (root `AGENTS.md`). This skill reads it to calibrate edits; it never copies the tag into a PR's title or body.
- This is distinct from the `[coding claude COMMIT_HASH]` / `[coding codex COMMIT_HASH]` prefix used by `address-pr-feedback` on PR *comments* — that one identifies which fix commit a reply is about, and does appear in the comment text itself.
