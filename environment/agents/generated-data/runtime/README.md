# Runtime

**Path:** `environment/agents/generated-data/runtime` | **Kind:** subsystem

## Modules

### `__init__.py`

L9 Subagent-Generated Data runtime.

### `classifier.py`

- `ClassificationFailure` — Raised when a generated data unit cannot be classified safely.
- `Classification`
- `GeneratedDataClassifier` — Deterministically enrich validated generated data units.
- `def main(argv) -> int`

### `harvester.py`

- `HarvestFailure` — Raised when harvesting cannot proceed safely.
- `HarvestedUnit`
- `HarvestResult`
- `SubagentDataHarvester` — Extract reusable generated-data units from a validated packet.
- `def main(argv) -> int`

### `learning_closure.py`

- `LearningClosureFailure` — Raised when a closure report cannot be computed.
- `ClosureCheck`
- `LearningClosureResult`
- `LearningClosureEvaluator` — Determine whether a campaign may seal its learning lifecycle.
- `def main(argv) -> int`

### `packet_validator.py`

- `PacketValidationFailure` — Raised when a subagent data packet violates a required contract.
- `ValidationFinding`
- `ValidationReport`
- `PacketValidator` — Validate packets against Wave 1 schemas and role obligations.
- `def main(argv) -> int`

### `promotion_gate.py`

- `PromotionFailure` — Raised when a promotion result cannot be determined safely.
- `PromotionResult`
- `PromotionGate` — Apply L9 promotion-risk rules to routing decisions.
- `def main(argv) -> int`

### `routing_engine.py`

- `RoutingFailure` — Raised when no safe routing decision can be produced.
- `RoutingDecision`
- `RoutingEngine` — Route harvested generated-data units using declarative route files.
- `def main(argv) -> int`

## Dependencies

**Internal:** `classifier`, `packet_validator`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
