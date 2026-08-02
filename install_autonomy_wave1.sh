#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
mkdir -p \
  "$ROOT/autonomy/schemas" \
  "$ROOT/autonomy/policies" \
  "$ROOT/autonomy/compiler" \
  "$ROOT/autonomy/validation" \
  "$ROOT/autonomy/examples" \
  "$ROOT/autonomy/tests"

cat > "$ROOT/autonomy/README.md" <<'MD'
# L9 Enforceable Autonomy Control Plane

Wave 1 converts autonomy orchestration from IDE convention into validated,
machine-readable contracts.

## Properties enforced

- Campaigns require resolved base SHAs.
- Autonomous merge, admin merge, and force push are forbidden.
- Executors require synthesis inputs.
- Mutation roles require exclusive write claims.
- Read-only roles cannot request write claims.
- Reviewers must be independent from executors.
- Reviews must consume verifier outputs.
- Every action declares a typed completion artifact.
- Role cardinality is validated before execution.
- Action graphs must be acyclic and dependency-complete.

## Compile the W7 graph

Replace the example base SHA first:

```bash
python - <<'PY'
import json
from pathlib import Path
path = Path("autonomy/examples/w7-campaign.json")
data = json.loads(path.read_text())
data["base_state"]["commit_sha"] = "YOUR_RESOLVED_BASE_SHA"
path.write_text(json.dumps(data, indent=2) + "\n")
PY
```

Compile:

```bash
python -m autonomy.compiler.graph_compiler \
  --campaign autonomy/examples/w7-campaign.json \
  --deployment autonomy/examples/w7-deployment.json \
  --actions autonomy/examples/w7-actions.json \
  --output .l9/autonomy/w7-compiled-graph.json
```

Validate:

```bash
python -m autonomy.validation.graph_linter \
  --graph .l9/autonomy/w7-compiled-graph.json \
  --deployment autonomy/examples/w7-deployment.json
```

Run tests:

```bash
python -m unittest discover -s autonomy/tests -v
```

## Wave boundaries

Wave 1 only compiles and validates authority and topology.

It intentionally does not yet grant leases or mediate tools. Runtime mutation
must remain disabled until Wave 2 is installed and its capability gateway is
active.
MD

cat > "$ROOT/autonomy/__init__.py" <<'PY'
"""
L9 enforceable autonomy control plane.
Wave 1 provides:
- machine-readable campaign and deployment contracts
- action graph compilation
- readiness and topology validation
- role and pipeline policy loading
"""
__version__ = "1.0.0"
PY

cat > "$ROOT/autonomy/cli.py" <<'PY'
from __future__ import annotations

import argparse
import sys

from autonomy.compiler.graph_compiler import main as compile_main
from autonomy.validation.graph_linter import main as lint_main


def main() -> int:
    parser = argparse.ArgumentParser(
        description="L9 autonomy control-plane CLI."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "compile",
        help="Compile campaign, deployment, and action contracts.",
    )
    subparsers.add_parser(
        "lint",
        help="Validate a compiled graph against enforcement policies.",
    )
    args, remaining = parser.parse_known_args()
    original_argv = sys.argv
    try:
        sys.argv = [original_argv[0], *remaining]
        if args.command == "compile":
            return compile_main()
        if args.command == "lint":
            return lint_main()
    finally:
        sys.argv = original_argv
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
PY

cat > "$ROOT/autonomy/compiler/__init__.py" <<'PY'
"""Action graph compilation for the L9 autonomy control plane."""
PY

cat > "$ROOT/autonomy/compiler/graph_compiler.py" <<'PY'
from __future__ import annotations

import argparse
import heapq
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Mapping

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
        raise GraphCompilationError(
            "Campaign and deployment manifest campaign IDs differ"
        )
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
                f"Action {action.id!r} has missing conditional dependency "
                f"{action.conditional_on!r}"
            )


def _validate_independence_references(
    actions: Mapping[str, Action],
) -> None:
    for action in actions.values():
        for source in action.independent_from:
            if source not in actions:
                raise GraphCompilationError(
                    f"Action {action.id!r} declares independence from "
                    f"missing action {source!r}"
                )


def _topological_sort(actions: Mapping[str, Action]) -> list[str]:
    indegree = {
        action_id: len(action.depends_on) for action_id, action in actions.items()
    }
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
        remaining = sorted(
            action_id for action_id, degree in indegree.items() if degree > 0
        )
        raise GraphCompilationError(
            "Action graph contains a dependency cycle involving: "
            + ", ".join(remaining)
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
    parser = argparse.ArgumentParser(
        description="Compile an enforceable L9 autonomy action graph."
    )
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
PY

cat > "$ROOT/autonomy/errors.py" <<'PY'
from __future__ import annotations


class AutonomyError(Exception):
    """Base class for autonomy control-plane failures."""


class ContractError(AutonomyError):
    """Raised when a machine-readable contract is malformed."""


class GraphCompilationError(AutonomyError):
    """Raised when an action graph cannot be compiled safely."""


class GraphValidationError(AutonomyError):
    """Raised when a compiled action graph violates invariants."""


class PolicyViolation(AutonomyError):
    """Raised when an action violates a declared governance policy."""


class CompatibilityError(AutonomyError):
    """Raised when contract or adapter versions are incompatible."""
PY

cat > "$ROOT/autonomy/examples/w7-actions.json" <<'JSON'
{
  "schema_version": "1.0.0",
  "actions": [
    {
      "id": "campaign-coordinator",
      "role": "coordinator",
      "kind": "work",
      "depends_on": [],
      "mutation": false,
      "resource_class": "repository_read",
      "claims": [],
      "completion": {
        "artifact_kind": "CampaignStatus",
        "required_fields": [
          "campaign_id",
          "state"
        ],
        "require_base_sha_match": true
      },
      "priority_weight": 10
    },
    {
      "id": "context-compile-task046",
      "role": "context_compiler",
      "kind": "work",
      "depends_on": [
        "campaign-coordinator"
      ],
      "mutation": false,
      "resource_class": "repository_read",
      "claims": [
        {
          "key": "repo:odoo",
          "mode": "read",
          "exclusive": false
        }
      ],
      "completion": {
        "artifact_kind": "ContextPack",
        "required_fields": [
          "objective",
          "authority",
          "base_sha",
          "allowed_paths",
          "forbidden_paths",
          "acceptance_criteria"
        ],
        "require_base_sha_match": true
      },
      "priority_weight": 9
    },
    {
      "id": "ro-stack-inventory",
      "role": "recon",
      "kind": "work",
      "depends_on": [
        "context-compile-task046"
      ],
      "mutation": false,
      "resource_class": "repository_read",
      "claims": [
        {
          "key": "repo:stack-config",
          "mode": "read",
          "exclusive": false
        }
      ],
      "completion": {
        "artifact_kind": "ReconReport",
        "required_fields": [
          "status",
          "feeds",
          "evidence",
          "impl_checklist"
        ],
        "require_base_sha_match": true,
        "require_empty_blockers": false
      },
      "priority_weight": 8
    },
    {
      "id": "ro-m0-gap",
      "role": "recon",
      "kind": "work",
      "depends_on": [
        "context-compile-task046"
      ],
      "mutation": false,
      "resource_class": "repository_read",
      "claims": [
        {
          "key": "repo:odoo",
          "mode": "read",
          "exclusive": false
        }
      ],
      "completion": {
        "artifact_kind": "ReconReport",
        "required_fields": [
          "status",
          "feeds",
          "evidence",
          "impl_checklist"
        ],
        "require_base_sha_match": true,
        "require_empty_blockers": false
      },
      "priority_weight": 10
    },
    {
      "id": "ro-owner-schemas",
      "role": "recon",
      "kind": "work",
      "depends_on": [
        "context-compile-task046"
      ],
      "mutation": false,
      "resource_class": "repository_read",
      "claims": [
        {
          "key": "repo:owner-schemas",
          "mode": "read",
          "exclusive": false
        }
      ],
      "completion": {
        "artifact_kind": "ReconReport",
        "required_fields": [
          "status",
          "feeds",
          "evidence",
          "impl_checklist"
        ],
        "require_base_sha_match": true,
        "require_empty_blockers": false
      },
      "priority_weight": 9
    },
    {
      "id": "ro-gate-actions",
      "role": "recon",
      "kind": "work",
      "depends_on": [
        "context-compile-task046"
      ],
      "mutation": false,
      "resource_class": "repository_read",
      "claims": [
        {
          "key": "repo:gate-actions",
          "mode": "read",
          "exclusive": false
        }
      ],
      "completion": {
        "artifact_kind": "ReconReport",
        "required_fields": [
          "status",
          "feeds",
          "evidence",
          "impl_checklist"
        ],
        "require_base_sha_match": true,
        "require_empty_blockers": false
      },
      "priority_weight": 7
    },
    {
      "id": "synthesize-m0",
      "role": "synthesis",
      "kind": "synthesis",
      "depends_on": [
        "ro-stack-inventory",
        "ro-m0-gap",
        "ro-owner-schemas",
        "ro-gate-actions"
      ],
      "mutation": false,
      "resource_class": "repository_read",
      "claims": [],
      "completion": {
        "artifact_kind": "ExecutionBrief",
        "required_fields": [
          "task_id",
          "contract",
          "base_sha",
          "inputs",
          "resolved_findings",
          "conflicts",
          "ordered_edits",
          "parallelizable_test_work",
          "unresolved_blockers"
        ],
        "require_base_sha_match": true,
        "require_empty_blockers": true
      },
      "priority_weight": 10
    },
    {
      "id": "execute-m0",
      "role": "executor",
      "kind": "work",
      "depends_on": [
        "synthesize-m0"
      ],
      "mutation": true,
      "resource_class": "repository_mutation",
      "claims": [
        {
          "key": "repo:odoo",
          "mode": "write",
          "exclusive": true
        },
        {
          "key": "branch:feat/mothball-local-intelligence",
          "mode": "write",
          "exclusive": true
        }
      ],
      "completion": {
        "artifact_kind": "ExecutionResult",
        "required_fields": [
          "task_id",
          "base_sha",
          "result_sha",
          "changed_paths",
          "test_results",
          "scope_validation"
        ],
        "require_base_sha_match": true,
        "require_empty_blockers": true
      },
      "priority_weight": 10,
      "metadata": {
        "operations": [
          "edit_scoped",
          "run_tests",
          "commit_local"
        ]
      }
    },
    {
      "id": "verify-m0-scope",
      "role": "verifier",
      "kind": "validation",
      "depends_on": [
        "execute-m0"
      ],
      "mutation": false,
      "resource_class": "repository_read",
      "claims": [
        {
          "key": "repo:odoo",
          "mode": "read",
          "exclusive": false
        }
      ],
      "completion": {
        "artifact_kind": "VerificationReport",
        "required_fields": [
          "verification_type",
          "target_sha",
          "checks",
          "verdict",
          "evidence"
        ],
        "require_base_sha_match": false,
        "require_empty_blockers": true
      },
      "priority_weight": 9
    },
    {
      "id": "verify-m0-live",
      "role": "verifier",
      "kind": "validation",
      "depends_on": [
        "execute-m0",
        "ro-stack-inventory",
        "ro-gate-actions"
      ],
      "mutation": false,
      "resource_class": "live_runtime",
      "claims": [
        {
          "key": "docker:five-service",
          "mode": "read",
          "exclusive": false
        }
      ],
      "completion": {
        "artifact_kind": "VerificationReport",
        "required_fields": [
          "verification_type",
          "target_sha",
          "checks",
          "verdict",
          "evidence",
          "live_five_service_stack_exercised"
        ],
        "require_base_sha_match": false,
        "require_empty_blockers": true
      },
      "priority_weight": 10
    },
    {
      "id": "review-m0-independent",
      "role": "reviewer",
      "kind": "validation",
      "depends_on": [
        "verify-m0-scope",
        "verify-m0-live"
      ],
      "mutation": false,
      "resource_class": "repository_read",
      "claims": [
        {
          "key": "repo:odoo",
          "mode": "read",
          "exclusive": false
        }
      ],
      "completion": {
        "artifact_kind": "ReviewVerdict",
        "required_fields": [
          "authority_compliance",
          "scope_compliance",
          "invariant_preservation",
          "correctness",
          "security",
          "verdict",
          "findings"
        ],
        "require_base_sha_match": false,
        "require_empty_blockers": false
      },
      "independent_from": [
        "execute-m0"
      ],
      "priority_weight": 10
    },
    {
      "id": "poll-m0",
      "role": "poller",
      "kind": "poll",
      "depends_on": [
        "review-m0-independent"
      ],
      "mutation": false,
      "resource_class": "poll_remote",
      "claims": [
        {
          "key": "pr:M0",
          "mode": "observe",
          "exclusive": false
        }
      ],
      "completion": {
        "artifact_kind": "PollReport",
        "required_fields": [
          "pr_number",
          "head_sha",
          "checks",
          "review_threads",
          "terminal_state"
        ],
        "require_base_sha_match": false,
        "require_empty_blockers": false
      },
      "conditional_on": "review-m0-independent",
      "priority_weight": 8
    },
    {
      "id": "base-sha-sentinel",
      "role": "sentinel",
      "kind": "validation",
      "depends_on": [
        "campaign-coordinator"
      ],
      "mutation": false,
      "resource_class": "repository_read",
      "claims": [
        {
          "key": "repo:odoo",
          "mode": "read",
          "exclusive": false
        }
      ],
      "completion": {
        "artifact_kind": "SentinelReport",
        "required_fields": [
          "campaign_id",
          "expected_base_sha",
          "observed_base_sha",
          "scope_drift",
          "policy_conflicts",
          "decision"
        ],
        "require_base_sha_match": false,
        "require_empty_blockers": false
      },
      "priority_weight": 10
    },
    {
      "id": "evidence-writer",
      "role": "evidence_writer",
      "kind": "work",
      "depends_on": [
        "review-m0-independent",
        "base-sha-sentinel"
      ],
      "mutation": false,
      "resource_class": "controller_mutation",
      "claims": [],
      "completion": {
        "artifact_kind": "EvidenceReceipt",
        "required_fields": [
          "campaign_id",
          "graph_id",
          "event_type",
          "artifact_hash",
          "previous_receipt_hash",
          "receipt_hash"
        ],
        "require_base_sha_match": false,
        "require_empty_blockers": true
      },
      "priority_weight": 7
    }
  ]
}
JSON

cat > "$ROOT/autonomy/examples/w7-campaign.json" <<'JSON'
{
  "schema_version": "1.0.0",
  "campaign_id": "autonomy-w7-mothball-2026-08-02",
  "objective": "Execute W7 M0-M6 with enforceable subagent deployment and human-only merge.",
  "authority": {
    "issuer": "human",
    "issued_at": "2026-08-02T15:00:00Z",
    "expires_at": "2026-08-03T03:00:00Z"
  },
  "scope": {
    "repositories": [
      "Quantum-L9/Cursor-Governance",
      "Quantum-L9/Cursor-Governance"
    ],
    "allowed_paths": [
      "addons/plasticos_gate/**",
      "program/mothballing-cursor-contracts/**",
      "ledger/artifacts/wave7/**",
      "autonomy/**"
    ],
    "forbidden_paths": [
      "ops/secrets/**",
      ".env",
      "**/*.pem",
      "**/*.key"
    ],
    "allowed_operations": [
      "read",
      "search",
      "create_worktree",
      "edit_scoped",
      "run_tests",
      "commit_local",
      "push_non_force_declared_branch",
      "open_pull_request",
      "inspect_ci",
      "inspect_review"
    ],
    "forbidden_operations": [
      "merge",
      "merge_pull_request",
      "admin_merge",
      "force_push",
      "modify_secrets",
      "weaken_tests_for_green"
    ]
  },
  "budgets": {
    "max_files_changed": 80,
    "max_lines_changed": 6000,
    "max_mutation_agents": 1,
    "max_read_agents": 4,
    "max_poll_agents": 3,
    "max_runtime_minutes": 720,
    "max_tool_failures": 8
  },
  "validation": {
    "required_checks": [
      "unit_tests",
      "schema_validation",
      "governance_invariants",
      "scope_lock",
      "live_integration_proof"
    ],
    "independent_review_required": true,
    "human_merge_required": true
  },
  "base_state": {
    "repository": "Quantum-L9/Cursor-Governance",
    "branch": "main",
    "commit_sha": "0000000"
  },
  "revocation": {
    "kill_switch_file": ".l9/autonomy/revoke",
    "revoke_on_scope_drift": true,
    "revoke_on_policy_conflict": true,
    "revoke_on_base_sha_drift": true
  }
}
JSON

cat > "$ROOT/autonomy/examples/w7-deployment.json" <<'JSON'
{
  "schema_version": "1.0.0",
  "deployment_id": "deploy-w7-task046-v1",
  "campaign_id": "autonomy-w7-mothball-2026-08-02",
  "graph_id": "AUTO",
  "required_roles": {
    "coordinator": {
      "min": 1,
      "max": 1,
      "mutation": false
    },
    "recon": {
      "min": 4,
      "max": 8,
      "mutation": false
    },
    "synthesis": {
      "min": 1,
      "max": 4,
      "mutation": false
    },
    "executor": {
      "min": 1,
      "max": 1,
      "mutation": true
    },
    "verifier": {
      "min": 2,
      "max": 8,
      "mutation": false
    },
    "reviewer": {
      "min": 1,
      "max": 4,
      "mutation": false,
      "independent_from": [
        "executor"
      ]
    },
    "poller": {
      "min": 0,
      "max": 3,
      "mutation": false,
      "conditional_on": "pr_open"
    },
    "context_compiler": {
      "min": 1,
      "max": 1,
      "mutation": false
    },
    "sentinel": {
      "min": 1,
      "max": 1,
      "mutation": false
    },
    "evidence_writer": {
      "min": 1,
      "max": 1,
      "mutation": false
    }
  },
  "fail_closed": {
    "missing_required_agent": true,
    "invalid_agent_output": true,
    "executor_without_synthesis": true,
    "self_review": true,
    "unverified_completion": true
  }
}
JSON

cat > "$ROOT/autonomy/io.py" <<'PY'
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> Any:
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"JSON file does not exist: {source}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {source}: line {exc.lineno}, column {exc.colno}: "
            f"{exc.msg}"
        ) from exc


def write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(target)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
PY

cat > "$ROOT/autonomy/models.py" <<'PY'
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

from autonomy.errors import ContractError


class Role(str, Enum):
    COORDINATOR = "coordinator"
    RECON = "recon"
    SYNTHESIS = "synthesis"
    EXECUTOR = "executor"
    VERIFIER = "verifier"
    REVIEWER = "reviewer"
    POLLER = "poller"
    FAILURE_CLASSIFIER = "failure_classifier"
    REMEDIATOR = "remediator"
    CONTEXT_COMPILER = "context_compiler"
    SENTINEL = "sentinel"
    EVIDENCE_WRITER = "evidence_writer"


class ActionKind(str, Enum):
    WORK = "work"
    POLL = "poll"
    HUMAN_GATE = "human_gate"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"


class CampaignState(str, Enum):
    DRAFT = "DRAFT"
    DIAGNOSED = "DIAGNOSED"
    AUTHORIZED = "AUTHORIZED"
    PLANNED = "PLANNED"
    LOCKED = "LOCKED"
    EXECUTING = "EXECUTING"
    VALIDATING = "VALIDATING"
    INDEPENDENT_REVIEW = "INDEPENDENT_REVIEW"
    READY_FOR_HUMAN = "READY_FOR_HUMAN"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class ResourceClaim:
    key: str
    mode: str
    exclusive: bool = False

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResourceClaim":
        key = require_nonempty_string(value, "key")
        mode = require_nonempty_string(value, "mode")
        if mode not in {"read", "write", "observe"}:
            raise ContractError(
                f"Unsupported resource claim mode {mode!r} for {key!r}"
            )
        exclusive = bool(value.get("exclusive", mode == "write"))
        if mode == "write" and not exclusive:
            raise ContractError(f"Write claim {key!r} must be exclusive")
        return cls(key=key, mode=mode, exclusive=exclusive)


@dataclass(frozen=True)
class CompletionPredicate:
    artifact_kind: str
    required_fields: tuple[str, ...] = ()
    require_base_sha_match: bool = True
    require_empty_blockers: bool = False

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CompletionPredicate":
        artifact_kind = require_nonempty_string(value, "artifact_kind")
        required_fields = tuple(
            require_string_list(value.get("required_fields", []), "required_fields")
        )
        return cls(
            artifact_kind=artifact_kind,
            required_fields=required_fields,
            require_base_sha_match=bool(value.get("require_base_sha_match", True)),
            require_empty_blockers=bool(value.get("require_empty_blockers", False)),
        )


@dataclass(frozen=True)
class Action:
    id: str
    role: Role
    kind: ActionKind
    depends_on: tuple[str, ...]
    mutation: bool
    resource_class: str
    claims: tuple[ResourceClaim, ...]
    completion: CompletionPredicate
    conditional_on: str | None = None
    independent_from: tuple[str, ...] = ()
    priority_weight: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Action":
        action_id = require_nonempty_string(value, "id")
        try:
            role = Role(require_nonempty_string(value, "role"))
        except ValueError as exc:
            raise ContractError(
                f"Action {action_id!r} has unsupported role: {value.get('role')!r}"
            ) from exc
        try:
            kind = ActionKind(value.get("kind", "work"))
        except ValueError as exc:
            raise ContractError(
                f"Action {action_id!r} has unsupported kind: {value.get('kind')!r}"
            ) from exc
        depends_on = tuple(require_string_list(value.get("depends_on", []), "depends_on"))
        claims_data = value.get("claims", [])
        if not isinstance(claims_data, list):
            raise ContractError(f"Action {action_id!r} field 'claims' must be a list")
        claims = tuple(ResourceClaim.from_dict(item) for item in claims_data)
        completion_data = value.get("completion")
        if not isinstance(completion_data, Mapping):
            raise ContractError(f"Action {action_id!r} requires a completion object")
        independent_from = tuple(
            require_string_list(
                value.get("independent_from", []),
                "independent_from",
            )
        )
        priority_weight = value.get("priority_weight", 1.0)
        if not isinstance(priority_weight, (int, float)) or priority_weight <= 0:
            raise ContractError(f"Action {action_id!r} priority_weight must be positive")
        metadata = value.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ContractError(f"Action {action_id!r} metadata must be an object")
        return cls(
            id=action_id,
            role=role,
            kind=kind,
            depends_on=depends_on,
            mutation=bool(value.get("mutation", False)),
            resource_class=require_nonempty_string(value, "resource_class"),
            claims=claims,
            completion=CompletionPredicate.from_dict(completion_data),
            conditional_on=optional_nonempty_string(
                value.get("conditional_on"),
                "conditional_on",
            ),
            independent_from=independent_from,
            priority_weight=float(priority_weight),
            metadata=dict(metadata),
        )


@dataclass(frozen=True)
class CampaignAuthorization:
    schema_version: str
    campaign_id: str
    objective: str
    authority: Mapping[str, Any]
    scope: Mapping[str, Any]
    budgets: Mapping[str, Any]
    validation: Mapping[str, Any]
    base_state: Mapping[str, Any]
    revocation: Mapping[str, Any]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CampaignAuthorization":
        required_objects = (
            "authority",
            "scope",
            "budgets",
            "validation",
            "base_state",
            "revocation",
        )
        for field_name in required_objects:
            if not isinstance(value.get(field_name), Mapping):
                raise ContractError(f"Campaign field {field_name!r} must be an object")
        campaign = cls(
            schema_version=require_nonempty_string(value, "schema_version"),
            campaign_id=require_nonempty_string(value, "campaign_id"),
            objective=require_nonempty_string(value, "objective"),
            authority=dict(value["authority"]),
            scope=dict(value["scope"]),
            budgets=dict(value["budgets"]),
            validation=dict(value["validation"]),
            base_state=dict(value["base_state"]),
            revocation=dict(value["revocation"]),
        )
        campaign.validate_semantics()
        return campaign

    def validate_semantics(self) -> None:
        allowed_operations = set(
            require_string_list(
                self.scope.get("allowed_operations", []),
                "scope.allowed_operations",
            )
        )
        forbidden_operations = set(
            require_string_list(
                self.scope.get("forbidden_operations", []),
                "scope.forbidden_operations",
            )
        )
        overlap = allowed_operations & forbidden_operations
        if overlap:
            raise ContractError(
                "Campaign operations cannot be both allowed and forbidden: "
                + ", ".join(sorted(overlap))
            )
        forbidden_merge_operations = {
            "merge",
            "merge_pull_request",
            "admin_merge",
            "force_push",
        }
        unsafe = allowed_operations & forbidden_merge_operations
        if unsafe:
            raise ContractError(
                "Autonomy campaign grants forbidden high-risk operations: "
                + ", ".join(sorted(unsafe))
            )
        if self.validation.get("independent_review_required") is not True:
            raise ContractError("Campaign must require independent review")
        base_sha = self.base_state.get("commit_sha")
        if not isinstance(base_sha, str) or not base_sha.strip():
            raise ContractError(
                "Campaign base_state.commit_sha must be resolved before execution"
            )
        max_mutation = self.budgets.get("max_mutation_agents")
        if not isinstance(max_mutation, int) or max_mutation < 1:
            raise ContractError("budgets.max_mutation_agents must be a positive integer")


@dataclass(frozen=True)
class DeploymentManifest:
    schema_version: str
    deployment_id: str
    campaign_id: str
    graph_id: str
    required_roles: Mapping[Role, Mapping[str, Any]]
    fail_closed: Mapping[str, bool]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DeploymentManifest":
        roles_raw = value.get("required_roles")
        if not isinstance(roles_raw, Mapping):
            raise ContractError("Deployment required_roles must be an object")
        roles: dict[Role, Mapping[str, Any]] = {}
        for role_name, role_config in roles_raw.items():
            try:
                role = Role(role_name)
            except ValueError as exc:
                raise ContractError(f"Unsupported deployment role: {role_name!r}") from exc
            if not isinstance(role_config, Mapping):
                raise ContractError(
                    f"Role configuration for {role_name!r} must be an object"
                )
            minimum = role_config.get("min", 0)
            maximum = role_config.get("max", 0)
            if not isinstance(minimum, int) or minimum < 0:
                raise ContractError(
                    f"Role {role_name!r} min must be a non-negative integer"
                )
            if not isinstance(maximum, int) or maximum < minimum:
                raise ContractError(f"Role {role_name!r} max must be >= min")
            roles[role] = dict(role_config)
        fail_closed_raw = value.get("fail_closed")
        if not isinstance(fail_closed_raw, Mapping):
            raise ContractError("Deployment fail_closed must be an object")
        fail_closed = {
            str(name): bool(enabled) for name, enabled in fail_closed_raw.items()
        }
        required_fail_closed = {
            "missing_required_agent",
            "invalid_agent_output",
            "executor_without_synthesis",
            "self_review",
            "unverified_completion",
        }
        disabled = {
            name for name in required_fail_closed if fail_closed.get(name) is not True
        }
        if disabled:
            raise ContractError(
                "Mandatory fail-closed controls are missing or disabled: "
                + ", ".join(sorted(disabled))
            )
        return cls(
            schema_version=require_nonempty_string(value, "schema_version"),
            deployment_id=require_nonempty_string(value, "deployment_id"),
            campaign_id=require_nonempty_string(value, "campaign_id"),
            graph_id=require_nonempty_string(value, "graph_id"),
            required_roles=roles,
            fail_closed=fail_closed,
        )


def require_nonempty_string(
    value: Mapping[str, Any],
    field_name: str,
) -> str:
    raw = value.get(field_name)
    if not isinstance(raw, str) or not raw.strip():
        raise ContractError(f"Field {field_name!r} must be a non-empty string")
    return raw.strip()


def optional_nonempty_string(
    raw: Any,
    field_name: str,
) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise ContractError(f"Field {field_name!r} must be null or a non-empty string")
    return raw.strip()


def require_string_list(raw: Any, field_name: str) -> list[str]:
    if not isinstance(raw, (list, tuple)):
        raise ContractError(f"Field {field_name!r} must be a list")
    result: list[str] = []
    for index, item in enumerate(raw):
        if not isinstance(item, str) or not item.strip():
            raise ContractError(
                f"Field {field_name!r}[{index}] must be a non-empty string"
            )
        result.append(item.strip())
    if len(result) != len(set(result)):
        raise ContractError(f"Field {field_name!r} contains duplicate values")
    return result


def count_roles(actions: Iterable[Action]) -> dict[Role, int]:
    result = {role: 0 for role in Role}
    for action in actions:
        result[action.role] += 1
    return result
PY

cat > "$ROOT/autonomy/policies/pipeline-invariants.json" <<'JSON'
{
  "schema_version": "1.0.0",
  "invariants": [
    {
      "id": "PIPE-001",
      "description": "No executor may start without a valid execution brief.",
      "severity": "blocking",
      "continuous": true
    },
    {
      "id": "PIPE-002",
      "description": "No mutation may occur without an active scoped write lease.",
      "severity": "blocking",
      "continuous": true
    },
    {
      "id": "PIPE-003",
      "description": "No action may consume stale or invalidated input artifacts.",
      "severity": "blocking",
      "continuous": true
    },
    {
      "id": "PIPE-004",
      "description": "No executor may review or approve its own output.",
      "severity": "blocking",
      "continuous": true
    },
    {
      "id": "PIPE-005",
      "description": "No result is merge-eligible without all required verifiers.",
      "severity": "blocking",
      "continuous": true
    },
    {
      "id": "PIPE-006",
      "description": "No action may exceed its declared path or operation scope.",
      "severity": "blocking",
      "continuous": true
    },
    {
      "id": "PIPE-007",
      "description": "No remediation mutation may start without a failure classification.",
      "severity": "blocking",
      "continuous": true
    },
    {
      "id": "PIPE-008",
      "description": "No human gate, human merge, or A4 stop may be bypassed.",
      "severity": "blocking",
      "continuous": true
    },
    {
      "id": "PIPE-009",
      "description": "No action is complete without a valid typed artifact and receipt.",
      "severity": "blocking",
      "continuous": true
    },
    {
      "id": "PIPE-010",
      "description": "No campaign may execute with a failed IDE adapter conformance check.",
      "severity": "blocking",
      "continuous": true
    }
  ]
}
JSON

cat > "$ROOT/autonomy/policies/resource-classes.json" <<'JSON'
{
  "schema_version": "1.0.0",
  "classes": {
    "repository_read": {
      "capacity": 4,
      "mutation": false,
      "preemptible": true
    },
    "repository_mutation": {
      "capacity": 1,
      "mutation": true,
      "preemptible": false
    },
    "controller_mutation": {
      "capacity": 1,
      "mutation": true,
      "preemptible": false
    },
    "live_runtime": {
      "capacity": 2,
      "mutation": false,
      "preemptible": false
    },
    "poll_remote": {
      "capacity": 3,
      "mutation": false,
      "preemptible": true
    },
    "human_gate": {
      "capacity": 1,
      "mutation": false,
      "preemptible": false
    }
  }
}
JSON

cat > "$ROOT/autonomy/policies/role-capabilities.json" <<'JSON'
{
  "schema_version": "1.0.0",
  "roles": {
    "coordinator": {
      "mutation_allowed": false,
      "capabilities": [
        "campaign.inspect",
        "graph.inspect",
        "scheduler.request",
        "status.inspect"
      ]
    },
    "recon": {
      "mutation_allowed": false,
      "capabilities": [
        "repository.read",
        "repository.search",
        "graphiti.read",
        "artifact.write_recon_report"
      ]
    },
    "synthesis": {
      "mutation_allowed": false,
      "capabilities": [
        "repository.read",
        "artifact.read_recon_report",
        "artifact.write_execution_brief",
        "graphiti.read"
      ]
    },
    "executor": {
      "mutation_allowed": true,
      "capabilities": [
        "repository.read",
        "repository.write_scoped",
        "test.run",
        "git.diff",
        "git.commit_local",
        "artifact.write_execution_result"
      ]
    },
    "verifier": {
      "mutation_allowed": false,
      "capabilities": [
        "repository.read",
        "diff.inspect",
        "test.run",
        "runtime.probe",
        "evidence.inspect",
        "artifact.write_verification_report"
      ]
    },
    "reviewer": {
      "mutation_allowed": false,
      "capabilities": [
        "repository.read",
        "diff.inspect",
        "test.inspect",
        "evidence.inspect",
        "receipt.inspect",
        "artifact.write_review_verdict"
      ]
    },
    "poller": {
      "mutation_allowed": false,
      "capabilities": [
        "pr.inspect",
        "ci.inspect",
        "review.inspect",
        "artifact.write_poll_report"
      ]
    },
    "failure_classifier": {
      "mutation_allowed": false,
      "capabilities": [
        "repository.read",
        "ci.inspect",
        "test.inspect",
        "diff.inspect",
        "artifact.write_remediation_brief"
      ]
    },
    "remediator": {
      "mutation_allowed": true,
      "capabilities": [
        "repository.read",
        "repository.write_scoped",
        "test.run",
        "git.diff",
        "git.commit_local",
        "git.push_non_force_declared_branch",
        "artifact.write_remediation_result"
      ]
    },
    "context_compiler": {
      "mutation_allowed": false,
      "capabilities": [
        "repository.read",
        "artifact.read",
        "graphiti.read",
        "artifact.write_context_pack"
      ]
    },
    "sentinel": {
      "mutation_allowed": false,
      "capabilities": [
        "repository.read",
        "git.inspect",
        "graph.inspect",
        "artifact.invalidate",
        "campaign.suspend",
        "artifact.write_sentinel_report"
      ]
    },
    "evidence_writer": {
      "mutation_allowed": false,
      "capabilities": [
        "artifact.read",
        "receipt.append",
        "artifact.write_evidence_receipt"
      ]
    }
  },
  "globally_forbidden_capabilities": [
    "git.force_push",
    "pr.merge",
    "pr.admin_merge",
    "secret.read",
    "secret.write",
    "test.weaken_for_green"
  ]
}
JSON

cat > "$ROOT/autonomy/schemas/agent-deployment.schema.json" <<'JSON'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://quantum-l9.dev/schemas/agent-deployment.schema.json",
  "title": "L9 Agent Deployment Manifest",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "deployment_id",
    "campaign_id",
    "graph_id",
    "required_roles",
    "fail_closed"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"
    },
    "deployment_id": {
      "type": "string",
      "minLength": 1
    },
    "campaign_id": {
      "type": "string",
      "minLength": 1
    },
    "graph_id": {
      "type": "string",
      "minLength": 1
    },
    "required_roles": {
      "type": "object",
      "minProperties": 1,
      "additionalProperties": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "min",
          "max",
          "mutation"
        ],
        "properties": {
          "min": {
            "type": "integer",
            "minimum": 0
          },
          "max": {
            "type": "integer",
            "minimum": 0
          },
          "mutation": {
            "type": "boolean"
          },
          "conditional_on": {
            "type": "string",
            "minLength": 1
          },
          "independent_from": {
            "type": "array",
            "uniqueItems": true,
            "items": {
              "type": "string",
              "minLength": 1
            }
          }
        }
      }
    },
    "fail_closed": {
      "type": "object",
      "additionalProperties": {
        "type": "boolean"
      },
      "required": [
        "missing_required_agent",
        "invalid_agent_output",
        "executor_without_synthesis",
        "self_review",
        "unverified_completion"
      ],
      "properties": {
        "missing_required_agent": {
          "const": true
        },
        "invalid_agent_output": {
          "const": true
        },
        "executor_without_synthesis": {
          "const": true
        },
        "self_review": {
          "const": true
        },
        "unverified_completion": {
          "const": true
        }
      }
    }
  }
}
JSON

cat > "$ROOT/autonomy/schemas/campaign-authorization.schema.json" <<'JSON'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://quantum-l9.dev/schemas/campaign-authorization.schema.json",
  "title": "L9 Campaign Authorization",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "campaign_id",
    "objective",
    "authority",
    "scope",
    "budgets",
    "validation",
    "base_state",
    "revocation"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"
    },
    "campaign_id": {
      "type": "string",
      "minLength": 1
    },
    "objective": {
      "type": "string",
      "minLength": 1
    },
    "authority": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "issuer",
        "issued_at",
        "expires_at"
      ],
      "properties": {
        "issuer": {
          "type": "string",
          "minLength": 1
        },
        "issued_at": {
          "type": "string",
          "format": "date-time"
        },
        "expires_at": {
          "type": "string",
          "format": "date-time"
        }
      }
    },
    "scope": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "repositories",
        "allowed_paths",
        "forbidden_paths",
        "allowed_operations",
        "forbidden_operations"
      ],
      "properties": {
        "repositories": {
          "type": "array",
          "minItems": 1,
          "uniqueItems": true,
          "items": {
            "type": "string",
            "minLength": 1
          }
        },
        "allowed_paths": {
          "type": "array",
          "uniqueItems": true,
          "items": {
            "type": "string",
            "minLength": 1
          }
        },
        "forbidden_paths": {
          "type": "array",
          "uniqueItems": true,
          "items": {
            "type": "string",
            "minLength": 1
          }
        },
        "allowed_operations": {
          "type": "array",
          "uniqueItems": true,
          "items": {
            "type": "string",
            "minLength": 1
          }
        },
        "forbidden_operations": {
          "type": "array",
          "uniqueItems": true,
          "items": {
            "type": "string",
            "minLength": 1
          }
        }
      }
    },
    "budgets": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "max_files_changed",
        "max_lines_changed",
        "max_mutation_agents",
        "max_read_agents",
        "max_poll_agents",
        "max_runtime_minutes",
        "max_tool_failures"
      ],
      "properties": {
        "max_files_changed": {
          "type": "integer",
          "minimum": 1
        },
        "max_lines_changed": {
          "type": "integer",
          "minimum": 1
        },
        "max_mutation_agents": {
          "type": "integer",
          "minimum": 1
        },
        "max_read_agents": {
          "type": "integer",
          "minimum": 1
        },
        "max_poll_agents": {
          "type": "integer",
          "minimum": 0
        },
        "max_runtime_minutes": {
          "type": "integer",
          "minimum": 1
        },
        "max_tool_failures": {
          "type": "integer",
          "minimum": 0
        }
      }
    },
    "validation": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "required_checks",
        "independent_review_required",
        "human_merge_required"
      ],
      "properties": {
        "required_checks": {
          "type": "array",
          "minItems": 1,
          "uniqueItems": true,
          "items": {
            "type": "string",
            "minLength": 1
          }
        },
        "independent_review_required": {
          "const": true
        },
        "human_merge_required": {
          "const": true
        }
      }
    },
    "base_state": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "repository",
        "branch",
        "commit_sha"
      ],
      "properties": {
        "repository": {
          "type": "string",
          "minLength": 1
        },
        "branch": {
          "type": "string",
          "minLength": 1
        },
        "commit_sha": {
          "type": "string",
          "minLength": 7
        }
      }
    },
    "revocation": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "kill_switch_file",
        "revoke_on_scope_drift",
        "revoke_on_policy_conflict",
        "revoke_on_base_sha_drift"
      ],
      "properties": {
        "kill_switch_file": {
          "type": "string",
          "minLength": 1
        },
        "revoke_on_scope_drift": {
          "const": true
        },
        "revoke_on_policy_conflict": {
          "const": true
        },
        "revoke_on_base_sha_drift": {
          "const": true
        }
      }
    }
  }
}
JSON

cat > "$ROOT/autonomy/tests/__init__.py" <<'PY'

PY

cat > "$ROOT/autonomy/tests/test_wave1.py" <<'PY'
from __future__ import annotations

import json
import unittest
from pathlib import Path

from autonomy.compiler.graph_compiler import compile_graph
from autonomy.errors import (
    ContractError,
    GraphCompilationError,
    GraphValidationError,
)
from autonomy.io import load_json
from autonomy.models import CampaignAuthorization, DeploymentManifest
from autonomy.validation.graph_linter import GraphLinter

ROOT = Path(__file__).resolve().parents[2]


class Wave1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.campaign_payload = load_json(ROOT / "autonomy/examples/w7-campaign.json")
        self.campaign_payload["base_state"]["commit_sha"] = "abc1234"
        self.deployment_payload = load_json(
            ROOT / "autonomy/examples/w7-deployment.json"
        )
        self.action_payload = load_json(ROOT / "autonomy/examples/w7-actions.json")
        self.role_policy = load_json(
            ROOT / "autonomy/policies/role-capabilities.json"
        )
        self.pipeline_policy = load_json(
            ROOT / "autonomy/policies/pipeline-invariants.json"
        )

    def compile(self):
        campaign = CampaignAuthorization.from_dict(self.campaign_payload)
        deployment = DeploymentManifest.from_dict(self.deployment_payload)
        return (
            compile_graph(
                campaign,
                deployment,
                self.action_payload,
            ),
            deployment,
        )

    def test_compiles_valid_w7_graph(self) -> None:
        compiled, _ = self.compile()
        self.assertTrue(compiled.graph_id.startswith("graph-"))
        self.assertEqual(
            len(compiled.topological_order),
            len(compiled.actions),
        )
        self.assertLess(
            compiled.topological_order.index("synthesize-m0"),
            compiled.topological_order.index("execute-m0"),
        )
        self.assertLess(
            compiled.topological_order.index("execute-m0"),
            compiled.topological_order.index("verify-m0-scope"),
        )

    def test_linter_accepts_valid_graph(self) -> None:
        compiled, deployment = self.compile()
        linter = GraphLinter(
            deployment=deployment,
            role_policy=self.role_policy,
            pipeline_policy=self.pipeline_policy,
        )
        linter.assert_valid(compiled.to_dict())

    def test_cycle_is_rejected(self) -> None:
        payload = json.loads(json.dumps(self.action_payload))
        first = payload["actions"][0]
        first["depends_on"] = ["evidence-writer"]
        campaign = CampaignAuthorization.from_dict(self.campaign_payload)
        deployment = DeploymentManifest.from_dict(self.deployment_payload)
        with self.assertRaises(GraphCompilationError):
            compile_graph(campaign, deployment, payload)

    def test_executor_without_synthesis_is_rejected(self) -> None:
        payload = json.loads(json.dumps(self.action_payload))
        for action in payload["actions"]:
            if action["id"] == "execute-m0":
                action["depends_on"] = ["ro-m0-gap"]
        campaign = CampaignAuthorization.from_dict(self.campaign_payload)
        deployment = DeploymentManifest.from_dict(self.deployment_payload)
        compiled = compile_graph(campaign, deployment, payload)
        linter = GraphLinter(
            deployment=deployment,
            role_policy=self.role_policy,
            pipeline_policy=self.pipeline_policy,
        )
        with self.assertRaises(GraphValidationError):
            linter.assert_valid(compiled.to_dict())

    def test_autonomous_merge_is_rejected(self) -> None:
        payload = json.loads(json.dumps(self.action_payload))
        for action in payload["actions"]:
            if action["id"] == "execute-m0":
                action["metadata"]["operations"].append("merge_pull_request")
        campaign = CampaignAuthorization.from_dict(self.campaign_payload)
        deployment = DeploymentManifest.from_dict(self.deployment_payload)
        compiled = compile_graph(campaign, deployment, payload)
        linter = GraphLinter(
            deployment=deployment,
            role_policy=self.role_policy,
            pipeline_policy=self.pipeline_policy,
        )
        findings = linter.lint(compiled.to_dict())
        self.assertTrue(any(item.code == "PIPE-008" for item in findings))

    def test_campaign_requires_resolved_base_sha(self) -> None:
        payload = json.loads(json.dumps(self.campaign_payload))
        payload["base_state"]["commit_sha"] = ""
        with self.assertRaises(ContractError):
            CampaignAuthorization.from_dict(payload)

    def test_campaign_cannot_allow_force_push(self) -> None:
        payload = json.loads(json.dumps(self.campaign_payload))
        payload["scope"]["allowed_operations"].append("force_push")
        with self.assertRaises(ContractError):
            CampaignAuthorization.from_dict(payload)


if __name__ == "__main__":
    unittest.main()
PY

cat > "$ROOT/autonomy/validation/__init__.py" <<'PY'
"""Compiled graph validation for the L9 autonomy control plane."""
PY

cat > "$ROOT/autonomy/validation/graph_linter.py" <<'PY'
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from autonomy.errors import GraphValidationError
from autonomy.io import load_json
from autonomy.models import (
    Action,
    DeploymentManifest,
    Role,
)


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    action_id: str | None = None

    def render(self) -> str:
        suffix = f" action={self.action_id}" if self.action_id else ""
        return f"{self.severity} {self.code}{suffix}: {self.message}"


class GraphLinter:
    def __init__(
        self,
        deployment: DeploymentManifest,
        role_policy: Mapping[str, Any],
        pipeline_policy: Mapping[str, Any],
    ) -> None:
        self.deployment = deployment
        self.role_policy = role_policy
        self.pipeline_policy = pipeline_policy

    def lint(self, compiled_graph: Mapping[str, Any]) -> list[Finding]:
        raw_actions = compiled_graph.get("actions")
        if not isinstance(raw_actions, list):
            raise GraphValidationError("Compiled graph actions must be a list")
        actions = [Action.from_dict(item) for item in raw_actions]
        findings: list[Finding] = []
        findings.extend(self._check_role_cardinality(actions))
        findings.extend(self._check_role_mutation(actions))
        findings.extend(self._check_executor_dependencies(actions))
        findings.extend(self._check_reviewer_independence(actions))
        findings.extend(self._check_verification_before_review(actions))
        findings.extend(self._check_human_merge_policy(actions))
        findings.extend(self._check_claim_modes(actions))
        findings.extend(self._check_completion_contracts(actions))
        return findings

    def assert_valid(self, compiled_graph: Mapping[str, Any]) -> None:
        findings = self.lint(compiled_graph)
        blocking = [finding for finding in findings if finding.severity == "ERROR"]
        if blocking:
            rendered = "\n".join(item.render() for item in blocking)
            raise GraphValidationError(
                f"Compiled graph failed validation:\n{rendered}"
            )

    def _check_role_cardinality(
        self,
        actions: Iterable[Action],
    ) -> list[Finding]:
        counts = Counter(action.role for action in actions)
        findings: list[Finding] = []
        for role, configuration in self.deployment.required_roles.items():
            minimum = int(configuration.get("min", 0))
            maximum = int(configuration.get("max", minimum))
            count = counts[role]
            if count < minimum:
                findings.append(
                    Finding(
                        "PIPE-ROLE-MIN",
                        "ERROR",
                        f"Role {role.value!r} requires at least {minimum} "
                        f"actions but graph contains {count}",
                    )
                )
            if count > maximum:
                findings.append(
                    Finding(
                        "PIPE-ROLE-MAX",
                        "ERROR",
                        f"Role {role.value!r} allows at most {maximum} "
                        f"actions but graph contains {count}",
                    )
                )
        return findings

    def _check_role_mutation(
        self,
        actions: Iterable[Action],
    ) -> list[Finding]:
        policies = self.role_policy.get("roles", {})
        findings: list[Finding] = []
        for action in actions:
            role_config = policies.get(action.role.value)
            if not isinstance(role_config, Mapping):
                findings.append(
                    Finding(
                        "POLICY-ROLE-MISSING",
                        "ERROR",
                        f"No role capability policy exists for {action.role.value!r}",
                        action.id,
                    )
                )
                continue
            mutation_allowed = bool(role_config.get("mutation_allowed", False))
            if action.mutation and not mutation_allowed:
                findings.append(
                    Finding(
                        "PIPE-MUTATION-ROLE",
                        "ERROR",
                        f"Role {action.role.value!r} is not allowed to mutate",
                        action.id,
                    )
                )
        return findings

    def _check_executor_dependencies(
        self,
        actions: Iterable[Action],
    ) -> list[Finding]:
        action_by_id = {action.id: action for action in actions}
        findings: list[Finding] = []
        for action in action_by_id.values():
            if action.role is not Role.EXECUTOR:
                continue
            dependencies = [
                action_by_id[dependency] for dependency in action.depends_on
            ]
            has_synthesis = any(
                dependency.role is Role.SYNTHESIS for dependency in dependencies
            )
            if not has_synthesis:
                findings.append(
                    Finding(
                        "PIPE-001",
                        "ERROR",
                        "Executor must depend directly on a synthesis action",
                        action.id,
                    )
                )
        return findings

    def _check_reviewer_independence(
        self,
        actions: Iterable[Action],
    ) -> list[Finding]:
        action_by_id = {action.id: action for action in actions}
        findings: list[Finding] = []
        for action in action_by_id.values():
            if action.role is not Role.REVIEWER:
                continue
            executor_dependencies = {
                source
                for source in action.independent_from
                if action_by_id[source].role is Role.EXECUTOR
            }
            if not executor_dependencies:
                findings.append(
                    Finding(
                        "PIPE-004",
                        "ERROR",
                        "Reviewer must declare independence from at least "
                        "one executor action",
                        action.id,
                    )
                )
            if action.mutation:
                findings.append(
                    Finding(
                        "PIPE-REVIEW-MUTATION",
                        "ERROR",
                        "Independent reviewer cannot mutate",
                        action.id,
                    )
                )
        return findings

    def _check_verification_before_review(
        self,
        actions: Iterable[Action],
    ) -> list[Finding]:
        action_by_id = {action.id: action for action in actions}
        findings: list[Finding] = []
        for action in action_by_id.values():
            if action.role is not Role.REVIEWER:
                continue
            dependencies = [
                action_by_id[dependency] for dependency in action.depends_on
            ]
            verifier_count = sum(
                dependency.role is Role.VERIFIER for dependency in dependencies
            )
            if verifier_count < 1:
                findings.append(
                    Finding(
                        "PIPE-005",
                        "ERROR",
                        "Reviewer must depend on at least one verifier",
                        action.id,
                    )
                )
        return findings

    def _check_human_merge_policy(
        self,
        actions: Iterable[Action],
    ) -> list[Finding]:
        findings: list[Finding] = []
        for action in actions:
            forbidden = {
                "merge",
                "merge_pull_request",
                "admin_merge",
                "force_push",
            }
            declared_operations = set(action.metadata.get("operations", []))
            unsafe = forbidden & declared_operations
            if unsafe:
                findings.append(
                    Finding(
                        "PIPE-008",
                        "ERROR",
                        "Action declares forbidden autonomous operations: "
                        + ", ".join(sorted(unsafe)),
                        action.id,
                    )
                )
        return findings

    def _check_claim_modes(
        self,
        actions: Iterable[Action],
    ) -> list[Finding]:
        findings: list[Finding] = []
        for action in actions:
            write_claims = [claim for claim in action.claims if claim.mode == "write"]
            if action.mutation and not write_claims:
                findings.append(
                    Finding(
                        "PIPE-WRITE-CLAIM",
                        "ERROR",
                        "Mutation action requires at least one exclusive write claim",
                        action.id,
                    )
                )
            if not action.mutation and write_claims:
                findings.append(
                    Finding(
                        "PIPE-READONLY-WRITE-CLAIM",
                        "ERROR",
                        "Non-mutation action cannot request write claims",
                        action.id,
                    )
                )
        return findings

    def _check_completion_contracts(
        self,
        actions: Iterable[Action],
    ) -> list[Finding]:
        findings: list[Finding] = []
        expected_artifacts = {
            Role.RECON: "ReconReport",
            Role.SYNTHESIS: "ExecutionBrief",
            Role.EXECUTOR: "ExecutionResult",
            Role.VERIFIER: "VerificationReport",
            Role.REVIEWER: "ReviewVerdict",
            Role.POLLER: "PollReport",
            Role.FAILURE_CLASSIFIER: "RemediationBrief",
            Role.REMEDIATOR: "RemediationResult",
            Role.CONTEXT_COMPILER: "ContextPack",
            Role.SENTINEL: "SentinelReport",
            Role.EVIDENCE_WRITER: "EvidenceReceipt",
        }
        for action in actions:
            expected = expected_artifacts.get(action.role)
            if expected and action.completion.artifact_kind != expected:
                findings.append(
                    Finding(
                        "PIPE-ARTIFACT-KIND",
                        "ERROR",
                        f"Role {action.role.value!r} must produce "
                        f"{expected!r}, not "
                        f"{action.completion.artifact_kind!r}",
                        action.id,
                    )
                )
        return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a compiled L9 autonomy graph."
    )
    parser.add_argument("--graph", required=True)
    parser.add_argument("--deployment", required=True)
    parser.add_argument(
        "--role-policy",
        default="autonomy/policies/role-capabilities.json",
    )
    parser.add_argument(
        "--pipeline-policy",
        default="autonomy/policies/pipeline-invariants.json",
    )
    args = parser.parse_args()
    graph = load_json(args.graph)
    deployment = DeploymentManifest.from_dict(load_json(args.deployment))
    role_policy = load_json(args.role_policy)
    pipeline_policy = load_json(args.pipeline_policy)
    linter = GraphLinter(
        deployment=deployment,
        role_policy=role_policy,
        pipeline_policy=pipeline_policy,
    )
    findings = linter.lint(graph)
    for finding in findings:
        print(finding.render())
    errors = [finding for finding in findings if finding.severity == "ERROR"]
    if errors:
        print(f"FAILED: {len(errors)} blocking finding(s)")
        return 1
    print("PASS: compiled graph satisfies Wave-1 invariants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

cat > "$ROOT/autonomy/versioning.py" <<'PY'
from __future__ import annotations

import re
from dataclasses import dataclass

from autonomy.errors import CompatibilityError

_VERSION_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)$"
)


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "Version":
        match = _VERSION_RE.match(value)
        if not match:
            raise CompatibilityError(
                f"Version must use strict MAJOR.MINOR.PATCH format: {value!r}"
            )
        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
        )

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def require_same_major(actual: str, expected: str, component: str) -> None:
    actual_version = Version.parse(actual)
    expected_version = Version.parse(expected)
    if actual_version.major != expected_version.major:
        raise CompatibilityError(
            f"{component} major-version mismatch: "
            f"actual={actual_version}, expected={expected_version}"
        )
    if actual_version < expected_version:
        raise CompatibilityError(
            f"{component} is older than the minimum supported version: "
            f"actual={actual_version}, minimum={expected_version}"
        )
PY

echo "Wave 1 installed under: $ROOT/autonomy"
echo
echo "Next steps:"
echo "  1. Replace 0000000 in autonomy/examples/w7-campaign.json"
echo "  2. Run: python -m unittest discover -s autonomy/tests -v"
echo "  3. Compile and lint using autonomy/README.md"

