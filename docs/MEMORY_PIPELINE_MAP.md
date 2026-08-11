# Memory Pipeline Map (live path SSOT)

Canonical narrative for agent episodic memory in Quantum-L9 coding workspaces.
Authority: CANONICAL_LAW §2.1 / §8, ADR-0005, rules `03-graphiti-memory` + `87-cursor-memory-kernel`.

## One store

| Layer | Role |
|-------|------|
| Graphiti (VPS MCP) | Sole agent episodic SSOT |
| `ops/graphiti/graphiti_memory_client.py` | Cursor-primary front door |
| `ops/graphiti/hydration/` | sessionStart compile + sessionEnd close |
| Claude `environment/claude-code/memory/` | Thin adapter only (no second brain) |
| `memory-bank/` | Deprecated / archival — never resume SSOT |
| PE Graphiti projection | Observability only — never write authority |

## Normal session lifecycle (no `/end-session` required)

```text
sessionStart
  → resolve group_id from CURSOR_PROJECT_DIR
  → compile SessionHydrationPacket (PICKUP + facts)
  → emit additional_context with objective + next= + compact JSON
  → inject receipt for gates (fail-open if Graphiti down)

session work
  → atomic writes via CLI/bridge with required agent_id
  → source_description = agent={id};kind={kind}

sessionEnd (X-out / window_close / completed / aborted)
  → idempotent receipt under .l9/memory/closes/{session_id}.json
  → Phase A (≤8s): heuristic pickup_context + session_summary
  → Phase B (≤18s, if key + time): SessionSignalPacket → promote atomics
  → never raise hook timeout into silent “nothing written” without Phase A attempt
```

Entry points:

| Surface | Start | Close |
|---------|-------|-------|
| Cursor | `ops/hooks/session_start_memory_orchestrator.sh` | `ops/hooks/graphiti-session-end.sh` |
| Claude | `environment/claude-code/hooks/memory_prefetch.py` | `environment/claude-code/hooks/memory_writeback.py` |
| CLI | `python -m ops.graphiti.hydration.cli compile` | `… cli close` |

## Identity

| Surface | `L9_MEMORY_AGENT_ID` | `USER_ID` |
|---------|----------------------|-----------|
| Cursor | `cursor` | `cursor_agent` |
| Claude Code | `claude-code` | `claude_code_agent` |
| Bootstrap mirror | `bootstrap` | `bootstrap_agent` |

Every new episode must be searchable by `agent=` in `source_description` and stamped in the body envelope.

## `/end-session` — force-retry / offline recovery only

Normal closes are automatic. Use `/end-session` (skill `l9-end-session`) only when:

- sessionEnd hook failed or was skipped (offline, missing project dir)
- you need a richer manual PICKUP after a degraded close
- governance backup / Redis handoff must be forced interactively

Do not treat `/end-session` as required for every X-out.

## Budgets

| Knob | Default |
|------|---------|
| `MEMORY_HYDRATION_CHAR_BUDGET` | 4000 |
| `MEMORY_CLOSE_TRANSCRIPT_CHARS` | 12000 |
| sessionEnd Graphiti hook timeout | 30s (template) |
| Phase A / B | ≤8s / ≤18s |

T3 full-chat ingest remains **forbidden**.

## Schemas

- `ops/graphiti/hydration/session_hydration_packet.schema.yaml`
- `ops/graphiti/hydration/session_signal_packet.schema.yaml`
- `ops/graphiti/hydration/promotion_rules.yaml`

WIP packs under `WIP/World Model/` are design evidence only — not runtime SSOT.
