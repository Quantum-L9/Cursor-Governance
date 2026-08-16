---
name: l9-plan
version: "2.0.0"
description: "Create deep PE+autonomy executable plan before action (Cursor .plan.md via first-class template)"
auto_chain: ynp
---

# /l9-plan — Execution Planning

## WHAT IT DOES

Create a structured plan before implementation. Delegates template authority to skill **`l9-plan`**:

- **Default workflow:** `skills/l9-plan/references/plan-workflow-pe-autonomy.md`
- **First-class fill-in template (git SSOT):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
- **Skill projection:** `skills/l9-plan/references/executable-plan.pe-autonomy.template.md` → symlink to SSOT
- **Legacy (kept):** `skills/l9-plan/references/plan-workflow.md` — not the default deliverable

1. Pre-Validate (mandatory)
2. Define objective + falsifiable success properties
3. Identify scope + execution envelope
4. List TODO items with deps (map to PE Task Cards / waves)
5. Doc / Root Surface Impact (mandatory)
6. Emit validated `PLAN_DOCUMENT` JSON
7. Project Cursor `.plan.md` via `render_plan_pe_autonomy.py` (must include PE+autonomy execute path)
8. Auto-chain to `/ynp`

Planning-only — do not edit product files, commit, or push from `/l9-plan`.

`/plan` is **retired** — use `/l9-plan` (this file) or invoke skill `l9-plan`.

---

## EXECUTION

Follow skill `l9-plan` (**plan mode default = PE+autonomy workflow**). Required deliverables (fail-closed):

1. Validated `PLAN_DOCUMENT` JSON (`scripts/validate_plan_document.py` PASS)
2. Cursor `.plan.md` under `.cursor/plans/<slug>_<8hex>.plan.md` filled from the first-class template
3. Sections listed in `plan-workflow-pe-autonomy.md` (frontmatter todos, baseline, envelope, DAG, evidence, convergence, **Execute via @environment/program-execution + autonomy**)

### Gate commands (governed workspaces)

```bash
# Changed-files scanners only — does NOT push or commit
OPEN_PR=0 make pr
```

Make remaps any capitalization of `pr`. There is no `pr-check` target.

### Project command

```bash
python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py <plan.json> \
  > .cursor/plans/<snake_slug>_<8hex>.plan.md
```

---

## OUTPUT

Deliver a Cursor `.plan.md` (not legacy GMP-only markdown). Shape SSOT:

`environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`

Must include execute authority:

```text
.plan.md
  → @environment/program-execution  (Blueprint → Program Lock → Controller)
  → @autonomy (/autonomy → l9-bounded-autonomy)  [subordinate]
  → PE adapter (cursor-foreground default)
```

→ **Auto-chains to /ynp** (recommends `/autonomy` + PE pipeline, or `/gmp` when GMP-locked)

---

## NOTES

- KERNEL pack / PE overlay / governed architecture landings: **new branch from `origin/main`** without asking. Do not mix unrelated WIP. Ask only if the user named the target branch or `origin/main` cannot be resolved. SSOT: `AGENTS.md` `KERNEL_PACK_NEW_BRANCH_DEFAULT_V1`; `rules/46-kernel-pack-new-branch.mdc`.

--- End Command ---
