#!/usr/bin/env python3
"""Deterministic fixture validator for l9-wire-into-repo core invariants."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

ALLOWED_ROLES = {
    "authoritative_owner",
    "source_registry",
    "generator",
    "generated_derivative",
    "adapter",
    "consumer",
    "documentation",
    "historical",
}


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    nodes_raw = data.get("nodes")
    edges_raw = data.get("edges")
    consumers_raw = data.get("intended_consumers")
    expected_ulp = data.get("expected_ulp")
    if not isinstance(nodes_raw, list) or not nodes_raw:
        return ["nodes must be a non-empty list"]
    if not isinstance(edges_raw, list):
        return ["edges must be a list"]
    if not isinstance(consumers_raw, list) or not consumers_raw:
        return ["intended_consumers must be a non-empty list"]

    roles: dict[str, str] = {}
    for node in nodes_raw:
        if not isinstance(node, dict):
            errors.append("node must be an object")
            continue
        node_id, role = node.get("id"), node.get("role")
        if not isinstance(node_id, str) or not node_id:
            errors.append("node id must be a non-empty string")
            continue
        if node_id in roles:
            errors.append(f"duplicate node id: {node_id}")
            continue
        if role not in ALLOWED_ROLES:
            errors.append(f"invalid role for {node_id}: {role!r}")
            continue
        roles[node_id] = role

    owners = sorted(node_id for node_id, role in roles.items() if role == "authoritative_owner")
    if len(owners) != 1:
        errors.append(f"expected exactly one authoritative owner, found {len(owners)}")
        return errors
    owner = owners[0]
    if expected_ulp != owner:
        errors.append(f"expected_ulp {expected_ulp!r} is not authoritative owner {owner!r}")

    graph: dict[str, list[str]] = defaultdict(list)
    incoming: dict[str, list[str]] = defaultdict(list)
    for edge in edges_raw:
        if (
            not isinstance(edge, list)
            or len(edge) != 2
            or not all(isinstance(x, str) for x in edge)
        ):
            errors.append(f"invalid edge: {edge!r}")
            continue
        source, target = edge
        if source not in roles or target not in roles:
            errors.append(f"edge references unknown node: {source!r} -> {target!r}")
            continue
        graph[source].append(target)
        incoming[target].append(source)

    for node_id, role in roles.items():
        if role == "generated_derivative":
            parents = incoming.get(node_id, [])
            if not parents:
                errors.append(f"generated derivative has no upstream source: {node_id}")
            elif all(
                roles[parent] in {"generated_derivative", "historical", "documentation"}
                for parent in parents
            ):
                errors.append(
                    f"generated derivative lacks authoritative propagation source: {node_id}"
                )

    reachable: set[str] = set()
    queue: deque[str] = deque([owner])
    while queue:
        current = queue.popleft()
        if current in reachable:
            continue
        reachable.add(current)
        queue.extend(graph.get(current, []))

    for consumer in consumers_raw:
        if not isinstance(consumer, str) or consumer not in roles:
            errors.append(f"unknown intended consumer: {consumer!r}")
            continue
        if roles[consumer] != "consumer":
            errors.append(f"intended consumer has non-consumer role: {consumer}")
        if consumer not in reachable:
            errors.append(f"intended consumer unreachable from authoritative owner: {consumer}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.fixture.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"fixture error: {exc}", file=sys.stderr)
        return 2
    if not isinstance(data, dict):
        print("fixture error: root must be an object", file=sys.stderr)
        return 2
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: authority and intended-consumer reachability proven")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
