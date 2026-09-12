#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from typing import Any

from _common import ContractError, dump_yaml, load_data
from validate_adapter_snapshot import compare_adapter_evidence, validate_adapter_snapshot
from validate_graph import validate_graph


def _bind_snapshot_to_unit(snapshot: dict[str, Any], unit: dict[str, Any]) -> None:
    if snapshot["unit_id"] != unit.get("id"):
        raise ContractError(
            "ADAPTER_CONTRACT_CONFLICT: capability snapshot unit_id does not match execution unit"
        )
    if snapshot["adapter"] != unit.get("adapter"):
        raise ContractError(
            "ADAPTER_CONTRACT_CONFLICT: capability snapshot adapter does not match execution unit"
        )


def check_unit(
    unit: dict[str, Any],
    current_caps: dict[str, Any],
    *,
    supplied_caps: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = validate_adapter_snapshot(current_caps)
    _bind_snapshot_to_unit(current, unit)
    if supplied_caps is not None:
        supplied = validate_adapter_snapshot(supplied_caps)
        _bind_snapshot_to_unit(supplied, unit)
        compare_adapter_evidence(supplied, current)

    repos = sorted(set(unit.get("target_repos", [])))
    topology_key = "multi_target" if len(repos) > 1 else "single_target"
    support = current["topologies"][topology_key]

    base = {
        "schema": "l9.idea-execute.adapter-compatibility/v2",
        "unit_id": unit["id"],
        "adapter": unit["adapter"],
        "front_door": current["front_door"]["value"],
        "source_refs": current["source_refs"],
        "source_bindings": current["source_bindings"],
    }
    if support is True:
        return {
            **base,
            "status": "COMPATIBLE",
            "compatible": True,
            "reason": f"validated current snapshot declares {topology_key} support",
        }
    if support is False:
        return {
            **base,
            "status": "EXECUTOR_CAPABILITY_GAP",
            "compatible": False,
            "reason": f"validated current snapshot explicitly denies {topology_key} support",
        }
    return {
        **base,
        "status": "ADAPTER_CAPABILITY_UNKNOWN",
        "compatible": None,
        "reason": f"validated current snapshot leaves {topology_key} support unknown",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("graph")
    parser.add_argument("capabilities", help="freshly discovered current adapter snapshot")
    parser.add_argument("--supplied", help="optional supplied/reused snapshot to reconcile")
    parser.add_argument("--envelope", required=True)
    parser.add_argument("--unit", dest="unit_id")
    args = parser.parse_args()
    try:
        graph = validate_graph(load_data(args.graph), load_data(args.envelope))
        current_caps = validate_adapter_snapshot(load_data(args.capabilities))
        supplied_caps = load_data(args.supplied) if args.supplied else None
        candidates = [u for u in graph["units"] if args.unit_id is None or u["id"] == args.unit_id]
        if args.unit_id and not candidates:
            raise ContractError(f"unit not found: {args.unit_id}")
        if not candidates:
            raise ContractError("graph has no execution units")
        if len(candidates) > 1 and args.unit_id is None:
            matching = [
                u
                for u in candidates
                if u.get("id") == current_caps.get("unit_id")
                and u.get("adapter") == current_caps.get("adapter")
            ]
            if len(matching) != 1:
                raise ContractError(
                    "specify --unit when capability snapshot does not select exactly one unit"
                )
            candidates = matching
        result = check_unit(candidates[0], current_caps, supplied_caps=supplied_caps)
        print(dump_yaml(result), end="")
        if result["status"] == "COMPATIBLE":
            return 0
        if result["status"] == "EXECUTOR_CAPABILITY_GAP":
            return 3
        return 4
    except ContractError as exc:
        print(f"ADAPTER_CAPABILITY_CHECK: FAIL\n- {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
