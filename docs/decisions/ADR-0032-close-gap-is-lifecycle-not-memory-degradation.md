# ADR-0032: A close-gap is a lifecycle condition, and an unbound runtime is an environment fault — neither is memory degradation

## Status

Accepted

## Date

2026-09-15

## Context

ADR-0028 made a missed session close **loud**: when the prior session left no
close receipt, `write_count=0`, or no session-scoped continuation, SessionStart
leads `additional_context` with `DEGRADED` + `REPAIR: /end-session`. That fixed
silent gaps. It also folded three unrelated conditions into one word.

`compile_session_packet.py` computed `degraded = hydration.degraded or
close_gap`, and `classify_hydrate_state.py` returned degraded for
`close_gap=true` **and** for `continuation_stale=true`. A session in this
repository therefore printed `memory-hydrate: degraded — STALE —
continuation_stale=true` on a hydrate whose canonical status was `OK` and whose
continuation record was real; the repository had simply moved on, which the
capsule already says is fine ("current git state wins").

Separately, the runtime binding (`ops/memory/runtime_binding.py`) defaulted to
`sys.executable`. From a consumer workspace whose own `.venv` carried an older
`l9-graphite-memory`, the binding failed `BINDING_FAILED: package version 2.3.1
does not match expected 2.4.0` — and `CanonicalHydration.degraded` reported it
as memory degradation. Canonical memory had never been observed. The `.venv`
was stale because the pin moved on `main` and nothing re-synced it; the repair
was `uv sync --locked`, not anything about memory.

Two consequences followed from the conflation. `memory_gate` /
`memory_prefetch` (Claude) consume the same classifier, so Claude skipped
writebacks on a "degraded" session that was merely stale. And operators were
told to repair memory when the actual repair was `/end-session` (lifecycle) or
the interpreter (environment).

ADR-0030 keeps `MemoryService` the only memory authority; nothing here changes
what memory decides. This ADR is about what Cursor-Governance is allowed to
*call* the result.

## Decision

1. **Three typed conditions, one meaning each.**

   | Field | Meaning | Repair |
   |---|---|---|
   | `memory_degraded` | Canonical memory ran and did not answer (`CANONICAL_UNAVAILABLE`, `UNAUTHORIZED_NAMESPACE`, `TIMEOUT`, `INVALID_RECEIPT`, `PARTIAL_PROJECTION_DEGRADED`). | memory / provider |
   | `environment_fault` | The runtime never reached memory (`BINDING_FAILED`, `NAMESPACE_UNRESOLVED`). | environment: `make memory-readiness`, `ensure_uv_environment.sh <root> apply`, repository identity |
   | `close_gap` (+ `close_gap_reason`) | The prior session left no close receipt / `write_count=0` / no session continuation. | `/end-session` |

   `continuation_stale` remains a fact on the continuation; it is not a
   condition of any kind and never lowers the session's verdict.

2. **`degraded` mirrors `memory_degraded`.** It stays on the packet for
   consumers that predate the split and is never ORed with `close_gap` or
   with an environment fault. `SessionHydrationPacket` declares
   `memory_degraded`, `environment_fault`, `close_gap_reason`
   (`additionalProperties: false` is enforced by a test).

3. **`additional_context` leads by class.** `ENVIRONMENT_FAULT` + its
   `REPAIR:` line, then `CLOSE_GAP` + `REPAIR: /end-session`, then
   `DEGRADED`. Mixed conditions print each lead once, in that order. The
   status line carries the same flags (`status=BINDING_FAILED
   ENVIRONMENT_FAULT CLOSE_GAP`).

4. **The classifier reports conditions, not a bigger `degraded`.**
   `classify_hydrate_state.py` derives `degraded` from `memory_degraded`
   (falling back to `degraded` for pre-split packets, subtracting the
   lifecycle and environment bits when it can) and prints a third line —
   `ENVIRONMENT_FAULT` / `CLOSE_GAP` / `STALE` with detail — for the
   non-degraded conditions. Consumers that read only the first two lines,
   including Claude's `memory_prefetch.py`, inherit the fix unchanged: a
   close-gap or stale continuation no longer skips a writeback.

5. **The runtime report renders each condition under its own name.**
   `memory-hydrate: degraded — …` is reserved for `memory_degraded`.
   `ENVIRONMENT_FAULT` lands in `### Degraded` as `environment_fault` (it is a
   fault to repair, named honestly); `CLOSE_GAP` and `STALE` are `ok` rows
   that carry their detail and, for close-gap, the repair.

6. **The fault split is computed at the source.** `OperationOutcome` and
   `CanonicalHydration` carry `fault_class` (`none` / `environment` /
   `canonical`) with `environment_fault` / `memory_degraded` derived from it;
   `diagnostics.py`, the runtime report and `plan_memory_prefetch.py` read
   that field rather than re-deriving it. The interpreter anchoring and the
   one-shot deterministic heal that make `BINDING_FAILED` rare are
   `runtime_binding.py` / `environment_heal.py` (INV-11).

## Consequences

- ADR-0028 §9 ("SessionStart prints hard `DEGRADED` + `REPAIR: /end-session`")
  is superseded by items 1–3: the lead is `CLOSE_GAP` + `REPAIR: /end-session`.
  The loudness ADR-0028 wanted is kept; the word is corrected.
- A stale continuation on an `OK` hydrate produces no degraded row and no
  `REPAIR:` line anywhere.
- `hydrate_stats.degrade_reason` is empty unless `memory_degraded`; the
  close-gap text moved to `close_gap_reason`, the environment text to
  `hydrate_stats.environment_fault_reason` (with `environment_heal`).
- Skills and commands that told operators to look for `DEGRADED` +
  `REPAIR: /end-session` (`l9-end-session`, `l9-graphiti-memory`,
  `commands/end-session.md`) now name `CLOSE_GAP`.
- No adapter edits were needed: Claude's `memory_prefetch.py` and
  `memory_gate.py` consume the compiled packet and the shared classifier.

## Related

- ADR-0028 — session hydrate/close visibility (superseded in part, §9)
- ADR-0030 — the memory control plane is the single front door (unchanged)
- `docs/MEMORY_PIPELINE_MAP.md` — lifecycle diagram
- `ops/graphiti/hydration/compile_session_packet.py`,
  `ops/graphiti/hydration/session_hydration_packet.schema.yaml`,
  `ops/scripts/classify_hydrate_state.py`,
  `ops/scripts/session_start_runtime_report.py`
- `ops/memory/runtime_binding.py`, `ops/memory/environment_heal.py`,
  `ops/memory/control_plane_client.py` (`fault_class_for`)
- `AGENTS.md` fragment `CLOSE_GAP_NOT_MEMORY_DEGRADED_V1`
