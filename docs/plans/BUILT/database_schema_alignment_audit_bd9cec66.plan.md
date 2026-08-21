---
name: Database Schema Alignment Audit
overview: Audit all Python files containing SQL queries against the actual PostgreSQL schema to identify and fix column name mismatches, ensuring all code is compliant with the database schema.
todos:
  - id: fix-cost-usd
    content: Fix cost_cents → cost_usd in tool_pattern_extractor.py Python logic
    status: completed
  - id: audit-substrate-repo
    content: Audit memory/substrate_repository.py SQL queries against schema
    status: completed
  - id: audit-retrieval
    content: Audit memory/retrieval.py SQL queries against schema
    status: completed
  - id: audit-tool-audit
    content: Audit memory/tool_audit.py and core/tools/tool_audit.py INSERT statements
    status: completed
  - id: audit-api-router
    content: Audit api/memory/router.py SQL queries
    status: completed
  - id: audit-world-model
    content: Audit world_model/repository.py SQL queries
    status: completed
  - id: validate-docker
    content: Rebuild container and verify no SQL errors in logs
    status: completed
  - id: update-tests
    content: Update test fixtures to use correct column names (cost_usd not cost_cents)
    status: completed
---

# Database Schema Alignment Audit Plan

## Objective

Systematically audit all Python files that interact with PostgreSQL to ensure SQL queries use correct column names matching the actual database schema.

## Current State

The L9 memory substrate has 25 tables in PostgreSQL. During Neo4j wiring debugging, I discovered that `tool_pattern_extractor.py` was using incorrect column names (`success`, `created_at`, `cost_cents`) that don't exist in the `tool_audit_log` table.**Already Fixed:**

- `tool_pattern_extractor.py` SQL query (lines 194-203): Fixed column names in SELECT

**Still Needs Fixing:**

- `tool_pattern_extractor.py` Python logic (lines 268-269): Uses `cost_cents` but query returns `cost_usd`

## Files Requiring Audit

Based on grep analysis, these 18 active Python files contain SQL queries:| File | Tables Referenced | Priority |

|------|-------------------|----------|

| [`memory/substrate_repository.py`](memory/substrate_repository.py) | packet_store, semantic_memory, knowledge_facts | HIGH |

| [`memory/retrieval.py`](memory/retrieval.py) | packet_store, knowledge_facts | HIGH |

| [`memory/tool_audit.py`](memory/tool_audit.py) | tool_audit_log | HIGH |

| [`core/tools/tool_audit.py`](core/tools/tool_audit.py) | tool_audit_log | HIGH |

| [`core/integration/tool_pattern_extractor.py`](core/integration/tool_pattern_extractor.py) | tool_audit_log | HIGH |

| [`api/memory/router.py`](api/memory/router.py) | packet_store, semantic_memory, knowledge_facts | MEDIUM |

| [`world_model/repository.py`](world_model/repository.py) | world_model_entities, world_model_updates | MEDIUM |

| [`memory/housekeeping.py`](memory/housekeeping.py) | Various tables | MEDIUM |

| [`memory/index_syncer.py`](memory/index_syncer.py) | memory_embeddings | MEDIUM |

| [`memory/migration_runner.py`](memory/migration_runner.py) | schema_migrations | LOW |

| [`core/governance/cursor_memory_kernel.py`](core/governance/cursor_memory_kernel.py) | Various tables | LOW |

| [`mcp_memory/src/routes/memory.py`](mcp_memory/src/routes/memory.py) | packet_store | LOW |

## Execution Strategy

### Phase 1: Fix Known Issue

Fix `cost_cents` → `cost_usd` mismatch in `tool_pattern_extractor.py`

### Phase 2: Audit HIGH Priority Files

For each file:

1. Extract all SQL queries
2. Cross-reference column names against actual schema
3. Verify data types match
4. Check INSERT statements match table columns

### Phase 3: Audit MEDIUM Priority Files

Same process for medium priority files

### Phase 4: Validation

1. Run existing tests
2. Docker container restart verification
3. Verify no runtime errors in logs

## Known Schema Reference (Key Tables)

**tool_audit_log:**

- `id` (bigint)
- `tool_name` (varchar)
- `agent_id` (varchar)
- `duration_ms` (double)
- `cost_usd` (double) - NOT cost_cents
- `error` (text) - success is derived: `error IS NULL`
- `timestamp` (timestamptz) - NOT created_at
- `request_id` (uuid)

**packet_store:**

- `packet_id` (uuid) - NOT id
- `timestamp` (timestamptz) - NOT created_at
- `packet_type` (text)
- `envelope` (jsonb)

## Risk Assessment

- **Risk Level:** MEDIUM
- **Impact:** Runtime errors if SQL queries use wrong columns
- **Rollback:** Changes are surgical, easy to revert

## Definition of Done

- All SQL queries use correct column names
- No "column does not exist" errors in container logs
- Existing tests pass