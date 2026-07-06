---
name: address-pr-feedback
description: Fetch, triage, and address GitHub pull request review feedback. Use when Codex or Claude Code needs to inspect PR comments or review threads, judge which feedback is valid versus excessive or inappropriate, flag edge cases for a human decision, implement justified fixes, push changes, and reply to PR comments with the required coding-agent prefix.
---

# Address PR Feedback

## Overview

Use this workflow to respond to GitHub PR feedback with judgment. Do not blindly apply every suggestion: separate valid feedback from excessive requests, questionable direction, and comments that need human product or architecture input.

## Workflow

1. **Identify the PR and branch**
   - Determine the active PR from the user's prompt, current branch, or GitHub tooling.
   - If the PR cannot be identified, ask for the PR URL or number before making changes.
   - Confirm the local branch matches the PR branch before editing.

2. **Fetch the full feedback context**
   - Fetch PR review comments, issue comments, and unresolved review threads from GitHub before evaluating feedback.
   - Prefer the GitHub app or available GitHub tools for PR metadata and comments.
   - Use `gh` when thread resolution state, inline context, or a complete review-thread view is not available through the app.
   - Read the surrounding diff and touched files for each inline comment before judging it.

3. **Classify each feedback item**
   - **Valid:** The comment identifies a correctness issue, regression risk, maintainability problem, missing test, unclear naming, security concern, or repo-standard violation.
   - **Too much / does not make sense:** The comment asks for unrelated refactors, contradicts project patterns, creates worse coupling, exceeds the PR scope without clear benefit, or is based on a misunderstanding of the code.
   - **Edge / human decision:** The comment involves product behavior, architecture ownership, tradeoffs with no clear winner, large scope expansion, reviewer preference, or anything you are not confident should be accepted.

4. **Report edge cases before acting on them**
   - Present edge cases to the human with the comment link, your read of the tradeoff, and a recommended decision.
   - Continue with clearly valid, independent fixes when doing so is safe.
   - Do not implement edge-case or "too much" requests unless the human confirms.

5. **Implement necessary changes**
   - Make the smallest coherent changes that address valid feedback.
   - Preserve project ownership boundaries: put logic in the service or module that owns the concept, not merely where the current workflow happens to be orchestrated.
   - Add or update focused tests when the feedback changes behavior or covers a regression risk.
   - Avoid unrelated cleanup, style churn, and broad refactors unless they are required to resolve valid feedback.

6. **Verify, commit, and push**
   - Run the narrowest meaningful validation for the files changed, plus broader checks when the feedback touches shared behavior.
   - Commit fixes in atomic units of work.
   - Push the branch after committing.

7. **Reply on the PR**
   - Prefix every PR comment made by the coding agent with the correct marker:
     - Use `[coding codex COMMIT_HASH]` when the agent is Codex, replacing `COMMIT_HASH` with the relevant fix commit hash.
     - Use `[coding claude COMMIT_HASH]` when the agent is Claude Code, replacing `COMMIT_HASH` with the relevant fix commit hash.
   - For implemented feedback, briefly state what changed and include the commit or pushed branch context when useful.
   - For feedback judged too much or invalid, explain the reason respectfully and invite the reviewer to clarify if they disagree.
   - For edge cases, state that the item needs human confirmation and summarize the decision needed.

## Output Expectations

When handing control back to the user, include:

- A short summary of comments fetched and classifications made.
- The valid feedback implemented.
- Edge or declined items and why they were not implemented.
- Validation run and any failures or skipped checks.
- Push status and PR comment status.
