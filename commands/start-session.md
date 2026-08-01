---
name: start-session
version: "3.0.0"
description: "Run the L9 sessionStart bootstrap for the open workspace (same path as Cursor hooks + make start)"
auto_chain: null
---

# /start-session — Session Startup

## WHAT IT DOES

Runs the **same** sessionStart bootstrap Cursor already uses on hook fire — wiring, Graphiti, memory-bank T0 excerpts, IDE/plugin reconcile — without the user locating any script.

Canonical implementation (single source of truth):

- Source: `$HOME/.cursor-governance/ops/hooks/session_start_bootstrap.sh`
- Installed hook copy: `$HOME/.cursor/hooks/session-start-bootstrap.sh`
- Human/agent entry: `make -C "$HOME/.cursor-governance" start WS="<repo>"`

Do **not** re-implement wiring / Graphiti / memory-bank steps in this command. The bootstrap owns them.

---

## EXECUTION (MANDATORY)

Agent runs this from the **open consumer workspace** (never ask the user for the bootstrap path):

```bash
REPO="${CURSOR_PROJECT_DIR:-$(pwd)}"
GC="$HOME/.cursor-governance"

# SSOT resolve (same order as bootstrap) — only if clone root missing
if [ ! -f "$GC/CANONICAL_LAW.md" ]; then
  for root in "$HOME/Dropbox/cursor governance" "$HOME/Dropbox/Cursor Governance"; do
    if [ -f "$root/CANONICAL_LAW.md" ]; then GC="$root"; break; fi
    if [ -f "$root/GlobalCommands/CANONICAL_LAW.md" ]; then GC="$root/GlobalCommands"; break; fi
  done
fi

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
| `CURSOR_PROJECT_DIR` | Workspace the bootstrap wires + reads `memory-bank/` from |

### After bootstrap output

1. Parse the rendered `env:` + `context:` lines (or raw JSON if renderer skipped).
2. If `wiring: FAIL` appears → auto-run:

```bash
bash "$GC/ops/scripts/wire_governance_workspace.sh" "$REPO"
make -C "$GC" start WS="$REPO"
```

3. Present the **STATE_SYNC** block below from bootstrap context (do not invent checks the bootstrap did not run).
4. If `memory-bank/activeContext.md` excerpt is thin or absent, optionally `head` the workspace `memory-bank/*.md` files for the user — still do not replace the bootstrap.

---

## QUICK MODE

```text
/start-session --quick
```

Same bootstrap, but agent may skip re-reading full `memory-bank/` bodies after the hook excerpts (still run `make start`).

---

## OUTPUT — STATE_SYNC

```markdown
## SESSION STARTED

### Bootstrap
| Check | Status |
|-------|--------|
| Bootstrap script | ✅ ran via make start / session_start_bootstrap.sh |
| Governance wiring | ✅ PASS / ❌ FAIL (from context) |
| Graphiti | ✅ healthy / ⚠️ degraded / ❌ down (from context) |
| memory-bank T0 | ✅ excerpts / ⚠️ absent (from context) |
| Slash commands | ✅ `.cursor-commands/commands` via l9-governance plugin |

### Context (from bootstrap)
{bullet list from rendered context lines}

### Ready For
→ `/ynp` — next action
→ `/gmp "{task}"` — phased work
→ `/commands-index` or read `commands/commands-index.md` — full slash library
```

---

## NOTES

- Cursor also runs this bootstrap automatically on `sessionStart` via `~/.cursor/hooks.json`. `/start-session` is the **manual / repair / new-window** entry that uses the identical script.
- Slash commands activate when governance is wired: `~/.cursor/plugins/local/l9-governance` → SSOT (discovers `commands/`), plus repo `.cursor-commands` symlink. Bootstrap/`make start` ensures that wiring.
- Legacy C1 / Redis steps are **not** part of this command; use Graphiti + memory-bank (T0) as the resume stack.

--- End Command ---
