---
name: l9-end-session
description: force-retry session close — Graphiti write PICKUP/learnings when auto sessionEnd failed or hydrate printed REPAIR. use for recovery, richer handoff, or governance backup — not required for normal X-out.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, session, handoff, memory, governance, graphiti, force-retry]
  owner: igor_beylin
  status: active
  version: 1.6.0
  updated: 2026-08-30
---

# End Session (force-retry / offline recovery)

## Purpose

**Normal closes are automatic.** Cursor `sessionEnd` runs
`ops/hooks/graphiti-session-end.sh` → `ops/graphiti/hydration/close_session.py`.
You should **not** need this skill for a routine X-out.

Use `/end-session` when SessionStart prints `DEGRADED` + `REPAIR: /end-session`,
or the auto-close hook failed / Graphiti was offline, or you need a richer
manual PICKUP. See ADR-0028.

Map: [`docs/MEMORY_PIPELINE_MAP.md`](../../docs/MEMORY_PIPELINE_MAP.md).

## Mandatory preload

Before any Graphiti CLI call, **load and follow** [`l9-graphiti-memory`](../l9-graphiti-memory/SKILL.md):

- Use governance **`.venv` Python** (`GRAPHITI_PY`), never bare `python3`.
- `write` accepts `--kind`, `--group-id`, `--agent-id`, `--dry-run` — **never** `--scope`.
- Stamp `L9_MEMORY_AGENT_ID=cursor` (or `--agent-id cursor`).

Slash command entry: [`commands/end-session.md`](../../commands/end-session.md).

## Core Contract (recovery path)

`HEALTH → client write PICKUP/lessons (agent_id) → stamp close receipt → REDIS (optional) → GOVERNANCE BACKUP → HANDOFF`

**Primary** is `graphiti_memory_client.py write` (or `hydration.cli repair-write`,
which is the same write + receipt stamp). Do **not** prefer
`hydration.cli close --reason force_retry` — that replays the hook closer
(ADR-0028 Option C rejected).

```bash
GOV="${HOME}/.cursor-governance"
GRAPHITI_PY="${GOV}/.venv/bin/python"
CLIENT="${GOV}/ops/graphiti/graphiti_memory_client.py"
export L9_MEMORY_AGENT_ID=cursor USER_ID=cursor_agent
"$GRAPHITI_PY" "$CLIENT" health
cd "$GOV" && PYTHONPATH="$GOV" "$GRAPHITI_PY" -m ops.graphiti.hydration.cli repair-write \
  --project-dir "$(pwd)" --session-id "${CURSOR_CONVERSATION_ID:-manual}" \
  --objective "{TASK}" --next "{NEXT}" --files "{FILES}" --blocker "{BLOCKER}" \
  --agent-id cursor
```

Equivalent primary write (same store):

```bash
"$GRAPHITI_PY" "$CLIENT" write \
  "PICKUP|date=$(date +%Y-%m-%d)|task={TASK}|next={NEXT}|blocker={BLOCKER}|session=${CURSOR_CONVERSATION_ID}" \
  --kind pickup_context --agent-id cursor
"$GRAPHITI_PY" "$CLIENT" write "{terse fact}" --kind lesson --agent-id cursor
```

`repair-write` skips a duplicate PICKUP when the close receipt is already
`closed` and `write_count>0`, unless `--supersede`.

`hydration.cli close` remains the **hook** closer only — not the preferred repair.

## Authority Order

1. ADR-0028 — hydrate/close visibility and write-primary repair
2. `docs/MEMORY_PIPELINE_MAP.md` — live hydrate/close path
3. `ops/graphiti/hydration/pickup_write.py` — repair / fallback writes
4. `ops/graphiti/hydration/close_session.py` — automatic hook closer
5. [`l9-graphiti-memory`](../l9-graphiti-memory/SKILL.md) — venv + CLI flags
6. `ops/scripts/backup_to_github.sh` — governance backup

## Compact Workflow

1. Confirm close-gap (hydrate `REPAIR: /end-session`, missing receipt, or `write_count=0`).
2. HEALTH, then `repair-write` or `graphiti_memory_client.py write` with `--agent-id`.
3. Optional Redis `cache_set_session_context`; else PICKUP is resume SSOT.
4. Run governance backup if needed.
5. Emit handoff summary (completed / in-progress / next).

## Resource Map

- [`../../docs/decisions/ADR-0028-session-hydrate-close-visibility.md`](../../docs/decisions/ADR-0028-session-hydrate-close-visibility.md)
- [`../../docs/MEMORY_PIPELINE_MAP.md`](../../docs/MEMORY_PIPELINE_MAP.md)
- [`../l9-graphiti-memory/SKILL.md`](../l9-graphiti-memory/SKILL.md)
- [`../../commands/end-session.md`](../../commands/end-session.md)
- `ops/hooks/graphiti-session-end.sh` — automatic primary close
- `ops/graphiti/hydration/` — compile / close / latches / repair-write

## Failure Handling

| Symptom | Action |
|---------|--------|
| Receipt already `closed` + `write_count>0` | Skip duplicate unless `--supersede` |
| `No module named 'yaml'` | Use `$GOV/.venv/bin/python` |
| `missing agent_id` | Export `L9_MEMORY_AGENT_ID` or pass `--agent-id` |
| Graphiti down | Warn; continue backup/handoff — no memory-bank |

When blocked: state exact gap, label `Unknown`, give smallest next action.
