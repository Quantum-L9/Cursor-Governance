---
name: plan-audit
version: "1.0.0"
description: "Audit unbuilt/stale Cursor plans from the last 7 days (same scanner as sessionStart)"
skill: l9-plan-audit
auto_chain: null
---

# /plan-audit — Recent unbuilt plan audit

## WHAT IT DOES

Runs the deterministic `l9-plan-audit` scanner against the machine-global Cursor
plans directory (`<workspace>/.cursor/plans` → `~/.cursor/plans`) and prints
unbuilt plans from the last **7 days** with staleness flags.

This is the **on-demand** path. SessionStart / `/start-session` already inserts
the same report under `### Plan audit` in bootstrap `additional_context`.

Findings are **display-only** — do not auto-Build plans from this command.

---

## EXECUTION (MANDATORY)

Agent runs from the open workspace:

```bash
REPO="${CURSOR_PROJECT_DIR:-$(pwd)}"
GOV="${HOME}/.cursor-governance"
[ -f "$GOV/skills/l9-plan-audit/scripts/audit_plans.py" ] || GOV="$REPO"

python3 "$GOV/skills/l9-plan-audit/scripts/audit_plans.py" \
  --workspace "$REPO" \
  --window-days 7 \
  --format markdown \
  --budget-chars 1200 \
  --limit 5
```

Optional JSON:

```bash
python3 "$GOV/skills/l9-plan-audit/scripts/audit_plans.py" \
  --workspace "$REPO" --format json --limit 10
```

---

## OUTPUT

Present the scanner stdout as-is. Do not invent plans not listed.

| Status line | Meaning |
|-------------|---------|
| `none: no unbuilt plans in window` | Clean |
| `STALE:` / `UNBUILT:` | Candidate with flags |
| `plan audit: no plans dir` | Plans path missing |
| `plan audit: unavailable` | Soft failure |

### Ready For

→ `/ynp` — prioritize among findings if the user wants a next action  
→ `/l9-plan` — author a new plan (not an audit)  
→ Build a listed plan only when the user explicitly chooses it

---

## NOTES

- Rules SSOT: `skills/l9-plan-audit/references/staleness-rules.md`
- SessionStart wiring: `ops/hooks/session_start_bootstrap.sh` → `### Plan audit`

--- End Command ---
