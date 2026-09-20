# Orchestration

**Path:** `environment/agents/generated-data/orchestration` | **Tier:** discovered

## Purpose

L9 Subagent-Generated Data — Instantiation Wave 1 (durable orchestration).



## Components

### `DeliveryError`

Base delivery failure.

- File: `environment/agents/generated-data/orchestration/delivery_worker.py` (L25–26)
- Methods: _none_

### `DestinationRejected`

Destination returned a permanent rejection.

- File: `environment/agents/generated-data/orchestration/delivery_worker.py` (L29–30)
- Methods: _none_

### `DeliveryTransport`

No description

- File: `environment/agents/generated-data/orchestration/delivery_worker.py` (L33–39)
- Methods: `deliver`

### `DeliveryWorkerConfiguration`

No description

- File: `environment/agents/generated-data/orchestration/delivery_worker.py` (L43–52)
- Methods: _none_

### `DeliveryExecutionResult`

No description

- File: `environment/agents/generated-data/orchestration/delivery_worker.py` (L56–82)
- Methods: `to_dict`

### `JsonCommandTransport`

Delegate a delivery envelope to an existing JSON command.

- File: `environment/agents/generated-data/orchestration/delivery_worker.py` (L85–127)
- Methods: `deliver`

### `RouteOutboxTransport`

Durably enqueue a non-memory routed unit.

- File: `environment/agents/generated-data/orchestration/delivery_worker.py` (L130–176)
- Methods: `deliver`

### `MemoryTransport`

Reuse the governed Graphiti candidate adapter.

- File: `environment/agents/generated-data/orchestration/delivery_worker.py` (L179–237)
- Methods: `deliver`

### `DeliveryWorker`

No description

- File: `environment/agents/generated-data/orchestration/delivery_worker.py` (L240–906)
- Methods: `run_once`, `run_batch`, `drain_memory_outbox`

### `PriorWaveModuleError`

Raised when a required prior-wave module or symbol cannot be loaded.

- File: `environment/agents/generated-data/orchestration/module_loader.py` (L42–43)
- Methods: _none_

### `PriorWaveModuleLoader`

Import runtime/adapter modules from a Cursor-Governance checkout.

- File: `environment/agents/generated-data/orchestration/module_loader.py` (L46–100)
- Methods: `load_runtime_module`, `load_adapter_module`, `validate_required_symbols`

### `ProcessingError`

Raised when a packet cannot be processed safely.

- File: `environment/agents/generated-data/orchestration/processor.py` (L27–28)
- Methods: _none_

## Functions

- `def main() -> int`
- `def utc_now_text() -> str`
- `def deterministic_id(prefix, payload) -> str`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `collections.abc`, `contextlib`, `dataclasses`, `datetime`, `enum`, `hashlib`, `importlib`, `json`, `module_loader`, `os`, `pathlib`, `receipts`, `retry_policy`, `sqlite3`, `state_store`, `subprocess`, `sys`, `tempfile`, `types`, `typing`

<!-- l9-module-readme: generated-from-ast -->
