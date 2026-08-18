"""Payload builders for wide (swarm-shaped) autonomy campaigns.

The W7 example graph is narrow by construction. Saturation behavior only shows
up on a graph that is genuinely wide, so these helpers generate one: a recon
fan-out, then a mutation fan-out whose write claims are disjoint by default and
overlapping on request.
"""

from __future__ import annotations

import copy
from typing import Any

from autonomy.policy_loader import load_example

CAMPAIGN_ID = "autonomy-swarm-test"
BASE_SHA = "abc1234"


def campaign_payload(**budget_overrides: int) -> dict[str, Any]:
    payload = copy.deepcopy(load_example("w7-campaign.json"))
    payload["campaign_id"] = CAMPAIGN_ID
    payload["base_state"]["commit_sha"] = BASE_SHA
    payload["budgets"].update(budget_overrides)
    return payload


def deployment_payload(**role_overrides: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(load_example("w7-deployment.json"))
    payload["campaign_id"] = CAMPAIGN_ID
    payload["deployment_id"] = "deploy-swarm-test"
    roles = payload["required_roles"]
    for role in roles.values():
        role["min"] = 0
    roles["coordinator"]["min"] = 1
    for role_name, override in role_overrides.items():
        roles[role_name].update(override)
    return payload


def _completion(kind: str) -> dict[str, Any]:
    return {
        "artifact_kind": kind,
        "required_fields": ["base_sha"],
        "require_base_sha_match": True,
    }


def actions_payload(
    *,
    recon: int = 0,
    mutations: int = 0,
    shared_mutation_key: bool = False,
) -> dict[str, Any]:
    """Build a coordinator -> recon* -> synthesis -> (mutate, verify)* graph.

    `shared_mutation_key` makes every mutation action claim the same key, which
    is the collision case: the claim registry must serialize those and only
    those.
    """

    actions: list[dict[str, Any]] = [
        {
            "id": "coordinate",
            "role": "coordinator",
            "kind": "work",
            "depends_on": [],
            "mutation": False,
            "resource_class": "repository_read",
            "claims": [],
            "completion": _completion("CampaignStatus"),
            "priority_weight": 10,
        }
    ]
    for index in range(recon):
        actions.append(
            {
                "id": f"recon-{index:03d}",
                "role": "recon",
                "kind": "work",
                "depends_on": ["coordinate"],
                "mutation": False,
                "resource_class": "repository_recon",
                "claims": [
                    {
                        "key": f"repo:module-{index:03d}",
                        "mode": "read",
                        "exclusive": False,
                    }
                ],
                "completion": _completion("ReconReport"),
                "priority_weight": 5,
            }
        )
    if mutations:
        actions.append(
            {
                "id": "synthesize",
                "role": "synthesis",
                "kind": "synthesis",
                "depends_on": ["coordinate"],
                "mutation": False,
                "resource_class": "synthesis",
                "claims": [],
                "completion": _completion("ExecutionBrief"),
                "priority_weight": 8,
            }
        )
        for index in range(mutations):
            claim_key = "repo:shared" if shared_mutation_key else f"repo:lane-{index:03d}"
            actions.append(
                {
                    "id": f"mutate-{index:03d}",
                    "role": "executor",
                    "kind": "work",
                    "depends_on": ["synthesize"],
                    "mutation": True,
                    "resource_class": "repository_mutation",
                    "claims": [
                        {
                            "key": claim_key,
                            "mode": "write",
                            "exclusive": True,
                        }
                    ],
                    "completion": _completion("ExecutionResult"),
                    "priority_weight": 7,
                }
            )
            actions.append(
                {
                    "id": f"verify-{index:03d}",
                    "role": "verifier",
                    "kind": "validation",
                    "depends_on": [f"mutate-{index:03d}"],
                    "mutation": False,
                    "resource_class": "verification",
                    "claims": [],
                    "completion": _completion("VerificationReport"),
                    "priority_weight": 6,
                }
            )
        actions.append(
            {
                "id": "review",
                "role": "reviewer",
                "kind": "validation",
                "depends_on": [f"verify-{index:03d}" for index in range(mutations)],
                "mutation": False,
                "resource_class": "review",
                "claims": [],
                "independent_from": [f"mutate-{index:03d}" for index in range(mutations)],
                "completion": _completion("ReviewVerdict"),
                "priority_weight": 4,
            }
        )
    return {"schema_version": "1.0.0", "actions": actions}
