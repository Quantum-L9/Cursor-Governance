#!/usr/bin/env python3
"""Validate GAR's graph-bound Product Architecture Decision with v0.8 reasoning-foursome intervention and signal discipline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "product-architecture-decision.schema.json"
DEPRECATED_DISPOSITIONS = {"HARVEST_THEN_DECIDE"}


class DecisionError(ValueError):
    pass


def load(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)


def digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return "sha256:" + hashlib.sha256(body).hexdigest()


def validate(
    decision: Any, *, envelope: Any | None = None, graph: Any | None = None
) -> dict[str, Any]:
    if not isinstance(decision, dict):
        raise DecisionError("GAR_DECISION_INVALID: decision must be an object")

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(
        jsonschema.Draft202012Validator(schema).iter_errors(decision), key=lambda e: list(e.path)
    )
    if errors:
        rendered = "; ".join(
            f"{'.'.join(str(p) for p in err.path) or '<root>'}: {err.message}" for err in errors
        )
        raise DecisionError(f"GAR_DECISION_INVALID: {rendered}")

    if decision["status"] == "ACCEPTED" and decision["architecture"]["material_unknowns"]:
        raise DecisionError(
            "GAR_DECISION_UNRESOLVED: ACCEPTED decision cannot carry material_unknowns"
        )

    dispositions = {item["disposition"] for item in decision["architecture"]["owner_dispositions"]}
    deprecated = dispositions & DEPRECATED_DISPOSITIONS
    if deprecated:
        raise DecisionError(f"GAR_DECISION_DEPRECATED_DISPOSITION: {sorted(deprecated)}")

    reasoning_class = decision["reasoning"]["intervention_class"]
    architecture_class = decision["architecture"]["intervention_class"]
    if reasoning_class != architecture_class:
        raise DecisionError(
            "GAR_DECISION_INTERVENTION_FIDELITY: architecture intervention_class must match bound First-Order projection"
        )

    if (
        reasoning_class in {"HARVEST_SEMANTICS", "BUILD_NEW"}
        and not decision["reasoning"]["solution_surface_census_ref"]
    ):
        raise DecisionError(
            "GAR_DECISION_INTERVENTION_UNBOUND: harvest/build requires a solution-surface census reference"
        )

    second_before = decision["reasoning"]["second_order_before_ref"]
    predicted_leverage = decision["reasoning"]["predicted_leverage_ref"]
    signal_prediction = decision["reasoning"]["signal_prediction_propagation_ref"]
    if (second_before is not None or predicted_leverage is not None) and signal_prediction is None:
        raise DecisionError(
            "GAR_DECISION_SIGNAL_UNBOUND: material pre-architecture reasoning requires a Signal Leverage prediction-propagation reference"
        )

    if envelope is not None and decision["idea_execute"]["envelope_digest"] != digest(envelope):
        raise DecisionError("GAR_DECISION_STALE: envelope digest does not match")

    if graph is not None:
        if decision["idea_execute"]["graph_digest"] != digest(graph):
            raise DecisionError("GAR_DECISION_STALE: graph digest does not match")
        graph_units = {
            str(unit.get("id")) for unit in graph.get("units", []) if isinstance(unit, dict)
        }
        covered = set(decision["idea_execute"]["graph_unit_ids"])
        if not covered <= graph_units:
            raise DecisionError(
                "GAR_DECISION_COVERAGE: decision cites unknown graph units "
                + str(sorted(covered - graph_units))
            )

    return decision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("decision")
    parser.add_argument("--envelope")
    parser.add_argument("--graph")
    args = parser.parse_args()
    try:
        validate(
            load(Path(args.decision)),
            envelope=load(Path(args.envelope)) if args.envelope else None,
            graph=load(Path(args.graph)) if args.graph else None,
        )
    except (DecisionError, OSError, ValueError, yaml.YAMLError, json.JSONDecodeError) as exc:
        print(f"GAR_PRODUCT_ARCHITECTURE_DECISION: FAIL\n- {exc}")
        return 1
    print("GAR_PRODUCT_ARCHITECTURE_DECISION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
