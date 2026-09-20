# Contracts

**Path:** `ops/contracts` | **Tier:** discovered

## Purpose

Build the deterministic Skills Doctrine Census.



## Components

### `UnionFind`

Minimal deterministic union-find for connected cluster construction.

- File: `ops/contracts/cluster_doctrine.py` (L117–142)
- Methods: `find`, `union`

### `Marker`

No description

- File: `ops/contracts/detect_hidden_doctrine.py` (L109–121)
- Methods: `as_dict`

### `Registry`

No description

- File: `ops/contracts/detect_hidden_doctrine.py` (L125–127)
- Methods: _none_

### `UniqueKeyLoader`

Safe YAML loader that rejects duplicate mapping keys.

- File: `ops/contracts/extract_doctrine.py` (L109–110)
- Methods: _none_

### `Finding`

Structured extraction diagnostic.

- File: `ops/contracts/extract_doctrine.py` (L135–153)
- Methods: `as_dict`

### `SourceBlock`

Exact source unit considered by the doctrine classifier.

- File: `ops/contracts/extract_doctrine.py` (L157–165)
- Methods: _none_

### `SignalRule`

One deterministic lexical signal.

- File: `ops/contracts/extract_doctrine.py` (L169–174)
- Methods: _none_

### `ContractRecord`

No description

- File: `ops/contracts/resolve_rule_contracts.py` (L52–60)
- Methods: _none_

### `ContractIndex`

No description

- File: `ops/contracts/resolve_rule_contracts.py` (L64–66)
- Methods: _none_

### `Finding`

No description

- File: `ops/contracts/validate_rule_binding.py` (L71–77)
- Methods: _none_

### `Finding`

No description

- File: `ops/contracts/validate_rule_projections.py` (L52–58)
- Methods: _none_

## Functions

- `def build_census() -> dict[str, Any]` — Build the complete deterministic doctrine census.
- `def render_census(census, output_format) -> str`
- `def write_if_changed(path, content) -> bool`
- `def main() -> int`
- `def extract_rule_doctrine(root) -> dict[str, Any]`
- `def build_rule_census(root, registry_path) -> dict[str, Any]`
- `def bootstrap_baseline(census, baseline_path, reason) -> None`
- `def check_baseline(census, baseline) -> list[str]`
- `def tighten_baseline(census, baseline_path) -> None`
- `def main() -> int`
- `def resolve_all(root, registry_path) -> list[dict[str, Any]]`
- `def build_projection_index(root, registry_path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]`
- `def expected_outputs(root, registry_path) -> tuple[dict[str, str], dict[str, dict[str, Any]]]`
- `def check(root, registry_path) -> list[str]`
- `def explain(root, selector, registry_path) -> dict[str, Any]`
- `def impact(root, contract_id, registry_path) -> list[dict[str, Any]]`
- `def main() -> int`
- `def semantic_tokens(record) -> set[str]`
- `def token_bigrams(tokens) -> set[str]`
- `def jaccard(left, right) -> float`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `build_doctrine_census`, `cluster_doctrine`, `collections`, `collections.abc`, `copy`, `cursor_rules`, `dataclasses`, `detect_hidden_doctrine`, `extract_doctrine`, `generate_rules_manifest`, `hashlib`, `json`, `lib.rule_frontmatter`, `math`, `os`, `pathlib`, `re`, `render_cursor_rule`, `resolve_rule_contracts`, `shlex`, `subprocess`, `sys`

<!-- l9-module-readme: generated-from-ast -->
