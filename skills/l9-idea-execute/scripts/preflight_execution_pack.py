#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from typing import Any

from _common import ContractError, dump_yaml, load_data
from validate_adapter_snapshot import validate_adapter_snapshot
from validate_envelope import validate_envelope
from validate_graph import validate_graph
from validate_receipt import validate_receipt


def _artifact(ref: str, status: str, reason: str) -> dict[str, str]:
    return {"ref": ref, "status": status, "reason": reason}


def preflight(
    envelope: Any,
    *,
    graph: Any | None = None,
    receipt: Any | None = None,
    adapter_snapshots: list[tuple[str, Any]] | None = None,
) -> dict[str, Any]:
    artifacts: list[dict[str, str]] = []
    blockers: list[dict[str, str]] = []
    overall = "REUSABLE"

    try:
        validated_envelope = validate_envelope(envelope)
        artifacts.append(_artifact("envelope", "REUSABLE", "validated source authority"))
    except ContractError as exc:
        return {
            "schema": "l9.idea-execute.execution-pack-preflight/v1",
            "status": "BLOCKED",
            "artifacts": [_artifact("envelope", "INVALID", str(exc))],
            "blockers": [{"code": "ENVELOPE_INVALID", "detail": str(exc)}],
            "earliest_invalid_layer": "envelope",
        }

    validated_graph: dict[str, Any] | None = None
    if graph is None:
        overall = "REPAIRABLE"
        artifacts.append(_artifact("graph", "STALE_REGENERATE", "graph not supplied"))
    else:
        try:
            validated_graph = validate_graph(graph, validated_envelope)
            artifacts.append(_artifact("graph", "REUSABLE", "parent digest binding verified"))
        except ContractError as exc:
            overall = "REPAIRABLE"
            artifacts.append(_artifact("graph", "STALE_REGENERATE", str(exc)))

    if receipt is not None:
        if validated_graph is None:
            overall = "REPAIRABLE"
            artifacts.append(
                _artifact(
                    "receipt",
                    "STALE_REGENERATE",
                    "graph is not reusable; receipt depends on graph",
                )
            )
        else:
            try:
                validate_receipt(receipt, validated_graph, validated_envelope)
                artifacts.append(_artifact("receipt", "REUSABLE", "digest chain verified"))
            except ContractError as exc:
                overall = "REPAIRABLE"
                artifacts.append(_artifact("receipt", "STALE_REGENERATE", str(exc)))

    for ref, snapshot in adapter_snapshots or []:
        try:
            validate_adapter_snapshot(snapshot)
            artifacts.append(_artifact(ref, "REUSABLE", "adapter snapshot contract validated"))
        except ContractError as exc:
            overall = "REPAIRABLE"
            artifacts.append(_artifact(ref, "INVALID", str(exc)))

    earliest = None
    for layer in ("envelope", "graph", "receipt"):
        match = next(
            (a for a in artifacts if a["ref"] == layer and a["status"] != "REUSABLE"),
            None,
        )
        if match:
            earliest = layer
            break
    if earliest is None:
        invalid_adapter = next((a for a in artifacts if a["status"] != "REUSABLE"), None)
        if invalid_adapter:
            earliest = invalid_adapter["ref"]

    return {
        "schema": "l9.idea-execute.execution-pack-preflight/v1",
        "status": overall,
        "artifacts": artifacts,
        "blockers": blockers,
        "earliest_invalid_layer": earliest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--envelope", required=True)
    parser.add_argument("--graph")
    parser.add_argument("--receipt")
    parser.add_argument("--adapter", action="append", default=[])
    args = parser.parse_args()

    try:
        adapters = [(path, load_data(path)) for path in args.adapter]
        report = preflight(
            load_data(args.envelope),
            graph=load_data(args.graph) if args.graph else None,
            receipt=load_data(args.receipt) if args.receipt else None,
            adapter_snapshots=adapters,
        )
    except ContractError as exc:
        print(f"EXECUTION_PACK_PREFLIGHT: FAIL\n- {exc}", file=sys.stderr)
        return 1

    print(dump_yaml(report), end="")
    if report["status"] == "REUSABLE":
        return 0
    if report["status"] == "REPAIRABLE":
        return 3
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
