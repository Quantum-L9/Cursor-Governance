# Skill Routing

**Path:** `ops/skill_routing` | **Tier:** discovered

## Purpose

Cursor-primary shared skill-routing ingress (CANONICAL_LAW §2.1).



## Components

### `MaterializationError`

A routed skill could not be resolved to a valid canonical resource.

- File: `ops/skill_routing/materialize.py` (L26–27)
- Methods: _none_

### `ReceiptError`

The receipt is absent, malformed, out of scope, stale, or unbound.

- File: `ops/skill_routing/receipt.py` (L51–52)
- Methods: _none_

### `RegistryError`

The registry is missing, corrupt, wrong-schema, or shape-invalid.

- File: `ops/skill_routing/registry.py` (L40–41)
- Methods: _none_

### `Registry`

Validated registry with a name index and generation identity.

- File: `ops/skill_routing/registry.py` (L67–103)
- Methods: `routing`, `skills`, `skills_root`, `identity`, `resolve_skill_record`

### `RouteLocator`

No description

- File: `ops/skill_routing/session_locator.py` (L84–110)
- Methods: `as_dict`, `env`, `banner`

## Functions

- `def canonical_skill_root(root) -> Path`
- `def resolve_skill_resource(name, record, root) -> dict[str, str]` — Resolve one registry record to a validated resource or raise.
- `def materialize_route(decision, registry, root) -> dict[str, Any]` — Return ``{"primary": resource, "supporting": [resource, ...]}``.
- `def ttl_seconds() -> int`
- `def prompt_digest(prompt) -> str`
- `def build_receipt() -> dict[str, Any]`
- `def atomic_write_json(path, payload) -> None` — Same-directory temp → flush → fsync → os.replace.
- `def write_receipt(receipt, state_root) -> Path` — Persist ``receipt`` at its conversation-scoped path and return it.
- `def validate_receipt(receipt) -> list[str]` — Return every reason the receipt must not be consumed (empty == valid).
- `def read_receipt(conversation_id) -> dict[str, Any]` — Load and validate the current receipt for a conversation or raise.
- `def resolve_governance_root(start) -> Path` — Resolve the governance root that carries the generated registry.
- `def validate_registry(data) -> None` — Raise ``RegistryError`` unless ``data`` is a well-formed v2 registry.
- `def load_registry(root) -> Registry` — Load and validate the registry under ``root``; raise ``RegistryError``.
- `def skill_index(registry) -> dict[str, dict[str, Any]]` — Name → record index for a ``Registry`` or a raw registry dict.
- `def resolve_prompt(prompt, root) -> dict[str, Any]`
- `def main(argv) -> int`
- `def normalize(text) -> str`
- `def phrase_hit(prompt, phrase) -> bool`
- `def resolve_root(start) -> Path` — Resolve governance root — delegates to the shared registry layer.
- `def load_registry(root) -> dict[str, Any]` — Raw registry dict for scoring. Validation lives in registry.load_registry.

## Exports

`DEFAULT_TTL_SECONDS`, `MAX_SUPPORTING`, `MaterializationError`, `RECEIPT_SCHEMA`, `REGISTRY_REL`, `ReceiptError`, `Registry`, `RegistryError`, `RouteLocator`, `SCHEMA_VERSION`, `SKILLS_REL`, `STATUSES`, `atomic_write_json`, `build_receipt`, `canonical_skill_root`, `load_registry`, `load_validated_registry`, `locator_from_payload`, `materialize_route`, `prompt_digest` (+9 more)

## Dependencies

`__future__`, `argparse`, `dataclasses`, `hashlib`, `importlib`, `importlib.util`, `json`, `materialize`, `os`, `pathlib`, `re`, `receipt`, `registry`, `route_prompt`, `session_locator`, `sys`, `tempfile`, `time`, `typing`

<!-- l9-module-readme: generated-from-ast -->
