#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from typing import Any

from _common import ContractError, dump_yaml, load_data
from validate_adapter_snapshot import validate_adapter_snapshot
from validate_graph import validate_graph


def check_unit(unit: dict[str, Any], caps: dict[str, Any]) -> dict[str, Any]:
    snapshot = validate_adapter_snapshot(caps)
    if snapshot["adapter"] != unit.get("adapter"):
        raise ContractError(
            "ADAPTER_CONTRACT_CONFLICT: capability snapshot adapter does not match execution unit"
        )

    repos = sorted(set(unit.get("target_repos", [])))
    topology_key = "multi_target" if len(repos) > 1 else "single_target"
    support = snapshot["topologies"][topology_key]

    base = {
        "schema": "l9.idea-execute.adapter-compatibility/v2",
        "unit_id": unit["id"],
        "adapter": unit["adapter"],
        "front_door": snapshot["front_door"]["value"],
        "source_refs": snapshot["source_refs"],
        "source_bindings": snapshot["source_bindings"],
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
        "reason": f"validated snapshot leaves {topology_key} support unknown",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("graph")
    parser.add_argument("capabilities")
    parser.add_argument("--envelope", required=True)
    parser.add_argument("--unit", dest="unit_id")
    args = parser.parse_args()
    try:
        graph = validate_graph(load_data(args.graph), load_data(args.envelope))
        caps = validate_adapter_snapshot(load_data(args.capabilities))
        candidates = [u for u in graph["units"] if args.unit_id is None or u["id"] == args.unit_id]
        if args.unit_id and not candidates:
            raise ContractError(f"unit not found: {args.unit_id}")
        if not candidates:
            raise ContractError("graph has no execution units")
        if len(candidates) > 1 and args.unit_id is None:
            matching = [u for u in candidates if u.get("adapter") == caps.get("adapter")]
            if len(matching) != 1:
                raise ContractError(
                    "specify --unit when capability snapshot does not select exactly one unit"
                )
            candidates = matching
        result = check_unit(candidates[0], caps)
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
