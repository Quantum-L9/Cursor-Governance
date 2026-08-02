---
name: l9-plan
description: planning playbook — load permanent fixtures and produce an execution-ready plan or spec before building. use when scope is unclear, requirements need decomposition, or the next step should be planned before code changes.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, plan, playbook, spec, execution, requirements]
owner: igor_beylin
status: active
version: 3.0.0
updated: 2026-08-02
---

# Planning Playbook

## Doctrine

> Proper planning prevents piss poor performance. A minute spent planning is an hour saved debugging.

Plan before build. Prefer clarifying questions and a locked plan over speculative coding.

## Purpose

Orchestrate a **planning playbook**: **Load / Read / apply** permanent in-repo fixtures, then emit a complete plan (or spec) draft. Planning-only — no product/code edits, commit, or push unless the user chains to `l9-gmp-protocol` / `/gmp` or another execution skill.

Do **not** distill or re-host fixture contracts inside this skill. Call them.

## Core Contract

| Mode | Output | Load |
|------|--------|------|
| plan | Playbook plan draft (shells + fixture-backed sections) | [references/plan-workflow.md](references/plan-workflow.md), [references/authority-bindings.md](references/authority-bindings.md) |
| spec | Spec draft with same bindings | [references/spec-workflow.md](references/spec-workflow.md), authority-bindings |
| ticket | Engineering ticket | [references/engineering-ticket-template.md](references/engineering-ticket-template.md) — Kernel Pass Log `N/A — ticket mode` |

## Authority Order

1. Explicit user objective and constraints.
2. Verified repo ground truth.
3. Repo invariants — `AGENTS.md`, `.cursor/rules/*.mdc`.
4. Bound fixtures via [authority-bindings.md](references/authority-bindings.md) (CCP PLAN/DoD, GMP refs, kernels).
5. This skill’s workflow shells.
6. `Unknown` — ask; do not invent.

## Compact Workflow (playbook)

1. **Bind** — resolve authorized target; inspection vs modification intent.
2. **Load fixtures** — Read [authority-bindings.md](references/authority-bindings.md); Read **always** fixtures; Read **CHANGE** fixtures if handoff is tracked implementation; Read **conditional** fixtures when triggers match. Record **Load log**.
3. **Pre-Validate** — lesson corpus; `make pr-check` when code in scope (**no commit, no push**); halt if baseline unsafe.
4. **Gather** — objective, success criteria; ask before build (doctrine).
5. **Draft shells** — fill [plan-workflow.md](references/plan-workflow.md): path scopes, Constraints, Modification Lock (if CHANGE), Acceptance, Assumptions, TODOs (Phase-0 shape if CHANGE), registers, Validation matrix, dual DoD, milestones/checkpoints/checklist.
6. **VALIDATE_PLAN** — required Loads done; shells complete; Quick forbidden for security/migration/shared contracts ([ccp-plan-patterns.md](references/ccp-plan-patterns.md)).
7. **Kernel Pass Pipeline** — [kernel-pass-pipeline.md](references/kernel-pass-pipeline.md); apply five kernels to **draft only**; Kernel Pass Log.
8. **Final Validate** — name post-impl gates; `make pr-check` when code in scope; do not claim merge/release readiness.
9. **Recommend** — MSNA + handoff profile; load `l9-ynp` / `/ynp` (auto-chain).

## Resource Map

- [references/authority-bindings.md](references/authority-bindings.md) — playbook Load map (SSOT for what to Read).
- [references/plan-workflow.md](references/plan-workflow.md) — plan section shells.
- [references/kernel-pass-pipeline.md](references/kernel-pass-pipeline.md) — five-kernel path SSOT + log schema.
- [references/ccp-plan-patterns.md](references/ccp-plan-patterns.md) — adaptive depth only + pointers.
- [references/spec-workflow.md](references/spec-workflow.md) — spec shells.
- [references/engineering-ticket-template.md](references/engineering-ticket-template.md) — ticket mode.

## Validation (fail-closed)

Incomplete if any missing:

- Load log with required Reads for this handoff
- Files in scope / Files out of scope (path tables) — or inspection-only N/A
- Constraints (MUST / MUST NOT)
- Modification Lock when handoff = CHANGE
- Plan Definition of Done + Post-implementation Definition of Done (named)
- Phase-0 TODO columns when handoff = CHANGE
- Pre-Validation, Final Validation, milestones, checkpoints, checklist
- Kernel Pass Log (five Applied/Blocked) for plan/spec
- MSNA + handoff profile
- plan_status not Ready with blocking Unknown
- No placeholder TODOs / “maybe” language without blockers

Never weaken scanners. Never run GMP Phases 2–6 from this skill.

## Failure Handling

- Ambiguous objective → STOP; ask.
- Required fixture unreadable → Blocked; earliest blocker.
- Scope creep → Out of scope / must-not-modify.
- User wants implementation now → recommend `l9-gmp-protocol`; do not edit product files here.
- Kernel pipeline Blocked → partial log; do not claim ready.
