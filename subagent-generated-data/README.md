# Subagent-Generated Data

Implementation of the **L9 Subagent-Generated Data Law**
(`law/SUBAGENT_GENERATED_DATA_LAW.md`, `law_id: l9.subagent_generated_data_law.v1`).

Every governed subagent execution produces two outputs: the primary artifact and
the *generated data* created while producing it. This subsystem captures,
validates, classifies, routes, and gates that generated data so reusable value
compounds instead of being discarded (law §1).

## Layout

| Path | Purpose |
|------|---------|
| `law/` | The canonical law text. |
| `schemas/` | JSON Schema (draft 2020-12) for the packet, generated-data unit, routing decision, and learning closure. |
| `roles/` | Role-specific generated-data obligations (recon, synthesis, executor, verifier, reviewer, poller — law §11). |
| `runtime/` | Deterministic enforcement pipeline (law §29). |
| `routes/` | Destination route definitions (law §15–§16). |
| `adapters/` | Repository-class and destination adapters (law §28). |
| `tests/` | Conformance, routing, negative, and golden tests (law §33). |

## Runtime pipeline (law §29)

`runtime/pipeline.py:process_packet` runs the enforcement sequence:

```
validate → persist as evidence → harvest → classify → dedupe →
conflict-check → route → promotion-decide → (learning-closure)
```

Each stage is a focused module:

- `packet_validator.py` — enforces the SGD invariants (law §31); a rejected
  packet never enters routing.
- `harvester.py` — lifts validated units out of the packet (capture before
  distillation, law §13).
- `classifier.py` — deterministic class → candidate-routes + risk mapping (§14, §18).
- `deduplicator.py` — collapses duplicate truths, preserves lineage (§19).
- `conflict_handler.py` — surfaces conflicts; high-impact ones block promotion (§20).
- `routing_engine.py` — assigns routes + one promotion decision per unit (§15–§18).
- `promotion_gate.py` — independent authority check (§3.3); high-risk needs
  designated authority (SGD-014).
- `learning_closure.py` — a campaign may not seal until closure passes (§25).
- `invalidation.py` / `reuse_tracking.py` / `evidence_archive.py` — freshness,
  behavioral-reuse accounting, and Tier-1 evidence retention (§22–§26).

## Invariants

The eighteen non-negotiable invariants (SGD-001 … SGD-018, law §31) are enforced
in code and asserted by the test suite. Producing agents never self-promote
(SGD-003); promotion is always an independent decision.

## Running the checks

```bash
uv run --extra dev pytest subagent-generated-data
uv run --extra dev ruff check subagent-generated-data
uv run --extra dev mypy subagent-generated-data/runtime
```
