# Retrieval

**Path:** `environment/agents/generated-data/retrieval` | **Tier:** discovered

## Purpose

Context retrieval, deterministic selection, and memory-reuse dispatch.



## Components

### `ContextRetrievalError`

Base failure for generated-data context retrieval.

- File: `environment/agents/generated-data/retrieval/context_query.py` (L58–59)
- Methods: _none_

### `RetrievalUnavailableError`

The configured retrieval surface could not be reached.

- File: `environment/agents/generated-data/retrieval/context_query.py` (L62–63)
- Methods: _none_

### `RetrievalProtocolError`

The retrieval surface returned an invalid response.

- File: `environment/agents/generated-data/retrieval/context_query.py` (L66–67)
- Methods: _none_

### `RetrievalSchemaError`

The retrieval response uses an unsupported schema version.

- File: `environment/agents/generated-data/retrieval/context_query.py` (L70–71)
- Methods: _none_

### `ContextScope`

No description

- File: `environment/agents/generated-data/retrieval/context_query.py` (L74–76)
- Methods: _none_

### `ContextBudget`

Hard context-selection limits supplied to the memory data plane.

- File: `environment/agents/generated-data/retrieval/context_query.py` (L80–96)
- Methods: `to_dict`

### `ContextQuery`

Governed request for memory search and bounded hydration.

- File: `environment/agents/generated-data/retrieval/context_query.py` (L100–175)
- Methods: `to_dict`, `default_query_text`

### `ContextCandidate`

One memory item returned by the canonical memory data plane.

- File: `environment/agents/generated-data/retrieval/context_query.py` (L179–312)
- Methods: `from_mapping`, `ordinarily_eligible`, `to_dict`

### `ContextQueryResult`

Typed retrieval response with availability separated from emptiness.

- File: `environment/agents/generated-data/retrieval/context_query.py` (L316–343)
- Methods: `empty`, `to_dict`

### `ContextClient`

No description

- File: `environment/agents/generated-data/retrieval/context_query.py` (L346–351)
- Methods: `query`

### `CommandContextClient`

Invoke the existing memory command with JSON over stdin/stdout.

- File: `environment/agents/generated-data/retrieval/context_query.py` (L354–435)
- Methods: `from_environment`, `query`

### `StaticContextClient`

Deterministic boundary for tests and explicit local simulation.

- File: `environment/agents/generated-data/retrieval/context_query.py` (L438–460)
- Methods: `query`

## Functions

- `def parse_query_result(payload) -> ContextQueryResult`
- `def query_from_mapping(payload) -> ContextQuery`
- `def normalize_repository_path(value) -> str`
- `def validate_schema_major(schema_version) -> None`
- `def string_field(value, field_name) -> str`
- `def sequence_field(value, field_name) -> Sequence[Any]`
- `def optional_string(value) -> str | None`
- `def canonical_json(value) -> str`
- `def exit_code_name(code) -> str`
- `def main(argv) -> int`
- `def build_invalidation_candidate(reuse_event) -> dict[str, Any]` — Create an advisory candidate; never mutate memory directly.
- `def deterministic_event_id(pending) -> str`
- `def load_state_store_module() -> ModuleType`
- `def validate_utc_timestamp(value) -> None`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `collections.abc`, `context_query`, `dataclasses`, `datetime`, `enum`, `hashlib`, `importlib.util`, `json`, `os`, `pathlib`, `shlex`, `subprocess`, `sys`, `types`, `typing`

<!-- l9-module-readme: generated-from-ast -->
