<!-- L9_META
l9_schema: 1
parent: l9-plan-simple
layer: reference
role: plan_workflow
tags: [plan, todo, validation, projection, cursor-build, embedded, handoff, gar, section-receipt]
owner: igor_beylin
status: active
version: 1.3.0
updated: 2026-09-02
/L9_META -->

# Plan Workflow — Shared Template, Two Handoff Modes

**Default for skill `l9-plan-simple` and `/l9-plan-simple`.**

Fill the **same** first-class SSOT as `l9-plan`:
[`environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`](../../../environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md)
(skill [executable-plan.template.md](executable-plan.template.md) is a symlink — do not fork).

Section list matches [`../l9-plan/references/plan-workflow-pe-autonomy.md`](../../l9-plan/references/plan-workflow-pe-autonomy.md) except the execute authority.

## Handoff modes

| Mode | Status | Terminates at | Frontmatter |
|------|--------|---------------|-------------|
| `cursor-build` | **default** | Build execution, then the stacked publish and PR URL | `kind: simple`, `execute_via: cursor-build` |
| `embedded` | first-class | validated planning artifacts, returned to the invoking caller | `kind: simple`, `execute_via: embedded` |

Mode selection is explicit and machine-observable (`--execute-via`, then `execute_via` in the projection frontmatter). `cursor-build` applies whenever embedded was not explicitly requested. Capability absence never selects `embedded`, and there is no silent fallback between modes.

## Dual artifact law (both modes)

| Artifact | Role | Gate |
|----------|------|------|
| `PLAN_DOCUMENT` JSON | Machine SSOT for depth gates | `python3 ../l9-plan/scripts/validate_plan_document.py` MUST PASS |
| Cursor `.plan.md` | Mode-selected projection | Shared canonical template; PE execute block **replaced** |

`PLAN_DOCUMENT` stays execution-neutral. The mode lives on the projection axis; do not encode it as a schema field, and do not fork the schema per mode.

## Architect upstream (required, both modes)

Read `skills/l9-global-architect/SKILL.md` and run the GAR bootloader **before** emit. Do not skip to PLAN_DOCUMENT. Standalone `/l9-global-architect` remains explicit-only; this step is the plan-simple supporting invoke. Embedded mode does not waive it — embedded narrows the *handoff*, never the planning depth.

## Shared steps (identical in both modes)

0. **Architect** — run `l9-global-architect` to settle architecture (or record that it is already settled).
1. **Doctrine and depth** — planning doctrine + `route_plan.py` classification (escalate-only).
2. **Pre-validation** — bind the current workspace (branch, dirty, HEAD if useful). For code in scope on governed workspaces name `.pre-commit-config.yaml` as the hook catalog. Do **not** write `Lock: origin/main = <sha>`. Do **not** require a clean tip worktree. Do **not** stop-and-replan as a Program Lock.
3. **Gather** — objective, scope in/out, falsifiable success. Ambiguity → STOP and ask.
4. **Decompose** — TODOs with files (or blocker) and deps. DAG / Phase-0 rows are the todo projection, not Controller `claim`/`render` Task Cards.
5. **Stress-test and leverage** — mandatory; no mode skips it.
6. **Doc / Root Surface Impact** — update TODOs or N/A with reason.
7. **Emit PLAN_DOCUMENT** — JSON conforming to the shared schema.
8. **Validate PLAN_DOCUMENT** — `validate_plan_document.py` MUST PASS before any projection is offered.
9. **Project the plan** — one renderer, mode-selected:

Run from the repository root: the scripts confine CLI paths to the working
directory, so a `../l9-plan/...` invocation from the skill root is rejected.

```bash
# default
python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py <plan.json> --execute-via=cursor-build \
  > .cursor/plans/<snake_slug>_<8hex>.plan.md

# caller-owned
python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py <plan.json> --execute-via=embedded
```

Or hand-copy the first-class SSOT and apply the mode's execute swap below. Do **not** call `render_plan_pe_autonomy.py` without `--execute-via` for a simple plan (the default injects PE).

Frontmatter in both modes: Cursor `name`, `overview`, `todos`, `isProject`, plus `kind: simple` and the selected `execute_via`. Convergence `execute_via` matches.

10. **Section receipt** — generate then validate, in both modes. The receipt stamps `handoff_mode`, so it is judged against that mode's headings: **Execute via Cursor Build** for `cursor-build`, **Handoff to Caller** for `embedded`. Schema owner stays `../l9-plan/schemas/plan-document.schema.json`; the receipt shape is `../schemas/plan-section-receipt.schema.json`.

```bash
# from the repository root
python3 skills/l9-plan-simple/scripts/generate_plan_section_receipt.py \
  --plan-json <plan.json> --plan-md <plan.md> --out <plan>.section-receipt.json \
  --gar-invoked
python3 skills/l9-plan-simple/scripts/validate_plan_section_receipt.py <plan>.section-receipt.json
```

## Branch — `cursor-build` (unchanged)

**Replace** the template heading **Execute via @environment/program-execution + autonomy** (pipeline steps, `make campaign`, campaign packet stub) with:

```markdown
## Execute via Cursor Build

Press **Build**. Plan on the current workspace. Execute on the unique open-PR chain tip.

- If any open PR exists: **never** branch from `origin/main`. Start from the unique chain tip (`PR_STACK=auto`). Use `agent_worktree_start.sh` when this checkout is not already that tip. Sibling open-PR chains fail closed.
- If the board is empty: `origin/main` is allowed.
- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a **planning** requirement.
- After Build todos complete: scoped-commit (pathspecs), `l4_local.py authorize-release`, then `PR_STACK=auto PR_REMEDIATE=0 make pr`. Do not skip `make pr`.
- The finish reply **must** display the opened PR URL as proof. Without that URL the Build is incomplete.
```

A delivered simple plan that still contains a live (unnegated) `make campaign` command or a live PE execute heading is not ready. Required prohibition sentences such as `Do not run make campaign` are not live wiring.

## Branch — `embedded` (terminal)

**Replace** the same template heading with a caller-owned handoff:

```markdown
## Handoff to Caller

This document is **validated planning evidence**. Embedded mode terminates here and returns control to the invoking caller.

- The `PLAN_DOCUMENT` behind this projection PASSed `validate_plan_document.py`.
- This markdown is that document's validated projection — a planning artifact, not a run instruction.
- The **caller** owns everything downstream: branch selection, worktree, mutation, verification, publication, and release.
- The caller MUST establish and enforce its own execution authority before acting on this plan.
- Embedded mode grants no mutation, commit, publication, pull-request, campaign, Program Execution, phased-execution-protocol, or deployment authority.
- Nothing in this document authorizes an executor to act on it.
```

The embedded branch is **terminal** once three things hold:

1. `PLAN_DOCUMENT` validated (`validate_plan_document.py` PASS).
2. Projection validated (mode-specific structural checks below).
3. Caller handoff recorded — the reply states that control returns to the caller and that no execution authority was conferred.

Nothing further is performed, requested, or implied: no branch, no worktree, no commit, no publication, no campaign, no phased execution protocol, no deployment.

**Intended callers:** nested skills, pre-birth and repository-birth workflows, orchestration pipelines, and any system that needs L9 planning depth while owning downstream realization itself.

## Required `.plan.md` sections

Same as the shared template / `plan-workflow-pe-autonomy.md` items 1–16. Item 17 is the mode's handoff section: **Execute via Cursor Build** or **Handoff to Caller**.

## Forbidden execute wiring (both modes)

- live `make campaign` (not a prohibition sentence)
- Program Lock / Controller
- campaign authorization packet
- `@environment/program-execution` as the run path
- new worktree from `origin/main` as a planning requirement

Additionally in `cursor-build`:

- branching from `origin/main` when any open PR exists
- finishing Build without `PR_STACK=auto PR_REMEDIATE=0 make pr`
- a finish reply that omits the opened PR URL

Additionally in `embedded` — the projection must carry **no live instruction** to:

- press Build, or execute the plan at all
- select a branch, open a worktree, or run `agent_worktree_start.sh`
- commit, push, publish, or open a pull request
- run a campaign, admit a Program Lock or Controller lease
- start a phased execution protocol
- deploy

KERNEL pack / PE overlay landings: escalate to `l9-plan` + `rules/46-kernel-pack-new-branch.mdc`. Do not invent a SHA lock here.
