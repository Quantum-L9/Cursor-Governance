# Invalidation

**Path:** `environment/agents/generated-data/invalidation` | **Tier:** discovered

## Purpose

Structured repository-event bridge for governed memory invalidation.



## Components

### `RepositoryEventBridgeError`

Base repository invalidation bridge failure.

- File: `environment/agents/generated-data/invalidation/repository_event_bridge.py` (L70–71)
- Methods: _none_

### `RepositoryStateError`

The repository state is unsuitable for deterministic diffing.

- File: `environment/agents/generated-data/invalidation/repository_event_bridge.py` (L74–75)
- Methods: _none_

### `InvalidationCollisionError`

An immutable event ID was reused with different content.

- File: `environment/agents/generated-data/invalidation/repository_event_bridge.py` (L78–79)
- Methods: _none_

### `InvalidationTransportError`

The invalidation destination failed or returned an invalid response.

- File: `environment/agents/generated-data/invalidation/repository_event_bridge.py` (L82–83)
- Methods: _none_

### `ChangeKind`

No description

- File: `environment/agents/generated-data/invalidation/repository_event_bridge.py` (L86–91)
- Methods: _none_

### `ChangedPath`

No description

- File: `environment/agents/generated-data/invalidation/repository_event_bridge.py` (L95–123)
- Methods: `to_dict`

### `RepositoryChangeEvent`

No description

- File: `environment/agents/generated-data/invalidation/repository_event_bridge.py` (L127–205)
- Methods: `effective_selectors`, `to_request`

### `InvalidationDispatchResult`

No description

- File: `environment/agents/generated-data/invalidation/repository_event_bridge.py` (L209–229)
- Methods: `to_dict`

### `InvalidationTransport`

No description

- File: `environment/agents/generated-data/invalidation/repository_event_bridge.py` (L232–237)
- Methods: `invalidate`

### `CommandInvalidationTransport`

Invoke the existing Graphiti invalidation command.

- File: `environment/agents/generated-data/invalidation/repository_event_bridge.py` (L240–335)
- Methods: `from_environment`, `invalidate`

### `RepositoryEventBridge`

Produce and dispatch structured invalidation requests.

- File: `environment/agents/generated-data/invalidation/repository_event_bridge.py` (L338–484)
- Methods: `from_database`, `from_git_diff`, `dispatch`

## Functions

- `def parse_name_status(output) -> list[ChangedPath]`
- `def normalize_selector(selector) -> dict[str, Any]`
- `def event_from_mapping(payload) -> RepositoryChangeEvent`
- `def deterministic_event_id() -> str`
- `def normalize_repository_path(value) -> str`
- `def assert_git_repository(root) -> None`
- `def ensure_clean_repository(root) -> None`
- `def validate_commit(root, revision) -> None`
- `def resolve_commit(root, revision) -> str`
- `def load_state_store_module() -> ModuleType`
- `def validate_schema_major(schema_version) -> None`
- `def optional_string(value) -> str | None`
- `def canonical_json(value) -> str`
- `def main(argv) -> int`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `collections.abc`, `dataclasses`, `enum`, `hashlib`, `importlib.util`, `json`, `os`, `pathlib`, `re`, `shlex`, `subprocess`, `sys`, `types`, `typing`

<!-- l9-module-readme: generated-from-ast -->
