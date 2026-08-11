<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-end-session
layer: reference
role: session_close_protocol
tags: [l9, session, handoff, memory, governance]
owner: igor_beylin
status: active
version: 1.3.0
updated: 2026-08-06
auto_chain: extract-chat
--- /SKILL_META ---
-->

# /end-session — Session Close

## WHAT IT DOES

Clean session close:

1. Write structured PICKUP context to Graphiti (sole memory path — memory-bank deprecated)
2. Extract learnings to memory (via canonical pipeline; see `docs/MEMORY_PIPELINE_MAP.md`)
3. Save Redis session context for cross-window resume
4. Create handoff summary
5. **Backup GlobalCommands to GitHub** (`Quantum-L9/Cursor-Governance`)

Protocol spec: `end-session.yaml` (v2.1)

---

## EXECUTION

### 1. MEMORY WRITE — Graphiti (REQUIRED)

Health-check first, then write the structured PICKUP packet + one atomic
write per learning fact, all to Graphiti. This is the canonical store.

If health check fails or a write errors: **warn and skip** memory persistence
for this close — do **not** fall back to `memory-bank/` (deprecated; see
`MEMORY_BANK_POLICY.md`). Continue with Redis/handoff.

Use governance **venv Python** (see `skills/l9-graphiti-memory/SKILL.md`). Bare `python3` often fails with `No module named 'yaml'`. Do **not** pass `--scope` / `--scope cursor` (not a CLI flag).

```bash
GOV="${HOME}/.cursor-governance"
GRAPHITI_PY="${GOV}/.venv/bin/python"
CLIENT="${GOV}/ops/graphiti/graphiti_memory_client.py"
[ -x "$GRAPHITI_PY" ] || GRAPHITI_PY="${HOME}/Cursor-Governance/.venv/bin/python"
[ -f "$CLIENT" ] || CLIENT="${HOME}/Cursor-Governance/ops/graphiti/graphiti_memory_client.py"

"$GRAPHITI_PY" "$CLIENT" health
# If healthy:
"$GRAPHITI_PY" "$CLIENT" write \
  "PICKUP|date=$(date +%Y-%m-%d)|task={TASK}|files={FILES}|next={NEXT}|blocker={BLOCKER}|gmps={GMPS}|outcome={OUTCOME}" \
  --kind pickup_context

# One atomic write per learning fact (see step 2 below for format).
```

`ops/hooks/graphiti-session-end.sh` on automatic `sessionEnd` tries Graphiti
only; on failure it WARNs and exits without writing `memory-bank/`.

### 2. EXTRACT LEARNINGS (canonical memory pipeline — part of step 1)

Only runs when step 1's Graphiti health check passed. If it did not, skip
learnings writes and note the gap in the handoff report.

Session learnings MUST be written through the **canonical memory path** so they get governance, audit, DAG (packet_store → graph_sync → semantic_embed → insights), and persistence. See `docs/MEMORY_PIPELINE_MAP.md`.

- **Path:** `graphiti_memory_client.py write` → Graphiti episode queue → entity/edge extraction → group-scoped graph. Legacy C1 path (`cursor_memory_client.py` → `save_memory` → SubstrateDAG → PostgreSQL/Neo4j/pgvector) is deprecated — do not use it for new writes.

**Write atomic memories — one fact per write, not one big blob.**
See `.cursor/rules/87-cursor-memory-kernel.mdc` → "Memory Write Format" for the full spec.

```bash
# One write per fact. Pre-classify with --kind only (no --scope). Terse, no preamble.
"$GRAPHITI_PY" "$CLIENT" write \
  "{terse fact 1}" \
  --kind lesson --group-id {resolved_group_id}

"$GRAPHITI_PY" "$CLIENT" write \
  "{terse fact 2}" \
  --kind insight --group-id {resolved_group_id}
```

### 3. REDIS SESSION CONTEXT (cache_set_session_context)

**Call MCP tool `cache_set_session_context`** so the next window can resume from this handoff. Use the same structure as the handoff below.

- **context** (required): JSON object with:
  - `summary`: 1–2 sentence summary of session work
  - `completed`: list of tasks completed
  - `in_progress`: list with status if any
  - `next_steps`: 2–5 concrete next steps
  - `open_questions`: list if any
  - `files_touched`: list of paths modified (optional but useful)
- **session_id**: omit (daily session)
- **ttl**: omit (default 86400)

This step is mandatory: without it, the next window will not have this handoff in Redis.

### 3b. SESSION HOOKS (Graphiti sessionEnd)

Rely on the installed Cursor hook `ops/hooks/graphiti-session-end.sh` (wired via `~/.cursor/hooks.json` after `setup_workspace_symlinks.sh`).

- On automatic `sessionEnd`, that script writes Graphiti `--kind session_summary` when a summary payload is present and Graphiti is enabled.
- If no summary was available, Graphiti is disabled, or the write fails: **skip** — warn in the close report; do not fall back to memory-bank or CEG working-memory promotion.
- **Do not** invoke CEG working-memory session hooks (not part of Cursor-Governance). Agent-side close persistence is Graphiti PICKUP + lessons (step 1).

### 4. GOVERNANCE GITHUB BACKUP (mandatory)

Push Dropbox SSOT (everything under `@.cursor-commands/`) to the governance repo:

```bash
bash .cursor-commands/ops/scripts/backup_to_github.sh "chore(governance): end-session $(date +%Y-%m-%d)"
```

Or: `/governance-backup` / `make governance-backup` (PlasticOS).

Also runs automatically on **sessionEnd** after `setup_workspace_symlinks.sh` (see `~/.cursor/hooks.json`).

### 5. HANDOFF

```markdown
## Session Handoff

### Completed
- {task 1}
- {task 2}

### In Progress
- {task} — {status}

### Next Steps
1. {action}
2. {action}

### Open Questions
- {question}
```

---

## OUTPUT

```markdown
## 👋 SESSION CLOSED

### Summary
**Work completed:** {count} items
**Reports generated:** {list}

### Handoff
- PICKUP context + learnings written to Graphiti (or warned if Graphiti unavailable) ✅
- Redis session context saved (cache_set_session_context) ✅
- Next steps defined ✅
- GlobalCommands pushed to Cursor-Governance ✅

### When you open a new window
→ Use **/start-session** to load Redis context + Graphiti PICKUP/inject and resume.
```

→ **Auto-chains to /extract-chat**
