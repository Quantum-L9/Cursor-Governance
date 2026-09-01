---
name: l9-plan-simple
description: create a machine-validated cursor .plan.md from the shared executable-plan
  template and execute it with the build button, then open a stacked PR. never branch
  off main when an open PR exists. always publish via the stacked path after build and display the PR URL.
  use when scope is unclear, requirements need decomposition, cursor plan mode is on,
  or the next step should be planned before code changes. do not use when the user
  asks for program-execution, make campaign, /l9-plan, or a pe campaign lock.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags:
  - l9
  - plan
  - spec
  - cursor-build
  - execution
  - requirements
  - validation
  owner: igor_beylin
  status: active
  version: 1.2.0
  updated: 2026-08-30
disable-model-invocation: true
---

# Execution Planning (Cursor Build)

## Purpose

Produce a deep, machine-validated plan from the **same** first-class executable-plan template as `l9-plan`, then execute it with the **Build** button, then **always** publish with `PR_STACK=auto PR_REMEDIATE=0 l9 pr`.

This skill does **not** wire the delivered plan to Program Execution. Do not run `make campaign`. Do not admit a Program Lock. Do not write `Lock: origin/main = <sha>`. Do not require a new worktree from tip as a **planning** requirement.

If any open PR exists, Build **never** branches from `origin/main`. Execute on the unique open-PR chain tip. After todos complete, open the stacked PR and **display the PR URL** as proof.

**Doctrine:** a minute of planning saves an hour of debugging. The template sections stay; only the execute path changes.

## Core Contract

| Mode | Output | Load |
|------|--------|------|
| plan | `PLAN_DOCUMENT` JSON + Cursor `.plan.md` (shared template, Build execute) | [`../l9-plan/schemas/plan-document.schema.json`](../l9-plan/schemas/plan-document.schema.json) + **[references/plan-workflow-simple.md](references/plan-workflow-simple.md)** + first-class SSOT [`environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`](../../environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md) (skill `references/executable-plan.template.md` → symlink) |

Authoritative machine artifact: **PLAN_DOCUMENT** (JSON), validated by `l9-plan`'s `validate_plan_document.py` (reuse, do not copy).

Upstream planner: **`l9-global-architect`**. This skill does not invent architecture. Load the GAR bootloader and run it before emitting PLAN_DOCUMENT. Standalone `/l9-global-architect` stays explicit-only; this supporting invoke is the plan-simple contract.

Default human/executable projection: the shared canonical `.plan.md` with the PE execute block **replaced** by **Execute via Cursor Build**.

Section proof: generate then validate a **section receipt** against `../l9-plan/schemas/plan-document.schema.json` required keys plus the required `.plan.md` headings (template items 1–16 + **Execute via Cursor Build**).

## Authority Order

1. Explicit user objective and constraints.
2. Verified repo ground truth — existing modules, patterns, ADRs.
3. Repo invariants — `AGENTS.md`, `.cursor/rules/*.mdc`.
4. `l9-global-architect` runtime (architecture selection before emit).
5. Shared executable plan template + Cursor Build execute path.
6. This skill's workflow, `l9-plan` schema/validator, and section receipt.
7. `Unknown` — ask before filling gaps.

## Activation / Reject

**Activate** when scope is unclear, Cursor Plan mode is on, the user wants a Build-button plan, or work should be planned before code changes.

**Reject** when the user names campaign / program-execution / `make campaign` / `/l9-plan` / Program Lock — hand off to `l9-plan`. Reject a trivial fully-specified one-liner. Reject KERNEL pack / PE overlay landings — those stay `l9-plan` + `rules/46-kernel-pack-new-branch.mdc`.

## Compact Workflow

1. **Architect (upstream, required)** — Read [`../l9-global-architect/SKILL.md`](../l9-global-architect/SKILL.md) and follow its bootloader: load `runtime/MANIFEST.yaml` in `load_order`, instantiate run state, derive the objective, select architecture. Do not emit PLAN_DOCUMENT until GAR has selected architecture or recorded that architecture is already settled.
2. **Doctrine / depth** — load `l9-plan` [planning-doctrine.md](../l9-plan/references/planning-doctrine.md) and classify via `python3 ../l9-plan/scripts/route_plan.py` (escalate-only). Do not omit baseline gates.
3. **Pre-Validate** — bind the **current workspace** (branch, dirty, HEAD if useful). For code in scope on governed workspaces name `.pre-commit-config.yaml` as the hook catalog. Do **not** lock `origin/main` or open a tip worktree.
4. **Gather** — objective, scope in/out, falsifiable success. Ambiguity → STOP and ask.
5. **Decompose** — TODOs with files (or blocker) and deps. DAG rows are Build todos, not Controller `claim`/`render` Task Cards.
6. **Stress-test + leverage** — mandatory; reuse `l9-plan` [plan-stress-test.md](../l9-plan/references/plan-stress-test.md) and [first-order-leverage.md](../l9-plan/references/first-order-leverage.md).
7. **Doc / Root Surface Impact** — update TODOs or N/A with reason.
8. **Emit PLAN_DOCUMENT** — JSON conforming to the shared schema.
9. **Validate JSON** — `python3 ../l9-plan/scripts/validate_plan_document.py <plan.json>`. FAIL → not ready.
10. **Project** — `python3 ../l9-plan/scripts/render_plan_pe_autonomy.py <plan.json> --execute-via=cursor-build > .cursor/plans/<slug>_<8hex>.plan.md` (or hand-fill [executable-plan.template.md](references/executable-plan.template.md) and swap the execute block per [plan-workflow-simple.md](references/plan-workflow-simple.md)). Frontmatter must include `kind: simple` and `execute_via: cursor-build`.
11. **Section receipt** — generate then validate. FAIL → not ready:

```bash
python3 scripts/generate_plan_section_receipt.py \
  --plan-json <plan.json> --plan-md <plan.md> --out <plan>.section-receipt.json \
  --gar-invoked
python3 scripts/validate_plan_section_receipt.py <plan>.section-receipt.json
```

12. **Handoff** — user presses **Build**. If any open PR exists, execute on the unique chain tip (`PR_STACK=auto`); never branch from `origin/main`. After todos: scoped-commit, `l4_local.py authorize-release`, then `PR_STACK=auto PR_REMEDIATE=0 make pr`. Do not skip `make pr`. Display the opened **PR URL**. Recommend `l9-ynp` only if the next skill is unclear.

## Resource Map

- Skill `l9-global-architect` — required upstream planner (bootloader + `runtime/MANIFEST.yaml`)
- [references/plan-workflow-simple.md](references/plan-workflow-simple.md) — fill shared template; swap execute only
- [references/executable-plan.template.md](references/executable-plan.template.md) — symlink to the first-class SSOT (do not fork)
- [references/validation-checklist.md](references/validation-checklist.md)
- [`../l9-plan/schemas/plan-document.schema.json`](../l9-plan/schemas/plan-document.schema.json) — required JSON sections
- [`schemas/plan-section-receipt.schema.json`](schemas/plan-section-receipt.schema.json) — receipt shape
- [`scripts/generate_plan_section_receipt.py`](scripts/generate_plan_section_receipt.py)
- [`scripts/validate_plan_section_receipt.py`](scripts/validate_plan_section_receipt.py)
- [`../l9-plan/scripts/validate_plan_document.py`](../l9-plan/scripts/validate_plan_document.py)
- [`../l9-plan/scripts/render_plan_pe_autonomy.py`](../l9-plan/scripts/render_plan_pe_autonomy.py) — `--execute-via=cursor-build`
- [`../l9-plan/scripts/route_plan.py`](../l9-plan/scripts/route_plan.py)
- Skill `l9-plan` — PE/campaign planner only

## Validation

```bash
python3 ../l9-plan/scripts/validate_plan_document.py ../l9-plan/fixtures/plan_pass.json
python3 ../l9-plan/scripts/render_plan_pe_autonomy.py ../l9-plan/fixtures/plan_pass.json --execute-via=cursor-build | grep -q "Execute via Cursor Build"
python3 ../l9-plan/scripts/render_plan_pe_autonomy.py ../l9-plan/fixtures/plan_pass.json --execute-via=cursor-build | grep -q "PR_STACK=auto"
python3 scripts/generate_plan_section_receipt.py --help >/dev/null
python3 scripts/validate_plan_section_receipt.py --help >/dev/null
python3 scripts/self_test.py
```

A delivered plan is incomplete unless `validate_plan_document.py` PASSes **and** `validate_plan_section_receipt.py` PASSes **and** the `.plan.md` has every required template section with **Execute via Cursor Build** (not `make campaign`, not Program Lock) **and** the stacked-PR / PR URL contract.

## Failure Handling

- Ambiguous objective → STOP; ask.
- Validator or section-receipt FAIL → fix or set `convergence.status=blocked`; do not claim ready.
- GAR skipped → not ready; load `l9-global-architect` before emit.
- User asks for PE / campaign / `make campaign` → hand off to `l9-plan`; do not invent a PE lock here.
- KERNEL / PE overlay landing → hand off to `l9-plan`.
- User presses Build → if any open PR exists, execute on the unique chain tip (never `origin/main`); after todos `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the **PR URL**; do not skip `make pr`; do not run `make campaign`.
- Build without the stacked publish, or a finish reply without the opened PR URL → incomplete.
