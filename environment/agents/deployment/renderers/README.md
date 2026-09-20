# Renderers

**Path:** `environment/agents/deployment/renderers` | **Tier:** discovered

## Purpose

Deterministic Cursor-native renderer for governed subagent roles.



## Components

_No public classes in this path._

## Functions

- `def content_digest(text) -> str`
- `def is_managed(text) -> bool`
- `def parse_managed_provenance(text) -> dict[str, str] | None`
- `def render_role(role_key, role) -> str` — Render one Cursor agent markdown definition deterministically.
- `def expected_definitions(roles) -> dict[str, str]` — Map filename -> rendered markdown for every role in the manifest.

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `collections.abc`, `hashlib`, `re`, `typing`

<!-- l9-module-readme: generated-from-ast -->
