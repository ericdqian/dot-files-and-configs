---
name: merge-pr
description: Rebase a GitHub pull request onto its latest target branch, validate migration lineage when relevant, push, and merge once all checks pass and no unresolved or actionable feedback remains. Use when the user asks to merge a PR or finish its merge workflow.
---

# Merge PR

Carry an identified PR through rebase, validation, push, checks, and merge. A request to merge authorizes the final merge once these gates pass; a request only to prepare or inspect a PR does not.

## Workflow

1. **Identify the PR and protect concurrent work**
   - Confirm the repository, PR number, head repository/branch, target branch, and current remote head SHA. Read the repository's agent guidance and merge conventions; reuse the head branch's existing worktree.
   - Use the PR's current target branch (`baseRefName`) as the rebase base, including non-main and stacked PR targets. Do not substitute `main` or silently retarget the PR.
   - Check for uncommitted work, an in-progress Git operation, and commits pushed by other sessions. Do not stash, discard, overwrite, or include another session's work automatically. Coordinate when safe ownership of the rebase is unclear.
   - Record the remote branch SHA that was inspected before rewriting history. Reconcile any local/remote divergence without dropping commits, and keep a local recovery reference to the pre-rebase head.

2. **Rebase onto the latest target branch**
   - Fetch the base repository's target branch and the PR head from their actual remotes (which can differ for fork PRs), then rebase the complete PR branch onto the fetched target branch.
   - Resolve conflicts only when the intended result is clear. Stop for a decision when a conflict changes behavior or risks losing concurrent work; do not skip commits merely to finish the rebase.

3. **Validate migration lineage when relevant**
   - Inspect migrations in both the PR diff and newly fetched target branch. When either changes migration ancestry or ordering, use the repository's migration tooling and conventions to verify a single linear chain per intended migration lineage: no competing heads, duplicate identifiers, missing predecessors, or cycles.
   - Reparent or renumber only PR-local, unapplied migrations where the framework permits it, preserving dependencies and execution order after the latest migration on the target branch. Do not add a merge migration that leaves branching ancestry merely to reduce the head count.
   - Do not rewrite migrations already applied, merged, or shared without explicit direction. If existing history branches or application status is uncertain, report the conflict and obtain a decision before changing that history or merging.
   - Run the repository's lineage validation and focused migration tests in its supported local/test environment. Do not apply migrations to a shared or production database as part of this workflow. Skip this step when migrations are irrelevant.

4. **Validate and push**
   - Run the repository's required local checks and focused tests for conflict resolutions or migration changes. Commit any fixes using the repository's commit conventions.
   - Push the rebased branch to the PR head remote. For rewritten history, use an explicit lease against the remote SHA recorded before the rebase, for example `git push --force-with-lease=refs/heads/BRANCH:EXPECTED_SHA HEAD:refs/heads/BRANCH`. Never use plain `--force`.
   - A rejected lease means someone changed the remote branch. Fetch and inspect their changes, reconcile them without loss, and repeat validation before pushing; do not simply refresh the lease and overwrite them.
   - Push subsequent fixes too. Use [commit-conventions](../commit-conventions/SKILL.md) when refreshing PR metadata after the branch's scope changes.

5. **Wait for checks and clear feedback**
   - Confirm the pushed local SHA matches the PR's remote head. Inspect all checks and commit statuses for that SHA, including optional checks; `gh pr checks PR --watch` can monitor completion. Do not restrict the gate to `--required` checks.
   - Require all expected checks to finish successfully. Pending, failing, cancelled, skipped, missing, or unreadable results are not evidence of success. If the repository intentionally has no checks, establish that from its configuration rather than treating an empty or delayed response as green.
   - Fetch all pages of PR conversation comments, review bodies, inline review comments, and review threads with resolution state, including feedback on earlier commits and outdated diffs. `gh pr view --comments` alone is insufficient for thread state.
   - Interpret "no comments" as no unresolved review threads, outstanding actionable feedback, or blocking reviews. Resolved historical discussion and informational bot messages may remain. A resolved marker does not excuse a still-actionable concern.
   - When feedback exists, follow [address-pr-feedback](../address-pr-feedback/SKILL.md) for triage, fixes, permitted replies, and thread resolution. Do not dismiss reviews or resolve threads unilaterally to satisfy the merge gate. Fixed but unresolved threads still block merging until the reviewer resolves them or the human explicitly decides their outcome.
   - After any fix or new push, repeat the push, check, and feedback gates for the new head SHA. If progress depends on a reviewer, permissions, unavailable checks, or a human decision, report the specific blocker rather than bypassing it or polling indefinitely.

6. **Recheck and merge the verified head**
   - Immediately before merging, re-read the PR's target branch and fetch it again. Verify its latest commit is an ancestor of the PR head. If the target changed or advanced beyond that head, repeat the rebase, migration validation, push, and gates against the current target.
   - Re-fetch the PR head SHA, all check results, feedback, and mergeability. Require the head to match the SHA just validated, all checks to pass, the feedback gate to remain clear, and repository review/protection requirements to be met. Restart the relevant gates if anything changed.
   - Merge using the repository's supported method and `gh pr merge PR --match-head-commit VERIFIED_SHA` with the appropriate strategy flag. Respect required merge queues; do not use `--admin` or auto-merge to bypass this skill's checks and feedback gate.
   - Verify GitHub reports the PR as merged. If queued, continue monitoring its checks and feedback until merged or blocked; queue admission alone is not completion. Report the PR URL, merge commit, validation performed, and any remaining blocker if it did not merge.
