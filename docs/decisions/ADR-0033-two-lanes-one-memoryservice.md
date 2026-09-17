# ADR-0033: Two lanes into one `MemoryService` — agents write directly, hooks write bounded, nothing writes around it

## Status

Accepted

## Date

2026-09-15

## Supersedes

- ADR-0030 items 7–9 where they name `memory.phase_lock → memory.write_governed`
  as *the* model write. That pair remains available as an optional,
  conflict-sensitive write. The ordinary agent write is `memory.write_agent`.
- The 2026-09-07 "Interactive memory write contract" sentence in `AGENTS.md`
  and `CANONICAL_LAW.md` §8.3 ("That is the only model write"). Both files are
  append-only; the superseding fragments are `MEMORY_TWO_LANES_V1`.

## Context

ADR-0030 made `MemoryService` (in `l9-graphiti-memory`) the only production
authority over canonical memory and moved Cursor-Governance behind
`ops/memory` (INV-03). What it did not settle was *who may call it, and how
directly*. Three things drifted in the year since:

1. **Cursor-Governance grew memory cognition of its own.** `close_session.py`
   ran a Phase B: an OpenAI extraction over the transcript, a local
   `resume_signal_scorer`, `promotion_rules.yaml`, and an S3 distill queue with
   an offline worker. Every one of those decided what memory *is* before memory
   saw it. They were deleted in this change (B1, B3).
2. **"One canonical egress" was being read as "all memory traffic goes
   through Cursor-Governance."** That reading turns `MemoryControlPlaneClient`
   into a mandatory toll booth and makes real-time agent handoff impossible: an
   agent's fact would only become visible to another agent after a session
   close, a distill, a PR gate, or a governance receipt.
3. **A Claude PreToolUse gate sat on the agent lane with no exemption.**
   `memory_gate.py` runs on every `Bash` call and fails closed: its
   `git-mutation` rule was the only shell pattern, but a widened pattern, an
   unreadable contract state, or a classify fault would deny whatever command
   was in flight — including `l9-memory write`, `python -m ops.memory.cli`,
   and the `memory_prefetch.py` repair the gate's own denial text tells the
   agent to run. `git`/`gh` had an explicit exemption for exactly that reason;
   memory did not. A hydration gate whose purpose is to protect repository
   edits must never be in a position to refuse the write that repairs memory.

The owner's intent (2026-09-15): one canonical service and persistence
pipeline; agents are first-class real-time producers on it; hooks are bounded
producers on it; Cursor-Governance owns *no* memory semantics and interposes
*no* authorization wall on agent-initiated writes.

## Decision — the key invariant (INV-03b)

> Agents are first-class real-time memory writers and may invoke the public
> `l9-memory` / MCP write surface directly; Cursor-Governance must not mediate
> or gate those writes. Automatic hooks use purpose-bounded write / distill /
> close operations with restricted hook principals. Both lanes converge
> directly on `MemoryService`; neither may access providers or persistence
> behind it.

```text
                         l9-graphiti-memory

          ┌──────────────── Agent lane ────────────────┐
          │                                            │
 Agent ───┴─► memory.write_agent / MCP write ──────────┤
 Agent ─────► handoff write (same call) ───────────────┤
 Agent ─────► search / hydrate ────────────────────────┤
                                                       ▼
                                                 MemoryService
                                                       │
                                               canonical state
                                                       ▲
          ┌──────────────── Hook lane ─────────────────┤
          │                                            │
 SessionStart/End ─► bounded write / close ────────────┤
 automatic hook ───► bounded distill ──────────────────┘
```

### Three producer classes

| Producer | Route | Authority |
|---|---|---|
| **Agent explicit write** | public `memory.write_agent` / MCP `write_agent` → `MemoryService` | normal agent memory authority: `MemoryPrincipal` identity, namespace grants, schema, admission — *memory-service* contracts, not a Cursor-Governance wall |
| **Agent real-time handoff** | the same public write | the same. Property: immediately visible to another agent's `hydrate` / `search`. No phase completion, no Cursor-Governance approval, no session close, no PR lifecycle, no local distill queue, no intermediate governance receipt |
| **Automatic hook** | bounded write / distill / close via `MemoryControlPlaneClient` → `MemoryService` | constrained hook authority: a narrower capability envelope on the *same* pipeline (`ops/config/memory-hook-envelopes.json`, ADR-0033 B7) |

"Bounded" means the same service, the same admission, the same store, with a
narrower envelope — never an alternate path.

### Why `write_governed` is optional, not the model path

`memory.phase_lock → memory.write_governed` is a conflict-sensitive write:
it asks memory to lock a phase, check contradictions and then admit. That is
useful for a plan lock or a GMP Phase 0. It is a ceremony memory offers,
not one Cursor-Governance imposes, and it was never the property that makes
handoff work. Naming it the only write made every ordinary lesson or decision
look like it needed a governance step. `memory.write_agent` is the ordinary
write; `write_governed` stays available for the cases that want the lock.

### What Cursor-Governance may still do

- Build `ContinuationCapsuleV2` and gather / redact / latch session material
  (that is *input preparation*, not cognition).
- Call the hook lane's bounded operations from automatic machinery
  (SessionStart hydrate / prefetch, SessionEnd capsule admission, `memory.close`,
  bounded `distill` on the redacted excerpt, deterministic-adapter writes such as
  `pr_publish_memory_write.py`, SGD `ingest_memory_candidate.py`).
- Gate **repository edits** on hydration. Claude's `memory_gate` on
  `Edit|Write` and Cursor's "edit-other" governed write are repo-edit
  preconditions. They are not memory-write walls and must not be widened into
  one (B8).

### What it may not do

- Extract, score, promote, or otherwise decide memory content locally.
- Hold a provider client, key, or model id on any memory path.
- Route an agent-directed read or write through `MemoryControlPlaneClient`
  as a requirement.
- Deny, defer, or precondition an agent's `l9-memory write` / MCP
  `write_agent` on a phase, a receipt, a session close, or a PR state.

## Lane classification of every caller

Placed deliberately so the next caller is too. "Hook lane" callers keep
`MemoryControlPlaneClient` and its envelope; "agent lane" callers use the
package's public CLI / MCP directly and use `runtime_binding` only to *locate*
the interpreter.

| Caller | Lane | Envelope surface |
|---|---|---|
| `ops/hooks/session_start_memory_orchestrator.sh` → `compile_session_packet.py` (`canonical_hydrate`) | hook | `cursor-session-start` |
| `ops/hooks/graphiti-session-end.sh` → `close_session.py` (capsule ingest, `close`, `distill`) | hook | `cursor-session-end` / `claude-session-end` |
| `environment/agents/adapters/claude-code/memory/memory_bridge.py` (hydrate, conflicts) | hook | `claude-session-start` |
| `environment/agents/adapters/claude-code/hooks/memory_writeback.py` | hook | `claude-session-end` |
| `ops/hooks/plan_memory_prefetch.py` | hook | `plan-prefetch` |
| `ops/hooks/pr_publish_memory_write.py` (deterministic adapter) | hook | `pr-publish` |
| `environment/agents/generated-data/adapters/ingest_memory_candidate.py` (SGD automatic ingest) | hook | `pe-sgd-ingest` |
| `ops/graphiti/hydration/pickup_write.py` (`/end-session` repair-write, operator) | hook | `cursor-session-end` |
| `ops/memory/cli.py` (operator form) | operator | none — the operator is a human on the bound interpreter |
| `environment/program-execution/integrations/graphiti/context_reader.py` when a PE **worker** hydrates / searches for its own task | **agent** | none — public `l9-memory hydrate|search` |
| Claude / Cursor model tools (`mcp__l9-graphite-memory__write_agent`, `search`, `hydrate`, `l9-memory write`) | **agent** | none |

## Consequences

- Real-time handoff is one call: agent A `write_agent(type=handoff, …)`;
  agent B `hydrate` / `search` sees it immediately.
- Close-time operations (Phase A capsule, bounded distill, `memory.close`)
  are supplementary lifecycle capture, not the mechanism by which agents
  communicate.
- The doctrine-residue ratchet gains two classes (B5): `local-memory-cognition`
  (no provider client, model id, promotion rule, `MEMORY_PHASE_B`,
  `MEMORY_DISTILL`, `boto3`/S3 or `graphiti_memory_client` on a memory path)
  and `agent-lane-interposition` (no doctrine that makes an ordinary agent
  write wait on a phase lock, receipt, close or PR gate; no hook matcher or
  gate tool-list that names a memory MCP tool or `l9-memory write` for denial).
- A native hook principal (signed agent assertion + grants JSON on the stdio
  door) is the preferred long-term envelope. It is a follow-on request against
  `l9-graphiti-memory`, recorded here, not a Cursor-Governance expansion; the
  client-side envelope is the interim.
- Out of scope and unchanged: PE `pec/signals.py` `runtime/distill_queue` is a
  local dry-run observability artifact, not S3, and stays. `archive_transcript.py`
  is an adjacent S3 chat archive, not memory.

## Enforcement

- `INVARIANTS.md` INV-03b → `tests/ops/memory/test_no_local_memory_cognition.py`,
  `tests/ops/memory/test_no_agent_lane_interposition.py`,
  `ops/scripts/validate_legacy_doctrine_residue.py` (`local-memory-cognition`,
  `agent-lane-interposition`), `ops/scripts/validate_memory_egress_boundary.py`.
- Cross-repo proof of the bounded distill on the bound wheel:
  `tests/ops/memory/test_cross_repo_lifecycle.py`.
- Epoch: `ops/config/memory-canonical-epoch.json` stage C15.

## References

- ADR-0030 (canonical memory control plane), ADR-0031 (signed-agent door,
  `write_agent` / `write_governed`), ADR-0032 (close-gap vs environment vs
  degradation).
- `docs/MEMORY_PIPELINE_MAP.md` "Lanes".
- Plan: `docs/plans/upstream_memory_realignment_8b0f30f5.plan.md`.
