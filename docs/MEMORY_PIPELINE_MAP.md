# Memory Pipeline Map (live path SSOT)

Canonical narrative for agent episodic memory in Quantum-L9 coding workspaces.
Authority: CANONICAL_LAW §2.1 / §8 / §8.2 / §8.5, ADR-0005, ADR-0028, ADR-0030, ADR-0031, rules `03-graphiti-memory` + `87-cursor-memory-kernel`.

**Updated 2026-09-06 (realignment C11/C12):** the store is the canonical `l9-graphite-memory` control plane; Graphiti is a projection memory owns. The direct provider client is a tombstone; every row below that once named it now names `ops/memory`.

**Updated 2026-09-07 (doctrine closure, CANONICAL_LAW §8.3, ADR-0030 items 7–9):** *(single-path write wording superseded 2026-09-13)* ONE authority (`MemoryService`), ONE canonical egress (`ops/memory`), two adapters (CLI, MCP). A model-initiated durable write is `memory.phase_lock` → `memory.write_governed` on the `l9-graphite-memory` MCP server; the CLI `write` is the operator / deterministic-adapter form. The phase-lock governs memory-write consistency only — never repository authority.

**Updated 2026-09-15 (ADR-0033, INV-03b — two lanes, one `MemoryService`):** agents are first-class real-time writers on the public `l9-memory` / MCP surface (`memory.write_agent` is the ordinary write; `phase_lock → write_governed` is optional, conflict-sensitive); Cursor-Governance never mediates or gates those writes. Automatic hooks use bounded write / distill / close through `ops/memory/control_plane_client.py`. Cursor-local memory cognition — Phase B OpenAI distill, `promotion_rules.yaml`, `resume_signal_scorer`, the S3 distill queue and its worker — is deleted (stage C15); the close hands the redacted excerpt to memory's own `l9-memory distill`. See "Lanes" below. The 2026-09-07 "A model-initiated durable write is `phase_lock → write_governed`" sentence is superseded.

**Updated 2026-09-13 (ADR-0031, CANONICAL_LAW §8.5 — dual write classes):** the model has two MCP writes on `l9-graphite-memory`. Ordinary / cold facts use `memory.write_agent` — no SessionStart receipt, no `phase_lock`. Conflict-sensitive facts use `memory.phase_lock` → `memory.write_governed`. `memory.ingest` and the CLI `write` are a bypass of neither. Agent HTTP stays sealed; identity is the shared agents door plus a signed `agent_id` assertion.

## One store

| Layer | Role |
|-------|------|
| `l9-graphite-memory` MemoryService (`memory-control-plane/v1`) | Sole agent episodic SSOT; Graphiti is its projection |
| `ops/memory/control_plane_client.py` (`python -m ops.memory.cli`) | The **hook lane** client (INV-03/03b): bound runtime per `ops/config/memory-binding.json`, per-surface envelope per `ops/config/memory-hook-envelopes.json`; operator / hook / deterministic-adapter CLI. Not a mandatory route for agents |
| `l9-graphite-memory` MCP server (stdio, package-owned; `make memory-mcp-install`) | The model's interactive adapter to the same MemoryService: `memory.search`, `memory.hydrate`, `memory.write_agent` (ordinary / cold), `memory.phase_lock` → `memory.write_governed` (conflict-sensitive) |
| `ops/graphiti/hydration/` | sessionStart compile + sessionEnd close (deterministic adapters) |
| Claude `environment/agents/adapters/claude-code/memory/` | Thin adapter only (no second brain); `memory-enforcement.contract.json` `interactive_memory_write` is the machine form of the write contract |
| `memory-bank/` | **RETIRED** — do not scaffold/read/write; delete residual trees |
| `.l9/pr/` | `make pr` remediation handoff JSON (not memory) |
| PE Graphiti projection | Observability only — never write authority |

## Lanes (ADR-0033, INV-03b)

```text
                         l9-graphiti-memory
          ┌──────────────── Agent lane ────────────────┐
 Agent ───┴─► memory.write_agent / MCP write ──────────┤   direct, ungated, immediately
 Agent ─────► handoff write (same call) ───────────────┤   visible to another agent's
 Agent ─────► search / hydrate ────────────────────────┤   hydrate / search
                                                       ▼
                                                 MemoryService
                                                       ▲
          ┌──────────────── Hook lane ─────────────────┤
 SessionStart/End ─► bounded write / close ────────────┤   same pipeline, narrower
 automatic hook ───► bounded distill ──────────────────┘   capability envelope
```

| Producer | Route | Authority |
|---|---|---|
| Agent explicit write | public `memory.write_agent` / MCP → `MemoryService` | memory-service contracts (principal, namespace grants, schema, admission) — not a Cursor-Governance wall |
| Agent real-time handoff | the same call | the same; no phase, receipt, close, PR or queue in front of it |
| Automatic hook | bounded write / distill / close via `MemoryControlPlaneClient` → `MemoryService` | constrained hook principal + envelope (`ops/config/memory-hook-envelopes.json`) |

Cursor-Governance gates **repository edits** on hydration (Claude `memory_gate` on `Edit|Write`, Cursor "edit-other"); it never gates a memory write. `memory_gate.py` exempts `l9-memory` / `python -m ops.memory.cli` from its `Bash` matcher the way it exempts git/gh.

## Write paths (caller taxonomy)

| Caller | Path | Operation | Note |
|--------|------|-----------|------|
| Model, mid-session, ordinary / cold fact (lesson / insight / decision) | MCP `l9-graphite-memory` | `memory.write_agent` | ADR-0031 cold-safe model write: no SessionStart receipt, no `phase_lock`; a refused write is the verdict |
| Model, mid-session, conflict-sensitive fact (concurrent writers / namespace snapshot) | MCP `l9-graphite-memory` | `memory.phase_lock` → `memory.write_governed` | Lock = namespace-snapshot consistency precondition; refused lock/write is the verdict |
| sessionEnd hook | `close_session.py` → `ops/memory` | `ingest_candidate` → `memory.close` (idempotent) | Deterministic adapter |
| SessionStart hook | `canonical_hydrate` → `ops/memory` | `hydrate` | Read only |
| `/end-session` repair | `hydration.cli repair-write` → `ops/memory` | canonical `write` + close-receipt stamp | Deterministic adapter; not the model's lesson path |
| Legacy provider history | `legacy_reconciliation.py` | canonical admission, tag `legacy_unverified` | Operator |
| Human operator / Program Execution | `python -m ops.memory.cli write` | generic canonical write | Operator form — not a bypass of `write_agent` / `write_governed` for a model-authored fact |
| Anything | provider transport (`add_memory`-class tools, provider URL/bearer) | — | **Forbidden**; no surface holds one |

A memory phase-lock never authorizes a source edit, commit, push or publication (`rules/96` E7/E8/E10, `rules/98`).

## Normal session lifecycle (no `/end-session` required)

```text
sessionStart
  → resolve repository identity + namespace hints (ops/memory/namespace_context.py)
  → write open latch (.l9/memory/opens + rotate previous_opened / last_opened)
  → canonical_hydrate: health → hydrate → typed ContinuationCapsuleV2 (stale loses to git)
  → compile SessionHydrationPacket (continuation + context sections + close-gap check)
  → three typed conditions, never ORed (ADR-0032):
      environment_fault (BINDING_FAILED / NAMESPACE_UNRESOLVED — runtime never reached memory)
        → lead ENVIRONMENT_FAULT + REPAIR: make memory-readiness
      close_gap (prior session missing receipt / write_count=0 / no session continuation)
        → lead CLOSE_GAP + REPAIR: /end-session
      memory_degraded (canonical memory ran and did not answer)
        → lead DEGRADED; `degraded` mirrors this one field only
      continuation_stale is a fact on the capsule, not a condition (git wins)
  → emit additional_context with objective + next= + compact JSON
  → canonical session state for the hydration-only gates (fail-open if memory down)

session work
  → atomic T2 model writes on the `l9-graphite-memory` MCP server
    (`memory_class: lesson|insight|decision`, ADR-0031):
      ordinary / cold   → `memory.write_agent` (no phase_lock, no SessionStart receipt)
      conflict-sensitive → `memory.phase_lock` → `memory.write_governed`
  → every write is a canonical receipt (admitted / duplicate / rejected / quarantined)
  → operator CLI `python -m ops.memory.cli write` is the human / adapter form only

sessionEnd (X-out / window_close / completed / aborted)
  → Phase A via close_session.py: capsule → governed candidate → memory.close (idempotent)
  → local obligation under .l9/memory/closes/ (authority: none); no provider fallback
  → stderr ERROR on skip/fail; the close receipt carries the verdict (no exit-2 queue path)
  → idempotent receipt under .l9/memory/closes/{session_id}.json
    (latches only — not resume SSOT)
  → Phase A (≤8s): heuristic pickup_context + session_summary (capsule *input*, not cognition)
  → bounded distill (after the close, within the remaining ≤30s budget, ADR-0033):
    the already-redacted excerpt (≤12k) is written to .l9/memory/distill/<session>.excerpt.txt
    and handed to memory's own `l9-memory distill <path> --group-id <ns>`; extraction,
    admission and every record are MemoryService's. NO_HITS / REJECTED / failure never
    unmakes a canonical close. Kill switch: `L9_MEMORY_DISTILL=0`
  → RETIRED at C15: Phase B (fixed-host OpenAI SessionSignalPacket, promotion rules,
    resume-signal scorer) and the S3 distill queue + GHA worker. `closed_enqueue_failed`
    receipts still parse as closes; none is written
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
Learnings extracted during `/end-session` are model-authored facts and take the
MCP model write — `memory.write_agent` for an ordinary lesson, `memory.phase_lock`
→ `memory.write_governed` only when the fact is conflict-sensitive — not the
operator CLI. Do not treat `/end-session` as required for every X-out. See
ADR-0028 (amended 2026-09-07), ADR-0030 and ADR-0031.

## Budgets

| Knob | Default |
|------|---------|
| `MEMORY_HYDRATION_CHAR_BUDGET` | 4000 |
| `MEMORY_CLOSE_TRANSCRIPT_CHARS` | 12000 |
| sessionEnd Graphiti hook timeout | 30s (template) |
| Phase A / total close | ≤8s / ≤30s |
| `L9_MEMORY_DISTILL` | `1` (set `0` to skip the bounded canonical distill) |
| `L9_MEMORY_ENV_HEAL` | `1` (set `0` to skip the one-shot `.venv` heal on binding drift, ADR-0032) |

T3 full-chat ingest remains **forbidden** — redacted excerpts only.

## Schemas

- `ops/graphiti/hydration/session_hydration_packet.schema.yaml`
- `ops/config/memory-receipt-contract.json` (Cursor's view of memory's receipts, incl. `DistillationReceipt`)
- `ops/config/memory-hook-envelopes.json` (hook-lane capability envelopes)

WIP packs under `WIP/World Model/` are design evidence only — not runtime SSOT.
