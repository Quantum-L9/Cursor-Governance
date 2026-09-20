---
name: l9-end-session
description: force-retry session close — canonical repair-write of the continuation record plus governed learning writes when auto sessionEnd failed or hydrate printed REPAIR. use for recovery, richer handoff, or governance backup — not required for normal X-out.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, session, handoff, memory, governance, control-plane, force-retry]
  owner: igor_beylin
  status: active
  version: 1.7.1
  updated: 2026-09-07
---

# End Session (force-retry / offline recovery)

## Purpose

**Normal closes are automatic.** Cursor `sessionEnd` runs
`ops/hooks/graphiti-session-end.sh` → `ops/graphiti/hydration/close_session.py`.
You should **not** need this skill for a routine X-out.

Use `/end-session` when SessionStart prints `CLOSE_GAP` + `REPAIR: /end-session`,
or the auto-close hook failed, or you need a richer manual continuation
record. A close-gap is a **lifecycle** condition, not memory degradation
(ADR-0032): `DEGRADED` means canonical memory did not answer, and
`ENVIRONMENT_FAULT` means the memory runtime was never bound — repair those
with `make memory-readiness`, not with this skill. See ADR-0028 (as amended
2026-09-07), ADR-0030 and ADR-0032.

Map: [`docs/MEMORY_PIPELINE_MAP.md`](../../docs/MEMORY_PIPELINE_MAP.md).

## Mandatory preload

Before any memory CLI call, **load and follow** [`l9-graphiti-memory`](../l9-graphiti-memory/SKILL.md):

- Use governance **`.venv` Python** (`GRAPHITI_PY`), never bare `python3`.
- `write` accepts `--kind`, `--group-id`, `--agent-id`, `--dry-run` — **never** `--scope`.
- Stamp `L9_MEMORY_AGENT_ID=cursor` (or `--agent-id cursor`).
- The repair is a **deterministic adapter** (`hydration.cli repair-write`);
  model-authored learnings are MCP writes on the `l9-graphite-memory` server:
  ordinary / cold lessons use `memory.write_agent` (no `phase_lock`), and
  conflict-sensitive facts use `memory.phase_lock` → `memory.write_governed`
  (ADR-0031, CANONICAL_LAW §8.5). Neither reaches a provider; all admit
  through the same `MemoryService`.

Slash command entry: [`commands/end-session.md`](../../commands/end-session.md).

## Core Contract (recovery path)

`HEALTH → repair-write (continuation record + receipt) → optional governed lesson writes → REDIS (optional) → GOVERNANCE BACKUP → HANDOFF`

**Primary** is `hydration.cli repair-write` (canonical continuation write +
`write_receipt`). A bare `ops.memory.cli write` does **not** stamp the close
receipt and is not the close-gap repair. Do **not** prefer
`hydration.cli close --reason force_retry` — that replays the hook closer
(ADR-0028 Option C rejected). Repair the **prior** session from
`previous_opened.json` when SessionStart reported a close-gap.

```bash
GOV="${HOME}/.cursor-governance"
GRAPHITI_PY="${GOV}/.venv/bin/python"
memcli() { (cd "$GOV" && PYTHONPATH="$GOV" "$GRAPHITI_PY" -m ops.memory.cli "$@" --workspace "${WS:-$PWD}"); }  # canonical control plane (C11)
WS="${CURSOR_PROJECT_DIR:-$(pwd)}"
PRIOR_FILE="$WS/.l9/memory/previous_opened.json"
REPAIR_SID=""
if [ -f "$PRIOR_FILE" ]; then
  REPAIR_SID="$("$GRAPHITI_PY" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("session_id") or "")' "$PRIOR_FILE")"
fi
REPAIR_SID="${REPAIR_SID:-${CURSOR_CONVERSATION_ID:-manual}}"
export L9_MEMORY_AGENT_ID=cursor USER_ID=cursor_agent
memcli health
cd "$GOV" && PYTHONPATH="$GOV" "$GRAPHITI_PY" -m ops.graphiti.hydration.cli repair-write \
  --project-dir "$WS" --session-id "$REPAIR_SID" \
  --objective "{TASK}" --next "{NEXT}" --files "{FILES}" --blocker "{BLOCKER}" \
  --agent-id cursor
```

Optional lesson writes after `repair-write` (same store; these do not stamp a
close receipt). Model-authored facts are MCP writes on the `l9-graphite-memory`
server; `memcli write` is the human-operator form only. An ordinary / cold
lesson is `memory.write_agent`; a conflict-sensitive fact takes the lock first
(ADR-0031, CANONICAL_LAW §8.5):

```text
memory.write_agent     {namespace: "<memcli resolve write hint>", content: "{terse fact}", memory_class: "lesson", tags: ["agent:cursor"]}
memory.phase_lock      {namespace: "<memcli resolve write hint>", task_signature: "end-session:<session_id>"}   # conflict-sensitive only
memory.write_governed  {namespace, content: "{terse fact}", task_signature: "end-session:<session_id>", memory_class: "lesson", tags: ["agent:cursor"]}
```

`repair-write` skips a duplicate continuation record when the close receipt
is already `closed` and `write_count>0`, unless `--supersede`.

`hydration.cli close` remains the **hook** closer only — not the preferred repair.

## Authority Order

1. ADR-0030 — memory control plane is the single front door (interactive write contract, items 7–9)
2. ADR-0028 (amended 2026-09-07) — hydrate/close visibility and canonical repair
3. `docs/MEMORY_PIPELINE_MAP.md` — live hydrate/close path
4. `ops/graphiti/hydration/pickup_write.py` — canonical repair writes (`repair_close`)
5. `ops/graphiti/hydration/close_session.py` — automatic hook closer
6. [`l9-graphiti-memory`](../l9-graphiti-memory/SKILL.md) — venv + CLI flags + governed write
7. `ops/scripts/backup_to_github.sh` — governance backup

## Compact Workflow

1. Confirm close-gap (hydrate `CLOSE_GAP` + `REPAIR: /end-session`, `close_gap_reason`, missing receipt, or `write_count=0`).
2. HEALTH, then `repair-write` targeting the prior session id. Do not use client `write` as the close-gap repair.
3. Optional Redis `cache_set_session_context`; the canonical continuation record (`ContinuationCapsuleV2`) is the resume SSOT either way.
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
| Memory runtime unbound (`readiness` R0 fails / `BINDING_FAILED`) | `make -C "$GOV" memory-binding`; warn; continue backup/handoff — no memory-bank, no provider write |

When blocked: state exact gap, label `Unknown`, give smallest next action.
