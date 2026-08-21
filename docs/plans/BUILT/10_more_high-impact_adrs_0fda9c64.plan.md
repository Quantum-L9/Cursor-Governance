---
name: 10 More High-Impact ADRs
overview: Create 10 additional ADRs (0014-0023) documenting critical L9 patterns that AI agents frequently misinterpret, using multi-modal reasoning to prioritize by impact.
todos:
  - id: adr-0014
    content: "Create ADR-0014: DORA Metadata Block Pattern (__dora_meta__ in 565 files)"
    status: completed
  - id: adr-0015
    content: "Create ADR-0015: Migration Sequential Apply Pattern (24 migrations, order-critical)"
    status: completed
  - id: adr-0016
    content: "Create ADR-0016: TypedDict vs Pydantic Boundary (LangGraph state vs API models)"
    status: completed
  - id: adr-0017
    content: "Create ADR-0017: Tool Definition Schema (OpenAI naming constraints)"
    status: completed
  - id: adr-0018
    content: "Create ADR-0018: Async Retry Pattern (exponential backoff, jitter)"
    status: completed
  - id: adr-0019
    content: "Create ADR-0019: structlog Logging Standard (444 files, ALWAYS structlog)"
    status: completed
  - id: adr-0020
    content: "Create ADR-0020: Test Fixture Hierarchy (conftest.py mock patterns)"
    status: completed
  - id: adr-0021
    content: "Create ADR-0021: LangGraph Node Wrapper (PacketNodeAdapter pattern)"
    status: completed
  - id: adr-0022
    content: "Create ADR-0022: Registry Pattern (Tool/Agent/Orchestrator/Cell registries)"
    status: completed
  - id: adr-0023
    content: "Create ADR-0023: Error Packet Pattern (error → packet with recovery spec)"
    status: completed
---

# 10 Additional High-Impact ADRs for AI Agents

## Reasoning: Impact Prioritization

Applied multi-modal reasoning to identify patterns by:

- **Abductive**: Which patterns do AI agents most frequently misinterpret?
- **Deductive**: Which patterns, if violated, break system invariants?
- **Inductive**: Which patterns are used most frequently across the codebase?

## Pattern Frequency Analysis

| Pattern | File Count | AI Misinterpret Risk |
|---------|------------|---------------------|
| `__dora_meta__` | 565 files | VERY HIGH (may remove "unused" metadata) |
| `structlog.get_logger` | 444 files | HIGH (may use print() or logging) |
| Migrations | 24 files | CRITICAL (wrong order breaks DB) |
| TypedDict vs Pydantic | 20+ LangGraph files | HIGH (will "fix" type system) |
| Tool naming (OpenAI) | 100+ tools | HIGH (will use dots in names) |

## ADRs Ranked by Impact Score

| ADR | Pattern | Impact | Frequency | AI Misinterpret Risk |
|-----|---------|--------|-----------|---------------------|
| 0014 | DORA Metadata Block | CRITICAL | 565 files | VERY HIGH (will remove) |
| 0015 | Migration Sequential Apply | CRITICAL | 24 migrations | MEDIUM (will skip) |
| 0016 | TypedDict vs Pydantic Boundary | HIGH | 20+ files | HIGH (will "fix") |
| 0017 | Tool Definition Schema | HIGH | 100+ tools | HIGH (invalid names) |
| 0018 | Async Retry Pattern | HIGH | 50+ callsites | MEDIUM (will remove retry) |
| 0019 | structlog Logging Standard | HIGH | 444 files | HIGH (will use print) |
| 0020 | Test Fixture Hierarchy | MEDIUM | 308 fixtures | MEDIUM (break tests) |
| 0021 | LangGraph Node Wrapper | HIGH | 8+ graphs | HIGH (skip packets) |
| 0022 | Registry Pattern | HIGH | 5 registries | MEDIUM (duplicate code) |
| 0023 | Error Packet Pattern | CRITICAL | All errors | HIGH (silent failures) |

## ADR Format (AI-Optimized)

Same format as 0004-0013: minimal verbosity, maximum information density.

## Implementation Files

All ADRs will be created in [readme/adr/](readme/adr/):

- `0014-dora-metadata-block.md`
- `0015-migration-sequential-apply.md`
- `0016-typeddict-pydantic-boundary.md`
- `0017-tool-definition-schema.md`
- `0018-async-retry-pattern.md`
- `0019-structlog-logging-standard.md`
- `0020-test-fixture-hierarchy.md`
- `0021-langgraph-node-wrapper.md`
- `0022-registry-pattern.md`
- `0023-error-packet-pattern.md`

## Key Files to Reference

- [runtime/dora.py](runtime/dora.py) - DORA metadata implementation
- [migrations/README.md](migrations/README.md) - Migration documentation
- [langgraph/TYPEDDICT_VS_PYDANTIC.md](langgraph/TYPEDDICT_VS_PYDANTIC.md) - Type system boundary
- [core/tools/tool_graph.py](core/tools/tool_graph.py) - ToolDefinition schema
- [core/resilience/retry.py](core/resilience/retry.py) - Async retry implementation
- [graph_adapter/packet_node_adapter.py](graph_adapter/packet_node_adapter.py) - Node wrapper
- [core/tools/base_registry.py](core/tools/base_registry.py) - Registry base class
- [tests/conftest.py](tests/conftest.py) - Test fixture patterns

## Post-Implementation

1. Update [readme/adr/README.md](readme/adr/README.md) with new ADRs
2. Update [readme/repo-index/adr_catalog.txt](readme/repo-index/adr_catalog.txt)
3. Verify [core/governance/session_startup.py](core/governance/session_startup.py) loads all ADRs