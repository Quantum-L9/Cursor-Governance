---
name: end-session
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

---

## EXECUTION

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
```

---

## RESUME AT NEXT SESSION

```bash
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py search "PICKUP|" --limit 3
```

Handled automatically by `/start-session`.

--- End Command ---
