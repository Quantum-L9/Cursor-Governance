<!-- L9_META
l9_schema: 1
parent: l9-plan-simple
layer: reference
role: plan_workflow
tags: [plan, todo, validation, projection, cursor-build]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-21
/L9_META -->

# Plan Workflow — Shared Template, Cursor Build Execute

**Default for skill `l9-plan-simple` and `/l9-plan-simple`.**

Fill the **same** first-class SSOT as `l9-plan`:
[`environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`](../../../environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md)
(skill [executable-plan.template.md](executable-plan.template.md) is a symlink — do not fork).

Section list matches [`../l9-plan/references/plan-workflow-pe-autonomy.md`](../../l9-plan/references/plan-workflow-pe-autonomy.md) except the execute authority.

## Dual artifact law

| Artifact | Role | Gate |
|----------|------|------|
| `PLAN_DOCUMENT` JSON | Machine SSOT for depth gates | `python3 ../l9-plan/scripts/validate_plan_document.py` MUST PASS |
| Cursor `.plan.md` | Executable projection the user Builds | Shared canonical template; PE execute block **replaced** |

## Emit sequence (fail-closed)

1. Emit + validate `PLAN_DOCUMENT` JSON.
2. Project with:

```bash
python3 ../l9-plan/scripts/render_plan_pe_autonomy.py <plan.json> --execute-via=cursor-build \
  > .cursor/plans/<snake_slug>_<8hex>.plan.md
```

   Or hand-copy the first-class SSOT and apply the execute swap below. Do **not** call `render_plan_pe_autonomy.py` without `--execute-via=cursor-build` (that injects PE).

3. Frontmatter: Cursor `name`, `overview`, `todos`, `isProject`, plus `kind: simple`, `execute_via: cursor-build`.
4. Convergence `execute_via`: `cursor-build`.
5. Immutable baseline: current workspace (branch, dirty, HEAD if useful). Do **not** write `Lock: origin/main = <sha>`. Do **not** require a clean tip worktree. Do **not** stop-and-replan as a Program Lock. For code in scope name `.pre-commit-config.yaml` as the hook catalog.
6. DAG / Phase-0 table: keep as the todo/DAG projection. Rows are Build todos, not Controller `claim`/`render` Task Cards.

## Execute swap (required)

**Replace** the template heading **Execute via @environment/program-execution + autonomy** (pipeline steps, `make campaign`, campaign packet stub) with:

```markdown
## Execute via Cursor Build

Press **Build**. Work in the **current checkout**.

- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a planning requirement.
```

A delivered simple plan that still contains a live (unnegated) `make campaign` command or a live PE execute heading is not ready. Required prohibition sentences such as `Do not run make campaign` are not live wiring.

## Required `.plan.md` sections

Same as the shared template / `plan-workflow-pe-autonomy.md` items 1–16, with item 17 swapped to **Execute via Cursor Build**.

## Forbidden execute wiring

- live `make campaign` (not a prohibition sentence)
- Program Lock / Controller
- campaign authorization packet
- `@environment/program-execution` as the run path
- new worktree from `origin/main` as a planning requirement

KERNEL pack / PE overlay landings: escalate to `l9-plan` + `rules/46-kernel-pack-new-branch.mdc`. Do not invent a SHA lock here.
