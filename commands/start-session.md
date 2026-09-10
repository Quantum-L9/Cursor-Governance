---
name: start-session
version: "3.2.0"
description: "Run the L9 sessionStart bootstrap for the open workspace (same path as Cursor hooks + make start)"
auto_chain: null
---

# /start-session — Session Startup

## WHAT IT DOES

Runs the **same** sessionStart bootstrap Cursor already uses on hook fire —
wiring, Graphiti health/inject, IDE/plugin reconcile — without the user locating
any script. Local `memory-bank/` T0 is **retired**; resume SSOT is Graphiti.

Canonical implementation (single source of truth):

- Source: `$HOME/.cursor-governance/ops/hooks/session_start_bootstrap.sh`
- Installed hook copy: `$HOME/.cursor/hooks/session-start-bootstrap.sh`
- Human/agent entry: `make -C "$HOME/.cursor-governance" start WS="<repo>"`

Do **not** re-implement wiring / Graphiti steps in this command. The bootstrap owns them.

`governance_activate_fresh.sh` (called by this command) must **not** drop
`.venv`, `.env.local`, `env.local`, `.env.*.local`, or
`.claude/settings.local.json` on a shallow-clone swap. Those paths are
carried from the bak onto the new live tree (`ops/scripts/lib/ssot_machine_local_keep.sh`).

---

## EXECUTION (MANDATORY)

Agent runs this from the **open consumer workspace** (never ask the user for the bootstrap path):

```bash
REPO="${CURSOR_PROJECT_DIR:-$(pwd)}"
GC="$HOME/.cursor-governance"

# Prefer make start (renders hook JSON for humans). Fallback = hook binary + renderer.
if [ -f "$GC/Makefile" ]; then
  make -C "$GC" start WS="$REPO"
else
  CURSOR_PROJECT_DIR="$REPO" L9_BOOTSTRAP_SYNC=1 \
    bash "$GC/ops/hooks/session_start_bootstrap.sh" \
    | python3 "$GC/ops/scripts/render_bootstrap_context.py"
fi
```

| Flag / env | Meaning |
|------------|---------|
| `L9_BOOTSTRAP_SYNC=1` | Foreground reconcilers (set by `make start`) |
| `CURSOR_PROJECT_DIR` | Workspace the bootstrap wires + Graphiti-resolves |

### After bootstrap output

1. Parse the rendered `env:` + `context:` lines (or raw JSON if renderer skipped).
2. If `wiring: FAIL` appears → auto-run:

```bash
bash "$GC/ops/scripts/wire_governance_workspace.sh" "$REPO"
make -C "$GC" start WS="$REPO"
```

3. Present the **STATE_SYNC** block below from bootstrap context (do not invent checks the bootstrap did not run).
4. Resume from Graphiti PICKUP / hydration `next=` — do **not** read `memory-bank/`.

---

## QUICK MODE

```text
/start-session --quick
```

Same bootstrap; agent may skip re-printing full Graphiti prefetch bodies (still run `make start`).

---

## OUTPUT — STATE_SYNC

Print these sections from bootstrap `additional_context`. Do not invent a
second check grid. If a section is absent, say so.

```markdown
## SESSION STARTED

{### FAILED — if present; else omit}
{### Runtime}
{### Degraded}
{### Plan audit}

### Ready For
→ `/ynp` — next action
→ `/l9-audit-plans` — shelf the plans store (root = current unbuilt)
→ `/l9-pipeline-audit` — plans + WIP + PE campaigns (`/plan-audit` alias)
→ `/gmp "{task}"` — phased work
→ `/commands-index` or read `commands/commands-index.md` — full slash library
```

---

## NOTES

- Cursor also runs this bootstrap automatically on `sessionStart` via `~/.cursor/hooks.json`. `/start-session` is the **manual / repair / new-window** entry that uses the identical script.
- Slash commands activate when governance is wired: `~/.cursor/plugins/local/l9-governance` → SSOT (discovers `commands/`), plus repo `.cursor-commands` symlink. Bootstrap/`make start` ensures that wiring.
- Resume stack is Graphiti only (`ops/graphiti/MEMORY_BANK_POLICY.md`).
- Plan-audit wording lives in bootstrap `### Plan audit`. Do not restate it here. On-demand harvest is `/l9-pipeline-audit`. Shelf-only is `/l9-audit-plans`.

--- End Command ---
