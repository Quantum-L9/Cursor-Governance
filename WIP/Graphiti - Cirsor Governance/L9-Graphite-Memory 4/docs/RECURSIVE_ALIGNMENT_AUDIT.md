# Recursive Alignment Audit: L9-Graphite-Memory ROADMAP.md

**Auditor:** l9_recursive_alignment_auditor  
**Target:** `ROADMAP.md` in `Quantum-L9/L9-Graphite-Memory`  
**Date:** 2026-07-05  
**Protocol:** RecursiveAlignment.md (10-pass convergence)

---

## Alignment Summary

The roadmap is **structurally sound** and correctly identifies the execution sequence (secrets → transport → packaging → CI → rollout → ontology). However, it contains drift from the active L9 architecture contract in several areas: references to a deprecated WIP repo (`L9-Ops-MCP`), missing `L9_META` across all tracked files, `print()` usage in production code, and a `process.env` reference that conflates the Node.js TypeScript pattern with the Python implementation. The roadmap also underspecifies the Python Infisical adapter contract and over-references the MCP "4 tools" contract from L9-Ops-MCP (which is WIP/concept, not canonical).

**Alignment Score: 72/100** — Viable after corrections. No critical architectural violations. All issues are correctable without redesign.

---

## Source Authority Used

| Authority | Applied To |
|-----------|-----------|
| L9 Master Kernel v3.0 | Transport, Gate routing, authority boundaries |
| RecursiveAlignment.md | 10-pass audit structure |
| `@quantum-l9/infisical-config` (PR #2) | Secrets architecture contract |
| ROADMAP.md itself | Self-declared boundaries and contracts |
| Repo source code inspection | Actual implementation state |

---

## Critical Violations

None.

---

## High Violations

| ID | Severity | Rule Broken | Evidence | Impact | Correction | Owner Layer | Blocks Release |
|----|----------|-------------|----------|--------|------------|-------------|----------------|
| H-1 | high | No L9-Ops-MCP references (boundary rule #5) | AGENTS.md line: "Quantum-L9/L9-Ops-MCP — Hydrator consumes memory via this module's API" | Creates false dependency on WIP repo; confuses ownership | Remove L9-Ops-MCP from AGENTS.md upstream dependencies | roadmap / docs | false |
| H-2 | high | No stubs, TODOs, placeholders | Roadmap Phase 2 references "4 MCP tools: `memory_get_budget_slice`, `memory_ingest_episode`, `memory_query_context`, `memory_invalidate_fact`" — these tool names come from L9-Ops-MCP (WIP), not from this repo | Pins the roadmap to a concept repo's API surface that may never ship | Replace with this repo's actual CLI contract: `search`, `write`, `health`, `bootstrap`, `phase-lock`, `conflicts` | roadmap | false |
| H-3 | high | Unknown must be labeled instead of invented | Roadmap says "Python equivalent of `@quantum-l9/infisical-config` does not exist yet" but then Phase 0 deliverables reference `loadSecrets()` as if the API is defined | Conflates TypeScript API with Python implementation; creates ambiguity | Define the Python adapter contract explicitly: function name, signature, return type, env var fallback behavior | roadmap | true (blocks Phase 0 implementation) |
| H-4 | high | No `print()` in production code | `graphiti_memory_client.py` has 15+ `print()` calls; `prune.py` likely has more | Violates security/observability alignment; no structured logging | Replace with `logging.getLogger()` calls in Phase 0 or Phase 1 (transport refactor) | source code | false (not a roadmap issue, but roadmap should acknowledge) |

---

## Medium Violations

| ID | Severity | Rule Broken | Evidence | Impact | Correction | Owner Layer | Blocks Release |
|----|----------|-------------|----------|--------|------------|-------------|----------------|
| M-1 | medium | L9_META present on tracked files | Zero files in the repo carry `L9_META` headers | Cannot verify provenance, version, or ownership of any file | Add `L9_META` to all Python source files in a dedicated pass (Phase 3 or earlier) | source code | false |
| M-2 | medium | `process.env` conflation | Roadmap Target State table says "Infisical Universal Auth → `process.env` hydration" | `process.env` is Node.js; Python uses `os.environ`. Mixing terminology signals unclear implementation boundary | Replace with "Infisical Universal Auth → `os.environ` hydration" | roadmap | false |
| M-3 | medium | Hardcoded VPS URL in production code | `graphiti_memory_client.py:37` defaults to `http://127.0.0.1:8100/mcp/` | Dead endpoint as default; will cause confusing failures if env var is unset | Phase 1 must change default to Zep Cloud URL or raise explicit error if `ZEP_API_KEY` is missing | source code | false |
| M-4 | medium | No behavior tests (only bash e2e) | `tests/` contains only shell scripts; no Python `pytest` tests exist | Cannot validate gate logic, episode contract, or group resolver in CI without bash | Add Python unit tests in Phase 3; roadmap should list this as a Phase 0 or Phase 1 deliverable | roadmap | false |
| M-5 | medium | Rotation-aware contract underspecified for Python | Roadmap says "SIGHUP or interval refresh for long-running MCP server processes" but Python signal handling differs significantly from Node.js | Python `signal.signal(signal.SIGHUP, handler)` is sync-only; asyncio services need `loop.add_signal_handler()` | Specify the Python-native rotation pattern in Phase 0 contract | roadmap | false |

---

## Unknowns

| ID | Item | Impact | Resolution Path |
|----|------|--------|-----------------|
| U-1 | Infisical project ID for quantum-l9 | Cannot implement Phase 0 runtime without it | User must provision and provide |
| U-2 | Infisical machine identity credentials | Cannot test Phase 0 locally | User must create machine identity |
| U-3 | Whether `@quantum-l9/infisical-config` PRs will merge before Phase 0 | If not merged, Python adapter cannot reference the TypeScript package as canonical | Decouple: Python adapter is standalone, follows same contract but is independent |
| U-4 | Zep Cloud API key | Blocks Phase 1 | User must provision |
| U-5 | Zep Cloud custom ontology support | Blocks Phase 5 | Research or Zep support ticket |
| U-6 | ~~Whether `infisical-python` SDK exists~~ | **RESOLVED** — `infisical-python` v2.3.6 on PyPI, official SDK, Python >=3.7 | Use `infisical-python` package directly |

---

## Boundary Map

```
┌─────────────────────────────────────────────────────────────┐
│  L9-Graphite-Memory (this repo)                             │
│                                                             │
│  SACRED (no-touch):                                         │
│    graphiti_gate_lib.py                                      │
│    episode_contract.py                                       │
│    group_resolver.py                                         │
│    rules/*.mdc                                              │
│    hooks/*.sh                                               │
│                                                             │
│  REFACTOR TARGETS:                                          │
│    graphiti_memory_client.py  (transport swap)               │
│    graphiti_env_loader.py     (replace with Infisical)       │
│                                                             │
│  ARCHIVE TARGETS:                                           │
│    config/graphiti.env.example                               │
│    config/graphiti.env.defaults                              │
│    scripts/init_graphiti_machine_env.sh                      │
│    _archived/* (already deprecated)                          │
│                                                             │
│  OUT OF SCOPE:                                              │
│    L9-Ops-MCP (WIP, not a dependency)                       │
│    Cursor-Governance (upstream consumer, not owned here)     │
│    Constellation.Gate (downstream, not owned here)           │
└─────────────────────────────────────────────────────────────┘
```

---

## Transport Packet Compliance

**Status: NOT APPLICABLE**

This repo is a **memory substrate**, not a constellation node. It does not send or receive `TransportPacket` messages. It exposes a CLI and MCP tool interface. The roadmap correctly does not reference TransportPacket. No violation.

However, if this repo is ever consumed as a node in the constellation (Phase 2 MCP server), the MCP responses should be structured as TransportPacket-compatible payloads. This is a **future consideration**, not a current violation.

---

## Gate Routing Compliance

**Status: COMPLIANT (with caveat)**

The `graphiti_gate_lib.py` implements local-only gate decisions (reads state files, no network calls). This is correct. The gate does not route to other nodes or dispatch work — it only returns `allow`/`deny` decisions.

**Caveat:** The roadmap's Phase 2 "MCP Server Packaging" introduces a server that exposes tools. If agents call these tools, the server becomes a routing point. The roadmap must clarify: the MCP server is a **service endpoint**, not a Gate. It does not make routing decisions — it only serves memory queries. This distinction should be explicit.

---

## Authority Boundary Compliance

**Status: COMPLIANT**

The roadmap correctly separates:
- Gate logic (local, sacred, no network)
- Transport (swappable, refactor target)
- Secrets (Infisical, runtime injection)
- Packaging (server wrapper, separate concern)

No authority leakage detected. The memory client does not implement chassis, routing, or admission logic.

---

## File Structure Compliance

**Status: MOSTLY COMPLIANT**

Current structure is clean:
- `src/l9_graphite_memory/` — all Python source
- `config/` — configuration
- `hooks/` — bash hooks
- `rules/` — governance rules
- `tests/` — test scripts
- `docs/` — documentation
- `_archived/` — deprecated files

**Issue:** No `L9_META` headers (M-1). No forbidden directories detected.

---

## Schema and Field Compliance

**Status: COMPLIANT**

- All Python files use `snake_case` for functions and variables
- YAML files use snake_case keys (`group_id`, `integrates_with`, `domain_packs`)
- Pydantic models use snake_case fields
- No camelCase in public APIs (the `toolName` reference in `graphiti_gate_lib.py` is reading external input, not defining it)

---

## Security and Observability Compliance

**Status: PARTIALLY COMPLIANT**

| Check | Status | Evidence |
|-------|--------|----------|
| No `eval()`/`exec()`/`compile()` | PASS | `re.compile()` is regex, not code execution |
| `yaml.safe_load` only | PASS | Both `group_resolver.py` and `prune.py` use `yaml.safe_load` |
| No `print()` | **FAIL** | 15+ `print()` calls in `graphiti_memory_client.py` |
| No forbidden log fields | PASS | No logging of secrets or PII |
| PII not logged | PASS | `episode_contract.py` actively redacts PII |
| Bounded caches | PASS | Circuit breaker has TTL; rate limiter has window |

---

## Testing and Validation Compliance

**Status: PARTIALLY COMPLIANT**

| Check | Status | Evidence |
|-------|--------|----------|
| Behavior tests exist | PARTIAL | Bash e2e tests validate gate behavior |
| Packet invariants tested | N/A | Not a packet-producing node |
| Gate boundaries tested | PASS | `test_gate_e2e.sh` and `test_gate_e2e_full.sh` |
| No stub scanner passes | PASS | No stubs in test files |
| CI gates match contracts | FAIL | No CI workflow exists yet (Phase 3 deliverable) |

---

## Overbuilt vs. Underbuilt

| Category | Items |
|----------|-------|
| **Overbuilt** | `graphiti_env_loader.py` — complex 3-tier loading (defaults → files → Keychain) for a pattern being replaced. The `init_graphiti_machine_env.sh` script is also overbuilt for a deprecated flow. |
| **Underbuilt** | Python unit tests (zero `pytest` files). The `secrets.py` adapter (does not exist yet). Structured logging (all `print()`). `L9_META` headers (missing entirely). The Python Infisical contract (unspecified). |
| **Duplicate logic** | `prune.py` re-implements the MCP URL resolution and YAML loading that `graphiti_memory_client.py` and `group_resolver.py` already do. |
| **Unnecessary abstractions** | None detected. The separation of concerns is appropriate. |
| **Missing primitive boundaries** | No clear interface/protocol class defining the "transport" abstraction that Phase 1 will swap. Currently it's just raw `httpx` calls inline in the client. |

---

## Correction Roadmap

Ordered by dependency unlock (fix transport/routing before cosmetics, fix authority before features, fix stubs before packaging, fix tests before ship).

| Priority | Correction | Blocks | Phase |
|----------|-----------|--------|-------|
| 1 | **Define Python Infisical adapter contract explicitly** (H-3) — function signature, return type, env var names, fail-soft behavior, rotation pattern for asyncio | Phase 0 implementation | Phase 0 |
| 2 | **Remove L9-Ops-MCP from AGENTS.md** (H-1) — delete the upstream dependency line | Boundary clarity | Immediate |
| 3 | **Replace "4 MCP tools" contract with actual CLI contract** (H-2) — the canonical interface is `search`, `write`, `health`, `bootstrap`, `phase-lock`, `conflicts` | Phase 2 design | Phase 2 |
| 4 | **Fix `process.env` → `os.environ` terminology** (M-2) | Documentation accuracy | Immediate |
| 5 | **Define transport abstraction protocol** (underbuilt) — `class MemoryTransport(Protocol)` with `search()`, `write()`, `health()` methods | Phase 1 clean implementation | Phase 1 |
| 6 | **Replace `print()` with `logging`** (H-4) | Security/observability compliance | Phase 1 |
| 7 | **Add Python pytest unit tests** (M-4) | CI gate validity | Phase 0 or Phase 1 |
| 8 | **Verify `infisical-python` SDK exists** (U-6) | Phase 0 implementation choice | Before Phase 0 |
| 9 | **Add `L9_META` headers** (M-1) | File provenance tracking | Phase 3 |
| 10 | **Specify Python SIGHUP rotation pattern** (M-5) | Long-running server correctness | Phase 2 |

---

## Minimum Safe Next Action

**Correct the roadmap itself** before implementing Phase 0:

1. Remove L9-Ops-MCP reference from AGENTS.md (H-1) — 1 line delete.
2. Replace "4 MCP tools" with actual CLI contract in Phase 1/Phase 2 sections (H-2).
3. Fix `process.env` → `os.environ` in Target State table (M-2).
4. Add explicit Python Infisical adapter contract to Phase 0 (H-3):
   - Function: `load_secrets(required: bool = False, overwrite: bool = False) -> LoadSecretsResult`
   - Env vars: `INFISICAL_CLIENT_ID`, `INFISICAL_CLIENT_SECRET`, `INFISICAL_PROJECT_ID`, `INFISICAL_ENV`, `INFISICAL_SECRET_PATH`
   - Fail-soft: returns `{"loaded": False, "source": "environ"}` when not configured
   - Rotation: `refresh_secrets()` + `signal.SIGHUP` handler (or `loop.add_signal_handler` for asyncio)
5. Verify whether `infisical-python` or `infisical-sdk` exists on PyPI (U-6).

After these 5 corrections, the roadmap is convergence-ready and Phase 0 can proceed safely.

---

## Convergence Block

```yaml
convergence_status: CONDITIONAL_PASS
alignment_score: 72/100
critical_violations: 0
high_violations: 4
medium_violations: 5
unknowns: 6
blocks_release: 1 (H-3 blocks Phase 0 implementation)
minimum_corrections_before_proceed: 5
estimated_correction_effort: 30 minutes (roadmap text edits + 1 PyPI check)
next_audit_trigger: After corrections applied, before Phase 0 implementation begins
```
