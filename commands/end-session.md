---
name: end-session
<<<<<<< Updated upstream
version: "2.1.0"
description: "Close Cursor session — structured handoff, memory write, Redis resume context, governance backup"
auto_chain: extract-chat
---

# /end-session — Session Shutdown

## WHAT IT DOES

Structured close-out so the next window resumes with zero amnesia:

1. **PICKUP context** — write a structured handoff packet (Graphiti T1 primary, memory-bank T0 fallback only)
2. **Lessons / errors** — capture anything non-obvious learned this session (optional)
3. **Git state** — capture uncommitted work so it isn't silently lost
4. **Governance backup** — push `.cursor-commands` (GlobalCommands) SSOT to `Quantum-L9/Cursor-Governance`
5. **Confirmation** — print a closed-session summary

Full protocol spec: [`end-session.yaml`](../end-session.yaml) (v2.1). Skill entry point: [`skills/l9-end-session/SKILL.md`](../skills/l9-end-session/SKILL.md).
=======
version: "1.0.0"
description: "Close session — save context, create handoff"
auto_chain: extract-chat
---

# /end-session — Session Close

## WHAT IT DOES

Clean session close:

1. Update workflow_state.md
2. Extract learnings to memory (via canonical pipeline; see `docs/MEMORY_PIPELINE_MAP.md`)
3. Create handoff summary
4. List next steps
5. **Backup GlobalCommands to GitHub** (`cryptoxdog/Cursor-Governance`)
>>>>>>> Stashed changes

---

## EXECUTION

<<<<<<< Updated upstream
### Phase 1 — PICKUP CONTEXT (required)

Primary path — Graphiti (T1, canonical):

```bash
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py health
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py write \
  "PICKUP|date={DATE}|task={TASK}|files={FILES}|next={NEXT}|blocker={BLOCKER}|gmps={GMPS}|outcome={OUTCOME}" \
  --kind pickup_context
```

Fallback ONLY if the health check fails or the write errors — never write both for the same session. Target is always `$CURSOR_PROJECT_DIR/memory-bank/` (the open workspace repo), never `$GLOBAL_COMMANDS`:

```bash
# APPEND (never overwrite) a dated PICKUP section to memory-bank/activeContext.md
```

Before relying on `memory-bank/` being trackable in the target repo, check it isn't gitignored:

```bash
git -C "$CURSOR_PROJECT_DIR" check-ignore -q memory-bank/activeContext.md && \
  echo "gitignored — add '!/memory-bank/' and '!/memory-bank/**' to that repo's .gitignore"
```

### Phase 2 — LESSONS & ERRORS (optional — only if something non-obvious happened)

```bash
python3 agents/cursor/cursor_memory_client.py write \
  "LESSON|topic={TOPIC}|learned={LEARNED}|context={CONTEXT}" --kind lesson
python3 agents/cursor/cursor_memory_client.py write \
  "ERROR|type={TYPE}|cause={CAUSE}|fix={FIX}" --kind error
```

### Phase 3 — GIT STATE (auto)

```bash
BRANCH=$(git branch --show-current)
COMMIT=$(git log -1 --format="%h %s")
UNCOMMITTED=$(git status --short | wc -l | tr -d ' ')
```

If `UNCOMMITTED > 0`, surface it in the confirmation output and ask whether to commit before closing.

### Phase 4 — GOVERNANCE GITHUB BACKUP (required)

```bash
bash .cursor-commands/ops/scripts/backup_to_github.sh \
  "chore(governance): end-session $(date +%Y-%m-%d)"
```

Verify:

```bash
tail -5 "$HOME/.cursor-governance/backup.log"
gh api repos/Quantum-L9/Cursor-Governance/commits --jq '.[0].sha'
```

Skip only with `GOVERNANCE_BACKUP_SKIP=1`.

### Phase 5 — CONFIRMATION (auto)

```markdown
## ✅ SESSION CLOSED — HANDOFF COMPLETE

📦 PICKUP: {task} | next={next_action} | outcome={outcome}
📝 Lessons: {lesson_count} | 🔧 Errors: {error_count}
📂 Git: {branch} @ {commit} — {uncommitted_count} uncommitted file(s)
🔒 Governance backup: pushed / nothing to commit
=======
### 1. UPDATE WORKFLOW STATE

**Use the workflow state script** to append to Recent Sessions (7-day window):

```bash
python3 scripts/workflow/update_workflow_state.py end-session --summary "{summary of work done}"
```

Example:
```bash
python3 scripts/workflow/update_workflow_state.py end-session --summary "Executed /end-session (workflow_state + memory write). Handoff + extract-chat chained."
```

Then, if needed, update **Next Steps** in `workflow_state.md` (add or adjust items under `## Next Steps (Next Session)`).

### 2. EXTRACT LEARNINGS (canonical memory pipeline)

Session learnings MUST be written through the **canonical memory path** so they get governance, audit, DAG (packet_store → graph_sync → semantic_embed → insights), and persistence. See `docs/MEMORY_PIPELINE_MAP.md`.

- **Path:** `cursor_memory_client.py write` → MCP `save_memory` → main pipeline (`write_packet` → SubstrateDAG) → PostgreSQL + Neo4j + pgvector.

**Write atomic memories — one fact per write, not one big blob.**
See `.cursor/rules/87-cursor-memory-kernel.mdc` → "Memory Write Format" for the full spec.

```bash
# One write per fact. Pre-classify with --kind. Terse, no preamble.
python3 agents/cursor/cursor_memory_client.py write \
  "{terse fact 1}" \
  --kind lesson --scope cursor

python3 agents/cursor/cursor_memory_client.py write \
  "{terse fact 2}" \
  --kind insight --scope cursor
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
>>>>>>> Stashed changes
```

---

<<<<<<< Updated upstream
## RESUME AT NEXT SESSION

```bash
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py search "PICKUP|" --limit 3
```

Handled automatically by `/start-session`.
=======
## OUTPUT

```markdown
## 👋 SESSION CLOSED

### Summary
**Work completed:** {count} items
**Reports generated:** {list}

### Handoff
- workflow_state.md updated ✅
- Memory written ✅
- Redis session context saved (cache_set_session_context) ✅
- Next steps defined ✅
- GlobalCommands pushed to Cursor-Governance ✅

### When you open a new window
→ Use **/start-session** to load Redis context + workflow_state + memory and resume.
```

→ **Auto-chains to /extract-chat**
>>>>>>> Stashed changes

--- End Command ---
