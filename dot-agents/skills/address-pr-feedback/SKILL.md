---
name: address-pr-feedback
description: Fetch, triage, and address GitHub pull request review feedback. Use when Codex or Claude Code needs to inspect PR comments or review threads, implement justified fixes, independently decline low-value suggestions, escalate decisions requiring human direction, push changes, reply with the required coding-agent prefix, and resolve threads whose outcome the human decided.
---

# Address PR Feedback

## Overview

Use this workflow to respond to GitHub PR feedback with independent judgment. Implement justified fixes and decline low-value suggestions without asking the human to make ordinary engineering judgments. Reserve escalation for decisions that require human direction.

## Workflow

1. **Identify the PR and branch**
   - Determine the active PR from the user's prompt, current branch, or GitHub tooling.
   - If the PR cannot be identified, ask for the PR URL or number before making changes.
   - Confirm the local branch matches the PR branch before editing.

2. **Fetch the full feedback context**
   - Fetch PR review comments, issue comments, and unresolved review threads from GitHub before evaluating feedback.
   - Include feedback on earlier commits and threads marked outdated; neither the commit age nor GitHub's outdated marker means the feedback is no longer relevant.
   - Prefer the GitHub app or available GitHub tools for PR metadata and comments.
   - Use `gh` when thread resolution state, inline context, or a complete review-thread view is not available through the app.
   - Read the surrounding diff and touched files for each inline comment before judging it.
   - Identify each comment's author using GitHub account metadata and, for coding agents posting through a shared account, an explicit coding-agent marker. Treat uncertain authorship as human. Human feedback still belongs in the context and triage below.
   - For feedback on earlier commits, read the original comment and diff context, then compare the concern with the current PR code. Address it through the same workflow if it still applies.

3. **Classify each feedback item**
   - Assess the actual code and established requirements rather than accepting the reviewer's label or proposed fix. For correctness findings, weigh reachability, likelihood, impact, and fix cost. A rare runtime input is not automatically a human decision; rarity alone does not justify declining a cheap fix that prevents serious harm.
   - Investigate ordinary uncertainty through the surrounding code and focused checks, then make the engineering judgment. A hypothetical future edit or reviewer preference alone does not establish that a change is worthwhile.
   - **Implement:** The comment demonstrates a bug, meaningful regression or security risk, clear violation of established standards, or a maintainability improvement whose benefit justifies its cost. Choose the smallest coherent fix, which may differ from the reviewer's proposals.
   - **No longer relevant:** After reading the feedback and checking the current code, the concern has already been addressed or the affected behavior no longer exists. Do not use this classification solely because the comment targets an earlier commit or an outdated diff.
   - **Decline:** The comment is based on a misunderstanding, contradicts established patterns, creates worse coupling, or asks for cosmetic preferences, speculative future-maintenance work, unnecessary abstractions, unrelated refactors, or improbable edge-case handling whose benefit does not justify the complexity. Decline these independently and explain the concrete tradeoff.
   - **Human decision:** Addressing the finding requires a new product policy, reversing an explicit user decision, materially expanding the agreed scope, or choosing between significant unresolved architecture alternatives. Routine implementation choices, reviewer preferences, and ordinary uncertainty do not belong in this category.

4. **Act on the classification**
   - Proceed with justified fixes and independent declines without requesting confirmation.
   - For human decisions, present the comment link, the specific policy, scope, or architecture choice, and a recommendation. Check whether the user has already supplied that direction before asking again.
   - Wait for the required human decision before making the dependent change; continue independent fixes while waiting.

5. **Implement necessary changes**
   - Make the smallest coherent changes that address feedback classified for implementation.
   - Preserve project ownership boundaries: put logic in the service or module that owns the concept, not merely where the current workflow happens to be orchestrated.
   - Add or update focused tests when the feedback changes behavior or covers a regression risk.
   - Avoid unrelated cleanup, style churn, and broad refactors unless they are required to resolve the justified finding.

6. **Verify, commit, and push**
   - Run the narrowest meaningful validation for the files changed, plus broader checks when the feedback touches shared behavior.
   - Commit fixes in atomic units of work.
   - Push the branch after committing.

7. **Reply on the PR**
   - Never reply to human reviewers' comments. Reply only to comments verified as authored by a bot or coding agent; this restriction applies to inline replies, review responses, and top-level comments that answer or mention the human's feedback.
   - In mixed-author threads, check both the thread's original comment and the specific comment being answered. Do not reply to a human-authored thread or answer a human follow-up in a bot-authored thread. Report any needed response to the user in chat instead.
   - Prefix every PR comment made by the coding agent with the correct marker:
     - Use `[coding codex COMMIT_HASH]` when the agent is Codex, replacing `COMMIT_HASH` with the relevant fix commit hash.
     - Use `[coding claude COMMIT_HASH]` when the agent is Claude Code, replacing `COMMIT_HASH` with the relevant fix commit hash.
     - When no fix commit is needed, use the current PR head commit hash that you evaluated.
   - For implemented feedback, briefly state what changed and include the commit or pushed branch context when useful.
   - For feedback that is no longer relevant, reply explaining why it no longer applies, citing the change or current code that supports that conclusion. Do not silently skip it.
   - For declined feedback, explain the concrete reason and tradeoff, including relevant evidence about reachability, impact, or complexity. Invite clarification if the reviewer has evidence that changes the assessment; human approval is not required for the decline.
   - For human decisions, summarize the specific direction needed and why existing requirements do not settle it.

8. **Resolve threads the human decided**
   - Reviewers resolve only findings they have verified as fixed, and a finding the human accepts, defers, or declines still applies to the code. Unless you resolve those threads, nobody will.
   - When the human has explicitly decided a thread's outcome (accept the limitation, defer it to a follow-up, or decline it), resolve the thread. Reply with the decision first only when step 7 permits a reply; otherwise report the decision to the user in chat without posting a PR response. For inline threads, use the `resolveReviewThread` GraphQL mutation through `gh api graphql`.
   - Leave threads open when a fix is implemented, so the reviewer can verify and resolve them. Leave them open too when you independently declined the feedback, or when an item still awaits the human's decision.

## Output Expectations

When handing control back to the user, include:

- A short summary of comments fetched and classifications made.
- The justified fixes implemented.
- Independently declined items and their concrete reasons, plus any outstanding human decisions.
- Validation run and any failures or skipped checks.
- Push status and PR comment status, including which threads you resolved and which remain open.
