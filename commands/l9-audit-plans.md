---
name: l9-audit-plans
version: "2.0.0"
description: "Audit, shelf, and refine the Cursor plans store: root = current; leftover todos fold or compile; harvested donors omitted"
auto_chain: null
---

# /l9-audit-plans — Plans-store shelf + refine

## WHAT IT DOES

Put every `.plan.md` on the binding shelf, then keep leftover todos as **plan
work** (fold onto a same-concern beneficiary, else compile one packet per
concern). Harvested donors keep folder `status` plus `harvested: true` and are
omitted later.

This is **not** `l9-plan` and **not** `/l9-pipeline-audit`.
Do **not** auto-Build. SessionStart must not call refine.

Store path: workspace `.cursor/plans` → `~/.cursor/plans` → `docs/plans/`.
Rules: [`docs/plans/README.md`](../docs/plans/README.md),
[`skills/l9-audit-plans/references/refine.md`](../skills/l9-audit-plans/references/refine.md).

---

## SHELVES (binding)

| Location | Who belongs there |
|---|---|
| *(root)* | **Current unbuilt** only. `status: current`. `_TEMPLATE.plan.md` stays. |
| `partially-built/` | Started: ≥1 todo `completed` or `in_progress`, not all done |
| `built/` | All todos done, or `built: true` / `status: completed` |
| `stale/` | Unbuilt, **not current** (written, never started) |
| `archive/` | Leftover companions |
| `archive/superseded/` | `status: superseded` or older same-slug copy |

`harvested: true` is a **tag**, not a status. `partial/` / `backlog/` /
`pending/` are retired.

---

## EXECUTION (MANDATORY)

```bash
REPO="${CURSOR_PROJECT_DIR:-$(pwd)}"
GOV="${HOME}/.cursor-governance"
[ -f "$GOV/skills/l9-audit-plans/scripts/run_audit_plans.py" ] || GOV="$REPO"

"$GOV/.venv/bin/python" "$GOV/skills/l9-audit-plans/scripts/run_audit_plans.py" \
  --workspace "$REPO"

python3 "$GOV/skills/l9-pipeline-audit/scripts/audit_plans.py" \
  --workspace "$REPO" \
  --window-days 7 \
  --format markdown \
  --budget-chars 1200 \
  --limit 15
```

`run_audit_plans.py` is shelf → refine → shelf → README. Set
`L9_AUDIT_PLANS_REFINE=0` to skip refine (diagnose).

Do **not** call `l9-intelligence-harvest` as a writer. Do **not** absorb leftover
todos into `AGENTS.md`.

Present script stdout. Do not invent paths it omitted.

---

## OUTPUT

```markdown
## Plans store audit

**Invoke:**
<paste run_audit_plans.py stdout>

**Live queue (scanner, display only):**
<paste audit_plans.py stdout>
```

### Ready For

→ `/ynp` — pick the next **root** plan
→ `/l9-plan-simple` or `/l9-plan` — author a new plan (not this command)
→ Build a listed root plan only when the user names it

---

## NOTES

- SessionStart `### Plan audit` is `l9-pipeline-audit` (display-only). This slash
  is the plans-store shelf + refine organizer.
- `/plan-audit` is a compatibility alias of `/l9-pipeline-audit`, not this command.
- Slash: `commands/l9-audit-plans.md`
- Skill: `skills/l9-audit-plans` (`scripts/run_audit_plans.py`)
