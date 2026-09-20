# Orchestration

**Path:** `environment/agents/generated-data/orchestration` | **Kind:** subsystem

## Modules

### `__init__.py`

L9 Subagent-Generated Data — Instantiation Wave 1 (durable orchestration).

### `delivery_worker.py`

- `DeliveryError` — Base delivery failure.
- `DestinationRejected` — Destination returned a permanent rejection.
- `DeliveryTransport`
- `DeliveryWorkerConfiguration`
- `DeliveryExecutionResult`
- `JsonCommandTransport` — Delegate a delivery envelope to an existing JSON command.
- `RouteOutboxTransport` — Durably enqueue a non-memory routed unit.
- `MemoryTransport` — Reuse the governed Graphiti candidate adapter.
- _+2 more public symbol(s)_

### `module_loader.py`

Load prior-wave runtime and adapter modules by their real filesystem path.

- `PriorWaveModuleError` — Raised when a required prior-wave module or symbol cannot be loaded.
- `PriorWaveModuleLoader` — Import runtime/adapter modules from a Cursor-Governance checkout.

### `processor.py`

Persisted generated-data processing with resumable stage snapshots.

- `ProcessingError` — Raised when a packet cannot be processed safely.
- `ProcessingConfiguration`
- `ProcessingResult`
- `GeneratedDataProcessor` — Deterministic, persisted and resumable generated-data pipeline.

### `receipts.py`

Hash-chained processing receipts with tamper-evident verification.

- `ProcessingReceiptChain` — Append-only, per-job hash chain of processing receipts.

### `retry_policy.py`

Deterministic retry classification and backoff decisions.

- `RetryClass`
- `RetryDecision`
- `RetryPolicy` — Bounded exponential-backoff retry policy.

### `state_store.py`

SQLite-backed durable state for the generated-data pipeline.

- `PipelineState`
- `StateStoreError` — Base state-store failure.
- `JobNotFoundError` — Raised when a referenced job does not exist.
- `StateTransitionError` — Raised when an optimistic state transition does not match.
- `ProcessingJob`
- `DeliveryAttempt`
- `JobEvent`
- `CampaignStatus`
- _+4 more public symbol(s)_

## Dependencies

**Internal:** `module_loader`, `receipts`, `retry_policy`, `state_store`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
