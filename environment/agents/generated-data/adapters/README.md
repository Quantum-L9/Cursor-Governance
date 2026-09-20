# Adapters

**Path:** `environment/agents/generated-data/adapters` | **Tier:** discovered

## Purpose

Destination and repository-class adapters for L9 subagent-generated data.



## Components

### `GraphitiAdapterError`

Raised when governed memory delivery cannot be completed safely.

- File: `environment/agents/generated-data/adapters/graphiti_memory.py` (L37–38)
- Methods: _none_

### `MemoryCandidate`

No description

- File: `environment/agents/generated-data/adapters/graphiti_memory.py` (L42–62)
- Methods: `to_dict`

### `MemoryDeliveryResult`

No description

- File: `environment/agents/generated-data/adapters/graphiti_memory.py` (L66–82)
- Methods: `to_dict`

### `MemoryTransport`

No description

- File: `environment/agents/generated-data/adapters/graphiti_memory.py` (L85–87)
- Methods: `deliver`

### `FileOutboxTransport`

Durably enqueue candidates for later Graphiti ingestion.

- File: `environment/agents/generated-data/adapters/graphiti_memory.py` (L90–128)
- Methods: `deliver`

### `HttpJsonTransport`

Submit governed candidates to an HTTPS JSON endpoint.

- File: `environment/agents/generated-data/adapters/graphiti_memory.py` (L131–196)
- Methods: `deliver`

### `CommandTransport`

Invoke an explicit Graphiti ingestion command with JSON on stdin.

- File: `environment/agents/generated-data/adapters/graphiti_memory.py` (L199–251)
- Methods: `deliver`

### `GraphitiMemoryAdapter`

Compile approved memory-route units into governed candidates.

- File: `environment/agents/generated-data/adapters/graphiti_memory.py` (L254–426)
- Methods: `compile_candidate`, `deliver`

### `L9PythonAdapterError`

Raised when an L9 Python repository cannot be adapted safely.

- File: `environment/agents/generated-data/adapters/l9_python.py` (L9–10)
- Methods: _none_

### `RepositoryContext`

No description

- File: `environment/agents/generated-data/adapters/l9_python.py` (L14–32)
- Methods: `to_dict`

### `L9PythonRepositoryAdapter`

Interpret generated data for strict L9 Python repositories.

- File: `environment/agents/generated-data/adapters/l9_python.py` (L35–159)
- Methods: `inspect`, `enrich_unit`

### `OdooAdapterError`

Raised when an Odoo repository cannot be adapted safely.

- File: `environment/agents/generated-data/adapters/odoo.py` (L9–10)
- Methods: _none_

## Functions

- `def canonical_json(value) -> bytes`
- `def select_transport() -> MemoryTransport`
- `def main(argv) -> int`
- `def resolve_namespace(candidate) -> str` — The namespace request for this candidate; raises when it cannot be honest.
- `def ingest_candidate(candidate) -> dict[str, Any]`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `collections.abc`, `dataclasses`, `hashlib`, `json`, `os`, `pathlib`, `safe_https`, `subprocess`, `sys`, `tempfile`, `typing`, `urllib.error`, `urllib.request`

<!-- l9-module-readme: generated-from-ast -->
