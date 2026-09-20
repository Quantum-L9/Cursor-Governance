# Runtime

**Path:** `autonomy/runtime` | **Tier:** discovered

## Purpose

Wave 2 enforcement runtime.



## Components

### `ArtifactValidator`

No description

- File: `autonomy/runtime/artifacts.py` (L15–343)
- Methods: `submit`, `invalidate`

### `CapabilityGateway`

No description

- File: `autonomy/runtime/capability_gateway.py` (L17–417)
- Methods: `authorize`, `require`

### `ClaimRegistry`

No description

- File: `autonomy/runtime/claims.py` (L126–239)
- Methods: `assert_available`, `create_claims`, `release_for_lease`

### `AutonomyRuntime`

No description

- File: `autonomy/runtime/engine.py` (L22–215)
- Methods: `from_repository`, `bootstrap`, `status`, `suspend`, `verify_receipts`

### `LeaseManager`

No description

- File: `autonomy/runtime/leases.py` (L82–554)
- Methods: `issue`, `acknowledge`, `heartbeat`, `sweep`, `release`, `revoke`, `get`, `assert_active`

### `ReceiptChain`

No description

- File: `autonomy/runtime/receipts.py` (L17–161)
- Methods: `append`, `verify`

### `Scheduler`

No description

- File: `autonomy/runtime/scheduler.py` (L45–465)
- Methods: `global_policy`, `resource_classes`, `fill_policy`, `reserved_control_slots`, `provider_concurrency_ceiling`, `worker_concurrency_ceiling`, `backpressure_enabled`, `record_provider_throttle`

### `RuntimeStore`

No description

- File: `autonomy/runtime/store.py` (L13–401)
- Methods: `connect`, `transaction`, `initialize`, `register_campaign`, `get_campaign`, `get_action`, `list_actions`, `set_campaign_state`

### `ActionStatus`

No description

- File: `autonomy/runtime/types.py` (L9–18)
- Methods: _none_

### `LeaseStatus`

No description

- File: `autonomy/runtime/types.py` (L21–25)
- Methods: _none_

### `CampaignRuntimeState`

No description

- File: `autonomy/runtime/types.py` (L28–38)
- Methods: _none_

### `Lease`

No description

- File: `autonomy/runtime/types.py` (L42–55)
- Methods: _none_

## Functions

- `def normalize_path(value) -> str`
- `def path_matches(pattern, path) -> bool`
- `def claims_collide() -> bool` — Whether two claims on *overlapping* resource keys may not be held at once.
- `def resource_keys_overlap(key_a, key_b) -> bool` — Canonical resource-key overlap rule for the claim plane.
- `def claim_scopes_conflict() -> bool` — One primitive for scope-aware claim conflict.
- `def main(argv) -> int`
- `def producer_agent_ids(connection) -> list[str]` — Agents that produced (or hold/held the lease on) the given actions.
- `def independence_sources(action) -> list[str]` — Actions this one must be independent from: the explicit declaration
- `def requires_independence(action) -> bool`
- `def canonical_dump(value) -> str`
- `def utc_now() -> datetime`
- `def utc_now_text() -> str`
- `def parse_timestamp(value) -> datetime`
- `def add_seconds(value, seconds) -> datetime`
- `def timestamp_text(value) -> str`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `autonomy.errors`, `autonomy.io`, `autonomy.models`, `autonomy.policy_loader`, `autonomy.runtime.artifacts`, `autonomy.runtime.capability_gateway`, `autonomy.runtime.claims`, `autonomy.runtime.leases`, `autonomy.runtime.receipts`, `autonomy.runtime.scheduler`, `autonomy.runtime.store`, `autonomy.runtime.timeutil`, `autonomy.runtime.types`, `autonomy.validation.graph_linter`, `collections`, `collections.abc`, `contextlib`, `dataclasses`, `datetime`, `enum`, `fnmatch`, `hashlib`, `hmac`

<!-- l9-module-readme: generated-from-ast -->
