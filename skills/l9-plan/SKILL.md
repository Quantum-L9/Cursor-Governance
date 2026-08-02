---
name: l9-plan
description: create an execution plan or implementation specification before building. use when scope is unclear, requirements need decomposition, or the next step should be planned before code changes.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, plan, spec, execution, requirements]
owner: igor_beylin
status: active
version: 2.2.0
updated: 2026-08-02
---

# Execution Planning

## Doctrine

> Proper planning prevents piss poor performance. A minute spent planning is an hour saved debugging.

Plan before build. Prefer clarifying questions and a locked plan over speculative coding — minutes of planning routinely save hours of debugging and rework. (Also encoded as lesson `lesson-005-ask-first` and `rules/92-learned-lessons.mdc`.)

## Purpose

Produce a structured plan or full specification before implementation. Planning-only — no code edits unless the user explicitly chains to `l9-gmp-protocol` or another execution skill.

## Core Contract

| Mode | Output | Load |
|------|--------|------|
| plan | Deep TODO plan with CCP fields, pre/final validation, kernel pass log, milestones, checkpoints, checklist | [references/plan-workflow.md](references/plan-workflow.md) |
| spec | Full spec document for forge/gmp (validation gates + kernel pass log) | [references/spec-workflow.md](references/spec-workflow.md) |
| ticket | Engineering ticket structure | [references/engineering-ticket-template.md](references/engineering-ticket-template.md) |

## Authority Order

1. Explicit user objective and constraints.
2. Verified repo ground truth — existing modules, patterns, ADRs.
3. Repo invariants — `AGENTS.md`, `.cursor/rules/*.mdc`.
4. This skill's references ([plan-workflow](references/plan-workflow.md), [ccp-plan-patterns](references/ccp-plan-patterns.md), [kernel-pass-pipeline](references/kernel-pass-pipeline.md)).
5. `Unknown` — ask before filling gaps in the spec.

## Compact Workflow

1. **Pre-Validate** — bind target; inventory baseline; lesson corpus recall when `learning/failures/repeated-mistakes.md` is accessible (`None matched` or list matches); for Cursor-Governance / governed workspaces with code in scope: `make pr-check` (changed-files scanners; **no commit, no push**). Record PASS/FAIL/SKIPPED with reason.
2. **Gather** — objective, scope in/out (inspection vs modification), falsifiable success; ask before build (doctrine).
3. **Decompose** — TODO table with files (or `TBD` + blocker), effort, risk; Depth (preserved/prohibited contracts; evidence classes); conditional key-component sections when triggers match (see plan-workflow).
4. **Dependencies** — task graph; execution waves only when write/contract-independent.
5. **Milestones** — outcome batches that unlock the next phase.
6. **Checkpoints** — go/no-go evidence gates between milestones.
7. **Checklist** — atomic done/not-done items tied to TODOs.
8. **Deliver** — plan markdown or `specs/{project}-spec.md` per mode using the required template (Planning Mode, plan_status, registers, Validation matrix included).
9. **VALIDATE_PLAN** — template completeness vs plan-workflow; CCP gates ([ccp-plan-patterns.md](references/ccp-plan-patterns.md)); conditional key-component gates; escalate Quick mode if security/migration/shared contracts.
10. **Kernel Pass Pipeline (mandatory for plan/spec)** — load [kernel-pass-pipeline.md](references/kernel-pass-pipeline.md); Read and apply five kernels to the **draft only**; attach Kernel Pass Log; halt readiness on Blocked. Ticket mode: `N/A — ticket mode`.
11. **Final Validate** — post-implementation gates named; `make pr-check` when code in scope (**no commit, no push** unless user asks); drift-watch paths when config/schema/policy in scope; do not infer merge/release readiness from implementation-ready.
12. **Recommend** — exactly one Minimum Safe Next Action + handoff profile; load `l9-ynp` for gmp vs forge vs continue.

## Resource Map

- [references/plan-workflow.md](references/plan-workflow.md) — execution plan output template (SSOT).
- [references/kernel-pass-pipeline.md](references/kernel-pass-pipeline.md) — sole kernel path SSOT, order, Kernel Pass Log schema.
- [references/ccp-plan-patterns.md](references/ccp-plan-patterns.md) — distilled CCP PLAN patterns (adaptive depth, registers, anti-patterns).
- [references/spec-workflow.md](references/spec-workflow.md) — full specification generator.
- [references/engineering-ticket-template.md](references/engineering-ticket-template.md) — acceptance criteria, GWT scenarios.

## Validation

A plan is incomplete (fail-closed — do not present as ready) if any of the following are missing:

- **Pre-Validation** section (commands + pass criteria, or explicit Skipped/N/A with reason) including lesson corpus row when accessible
- **Final Validation** section (commands + pass criteria; `make pr-check` when code in scope)
- **Planning Mode**, **plan_status**, **Unknown register**, **Decision register**, **Validation matrix**
- **Milestones**, **Checkpoints**, and **Checklist**
- **Kernel Pass Log** — five `Applied`/`Blocked` rows for plan/spec (see kernel-pass-pipeline); ticket: `N/A — ticket mode`
- **Minimum Safe Next Action** and **handoff profile**
- Conditional key-component sections when triggers match (or explicit `N/A — trigger not met`)
- Every TODO names files or `TBD` with a blocker note
- Scope out is explicit (inspection vs modification)
- No placeholder "TODO: fill in" without a question to the user
- `plan_status` is not Ready while a blocking Unknown remains
- Quick mode is not used for security-sensitive, migration, or shared-contract work

Code written under a plan that implied implementation MUST be clean: run `make pr-check` (alias `make pr`) locally; do not open/push a PR on a failing gate. Never weaken scanners to obtain PASS.

## Failure Handling

- Ambiguous objective → STOP at gather; ask clarifying questions.
- Scope creep detected → move items to Out of scope.
- Protected-path changes planned → flag KERNEL GMP requirement.
- Pre-Validation FAIL on unrelated dirty tree → quarantine unrelated changes or document baseline FAIL; do not claim whole-tree cleanliness.
- User requests immediate implementation → recommend `l9-gmp-protocol`; do not edit files in plan mode.
- Kernel pipeline Blocked → emit partial Kernel Pass Log; do not claim ready.
- Required conditional section omitted when trigger matches → incomplete plan.
