---
name: shortcut-stories
description: Turn merged or open pull requests into Shortcut stories and place them under the right epic. Use when the user asks to map PRs to stories, backfill Shortcut from recent work, draft story names, decide which epic a piece of work belongs to, or create or update stories through the Shortcut MCP connector.
---

# Shortcut Stories

## Overview

A Shortcut story names one concrete deliverable that a teammate could point at and say "that shipped." A story can span several PRs, but only when those PRs all build the same thing. The story name should say exactly what that thing is.

## Naming stories

Name the artifact or capability being built, not the category of work.

- Good: "Hermes release utilities", "Post execution failures to #eng-alerts", "Log client IPs behind the AWS ALB", "Ping the commit author when main fails the migration lineage check".
- Too general: "Hermes and agent deploy reliability", "Failure alerting and observability", "Codebase health", "Infra improvements".

Checks before accepting a name:

1. **Could someone tell from the name alone whether a given PR belongs?** If the name is a quality attribute (reliability, observability, efficiency, cleanup), it is an epic or theme, not a story. Narrow it to the specific tool, pipeline, table, flow, or behavior.
2. **Does the name use the system's own nouns?** Prefer the real names of services, commands, agents, channels, and entities (`cutil`, Hermes, Iris, `#eng-alerts`, census) over generic ones ("tooling", "the agent", "notifications").
3. **Does the name say what the work is for, not how it works?** Name the result someone sees. The CI job, script, or plumbing that gets you there is the mechanism. Read the PR's motivation, not just its title. For example, a PR titled "run migration lineage check on Buildkite and tag the author in #eng-alerts" exists so that people get pinged when main breaks. The story is "Ping the commit author in #eng-alerts when main fails the migration lineage check", not "Run the migration lineage check on Buildkite".
4. **Is it short?** Aim for 3 to 8 words. Precision comes from specific nouns, not added clauses.

## Grouping PRs into stories

- **Same artifact means same story.** PRs that incrementally build one tool or pipeline belong together. For example, `cutil release`, auto-promote after staging, and the parallel gateway restart with crash-loop detection all belong to "Hermes release utilities".
- **Separate concerns get separate stories, even when they're small.** A single PR that ships an independent behavior is its own story. Don't pile unrelated one-PR changes into a themed bucket just because they share a flavor. For example, ALB client-IP logging, pinging the author when main fails the lineage check, and execution-failure Slack alerts are three stories, not one "observability" story.
- **Leave out work that isn't team-facing.** Skip PRs that only change a personal agent skill, a doc for one person's workflow, or other work that no teammate would track. An example is making a vuln-review skill post to Slack. Mention what you skipped so the user can override.
- **Work done by a recurring scheduled task never becomes a story.** A cron job or scheduled agent that keeps opening the same kind of PR is standing upkeep, not planned work. That covers a recurring type-inlining sweep, a weekly vulnerability review, and a daily report. Skip those PRs no matter how many there are or what they change. A run of same-shape PR titles across different days is the usual sign. Check the user's scheduled tasks, or ask, before assuming. Building or changing the scheduled task itself counts as ordinary work, but only when it's team-facing.
- **Attach to existing stories first.** Search the epic's stories before proposing a new one. If a PR clearly advances an existing story, attach it there, even when the existing name is broader than this guideline would produce. Don't rename other people's stories without asking.

## Placing stories under epics

- Product and domain work goes under the product epic that owns the outcome, such as census and context, intake, carrier submissions, or commitments.
- Developer-facing tooling, CI, release, deploy, alerting, and internal observability go under the dev-efficiency epic when one exists. Agent-facing safety or performance work stays in the agent epic.
- If nothing fits, say so and propose either leaving the work out of Shortcut or creating an epic. Never force a story into a loosely related epic.

## Workflow

1. **Collect the PRs.** Use `gh pr list --author @me --state all --limit <n> --json number,title,state,createdAt,mergedAt` in each relevant repo, or take the PR set the user names.
2. **Load the Shortcut context.** List the epics with `epics-search`, then call `stories-search` with `epic: <id>` for each candidate epic. This shows existing stories and their granularity.
3. **Draft the mapping.** For each epic, list the existing stories that each PR advances and the new stories being proposed, each with its PR numbers. List skipped PRs separately with a one-line reason.
4. **Get confirmation before writing.** Show the draft and wait for approval. Creating or renaming stories is visible to the whole team.
5. **Create or update.** Use `stories-create` with the epic, the team, the user as owner, a story type (`chore` for dev tooling and cleanup, `feature` for product capabilities, `bug` for fixes), and the workflow state implied by the PRs (all merged means Done, any open means In Progress). Link PRs with `stories-add-external-link` unless the user prefers Shortcut's GitHub integration.
6. **Report.** Give each created or updated story's name, ID, and URL.
