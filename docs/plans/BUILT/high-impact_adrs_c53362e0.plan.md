---
name: High-Impact ADRs
overview: Create 10 high-impact Architecture Decision Records (ADRs) optimized for AI agent comprehension, documenting critical patterns that AI might otherwise misinterpret or incorrectly refactor.
todos:
  - id: adr-0004
    content: "Create ADR-0004: Singleton Auto-Registry Pattern (@register_singleton decorator)"
    status: completed
  - id: adr-0005
    content: "Create ADR-0005: RLS Shared Tenant Model (L+C same tenant, scope-based isolation)"
    status: completed
  - id: adr-0006
    content: "Create ADR-0006: PacketEnvelope Audit Trail (all operations emit packets)"
    status: completed
  - id: adr-0007
    content: "Create ADR-0007: 7-Phase Bootstrap Ceremony (kernel loading sequence)"
    status: completed
  - id: adr-0008
    content: "Create ADR-0008: Feature Flag Gating Pattern (env-based feature control)"
    status: completed
  - id: adr-0009
    content: "Create ADR-0009: Circuit Breaker Resilience (failure isolation)"
    status: completed
  - id: adr-0010
    content: "Create ADR-0010: must_stay_async Decorator (async function protection)"
    status: completed
  - id: adr-0011
    content: "Create ADR-0011: Lazy Initialization Pattern (get_* accessor pattern)"
    status: completed
  - id: adr-0012
    content: "Create ADR-0012: Memory DAG Pipeline (SubstrateDAG node processing)"
    status: completed
  - id: adr-0013
    content: "Create ADR-0013: Governance Authority Hierarchy (Igor > L > Agents)"
    status: completed
---

# 10 High-Impact ADRs for AI-Readable Architecture

## Reasoning: Impact Prioritization

Applied multi-modal reasoning to identify ADRs by:

- **Abductive**: Which patterns do AI agents most frequently misinterpret?
- **Deductive**: Which patterns, if violated, break system invariants?
- **Inductive**: Which patterns are used most frequently across the codebase?

## ADRs Ranked by Impact Score

| ADR | Pattern | Impact | Frequency | AI Misinterpret Risk |

|-----|---------|--------|-----------|---------------------|

| 0004 | Singleton Auto-Registry | HIGH | 15+ modules | HIGH (may remove decorators) |

| 0005 | RLS Shared Tenant Model | CRITICAL | All memory ops | HIGH (may add separate tenants) |

| 0006 | PacketEnvelope Audit Trail | CRITICAL | Every operation | MEDIUM (may skip logging) |

| 0007 | 7-Phase Bootstrap Ceremony | HIGH | Startup | MEDIUM (may simplify) |

| 0008 | Feature Flag Gating | HIGH | 10+ flags | HIGH (may hardcode values) |

| 0009 | Circuit Breaker Resilience | HIGH | Memory/API | MEDIUM (may remove) |

| 0010 | must_stay_async Decorator | MEDIUM | 50+ functions | VERY HIGH (will "fix" async) |

| 0011 | Lazy Initialization Pattern | MEDIUM | All singletons | HIGH (may eager-load) |

| 0012 | Memory DAG Pipeline | CRITICAL | All packets | MEDIUM (may bypass nodes) |

| 0013 | Governance Authority Hierarchy | CRITICAL | All tools | HIGH (may ignore approvals) |

## ADR Format (AI-Optimized)

Each ADR will use minimal verbosity, maximum information density:

```markdown
# ADR XXXX: [Title]

## Status
Accepted

## Pattern
[One-line description]

## Files
[Bullet list of affected files]

## Rules
[Numbered list of invariants]

## AI Guidance
DO: [What to do]
DO NOT: [What not to do]
```

## Implementation Files

All ADRs will be created in [readme/adr/](readme/adr/):

- `0004-singleton-auto-registry.md`
- `0005-rls-shared-tenant-model.md`
- `0006-packet-envelope-audit-trail.md`
- `0007-seven-phase-bootstrap.md`
- `0008-feature-flag-gating.md`
- `0009-circuit-breaker-resilience.md`
- `0010-must-stay-async-decorator.md`
- `0011-lazy-initialization-pattern.md`
- `0012-memory-dag-pipeline.md`
- `0013-governance-authority-hierarchy.md`

## Key Files to Reference

- [core/singleton_auto_registry.py](core/singleton_auto_registry.py) - Auto-registry decorators
- [config/rls_config.py](config/rls_config.py) - RLS UUID configuration
- [core/schemas/packet_envelope_v2.py](core/schemas/packet_envelope_v2.py) - Packet schema
- [core/agents/bootstrap/](core/agents/bootstrap/) - 7-phase bootstrap
- [config/settings.py](config/settings.py) - Feature flags
- [core/observability/circuit_breaker.py](core/observability/circuit_breaker.py) - Circuit breaker
- [core/decorators.py](core/decorators.py) - must_stay_async decorator
- [memory/substrate_dag.py](memory/substrate_dag.py) - DAG pipeline
- [readme/repo-index/governance_model.txt](readme/repo-index/governance_model.txt) - Authority hierarchy

## Post-Implementation

1. Update [readme/adr/README.md](readme/adr/README.md) with new ADRs
2. Update [readme/repo-index/adr_catalog.txt](readme/repo-index/adr_catalog.txt)
3. Verify [core/governance/session_startup.py](core/governance/session_startup.py) loads all ADRs
