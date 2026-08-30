---
name: l9-pipeline-audit
version: "1.0.0"
description: "Audit plans, WIP, and PE campaigns; harvest via l9-intelligence-harvest; emit compiled WIP or campaign INTENT"
auto_chain: null
---

# /l9-pipeline-audit — Pipeline component audit

## WHAT IT DOES

Classify **three surfaces** with the same component verdicts used for Cursor
plans (`live_invariant`, `stale_wiring`, `superseded_mission`, `spent`):

| Surface | Root |
|---|---|
| plans | `docs/plans/` (top-level `*.plan.md`) |
| wip | `WIP/` (skip Legal Defense and secret globs) |
| campaigns | `environment/program-execution/campaigns/*/CAMPAIGN_SOURCE.yaml` |

Harvest live invariants through skill **`l9-intelligence-harvest`**. Emit
compiled packets as a new plan, `WIP/<M-D-YY>/<concern>/`, or a campaign
`HARVEST_INTENT.md`. Execute those packets with `/gmp`.

SessionStart uses this pack's `audit_pipeline.py --format session-start`
(same three surfaces; heading stays `### Plan audit`; NEXT 1–3 is one slot
per surface). On-demand harvest stays this slash. This is **not**
`/l9-audit-plans` (plans-store shelf only).
This is **not** `/harvest` / `l9-harvest-pipeline` (sed/cp deploy).

Do **not** auto-Build. Do **not** run `make campaign`. Do **not** admit a
Program Lock. Do **not** whole-file supersede a mixed donor.

`/plan-audit` is a compatibility alias of this command.

---

## SKILLS THIS COMMAND CALLS

1. this pack `scripts/audit_plans.py` — plans scan
2. `ops/scripts/wip_corpus.py` — read `WIP/INVENTORY.yaml` only (do not write)
3. Campaign sources — classify `CAMPAIGN_SOURCE.yaml` (do not mutate immutable source)
4. `l9-intelligence-harvest` — `bind_request.py` + `inventory_source.py` + qualify
5. `l9-gmp-protocol` — execute a compiled packet when the user names it

---

## EXECUTION (MANDATORY)

### 1. Multi-surface scan (display)

```bash
REPO="${CURSOR_PROJECT_DIR:-$(pwd)}"
GOV="${HOME}/.cursor-governance"
[ -f "$GOV/skills/l9-pipeline-audit/scripts/audit_pipeline.py" ] || GOV="$REPO"

"$GOV/.venv/bin/python" "$GOV/skills/l9-pipeline-audit/scripts/audit_pipeline.py" \
  --workspace "$REPO" \
  --format markdown
```

Present that stdout. Do not invent items it omitted.

### 2. Harvest (only named donors)

Do not auto-compile the whole harvestable list.

```bash
"$GOV/.venv/bin/python" "$GOV/skills/l9-pipeline-audit/scripts/run_intelligence_harvest.py" \
  --request-id "pipeline-audit-<concern>-<stamp>" \
  --beneficiary "$REPO" \
  --harvest-target "<concern> invariants" \
  --concern <concern> \
  --emit-dest plan|wip|campaign \
  --emit-path "$REPO/<dest>" \
  --out "$REPO/docs/plans/<concern>_compiled_M-D-YY.harvest.json" \
  <donor> [...]
```

`--emit-dest wip` writes `WIP/<M-D-YY>/<concern>/HARVEST.md`.
`--emit-dest campaign` writes `<campaign>/HARVEST_INTENT.md` (not `CAMPAIGN_SOURCE.yaml`).

Stamp donors `compiled_into` only. Do not set `status: superseded` on a mixed file.

### 3. Execute

`/gmp` the compiled packet. Do not `make campaign`.

---

## OUTPUT

```markdown
## Pipeline audit

**Scan:**
<paste CLI stdout>

**Harvested (if any):**
- concern / dest path

**Not done:**
- no Program Lock
- no whole-file donor supersede
```

### Ready For

→ `/gmp` a named compiled packet
→ `/l9-audit-plans` if the user only wants plans-store shelf moves
→ `/ynp` against harvestable concerns
