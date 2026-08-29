---
name: l9-ynp
description: synthesize the single highest-leverage next action from current context. use after completing work, when priorities are unclear, or when the user asks what to do next.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, ynp, next-action, leverage, priority]
  owner: igor_beylin
  status: active
  version: 2.1.0
  updated: 2026-08-28
---

# Your Next Play (YNP)

## Purpose

Synthesize the **single highest-leverage next action** from current context. Recommend only — do not auto-execute unless the user explicitly asks to run the recommended command.

## Core Contract

| Input | Output | Scope |
|-------|--------|-------|
| Chat context, workflow state, recent outputs | One primary play + `action` enum + alternates | Local file ops, slash commands, GMP — not VPS/SSH/production deploy |

Load workflow detail: [references/ynp-workflow.md](references/ynp-workflow.md).

## Authority Order

1. Explicit user priority or "what next" request.
2. Highest-severity open blocker in context (CI, merge blockers, failed gates).
3. Locked TODO plan or workflow_state when present.
4. This skill's references.
5. `Unknown` — ask a clarifying question when `action` is `block` or `bounded_probe` and the missing evidence is unnamed.

## Compact Workflow

1. **Harvest** — chat context, workflow_state, recent GMP outputs, reusable assets.
2. **Synthesize** — abductive/deductive/inductive reasoning on candidates.
3. **Score** — emit `evidence_quality`, `decision_risk`, and `action`. A bare percent is `uncalibrated` and must not select the play.
4. **Deliver** — one primary play, scope, alternates if blocked.

```yaml
evidence_quality: high | medium | low | unknown
decision_risk: reversible | guarded | irreversible
action: proceed | proceed_with_validation | bounded_probe | block
calibration_status: none | uncalibrated | calibrated
```

Display alias only (do not compute these percents): `proceed` ≈ old ≥90 slot, `proceed_with_validation` ≈ 80–89, `bounded_probe` ≈ 70–79, `block` ≈ below 70.

## Resource Map

- [references/ynp-workflow.md](references/ynp-workflow.md) — execution steps, tier routing, output format, stop conditions.

## Validation

Exactly one primary recommendation. action: MUST be stated. A bare percent is labeled uncalibrated and must not choose the play. Batch related TODOs (3 in one GMP > 3 separate runs).

## Failure Handling

- Ambiguous context → ask clarifying question.
- Multiple equal-priority items → present ranked options with trade-offs.
- Protected file without approval → route to KERNEL GMP.
- `action: block` or unnamed missing evidence → gather more info; do not guess.
