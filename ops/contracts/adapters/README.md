# Adapters

**Path:** `ops/contracts/adapters` | **Kind:** module

## Purpose

Cursor rule adapter for the contract-first governance compiler.

## Public interface

- `UniqueKeyLoader` — Safe loader that rejects duplicate YAML mapping keys.
- `CursorRule`
- `RuleBinding`
- `def sha256_bytes(value) -> str`
- `def canonical_json_bytes(value) -> bytes`
- `def stable_digest(value) -> str`
- `def load_yaml_unique(path) -> Any`
- `def first_heading(body) -> str`
- _+16 more public symbol(s)_

## Dependencies

**Internal:** `lib`

**External:** `yaml`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=module -->
