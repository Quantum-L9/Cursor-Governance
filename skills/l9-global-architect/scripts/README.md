# Scripts

**Path:** `skills/l9-global-architect/scripts` | **Kind:** module

## Purpose

Validate GAR's graph-bound Product Architecture Decision.

## Public interface

- `DecisionError`
- `def load(path) -> Any`
- `def digest(value) -> str`
- `def validate(decision) -> dict[str, Any]`
- `def main() -> int`

## Dependencies

**External:** `jsonschema`, `yaml`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=module -->
