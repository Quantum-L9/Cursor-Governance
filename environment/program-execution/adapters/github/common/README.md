# Common

**Path:** `environment/program-execution/adapters/github/common` | **Kind:** subsystem

## Modules

### `__init__.py`

Shared GitHub adapter transport.

### `auth_probe.py`

- `def probe(cwd) -> dict[str, Any]`

### `gh_transport.py`

- `GhTransport`

### `permission_probe.py`

- `def repository_permissions(transport, repository) -> dict[str, Any]`

### `response_normalizer.py`

- `def parse_json(value) -> Any`

## Dependencies

**Internal:** `adapters`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
