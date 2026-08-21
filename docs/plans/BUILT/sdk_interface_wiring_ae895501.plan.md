---
name: SDK Interface Wiring
overview: Wire 7 new SDK interfaces (MemoryInterface, MemoryGraphInterface, MemoryCacheInterface, ResearchInterface, CommandsInterface, EmailInterface) and expand WorldModelInterface to consolidate L9's 225+ HTTP routes behind the SDK adapter per ADR-0102.
todos:
  - id: t1-memory
    content: "T1: MemoryInterface — search, ingest, get_packet, thread, facts, insights, semantic/hybrid search"
    status: completed
  - id: t2-graph
    content: "T2: MemoryGraphInterface — entity CRUD, relationships, cypher query (nested on MemoryInterface)"
    status: completed
  - id: t3-cache
    content: "T3: MemoryCacheInterface — get/set/delete, session context, task context, rate limit (nested on MemoryInterface)"
    status: completed
  - id: t4-worldmodel
    content: "T4: Expand WorldModelInterface — list_entities, upsert, delete, snapshots, updates"
    status: completed
  - id: t5-research
    content: "T5: ResearchInterface — synthesize, discover, generate_spec, research_to_code"
    status: completed
  - id: t6-commands
    content: "T6: CommandsInterface — execute(command_text, context)"
    status: completed
  - id: t7-email
    content: "T7: EmailInterface — send, draft, reply, forward, get, query"
    status: completed
  - id: t8-wire
    content: "T8: Wire all interfaces into L9SDK.__init__ + properties + docstring"
    status: completed
  - id: t9-exports
    content: "T9: Update SDK/__init__.py exports"
    status: completed
isProject: false
---

# SDK-First Interface Wiring (ADR-0102)

All changes are in two files: [SDK/SDK.py](SDK/SDK.py) and [SDK/**init**.py](SDK/__init__.py).

Each interface follows the established pattern from `WorkflowsInterface`:

- Lazy-load the backing service via `_get_service()`
- Auto-inject `agent_id`/`tenant_id` from SDK context
- Use `@must_stay_async` decorator
- Subprocess fallback where appropriate

## P0 Interfaces (Memory Stack)

### T1: MemoryInterface — `sdk.memory`

Wraps `memory/retrieval.py::RetrievalPipeline` and `memory/ingestion.py::ingest_packet`.

Methods:

- `search(query, limit, min_similarity)` -> RetrievalPipeline.search()
- `semantic_search(query, top_k, tags)` -> RetrievalPipeline.semantic_search()
- `hybrid_search(query, top_k, filters)` -> RetrievalPipeline.hybrid_search()
- `ingest(content, kind, metadata)` -> ingest_packet()
- `get_packet(packet_id)` -> MemorySubstrateService.get_packet()
- `get_thread(thread_id, limit)` -> RetrievalPipeline.fetch_thread()
- `get_facts(subject, predicate, limit)` -> RetrievalPipeline.fetch_facts()
- `get_insights(packet_id, insight_type, limit)` -> RetrievalPipeline.fetch_insights()

### T2: MemoryGraphInterface — `sdk.memory.graph`

Nested interface on MemoryInterface. Wraps `memory/graph_client.py::Neo4jClient`.

Methods:

- `create_entity(entity_type, entity_id, properties)`
- `get_entity(entity_type, entity_id)`
- `delete_entity(entity_type, entity_id)`
- `create_relationship(from_type, from_id, to_type, to_id, rel_type, properties)`
- `get_relationships(entity_type, entity_id, rel_type, direction)`
- `run_query(cypher, parameters)`

### T3: MemoryCacheInterface — `sdk.memory.cache`

Nested interface on MemoryInterface. Wraps `runtime/redis_client.py::RedisClient`.

Methods:

- `get(key)` / `set(key, value, ttl)` / `delete(key)`
- `keys(pattern)`
- `get_session_context(session_id)` / `set_session_context(session_id, context, ttl)`
- `get_task_context(task_id)` / `set_task_context(task_id, context, ttl)`
- `get_rate_limit(key)` / `increment_rate_limit(key, ttl)`

## P1 Interfaces

### T4: Expand WorldModelInterface — `sdk.world_model`

Currently only has `get_entity()`. Add from `world_model/service.py::WorldModelService`:

- `list_entities(entity_type, limit, offset)`
- `upsert_entity(entity_id, attributes, entity_type, confidence)`
- `delete_entity(entity_id)`
- `create_snapshot(description)`
- `restore_snapshot(snapshot_id)`
- `list_snapshots(limit)`
- `list_updates(insight_type, min_confidence, since, limit)`

### T5: ResearchInterface — `sdk.research`

Wraps `agents/research_agent_impl.py::ResearchAgent`.

Methods:

- `synthesize(topic, context)`
- `discover(topic, domain, stages)`
- `generate_spec(topic, description)`
- `research_to_code(topic, mode, domain)`

### T6: CommandsInterface — `sdk.commands`

Wraps `core/commands/executor.py::CommandExecutor`.

Methods:

- `execute(command_text, context)`

### T7: EmailInterface — `sdk.email`

Wraps `email_agent/gmail_client.py::GmailClient`.

Methods:

- `send(account, to, subject, body)`
- `draft(account, to, subject, body)`
- `reply(account, msg_id, body)`
- `forward(account, msg_id, to, body)`
- `get(account, msg_id)`
- `query(account, query_str, limit)`

## Wiring (T8-T9)

### T8: Wire into L9SDK class

In `L9SDK.__init__`:

- Add `self._memory = MemoryInterface(self)` (P0)
- Add `self._research = ResearchInterface(self)` (P1)
- Add `self._commands = CommandsInterface(self)` (P1)
- Add `self._email = EmailInterface(self)` (P1)
- Add `@property` accessors for each
- Update docstring to list all interfaces

Note: `sdk.memory.graph` and `sdk.memory.cache` are sub-interfaces accessed via `sdk.memory.graph` and `sdk.memory.cache` — initialized inside MemoryInterface.

### T9: Update SDK/**init**.py exports

Add all new interface classes to imports and `__all__`.

## P2 (Not in this GMP — add to TODO.md)

After execution, append P2 items to a tracking location:

- `sdk.evaluation` (4 routes)
- `sdk.factory` (5 routes)
- `sdk.simulation` (3 routes)
- `sdk.reasoning` expansion (4 routes)
- `sdk.learning` expansion (7 routes)

## Validation

- `python3 -m py_compile SDK/SDK.py`
- `ruff check SDK/ --select=E,F`
- Import test: `python3 -c "from SDK import L9SDK, MemoryInterface, ..."`
- Integration test: instantiate SDK, verify all properties return correct interface types

