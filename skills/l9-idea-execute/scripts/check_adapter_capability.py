#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from typing import Any

from _common import ContractError, dump_yaml, load_data, nonempty_string
from validate_graph import validate_graph

CAP_SCHEMA = "l9.idea-execute.adapter-capabilities/v1"


def check_unit(unit: dict[str, Any], caps: dict[str, Any]) -> dict[str, Any]:
    if caps.get("schema") != CAP_SCHEMA:
        raise ContractError(f"capability snapshot schema must equal {CAP_SCHEMA}")
    if caps.get("adapter") != unit.get("adapter"):
        raise ContractError("capability snapshot adapter does not match execution unit adapter")
    if not isinstance(caps.get("source_refs"), list) or not caps["source_refs"]:
        raise ContractError("capability snapshot must include source_refs")
    front = caps.get("front_door")
    if not isinstance(front, dict) or not nonempty_string(front.get("value")):
        raise ContractError("capability snapshot must include front_door.value")

    repos = sorted(set(unit.get("target_repos", [])))
    topo = caps.get("topologies", {})
    if not isinstance(topo, dict):
        raise ContractError("capability snapshot topologies must be a mapping")

    reason = None
    if len(repos) > 1 and topo.get("multi_target") is not True:
        reason = f"adapter {caps['adapter']} cannot represent {len(repos)} target repositories"
    elif len(repos) <= 1 and repos and topo.get("single_target") is not True:
        reason = f"adapter {caps['adapter']} does not declare single_target support"

    if reason:
        return {
            "schema": "l9.idea-execute.adapter-compatibility/v1",
            "unit_id": unit["id"],
            "adapter": unit["adapter"],
            "status": "EXECUTOR_CAPABILITY_GAP",
            "compatible": False,
            "reason": reason,
            "front_door": front["value"],
            "source_refs": caps["source_refs"],
        }
    return {
        "schema": "l9.idea-execute.adapter-compatibility/v1",
        "unit_id": unit["id"],
        "adapter": unit["adapter"],
        "status": "COMPATIBLE",
        "compatible": True,
        "reason": "requested target topology is supported by the discovered adapter snapshot",
        "front_door": front["value"],
        "source_refs": caps["source_refs"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("graph")
    parser.add_argument("capabilities")
    parser.add_argument("--unit", dest="unit_id")
    args = parser.parse_args()
    try:
        graph = validate_graph(load_data(args.graph))
        caps = load_data(args.capabilities)
        if not isinstance(caps, dict):
            raise ContractError("capability snapshot must be a mapping")
        candidates = [u for u in graph["units"] if args.unit_id is None or u["id"] == args.unit_id]
        if args.unit_id and not candidates:
            raise ContractError(f"unit not found: {args.unit_id}")
        if not candidates:
            raise ContractError("graph has no execution units")
        if len(candidates) > 1 and args.unit_id is None:
            matching = [u for u in candidates if u.get("adapter") == caps.get("adapter")]
            if len(matching) != 1:
                raise ContractError("specify --unit when capability snapshot does not select exactly one unit")
            candidates = matching
        result = check_unit(candidates[0], caps)
        print(dump_yaml(result), end="")
        return 0 if result["compatible"] else 3
    except ContractError as exc:
        print(f"ADAPTER_CAPABILITY_CHECK: FAIL\n- {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
