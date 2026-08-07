---
name: l9-plan
description: create a machine-validated execution plan or implementation specification before building. use when scope is unclear, requirements need decomposition, or the next step should be planned before code changes. do not use when the user only wants to execute an already-settled plan or a trivial fully-specified one-line fix.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, plan, spec, execution, requirements, validation]
owner: igor_beylin
status: active
version: 3.0.0
updated: 2026-08-07
---

# Execution Planning

## Purpose

Produce a deep, machine-validated plan or specification before implementation. Planning-only — no code edits unless the user explicitly chains to `l9-gmp-protocol` or another execution skill.

**Doctrine:** a minute of planning saves an hour of debugging. Skipping planning depth to save tokens creates rework and is forbidden. True efficiency is less rework.

## Core Contract

| Mode | Output | Load |
|------|--------|------|
| plan | `PLAN_DOCUMENT` JSON + markdown projection | [schemas/plan-document.schema.json](schemas/plan-document.schema.json) + [references/plan-workflow.md](references/plan-workflow.md) |
| spec | Full spec with the same validation gates | [references/spec-workflow.md](references/spec-workflow.md) |
| ticket | Engineering ticket structure | [references/engineering-ticket-template.md](references/engineering-ticket-template.md) |

Authoritative artifact: **PLAN_DOCUMENT** (JSON/YAML). Markdown is a human projection only.

## Authority Order

1. Explicit user objective and constraints.
2. Verified repo ground truth — existing modules, patterns, ADRs.
3. Repo invariants — `AGENTS.md`, `.cursor/rules/*.mdc`.
4. GMP Phase 0 lock shape when execution will follow.
5. This skill's schema, validators, and references.
6. `Unknown` — ask before filling gaps.

## Activation / Reject

**Activate** when scope is unclear, a plan/spec/ticket is requested, or work should be planned before code changes.

**Reject** when the user only wants to execute an already-settled plan, the change is a trivial fully-specified one-liner, or a more specific domain Skill already owns the planning contract.

## Compact Workflow

1. **Doctrine check** — load [references/planning-doctrine.md](references/planning-doctrine.md). Do not omit mandatory gates for efficiency.
2. **Classify depth** — run `python3 scripts/route_plan.py` (or apply [references/plan-router.yaml](references/plan-router.yaml)). Classifier may only **escalate** obligations; baseline gates always apply.
3. **Pre-Validate** — bind target; inventory baseline; for code in scope on governed workspaces name `make pr-check` (**no commit, no push**).
4. **Gather** — objective, scope in/out, falsifiable success criteria. Ambiguity → STOP and ask.
5. **Decompose** — TODOs with files (or blocker), deps, leverage ranks, GMP-lockable fields when known.
6. **Stress-test + leverage** — mandatory; see [references/plan-stress-test.md](references/plan-stress-test.md) and [references/first-order-leverage.md](references/first-order-leverage.md).
7. **Doc / Root Surface Impact** — Update TODOs or N/A with reason.
8. **Emit PLAN_DOCUMENT** — write JSON conforming to the schema.
9. **Validate** — `python3 scripts/validate_plan_document.py <plan.json>`. FAIL → not ready.
10. **Project** — optional markdown via `python3 scripts/render_plan_markdown.py <plan.json>`.
11. **Handoff** — `python3 scripts/emit_gmp_phase0.py <plan.json>` when chaining to GMP; recommend `l9-ynp` for next skill.

## Depth Classifier (escalate-only)

| Depth | When | Extra obligations |
|-------|------|-------------------|
| standard | default | all baseline gates |
| deep | guarded/irreversible risk, conflicting evidence, multi-milestone | richer stress-test, explicit rollback, denser unknowns |
| rapid | **does not omit gates** | same baseline; only reduces narrative verbosity in the markdown projection |

## Resource Map

- [schemas/plan-document.schema.json](schemas/plan-document.schema.json) — authoritative plan object
- [references/planning-doctrine.md](references/planning-doctrine.md) — anti-rework law
- [references/plan-quality-gates.md](references/plan-quality-gates.md) — gate IDs mirrored in validator
- [references/plan-router.yaml](references/plan-router.yaml) — escalate-only depth routing
- [references/plan-workflow.md](references/plan-workflow.md) — markdown projection template
- [references/spec-workflow.md](references/spec-workflow.md) — specification mode
- [references/engineering-ticket-template.md](references/engineering-ticket-template.md) — ticket mode
- [references/plan-stress-test.md](references/plan-stress-test.md)
- [references/first-order-leverage.md](references/first-order-leverage.md)
- [references/convergence-block.md](references/convergence-block.md)
- [references/gmp-phase0-handoff.md](references/gmp-phase0-handoff.md)
- [references/validation-checklist.md](references/validation-checklist.md)

## Validation

Run before claiming the skill pack or a plan is ready:

```bash
python3 scripts/validate_pack_structure.py .
python3 scripts/validate_exemplary_skill.py .
python3 scripts/route_plan.py --self-test
python3 scripts/validate_plan_document.py fixtures/plan_pass.json
python3 scripts/self_test.py
```

A delivered plan is incomplete (fail-closed) unless `validate_plan_document.py` PASSes. Heading-complete markdown without a validated PLAN_DOCUMENT is not ready.

## Failure Handling

- Ambiguous objective → STOP; ask.
- Validator FAIL → fix or set `convergence.status=blocked`; do not claim ready.
- Scope creep → move to `scope.out`.
- Protected-path changes → flag KERNEL GMP in risks/handoff.
- User requests immediate implementation → recommend `l9-gmp-protocol`; do not edit in plan mode.
