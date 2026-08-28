---
name: l9-audit-plans
version: "1.1.0"
description: "Audit and shelf the Cursor plans store: root = current unbuilt only; partial / built / superseded / parked go in subfolders"
auto_chain: null
---

# /l9-audit-plans — Plans-store shelf audit

## WHAT IT DOES

Audit the machine-global Cursor **plans store** and put every `.plan.md` on the
correct shelf. This is **not** `l9-plan` (author a plan) and **not** the
sessionStart skill `l9-plan-audit` (7-day live-queue display only).

Store path: workspace `.cursor/plans` → `~/.cursor/plans` → `docs/plans/`
(stamp `$HOME/.cursor/l9-plans-store`). Rules: [`docs/plans/README.md`](../docs/plans/README.md).

Do **not** auto-Build any plan.

---

## SHELVES (binding)

| Location | Who belongs there |
|---|---|
| *(root)* | **Current unbuilt** only — every todo still `pending`. `_TEMPLATE.plan.md` stays. |
| `partially-built/` | Started: ≥1 todo `completed` or `in_progress`, not all done |
| `built/` | All todos `completed`/`cancelled`, or `built: true` / `status: completed` |
| `backlog/` | Unbuilt, **not current** (parked) |
| `archive/` | Non-plan harvest / leftover companions |
| `archive/superseded/` | `status: superseded` or older same-slug copy |

**Current** = README live-queue name, or this week's dated `_*_M-D-YY` stamp, or
an explicit current hex the operator named. Do **not** treat a bulk mtime bump
as current.

Same-slug: dated `M-D-YY` outranks 8-hex. Compare only **root + backlog +
partially-built** — ignore `built/` and `archive/` mtimes.

Companion `.plan.json` / `.activate.yaml` move with their `.plan.md`.

---

## EXECUTION (MANDATORY)

### 1. Live-queue scan (sessionStart CLI — display)

```bash
REPO="${CURSOR_PROJECT_DIR:-$(pwd)}"
GOV="${HOME}/.cursor-governance"
[ -f "$GOV/skills/l9-plan-audit/scripts/audit_plans.py" ] || GOV="$REPO"

python3 "$GOV/skills/l9-plan-audit/scripts/audit_plans.py" \
  --workspace "$REPO" \
  --window-days 7 \
  --format markdown \
  --budget-chars 1200 \
  --limit 15
```

Present that stdout as the live-queue report. Do not invent plans it omitted.

### 1b. Harvest-candidate report (display)

From the same scan, list findings flagged `harvestable`. Group by concern
(`pe-execute`, `baseline`, `mission`). Those plans have live invariants **and**
stale wiring or a superseded mission.

Do **not** auto-Build. Do **not** auto-compile. Do **not** `git mv` a mixed
plan to `archive/superseded/`.

Harvest owner is skill `l9-intelligence-harvest`, invoked through
`/l9-pipeline-audit` (plans + WIP + campaigns). Do not call
`l9-harvest-pipeline`. Then `/gmp` the compiled packet. Do not
`make campaign`.

### 2. Shelf hygiene (root + backlog + partially-built)

Classify every top-level, `backlog/*.plan.md`, and `partially-built/*.plan.md`
(skip `_TEMPLATE.plan.md`):

1. `status: superseded` or older same-slug → `archive/superseded/`
2. `built: true` / `status: completed` / all todos done → `built/`
3. Same basename already in `built/` → drop the leftover (do not duplicate)
4. Any `completed` or `in_progress` remaining → `partially-built/`
5. Current + all `pending` → root
6. Unbuilt + not current → `backlog/`

**Backlog check is required.** Promote only current unbuilt to root. Move
current partials out of backlog into `partially-built/`. Move built/superseded
out of backlog.

### 3. Organize

Move (prefer `git mv` when tracked). Create `partially-built/` if missing.
Print a count table: root kept / partial / built / superseded / backlog / dropped dups.

Do not mass-rename historical hex/ISO stamps. Do not invent `pe/`, `ci/`, or date folders.

### 4. Re-scan

Re-run the step-1 CLI. Root must be current unbuilt only (plus `_TEMPLATE`).

---

## OUTPUT

```markdown
## Plans store audit

**Live queue (scanner):**
<paste CLI stdout>

**Moves:** root N | partially-built N | built N | superseded N | backlog N | dropped-dup N

**Root now:**
- `name.plan.md` …
```

| Scanner line | Meaning |
|---|---|
| `none: no unbuilt plans in window` | Live queue empty in the 7-day window |
| `UNBUILT:` / `STALE:` | Still at root; flags only — not a Build order |
| `plan audit: no plans dir` | Store path missing |

### Ready For

→ `/ynp` — pick the next **root** plan
→ `/l9-plan-simple` or `/l9-plan` — author a new plan (not this command)
→ Build a listed root plan only when the user names it

---

## NOTES

- SessionStart `### Plan audit` stays the `l9-plan-audit` skill (display-only, no moves).
- `/plan-audit` is a compatibility alias of `/l9-pipeline-audit`, not this command.
- Slash: `commands/l9-audit-plans.md`
