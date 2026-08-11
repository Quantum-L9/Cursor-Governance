---
name: end-session
version: "2.3.0"
description: "Force-retry session close — manual PICKUP when auto sessionEnd failed; not required for normal X-out"
auto_chain: extract-chat
skill: l9-end-session
graphiti_skill: l9-graphiti-memory
---

# /end-session — Force-retry / offline recovery

**Normal X-out does not need this command.** `sessionEnd` →
`graphiti-session-end.sh` → Phase A/B close writes PICKUP automatically.
See [`docs/MEMORY_PIPELINE_MAP.md`](../docs/MEMORY_PIPELINE_MAP.md).

## Agent preload (required)

1. Load [`skills/l9-end-session/SKILL.md`](../skills/l9-end-session/SKILL.md)
2. Load [`skills/l9-graphiti-memory/SKILL.md`](../skills/l9-graphiti-memory/SKILL.md) for **venv Python** + CLI flags
3. Execute Graphiti **only** via governance `.venv` — never bare `python3`
4. Never pass `--scope`; always stamp `--agent-id` / `L9_MEMORY_AGENT_ID`

## WHEN TO USE

- Auto-close hook failed / Graphiti was offline
- Need a richer manual PICKUP after degraded Phase A
- Force governance backup / Redis handoff interactively

## WHAT IT DOES (recovery)

1. **PICKUP context** — via `hydration.cli close` or manual `--kind pickup_context`
2. **Lessons / errors** — atomic writes with `--agent-id`
3. **Governance backup** — push SSOT when requested
4. **Confirmation** — closed-session summary

Skill entry point: [`skills/l9-end-session/SKILL.md`](../skills/l9-end-session/SKILL.md).

---

## EXECUTION

### Phase 1 — PICKUP CONTEXT (force-retry)

Prefer shared closer (same as sessionEnd hook):

```bash
GOV="${HOME}/.cursor-governance"
GRAPHITI_PY="${GOV}/.venv/bin/python"
export L9_MEMORY_AGENT_ID=cursor USER_ID=cursor_agent
cd "$GOV" && PYTHONPATH="$GOV" "$GRAPHITI_PY" -m ops.graphiti.hydration.cli close \
  --project-dir "$CURSOR_PROJECT_DIR" \
  --session-id "${CURSOR_CONVERSATION_ID:-manual}" \
  --reason force_retry --agent-id cursor
```

Manual fallback:

```bash
CLIENT="${GOV}/ops/graphiti/graphiti_memory_client.py"
"$GRAPHITI_PY" "$CLIENT" write \
  "PICKUP|date={DATE}|task={TASK}|files={FILES}|next={NEXT}|blocker={BLOCKER}" \
  --kind pickup_context --agent-id cursor
```

Do **not** write `memory-bank/` (deprecated).

### Phase 2 — LESSONS & ERRORS (optional — only if something non-obvious happened)

Use the **same** Graphiti client (not deprecated `cursor_memory_client.py`):

```bash
"$GRAPHITI_PY" "$CLIENT" write \
  "LESSON|topic={TOPIC}|learned={LEARNED}|context={CONTEXT}" --kind lesson --agent-id cursor
"$GRAPHITI_PY" "$CLIENT" write \
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
bash "${GOV}/ops/scripts/backup_to_github.sh" \
  "chore(governance): end-session $(date +%Y-%m-%d)"
# or: bash .cursor-commands/ops/scripts/backup_to_github.sh "…"
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
```

---

## RESUME AT NEXT SESSION

```bash
"$GRAPHITI_PY" "$CLIENT" search "PICKUP|" --limit 3
```

Handled automatically by `/start-session`.

--- End Command ---
