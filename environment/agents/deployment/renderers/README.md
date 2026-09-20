# Renderers

**Path:** `environment/agents/deployment/renderers` | **Kind:** subsystem

## Modules

### `__init__.py`

### `cursor.py`

Deterministic Cursor-native renderer for governed subagent roles.

- `def content_digest(text) -> str`
- `def is_managed(text) -> bool`
- `def parse_managed_provenance(text) -> dict[str, str] | None`
- `def render_role(role_key, role) -> str` — Render one Cursor agent markdown definition deterministically.
- `def expected_definitions(roles) -> dict[str, str]` — Map filename -> rendered markdown for every role in the manifest.

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
