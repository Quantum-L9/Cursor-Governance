---
name: end-session
description: Force-retry ContinuationCapsuleV2 close when auto sessionEnd failed or hydrate printed REPAIR
---

# /end-session — Force-retry / offline recovery

**Normal X-out does not need this command.** `sessionEnd` →
`graphiti-session-end.sh` → Phase A/B close writes the continuation capsule automatically.
See [`docs/MEMORY_PIPELINE_MAP.md`](../docs/MEMORY_PIPELINE_MAP.md) and
[ADR-0028](../docs/decisions/ADR-0028-session-hydrate-close-visibility.md).

## Agent preload (required)

1. Load [`skills/l9-end-session/SKILL.md`](../skills/l9-end-session/SKILL.md)
2. Load [`skills/l9-graphiti-memory/SKILL.md`](../skills/l9-graphiti-memory/SKILL.md)
3. Execute memory **only** via governance `.venv` (`python -m ops.memory.cli` / `hydration.cli`) — never bare `python3`
4. Never pass `--scope`; always stamp `--agent-id` / `L9_MEMORY_AGENT_ID`

## WHEN TO USE

- SessionStart printed `DEGRADED` + `REPAIR: /end-session`
- Auto-close hook failed / canonical memory was unbound
- Richer manual continuation after a thin Phase A close
- Force governance backup / Redis handoff interactively

## WHAT IT DOES (recovery)

1. **Continuation** — `hydration.cli repair-write` (canonical write + receipt stamp).
   Do not prefer `ops.memory.cli write --kind pickup_context` for this step.
2. **Lessons / errors** — atomic writes with `--agent-id`
3. **Governance backup** — push SSOT when requested
4. **Confirmation** — closed-session summary

Do **not** prefer `hydration.cli close` as the repair (ADR-0028).

## EXECUTION

### Phase 1 — CONTINUATION (primary = repair-write)

```bash
GOV="${HOME}/.cursor-governance"
GRAPHITI_PY="${GOV}/.venv/bin/python"
WS="${CURSOR_PROJECT_DIR:-$(pwd)}"
export L9_MEMORY_AGENT_ID=cursor USER_ID=cursor_agent
PRIOR_FILE="$WS/.l9/memory/previous_opened.json"
REPAIR_SID=""
if [ -f "$PRIOR_FILE" ]; then
  REPAIR_SID="$("$GRAPHITI_PY" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("session_id") or "")' "$PRIOR_FILE")"
fi
REPAIR_SID="${REPAIR_SID:-${CURSOR_CONVERSATION_ID:-manual}}"
memcli health
cd "$GOV" && PYTHONPATH="$GOV" "$GRAPHITI_PY" -m ops.graphiti.hydration.cli repair-write \
  --project-dir "$WS" \
  --session-id "$REPAIR_SID" \
  --objective "{TASK}" --next "{NEXT}" --agent-id cursor
```

Do **not** substitute `ops.memory.cli write` for this step. That path
creates a pickup-class episode and never calls `write_receipt`, so hydrate still
classifies a close-gap. `repair-write` is the only documented repair.

Skip if the close receipt is already `closed` and `write_count>0` unless
superseding. Do **not** write `memory-bank/`.

### Phase 2 — LESSONS & ERRORS (optional)

```bash
memcli write \
  "LESSON|topic={TOPIC}|learned={LEARNED}|context={CONTEXT}" --kind lesson --agent-id cursor
```

### Phase 3 — GIT STATE (auto)

Surface uncommitted count; do not auto-commit foreign paths.

### Phase 4 — GOVERNANCE GITHUB BACKUP (required)

```bash
bash "${GOV}/ops/scripts/backup_to_github.sh" \
  "chore(governance): end-session $(date +%Y-%m-%d)"
```

Skip only with `GOVERNANCE_BACKUP_SKIP=1`.

### Phase 5 — CONFIRMATION

Continuation task / next / outcome, lesson count, git branch, backup status.
