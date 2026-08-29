<!-- L9_META
l9_schema: 1
parent: l9-plan-simple
layer: reference
role: plan_workflow
tags: [plan, todo, validation, projection, cursor-build]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-29
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

## Required `.plan.md` sections

Same as the shared template / `plan-workflow-pe-autonomy.md` items 1–16, with item 17 swapped to **Execute via Cursor Build**.

## Forbidden execute wiring

- live `make campaign` (not a prohibition sentence)
- Program Lock / Controller
- campaign authorization packet
- `@environment/program-execution` as the run path
- new worktree from `origin/main` as a planning requirement
- branching from `origin/main` when any open PR exists
- finishing Build without `PR_STACK=auto PR_REMEDIATE=0 make pr`
- a finish reply that omits the opened PR URL

KERNEL pack / PE overlay landings: escalate to `l9-plan` + `rules/46-kernel-pack-new-branch.mdc`. Do not invent a SHA lock here.
