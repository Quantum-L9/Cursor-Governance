# Adapters

**Path:** `ops/contracts/adapters` | **Tier:** discovered

## Purpose

Cursor rule adapter for the contract-first governance compiler.



## Components

### `UniqueKeyLoader`

Safe loader that rejects duplicate YAML mapping keys.

- File: `ops/contracts/adapters/cursor_rules.py` (L34–35)
- Methods: _none_

### `CursorRule`

No description

- File: `ops/contracts/adapters/cursor_rules.py` (L60–77)
- Methods: _none_

### `RuleBinding`

No description

- File: `ops/contracts/adapters/cursor_rules.py` (L81–88)
- Methods: _none_

## Functions

- `def sha256_bytes(value) -> str`
- `def canonical_json_bytes(value) -> bytes`
- `def stable_digest(value) -> str`
- `def load_yaml_unique(path) -> Any`
- `def first_heading(body) -> str`
- `def slug(value) -> str`
- `def infer_domain(filename, description) -> str`
- `def normalize_activation(metadata, globs) -> str`
- `def parse_cursor_rule(root, path) -> CursorRule`
- `def discover_cursor_rules(root) -> list[CursorRule]`
- `def load_rule_binding(root, path) -> RuleBinding`
- `def discover_rule_bindings(root, binding_dir) -> list[RuleBinding]`
- `def binding_contract_refs(binding) -> list[dict[str, Any]]`
- `def binding_activation(binding) -> dict[str, Any]`
- `def binding_rule_identity(binding) -> dict[str, Any]`
- `def binding_render_config(binding) -> dict[str, Any]`
- `def binding_guidance(binding) -> dict[str, Any]`
- `def static_glob_prefix(pattern) -> str`
- `def glob_is_narrower_or_equal(candidate, owner) -> bool` — Conservative approximation of glob subset relation.
- `def globs_may_overlap(left, right) -> bool`

## Exports

`BINDING_ID_RE`, `BINDING_SCHEMA`, `CursorRule`, `OUTPUT_RE`, `ROOT`, `RULE_ID_RE`, `RuleBinding`, `activations_may_overlap`, `binding_activation`, `binding_contract_refs`, `binding_guidance`, `binding_render_config`, `binding_rule_identity`, `canonical_json_bytes`, `discover_cursor_rules`, `discover_rule_bindings`, `glob_is_narrower_or_equal`, `globs_may_overlap`, `load_rule_binding`, `load_yaml_unique` (+3 more)

## Dependencies

`__future__`, `collections.abc`, `dataclasses`, `hashlib`, `json`, `lib.rule_frontmatter`, `pathlib`, `re`, `sys`, `typing`, `yaml`

<!-- l9-module-readme: generated-from-ast -->
