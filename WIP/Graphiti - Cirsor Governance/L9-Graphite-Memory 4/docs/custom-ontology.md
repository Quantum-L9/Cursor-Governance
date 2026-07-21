<!-- L9_META
l9_schema: 1
parent: l9-graphite-memory
layer: docs
role: guide
tags: [ontology, customization, knowledge-graph, schema]
owner: platform
status: active
version: 1.0.0
updated: 2026-07-05
/L9_META -->

# Custom Ontology Guide

This document describes how to extend the L9 Graphite Memory knowledge graph with custom entity types, relationship types, and domain-specific schemas.

## Overview

The default ontology includes:

| Entity Type | Description |
|---|---|
| `fact` | A discrete piece of knowledge extracted from episodes |
| `episode` | A raw input event (code change, decision, observation) |
| `session` | A group of related episodes (maps to Zep session) |
| `integration_edge` | A relationship between two groups/repos |

## Extending the Ontology

### 1. Custom Episode Kinds

The `kind` field on episodes controls how facts are extracted. Default kinds:

```yaml
kinds:
  - lesson        # Learned insight
  - decision      # Architectural or process decision
  - observation   # Passive observation
  - manifest      # Repo/system manifest (bootstrap)
  - integration   # Cross-repo integration edge
```

To add a custom kind, update `config/domain_packs/` with a YAML file:

```yaml
# config/domain_packs/plasticos.yaml
name: plasticos
kinds:
  - module_spec    # PlasticOS module specification
  - pricing_rule  # Pricing engine rule
  - buyer_match   # Buyer matching result
fact_extraction:
  module_spec:
    extract_entities: true
    entity_types: ["module", "dependency", "api_endpoint"]
  pricing_rule:
    extract_entities: true
    entity_types: ["material", "grade", "price_point"]
```

### 2. Custom Fact Rating Instructions

Zep Cloud supports custom fact rating instructions that control how facts are scored for relevance:

```python
from l9_graphite_memory.transport import get_transport

transport = get_transport()
# When using Zep Cloud, session-level fact rating can be configured:
transport.call_tool("add_episode", {
    "body": "PET flake prices increased 15% in Q2 2026",
    "group_id": "market-intelligence",
    "fact_instruction": "Rate higher if the fact contains specific pricing data with dates",
})
```

### 3. Group Isolation and Cross-Group Queries

Groups provide tenant isolation in the knowledge graph. Each group maps to a Zep session:

```yaml
# config/group_registry.yaml
workspace_group: igor-workspace
repos:
  cursor-governance:
    github: "https://github.com/Quantum-L9/Cursor-Governance"
    integrates_with: [l9-graphite-memory, infisical-config]
  l9-graphite-memory:
    github: "https://github.com/Quantum-L9/L9-Graphite-Memory"
    integrates_with: [infisical-config]
```

Cross-group queries use the `resolve_read_groups()` function which always includes the workspace group:

```python
# Reading from a specific group also reads the workspace
read_groups = resolve_read_groups("cursor-governance")
# Returns: ["cursor-governance", "igor-workspace"]
```

### 4. Entity Extraction Configuration

When using Zep Cloud, entity extraction is handled server-side. To influence what entities are extracted, use the `fact_instruction` parameter:

```python
# Guide entity extraction for domain-specific content
transport.write(
    body="Module plasticos_pricing v2.3 depends on plasticos_base and exposes /api/v1/quotes",
    group_id="plasticos-erp",
    kind="module_spec",
    fact_instruction="Extract module names, version numbers, API endpoints, and dependency relationships",
)
```

### 5. Temporal Queries

The knowledge graph is bi-temporal — facts have both an event time (when the thing happened) and a record time (when it was stored). To query by time:

```python
# Search with temporal context
results = transport.search(
    query="pricing decisions made in June 2026",
    group_id="market-intelligence",
    limit=20,
)
```

## Domain Pack Structure

```
config/domain_packs/
├── default.yaml          # Base ontology (always loaded)
├── governance.yaml       # L9 governance domain
├── plasticos.yaml        # PlasticOS ERP domain
└── market_intel.yaml     # Market intelligence domain
```

Each domain pack can define:
- Custom `kinds` for episodes
- `fact_extraction` rules per kind
- `entity_types` to look for
- `relationship_types` between entities
- `rating_instructions` for fact scoring

## Limitations

1. **Zep Cloud mode**: Entity extraction is server-side; custom entity types are advisory (via `fact_instruction`), not enforced.
2. **HTTP MCP mode**: Entity extraction depends on the self-hosted Graphiti server configuration.
3. **Cross-group writes**: Only the workspace group can receive integration edges from other groups.
4. **Schema evolution**: Adding new kinds is non-breaking; removing kinds requires migration of existing episodes.
