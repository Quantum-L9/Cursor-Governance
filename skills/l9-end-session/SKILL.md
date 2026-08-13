---
name: l9-end-session
description: force-retry session close — manual PICKUP/learnings when auto sessionEnd failed or offline. use for recovery, richer handoff, or governance backup — not required for normal X-out.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, session, handoff, memory, governance, graphiti, force-retry]
  owner: igor_beylin
  status: active
  version: 1.5.0
  updated: 2026-08-11
---

# End Session (force-retry / offline recovery)

## Purpose

**Normal closes are automatic.** Cursor `sessionEnd` runs
`ops/hooks/graphiti-session-end.sh` → `ops/graphiti/hydration/close_session.py`
(Phase A heuristic PICKUP ≤8s, Phase B distill ≤18s). You should **not** need
this skill for a routine X-out / window close.

Use `/end-session` only when:

- the auto-close hook failed, was skipped, or Graphiti was offline
- you need a richer manual PICKUP after a degraded Phase A-only close
- you must force governance backup / Redis handoff interactively

Map: [`docs/MEMORY_PIPELINE_MAP.md`](../../docs/MEMORY_PIPELINE_MAP.md).

## Mandatory preload

Before any Graphiti CLI call, **load and follow** [`l9-graphiti-memory`](../l9-graphiti-memory/SKILL.md):

- Use governance **`.venv` Python** (`GRAPHITI_PY`), never bare `python3`.
- `write` accepts `--kind`, `--group-id`, `--agent-id`, `--dry-run` — **never** `--scope`.
- Stamp `L9_MEMORY_AGENT_ID=cursor` (or `--agent-id cursor`).

Slash command entry: [`commands/end-session.md`](../../commands/end-session.md).

## Core Contract (recovery path)

`HEALTH → PICKUP + atomics (agent_id) → REDIS (optional) → GOVERNANCE BACKUP → HANDOFF`

Prefer the shared closer when possible:

```bash
GOV="${HOME}/.cursor-governance"
GRAPHITI_PY="${GOV}/.venv/bin/python"
export L9_MEMORY_AGENT_ID=cursor USER_ID=cursor_agent
cd "$GOV" && PYTHONPATH="$GOV" "$GRAPHITI_PY" -m ops.graphiti.hydration.cli close \
  --project-dir "$(pwd)" --session-id "${CURSOR_CONVERSATION_ID:-manual}" \
  --reason force_retry --agent-id cursor
```

Manual writes (if CLI close unavailable):

```bash
"$GRAPHITI_PY" "$GOV/ops/graphiti/graphiti_memory_client.py" health
"$GRAPHITI_PY" "$GOV/ops/graphiti/graphiti_memory_client.py" write \
  "PICKUP|date=$(date +%Y-%m-%d)|task={TASK}|next={NEXT}|blocker={BLOCKER}" \
  --kind pickup_context --agent-id cursor
"$GRAPHITI_PY" "$GOV/ops/graphiti/graphiti_memory_client.py" write "{terse fact}" \
  --kind lesson --agent-id cursor
```

## Authority Order

1. `docs/MEMORY_PIPELINE_MAP.md` — live hydrate/close path
2. `ops/graphiti/hydration/close_session.py` — automatic closer (primary)
3. `.cursor/rules/87-cursor-memory-kernel.mdc` — kinds + identity
4. [`l9-graphiti-memory`](../l9-graphiti-memory/SKILL.md) — venv + CLI flags
5. [`references/end-session-protocol.md`](references/end-session-protocol.md) — step-by-step recovery
6. `ops/scripts/backup_to_github.sh` — governance backup

## Compact Workflow

1. Confirm auto-close receipt missing or degraded (`.l9/memory/closes/` or Graphiti search).
2. Run shared `hydration.cli close` or manual PICKUP + atomic writes with `--agent-id`.
3. Optional Redis `cache_set_session_context`; else PICKUP is resume SSOT.
4. Run governance backup if needed.
5. Emit handoff summary (completed / in-progress / next).

## Resource Map

- [`../../docs/MEMORY_PIPELINE_MAP.md`](../../docs/MEMORY_PIPELINE_MAP.md)
- [`../l9-graphiti-memory/SKILL.md`](../l9-graphiti-memory/SKILL.md)
- [`references/end-session-protocol.md`](references/end-session-protocol.md)
- [`../../commands/end-session.md`](../../commands/end-session.md)
- `ops/hooks/graphiti-session-end.sh` — automatic primary close
- `ops/graphiti/hydration/` — shared compile/close library

## Failure Handling

| Symptom | Action |
|---------|--------|
| Auto-close already wrote PICKUP | Skip duplicate unless superseding with richer next= |
| `No module named 'yaml'` | Use `$GOV/.venv/bin/python` |
| `missing agent_id` | Export `L9_MEMORY_AGENT_ID` or pass `--agent-id` |
| Graphiti down | Warn; continue backup/handoff — no memory-bank |

When blocked: state exact gap, label `Unknown`, give smallest next action.
