<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/docs/MEMORY_TOPOLOGY.md
layer: doc
owner: governance-control-plane
status: active
version: 2.0.0
updated: 2026-09-07
/L9_META -->

# Memory Topology — one MemoryService, N surfaces

Authority: `CANONICAL_LAW.md` §8.2 / §8.3, ADR-0030 (items 7–9), ADR-0005.
Live path map: `docs/MEMORY_PIPELINE_MAP.md`. Boundary: `ops/memory/README.md`.

## 1. The requirement

All agents — Cursor IDE, Claude Code desktop / Web / Mobile, Codex, Gemini,
Manus, generic adapters — read and write the **same** agent episodic memory
through **one** authority: `MemoryService` in `l9-graphite-memory`
(`memory-control-plane/v1`, release pinned in `ops/config/memory-binding.json`).
Graphiti is a projection that memory owns downstream; no surface reads or
writes it.

## 2. Live topology (2026-09-07 — ACTIVE)

```text
surface (Cursor / Claude / Codex / Gemini / Manus / generic)
   │
   ├── deterministic lifecycle (hooks, repair, reconciliation, diagnostics, PE)
   │       ops/memory  →  python -m ops.memory.cli  ──┐
   │                                                  │  stdio to the ONE bound runtime
   └── interactive (model-initiated read / governed write)                │
           l9-graphite-memory MCP server (stdio, package-owned) ──────────┤
                                                                          ▼
                                         MemoryService (l9-graphite-memory)
                                                  │
                                    canonical store → outbox → Graphiti projection
```

| Item | Value |
|---|---|
| Authority | `MemoryService` (`l9-graphite-memory`) — admission, identity, supersession, authorization, receipts |
| Canonical egress | `ops/memory/control_plane_client.py` (INV-03); binding proven by `ops/memory/runtime_binding.py` (INV-11) |
| Adapter — CLI | `python -m ops.memory.cli health\|resolve\|search\|write\|hydrate\|conflicts\|readiness` (operator, hooks, deterministic adapters) |
| Adapter — MCP | `l9-graphite-memory` stdio server, rendered only when `L9_MEMORY_INTERPRETER` is bound (`make memory-mcp-install`); no `env`, `url` or `headers` |
| Model write | `memory.phase_lock` → `memory.write_governed` (ADR-0030 item 7) |
| Resume SSOT | canonical `session_continuation` record (`ContinuationCapsuleV2`), current git state wins |
| Credentials on a surface | **none** — no provider URL, no bearer (stage C9); the runtime resolves its own configuration (memory ADR-016) |
| Namespace | a *request* from `python -m ops.memory.cli resolve`; memory authorizes (INV-07) |

## 3. Per-surface wiring

Every surface wires the same door; only the registration differs.

| Surface | Lifecycle (deterministic) | Interactive |
|---|---|---|
| Cursor IDE | `ops/hooks/session_start_memory_orchestrator.sh` / `ops/hooks/graphiti-session-end.sh` → `ops/graphiti/hydration/` → `ops/memory` | `~/.cursor/mcp.json` entry written by `l9-memory client cursor install` (`ops/memory/mcp_instantiation.py`) |
| Claude Code (desktop / Web / Mobile) | `hooks/memory_prefetch.py` / `hooks/memory_writeback.py` → `memory/memory_bridge.py` → `ops/memory` | `mcp.template.json` `l9-graphite-memory` (`${L9_MEMORY_INTERPRETER}`) |
| Codex / Gemini / Manus / generic | thin adapter hooks → `ops/memory` | package-owned `l9-graphite-memory` entry, same shape |

Identity: `L9_MEMORY_AGENT_ID` (`cursor`, `claude-code`, …) and `USER_ID` per
`agent_registry.yaml`; stamped as tags / `agent=` on every record.

## 4. Non-negotiables

- **One authority, one egress.** No production path calls a provider; the
  egress scanner (`validate_memory_egress_boundary.py --enforce`), the AST /
  runtime transport-boundary suite and the `l9.memory-boundary-*` semgrep rules
  enforce it.
- **Agents MUST be able to write durable memory, and MUST NOT write to the
  provider transport.** The model's write is the governed MCP write; generic
  `memory.ingest` and the operator CLI `write` are not its alternative.
- **The memory phase-lock is not repository authority.** It is a namespace
  snapshot-consistency precondition verified inside the admitting transaction.
  Edits, commits, pushes and publication are governed by worktree / branch /
  publication rules (`rules/96` E7/E8/E10), never by a memory lock.
- **Deterministic adapters are not second egresses.** Hydrate, close,
  `repair-write`, reconciliation and diagnostics are purpose-specific
  `ops/memory` operations over the same admission path.
- **No bearer, no URL, anywhere.** `~/.cursor/graphiti.env` carries switches
  only (`L9_MEMORY_ENABLED`, `L9_MEMORY_WRITE_GATES`); a URL or token line is
  residue the bootstrap reports.

## 5. Retired topology (historical — do not wire)

Before realignment stages C1–C12 (ADR-0030) this file described an HTTPS
Graphiti MCP plane on C1 behind Caddy with a per-agent plane bearer, a
Cursor-only SSH tunnel to the provider on loopback, and a retired L9 HTTP tool
plane. All three were provider transports held by model surfaces. They are
retired: the provider client is a tombstone (`ops/graphiti/graphiti_memory_client.py`,
exit 2), the env plane was deleted at C11, the HTTPS exposure is legacy
operator infrastructure of the provider deployment (ADR-0007 superseded), and
`environment/agents/tools/validate_agents.py` fails an adapter env that still
sets a provider URL or bearer. `agent_registry.yaml`'s `memory.*` fields are
identity only.
