# Adapters

**Path:** `environment/agents/generated-data/adapters` | **Kind:** subsystem

## Modules

### `__init__.py`

Destination and repository-class adapters for L9 subagent-generated data. Adapters do not decide whether a unit is eligible for promotion.

### `graphiti_memory.py`

- `GraphitiAdapterError` — Raised when governed memory delivery cannot be completed safely.
- `MemoryCandidate`
- `MemoryDeliveryResult`
- `MemoryTransport`
- `FileOutboxTransport` — Durably enqueue candidates for later Graphiti ingestion.
- `HttpJsonTransport` — Submit governed candidates to an HTTPS JSON endpoint.
- `CommandTransport` — Invoke an explicit Graphiti ingestion command with JSON on stdin.
- `GraphitiMemoryAdapter` — Compile approved memory-route units into governed candidates.
- _+3 more public symbol(s)_

### `ingest_memory_candidate.py`

Map a MemoryCandidate on stdin to a canonical memory write (stage C10).

- `def resolve_namespace(candidate) -> str` — The namespace request for this candidate; raises when it cannot be honest.
- `def ingest_candidate(candidate) -> dict[str, Any]`
- `def main(argv) -> int`

### `l9_python.py`

- `L9PythonAdapterError` — Raised when an L9 Python repository cannot be adapted safely.
- `RepositoryContext`
- `L9PythonRepositoryAdapter` — Interpret generated data for strict L9 Python repositories.
- `def main(argv) -> int`

### `odoo.py`

- `OdooAdapterError` — Raised when an Odoo repository cannot be adapted safely.
- `OdooRepositoryContext`
- `OdooRepositoryAdapter` — Interpret generated data for pragmatic local-first Odoo repos.
- `def main(argv) -> int`

## Dependencies

**Internal:** `safe_https`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
