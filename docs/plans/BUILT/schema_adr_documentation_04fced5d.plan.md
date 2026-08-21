---
name: Schema ADR Documentation
overview: Create an ADR documenting the dual-pattern schema architecture (centralized core + domain-colocated) to make the existing organization discoverable and maintainable.
todos:
  - id: create-adr
    content: Create ADR-0036 documenting the dual-pattern schema architecture following adr_schema.yaml format
    status: completed
  - id: update-adr-readme
    content: Add ADR-0036 to readme/adr/README.md index
    status: completed
---

# ADR for Schema Organization Pattern

## Decision

Document the existing dual-pattern schema architecture as **ADR-0036** (next available number based on existing ADRs up to 0035).

## Key Content for ADR

### Pattern Summary

L9 uses a **hybrid schema organization**:

- **Core schemas** (`core/schemas/`) — Cross-domain infrastructure (PacketEnvelope, Tasks, Events, Security)
- **Domain schemas** (`{domain}/schemas.py`) — Domain-specific models colocated with their domain

### Files to Reference

| Location | Purpose |
|----------|---------|
| `core/schemas/` | Infrastructure schemas - packets, tasks, events, research factory |
| `core/agents/schemas.py` | Agent task, config, tool binding models |
| `core/kernels/schemas.py` | Kernel manifest Pydantic models |
| `core/governance/schemas.py` | Policy evaluation models |
| `core/commands/schemas.py` | Command parsing models |
| `core/worldmodel/l9_schema.py` | Entity/relationship models |
| `core/agents/graph_state/schema.py` | Neo4j Cypher query definitions |
| `ir_engine/ir_schema.py` | Intent representation models |
| `config/schemas/` | YAML validation schemas (ADR format, GMP scope) |

### Rules to Codify

1. **Cross-domain schemas** (used by 3+ domains) MUST go in `core/schemas/`
2. **Domain-specific schemas** SHOULD be colocated as `{domain}/schemas.py`
3. **YAML validation schemas** go in `config/schemas/`
4. All schema modules MUST export `__all__` for discoverability
5. New schemas MUST follow existing naming: `schemas.py` or `{domain}_schema.py`

### AI Guidance Section

**DO:**

- Check `core/schemas/` first for infrastructure models
- Look for `schemas.py` in the domain folder for domain-specific models
- Import from the canonical location (don't re-export)

**DO NOT:**

- Consolidate all schemas into one folder
- Create new schema folders outside this pattern
- Duplicate models across locations

## Implementation

Create: `readme/adr/0036-schema-organization-pattern.md`

Follow the schema format from `config/schemas/adr_schema.yaml` which requires:

- Status
- Pattern (1-2 sentences)
- Files (bullet list)
- Rules (numbered MUST/MUST NOT)
- AI Guidance (DO/DO NOT)
- Import Block (copy-paste ready)
- Minimal Implementation (example)