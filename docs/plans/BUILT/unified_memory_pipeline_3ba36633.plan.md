---
name: Unified Memory Pipeline
overview: "Unify the three memory ingestion paths into a single canonical pipeline: IngestionPipeline as primary with SubstrateDAG as optional enrichment layer. Eliminate MCP direct DB bypass and add tiered fallback for resilience."
todos:
  - id: T1
    content: "Extend PacketWriteResult with typed enrichment fields: enrichment_status (Literal enum), enrichment_error, enrichment_facts_count, write_tier_used, warnings"
    status: completed
  - id: T2
    content: Add EnrichmentResult dataclass to memory/substrate_models.py with facts, insights, reasoning_trace fields
    status: completed
  - id: T3
    content: Add insert_knowledge_fact() method to repository with UPSERT (ON CONFLICT), return KnowledgeFactRow, proper exception handling
    status: completed
  - id: T4
    content: Add SubstrateDAG.enrich() with pre-validation, preload_state pattern, skips intake/write/embed nodes
    status: completed
  - id: T5
    content: Update store_insights_node to call repository.insert_knowledge_fact() with idempotent UPSERT
    status: completed
  - id: T6
    content: Add ENABLE_DAG_ENRICHMENT feature flag to config/memory_substrate_settings.py (default=False)
    status: completed
  - id: T7
    content: Wire DAG enrichment into IngestionPipeline.__init__() with dag and enable_enrichment params
    status: completed
  - id: T8
    content: Add enrichment call after core writes in IngestionPipeline.ingest() - NO RETRY on failure, just log
    status: completed
  - id: T9
    content: "Refactor MCP tiered fallback: enrichment failure = 200 with status, core failure = try direct DB, direct failure = 503"
    status: completed
  - id: T10
    content: Wire IngestionPipeline result through to MCP HTTP response with all enrichment/tier fields
    status: completed
  - id: T11
    content: "Create tests: core writes, enrichment, fallback tiers, idempotency (no duplicate facts), enrichment timeout"
    status: completed
---

# GMP-67: Unified Memory Pipeline Architecture (v2 - REVISED)

## Variable Bindings

```yaml
TASK_NAME: unified_memory_pipeline
EXECUTION_SCOPE: |
  Consolidate 3 memory write paths into 1 canonical pipeline:
  1. IngestionPipeline (primary)
  2. SubstrateDAG (optional enrichment)
  3. MCP direct DB → FALLBACK ONLY (not eliminated, but last resort)
RISK_LEVEL: High
IMPACT_METRICS: Memory write reliability, DAG enrichment availability, MCP resilience
VALIDATION_NOTES: Test with ENABLE_DAG_ENRICHMENT=false first, then =true
```

## Current State (Problem)

Three parallel write paths exist:
- [memory/ingestion.py](memory/ingestion.py) `ingest_packet()` - Production path, bypasses DAG
- [memory/substrate_dag.py](memory/substrate_dag.py) `SubstrateDAG.run()` - Full DAG but NOT used
- [mcp_memory/src/routes/memory_unified.py](mcp_memory/src/routes/memory_unified.py) `_save_via_direct_db()` - Direct INSERT fallback

## Target Architecture

```
ingest_packet()
      │
      ▼
IngestionPipeline.ingest()  [CORE WRITES - always runs first]
      │
      │ (if ENABLE_DAG_ENRICHMENT=True AND core succeeded)
      ▼
SubstrateDAG.enrich()  [ENRICHMENT ONLY - runs ONCE, no retry]
      │
      │ (enrichment failure = log + return 200 with enrichment_status="failed")
      ▼
Return PacketWriteResult with enrichment_status, tier_used, warnings
```

## MCP Tiered Fallback (CORRECTED)

```
Tier 1: Try IngestionPipeline.ingest() (core + enrichment if enabled)
        │
        ├─ IF enrichment fails: Log, set enrichment_status="failed", return 200
        │   (NO RETRY - core write already succeeded)
        │
        ├─ IF core write fails: Fall to Tier 2
        │
Tier 2: Try _save_via_direct_db() (emergency fallback)
        │
        ├─ IF success: Return 200 with tier_used="direct_db", warnings=["pipeline_unavailable"]
        │
        ├─ IF fails: Fall to Tier 3
        │
Tier 3: Return 503 Service Unavailable
```

**Key invariant:** Enrichment is NEVER retried. If it fails, core write already persisted, just log the error.

---

## Phase 1: Foundation (Schema + Repository)

### T1: Extend PacketWriteResult with typed enrichment fields

- **File:** [core/schemas/packet_envelope_v2.py](core/schemas/packet_envelope_v2.py)
- **Lines:** 399-409
- **Action:** MODIFY PacketWriteResult class
- **Change:** Add typed fields for enrichment visibility

```python
class PacketWriteResult(BaseModel):
    """Result of writing a PacketEnvelope."""

    # Existing fields
    status: str = Field(..., description="'ok' or 'error'")
    packet_id: UUID = Field(..., description="Echoed packet ID")
    written_tables: list[str] = Field(default_factory=list, description="Tables updated")
    error_message: Optional[str] = Field(None, description="Error details if status='error'")

    # NEW: Enrichment visibility (v2.1.0)
    enrichment_status: Literal["not_attempted", "success", "failed", "disabled"] = Field(
        default="not_attempted",
        description="DAG enrichment outcome"
    )
    enrichment_error: Optional[str] = Field(None, description="Enrichment error if failed")
    enrichment_facts_count: int = Field(default=0, description="Number of facts extracted")

    # NEW: Resilience tracking (v2.1.0)
    write_tier_used: Literal["full", "core_only", "direct_db", "failed"] = Field(
        default="full",
        description="Which write tier succeeded"
    )
    warnings: list[str] = Field(default_factory=list, description="Non-fatal warnings")
```

### T2: Add EnrichmentResult dataclass

- **File:** [memory/substrate_models.py](memory/substrate_models.py)
- **Lines:** 553 (end of file)
- **Action:** INSERT
- **Change:** Add structured output for DAG enrichment

```python
class EnrichmentResult(BaseModel):
    """Result of SubstrateDAG.enrich() execution."""
    
    packet_id: UUID = Field(..., description="Source packet that was enriched")
    
    # Extracted data
    facts: list[KnowledgeFact] = Field(default_factory=list, description="Extracted knowledge facts")
    insights: list[ExtractedInsight] = Field(default_factory=list, description="Extracted insights")
    reasoning_trace: Optional[StructuredReasoningBlock] = Field(None, description="Reasoning trace if generated")
    
    # Metrics
    facts_inserted: int = Field(default=0, description="Facts persisted to knowledge_facts table")
    world_model_triggered: bool = Field(default=False, description="Whether world model update was triggered")
    
    # Timing
    enrichment_duration_ms: float = Field(default=0.0, description="Enrichment execution time")
```

### T3: Add insert_knowledge_fact method with UPSERT

- **File:** [memory/substrate_repository.py](memory/substrate_repository.py)
- **Lines:** 530 (after reasoning traces section)
- **Action:** INSERT
- **Change:** Add idempotent fact insertion with UPSERT

```python
async def insert_knowledge_fact(
    self,
    fact: KnowledgeFact,
    packet_id: UUID,
) -> KnowledgeFactRow:
    """
    Insert or update knowledge fact (idempotent via UPSERT).
    
    Uses ON CONFLICT (source_packet, subject, predicate) DO UPDATE
    to prevent duplicate facts from same packet.
    
    Args:
        fact: KnowledgeFact to persist
        packet_id: Source packet ID (foreign key)
        
    Returns:
        KnowledgeFactRow with assigned fact_id
        
    Raises:
        Exception: DB error (caller decides whether to propagate or log)
    """
    rls_conn = _current_rls_connection.get()
    conn = rls_conn or await self._pool.acquire()
    
    try:
        # UPSERT: Insert or update on conflict
        row = await conn.fetchrow(
            """
            INSERT INTO knowledge_facts (
                fact_id, subject, predicate, object, confidence, source_packet, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (source_packet, subject, predicate) 
            DO UPDATE SET 
                object = EXCLUDED.object,
                confidence = EXCLUDED.confidence
            RETURNING *
            """,
            fact.fact_id,
            fact.subject,
            fact.predicate,
            json.dumps(fact.object) if not isinstance(fact.object, str) else fact.object,
            fact.confidence,
            packet_id,
            fact.created_at or datetime.utcnow(),
        )
        logger.debug(f"Upserted knowledge fact {row['fact_id']} for packet {packet_id}")
        return KnowledgeFactRow(**dict(row))
    finally:
        if not rls_conn:
            await self._pool.release(conn)
```

**Note:** Requires adding unique constraint to knowledge_facts table:
```sql
-- Migration 0015 (if not exists)
CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_facts_upsert_key
    ON knowledge_facts (source_packet, subject, predicate)
    WHERE source_packet IS NOT NULL;
```

---

## Phase 2: SubstrateDAG Enrichment Mode

### T4: Add SubstrateDAG.enrich() with pre-validation

- **File:** [memory/substrate_dag.py](memory/substrate_dag.py)
- **Lines:** 836 (after existing run() method)
- **Action:** ADD_METHOD
- **Change:** Add enrichment-only execution path with pre-validation

```python
async def enrich(
    self,
    envelope: PacketEnvelope,
    preload_state: Optional[dict[str, Any]] = None,
) -> EnrichmentResult:
    """
    Run ENRICHMENT ONLY pipeline on already-persisted packet.
    
    SKIPS: intake_node, memory_write_node, semantic_embed_node (already done by IngestionPipeline)
    RUNS: reasoning_node → extract_insights_node → store_insights_node → world_model_trigger_node
    
    Pre-validation: Envelope must have packet_id, packet_type, payload populated.
    State is pre-hydrated from envelope (no DB reads required).
    
    Args:
        envelope: Already-persisted PacketEnvelope
        preload_state: Optional pre-hydrated state (for testing or custom workflows)
        
    Returns:
        EnrichmentResult with extracted facts, insights, metrics
        
    Raises:
        ValueError: If envelope is missing required fields
    """
    import time
    start_time = time.time()
    
    # Pre-validation: envelope must be fully populated
    if not envelope.packet_id:
        raise ValueError("Envelope must have packet_id (already persisted)")
    if not envelope.packet_type:
        raise ValueError("Envelope must have packet_type")
    if not envelope.payload:
        raise ValueError("Envelope must have payload")
    
    # Pre-hydrate state from envelope (skip intake_node's DB reads)
    state: SubstrateGraphState = preload_state or {
        "envelope": envelope.model_dump(mode="json"),
        "reasoning_block": None,
        "written_tables": [],  # Not writing core tables
        "embedding_id": None,  # Already embedded
        "saved_checkpoint_id": None,
        "insights": [],
        "facts": [],
        "world_model_triggered": False,
        "errors": [],
    }
    
    # Run enrichment nodes ONLY (skip intake, memory_write, semantic_embed)
    state = await reasoning_node(state, repository=self._repository)
    state = await extract_insights_node(state, repository=self._repository)
    state = await store_insights_node(state, repository=self._repository)
    state = await world_model_trigger_node(
        state,
        repository=self._repository,
        world_model_service=self._world_model_service,
    )
    
    # Build result
    duration_ms = (time.time() - start_time) * 1000
    
    return EnrichmentResult(
        packet_id=envelope.packet_id,
        facts=[KnowledgeFact(**f) for f in state.get("facts", [])],
        insights=[ExtractedInsight(**i) for i in state.get("insights", [])],
        reasoning_trace=StructuredReasoningBlock(**state["reasoning_block"]) if state.get("reasoning_block") else None,
        facts_inserted=len(state.get("facts", [])),
        world_model_triggered=state.get("world_model_triggered", False),
        enrichment_duration_ms=duration_ms,
    )
```

### T5: Update store_insights_node with idempotent UPSERT

- **File:** [memory/substrate_dag.py](memory/substrate_dag.py)
- **Lines:** 582-631
- **Action:** MODIFY
- **Change:** Wire repository.insert_knowledge_fact() call

```python
async def store_insights_node(
    state: SubstrateGraphState, repository=None
) -> SubstrateGraphState:
    """
    Store extracted insights and facts to database.
    
    Uses UPSERT to ensure idempotency (same packet enriched twice = no duplicates).
    """
    logger.debug("store_insights_node: Storing insights and facts")

    insights = state.get("insights", [])
    facts = state.get("facts", [])
    errors = list(state.get("errors", []))
    written_tables = list(state.get("written_tables", []))
    
    packet_id = state.get("envelope", {}).get("packet_id")

    if not insights and not facts:
        logger.debug("store_insights_node: No insights or facts to store")
        return state

    if repository is None:
        logger.warning("store_insights_node: No repository, skipping persistence")
        return state

    try:
        # Store facts via UPSERT (idempotent)
        facts_inserted = 0
        for fact_dict in facts:
            fact = KnowledgeFact(**fact_dict) if isinstance(fact_dict, dict) else fact_dict
            await repository.insert_knowledge_fact(
                fact=fact,
                packet_id=UUID(packet_id) if packet_id else fact.source_packet,
            )
            facts_inserted += 1

        if facts_inserted > 0:
            written_tables.append("knowledge_facts")
            logger.debug(f"store_insights_node: Upserted {facts_inserted} facts")

    except Exception as e:
        logger.error(f"store_insights_node: Failed to store: {e}")
        errors.append(f"store_insights_node error: {str(e)}")

    return {
        **state,
        "written_tables": written_tables,
        "errors": errors,
    }
```

---

## Phase 3: IngestionPipeline Integration

### T6: Add ENABLE_DAG_ENRICHMENT feature flag

- **File:** [config/memory_substrate_settings.py](config/memory_substrate_settings.py)
- **Lines:** 70 (before Config class)
- **Action:** INSERT
- **Change:** Add feature flag with env var

```python
    # DAG Enrichment (v2.1.0 - unified pipeline)
    enable_dag_enrichment: bool = Field(
        default=False,
        alias="ENABLE_DAG_ENRICHMENT",
        description="Enable SubstrateDAG enrichment after core writes (default: False for safety)",
    )
    
    dag_enrichment_timeout_seconds: float = Field(
        default=30.0,
        alias="DAG_ENRICHMENT_TIMEOUT",
        description="Max time for DAG enrichment before timeout (enrichment failure, core write preserved)",
    )
```

### T7: Wire DAG enrichment into IngestionPipeline.__init__()

- **File:** [memory/ingestion.py](memory/ingestion.py)
- **Lines:** 59-82
- **Action:** MODIFY
- **Change:** Accept dag and enable_enrichment params

```python
def __init__(
    self,
    repository=None,
    semantic_service=None,
    agent_persistence=None,
    auto_embed: bool = True,
    auto_tag: bool = True,
    # NEW: DAG enrichment (v2.1.0)
    dag: Optional["SubstrateDAG"] = None,
    enable_enrichment: bool = False,
    enrichment_timeout: float = 30.0,
):
    """
    Initialize ingestion pipeline.

    Args:
        repository: SubstrateRepository instance
        semantic_service: SemanticService for embeddings
        agent_persistence: AgentPersistenceService for checkpoint triggers
        auto_embed: Automatically embed text content
        auto_tag: Automatically generate tags from content
        dag: Optional SubstrateDAG for enrichment (facts, insights, world model)
        enable_enrichment: Whether to run DAG enrichment after core writes
        enrichment_timeout: Max seconds for enrichment (timeout = log + continue)
    """
    self._repository = repository
    self._semantic_service = semantic_service
    self._agent_persistence = agent_persistence
    self._auto_embed = auto_embed
    self._auto_tag = auto_tag
    
    # DAG enrichment (v2.1.0)
    self._dag = dag
    self._enable_enrichment = enable_enrichment
    self._enrichment_timeout = enrichment_timeout
    
    logger.info("IngestionPipeline initialized", enable_enrichment=enable_enrichment)
```

### T8: Add enrichment call after core writes (NO RETRY on failure)

- **File:** [memory/ingestion.py](memory/ingestion.py)
- **Lines:** 220-236 (after core writes, before return)
- **Action:** INSERT
- **Change:** Call dag.enrich() once, log failures, never retry

```python
        # ... after core writes complete, before return ...
        
        # DAG Enrichment (v2.1.0 - optional post-processing)
        enrichment_status = "not_attempted"
        enrichment_error = None
        enrichment_facts_count = 0
        
        if self._enable_enrichment and self._dag and status in ("ok", "partial"):
            enrichment_status = "disabled" if not self._enable_enrichment else "not_attempted"
            
            try:
                import asyncio
                # Run enrichment with timeout (NO RETRY on failure)
                enrichment_result = await asyncio.wait_for(
                    self._dag.enrich(envelope),
                    timeout=self._enrichment_timeout,
                )
                enrichment_status = "success"
                enrichment_facts_count = enrichment_result.facts_inserted
                written_tables.extend(["knowledge_facts", "reasoning_traces"])
                logger.info(
                    "DAG enrichment succeeded",
                    packet_id=str(envelope.packet_id),
                    facts_count=enrichment_facts_count,
                )
            except asyncio.TimeoutError:
                enrichment_status = "failed"
                enrichment_error = f"Enrichment timed out after {self._enrichment_timeout}s"
                logger.warning(enrichment_error, packet_id=str(envelope.packet_id))
                # NO RETRY - core write succeeded, just log and continue
            except Exception as e:
                enrichment_status = "failed"
                enrichment_error = str(e)
                logger.error(
                    "DAG enrichment failed (non-blocking)",
                    packet_id=str(envelope.packet_id),
                    error=enrichment_error,
                )
                # NO RETRY - core write succeeded, just log and continue
        elif not self._enable_enrichment:
            enrichment_status = "disabled"

        return PacketWriteResult(
            packet_id=envelope.packet_id,
            written_tables=written_tables,
            status=status,
            error_message="; ".join(errors) if errors else None,
            # NEW: Enrichment fields (v2.1.0)
            enrichment_status=enrichment_status,
            enrichment_error=enrichment_error,
            enrichment_facts_count=enrichment_facts_count,
            write_tier_used="full" if enrichment_status == "success" else "core_only",
            warnings=[enrichment_error] if enrichment_error else [],
        )
```

---

## Phase 4: MCP Tiered Fallback (CORRECTED)

### T9: Refactor MCP tiered fallback (no enrichment retry)

- **File:** [mcp_memory/src/routes/memory_unified.py](mcp_memory/src/routes/memory_unified.py)
- **Lines:** 65-139 (save_memory_handler)
- **Action:** MODIFY
- **Change:** Implement corrected tiered fallback

```python
async def save_memory_handler(
    user_id: str,
    content: str,
    kind: str,
    scope: str = "developer",
    # ... other params ...
    substrate_service: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Save memory with tiered fallback (v2.1.0 - corrected).
    
    Tier 1: Try full pipeline (core + enrichment if enabled)
            - Enrichment failure = 200 with enrichment_status="failed" (NO RETRY)
            - Core failure = fall to Tier 2
    Tier 2: Try direct DB (emergency fallback)
            - Success = 200 with tier_used="direct_db"
            - Failure = fall to Tier 3
    Tier 3: Return 503 Service Unavailable
    
    KEY INVARIANT: Enrichment is NEVER retried. If it fails, core write already persisted.
    """
    
    # Tier 1: Full pipeline (preferred path)
    if substrate_service:
        try:
            result = await _save_via_main_pipeline(
                user_id=user_id,
                content=content,
                kind=kind,
                scope=scope,
                # ... other params ...
                substrate_service=substrate_service,
            )
            
            # Enrichment failure is NOT a tier failure - core write succeeded
            # Just return 200 with enrichment_status="failed"
            return result
            
        except Exception as pipeline_error:
            logger.warning(
                "Full pipeline failed, falling back to direct DB",
                error=str(pipeline_error),
            )
            # Fall through to Tier 2
    
    # Tier 2: Direct DB (emergency fallback)
    try:
        result = await _save_via_direct_db(
            user_id=user_id,
            content=content,
            kind=kind,
            scope=scope,
            # ... other params ...
        )
        result["tier_used"] = "direct_db"
        result["warnings"] = ["pipeline_unavailable", "enrichment_skipped", "neo4j_skipped"]
        logger.info("Saved via direct DB fallback", packet_id=result.get("packet_id"))
        return result
        
    except Exception as direct_db_error:
        logger.error(
            "All fallbacks exhausted",
            pipeline_error=str(pipeline_error) if 'pipeline_error' in locals() else "N/A",
            direct_db_error=str(direct_db_error),
        )
        # Tier 3: 503
        raise HTTPException(
            status_code=503,
            detail="Memory substrate unavailable. All fallbacks exhausted.",
        )
```

### T10: Wire IngestionPipeline result through to MCP response

- **File:** [mcp_memory/src/routes/memory_unified.py](mcp_memory/src/routes/memory_unified.py)
- **Lines:** 239-250
- **Action:** MODIFY
- **Change:** Pass through enrichment fields from pipeline result

```python
async def _save_via_main_pipeline(
    # ... params ...
    substrate_service: Any,
) -> Dict[str, Any]:
    """Save memory via main L9 ingestion pipeline (full DAG)."""
    # ... existing code to build packet_in ...
    
    # Use main ingestion pipeline
    start_time = time.time()
    result = await substrate_service.write_packet(packet_in)
    ingest_time_ms = (time.time() - start_time) * 1000
    
    if result.status == "error":
        raise HTTPException(
            status_code=500,
            detail=f"Memory ingestion failed: {result.error_message}",
        )
    
    # Wire through ALL fields from PacketWriteResult
    return {
        "packet_id": str(result.packet_id),
        "user_id": user_id,
        "kind": kind,
        "scope": scope,
        "content": content[:100] + "..." if len(content) > 100 else content,
        "importance": importance,
        "created_at": datetime.utcnow().isoformat(),
        "written_tables": result.written_tables,
        "ingest_time_ms": ingest_time_ms,
        
        # NEW: Enrichment visibility (v2.1.0)
        "enrichment_status": result.enrichment_status,
        "enrichment_error": result.enrichment_error,
        "enrichment_facts_count": result.enrichment_facts_count,
        
        # NEW: Tier visibility (v2.1.0)
        "tier_used": result.write_tier_used,
        "warnings": result.warnings,
        
        "pipeline": "main_dag",
    }
```

---

## Phase 5: Validation + Tests

### T11: Comprehensive integration tests

- **File:** [tests/memory/test_unified_pipeline.py](tests/memory/test_unified_pipeline.py)
- **Action:** CREATE
- **Change:** Test all scenarios including edge cases

```python
"""
Integration tests for unified memory pipeline (GMP-67).

Tests:
1. Core writes work with enrichment disabled
2. Core writes + enrichment work when enabled
3. Enrichment failure doesn't block core writes
4. MCP fallback tiers work correctly
5. Idempotency: same packet twice = no duplicate facts
6. Enrichment timeout handling
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from memory.ingestion import IngestionPipeline, ingest_packet
from memory.substrate_dag import SubstrateDAG
from core.schemas.packet_envelope_v2 import PacketEnvelopeIn


class TestUnifiedPipeline:
    """Test IngestionPipeline with optional DAG enrichment."""
    
    @pytest.mark.asyncio
    async def test_core_writes_with_enrichment_disabled(self, mock_repository):
        """Core writes succeed when enrichment is disabled."""
        pipeline = IngestionPipeline(
            repository=mock_repository,
            enable_enrichment=False,
        )
        packet = PacketEnvelopeIn(packet_type="test", payload={"content": "test"})
        
        result = await pipeline.ingest(packet)
        
        assert result.status == "ok"
        assert result.enrichment_status == "disabled"
        assert "packet_store" in result.written_tables
    
    @pytest.mark.asyncio
    async def test_core_writes_plus_enrichment(self, mock_repository, mock_dag):
        """Core writes + enrichment work when enabled."""
        pipeline = IngestionPipeline(
            repository=mock_repository,
            dag=mock_dag,
            enable_enrichment=True,
        )
        packet = PacketEnvelopeIn(packet_type="test", payload={"content": "test"})
        
        result = await pipeline.ingest(packet)
        
        assert result.status == "ok"
        assert result.enrichment_status == "success"
        assert result.enrichment_facts_count >= 0
        assert result.write_tier_used == "full"
    
    @pytest.mark.asyncio
    async def test_enrichment_failure_does_not_block_core(self, mock_repository):
        """Enrichment failure = core write persisted, enrichment_status='failed'."""
        mock_dag = AsyncMock()
        mock_dag.enrich.side_effect = Exception("DAG exploded")
        
        pipeline = IngestionPipeline(
            repository=mock_repository,
            dag=mock_dag,
            enable_enrichment=True,
        )
        packet = PacketEnvelopeIn(packet_type="test", payload={"content": "test"})
        
        result = await pipeline.ingest(packet)
        
        assert result.status == "ok"  # Core write succeeded!
        assert result.enrichment_status == "failed"
        assert result.enrichment_error == "DAG exploded"
        assert result.write_tier_used == "core_only"
        assert "packet_store" in result.written_tables


class TestMCPFallbackTiers:
    """Test MCP tiered fallback behavior."""
    
    @pytest.mark.asyncio
    async def test_mcp_returns_200_on_enrichment_failure(self, mock_substrate_service):
        """Enrichment failure = 200 with enrichment_status='failed' (NO retry)."""
        mock_substrate_service.write_packet.return_value = PacketWriteResult(
            status="ok",
            packet_id=uuid4(),
            written_tables=["packet_store"],
            enrichment_status="failed",
            enrichment_error="DAG timeout",
            write_tier_used="core_only",
        )
        
        result = await save_memory_handler(
            user_id="test",
            content="test",
            kind="fact",
            substrate_service=mock_substrate_service,
        )
        
        assert result["enrichment_status"] == "failed"
        assert result["tier_used"] == "core_only"
        # HTTP 200 returned (not 500)
    
    @pytest.mark.asyncio
    async def test_mcp_falls_back_to_direct_db_on_pipeline_failure(self):
        """Pipeline failure = try direct DB, return with tier='direct_db'."""
        mock_substrate_service = AsyncMock()
        mock_substrate_service.write_packet.side_effect = Exception("Pipeline down")
        
        with patch("mcp_memory.src.routes.memory_unified._save_via_direct_db") as mock_direct:
            mock_direct.return_value = {"packet_id": str(uuid4())}
            
            result = await save_memory_handler(
                user_id="test",
                content="test",
                kind="fact",
                substrate_service=mock_substrate_service,
            )
            
            assert result["tier_used"] == "direct_db"
            assert "pipeline_unavailable" in result["warnings"]


class TestIdempotency:
    """Test that same packet enriched twice doesn't duplicate facts."""
    
    @pytest.mark.asyncio
    async def test_no_duplicate_facts_on_replay(self, mock_repository, mock_dag):
        """Same packet ingested twice = same fact count (UPSERT)."""
        pipeline = IngestionPipeline(
            repository=mock_repository,
            dag=mock_dag,
            enable_enrichment=True,
        )
        packet = PacketEnvelopeIn(
            packet_id=uuid4(),  # Fixed ID
            packet_type="test",
            payload={"content": "test"},
        )
        
        # First ingestion
        result1 = await pipeline.ingest(packet)
        facts_v1 = await mock_repository.query_facts(packet.packet_id)
        
        # Second ingestion (same packet)
        result2 = await pipeline.ingest(packet)
        facts_v2 = await mock_repository.query_facts(packet.packet_id)
        
        assert len(facts_v1) == len(facts_v2), "Facts duplicated on replay!"


class TestEnrichmentTimeout:
    """Test enrichment timeout handling."""
    
    @pytest.mark.asyncio
    async def test_enrichment_timeout_logs_and_continues(self, mock_repository):
        """Slow DAG = timeout, core write persisted, enrichment_status='failed'."""
        import asyncio
        
        async def slow_enrich(*args, **kwargs):
            await asyncio.sleep(60)  # Way longer than timeout
        
        mock_dag = AsyncMock()
        mock_dag.enrich = slow_enrich
        
        pipeline = IngestionPipeline(
            repository=mock_repository,
            dag=mock_dag,
            enable_enrichment=True,
            enrichment_timeout=0.1,  # 100ms timeout
        )
        packet = PacketEnvelopeIn(packet_type="test", payload={"content": "test"})
        
        result = await pipeline.ingest(packet)
        
        assert result.status == "ok"  # Core write succeeded
        assert result.enrichment_status == "failed"
        assert "timed out" in result.enrichment_error.lower()
```

---

## Key Files Summary

| File | Changes |
|------|---------|
| `core/schemas/packet_envelope_v2.py` | Extend PacketWriteResult with enrichment_status, enrichment_error, enrichment_facts_count, write_tier_used, warnings |
| `memory/substrate_models.py` | Add EnrichmentResult dataclass |
| `memory/substrate_repository.py` | Add insert_knowledge_fact() with UPSERT |
| `memory/substrate_dag.py` | Add enrich() method with pre-validation, update store_insights_node |
| `config/memory_substrate_settings.py` | Add ENABLE_DAG_ENRICHMENT, DAG_ENRICHMENT_TIMEOUT |
| `memory/ingestion.py` | Wire DAG enrichment with NO RETRY semantics |
| `mcp_memory/src/routes/memory_unified.py` | Corrected tiered fallback, wire result through |
| `tests/memory/test_unified_pipeline.py` | Comprehensive tests including idempotency, timeout |

## Migration Required

Add unique constraint for fact UPSERT:

```sql
-- migrations/0015_knowledge_facts_upsert_key.sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_facts_upsert_key
    ON knowledge_facts (source_packet, subject, predicate)
    WHERE source_packet IS NOT NULL;
```

## Constraints (Locked)

- ENABLE_DAG_ENRICHMENT=False by default
- Enrichment errors are LOGGED but do NOT block core writes
- Enrichment is NEVER retried (avoid double writes)
- MCP always returns tier_used + warnings for observability
- Direct DB fallback preserved for resilience
- Facts use UPSERT to ensure idempotency

## Validation Gates

- `py_compile` on all modified files
- `ruff check` passes
- `pytest tests/memory/test_unified_pipeline.py` passes
- Manual test: ingest with ENABLE_DAG_ENRICHMENT=false → verify core write only
- Manual test: ingest with ENABLE_DAG_ENRICHMENT=true → verify facts in knowledge_facts table
- Manual test: same packet twice → verify no duplicate facts