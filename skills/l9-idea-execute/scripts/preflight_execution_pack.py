#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from typing import Any

from _common import ContractError, dump_yaml, load_data
from validate_adapter_snapshot import compare_adapter_evidence, validate_adapter_snapshot
from validate_envelope import validate_envelope
from validate_graph import validate_graph
from validate_receipt import validate_receipt


def _artifact(ref: str, status: str, reason: str) -> dict[str, str]:
    return {"ref": ref, "status": status, "reason": reason}


def _bind_snapshot_to_graph(snapshot: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    graph_by_id = {unit["id"]: unit for unit in graph["units"]}
    unit = graph_by_id.get(snapshot["unit_id"])
    if unit is None:
        raise ContractError(
            "ADAPTER_CONTRACT_CONFLICT: capability snapshot unit_id is not present in graph"
        )
    if snapshot["adapter"] != unit["adapter"]:
        raise ContractError(
            "ADAPTER_CONTRACT_CONFLICT: capability snapshot adapter does not match graph unit"
        )
    return unit


def preflight(
    envelope: Any,
    *,
    graph: Any | None = None,
    receipt: Any | None = None,
    adapter_snapshots: list[tuple[str, Any]] | None = None,
    current_adapter_snapshots: list[tuple[str, Any]] | None = None,
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
            artifacts.append(_artifact("graph", "REUSABLE", "parent binding and coverage verified"))
        except ContractError as exc:
            overall = "REPAIRABLE"
            artifacts.append(_artifact("graph", "STALE_REGENERATE", str(exc)))

    current_by_unit: dict[str, tuple[str, dict[str, Any]]] = {}
    for ref, raw_snapshot in current_adapter_snapshots or []:
        try:
            current = validate_adapter_snapshot(raw_snapshot)
            if validated_graph is None:
                raise ContractError(
                    "ADAPTER_CONTRACT_CONFLICT: graph is not reusable; adapter evidence cannot bind"
                )
            _bind_snapshot_to_graph(current, validated_graph)
            if current["unit_id"] in current_by_unit:
                raise ContractError(
                    "ADAPTER_CONTRACT_CONFLICT: multiple current snapshots bind the same graph unit"
                )
            current_by_unit[current["unit_id"]] = (ref, current)
            artifacts.append(_artifact(ref, "REUSABLE", "current graph-unit binding verified"))
        except ContractError as exc:
            overall = "REPAIRABLE"
            artifacts.append(_artifact(ref, "INVALID", str(exc)))

    for ref, raw_snapshot in adapter_snapshots or []:
        try:
            supplied = validate_adapter_snapshot(raw_snapshot)
            if validated_graph is None:
                raise ContractError(
                    "ADAPTER_CONTRACT_CONFLICT: graph is not reusable; adapter evidence cannot bind"
                )
            _bind_snapshot_to_graph(supplied, validated_graph)
            current_entry = current_by_unit.get(supplied["unit_id"])
            if current_entry is None:
                overall = "REPAIRABLE"
                artifacts.append(
                    _artifact(
                        ref,
                        "UNRESOLVED",
                        "fresh current adapter evidence is required before snapshot reuse",
                    )
                )
                continue
            _, current = current_entry
            compare_adapter_evidence(supplied, current)
            artifacts.append(
                _artifact(ref, "REUSABLE", "graph-unit and current source bindings verified")
            )
        except ContractError as exc:
            overall = "REPAIRABLE"
            status = "STALE_REGENERATE" if "ADAPTER_SNAPSHOT_STALE" in str(exc) else "INVALID"
            artifacts.append(_artifact(ref, status, str(exc)))

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
                artifacts.append(
                    _artifact("receipt", "REUSABLE", "digest and unit bindings verified")
                )
            except ContractError as exc:
                overall = "REPAIRABLE"
                artifacts.append(_artifact("receipt", "STALE_REGENERATE", str(exc)))

    earliest = None
    for layer in ("envelope", "graph"):
        match = next(
            (a for a in artifacts if a["ref"] == layer and a["status"] != "REUSABLE"),
            None,
        )
        if match:
            earliest = layer
            break
    if earliest is None:
        adapter_refs = {
            ref for ref, _ in (adapter_snapshots or []) + (current_adapter_snapshots or [])
        }
        invalid_adapter = next(
            (a for a in artifacts if a["ref"] in adapter_refs and a["status"] != "REUSABLE"),
            None,
        )
        if invalid_adapter:
            earliest = invalid_adapter["ref"]
    if earliest is None:
        receipt_artifact = next(
            (a for a in artifacts if a["ref"] == "receipt" and a["status"] != "REUSABLE"),
            None,
        )
        if receipt_artifact:
            earliest = "receipt"

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
    parser.add_argument("--current-adapter", action="append", default=[])
    args = parser.parse_args()

    try:
        adapters = [(path, load_data(path)) for path in args.adapter]
        current_adapters = [(path, load_data(path)) for path in args.current_adapter]
        report = preflight(
            load_data(args.envelope),
            graph=load_data(args.graph) if args.graph else None,
            receipt=load_data(args.receipt) if args.receipt else None,
            adapter_snapshots=adapters,
            current_adapter_snapshots=current_adapters,
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
