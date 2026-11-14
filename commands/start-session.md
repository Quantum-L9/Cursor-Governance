---
name: start-session
version: "4.0.0"
description: "Run the L9 sessionStart bootstrap for the open workspace (same path as Cursor hooks + make start)"
auto_chain: null
---

# /start-session — Session Startup

## WHAT IT DOES

Runs the **same** sessionStart bootstrap Cursor runs on hook fire, so every
repository opens on the same primed operating plane:

1. SSOT tip reported against `origin/main` (never moved — catch-up is `/ff`).
2. Workspace links healed (links-only, one retry).
3. Runtime probes: venv, IDE profile, memory **health only**, publish path,
   secrets plane, wiring, backup.
4. **Default projection binding** — `l9.projection/cursor-governance-operating-plane@2`
   plus the `always` Cursor domains (`governance/host-bindings/cursor.yaml`),
   verified against the governance-managed authority checkout
   `~/.l9/authority/.github`, which SessionStart provisions itself
   (`ops/scripts/ensure_authority_checkout.sh`). No skill or command is needed;
   `/coding-agent`, `/lcto`, `/architect` are the manual bindings.
5. Route locator for this conversation.

SessionStart does **not** hydrate memory, read `memory-bank/` (retired), or read,
rank or display plans. Resume is on demand:
`python -m ops.memory.cli hydrate "<task>" --workspace <repo>` (CANONICAL_LAW §8.9).

Canonical implementation (single source of truth — do not re-implement its steps here):

- Source: `$HOME/.cursor-governance/ops/hooks/session_start_bootstrap.sh`
- Installed hook copy: `$HOME/.cursor/hooks/session-start-bootstrap.sh`
- Human/agent entry: `make -C "$HOME/.cursor-governance" start WS="<repo>"`

---

## EXECUTION (MANDATORY)

Run from the **open workspace** (never ask the user for the bootstrap path):

```bash
REPO="${CURSOR_PROJECT_DIR:-$(pwd)}"
GC="$HOME/.cursor-governance"
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
| `CURSOR_PROJECT_DIR` | Workspace the bootstrap wires and reports on |
| `L9_AUTHORITY_ROOT` | Operator-chosen authority checkout; the managed one is then not used |

### Remediation — follow the remedy the report names, once

| Report says | Do |
|---|---|
| `wiring: … remedy: /ff` (SSOT tip not `origin/main`) | Tell the user; `/ff` parks unique commits then fast-forwards. Do not `git checkout`, reset, or run `governance_activate_fresh.sh`. |
| `wiring: … exhausted auto-repair; remedy: /wire` | `bash "$GC/ops/scripts/wire_governance_workspace.sh" "$REPO"`, then re-run `make start` once. |
| `authority checkout: UNAVAILABLE` / `TIMED OUT` | Report it. Binding stays NOT BOUND; the next session resumes provisioning. |
| `default projection binding: NOT BOUND` / `DEGRADED` | Report the named reason. Cite **no** operating-plane semantics that did not verify. |

Do not re-diagnose what the report already classified, and do not run a second
check grid.

---

## OUTPUT — STATE_SYNC (concise, each fact once)

Render from bootstrap `additional_context`. One line per fact; never repeat a
line that appears in another section; omit healthy detail.

```markdown
## SESSION STARTED — {workspace basename} @ {branch}

**Plane:** {BOUND | DEGRADED | NOT BOUND} — operating-plane@2 at authority main {sha12}; domains {list of BOUND domains | reason}
**SSOT:** {sha7} vs origin/main {sha7} ({match | N ahead / M behind})

{### Needs attention — ONLY the ### FAILED and ### Degraded lines, verbatim, each with its remedy; omit the section when both say none}

**Healthy:** {comma-separated names of the ### Runtime lines, e.g. venv, ide-profile, memory, publish-path, secrets-bind}

→ `/ynp` next action · `/gmp "{task}"` phased work · `commands/commands-index.md` full library
```

Rules:

- The binding line is mandatory. It is the answer to "what may this session cite".
- Do not print the `### memory status` block or invent a `next=`; memory is health-only.
- Do not print `n/a` lines, the route locator, or code-graph unless they are the cause of a fault.
- No narrative below the block. If a fault needs explanation, the remedy column above is the explanation.

---

## QUICK MODE

```text
/start-session --quick
```

Same bootstrap; print only the **Plane** line and **Needs attention**.

---

## NOTES

- Cursor runs this bootstrap automatically on `sessionStart` via `~/.cursor/hooks.json`;
  Claude Code runs the equivalent binding from `session_start_claude_governance.sh`.
  `/start-session` is the manual / repair / new-window entry to the identical script.
- Every run writes `~/.l9/cursor/bootstrap-state.json` (`l9.cursor-bootstrap.v2`). Its
  `cursor-adapter` line aggregates other lines and is not a second fault when they are.
- Plan harvest stays `/l9-pipeline-audit`; leftover-todo refine is `/l9-audit-plans`.

--- End Command ---
