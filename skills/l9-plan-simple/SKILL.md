---
name: l9-plan-simple
description: create a machine-validated cursor .plan.md from the shared executable-plan
  template in one of two handoff modes. default mode cursor-build executes with the build
  button and then opens a stacked PR; never branch off main when an open PR exists, and
  display the PR URL. embedded mode is for callers that own their own execution — it stops
  at validated planning artifacts and grants no execution, commit, publication, campaign,
  or deployment authority. use when scope is unclear, requirements need decomposition,
  cursor plan mode is on, the next step should be planned before code changes, or a
  nested skill or pipeline needs planning depth without downstream authority. do not use
  when the user asks for program-execution, make campaign, /l9-plan, or a pe campaign lock.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags:
  - l9
  - plan
  - spec
  - cursor-build
  - embedded
  - handoff
  - execution
  - requirements
  - validation
  owner: igor_beylin
  status: active
  version: 1.2.0
  updated: 2026-09-02
disable-model-invocation: true
---

# Execution Planning (Cursor Build · Embedded)

## Purpose

Produce a deep, machine-validated plan from the **same** first-class executable-plan template as `l9-plan`, then hand it off along one of two **handoff modes**:

| Mode | Status | Handoff | Frontmatter |
|------|--------|---------|-------------|
| `cursor-build` | **default** | user presses **Build**, then publishes with `PR_STACK=auto PR_REMEDIATE=0 l9 pr` and shows the PR URL | `kind: simple`, `execute_via: cursor-build` |
| `embedded` | first-class | terminates at validated planning artifacts and returns control to the invoking caller | `kind: simple`, `execute_via: embedded` |

Both modes share one doctrine, one PLAN_DOCUMENT schema, one validator, one stress-test and leverage pass, and one canonical projection renderer. Only the handoff projection differs. There is no second planner.

This skill does **not** wire the delivered plan to Program Execution in either mode. Do not run `make campaign`. Do not admit a Program Lock. Do not write `Lock: origin/main = <sha>`. Do not require a new worktree from tip as a **planning** requirement.

**Doctrine:** a minute of planning saves an hour of debugging. The template sections stay; only the handoff changes.

## Mode Selection

**`cursor-build` is the default.** Absent an explicit embedded request, plan in `cursor-build`.

Select `embedded` **only** when the caller asks for it explicitly and observably — a nested skill, contract, pipeline, or user that names embedded mode, `--execute-via=embedded`, or "planning only, I own execution". The selected mode is machine-observable in the projection frontmatter (`execute_via`), so the choice is auditable rather than inferred.

**Never infer embedded from capability absence.** Missing execution tools, a denied gate, an unavailable PR path, or a read-only surface are *blockers to report*, not a mode selector. There is **no** silent fallback from `cursor-build` to `embedded`: switching modes is a caller decision, and an unrequested switch is a contract violation, not a graceful degrade.

`embedded` is likewise not a rename of `cursor-build`. It projects different content and confers strictly less authority.

## Intended Embedded Callers

Nested skills; pre-birth and repository-birth workflows; orchestration pipelines; L9 Idea Foundry and comparable systems; any caller that needs L9 planning depth while owning branch, mutation, verification, publication, and release itself under its own contract.

## Core Contract

| Mode | Output | Load |
|------|--------|------|
| plan | `PLAN_DOCUMENT` JSON + Cursor `.plan.md` (shared template; Build handoff or embedded handoff) | [`../l9-plan/schemas/plan-document.schema.json`](../l9-plan/schemas/plan-document.schema.json) + **[references/plan-workflow-simple.md](references/plan-workflow-simple.md)** + first-class SSOT [`environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`](../../environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md) (skill `references/executable-plan.template.md` → symlink) |

Authoritative machine artifact: **PLAN_DOCUMENT** (JSON), validated by `l9-plan`'s `validate_plan_document.py` (reuse, do not copy). PLAN_DOCUMENT stays execution-neutral — the mode lives on the projection axis, not in the schema.

Default human/executable projection: the shared canonical `.plan.md` with the PE execute block **replaced** by the selected mode's handoff block.

## Authority Order

1. Explicit user objective and constraints.
2. Verified repo ground truth — existing modules, patterns, ADRs.
3. Repo invariants — `AGENTS.md`, `.cursor/rules/*.mdc`.
4. Shared executable plan template + the selected handoff mode.
5. This skill's workflow and `l9-plan` schema/validator.
6. `Unknown` — ask before filling gaps.

## Activation / Reject

**Activate** when scope is unclear, Cursor Plan mode is on, the user wants a Build-button plan, work should be planned before code changes, or a caller explicitly requests embedded planning it will realize itself.

**Reject** when the user names campaign / program-execution / `make campaign` / `/l9-plan` / Program Lock — hand off to `l9-plan`. Reject a trivial fully-specified one-liner. Reject KERNEL pack / PE overlay landings — those stay `l9-plan` + `rules/46-kernel-pack-new-branch.mdc`.

## Compact Workflow

Steps 1–8 are **identical in both modes**.

1. **Doctrine / depth** — load `l9-plan` [planning-doctrine.md](../l9-plan/references/planning-doctrine.md) and classify via `python3 ../l9-plan/scripts/route_plan.py` (escalate-only). Do not omit baseline gates.
2. **Pre-Validate** — bind the **current workspace** (branch, dirty, HEAD if useful). For code in scope on governed workspaces name `.pre-commit-config.yaml` as the hook catalog. Do **not** lock `origin/main` or open a tip worktree.
3. **Gather** — objective, scope in/out, falsifiable success. Ambiguity → STOP and ask.
4. **Decompose** — TODOs with files (or blocker) and deps. DAG rows are the task decomposition, not Controller `claim`/`render` Task Cards.
5. **Stress-test + leverage** — mandatory in both modes; reuse `l9-plan` [plan-stress-test.md](../l9-plan/references/plan-stress-test.md) and [first-order-leverage.md](../l9-plan/references/first-order-leverage.md).
6. **Doc / Root Surface Impact** — update TODOs or N/A with reason.
7. **Emit PLAN_DOCUMENT** — JSON conforming to the shared schema.
8. **Validate** — `python3 ../l9-plan/scripts/validate_plan_document.py <plan.json>`. FAIL → not ready.
9. **Project** — one renderer, mode-selected:

   ```bash
   # from the repository root
   python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py <plan.json> --execute-via=cursor-build   # default
   python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py <plan.json> --execute-via=embedded       # caller-owned
   ```

   Write to `.cursor/plans/<slug>_<8hex>.plan.md` in `cursor-build`; in `embedded`, return the projection to the caller (a path only if the caller asked for one). Frontmatter must carry `kind: simple` plus the selected `execute_via`.
10. **Handoff** — mode-specific, below.

### Handoff — `cursor-build` (default, unchanged)

User presses **Build**. If any open PR exists, execute on the unique chain tip (`PR_STACK=auto`); never branch from `origin/main`. After todos: scoped-commit, `l4_local.py authorize-release`, `PR_STACK=auto PR_REMEDIATE=0 make pr`. Display the opened **PR URL**. Recommend `l9-ynp` only if the next skill is unclear.

### Handoff — `embedded` (terminal)

Return the validated PLAN_DOCUMENT and the embedded projection to the invoking caller, and **stop**. State plainly that the caller owns everything downstream and must establish its own execution authority.

**Embedded success** is exactly this: `validate_plan_document.py` PASSes **and** the embedded projection passes its mode-specific structural checks (`kind: simple`, `execute_via: embedded`, a **Handoff to Caller** section, no live execution authority). No code execution, branch, commit, publication, or PR is required — or permitted — by this mode.

**Embedded grants none of:** Build execution · branch selection · worktree creation · commit authority · publication or pull-request authority · Program Execution or campaign authority · Program Lock or Controller lease · phased-execution-protocol authority · deployment authority. Do not emit a live instruction to run any of them, and do not treat the projection as authorization to act.

## Resource Map

- [references/plan-workflow-simple.md](references/plan-workflow-simple.md) — shared workflow; two handoff branches
- [references/executable-plan.template.md](references/executable-plan.template.md) — symlink to the first-class SSOT (do not fork)
- [references/validation-checklist.md](references/validation-checklist.md)
- [`../l9-plan/schemas/plan-document.schema.json`](../l9-plan/schemas/plan-document.schema.json)
- [`../l9-plan/scripts/validate_plan_document.py`](../l9-plan/scripts/validate_plan_document.py)
- [`../l9-plan/scripts/render_plan_pe_autonomy.py`](../l9-plan/scripts/render_plan_pe_autonomy.py) — `--execute-via=cursor-build` | `--execute-via=embedded`
- [`../l9-plan/scripts/route_plan.py`](../l9-plan/scripts/route_plan.py)
- Skill `l9-plan` — PE/campaign planner only

## Validation

Run from the repository root — the scripts reject paths that escape the working
directory, so `../l9-plan/...` from the skill root fails on path confinement.

```bash
python3 skills/l9-plan/scripts/validate_plan_document.py skills/l9-plan/fixtures/plan_pass.json
python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py skills/l9-plan/fixtures/plan_pass.json --execute-via=cursor-build | grep -q "Execute via Cursor Build"
python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py skills/l9-plan/fixtures/plan_pass.json --execute-via=cursor-build | grep -q "PR_STACK=auto"
python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py skills/l9-plan/fixtures/plan_pass.json --execute-via=embedded | grep -q "Handoff to Caller"
! python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py skills/l9-plan/fixtures/plan_pass.json --execute-via=embedded | grep -q "PR_STACK=auto"
python3 -m pytest tests/skills/test_l9_plan_simple_embedded.py -q
```

A delivered `cursor-build` plan is incomplete unless `validate_plan_document.py` PASSes **and** the `.plan.md` has every required template section with **Execute via Cursor Build** (not `make campaign`, not Program Lock) **and** the stacked-PR / PR URL contract.

A delivered `embedded` plan is incomplete unless `validate_plan_document.py` PASSes **and** the projection has every required template section with **Handoff to Caller** **and** carries no live execution, commit, publication, campaign, or deployment authority.

## Failure Handling

- Ambiguous objective → STOP; ask.
- Validator FAIL → fix or set `convergence.status=blocked`; do not claim ready.
- User asks for PE / campaign / `make campaign` → hand off to `l9-plan`; do not invent a PE lock here.
- KERNEL / PE overlay landing → hand off to `l9-plan`.
- Execution tooling unavailable in `cursor-build` → report the blocker. Do not silently switch to `embedded`.
- Caller requests `embedded` but expects mutation → STOP; the modes are not interchangeable and embedded confers no authority.
- User presses Build → if any open PR exists, execute on the unique chain tip (never `origin/main`); after todos `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the **PR URL**; do not run `make campaign`.
- Build without the stacked publish, or a finish reply without the opened PR URL → incomplete.
- Embedded projection that carries any live execution or publication instruction → incomplete; re-project.
