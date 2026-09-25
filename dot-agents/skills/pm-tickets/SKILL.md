---
name: pm-tickets
description: Write, scope, and file product-management tickets in any tracker (Shortcut, Linear, Jira, GitHub Issues). Use when the user asks to turn PRs or recent work into tickets, backfill a tracker, break planned work into tickets, name or rename tickets, decide which epic or project a piece of work belongs to, or create or update tickets through a tracker's MCP connector or CLI.
---

# PM Tickets

## Overview

A ticket names one concrete deliverable that a teammate could point at and say "that shipped." A ticket can span several PRs, but only when those PRs all build the same thing. The ticket name should say exactly what that thing is.

Trackers use different words for the same levels. This skill says **ticket** for the unit of work (a Shortcut story, a Linear issue, a Jira story or task) and **epic** for the grouping above it (a Shortcut epic, a Linear project, a Jira epic).

## Naming tickets

Name the artifact or capability being built, not the category of work.

- Good: "Agent release utilities", "Post execution failures to #eng-alerts", "Log client IPs behind the AWS ALB", "Ping the commit author when main fails the migration lineage check".
- Too general: "Agent deploy reliability", "Failure alerting and observability", "Codebase health", "Infra improvements".

Checks before accepting a name:

1. **Could someone tell from the name alone whether a given PR belongs?** If the name is a quality attribute (reliability, observability, efficiency, cleanup), it is an epic or theme, not a ticket. Narrow it to the specific tool, pipeline, table, flow, or behavior.
2. **Does the name use the system's own nouns?** Prefer the real names of services, commands, agents, channels, and entities (`cutil`, Iris, `#eng-alerts`, census) over generic ones ("tooling", "the service", "notifications").
3. **Does the name say what the work is for, not how it works?** Name the result someone sees. The CI job, script, or plumbing that gets you there is the mechanism. Read the PR's motivation, not just its title. For example, a PR titled "run migration lineage check on Buildkite and tag the author in #eng-alerts" exists so that people get pinged when main breaks. The ticket is "Ping the commit author in #eng-alerts when main fails the migration lineage check", not "Run the migration lineage check on Buildkite".
4. **Is it short?** Aim for 3 to 8 words. Precision comes from specific nouns, not added clauses.

## Scoping tickets

These rules apply whether you're grouping finished PRs or splitting planned work.

- **Same artifact means same ticket.** PRs that incrementally build one tool or pipeline belong together. For example, `cutil release`, auto-promote after staging, and the parallel gateway restart with crash-loop detection all belong to "Agent release utilities".
- **Separate concerns get separate tickets, even when they're small.** A single PR that ships an independent behavior is its own ticket. Don't pile unrelated one-PR changes into a themed bucket just because they share a flavor. For example, ALB client-IP logging, pinging the author when main fails the lineage check, and execution-failure Slack alerts are three tickets, not one "observability" ticket.
- **Leave out work that isn't team-facing.** Skip work that only changes a personal agent skill, a doc for one person's workflow, or anything else no teammate would track. Mention what you skipped so the user can override.
- **Work done by a recurring scheduled task never becomes a ticket.** A cron job or scheduled agent that keeps opening the same kind of PR is standing upkeep, not planned work. That covers a recurring type-inlining sweep, a weekly vulnerability review, and a daily report. Skip those PRs no matter how many there are or what they change. A run of same-shape PR titles across different days is the usual sign. Check the user's scheduled tasks, or ask, before assuming. Building or changing the scheduled task itself counts as ordinary work, but only when it's team-facing.
- **Attach to existing tickets first.** Search the epic's tickets before proposing a new one. If a PR clearly advances an existing ticket, attach it there, even when the existing name is broader than this guideline would produce. Don't rename other people's tickets without asking.

## Placing tickets under epics

- Product and domain work goes under the product epic that owns the outcome.
- Developer-facing tooling, CI, release, deploy, alerting, and internal observability go under a dev-efficiency epic when one exists. Agent-facing safety or performance work stays in the agent epic.
- If nothing fits, say so and propose either leaving the work out of the tracker or creating an epic. Never force a ticket into a loosely related epic.

## Workflow

1. **Collect the work.** For a backfill, list PRs with `gh pr list --author @me --state all --limit <n> --json number,title,state,createdAt,mergedAt` in each relevant repo, or take the PR set the user names. For planned work, take the user's description and ask about anything that changes scope.
2. **Load the tracker context.** List the epics, then list the tickets in each candidate epic. This shows existing tickets and how big the team usually makes them. Match the team's conventions for ticket types, priority fields, and workflow states.
3. **Draft the mapping.** For each epic, list the existing tickets the work advances and the new tickets being proposed, each with its PR numbers or scope. List skipped work separately with a one-line reason.
4. **Get confirmation before writing.** Show the draft and wait for approval. Creating or renaming tickets is visible to the whole team.
5. **Create or update.** Set the epic, the team, the user as owner, a type if the tracker has types (chore for dev tooling, feature for product capabilities, bug for fixes), and the state implied by the PRs (all merged means done, any open means in progress). Link the PRs unless the tracker's GitHub integration already links them.
6. **Report.** Give each created or updated ticket's name, ID, and URL.

## Tracker notes

- **Shortcut (MCP):** Use `epics-search` to list epics, `stories-search` with `epic: <id>` to list tickets, `stories-create` to create, and `stories-add-external-link` to link PRs. The GitHub integration links a PR when its branch name contains `sc-<id>`.
- **Linear (MCP):** Epics are projects. Use `list_projects`, `list_issues` filtered by project, `save_issue`, and `create_attachment` for PR links.
- **Other trackers:** Map the same two levels onto whatever the tracker offers. Say so if it has no epic-level grouping.
