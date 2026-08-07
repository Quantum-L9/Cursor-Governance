# ADR-0003: Memory architecture — two entry points, one contract

## Status

Accepted

## Date

2026-08-04

## Context

The Claude Code surface reaches the L9 shared memory service (`l9-graphite-memory`,
the `l9-shared-memory` HTTP MCP control plane) through **two** code paths, and an
audit (`reports/graphiti-memory-audit-2026-08-04/`) raised the reasonable question
of whether that duplication is a defect to be collapsed.

The two paths are:

1. **Hook path (harness-driven).** `SessionStart` runs
   `environment/claude-code/hooks/memory_prefetch.py`; `Stop` runs
   `memory_writeback.py`; the `PreToolUse` gate (`memory_gate.py`) and
   `memory_lock.py` verify phase-locks. All of these call the memory service
   through `environment/claude-code/memory/memory_client.py` — a **zero-dependency,
   stdlib-only JSON-RPC client** so the enforcement hooks run in any consumer repo
   with no virtualenv and no MCP runtime.
2. **Interactive MCP path (model-driven).** `l9-shared-memory` registered as an MCP
   server (`environment/claude-code/mcp.template.json`) exposes `memory.*` tools the
   model can call on demand mid-session.

They are **not** redundant. They differ on *who drives* and *when*:

| | Hook path | Interactive MCP path |
|---|---|---|
| Trigger | Harness lifecycle (SessionStart, Stop, PreToolUse) | The model, on demand |
| Runs even if the model does nothing | Yes | No |
| Owns | Deterministic prefetch + **context injection**, the enforcement **receipt** the gate depends on, phase-locks, deterministic provenance writeback | Ad-hoc "search memory for X", write a curated lesson now |
| Dependencies | stdlib only (portable to any repo) | requires the MCP server registered in the runtime |

Neither can do the other's job. A SessionStart hook is the only place to inject
prefetched context and to write the receipt that gates governed writes — an
MCP-only design would make memory and enforcement contingent on the model choosing
to call a tool. Conversely, a one-shot prefetch cannot answer a question the model
forms three turns later, nor let it write a lesson on the spot; that needs callable
tools, which only the MCP server provides.

The audit found that the real problem was **not** that there are two paths, but
that they were allowed to **diverge**:

- **RC1 / MEM-001/002:** `memory_prefetch.py` read `records`/`hits` from a
  `memory.hydrate` result that only carries `sections` (`HydrationResult`), and
  never injected the returned `sections`. SessionStart therefore always reported
  "0 record(s) hydrated" and surfaced no memory, regardless of stored data.
- **RC2 / MEM-003:** in the managed (CCR) runtime the MCP set is sourced from the
  launch `--mcp-config` (account connectors); `l9-shared-memory` was absent, so the
  interactive path did not exist and `claude mcp list` was empty.

## Decision

**Keep both entry points. Unify the contract, transport, and identity beneath them.**

1. **One contract.** Both paths speak the same `memory.*` tool contract against the
   same `${L9_MEMORY_HTTP_URL}/mcp` endpoint with the same bearer-derived identity
   (`agent_id=claude-code`). `memory.hydrate` returns context under `sections`;
   `memory.search` returns `hits`. The stdlib client
   (`environment/claude-code/memory/memory_client.py`) is the **single place** that
   names those response keys, via the accessors `hydrated_sections()`,
   `search_hits()`, and `render_sections()`. Hook consumers MUST use those accessors
   rather than re-reading raw keys, so a consumer cannot silently drift from the
   server schema. This is formalized in ADR-0004.

2. **Two roles, kept distinct.** The hook path remains the harness-driven,
   stdlib-only, enforcement-bearing path (prefetch + inject + receipt + lock +
   writeback). The interactive MCP path remains the model-driven, on-demand
   read/write path. We do not collapse them.

3. **The interactive path must actually be registered** on every surface it is
   claimed on. On the managed surface, presence of a repo `.mcp.json` is **not**
   proof; readiness is `claude mcp list` (or the runtime `--mcp-config`) showing
   `l9-shared-memory`. Wiring that registration into the managed launcher is tracked
   as remediation MEM-003/FIX-2 and is out of scope for this ADR (it touches
   managed-environment connector config outside this tree).

4. **Fail-closed enforcement, fail-open prefetch stay as-is.** A prefetch failure
   degrades to a visible DEGRADED banner and writes no receipt (keeping governed
   writes fail-closed); it never blocks the session. An *empty* successful hydrate
   is reported as `0 section(s)` and is distinct from the DEGRADED path.

## Consequences

- The two-path design is now an explicit, documented decision rather than apparent
  accidental duplication.
- Prefetched memory is actually injected into the session (fix in
  `memory_prefetch.py`); the receipt count reflects hydrated sections.
- Drift between the stdlib client and the server contract is guarded by a
  network-free contract test (`tests/test_memory_client_contract.py`) that
  `validate_memory_enforcement.py` executes (ADR-0004).
- Callers must not reintroduce raw `bundle.get("records")`/`bundle.get("hits")`
  reads of a hydrate result; use the client accessors.
- Registration of the interactive MCP path on the managed surface remains open
  work (MEM-003/FIX-2); until it lands, the hook path is the only live path and its
  correctness (this ADR) is what makes memory usable.

## Alternatives considered

- **Collapse to a single path.** Rejected: dropping the hook path loses
  deterministic startup context and the enforcement receipt; dropping the MCP path
  loses on-demand model read/write. Each sacrifices a capability the other cannot
  provide.
- **Make the hooks depend on the real MCP runtime instead of the stdlib client.**
  Rejected: the zero-dependency property lets enforcement run in any consumer repo
  without a venv/MCP runtime. Unifying the *contract* (ADR-0004) achieves parity
  without giving up portability.

## References

- ADR-0002 — memory enforcement contract (receipt/lock/gate)
- ADR-0004 — hook memory client is a contract-pinned stdlib mirror
- `reports/graphiti-memory-audit-2026-08-04/` — the audit that motivated this ADR
- `environment/claude-code/mcp.template.json`, `memory/memory_client.py`,
  `hooks/memory_prefetch.py`

## See also

- ADR-0005 — one agent memory; product/domain memory out of band
