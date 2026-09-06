# Memory Pipeline Map (live path SSOT)

Canonical narrative for agent episodic memory in Quantum-L9 coding workspaces.
Authority: CANONICAL_LAW §2.1 / §8 / §8.2, ADR-0005, ADR-0028, ADR-0030, rules `03-graphiti-memory` + `87-cursor-memory-kernel`.

**Updated 2026-09-06 (realignment C11/C12):** the store is the canonical `l9-graphite-memory` control plane; Graphiti is a projection memory owns. The direct provider client is a tombstone; every row below that once named it now names `ops/memory`.

## One store

| Layer | Role |
|-------|------|
| `l9-graphite-memory` MemoryService (`memory-control-plane/v1`) | Sole agent episodic SSOT; Graphiti is its projection |
| `ops/memory/control_plane_client.py` (`python -m ops.memory.cli`) | Cursor's only front door (INV-03); bound runtime per `ops/config/memory-binding.json` |
| `ops/graphiti/hydration/` | sessionStart compile + sessionEnd close |
| Claude `environment/agents/adapters/claude-code/memory/` | Thin adapter only (no second brain) |
| `memory-bank/` | **RETIRED** — do not scaffold/read/write; delete residual trees |
| `.l9/pr/` | `make pr` remediation handoff JSON (not memory) |
| PE Graphiti projection | Observability only — never write authority |

## Normal session lifecycle (no `/end-session` required)

```text
sessionStart
  → resolve repository identity + namespace hints (ops/memory/namespace_context.py)
  → write open latch (.l9/memory/opens + rotate previous_opened / last_opened)
  → canonical_hydrate: health → hydrate → typed ContinuationCapsuleV2 (stale loses to git)
  → compile SessionHydrationPacket (continuation + context sections + close-gap check)
  → if prior session missing receipt / write_count=0 / no session PICKUP:
      lead additional_context with DEGRADED + REPAIR: /end-session (ADR-0028)
  → emit additional_context with objective + next= + compact JSON
  → canonical session state for the hydration-only gates (fail-open if memory down)

session work
  → atomic T2 writes via `python -m ops.memory.cli write --kind lesson|insight|decision`
  → every write is a canonical receipt (admitted / duplicate / rejected / quarantined)

sessionEnd (X-out / window_close / completed / aborted)
  → Phase A/B via close_session.py: capsule → governed candidate → memory.close (idempotent)
  → local obligation under .l9/memory/closes/ (authority: none); no provider fallback
  → stderr ERROR on skip/fail; enqueue failure still exit 2
  → idempotent receipt under .l9/memory/closes/{session_id}.json
    (latches only — not resume SSOT)
  → Phase A (≤8s): heuristic pickup_context + session_summary
  → Phase B (≤18s, if key + time): SessionSignalPacket via fixed-host OpenAI
    helper (`ops/graphiti/hydration/openai_fixed_host.py`); ephemeral key from
    env or AWS SM `l9/OPENAI_API_KEY` (never long-lived in `graphiti.env`)
  → Enqueue redacted excerpt (≤12k) to S3 distill queue when
    `MEMORY_DISTILL_S3_BUCKET` is set — content-hash idempotent; enqueue
    failure is fail-loud (receipt + stderr). Rollback flags:
    `MEMORY_PHASE_B=0`, `MEMORY_DISTILL_ENQUEUE=0`
  → Archive **full chat words** (user/assistant text + timestamps, no sqlite/tools)
    to S3 `L9_CHAT_TRANSCRIPT_S3_BUCKET` / `l9-chat-transcripts-020125249784`
    (`ops.graphiti.hydration.archive_transcript`, background from sessionEnd)
  → never raise hook timeout into silent “nothing written” without Phase A attempt

Batch catch-up (no Mac awake at cron time)
  → GitHub Actions `.github/workflows/memory-distill.yml` (schedule + dispatch)
  → pull pending S3 jobs → OpenAI distill → canonical ingest (ops/memory control plane)
  → Mac LaunchAgent `com.l9.transcript-distiller` / Dropbox / C1 `save_memory`
    are RETIRED (see `ops/scripts/RETIRED_transcript_distiller_launchagent.md`)
```

Entry points:

| Surface | Start | Close |
|---------|-------|-------|
| Cursor | `ops/hooks/session_start_memory_orchestrator.sh` | `ops/hooks/graphiti-session-end.sh` |
| Claude | `environment/agents/adapters/claude-code/hooks/memory_prefetch.py` | `environment/agents/adapters/claude-code/hooks/memory_writeback.py` |
| CLI | `python -m ops.graphiti.hydration.cli compile` | `… cli close` |

## Identity

| Surface | `L9_MEMORY_AGENT_ID` | `USER_ID` |
|---------|----------------------|-----------|
| Cursor | `cursor` | `cursor_agent` |
| Claude Code | `claude-code` | `claude_code_agent` |
| Bootstrap mirror | `bootstrap` | `bootstrap_agent` |

Every new episode must be searchable by `agent=` in `source_description` and stamped in the body envelope.

## `/end-session` — force-retry / offline recovery only

Normal closes are automatic. Use `/end-session` (skill `l9-end-session`) when
SessionStart prints `REPAIR: /end-session`, or:

- sessionEnd hook failed or was skipped (offline, missing project dir)
- you need a richer manual PICKUP after a degraded close
- governance backup / Redis handoff must be forced interactively

**Primary repair** is `hydration.cli repair-write` (canonical write + receipt stamp).
Do not prefer `hydration.cli close`; there is no provider `write` fallback (C11).
Do not treat `/end-session` as required for every X-out. See ADR-0028.

## Budgets

| Knob | Default |
|------|---------|
| `MEMORY_HYDRATION_CHAR_BUDGET` | 4000 |
| `MEMORY_CLOSE_TRANSCRIPT_CHARS` | 12000 |
| sessionEnd Graphiti hook timeout | 30s (template) |
| Phase A / B | ≤8s / ≤18s |
| `MEMORY_PHASE_B` | `1` (set `0` to skip sync distill) |
| `MEMORY_DISTILL_ENQUEUE` | `1` when bucket set (set `0` to skip S3) |
| `MEMORY_DISTILL_S3_BUCKET` | unset = enqueue skipped (warn) |
| `MEMORY_DISTILL_S3_PREFIX` | `distill-queue/pending/` |
| `MEMORY_DISTILL_TOKEN_BUDGET` | 300 |

T3 full-chat ingest remains **forbidden** — redacted excerpts only.

## Schemas

- `ops/graphiti/hydration/session_hydration_packet.schema.yaml`
- `ops/graphiti/hydration/session_signal_packet.schema.yaml`
- `ops/graphiti/hydration/promotion_rules.yaml`
- `ops/graphiti/distill_queue/schema.yaml`

WIP packs under `WIP/World Model/` are design evidence only — not runtime SSOT.
