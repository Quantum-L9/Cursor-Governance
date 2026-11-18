---
name: l9-plan
description: "explicit-only Program Execution campaign planner and owner of the PLAN_DOCUMENT schema, validator and renderers that l9-plan-simple runs. use when the user explicitly invokes /l9-plan to plan a make campaign (it renders the validated plan as a campaign-source.v2 that make campaign admits unchanged) or a task must change that schema, validator or renderer. ordinary plans are l9-plan-simple."
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, plan, spec, execution, requirements, validation, program-execution, autonomy]
  owner: igor_beylin
  status: active
  version: 4.3.0
  updated: 2026-11-13
---

# l9-plan (explicit-only)

Live, user-invoked only. This pack is the **Program Execution campaign planner** (CANONICAL_LAW `PROGRAM_EXECUTION_PLANNER_V1`) and owns the PLAN_DOCUMENT schema (`schemas/plan-document.schema.json`), validator (`scripts/validate_plan_document.py`), projection renderer (`scripts/render_plan_pe_autonomy.py`) and campaign renderer (`scripts/render_campaign_source.py`). Its campaign deliverable is an `l9.program-execution.campaign-source.v2` that `make campaign` takes on its direct route with nothing synthesized or hand-edited. Ordinary plans are `l9-plan-simple`, which runs this pack's schema, validator and projection renderer but never plans a campaign.

# Execution Planning

## Purpose

Produce a deep, machine-validated **PE+autonomy** plan or specification before implementation. Planning-only — no code edits unless the user explicitly chains to execution (`/autonomy` + `@environment/program-execution`) or `l9-gmp-protocol`.

Ordinary Cursor Plan mode / Build-button plans belong to **`l9-plan-simple`** (same template, no PE wire).

**Doctrine:** a minute of planning saves an hour of debugging. Skipping planning depth to save tokens creates rework and is forbidden. True efficiency is less rework.

## Core Contract

| Mode | Output | Load |
|------|--------|------|
| campaign | `PLAN_DOCUMENT` JSON + **`CAMPAIGN_SOURCE.yaml` (`campaign-source.v2`)** for `make campaign` | this file's **Campaign source** steps + [`environment/program-execution/templates/campaign-source-v2/`](../../environment/program-execution/templates/campaign-source-v2/README.md) |
| plan | `PLAN_DOCUMENT` JSON + Cursor `.plan.md` (PE+autonomy) | [schemas/plan-document.schema.json](schemas/plan-document.schema.json) + **[references/plan-workflow-pe-autonomy.md](references/plan-workflow-pe-autonomy.md)** + **first-class SSOT** [`environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`](../../environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md) (skill `references/executable-plan.pe-autonomy.template.md` → symlink) |
| spec | Full spec with the same validation gates | [references/spec-workflow.md](references/spec-workflow.md) |
| ticket | Engineering ticket structure | [references/engineering-ticket-template.md](references/engineering-ticket-template.md) |

Authoritative machine artifact: **PLAN_DOCUMENT** (JSON). For a campaign, the executable deliverable is the rendered **campaign-source.v2**; the `.plan.md` is the human projection.
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

**Activate** only when the user explicitly invokes `/l9-plan` — to plan a `make campaign`, a Program Lock or PE+autonomy work, or to change this pack's schema, validator or renderers. It is never routed ambiently: Program Execution runs only on the operator's own words (`PROGRAM_EXECUTION_REGISTERED_STAGE_V1`).

**Reject** ordinary Cursor Plan mode / Build-button plans — use `l9-plan-simple`. Reject when the user only wants to execute an already-settled plan, the change is a trivial fully-specified one-liner, or a more specific domain Skill already owns the planning contract.

## Compact Workflow

0. **Memory prefetch** — run `python3 ops/hooks/plan_memory_prefetch.py --workspace "$PWD" --task "<objective>"` and cite `MEMORY_PREFETCH` from `.l9/memory/plan-prefetch.json` (`namespace`, `snapshot_digest`, `checked_record_count`, `conflicts`, `policy_version`). Cursor `beforeSubmitPrompt` fires the same hook when this skill is routed.
1. **Doctrine check** — load [references/planning-doctrine.md](references/planning-doctrine.md). Do not omit mandatory gates for efficiency.
2. **Classify depth** — run `python3 scripts/route_plan.py` (or apply [references/plan-router.yaml](references/plan-router.yaml)). Classifier may only **escalate** obligations; baseline gates always apply.
3. **Pre-Validate** — bind target; inventory baseline; for code in scope on governed workspaces name `.pre-commit-config.yaml` as the hook catalog. KERNEL pack / PE overlay landings: new branch from `origin/main` without asking (`AGENTS.md` `KERNEL_PACK_NEW_BRANCH_DEFAULT_V1`; `rules/46-kernel-pack-new-branch.mdc`).
4. **Gather** — objective, scope in/out, falsifiable success criteria. Ambiguity → STOP and ask. Current-vs-new-branch for KERNEL/pack landings is **not** ambiguity.
5. **Decompose** — TODOs with files (or blocker), deps, leverage ranks, GMP-lockable fields when known. For a campaign, every todo that writes files also carries `validation` (single admissible commands: no pipes, `&&`, redirection, `-c`/`-e`, or mutating git) and an `acceptance` statement; `dependencies` become the campaign's dependency edges and waves.
6. **Stress-test + leverage** — mandatory; see [references/plan-stress-test.md](references/plan-stress-test.md) and [references/first-order-leverage.md](references/first-order-leverage.md).
7. **Doc / Root Surface Impact** — Update TODOs or N/A with reason.
8. **Emit PLAN_DOCUMENT** — write JSON conforming to the schema.
9. **Validate** — `python3 scripts/validate_plan_document.py <plan.json>`. FAIL → not ready.
10. **Project (default)** — `python3 scripts/render_plan_pe_autonomy.py <plan.json> > .cursor/plans/<slug>_<8hex>.plan.md` (or hand-fill [executable-plan.pe-autonomy.template.md](references/executable-plan.pe-autonomy.template.md)). Must retain **Execute via @environment/program-execution + autonomy**.
11. **Kernel receipt** — ready only when `python3 scripts/validate_plan_kernel_receipt.py <bound.plan.md>` PASSes. Hooks enforce this; this step is the pointer.
12. **Campaign source (campaign mode)** — `python3 scripts/render_campaign_source.py <plan.json> [--target OWNER/REPO] [--out PATH]`. It refuses a writing todo without validation, an unknown or cyclic dependency, and an `ask`/`block` unknown; then judges the render with Program Execution's own front door, compiler and launchability (inference off). Only `ADMITTED` is a deliverable. Default output: `.l9/plans/<campaign_id>/CAMPAIGN_SOURCE.yaml`; set `campaign.campaign_id` / `campaign.target_repository` in the plan or pass the flags.
13. **Handoff** — give the operator the printed `next` line: `/coding-agent on`, then `L9_PE_OPERATOR_INVOCATION="<their words>" make -C "$HOME/.cursor-governance" campaign INTENT=<CAMPAIGN_SOURCE.yaml> WS="$PWD"`. Never run `make campaign` yourself and never set the invocation. The campaign finishes with the SSOT `make pr`. Optional `python3 scripts/emit_gmp_phase0.py <plan.json>` when also chaining GMP.

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
- [scripts/render_campaign_source.py](scripts/render_campaign_source.py) — PLAN_DOCUMENT → `campaign-source.v2`, admitted by PE's own checks
- `environment/program-execution/` — authoritative execution pipeline (`make campaign`)
- `commands/autonomy.md` / skill `l9-bounded-autonomy` — subordinate orchestration under Program lease

## Validation

Run before claiming the skill pack or a plan is ready:

```bash
python3 scripts/validate_pack_structure.py .
python3 scripts/validate_exemplary_skill.py .
python3 scripts/route_plan.py --self-test
python3 scripts/validate_plan_document.py fixtures/plan_pass.json
python3 scripts/render_campaign_source.py fixtures/plan_campaign.json --out /tmp/l9-plan-campaign/CAMPAIGN_SOURCE.yaml
python3 scripts/validate_plan_kernel_receipt.py fixtures/plan_kernel_pass.plan.md
python3 scripts/self_test.py
```

A delivered **campaign** plan is incomplete (fail-closed) unless `render_campaign_source.py` prints `ADMITTED`. A delivered plan is incomplete (fail-closed) unless `validate_plan_document.py` PASSes, the PE+autonomy `.plan.md` projection exists with the execute pipeline section, **and** `validate_plan_kernel_receipt.py` PASSes on that `.plan.md`. Heading-complete legacy markdown alone is not ready.

## Failure Handling

- Ambiguous objective → STOP; ask.
- Validator FAIL → fix or set `convergence.status=blocked`; do not claim ready.
- Scope creep → move to `scope.out`.
- Protected-path changes → flag KERNEL GMP in risks/handoff.
- User requests immediate implementation → recommend `@environment/program-execution` + `/autonomy` (or `l9-gmp-protocol` when GMP-locked); do not edit in plan mode.
