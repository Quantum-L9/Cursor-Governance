# Skill Routing

**Path:** `ops/skill_routing` | **Kind:** subsystem

## Modules

### `__init__.py`

Cursor-primary shared skill-routing ingress (CANONICAL_LAW §2.1).

Exports: `MaterializationError`, `RECEIPT_SCHEMA`, `REGISTRY_REL`, `ReceiptError`, `Registry`, `RegistryError`, `RouteLocator`, `build_receipt`, `load_registry`, `load_validated_registry`, `locator_from_payload`, `materialize_route` (+6 more)

### `materialize.py`

Materialize a RouteDecision into exact, validated canonical skill resources.

- `MaterializationError` — A routed skill could not be resolved to a valid canonical resource.
- `def canonical_skill_root(root) -> Path`
- `def resolve_skill_resource(name, record, root) -> dict[str, str]` — Resolve one registry record to a validated resource or raise.
- `def materialize_route(decision, registry, root) -> dict[str, Any]` — Return ``{"primary": resource, "supporting": [resource, ...]}``.

Exports: `MAX_SUPPORTING`, `MaterializationError`, `canonical_skill_root`, `materialize_route`, `resolve_skill_resource`

### `receipt.py`

Conversation-scoped, atomically written route receipts (schema v2).

- `ReceiptError` — The receipt is absent, malformed, out of scope, stale, or unbound.
- `def ttl_seconds() -> int`
- `def prompt_digest(prompt) -> str`
- `def build_receipt() -> dict[str, Any]`
- `def atomic_write_json(path, payload) -> None` — Same-directory temp → flush → fsync → os.replace.
- `def write_receipt(receipt, state_root) -> Path` — Persist ``receipt`` at its conversation-scoped path and return it.
- `def validate_receipt(receipt) -> list[str]` — Return every reason the receipt must not be consumed (empty == valid).
- `def read_receipt(conversation_id) -> dict[str, Any]` — Load and validate the current receipt for a conversation or raise.

Exports: `DEFAULT_TTL_SECONDS`, `RECEIPT_SCHEMA`, `ReceiptError`, `STATUSES`, `atomic_write_json`, `build_receipt`, `locator_from_payload`, `prompt_digest`, `read_receipt`, `validate_receipt`, `write_receipt`

### `registry.py`

Skill registry loading and validation — the runtime side of registry v2.

- `RegistryError` — The registry is missing, corrupt, wrong-schema, or shape-invalid.
- `Registry` — Validated registry with a name index and generation identity.
- `def resolve_governance_root(start) -> Path` — Resolve the governance root that carries the generated registry.
- `def validate_registry(data) -> None` — Raise ``RegistryError`` unless ``data`` is a well-formed v2 registry.
- `def load_registry(root) -> Registry` — Load and validate the registry under ``root``; raise ``RegistryError``.
- `def skill_index(registry) -> dict[str, dict[str, Any]]` — Name → record index for a ``Registry`` or a raw registry dict.

Exports: `REGISTRY_REL`, `Registry`, `RegistryError`, `SCHEMA_VERSION`, `SKILLS_REL`, `load_registry`, `resolve_governance_root`, `skill_index`, `validate_registry`

### `resolve.py`

Shared L9 resolver — the gateway's manual fallback and a diagnostics CLI.

- `def resolve_prompt(prompt, root) -> dict[str, Any]`
- `def main(argv) -> int`

### `route_prompt.py`

Shared L9 skill-routing scorer — Cursor-primary ownership (CANONICAL_LAW §2.1).

- `def normalize(text) -> str`
- `def phrase_hit(prompt, phrase) -> bool`
- `def resolve_root(start) -> Path` — Resolve governance root — delegates to the shared registry layer.
- `def load_registry(root) -> dict[str, Any]` — Raw registry dict for scoring. Validation lives in registry.load_registry.
- `def score_description_match(prompt, skill) -> int` — Fallback scorer from skill when_to_use / description when no route fires.
- `def retrieve_candidates(registry) -> list[dict[str, Any]]` — Eligible routes for scoring — the retrieval boundary.
- `def rank_candidates(normalized, routes, explicit) -> tuple[tuple[int, dict[str, Any], str] | None, set[str]]` — Score eligible routes; return (best, blocked_primaries).
- `def route_prompt(prompt, registry) -> dict[str, Any] | None`

### `session_locator.py`

One route-receipt identity per Cursor conversation.

- `RouteLocator`
- `def default_state_root() -> Path`
- `def conversation_key(conversation_id) -> str` — sha256 of the UTF-8 conversation id, truncated to a safe dir token.
- `def normalize_workspace_roots(roots) -> list[str]`
- `def workspace_key(roots) -> str`
- `def extract_conversation_id(payload) -> str` — The single correlation adapter between Cursor payloads and receipts.
- `def receipt_path_for(conversation_id, state_root) -> Path`
- `def locator_from_payload(payload, state_root) -> RouteLocator | None` — Return a locator, or ``None`` when the payload has no conversation.
- _+1 more public symbol(s)_

## Dependencies

**Internal:** `materialize`, `receipt`, `registry`, `route_prompt`, `session_locator`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
