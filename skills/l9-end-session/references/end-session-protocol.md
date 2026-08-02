<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-end-session
layer: reference
role: session_close_protocol
tags: [l9, session, handoff, memory, governance]
owner: igor_beylin
status: active
version: 1.2.0
updated: 2026-07-28
auto_chain: extract-chat
--- /SKILL_META ---
-->

# /end-session — Session Close

## WHAT IT DOES

Clean session close:

1. Write structured PICKUP context to Graphiti (primary) — memory-bank only as a fallback
2. Extract learnings to memory (via canonical pipeline; see `docs/MEMORY_PIPELINE_MAP.md`)
3. Save Redis session context for cross-window resume
4. Create handoff summary
5. **Backup GlobalCommands to GitHub** (`Quantum-L9/Cursor-Governance`)

Protocol spec: `end-session.yaml` (v2.1)

---

## EXECUTION

### 1. MEMORY WRITE — Graphiti (primary, REQUIRED)

Health-check first, then write the structured PICKUP packet + one atomic
write per learning fact, all to Graphiti. This is the canonical store — when
this step succeeds, **skip step 1b entirely**; do not also write the same
session summary into `memory-bank/`.

```bash
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py health
# If healthy:
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py write \
  "PICKUP|date=$(date +%Y-%m-%d)|task={TASK}|files={FILES}|next={NEXT}|blocker={BLOCKER}|gmps={GMPS}|outcome={OUTCOME}" \
  --kind pickup_context

# One atomic write per learning fact (see step 2 below for format).
```

### 1b. MEMORY-BANK FALLBACK (only if Graphiti unreachable or a write fails)

Trigger this step **only** when step 1's health check fails or a write
errors — it replaces the Graphiti write for this session, it does not
supplement it. Fall back to the T0 `memory-bank/` files directly in the
**target repo being worked on** (`$CURSOR_PROJECT_DIR`) — never in
`$GLOBAL_COMMANDS` / the Cursor-Governance clone. See `MEMORY_BANK_POLICY.md`.

1. **Read current files first** — `activeContext.md`, `tasks.md`,
   `progress.md`, `tech-debt.md`. If another agent/thread is actively
   writing to them concurrently, wait for it to finish before editing.
2. **Append, never overwrite** — add a new dated section per file. Do not
   truncate or replace existing content; a full-file rewrite destroys any
   detail a prior session wrote manually. If `activeContext.md` has grown
   past ~1 screen, a manual consolidation pass may rewrite the "current
   state" summary as a fresh top section, but must not delete prior
   sessions' appended history outright (`85-workflow-state-bridge.mdc`).
3. **Check gitignore before assuming it's trackable:**
   ```bash
   git -C "$CURSOR_PROJECT_DIR" check-ignore -q memory-bank/activeContext.md
   ```
   If this exits `0` (ignored — commonly this machine's global
   `~/.gitignore_global`, not the repo's own `.gitignore`), append a
   repo-local negation to that repo's `.gitignore` (after any blanket ignore
   rule already in the file):
   ```
   !/memory-bank/
   !/memory-bank/**
   ```
   Then re-run `git check-ignore` to confirm it now resolves as trackable.
4. **Push without touching unrelated in-flight work** — if the target repo's
   current branch has a large unrelated uncommitted diff, do not commit on
   top of it. Create an isolated `git worktree` off a fresh copy of the
   repo's default branch, copy the `memory-bank/` files + `.gitignore`
   negation there, commit, push, and open a normal PR.

`ops/hooks/graphiti-session-end.sh` on automatic `sessionEnd` tries Graphiti
first; it runs `ensure_memory_bank_trackable()` + append-only `activeContext.md`
write **only** when Graphiti is unavailable or the write fails. This section
documents the same fallback contract for the manual `/end-session` flow.

### 2. EXTRACT LEARNINGS (canonical memory pipeline — part of step 1, primary path)

Only runs when step 1's Graphiti health check passed (if it didn't, learnings
go into the memory-bank fallback in step 1b instead — e.g. as bullet points
appended to `progress.md` — not written a second time here).

Session learnings MUST be written through the **canonical memory path** so they get governance, audit, DAG (packet_store → graph_sync → semantic_embed → insights), and persistence. See `docs/MEMORY_PIPELINE_MAP.md`.

- **Path:** `graphiti_memory_client.py write` → Graphiti episode queue → entity/edge extraction → group-scoped graph. Legacy C1 path (`cursor_memory_client.py` → `save_memory` → SubstrateDAG → PostgreSQL/Neo4j/pgvector) is deprecated — do not use it for new writes.

**Write atomic memories — one fact per write, not one big blob.**
See `.cursor/rules/87-cursor-memory-kernel.mdc` → "Memory Write Format" for the full spec.

```bash
# One write per fact. Pre-classify with --kind. Terse, no preamble.
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py write \
  "{terse fact 1}" \
  --kind lesson --group-id {resolved_group_id}

python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py write \
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

### 3b. SESSION HOOKS TEARDOWN

If session hooks were activated at `/start-session`, close them now:

- Call `CursorSessionHooks.on_session_end(repo_id="l9", branch="main", promote=True)` to escalate high-confidence items to long-term memory
- This promotes recent decisions and errors-to-avoid into persistent storage
- Reference: `agents/cursor/cursor_session_hooks.py`

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
- PICKUP context + learnings written to Graphiti (or memory-bank fallback, if noted) ✅
- Redis session context saved (cache_set_session_context) ✅
- Next steps defined ✅
- GlobalCommands pushed to Cursor-Governance ✅

### When you open a new window
→ Use **/start-session** to load Redis context + Graphiti/memory-bank and resume.
```

→ **Auto-chains to /extract-chat**
