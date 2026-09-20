# Runtime

**Path:** `autonomy/runtime` | **Kind:** subsystem

## Modules

### `__init__.py`

Wave 2 enforcement runtime.

### `artifacts.py`

- `ArtifactValidator`

### `capability_gateway.py`

- `CapabilityGateway`
- `def normalize_path(value) -> str`
- `def path_matches(pattern, path) -> bool`

### `claims.py`

- `ClaimRegistry`
- `def claims_collide() -> bool` — Whether two claims on *overlapping* resource keys may not be held at once.
- `def resource_keys_overlap(key_a, key_b) -> bool` — Canonical resource-key overlap rule for the claim plane.
- `def claim_scopes_conflict() -> bool` — One primitive for scope-aware claim conflict.

### `cli.py`

- `def main(argv) -> int`

### `engine.py`

- `AutonomyRuntime`

### `leases.py`

- `LeaseManager`
- `def producer_agent_ids(connection) -> list[str]` — Agents that produced (or hold/held the lease on) the given actions.
- `def independence_sources(action) -> list[str]` — Actions this one must be independent from: the explicit declaration
- `def requires_independence(action) -> bool`

### `receipts.py`

- `ReceiptChain`

### `scheduler.py`

Saturation-seeking, claim-aware scheduler for the autonomy control plane.

- `Scheduler`

### `store.py`

- `RuntimeStore`
- `def canonical_dump(value) -> str`

### `timeutil.py`

- `def utc_now() -> datetime`
- `def utc_now_text() -> str`
- `def parse_timestamp(value) -> datetime`
- `def add_seconds(value, seconds) -> datetime`
- `def timestamp_text(value) -> str`

### `types.py`

- `ActionStatus`
- `LeaseStatus`
- `CampaignRuntimeState`
- `Lease`
- `AuthorizationDecision`
- `ScheduledAction`
- `SchedulingCycle` — One saturation cycle: what was admitted and, when short, why.

## Dependencies

**Internal:** `autonomy`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
