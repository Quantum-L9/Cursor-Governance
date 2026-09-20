# Retrieval

**Path:** `environment/agents/generated-data/retrieval` | **Kind:** subsystem

## Modules

### `__init__.py`

Context retrieval, deterministic selection, and memory-reuse dispatch.

### `context_query.py`

Typed, bounded context retrieval through the existing Graphiti surface.

- `ContextRetrievalError` — Base failure for generated-data context retrieval.
- `RetrievalUnavailableError` — The configured retrieval surface could not be reached.
- `RetrievalProtocolError` — The retrieval surface returned an invalid response.
- `RetrievalSchemaError` — The retrieval response uses an unsupported schema version.
- `ContextScope`
- `ContextBudget` — Hard context-selection limits supplied to the memory data plane.
- `ContextQuery` — Governed request for memory search and bounded hydration.
- `ContextCandidate` — One memory item returned by the canonical memory data plane.
- _+14 more public symbol(s)_

### `context_selector.py`

- `SelectionWeights`
- `SelectionExclusion`
- `ContextSelection`
- `ContextSelectionResult`
- `ContextSelector`

### `reuse_recorder.py`

Governed memory-reuse lifecycle and remote recording bridge.

- `ReuseRecorderError` — Base memory-reuse recording failure.
- `ReuseProtocolError` — The local or remote reuse protocol was invalid.
- `ReuseCollisionError` — An immutable reuse event ID was reused with different content.
- `ReuseTransportError` — The memory reuse destination could not be called safely.
- `ReuseStage`
- `ReuseIdentity`
- `PendingReuse`
- `ReuseFinalization`
- _+10 more public symbol(s)_

## Dependencies

**Internal:** `context_query`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
