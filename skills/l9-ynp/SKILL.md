---
name: l9-ynp
description: synthesize the single highest-leverage next action from current context. use after completing work, when priorities are unclear, or when the user asks what to do next.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, ynp, next-action, leverage, priority]
owner: igor_beylin
status: active
version: 2.0.0
updated: 2026-06-06
---

# Your Next Play (YNP)

## Purpose

Synthesize the **single highest-leverage next action** from current context. Recommend only — do not auto-execute unless the user explicitly asks to run the recommended command.

## Core Contract

| Input | Output | Scope |
|-------|--------|-------|
| Chat context, workflow state, recent outputs | One primary action + confidence + alternates | Local file ops, slash commands, GMP — not VPS/SSH/production deploy |

Load workflow detail: [references/ynp-workflow.md](references/ynp-workflow.md).

## Authority Order

1. Explicit user priority or "what next" request.
2. Highest-severity open blocker in context (CI, merge blockers, failed gates).
3. Locked TODO plan or workflow_state when present.
4. This skill's references.
5. `Unknown` — ask clarifying question when confidence <70%.

## Compact Workflow

1. **Harvest** — chat context, workflow_state, recent GMP outputs, reusable assets.
2. **Synthesize** — abductive/deductive/inductive reasoning on candidates.
3. **Score** — confidence ≥90% strong | 80–89% recommend | 70–79% caveats | <70% ask.
4. **Deliver** — one primary play, scope, alternates if blocked.

## Resource Map

- [references/ynp-workflow.md](references/ynp-workflow.md) — execution steps, tier routing, output format, stop conditions.

## Validation

Exactly one primary recommendation. Confidence MUST be stated. Batch related TODOs (3 in one GMP > 3 separate runs).

## Failure Handling

- Ambiguous context → ask clarifying question.
- Multiple equal-priority items → present ranked options with trade-offs.
- Protected file without approval → route to KERNEL GMP.
- Confidence <70% → gather more info; do not guess.
