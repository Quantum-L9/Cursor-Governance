# Contracts

**Path:** `ops/contracts` | **Kind:** subsystem

## Modules

### `build_doctrine_census.py`

Build the deterministic Skills Doctrine Census. The census is the migration inventory for the contract-first conversion. It combines: 1. extraction; 2. duplicate/conflict clustering; 3.

- `def build_census() -> dict[str, Any]` — Build the complete deterministic doctrine census.
- `def render_census(census, output_format) -> str`
- `def write_if_changed(path, content) -> bool`
- `def main() -> int`

### `build_rule_doctrine_census.py`

Build rules/** doctrine census and enforce its monotonic debt baseline.

- `def extract_rule_doctrine(root) -> dict[str, Any]`
- `def build_rule_census(root, registry_path) -> dict[str, Any]`
- `def bootstrap_baseline(census, baseline_path, reason) -> None`
- `def check_baseline(census, baseline) -> list[str]`
- `def tighten_baseline(census, baseline_path) -> None`
- `def main() -> int`

### `build_rules.py`

Contract-first Cursor rules compiler front door.

- `def resolve_all(root, registry_path) -> list[dict[str, Any]]`
- `def build_projection_index(root, registry_path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]`
- `def expected_outputs(root, registry_path) -> tuple[dict[str, str], dict[str, dict[str, Any]]]`
- `def check(root, registry_path) -> list[str]`
- `def explain(root, selector, registry_path) -> dict[str, Any]`
- `def impact(root, contract_id, registry_path) -> list[dict[str, Any]]`
- `def main() -> int`

### `cluster_doctrine.py`

Cluster extracted doctrine into duplicate and potential-conflict families. This is an analysis stage, not an authority stage.

- `UnionFind` — Minimal deterministic union-find for connected cluster construction.
- `def semantic_tokens(record) -> set[str]`
- `def token_bigrams(tokens) -> set[str]`
- `def jaccard(left, right) -> float`
- `def classification_similarity(left, right) -> float`
- `def semantic_similarity(left, right) -> float`
- `def normalized_proposition(record) -> str` — Normalize lexical form without attempting semantic rewriting.
- `def exact_duplicate_key(record) -> str` — Fingerprint normalized source wording while preserving normative effect.
- _+3 more public symbol(s)_

### `detect_hidden_doctrine.py`

Detect normative skill doctrine that lacks an authoritative owner. Ownership is explicit. This validator never infers ownership because a contract name happens to appear nearby.

- `Marker`
- `Registry`
- `def doctrine_fingerprint(record) -> str` — Fingerprint debt independently of its line number. Repeated copies of the same doctrine intentionally share a fingerprint; the ratchet tracks occurrence count separately.
- `def parse_marker_fields(body) -> dict[str, str]`
- `def parse_markers() -> tuple[list[Marker], list[Finding]]`
- `def bind_markers() -> tuple[dict[str, Marker], list[Finding]]` — Bind each marker to exactly one immediately following extraction record.
- `def load_contract_registry() -> Registry`
- `def analyze_ownership() -> dict[str, Any]`
- _+2 more public symbol(s)_

### `extract_doctrine.py`

Extract candidate governance doctrine from active skill surfaces. This module is deliberately non-authoritative.

- `UniqueKeyLoader` — Safe YAML loader that rejects duplicate mapping keys.
- `Finding` — Structured extraction diagnostic.
- `SourceBlock` — Exact source unit considered by the doctrine classifier.
- `SignalRule` — One deterministic lexical signal.
- `def load_yaml_unique(path) -> Any` — Load YAML safely and reject duplicate mapping keys.
- `def dump_yaml(value) -> str` — Serialize YAML deterministically enough for repository generation.
- `def canonical_json_bytes(value) -> bytes` — Return stable JSON bytes suitable for hashing.
- `def sha256_bytes(value) -> str`
- _+21 more public symbol(s)_

### `render_cursor_rule.py`

Deterministically render a resolved contract bundle into Cursor .mdc.

- `def render_directive(directive) -> str`
- `def render_cursor_rule(resolution) -> str`
- `def measure_rendered_rule(text) -> dict[str, int]`
- `def enforce_context_budget(resolution, rendered) -> dict[str, int]`
- `def main() -> int`

### `resolve_rule_contracts.py`

Resolve canonical governance contracts for Cursor rule bindings.

- `ContractRecord`
- `ContractIndex`
- `def parse_semver(value) -> tuple[int, int, int]`
- `def version_matches(version, constraint) -> bool`
- `def canonical_contract_digest(document) -> str`
- `def load_contract_index(root, registry_path) -> ContractIndex`
- `def resolve_binding(binding, contract_index) -> dict[str, Any]`
- `def directive_key(directive) -> tuple[str, str, str]`
- _+3 more public symbol(s)_

### `validate_doctrine_ratchet.py`

Enforce the no-new-hidden-doctrine migration ratchet. Policy: Legacy doctrine debt may remain temporarily. Legacy doctrine debt may decrease. Legacy doctrine debt may NEVER increase silently.

- `def build_baseline() -> dict[str, Any]`
- `def validate_baseline_structure(baseline) -> list[str]`
- `def compare_to_baseline() -> dict[str, Any]` — Compare current repository state to immutable ratchet allowances.
- `def tighten_baseline() -> dict[str, Any]` — Return a baseline that can only become stricter.
- `def main() -> int`

### `validate_rule_binding.py`

Fail-closed validator for canonical Cursor rule activation bindings.

- `Finding`
- `def validate_binding(binding, contract_index, root) -> list[Finding]`
- `def validate_all_bindings(root, registry_path) -> list[Finding]`
- `def main() -> int`

### `validate_rule_projections.py`

Independent assurance for generated contract-first Cursor rule projections.

- `Finding`
- `def validate_projection_set(root, registry_path) -> list[Finding]`
- `def main() -> int`

## Dependencies

**Internal:** `build_doctrine_census`, `cluster_doctrine`, `cursor_rules`, `detect_hidden_doctrine`, `extract_doctrine`, `generate_rules_manifest`, `lib`, `render_cursor_rule`, `resolve_rule_contracts`, `validate_rule_binding`

**External:** `yaml`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
