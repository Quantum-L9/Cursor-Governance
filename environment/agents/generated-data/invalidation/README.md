# Invalidation

**Path:** `environment/agents/generated-data/invalidation` | **Kind:** subsystem

## Modules

### `__init__.py`

Structured repository-event bridge for governed memory invalidation.

### `repository_event_bridge.py`

Structured repository-change to memory-invalidation bridge.

- `RepositoryEventBridgeError` — Base repository invalidation bridge failure.
- `RepositoryStateError` — The repository state is unsuitable for deterministic diffing.
- `InvalidationCollisionError` — An immutable event ID was reused with different content.
- `InvalidationTransportError` — The invalidation destination failed or returned an invalid response.
- `ChangeKind`
- `ChangedPath`
- `RepositoryChangeEvent`
- `InvalidationDispatchResult`
- _+17 more public symbol(s)_

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
