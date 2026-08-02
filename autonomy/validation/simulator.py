from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from typing import Any

from autonomy.io import load_json, write_json

SUCCESS = "COMPLETED"


class PipelineSimulator:
    def __init__(
        self,
        graph: Mapping[str, Any],
        resource_policy: Mapping[str, Any],
    ) -> None:
        self.graph = graph
        self.resource_policy = resource_policy
        self.actions = {action["id"]: action for action in graph["actions"]}

    def simulate(self) -> dict[str, Any]:
        status = {action_id: "PENDING" for action_id in self.actions}
        waves: list[dict[str, Any]] = []
        peak = Counter()
        human_stops: list[str] = []
        step = 0
        while True:
            pending = [
                action_id
                for action_id, action_status in status.items()
                if action_status == "PENDING"
            ]
            if not pending:
                break
            ready = [
                self.actions[action_id]
                for action_id in pending
                if self._dependencies_complete(self.actions[action_id], status)
            ]
            human_ready = [action for action in ready if action["kind"] == "human_gate"]
            for action in human_ready:
                status[action["id"]] = "HUMAN_STOP"
                human_stops.append(action["id"])
            runnable = [action for action in ready if action["kind"] != "human_gate"]
            selected = self._select_by_capacity(runnable)
            if not selected:
                break
            by_resource = Counter(action["resource_class"] for action in selected)
            for resource_class, count in by_resource.items():
                peak[resource_class] = max(peak[resource_class], count)
            waves.append(
                {
                    "step": step,
                    "actions": [
                        {
                            "action_id": action["id"],
                            "role": action["role"],
                            "resource_class": action["resource_class"],
                            "mutation": bool(action["mutation"]),
                        }
                        for action in selected
                    ],
                    "resource_usage": dict(sorted(by_resource.items())),
                }
            )
            for action in selected:
                status[action["id"]] = SUCCESS
            step += 1
        unreachable = sorted(
            action_id for action_id, action_status in status.items() if action_status == "PENDING"
        )
        lock_conflicts = self._static_lock_conflicts()
        warnings: list[str] = []
        if lock_conflicts:
            warnings.append("Exclusive resource claims serialize some actions.")
        if human_stops:
            warnings.append("Simulation stopped human-gated branches without auto-approving them.")
        return {
            "schema_version": "1.0.0",
            "graph_id": self.graph["graph_id"],
            "valid": not unreachable,
            "steps": len(waves),
            "waves": waves,
            "peak_resource_usage": dict(sorted(peak.items())),
            "human_stops": human_stops,
            "unreachable_actions": unreachable,
            "static_lock_conflicts": lock_conflicts,
            "warnings": warnings,
        }

    def _dependencies_complete(
        self,
        action: Mapping[str, Any],
        status: Mapping[str, str],
    ) -> bool:
        for dependency in action.get("depends_on", []):
            if status.get(dependency) != SUCCESS:
                return False
        conditional = action.get("conditional_on")
        if conditional and status.get(conditional) != SUCCESS:
            return False
        return True

    def _select_by_capacity(
        self,
        ready: list[Mapping[str, Any]],
    ) -> list[Mapping[str, Any]]:
        capacities = {
            resource: int(config["capacity"])
            for resource, config in self.resource_policy["classes"].items()
        }
        used = Counter()
        claimed_exclusive: set[str] = set()
        claimed_shared: Counter[str] = Counter()
        selected: list[Mapping[str, Any]] = []
        ordered = sorted(
            ready,
            key=lambda action: (
                -float(action.get("priority_weight", 1.0)),
                -int(self.graph.get("critical_depth", {}).get(action["id"], 1)),
                action["id"],
            ),
        )
        for action in ordered:
            resource_class = action["resource_class"]
            if used[resource_class] >= capacities.get(resource_class, 0):
                continue
            if self._claims_conflict(action, claimed_exclusive, claimed_shared):
                continue
            selected.append(action)
            used[resource_class] += 1
            for claim in action.get("claims", []):
                key = claim["key"]
                exclusive = bool(claim.get("exclusive", claim["mode"] == "write"))
                if exclusive:
                    claimed_exclusive.add(key)
                else:
                    claimed_shared[key] += 1
        return selected

    def _claims_conflict(
        self,
        action: Mapping[str, Any],
        claimed_exclusive: set[str],
        claimed_shared: Counter[str],
    ) -> bool:
        for claim in action.get("claims", []):
            key = claim["key"]
            exclusive = bool(claim.get("exclusive", claim["mode"] == "write"))
            if key in claimed_exclusive:
                return True
            if exclusive and claimed_shared[key] > 0:
                return True
        return False

    def _static_lock_conflicts(self) -> list[dict[str, Any]]:
        by_resource: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for action in self.actions.values():
            for claim in action.get("claims", []):
                if bool(claim.get("exclusive", claim["mode"] == "write")):
                    by_resource[claim["key"]].append(
                        {
                            "action_id": action["id"],
                            "role": action["role"],
                        }
                    )
        return [
            {"resource": resource, "actions": actions}
            for resource, actions in sorted(by_resource.items())
            if len(actions) > 1
        ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate an L9 compiled autonomy graph.")
    parser.add_argument("--graph", required=True)
    parser.add_argument(
        "--resource-policy",
        default="autonomy/policies/resource-classes.json",
    )
    parser.add_argument("--output")
    args = parser.parse_args()
    result = PipelineSimulator(
        load_json(args.graph),
        load_json(args.resource_policy),
    ).simulate()
    if args.output:
        write_json(args.output, result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
