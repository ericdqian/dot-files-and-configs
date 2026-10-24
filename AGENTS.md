Make frequent commmits for what would be considered atomic units of work.

Every commit subject line must start with a `[$MODEL_NAME $SESSION_ID]` prefix, e.g. `[claude eaf85d4d-de26-4a85-b52e-cb262f75f3ff] fix: handle empty input`, where `$MODEL_NAME` is `claude` or `codex` (whichever agent is driving the session) and `$SESSION_ID` is that session's own identifier (`$CLAUDE_CODE_SESSION_ID` in Claude Code, or the equivalent value Codex exposes for its session). This disambiguates authorship when more than one session is working on the same branch concurrently, and the `/commit-conventions` skill relies on these prefixes to gauge how much license a session has to rewrite a PR's title and description.

Before beginning work, create a thorough plan. Ask the user questions to resolve meaningful ambiguity before proceeding, especially when assumptions could change scope, implementation, or user-visible behavior.

Skip the plan when the task is unambiguous, the work is short, or the steps to resolve it are uncontroversial. Renaming a symbol, fixing a typo, or updating a branch by fetching main, rebasing, and pushing are examples where you should just do the work and report what you did. Plan when none of those hold, such as when the request has more than one reasonable interpretation, the change spans multiple modules or domains, and the approach itself is a real decision. When in doubt, plan and propose it.

Once you have enough context for a good task description and are ready to implement, promptly check whether you are running inside tmux. If so, use the agent process's `$TMUX_PANE` to resolve its own stable window ID, then pass that ID explicitly to `tmux rename-window -t`; never rely on tmux's implicit current-window target, because the user may switch windows between commands. For example:

```sh
tmux_window_id="$(tmux display-message -p -t "$TMUX_PANE" '#{window_id}')"
tmux rename-window -t "$tmux_window_id" 'short purpose'
```

Rename that window once to a short description of the current or anticipated PR's purpose, approximately three words long. Keep that window name stable throughout the PR; do not rename it for individual tasks or implementation phases. Rename it again only if the PR's overall purpose materially changes.

Before you return control to the user, if you have new commits, push. If no PR exists yet, make one. Make the PR description using the /commit-conventions skill. Keep the PR title and description updated so they accurately reflect the current status and scope of the PR as it evolves.

When creating or updating a PR description, include a line-change table with `Category`, `Added`, `Removed`, and `Net` columns. Use these rows in order: `Production code`, `Tests`, `Documentation`, `Generated code`, `Configuration`, and `Total`. Include every category even when its counts are zero; calculate `Net` as added minus removed.

Measure the entire PR against its base branch using the merge-base diff (for example, `git diff --numstat origin/main...HEAD`), not just the latest commit. Classify each changed line exactly once by purpose, rather than file extension, so the category counts sum to the total. Agent guidance belongs under documentation; settings, manifests, and lockfiles belong under configuration. Keep generated code separate from handwritten production code. Report binary files separately when Git cannot provide line counts.

Briefly note substantial code moves or refactors below the table so relocated lines are not mistaken for new functionality. Refresh the table when updating the PR description as the scope changes.

Opened PR branches should use the format `eq/<type>/<description>`, such as `eq/chore/update-install-scripts`, where `<type>` is `feat`, `bug`, or `chore` depending on the PR's purpose. Use `feat` for features, `bug` for fixes, and `chore` for scripts, maintenance, or other changes that do not add real product functionality.

When the user asks you to revise something you already did, or gives guidance that sounds like a reusable principle, ask whether they would like that feedback persisted into an `AGENTS.md` file for future agents.

Before running `tofu apply`, `terraform apply`, or any equivalent command that mutates managed infrastructure, show the user the relevant code/config diff and wait for explicit approval to apply. Do not treat plan approval, implementation approval, or a successful validation as approval to apply infrastructure changes.

Function and method ordering:
- Order code for the reader's path through the file.
- Put each top-level function or method before the helpers that serve it.
- Put those helpers immediately after that top-level function or method.
- Then move on to the next top-level function or method and its helpers.
- For a class that handles a business entity's lifecycle, order its methods by the sequence they are normally invoked in, such as create/setup methods first, then update/transition methods, then completion/archive/delete methods.
- For example, if top-level function `A` uses helpers `a` and `b`, and top-level function `B` uses helpers `c` and `d`, prefer this order: `A`, `a`, `b`, `B`, `c`, `d`.

Name every parameter and local variable so its intent is clear from any line where it appears, without reading back to its declaration or its call sites. A reader who opens a function in the middle should know what each name holds: which entity, which stage of processing, and which side of a mapping. Prefer `saved_extraction`, `census_snapshot`, `proposed_merge`, and `unresolved_results` over `saved`, `census`, `update`, and `unresolved`. When a function holds several values of the same type or concept, name each for its role, such as `previous_proposal` versus `latest_proposal` or `original_value` versus `repaired_value`. Name index lists and maps for both sides, such as `proposal_rows_to_source_members`. Short names are fine only for a loop variable or lambda parameter whose meaning is obvious within a line or two.

Functions and methods should be pure by default. Do not give a function side effects unless there is a very good reason, and make any necessary side effect obvious from the function name and call site. Avoid helpers whose return value is ignored because they are being used only to throw, mutate, write, enqueue, log, cache, or perform IO. If a side effect is intentional, call out why that side effect belongs there in a short nearby comment.

Keep simple batching and retry loops beside the requests they control. Do not
pass request functions or callbacks into a generic window orchestrator just to
share loop mechanics. Share constants or small pure policy calculations when
needed, while leaving request order and retry behavior visible at the call site.

Do not mutate input parameters, including objects, arrays, maps, or sets passed by callers. Prefer returning new values and keeping data flow lean and functional. If input mutation is necessary for performance, an external API contract, transaction semantics, or another strong reason, call out why the mutation is acceptable near the mutation site and keep it narrowly scoped.

Only define a named TypeScript type when it is used more than once. For one-off input or output shapes, inline the type at the function, method, or variable boundary instead of naming it.

Scope `AGENTS.md` files to the directory where the guidance applies. Generic agent behavior and cross-repo preferences belong in this root `AGENTS.md`, which is symlinked into the global agent locations. Repo-specific instructions should live in that repo's `AGENTS.md`, and directory- or subsystem-specific instructions should live in the deepest relevant directory so only the right files inherit them. If a repo-specific rule reveals a broader reusable principle, that generalized principle may be added to this root `AGENTS.md` while the concrete repo-specific rule stays in the relevant repo or directory. Do not duplicate narrow instructions in broader files unless the broader file needs to point agents to where the narrower guidance lives.

Treat semantic divergence among a directory's files as a smell that the directory needs further splitting. Group cohesive responsibilities into subdirectories named for the concepts they own, and keep shared files at the closest common parent where their meaning remains clear.

## Worktrees and agent navigation

Before implementing branch or PR work, reuse the existing Git worktree for the target branch, even when another agent is already working in it, so the PR's changes are runnable locally in one place that reflects the PR. Create a dedicated worktree only when none exists for the branch, and do not work in the main checkout unless the user explicitly requests it. When sharing a worktree, stage files by name and do not rewrite or discard another agent's uncommitted work. Follow the target repository’s guidance for worktree locations and base branches; do not relocate running agents or move existing uncommitted work automatically.

Inside tmux, keep a one-to-one relationship between a branch (and its PR) and a tmux window. All panes in a claimed window support that same branch. Reuse its existing window for follow-up work, including when another agent shares the worktree. For a new branch or PR, open a separate window in the source agent's existing tmux session; never repurpose the old branch's window or mix PRs across its panes. Do not automatically move running agents or their uncommitted changes.

When `~/.tmux/navigation/search.py` exists, use it to register explicit window ownership rather than relying on pane directories or names:

- From the repository, run `python3 ~/.tmux/navigation/search.py start BRANCH --checkout PATH --base BASE --name 'Short purpose' --pane SOURCE_PANE`. Resolve `SOURCE_PANE` from the agent's own `$TMUX_PANE`, never tmux's implicit current pane. The command reuses the branch's existing worktree and owned window if present; otherwise it creates the worktree and a new window in the source pane's session. `PATH` is the proposed location only when no worktree exists. Use the returned worktree path and destination pane ID for subsequent work and navigation commands.
- Opening a window does not relocate the running agent. Launch any continuation in the destination window with the task context, or explicitly target its returned pane ID and worktree when using tools from the original agent. Keep lifecycle-hook observations from the source pane from claiming the new branch there.
- When already in the correct branch window, run `python3 ~/.tmux/navigation/search.py claim --checkout PATH --name 'Short purpose' --pane DESTINATION_PANE`. This records repository, branch, checkout, agent session, and description on the window. A conflicting claim is an error: reuse the reported owner window or run `start`; do not unset another branch's ownership to bypass it.
- After creating or changing the associated PR, run `python3 ~/.tmux/navigation/search.py claim PR_URL --checkout PATH --pane DESTINATION_PANE`. This adds the PR URL to the same window record so the navigator can resolve it locally. Keep the window's short purpose stable throughout that PR. Do not use historical `link` records to associate another PR with an owned window.
- If the agent's pane is known explicitly but `$TMUX_PANE` is unavailable, pass its stable `--pane %ID`. Never infer ownership from a shared checkout's current branch. If the helper is unavailable, create a window with `tmux new-window -d -P -F '#{pane_id}' -t SESSION_ID: -n 'Short purpose' -c PATH`, resolving `SESSION_ID` explicitly from the source pane; report that navigator ownership could not be registered. Outside tmux, use Git worktrees directly; there is no tmux destination to claim.
