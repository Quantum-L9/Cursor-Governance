---
name: Memory Graph Population - 9 Strategies
overview: "Implement 9 remaining memory graph population strategies (beyond /index) for maximum leverage, scale, and utility. Strategies include: fixing semantic search threshold, fixing knowledge fact queries, ensuring extraction pipelines run, and indexing high-value content (GMP reports, Slack conversations, tool usage, errors, architecture, preferences)."
todos:
  - id: fix-semantic-threshold
    content: Add min_score parameter to SemanticSearchRequest model and pass to semantic_search() method to unlock 14,768 embeddings
    status: completed
  - id: fix-knowledge-facts
    content: Fix knowledge facts API query logic to handle empty subject and return all facts when subject is None/empty
    status: completed
  - id: verify-extraction
    content: Create test to verify extraction pipelines (extract_insights_node, store_insights_node) execute automatically on packet ingestion
    status: completed
  - id: index-gmp-reports
    content: Create script to parse GMP reports, extract decisions/lessons, create knowledge facts and semantic embeddings
    status: completed
    dependencies:
      - fix-semantic-threshold
      - fix-knowledge-facts
  - id: index-slack
    content: Extend Slack ingestion to index conversations - extract preferences/corrections, create knowledge facts and embeddings
    status: completed
    dependencies:
      - fix-semantic-threshold
      - fix-knowledge-facts
  - id: index-tool-usage
    content: Create script to index tool usage patterns from tool_audit table to Neo4j graph
    status: completed
  - id: index-errors
    content: Create script to index error patterns from FAILURE packets, create knowledge facts and embeddings
    status: completed
    dependencies:
      - fix-semantic-threshold
      - fix-knowledge-facts
  - id: index-architecture
    content: Create script to index architectural decisions from code comments and GMP reports to Neo4j and knowledge facts
    status: completed
  - id: index-preferences
    content: Create script to index user preferences from preference packets and Slack conversations
    status: completed
    dependencies:
      - fix-semantic-threshold
      - fix-knowledge-facts
---

# L9 ENTERPRISE PLAN: Memory Graph Population - 9 Strategies

**Generated:** 2026-01-09

**Target:** Implement 9 memory graph population strategies for maximum leverage

**Tier:** RUNTIME_TIER (memory substrate, indexing, extraction)

**Confidence:** 0.88

**Protocol Version:** GMP v1.0---

## STATE_SYNC

**Current Phase:** 6 (FINALIZE - Governance Upgrade Complete)

**Context:** L's memory is working in local Docker. Neo4j repo structure loaded via `/index` command (1,000+ files, 1,900+ classes, 4,794+ functions).

**Priority:** Populate memory graphs with remaining strategies for agent context enhancement.**Current Memory Status:**

- Packets: 173
- Embeddings: 14,768 (generated but search returns 0)
- Facts: 298 (exist but retrieval returns 0)
- Neo4j: Repo structure loaded ✅

---

## PROTOCOLS LOADED

| Protocol | Path | Status |

|----------|------|--------|

| GMP-System-Prompt-v1.0 | `docs/_GMP Execute + Audit/GMP-System-Prompt-v1.0.md` | ✅ Loaded |

| GMP-Action-Prompt-Canonical-v1.0 | `docs/_GMP Execute + Audit/GMP-Action-Prompt-Canonical-v1.0.md` | ✅ Loaded |

| GMP-Audit-Prompt-Canonical-v1.0 | `docs/_GMP Execute + Audit/GMP-Audit-Prompt-Canonical-v1.0.md` | ✅ Loaded |**L9 Invariants Check:**

- [x] docker-compose.yml — NOT TOUCHED
- [x] kernel_loader.py — NOT TOUCHED
- [x] executor.py — NOT TOUCHED
- [x] memory_substrate_service.py — ⚠️ TOUCHED (semantic search method)
- [x] websocket_orchestrator.py — NOT TOUCHED

---

## CONTEXT HARVEST

### Chat Context Inventory

| Type | Count | Details |

|------|-------|---------|

| Provided files | 0 | None in current chat |

| Referenced files | 5 | memory/substrate_service.py, memory/substrate_graph.py, api/memory/router.py, memory/substrate_models.py, memory/substrate_repository.py |

| Embedded code blocks | 0 | None |

| External references | 1 | Previous analysis of 10 strategies |

### Existing Artifacts

| Location | Asset | Reusable? | Action |

|----------|-------|-----------|--------|

| memory/substrate_graph.py | extract_insights_node, store_insights_node | ✅ | Already in DAG, verify execution |

| api/memory/router.py | /semantic/search, /facts endpoints | ✅ | Use existing endpoints |

| memory/substrate_service.py | semantic_search(), get_facts_by_subject() | ✅ | Use existing methods |

| reports/ | 4 GMP reports | ✅ | Parse and index |

| memory/slack_ingest.py | Slack ingestion pipeline | ✅ | Extend for indexing |

### Scope Adjustment

- **Original scope:** 9 strategies
- **Net new work:** 9 implementation tasks (fixes + indexing scripts)
- **Time saved:** ~2 hours (leveraging existing DAG nodes, API endpoints, service methods)

---

## ANALYSIS FINDINGS

### Structure Map

**Files in Scope:**

- `memory/substrate_service.py` - Semantic search method (needs threshold parameter)
- `memory/substrate_models.py` - SemanticSearchRequest model (needs threshold field)
- `api/memory/router.py` - API endpoints (semantic search, facts)
- `memory/substrate_graph.py` - Extraction DAG nodes (verify execution)
- `scripts/` - New indexing scripts needed

**Dependencies:**

- Memory substrate service (existing)
- Neo4j graph (loaded via /index)
- PostgreSQL packet store (existing)
- Slack ingestion pipeline (existing)

### Health Scan

**Issues Found:**

1. Semantic search returns 0 results despite 14,768 embeddings - threshold filtering may be too strict
2. Knowledge facts return 0 results despite 298 existing - API endpoint may have query issues
3. Extraction pipelines exist in DAG but may not be triggered for all packets
4. No indexing scripts for GMP reports, Slack conversations, tool usage, errors, architecture, preferences

**L9 Pattern Compliance:**

- ✅ Uses existing memory substrate patterns
- ✅ Follows DAG node structure
- ✅ Uses existing API endpoint patterns
- ⚠️ New indexing scripts need to follow L9 patterns

### Cross-Referenced Findings

**Impact Projection:**

- Fix semantic search: Unlocks 14,768 embeddings for agent context
- Fix knowledge facts: Unlocks 298 facts for structured queries
- Verify extraction: Ensures automatic fact creation from packets
- Index GMP reports: ~47 reports → architectural decisions + lessons
- Index Slack: User preferences + corrections (ongoing)
- Index tool usage: Capability discovery for agents
- Index errors: Faster debugging via pattern matching
- Index architecture: Design rationale preservation
- Index preferences: Personalization for Igor

**Tech Debt Score:** LOW (mostly new features, minimal refactoring)---

## SYNTHESIZED PLAN

### Objective

Implement 9 memory graph population strategies to maximize agent context, enable semantic search, unlock knowledge facts, and index high-value content for compound leverage.

### Success Criteria

- [ ] Semantic search returns results for agent queries (unlocks 14,768 embeddings)
- [ ] Knowledge facts API returns results (unlocks 298 facts)
- [ ] Extraction pipelines verified and working automatically
- [ ] GMP reports indexed (decisions + lessons extracted)
- [ ] Slack conversations indexed (preferences + corrections)
- [ ] Tool usage patterns indexed (capability discovery)
- [ ] Error patterns indexed (faster debugging)
- [ ] Architectural decisions indexed (design rationale)
- [ ] User preferences indexed (personalization)

### Constraints

- Time: ~8-12 hours total (9 strategies, ~1-1.5h each)
- Scope: Memory substrate only, no kernel changes
- Dependencies: Existing memory substrate, Neo4j, PostgreSQL
- Risk tolerance: MEDIUM (touches memory_substrate_service.py)

### Implementation Path

#### Option A: Phased Implementation (RECOMMENDED) ⭐

**Approach:** Implement in 3 tiers: Immediate fixes (2-3h) → Automation verification (1-2h) → Content indexing (5-7h)**Effort:** 8-12 hours total

**Risk:** MEDIUM (touches memory_substrate_service.py)

**Pros:**

- Immediate value from fixes (unlocks existing data)
- Incremental validation at each tier
- Can deploy fixes independently

**Cons:**

- Longer total timeline
- Multiple deployment cycles

#### Option B: All-at-Once Implementation

**Approach:** Implement all 9 strategies in single GMP run**Effort:** 10-14 hours (more coordination overhead)

**Risk:** HIGH (large change set, harder to debug)

**Pros:**

- Single deployment
- All features available together

**Cons:**

- Harder to validate incrementally
- Higher risk of breaking changes
- Longer review cycle

**Recommendation:** Option A (Phased Implementation) - better risk management and incremental value delivery.

### Preliminary TODO Plan

| # | Strategy | Files | Effort | Risk |

|---|----------|-------|--------|------|

| T1-T2 | Fix semantic search threshold | memory/substrate_service.py, memory/substrate_models.py | 1h | LOW |

| T3-T4 | Fix knowledge facts queries | api/memory/router.py, memory/substrate_service.py | 1h | LOW |

| T5 | Verify extraction pipelines | memory/substrate_graph.py, tests | 1h | LOW |

| T6 | Index GMP reports | scripts/index_gmp_reports.py (new) | 2h | MEDIUM |

| T7 | Index Slack conversations | memory/slack_ingest.py (extend) | 1.5h | MEDIUM |

| T8 | Index tool usage patterns | scripts/index_tool_usage.py (new) | 1.5h | MEDIUM |

| T9 | Index error patterns | scripts/index_error_patterns.py (new) | 1.5h | MEDIUM |

| T10 | Index architectural decisions | scripts/index_architecture.py (new) | 1.5h | MEDIUM |

| T11 | Index user preferences | scripts/index_preferences.py (new) | 1h | LOW |

### Dependencies

- **Before:** None (all strategies can start independently)
- **Parallel:** Strategies 1-5 can run in parallel (fixes + verification)
- **After:** Strategies 6-11 depend on fixes being complete (need working semantic search + facts)

---

## REASONING REFINEMENT

### Abductive Analysis (Pattern Discovery)

**Observations:**

- 14,768 embeddings exist but search returns 0 → threshold filtering too strict or missing parameter
- 298 facts exist but retrieval returns 0 → API query logic issue
- Extraction nodes in DAG but may not execute for all packets → verification needed
- High-value content (GMP, Slack, tools, errors) not indexed → scripts needed

**Possible Explanations:**

1. SemanticSearchRequest lacks threshold parameter → service uses default 0.7 (too high)
2. Knowledge facts API requires non-empty subject → empty string query fails
3. Extraction nodes may skip on errors → need to verify DAG execution
4. No indexing scripts exist → need to create extraction + storage scripts

**Hypothesis:** Add threshold parameter to semantic search, fix knowledge facts query logic, verify extraction DAG execution, create indexing scripts for high-value content.**Confidence:** 0.90

### Deductive Analysis (Logical Validation)

**Premises:**

1. Semantic search uses cosine similarity (0-1 scale)
2. Default threshold of 0.7 may filter all results if embeddings are diverse
3. Knowledge facts API exists but may have query parameter issues
4. Extraction DAG nodes exist and are connected in graph
5. Indexing scripts can use existing memory substrate APIs

**Logical Check:**

- IF we add threshold parameter to SemanticSearchRequest THEN service can use lower threshold
- IF we fix knowledge facts query logic THEN API will return results
- IF we verify DAG execution THEN extraction will work automatically
- IF we create indexing scripts THEN high-value content will be indexed

**Validation Result:** PASS - all logical steps are sound

**Confidence:** 0.95

### Inductive Analysis (Pattern Generalization)

**Prior Examples:**

1. `/index` command loaded repo structure successfully → indexing scripts work
2. Memory substrate has working APIs → can be used by indexing scripts
3. Extraction nodes exist in DAG → pattern for automatic extraction established

**Generalized Principle:** Use existing memory substrate APIs and DAG patterns for all indexing. Fix API issues first, then build indexing scripts.**Applicability:** HIGH - all strategies follow this pattern

**Confidence:** 0.90

### Synthesis

**Refined Path:** Phased implementation with immediate fixes first, then automation verification, then content indexing.**Key Refinements:**

- Add threshold parameter with default 0.5 (broader results)
- Fix knowledge facts API to handle empty subject queries
- Verify extraction DAG with test packet ingestion
- Create reusable indexing script pattern for all content types

**Risk Mitigations:**

- Memory substrate changes → Add tests for semantic search + facts
- Indexing scripts → Use existing API patterns, validate before bulk indexing
- Large content volumes → Batch processing, rate limiting

**Blind Spots Identified:**

- Semantic search threshold may need tuning per query type
- Knowledge facts may need better subject extraction
- Indexing scripts may need deduplication logic

**Overall Confidence Score:** 0.88---

## APPROVAL PACKAGE (Protocol-Compliant)

### Executive Summary

Implement 9 memory graph population strategies in 3 phases: (1) Fix semantic search threshold and knowledge facts queries to unlock existing data, (2) Verify extraction pipelines are working automatically, (3) Create indexing scripts for GMP reports, Slack conversations, tool usage, errors, architecture, and preferences.

### Plan Metrics

| Metric | Value |

|--------|-------|

| Files affected | 5 existing + 5 new scripts |

| Estimated effort | 8-12 hours |

| Risk level | MEDIUM |

| Confidence score | 0.88 |

| Tier classification | RUNTIME_TIER |

| L9 Invariants touched | YES - memory_substrate_service.py (semantic search method) |

### Recommended Path

**Option A: Phased Implementation** - Immediate fixes unlock existing data, then verification, then content indexing. Better risk management and incremental value.

### Risk Assessment

| Risk | Probability | Impact | Mitigation |

|------|------------|--------|------------|

| Semantic search threshold breaks existing queries | LOW | MEDIUM | Add parameter with default 0.5, test with sample queries |

| Knowledge facts API changes break clients | LOW | MEDIUM | Maintain backward compatibility, add tests |

| Indexing scripts create duplicate facts | MEDIUM | LOW | Add deduplication logic, use content_hash |

| Large content volumes slow indexing | MEDIUM | LOW | Batch processing, rate limiting, async execution |---

## GMP-READY TODO PLAN (Canonical Format)

### TODO PLAN (LOCKED)

- [T1] File: `/Users/ib-mac/Projects/L9/memory/substrate_models.py`

Lines: 336-342

Action: Insert

Target: `SemanticSearchRequest` class

Change: Add `min_score: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity score threshold")` field after `agent_id` field

Gate: py_compile

Imports: NONE

- [T2] File: `/Users/ib-mac/Projects/L9/memory/substrate_service.py`

Lines: 250-280 (semantic_search method)

Action: Replace

Target: `semantic_search()` method

Change: Pass `min_score` parameter from request to `retrieval_pipeline.semantic_search()` call, default to 0.5 if not provided

Gate: py_compile

Imports: NONE

- [T3] File: `/Users/ib-mac/Projects/L9/api/memory/router.py`

Lines: 319-345

Action: Replace

Target: `get_facts()` endpoint

Change: Fix query logic to handle empty subject string - if subject is None or empty, return all facts (limit by limit parameter), otherwise filter by subject

Gate: py_compile

Imports: NONE

- [T4] File: `/Users/ib-mac/Projects/L9/memory/substrate_service.py`

Lines: 686-708

Action: Replace

Target: `get_facts_by_subject()` method

Change: If subject is empty string, modify repository call to return all facts (remove subject filter), otherwise use existing subject filter

Gate: py_compile

Imports: NONE

- [T5] File: `/Users/ib-mac/Projects/L9/tests/memory/test_extraction_pipeline.py` (new file)

Lines: 1-100

Action: Insert

Target: New test file

Change: Create test that ingests sample packet, verifies extract_insights_node and store_insights_node execute, and checks knowledge_facts table for new facts

Gate: pytest

Imports: `import pytest`, `from memory.substrate_service import MemorySubstrateService`, `from memory.substrate_models import PacketEnvelopeIn`

- [T6] File: `/Users/ib-mac/Projects/L9/scripts/index_gmp_reports.py` (new file)

Lines: 1-300

Action: Insert

Target: New script file

Change: Create script that parses GMP reports from reports/ directory, extracts decisions and lessons, creates knowledge facts (subject=GMP-ID, predicate=decided/learned, object=content), and creates semantic embeddings for full reports. Use memory substrate APIs.

Gate: py_compile

Imports: `import json`, `import re`, `from pathlib import Path`, `from memory.substrate_service import MemorySubstrateService`, `from memory.substrate_models import PacketEnvelopeIn`

- [T7] File: `/Users/ib-mac/Projects/L9/memory/slack_ingest.py`

Lines: 1350-1400 (approximate, find _retrieve_semantic_hits area)

Action: Insert

Target: After Slack message ingestion

Change: Add call to index Slack conversation - extract user preferences and corrections, create knowledge facts (subject=Igor, predicate=prefers/corrects, object=pattern), create semantic embeddings for conversation context

Gate: py_compile

Imports: NONE (use existing imports)

- [T8] File: `/Users/ib-mac/Projects/L9/scripts/index_tool_usage.py` (new file)

Lines: 1-200

Action: Insert

Target: New script file

Change: Create script that queries tool_audit table, extracts tool usage patterns (tool_id, usage_count, success_rate), creates Neo4j nodes (Tool {name, usage_count, success_rate}), links to agents via USES relationship. Use Neo4j API.

Gate: py_compile

Imports: `import asyncio`, `from memory.substrate_repository import SubstrateRepository`, `from neo4j import GraphDatabase`

- [T9] File: `/Users/ib-mac/Projects/L9/scripts/index_error_patterns.py` (new file)

Lines: 1-250

Action: Insert

Target: New script file

Change: Create script that queries packet_store for packets with kind=FAILURE, extracts error_type, error_message, fix_applied, creates knowledge facts (subject=error_type, predicate=fixed_by, object=solution), creates semantic embeddings for error context. Use memory substrate APIs.

Gate: py_compile

Imports: `import json`, `import re`, `from memory.substrate_repository import SubstrateRepository`, `from memory.substrate_service import MemorySubstrateService`

- [T10] File: `/Users/ib-mac/Projects/L9/scripts/index_architecture.py` (new file)

Lines: 1-200

Action: Insert

Target: New script file

Change: Create script that parses code comments with "ARCHITECTURE:" or "DECISION:" markers, extracts from GMP reports architectural choices, creates knowledge facts (subject=component, predicate=designed_as, object=rationale), links components via ARCHITECTED_BY relationship in Neo4j. Use memory substrate APIs and Neo4j API.

Gate: py_compile

Imports: `import re`, `from pathlib import Path`, `from memory.substrate_service import MemorySubstrateService`, `from neo4j import GraphDatabase`

- [T11] File: `/Users/ib-mac/Projects/L9/scripts/index_preferences.py` (new file)

Lines: 1-150

Action: Insert

Target: New script file

Change: Create script that queries packet_store for packets with kind=preference, extracts from Slack user corrections and stated preferences, creates knowledge facts (subject=Igor, predicate=prefers, object=pattern), creates semantic embeddings for preference context. Use memory substrate APIs.

Gate: py_compile

Imports: `import json`, `from memory.substrate_repository import SubstrateRepository`, `from memory.substrate_service import MemorySubstrateService`

### TODO INDEX HASH

```javascript
SHA256(TODO_PLAN_TEXT) = [auto-generated on execution]
```



### L9 INVARIANT CHECK

| Invariant File | Touched? | Justification |

|----------------|----------|---------------|

| docker-compose.yml | NO | — |

| kernel_loader.py | NO | — |

| executor.py | NO | — |

| memory_substrate_service.py | YES | Adding min_score parameter to semantic_search() method - required for unlocking 14,768 embeddings |

| websocket_orchestrator.py | NO | — |---

### Approval Request

**Requesting approval for:**

- [ ] Proceed with phased implementation (Option A)
- [ ] Allocate 8-12 hours for implementation
- [ ] Accept MEDIUM risk with mitigations (tests, backward compatibility)
- [ ] L9 invariants: memory_substrate_service.py touched with justification

**Approval authority required:**

- RUNTIME_TIER: Proceed with monitoring

### Execution Command

Once approved, execute with:

```javascript
/gmp @generated/plans/PLAN-20260109-memory-graph-population.md
```

Or copy the TODO PLAN (LOCKED) section directly into a new /gmp invocation.

### Protocol References

- GMP-System-Prompt: `docs/_GMP Execute + Audit/GMP-System-Prompt-v1.0.md`
- GMP-Action-Prompt: `docs/_GMP Execute + Audit/GMP-Action-Prompt-Canonical-v1.0.md`
- GMP-Audit-Prompt: `docs/_GMP Execute + Audit/GMP-Audit-Prompt-Canonical-v1.0.md`

---

## YNP RECOMMENDATION

**IF APPROVED:**

Primary: `/gmp` with TODO Plan from Phase 4

Scope: 11 TODOs across 5 existing files + 5 new scripts

Estimated time: 8-12 hours (phased: 2-3h fixes, 1-2h verification, 5-7h indexing)**IF NEEDS REFINEMENT:**

Primary: Re-run `/plan` with clarified constraints

Focus: Specify which strategies to prioritize if not all 9**IF DEFERRED:**

Primary: Update workflow_state.md with plan for later

Next: Focus on immediate fixes (T1-T4) only**Alternates:**

1. Implement fixes only (T1-T4) - 2-3h, unlocks existing data immediately
2. Implement fixes + verification (T1-T5) - 3-4h, ensures automation works
3. Implement all strategies in single GMP - 10-14h, all features together

---

## PLAN METADATA

```yaml
plan:
  id: PLAN-20260109-memory-graph-population
  target: 9 memory graph population strategies
  tier: RUNTIME_TIER
  generated: 2026-01-09
  protocol_version: "GMP-v1.0"

  protocols_loaded:
    - GMP-System-Prompt-v1.0: ✅
    - GMP-Action-Prompt-Canonical-v1.0: ✅
    - GMP-Audit-Prompt-Canonical-v1.0: ✅

  phases_completed:
    - state_sync: ✅
    - protocol_load: ✅
    - context_harvest: ✅
    - analyze_evaluate: ✅
    - synthesis: ✅
    - reasoning: ✅
    - approval_gen: ✅

  confidence:
    abductive: 0.90
    deductive: 0.95
    inductive: 0.90
    overall: 0.88

  l9_invariants:
    docker_compose: NOT_TOUCHED
    kernel_loader: NOT_TOUCHED
    executor: NOT_TOUCHED
    memory_substrate: TOUCHED (semantic_search method - justified)
    websocket_orchestrator: NOT_TOUCHED

  approval:
    authority_required: RUNTIME_TIER (proceed with monitoring)
    status: PENDING

  execution:
    next_command: "/gmp"
    todo_count: 11
    estimated_effort: "8-12 hours"
    todo_format: "GMP-Action-Canonical-v1.0"

```
