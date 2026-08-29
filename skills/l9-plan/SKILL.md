---
name: l9-plan
description: create a machine-validated pe+autonomy execution plan or specification that runs through program-execution and make campaign. use when the user asks for /l9-plan, make campaign, program lock, campaign plan, or pe+autonomy. do not use for ordinary cursor plan mode or build-button plans (use l9-plan-simple).
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, plan, spec, execution, requirements, validation, program-execution, autonomy]
  owner: igor_beylin
  status: active
  version: 4.1.0
  updated: 2026-08-21
---

# Execution Planning

## Purpose

Produce a deep, machine-validated **PE+autonomy** plan or specification before implementation. Planning-only — no code edits unless the user explicitly chains to execution (`/autonomy` + `@environment/program-execution`) or `l9-gmp-protocol`.

Ordinary Cursor Plan mode / Build-button plans belong to **`l9-plan-simple`** (same template, no PE wire).

**Doctrine:** a minute of planning saves an hour of debugging. Skipping planning depth to save tokens creates rework and is forbidden. True efficiency is less rework.

## Core Contract

| Mode | Output | Load |
|------|--------|------|
| plan | `PLAN_DOCUMENT` JSON + Cursor `.plan.md` (PE+autonomy) | [schemas/plan-document.schema.json](schemas/plan-document.schema.json) + **[references/plan-workflow-pe-autonomy.md](references/plan-workflow-pe-autonomy.md)** + **first-class SSOT** [`environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`](../../environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md) (skill `references/executable-plan.pe-autonomy.template.md` → symlink) |
| spec | Full spec with the same validation gates | [references/spec-workflow.md](references/spec-workflow.md) |
| ticket | Engineering ticket structure | [references/engineering-ticket-template.md](references/engineering-ticket-template.md) |

Authoritative machine artifact: **PLAN_DOCUMENT** (JSON).
Default human/executable projection: **Cursor `.plan.md`** from the PE+autonomy template (not the legacy GMP-only markdown).

Legacy projection kept in place: [references/plan-workflow.md](references/plan-workflow.md) + `scripts/render_plan_markdown.py` — do not delete; not the default deliverable.

## Authority Order

1. Explicit user objective and constraints.
2. Verified repo ground truth — existing modules, patterns, ADRs.
3. Repo invariants — `AGENTS.md`, `.cursor/rules/*.mdc`, `environment/agents/PEER_EXECUTION.md`.
4. Executable plan template + PE/autonomy execute path (plan mode default).
5. GMP Phase 0 lock shape when GMP execution will follow.
6. This skill's schema, validators, and references.
7. `Unknown` — ask before filling gaps.

## Activation / Reject

**Activate** when the user asks for `/l9-plan`, `make campaign`, Program Lock, a campaign plan, or PE+autonomy execution.

**Reject** ordinary Cursor Plan mode / Build-button plans — use `l9-plan-simple`. Reject when the user only wants to execute an already-settled plan, the change is a trivial fully-specified one-liner, or a more specific domain Skill already owns the planning contract.

## Compact Workflow

1. **Doctrine check** — load [references/planning-doctrine.md](references/planning-doctrine.md). Do not omit mandatory gates for efficiency.
2. **Classify depth** — run `python3 scripts/route_plan.py` (or apply [references/plan-router.yaml](references/plan-router.yaml)). Classifier may only **escalate** obligations; baseline gates always apply.
3. **Pre-Validate** — bind target; inventory baseline; for code in scope on governed workspaces name `.pre-commit-config.yaml` as the hook catalog. KERNEL pack / PE overlay landings: new branch from `origin/main` without asking (`AGENTS.md` `KERNEL_PACK_NEW_BRANCH_DEFAULT_V1`; `rules/46-kernel-pack-new-branch.mdc`).
4. **Gather** — objective, scope in/out, falsifiable success criteria. Ambiguity → STOP and ask. Current-vs-new-branch for KERNEL/pack landings is **not** ambiguity.
5. **Decompose** — TODOs with files (or blocker), deps, leverage ranks, GMP-lockable fields when known; map todos to PE Task Card / wave ids.
6. **Stress-test + leverage** — mandatory; see [references/plan-stress-test.md](references/plan-stress-test.md) and [references/first-order-leverage.md](references/first-order-leverage.md).
7. **Doc / Root Surface Impact** — Update TODOs or N/A with reason.
8. **Emit PLAN_DOCUMENT** — write JSON conforming to the schema.
9. **Validate** — `python3 scripts/validate_plan_document.py <plan.json>`. FAIL → not ready.
10. **Project (default)** — `python3 scripts/render_plan_pe_autonomy.py <plan.json> > .cursor/plans/<slug>_<8hex>.plan.md` (or hand-fill [executable-plan.pe-autonomy.template.md](references/executable-plan.pe-autonomy.template.md)). Must retain **Execute via @environment/program-execution + autonomy**.
11. **Kernel receipt** — ready only when `python3 scripts/validate_plan_kernel_receipt.py <bound.plan.md>` PASSes. Hooks enforce this; this step is the pointer.
12. **Handoff** — execution path is `@environment/program-execution` → Program Lock/Controller → `@autonomy` (`/autonomy` → `l9-bounded-autonomy`) under Program lease. Optional `python3 scripts/emit_gmp_phase0.py <plan.json>` when also chaining GMP. Recommend `l9-ynp` for next skill.

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
- **[references/plan-workflow-pe-autonomy.md](references/plan-workflow-pe-autonomy.md)** — **default** plan-mode projection + execute pipeline
- **[`environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`](../../environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md)** — **first-class** Cursor `.plan.md` fill-in SSOT (`MANIFEST.yaml`)
- [references/executable-plan.pe-autonomy.template.md](references/executable-plan.pe-autonomy.template.md) — symlink projection of the SSOT (do not fork)
- [scripts/validate_plan_kernel_receipt.py](scripts/validate_plan_kernel_receipt.py) — hashed Improve then V&R receipt on the bound `.plan.md`
- [scripts/sync_cursor_plan_template.py](scripts/sync_cursor_plan_template.py) — write/check local `.cursor/plans/_TEMPLATE.plan.md` mirror (gitignored)
- [references/plan-workflow.md](references/plan-workflow.md) — **legacy** GMP-section markdown projection (kept)
- [references/spec-workflow.md](references/spec-workflow.md) — specification mode
- [references/engineering-ticket-template.md](references/engineering-ticket-template.md) — ticket mode
- [references/plan-stress-test.md](references/plan-stress-test.md)
- [references/first-order-leverage.md](references/first-order-leverage.md)
- [references/convergence-block.md](references/convergence-block.md)
- [references/gmp-phase0-handoff.md](references/gmp-phase0-handoff.md)
- [references/validation-checklist.md](references/validation-checklist.md)
- `environment/program-execution/` — authoritative execution pipeline
- `commands/autonomy.md` / skill `l9-bounded-autonomy` — subordinate orchestration under Program lease

## Validation

Run before claiming the skill pack or a plan is ready:

```bash
python3 scripts/validate_pack_structure.py .
python3 scripts/validate_exemplary_skill.py .
python3 scripts/route_plan.py --self-test
python3 scripts/validate_plan_document.py fixtures/plan_pass.json
python3 scripts/validate_plan_kernel_receipt.py fixtures/plan_kernel_pass.plan.md
python3 scripts/self_test.py
```

A delivered plan is incomplete (fail-closed) unless `validate_plan_document.py` PASSes, the PE+autonomy `.plan.md` projection exists with the execute pipeline section, **and** `validate_plan_kernel_receipt.py` PASSes on that `.plan.md`. Heading-complete legacy markdown alone is not ready.

## Failure Handling

- Ambiguous objective → STOP; ask.
- Validator FAIL → fix or set `convergence.status=blocked`; do not claim ready.
- Scope creep → move to `scope.out`.
- Protected-path changes → flag KERNEL GMP in risks/handoff.
- User requests immediate implementation → recommend `@environment/program-execution` + `/autonomy` (or `l9-gmp-protocol` when GMP-locked); do not edit in plan mode.
