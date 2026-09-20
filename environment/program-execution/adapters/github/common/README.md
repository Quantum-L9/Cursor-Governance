# Common

**Path:** `environment/program-execution/adapters/github/common` | **Tier:** discovered

## Purpose

Shared GitHub adapter transport.



## Components

### `GhTransport`

No description

- File: `environment/program-execution/adapters/github/common/gh_transport.py` (L10–52)
- Methods: `run`, `json`, `api`

## Functions

- `def probe(cwd) -> dict[str, Any]`
- `def repository_permissions(transport, repository) -> dict[str, Any]`
- `def parse_json(value) -> Any`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `adapters.common.subprocess_runner`, `adapters.github.common.gh_transport`, `json`, `pathlib`, `shutil`, `typing`

<!-- l9-module-readme: generated-from-ast -->
