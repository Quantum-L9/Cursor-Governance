# Runtime

**Path:** `environment/agents/generated-data/runtime` | **Tier:** discovered

## Purpose

L9 Subagent-Generated Data runtime.



## Components

### `ClassificationFailure`

Raised when a generated data unit cannot be classified safely.

- File: `environment/agents/generated-data/runtime/classifier.py` (L76–77)
- Methods: _none_

### `Classification`

No description

- File: `environment/agents/generated-data/runtime/classifier.py` (L81–105)
- Methods: `to_dict`

### `GeneratedDataClassifier`

Deterministically enrich validated generated data units.

- File: `environment/agents/generated-data/runtime/classifier.py` (L108–290)
- Methods: `classify`, `classify_packet`

### `HarvestFailure`

Raised when harvesting cannot proceed safely.

- File: `environment/agents/generated-data/runtime/harvester.py` (L18–19)
- Methods: _none_

### `HarvestedUnit`

No description

- File: `environment/agents/generated-data/runtime/harvester.py` (L23–49)
- Methods: `to_dict`

### `HarvestResult`

No description

- File: `environment/agents/generated-data/runtime/harvester.py` (L53–69)
- Methods: `to_dict`

### `SubagentDataHarvester`

Extract reusable generated-data units from a validated packet.

- File: `environment/agents/generated-data/runtime/harvester.py` (L72–233)
- Methods: `harvest`

### `LearningClosureFailure`

Raised when a closure report cannot be computed.

- File: `environment/agents/generated-data/runtime/learning_closure.py` (L10–11)
- Methods: _none_

### `ClosureCheck`

No description

- File: `environment/agents/generated-data/runtime/learning_closure.py` (L15–27)
- Methods: `to_dict`

### `LearningClosureResult`

No description

- File: `environment/agents/generated-data/runtime/learning_closure.py` (L31–49)
- Methods: `to_dict`

### `LearningClosureEvaluator`

Determine whether a campaign may seal its learning lifecycle.

- File: `environment/agents/generated-data/runtime/learning_closure.py` (L52–302)
- Methods: `evaluate`

### `PacketValidationFailure`

Raised when a subagent data packet violates a required contract.

- File: `environment/agents/generated-data/runtime/packet_validator.py` (L42–43)
- Methods: _none_

## Functions

- `def main(argv) -> int`
- `def main(argv) -> int`
- `def main(argv) -> int`
- `def main(argv) -> int`
- `def main(argv) -> int`
- `def main(argv) -> int`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `classifier`, `collections.abc`, `dataclasses`, `hashlib`, `json`, `packet_validator`, `pathlib`, `sys`, `typing`

<!-- l9-module-readme: generated-from-ast -->
