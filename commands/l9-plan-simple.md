---
name: l9-plan-simple
version: "1.0.0"
description: "Create a Cursor Build plan from the shared executable-plan template (not PE / make campaign)"
auto_chain: ynp
---

# /l9-plan-simple — Cursor Build Planning

## WHAT IT DOES

Create a structured plan before implementation using the **same** first-class template as `/l9-plan`, then execute it with the **Build** button on the current checkout.

Delegates to skill **`l9-plan-simple`**:

- **Workflow:** `skills/l9-plan-simple/references/plan-workflow-simple.md`
- **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
- **Skill projection:** `skills/l9-plan-simple/references/executable-plan.template.md` → symlink (do not fork)
- **Validator:** `skills/l9-plan/scripts/validate_plan_document.py` (reuse)

This command does **not** run `make campaign` and does **not** admit a Program Lock.

For PE/campaign plans use **`/l9-plan`**.

---

## EXECUTION

Follow skill `l9-plan-simple`. Required deliverables:

1. Validated `PLAN_DOCUMENT` JSON
2. Cursor `.plan.md` under `.cursor/plans/<slug>_<8hex>.plan.md` from the shared template
3. Frontmatter `kind: simple`, `execute_via: cursor-build`
4. **Execute via Cursor Build** (PE execute block swapped)

### Project command

```bash
python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py <plan.json> --execute-via=cursor-build \
  > .cursor/plans/<snake_slug>_<8hex>.plan.md
```

Planning-only — do not edit product files until the user presses **Build**.

---

## NOTES

- Baseline records the current workspace. Do not write `Lock: origin/main = <sha>`.
- KERNEL pack / PE overlay landings: use `/l9-plan`, not this command.

--- End Command ---
