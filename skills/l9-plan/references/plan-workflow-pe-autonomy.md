<!-- L9_META
l9_schema: 1
parent: l9-plan
tags: [plan, todo, validation, projection, program-execution, autonomy]
status: active
version: 4.0.0
updated: 2026-08-12
supersedes_for_default_plan_mode: plan-workflow.md
/L9_META -->

# Plan Workflow — PE + Autonomy Executable Projection (default)

**Default for `/l9-plan` and skill `l9-plan` plan mode.**  
Legacy human projection (GMP-section markdown only) remains at [plan-workflow.md](plan-workflow.md) — do not delete; do not use as the default deliverable. `/plan` slash is retired.

## Dual artifact law

| Artifact | Role | Gate |
|----------|------|------|
| `PLAN_DOCUMENT` JSON | Machine SSOT for depth gates (`schemas/plan-document.schema.json`) | `scripts/validate_plan_document.py` MUST PASS |
| Cursor `.plan.md` | Executable projection agents Build / run | **MUST** be filled from first-class SSOT [`environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`](../../../environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md) (skill `executable-plan.pe-autonomy.template.md` is a symlink) |

Heading-complete legacy markdown without a validated JSON + PE/autonomy `.plan.md` is **not ready**.

Aligned body contract: WIP/canonical `canonical.schema.plan_document.v1` sections (baseline, envelope, DAG, evidence, convergence). Cursor frontmatter stays Build-compatible (`name`, `overview`, `todos`, `isProject`).

## Emit sequence (fail-closed)

1. Emit + validate `PLAN_DOCUMENT` JSON (unchanged depth gates).
2. **Project** with:

```bash
python3 scripts/render_plan_pe_autonomy.py <plan.json> > .cursor/plans/<snake_slug>_<8hex>.plan.md
```

   Or hand-copy the first-class SSOT [`canonical.template.executable_plan.v1.plan.md`](../../../environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md) and fill every required section. Do **not** use `render_plan_markdown.py` as the primary deliverable (legacy only).

3. Ensure frontmatter `todos` are atomic, verb-led, `status: pending`, with `depends_on` matching the execution DAG.
4. Ensure the **Execute via @environment/program-execution + autonomy** section is present and not stripped.
5. Set plan `status` to `executable` only when the template’s executability law holds.

## Execution pipeline (required next-skill path)

When the user executes (Build / `/autonomy` / explicit run), the plan **MUST** flow:

```text
.plan.md
  → @environment/program-execution  (Blueprint → Program Lock → Controller)
  → root autonomy/ + @autonomy (/autonomy → l9-bounded-autonomy)  [subordinate lease]
  → PE adapter (default Cursor: cursor-foreground)
```

Authority order: `environment/agents/PEER_EXECUTION.md`.  
Program lease is authoritative; autonomy packet must not widen Task Card ceilings or outlive the Program lease.

**Do not** free-form mutate from plan chat. **Do not** treat legacy `plan-workflow.md` sections as sufficient execution authority.

Recommended handoff skills: `/autonomy` + PE Controller runbook; optional `emit_gmp_phase0.py` only when also chaining GMP. Prefer `l9-ynp` to pick the next skill after planning.

## Required `.plan.md` sections (mirror template)

Fail-closed if any missing from the delivered `.plan.md`:

1. Cursor YAML frontmatter (`name`, `overview`, `todos`, `isProject`)
2. Metadata (+ `plan_id`, `schema_version`, `status`)
3. Architect framing
4. Immutable baseline (full commit SHA)
5. Objective + success properties (evidence-typed)
6. Capability preflight (ref)
7. Execution envelope (fs / commands / network / secrets / `autonomous_merge: false`)
8. Side effects + idempotency (per mutating todo)
9. Architecture impact
10. Rollback (ref)
11. Complexity and uncertainty
12. Execution DAG / Phase-0 ↔ PE Task Cards table
13. Property evidence matrix
14. Stress and disconfirm
15. Out of scope
16. Convergence (+ `execute_via` PE+autonomy)
17. **Execute via @environment/program-execution + autonomy** (pipeline steps + campaign packet stub)

Optional (activate when conditions in template/schema apply): inventory classification, gated write pipeline, regeneration extinguishment, follow-on milestone.

## Gate rules

- Every plan must validate via `scripts/validate_plan_document.py`.
- Delivered markdown for plan mode **MUST** be the PE+autonomy `.plan.md` shape (this workflow + template).
- Code-editing plans must include `make pr-check` in final / quality-gate success properties.
- Never weaken scanners to obtain PASS.
- Do not push, open a PR, or mutate product code from plan mode.
- `autonomous_merge` remains `false` in the campaign packet (`COMPATIBILITY.yaml`); L4 plan/PE stack merge only after green+mergeable per AGENTS.md.
