#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from typing import Any

from _common import ContractError, load_data, nonempty_string, require_mapping

SCHEMA = "l9.idea-execute.adapter-capabilities/v2"


def _valid_digest(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    hex_part = value.removeprefix("sha256:")
    return len(hex_part) == 64 and all(ch in "0123456789abcdef" for ch in hex_part)


def validate_adapter_snapshot(data: Any) -> dict[str, Any]:
    root = require_mapping(data, "adapter capability snapshot")
    errors: list[str] = []

    if root.get("schema") != SCHEMA:
        errors.append(f"schema must equal {SCHEMA}")
    if not nonempty_string(root.get("unit_id")):
        errors.append("unit_id must be a non-empty string")
    if not nonempty_string(root.get("adapter")):
        errors.append("adapter must be a non-empty string")
    if not nonempty_string(root.get("observed_at")):
        errors.append("observed_at must be a non-empty string")

    source_refs = root.get("source_refs")
    if (
        not isinstance(source_refs, list)
        or not source_refs
        or not all(nonempty_string(x) for x in source_refs)
    ):
        errors.append("source_refs must be a non-empty string list")

    bindings = root.get("source_bindings")
    if not isinstance(bindings, list) or not bindings:
        errors.append("source_bindings must be a non-empty list")
        bindings = []
    seen_bindings: set[tuple[str, str]] = set()
    for idx, binding in enumerate(bindings):
        label = f"source_bindings[{idx}]"
        if not isinstance(binding, dict):
            errors.append(f"{label} must be a mapping")
            continue
        for key in ("repo", "revision", "path"):
            if not nonempty_string(binding.get(key)):
                errors.append(f"{label}.{key} must be a non-empty string")
        digest = binding.get("digest")
        if digest is not None and not _valid_digest(digest):
            errors.append(f"{label}.digest must be a lowercase sha256 digest when present")
        repo = binding.get("repo")
        path = binding.get("path")
        if nonempty_string(repo) and nonempty_string(path):
            key = (repo, path)
            if key in seen_bindings:
                errors.append(f"duplicate source binding for {repo}:{path}")
            seen_bindings.add(key)

    front = root.get("front_door")
    if not isinstance(front, dict):
        errors.append("front_door must be a mapping")
    else:
        if not nonempty_string(front.get("kind")):
            errors.append("front_door.kind must be a non-empty string")
        if not nonempty_string(front.get("value")):
            errors.append("front_door.value must be a non-empty string")

    accepted = root.get("accepted_inputs")
    if not isinstance(accepted, list) or not all(nonempty_string(x) for x in accepted):
        errors.append("accepted_inputs must be a string list")

    topologies = root.get("topologies")
    if not isinstance(topologies, dict):
        errors.append("topologies must be a mapping")
    else:
        for key in ("single_target", "multi_target"):
            if key not in topologies:
                errors.append(f"topologies.{key} must be declared")
            elif topologies[key] is not None and not isinstance(topologies[key], bool):
                errors.append(f"topologies.{key} must be true, false, or null")

    authority = root.get("authority")
    if not isinstance(authority, dict):
        errors.append("authority must be a mapping")
    else:
        for key, value in authority.items():
            if not nonempty_string(key) or not isinstance(value, bool):
                errors.append("authority keys must be non-empty strings with boolean values")

    if errors:
        raise ContractError("ADAPTER_SNAPSHOT_INVALID: " + "; ".join(errors))
    return root


def _normalized_bindings(value: dict[str, Any]) -> dict[tuple[str, str], tuple[str, str | None]]:
    return {
        (item["repo"], item["path"]): (item["revision"], item.get("digest"))
        for item in value["source_bindings"]
    }


def compare_adapter_evidence(snapshot: Any, current: Any) -> dict[str, Any]:
    supplied = validate_adapter_snapshot(snapshot)
    live = validate_adapter_snapshot(current)
    if supplied["unit_id"] != live["unit_id"] or supplied["adapter"] != live["adapter"]:
        raise ContractError("ADAPTER_CONTRACT_CONFLICT: adapter or unit binding changed")
    if _normalized_bindings(supplied) != _normalized_bindings(live):
        raise ContractError("ADAPTER_SNAPSHOT_STALE: source bindings changed")
    for field in ("front_door", "accepted_inputs", "topologies", "authority"):
        if supplied[field] != live[field]:
            raise ContractError(
                f"ADAPTER_CONTRACT_CONFLICT: {field} differs for identical source bindings"
            )
    return live


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot")
    parser.add_argument("--current")
    args = parser.parse_args()
    try:
        snapshot = validate_adapter_snapshot(load_data(args.snapshot))
        if args.current:
            compare_adapter_evidence(snapshot, load_data(args.current))
    except ContractError as exc:
        print(f"ADAPTER_SNAPSHOT: FAIL\n- {exc}", file=sys.stderr)
        return 1
    print("ADAPTER_SNAPSHOT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
