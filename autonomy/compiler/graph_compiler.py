from __future__ import annotations

import argparse
import heapq
from collections.abc import Iterable, Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

from autonomy.errors import GraphCompilationError
from autonomy.io import load_json, sha256_json, write_json
from autonomy.models import (
    Action,
    CampaignAuthorization,
    DeploymentManifest,
)


class CompiledGraph:
    def __init__(
        self,
        *,
        graph_id: str,
        campaign_id: str,
        actions: list[Action],
        topological_order: list[str],
        reverse_dependencies: Mapping[str, list[str]],
        critical_depth: Mapping[str, int],
        source_hashes: Mapping[str, str],
    ) -> None:
        self.graph_id = graph_id
        self.campaign_id = campaign_id
        self.actions = actions
        self.topological_order = topological_order
        self.reverse_dependencies = dict(reverse_dependencies)
        self.critical_depth = dict(critical_depth)
        self.source_hashes = dict(source_hashes)

    def to_dict(self) -> dict[str, Any]:
        actions_payload: list[dict[str, Any]] = []
        for action in self.actions:
            item = asdict(action)
            item["role"] = action.role.value
            item["kind"] = action.kind.value
            # asdict keeps tuples; emit JSON-compatible lists for re-parse.
            item["depends_on"] = list(action.depends_on)
            item["independent_from"] = list(action.independent_from)
            item["claims"] = [
                {
                    "key": claim.key,
                    "mode": claim.mode,
                    "exclusive": claim.exclusive,
                }
                for claim in action.claims
            ]
            item["completion"] = {
                "artifact_kind": action.completion.artifact_kind,
                "required_fields": list(action.completion.required_fields),
                "require_base_sha_match": action.completion.require_base_sha_match,
                "require_empty_blockers": action.completion.require_empty_blockers,
            }
            item["metadata"] = dict(action.metadata)
            actions_payload.append(item)
        payload = {
            "schema_version": "1.0.0",
            "graph_id": self.graph_id,
            "campaign_id": self.campaign_id,
            "actions": actions_payload,
            "topological_order": list(self.topological_order),
            "reverse_dependencies": {
                key: list(value) for key, value in self.reverse_dependencies.items()
            },
            "critical_depth": dict(self.critical_depth),
            "source_hashes": dict(self.source_hashes),
        }
        payload["graph_hash"] = sha256_json(payload)
        return payload


def compile_graph(
    campaign: CampaignAuthorization,
    deployment: DeploymentManifest,
    action_payload: Mapping[str, Any],
) -> CompiledGraph:
    if campaign.campaign_id != deployment.campaign_id:
        raise GraphCompilationError("Campaign and deployment manifest campaign IDs differ")
    raw_actions = action_payload.get("actions")
    if not isinstance(raw_actions, list) or not raw_actions:
        raise GraphCompilationError("Action graph requires a non-empty actions list")
    actions = [Action.from_dict(item) for item in raw_actions]
    action_by_id = _index_actions(actions)
    _validate_dependencies(action_by_id)
    _validate_conditional_references(action_by_id)
    _validate_independence_references(action_by_id)
    topological_order = _topological_sort(action_by_id)
    reverse_dependencies = _reverse_dependencies(action_by_id)
    critical_depth = _critical_depth(
        action_by_id,
        topological_order,
        reverse_dependencies,
    )
    graph_seed = {
        "campaign_id": campaign.campaign_id,
        "deployment_id": deployment.deployment_id,
        "actions": [
            {
                "id": action.id,
                "role": action.role.value,
                "kind": action.kind.value,
                "depends_on": list(action.depends_on),
                "mutation": action.mutation,
                "resource_class": action.resource_class,
            }
            for action in actions
        ],
    }
    graph_id = f"graph-{campaign.campaign_id}-{sha256_json(graph_seed)[:12]}"
    if deployment.graph_id not in {"AUTO", graph_id}:
        raise GraphCompilationError(
            "Deployment graph_id does not match the compiled graph: "
            f"declared={deployment.graph_id}, compiled={graph_id}"
        )
    return CompiledGraph(
        graph_id=graph_id,
        campaign_id=campaign.campaign_id,
        actions=actions,
        topological_order=topological_order,
        reverse_dependencies=reverse_dependencies,
        critical_depth=critical_depth,
        source_hashes={
            "campaign": sha256_json(asdict(campaign)),
            "deployment": sha256_json(
                {
                    "schema_version": deployment.schema_version,
                    "deployment_id": deployment.deployment_id,
                    "campaign_id": deployment.campaign_id,
                    "graph_id": deployment.graph_id,
                    "required_roles": {
                        role.value: dict(config)
                        for role, config in deployment.required_roles.items()
                    },
                    "fail_closed": dict(deployment.fail_closed),
                }
            ),
            "actions": sha256_json(action_payload),
        },
    )


def _index_actions(actions: Iterable[Action]) -> dict[str, Action]:
    result: dict[str, Action] = {}
    for action in actions:
        if action.id in result:
            raise GraphCompilationError(f"Duplicate action ID: {action.id}")
        result[action.id] = action
    return result


def _validate_dependencies(actions: Mapping[str, Action]) -> None:
    for action in actions.values():
        for dependency in action.depends_on:
            if dependency == action.id:
                raise GraphCompilationError(f"Action {action.id!r} depends on itself")
            if dependency not in actions:
                raise GraphCompilationError(
                    f"Action {action.id!r} depends on missing action {dependency!r}"
                )


def _validate_conditional_references(
    actions: Mapping[str, Action],
) -> None:
    for action in actions.values():
        if action.conditional_on is not None and action.conditional_on not in actions:
            raise GraphCompilationError(
                f"Action {action.id!r} has missing conditional dependency {action.conditional_on!r}"
            )


def _validate_independence_references(
    actions: Mapping[str, Action],
) -> None:
    for action in actions.values():
        for source in action.independent_from:
            if source not in actions:
                raise GraphCompilationError(
                    f"Action {action.id!r} declares independence from missing action {source!r}"
                )


def _topological_sort(actions: Mapping[str, Action]) -> list[str]:
    indegree = {action_id: len(action.depends_on) for action_id, action in actions.items()}
    dependents = _reverse_dependencies(actions)
    ready = [action_id for action_id, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    result: list[str] = []
    while ready:
        action_id = heapq.heappop(ready)
        result.append(action_id)
        for dependent in sorted(dependents[action_id]):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(ready, dependent)
    if len(result) != len(actions):
        remaining = sorted(action_id for action_id, degree in indegree.items() if degree > 0)
        raise GraphCompilationError(
            "Action graph contains a dependency cycle involving: " + ", ".join(remaining)
        )
    return result


def _reverse_dependencies(
    actions: Mapping[str, Action],
) -> dict[str, list[str]]:
    result = {action_id: [] for action_id in actions}
    for action in actions.values():
        for dependency in action.depends_on:
            result[dependency].append(action.id)
    for action_id in result:
        result[action_id].sort()
    return result


def _critical_depth(
    actions: Mapping[str, Action],
    topological_order: list[str],
    reverse_dependencies: Mapping[str, list[str]],
) -> dict[str, int]:
    depth = {action_id: 1 for action_id in actions}
    for action_id in reversed(topological_order):
        dependents = reverse_dependencies[action_id]
        if dependents:
            depth[action_id] = 1 + max(depth[item] for item in dependents)
    return depth


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile an enforceable L9 autonomy action graph.")
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--deployment", required=True)
    parser.add_argument("--actions", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    campaign = CampaignAuthorization.from_dict(load_json(args.campaign))
    deployment = DeploymentManifest.from_dict(load_json(args.deployment))
    actions = load_json(args.actions)
    compiled = compile_graph(campaign, deployment, actions)
    write_json(args.output, compiled.to_dict())
    print(f"compiled graph: {compiled.graph_id}")
    print(f"actions: {len(compiled.actions)}")
    print(f"output: {Path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
