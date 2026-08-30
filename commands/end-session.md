---
name: end-session
description: Force-retry Graphiti PICKUP write when auto sessionEnd failed or hydrate printed REPAIR
---

# /end-session — Force-retry / offline recovery

**Normal X-out does not need this command.** `sessionEnd` →
`graphiti-session-end.sh` → Phase A/B close writes PICKUP automatically.
See [`docs/MEMORY_PIPELINE_MAP.md`](../docs/MEMORY_PIPELINE_MAP.md) and
[ADR-0028](../docs/decisions/ADR-0028-session-hydrate-close-visibility.md).

## Agent preload (required)

1. Load [`skills/l9-end-session/SKILL.md`](../skills/l9-end-session/SKILL.md)
2. Load [`skills/l9-graphiti-memory/SKILL.md`](../skills/l9-graphiti-memory/SKILL.md)
3. Execute Graphiti **only** via governance `.venv` — never bare `python3`
4. Never pass `--scope`; always stamp `--agent-id` / `L9_MEMORY_AGENT_ID`

## WHEN TO USE

- SessionStart printed `DEGRADED` + `REPAIR: /end-session`
- Auto-close hook failed / Graphiti was offline
- Richer manual PICKUP after a thin Phase A close
- Force governance backup / Redis handoff interactively

## WHAT IT DOES (recovery)

1. **PICKUP context** — `graphiti_memory_client.py write --kind pickup_context`
   or `hydration.cli repair-write` (same write + receipt stamp)
2. **Lessons / errors** — atomic writes with `--agent-id`
3. **Governance backup** — push SSOT when requested
4. **Confirmation** — closed-session summary

Do **not** prefer `hydration.cli close` as the repair (ADR-0028).

## EXECUTION

### Phase 1 — PICKUP CONTEXT (primary = client write)

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
"$GRAPHITI_PY" "$GOV/ops/graphiti/graphiti_memory_client.py" health
cd "$GOV" && PYTHONPATH="$GOV" "$GRAPHITI_PY" -m ops.graphiti.hydration.cli repair-write \
  --project-dir "$WS" \
  --session-id "$REPAIR_SID" \
  --objective "{TASK}" --next "{NEXT}" --agent-id cursor
```

Do **not** substitute `graphiti_memory_client.py write` for this step. That path
creates a PICKUP episode and never calls `write_receipt`, so hydrate still
classifies a close-gap. `repair-write` is the only documented repair.

Skip if the close receipt is already `closed` and `write_count>0` unless
superseding. Do **not** write `memory-bank/`.

### Phase 2 — LESSONS & ERRORS (optional)

```bash
"$GRAPHITI_PY" "$GOV/ops/graphiti/graphiti_memory_client.py" write \
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

PICKUP task / next / outcome, lesson count, git branch, backup status.
