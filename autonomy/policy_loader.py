from __future__ import annotations

import copy
import json
from typing import Any

# Embedded payloads — no filesystem I/O (Sonar pythonsecurity:S8707).
# Edit autonomy/{policies,examples,tests/golden} JSON, then regenerate this module.
# Regenerate: python3 ops/scripts/regenerate_autonomy_policy_loader.py

_POLICIES: dict[str, Any] = json.loads(
    """
{
  "adapter-requirements": {
    "canonical_autonomy_provider": "root-autonomy-control-plane",
    "fail_closed_on": [
      "adapter_protocol_mismatch",
      "canonical_peer_binding_invalid",
      "runtime_unavailable",
      "gateway_unavailable",
      "policy_unavailable",
      "database_unwritable",
      "mandatory_policy_mismatch",
      "required_surface_capability_missing"
    ],
    "mandatory": {
      "autonomous_merge": false,
      "direct_tool_access": false,
      "supports_agent_identity": true,
      "supports_heartbeat": true,
      "supports_human_gate": true,
      "supports_lease_propagation": true,
      "supports_typed_artifacts": true,
      "tool_mediation_mode": "mandatory"
    },
    "optional_capabilities": {
      "supports_background_agents": "background_agent",
      "supports_independent_review": "independent_review"
    },
    "protocol_version": "1.0.0",
    "schema_version": "2.0.0"
  },
  "operation-aliases": {
    "capability_to_operation": {
      "artifact.invalidate": "edit_scoped",
      "artifact.read": "read",
      "artifact.read_recon_report": "read",
      "artifact.write_context_pack": "edit_scoped",
      "artifact.write_evidence_receipt": "edit_scoped",
      "artifact.write_execution_brief": "edit_scoped",
      "artifact.write_execution_result": "edit_scoped",
      "artifact.write_poll_report": "edit_scoped",
      "artifact.write_recon_report": "edit_scoped",
      "artifact.write_remediation_brief": "edit_scoped",
      "artifact.write_remediation_result": "edit_scoped",
      "artifact.write_review_verdict": "edit_scoped",
      "artifact.write_sentinel_report": "edit_scoped",
      "artifact.write_verification_report": "edit_scoped",
      "campaign.inspect": "read",
      "campaign.suspend": "read",
      "ci.inspect": "inspect_ci",
      "diff.inspect": "read",
      "evidence.inspect": "read",
      "git.commit_local": "commit_local",
      "git.diff": "read",
      "git.force_push": "force_push",
      "git.inspect": "read",
      "git.push_non_force_declared_branch": "push_non_force_declared_branch",
      "graph.inspect": "read",
      "graphiti.read": "read",
      "pr.admin_merge": "admin_merge",
      "pr.inspect": "inspect_review",
      "pr.merge": "merge",
      "receipt.append": "read",
      "receipt.inspect": "read",
      "repository.read": "read",
      "repository.search": "search",
      "repository.write_scoped": "edit_scoped",
      "review.inspect": "inspect_review",
      "runtime.probe": "read",
      "scheduler.request": "read",
      "secret.read": "modify_secrets",
      "secret.write": "modify_secrets",
      "status.inspect": "read",
      "test.inspect": "inspect_ci",
      "test.run": "run_tests",
      "test.weaken_for_green": "weaken_tests_for_green"
    },
    "schema_version": "1.0.0"
  },
  "pipeline-invariants": {
    "invariants": [
      {
        "continuous": true,
        "description": "No executor may start without a valid execution brief.",
        "id": "PIPE-001",
        "severity": "blocking"
      },
      {
        "continuous": true,
        "description": "No mutation may occur without an active scoped write lease.",
        "id": "PIPE-002",
        "severity": "blocking"
      },
      {
        "continuous": true,
        "description": "No action may consume stale or invalidated input artifacts.",
        "id": "PIPE-003",
        "severity": "blocking"
      },
      {
        "continuous": true,
        "description": "No executor may review or approve its own output.",
        "id": "PIPE-004",
        "severity": "blocking"
      },
      {
        "continuous": true,
        "description": "No result is merge-eligible without all required verifiers.",
        "id": "PIPE-005",
        "severity": "blocking"
      },
      {
        "continuous": true,
        "description": "No action may exceed its declared path or operation scope.",
        "id": "PIPE-006",
        "severity": "blocking"
      },
      {
        "continuous": true,
        "description": "No remediation mutation may start without a failure classification.",
        "id": "PIPE-007",
        "severity": "blocking"
      },
      {
        "continuous": true,
        "description": "No human gate, human merge, or A4 stop may be bypassed.",
        "id": "PIPE-008",
        "severity": "blocking"
      },
      {
        "continuous": true,
        "description": "No action is complete without a valid typed artifact and receipt.",
        "id": "PIPE-009",
        "severity": "blocking"
      },
      {
        "continuous": true,
        "description": "No campaign may execute with a failed root-autonomy client conformance check.",
        "id": "PIPE-010",
        "severity": "blocking"
      }
    ],
    "schema_version": "1.0.0"
  },
  "resource-classes": {
    "classes": {
      "context_compile": {
        "capacity": 64,
        "fill_policy": "saturate",
        "min_concurrency": 1,
        "mutation": false,
        "preemptible": true,
        "target_concurrency": 32
      },
      "controller_mutation": {
        "capacity": 16,
        "min_concurrency": 1,
        "mutation": true,
        "preemptible": false,
        "target_concurrency": 8
      },
      "evidence": {
        "capacity": 32,
        "min_concurrency": 0,
        "mutation": false,
        "preemptible": true,
        "target_concurrency": 16
      },
      "failure_analysis": {
        "capacity": 64,
        "fill_policy": "saturate",
        "min_concurrency": 0,
        "mutation": false,
        "preemptible": true,
        "target_concurrency": 32
      },
      "human_gate": {
        "capacity": 1,
        "min_concurrency": 0,
        "mutation": false,
        "preemptible": false,
        "target_concurrency": 1
      },
      "live_runtime": {
        "capacity": 64,
        "fill_policy": "saturate",
        "min_concurrency": 0,
        "mutation": false,
        "preemptible": false,
        "target_concurrency": 32
      },
      "poll_remote": {
        "capacity": 64,
        "fill_policy": "saturate",
        "min_concurrency": 0,
        "mutation": false,
        "preemptible": true,
        "target_concurrency": 32
      },
      "remediation_mutation": {
        "capacity": 96,
        "conflict_policy": "exclusive_claims_only",
        "fill_policy": "saturate",
        "min_concurrency": 1,
        "mutation": true,
        "preemptible": false,
        "target_concurrency": 64
      },
      "repository_mutation": {
        "capacity": 128,
        "conflict_policy": "exclusive_claims_only",
        "fill_policy": "saturate",
        "min_concurrency": 1,
        "mutation": true,
        "preemptible": false,
        "target_concurrency": 96
      },
      "repository_read": {
        "capacity": 400,
        "fill_policy": "saturate",
        "min_concurrency": 32,
        "mutation": false,
        "preemptible": true,
        "target_concurrency": 350
      },
      "repository_recon": {
        "capacity": 300,
        "fill_policy": "saturate",
        "min_concurrency": 32,
        "mutation": false,
        "preemptible": true,
        "target_concurrency": 300
      },
      "review": {
        "capacity": 96,
        "fill_policy": "saturate",
        "min_concurrency": 2,
        "mutation": false,
        "preemptible": true,
        "target_concurrency": 64
      },
      "sentinel": {
        "capacity": 16,
        "min_concurrency": 1,
        "mutation": false,
        "preemptible": false,
        "target_concurrency": 8
      },
      "synthesis": {
        "capacity": 64,
        "fill_policy": "saturate",
        "min_concurrency": 1,
        "mutation": false,
        "preemptible": true,
        "target_concurrency": 32
      },
      "verification": {
        "capacity": 160,
        "fill_policy": "saturate",
        "min_concurrency": 4,
        "mutation": false,
        "preemptible": true,
        "target_concurrency": 128
      }
    },
    "global": {
      "adaptive_backpressure": {
        "decrease_factor": 0.75,
        "enabled": true,
        "on_429": "multiplicative_decrease",
        "recovery": "additive_increase"
      },
      "backfill": true,
      "fill_policy": "saturate",
      "force_parallel_ready_actions": true,
      "mutation_parallelism": "max_non_conflicting",
      "provider_concurrency_ceiling": 500,
      "read_parallelism": "max_available",
      "reserved_control_slots": 20,
      "target_total_concurrency": 480
    },
    "schema_version": "2.0.0"
  },
  "role-capabilities": {
    "globally_forbidden_capabilities": [
      "git.force_push",
      "pr.merge",
      "pr.admin_merge",
      "secret.read",
      "secret.write",
      "test.weaken_for_green"
    ],
    "roles": {
      "context_compiler": {
        "capabilities": [
          "repository.read",
          "artifact.read",
          "graphiti.read",
          "artifact.write_context_pack"
        ],
        "mutation_allowed": false
      },
      "coordinator": {
        "capabilities": [
          "campaign.inspect",
          "graph.inspect",
          "scheduler.request",
          "status.inspect"
        ],
        "mutation_allowed": false
      },
      "evidence_writer": {
        "capabilities": [
          "artifact.read",
          "receipt.append",
          "artifact.write_evidence_receipt"
        ],
        "mutation_allowed": false
      },
      "executor": {
        "capabilities": [
          "repository.read",
          "repository.write_scoped",
          "test.run",
          "git.diff",
          "git.commit_local",
          "artifact.write_execution_result"
        ],
        "mutation_allowed": true
      },
      "failure_classifier": {
        "capabilities": [
          "repository.read",
          "ci.inspect",
          "test.inspect",
          "diff.inspect",
          "artifact.write_remediation_brief"
        ],
        "mutation_allowed": false
      },
      "poller": {
        "capabilities": [
          "pr.inspect",
          "ci.inspect",
          "review.inspect",
          "artifact.write_poll_report"
        ],
        "mutation_allowed": false
      },
      "recon": {
        "capabilities": [
          "repository.read",
          "repository.search",
          "graphiti.read",
          "artifact.write_recon_report"
        ],
        "mutation_allowed": false
      },
      "remediator": {
        "capabilities": [
          "repository.read",
          "repository.write_scoped",
          "test.run",
          "git.diff",
          "git.commit_local",
          "git.push_non_force_declared_branch",
          "artifact.write_remediation_result"
        ],
        "mutation_allowed": true
      },
      "reviewer": {
        "capabilities": [
          "repository.read",
          "diff.inspect",
          "test.inspect",
          "evidence.inspect",
          "receipt.inspect",
          "artifact.write_review_verdict"
        ],
        "mutation_allowed": false
      },
      "sentinel": {
        "capabilities": [
          "repository.read",
          "git.inspect",
          "graph.inspect",
          "artifact.invalidate",
          "campaign.suspend",
          "artifact.write_sentinel_report"
        ],
        "mutation_allowed": false
      },
      "synthesis": {
        "capabilities": [
          "repository.read",
          "artifact.read_recon_report",
          "artifact.write_execution_brief",
          "graphiti.read"
        ],
        "mutation_allowed": false
      },
      "verifier": {
        "capabilities": [
          "repository.read",
          "diff.inspect",
          "test.run",
          "runtime.probe",
          "evidence.inspect",
          "artifact.write_verification_report"
        ],
        "mutation_allowed": false
      }
    },
    "schema_version": "1.0.0"
  }
}
"""
)

_EXAMPLES: dict[str, Any] = json.loads(
    """
{
  "adapters/claude-code.json": {
    "adapter_id": "claude-code-local",
    "adapter_type": "claude-code",
    "autonomous_merge": false,
    "direct_tool_access": false,
    "executable": "claude",
    "execution_profile_ref": "worker-default",
    "metadata": {
      "database_path": ".l9/autonomy/runtime.sqlite3",
      "merge_protocol": "human-only",
      "poll_protocol": "protocol-b",
      "pre_tool_hook_required": true,
      "task_transport": "claude-code-task"
    },
    "peer_ref": "claude-code",
    "protocol_version": "1.0.0",
    "provider_ref": "claude-code-direct",
    "supports_agent_identity": true,
    "supports_background_agents": true,
    "supports_heartbeat": true,
    "supports_human_gate": true,
    "supports_independent_review": true,
    "supports_lease_propagation": true,
    "supports_typed_artifacts": true,
    "surface": "claude-cli",
    "tool_mediation_mode": "mandatory"
  },
  "adapters/cursor.json": {
    "adapter_id": "cursor-local",
    "adapter_type": "cursor",
    "autonomous_merge": false,
    "direct_tool_access": false,
    "executable": "cursor",
    "execution_profile_ref": "worker-default",
    "metadata": {
      "database_path": ".l9/autonomy/runtime.sqlite3",
      "merge_protocol": "human-only",
      "poll_protocol": "protocol-b",
      "task_transport": "cursor-task"
    },
    "peer_ref": "cursor",
    "protocol_version": "1.0.0",
    "provider_ref": "cursor-foreground",
    "supports_agent_identity": true,
    "supports_background_agents": true,
    "supports_heartbeat": true,
    "supports_human_gate": true,
    "supports_independent_review": true,
    "supports_lease_propagation": true,
    "supports_typed_artifacts": true,
    "surface": "cursor-ide",
    "tool_mediation_mode": "mandatory"
  },
  "w7-actions.json": {
    "actions": [
      {
        "claims": [],
        "completion": {
          "artifact_kind": "CampaignStatus",
          "require_base_sha_match": true,
          "required_fields": [
            "campaign_id",
            "state"
          ]
        },
        "depends_on": [],
        "id": "campaign-coordinator",
        "kind": "work",
        "mutation": false,
        "priority_weight": 10,
        "resource_class": "repository_read",
        "role": "coordinator"
      },
      {
        "claims": [
          {
            "exclusive": false,
            "key": "repo:odoo",
            "mode": "read"
          }
        ],
        "completion": {
          "artifact_kind": "ContextPack",
          "require_base_sha_match": true,
          "required_fields": [
            "objective",
            "authority",
            "base_sha",
            "allowed_paths",
            "forbidden_paths",
            "acceptance_criteria"
          ]
        },
        "depends_on": [
          "campaign-coordinator"
        ],
        "id": "context-compile-task046",
        "kind": "work",
        "mutation": false,
        "priority_weight": 9,
        "resource_class": "context_compile",
        "role": "context_compiler"
      },
      {
        "claims": [
          {
            "exclusive": false,
            "key": "repo:stack-config",
            "mode": "read"
          }
        ],
        "completion": {
          "artifact_kind": "ReconReport",
          "require_base_sha_match": true,
          "require_empty_blockers": false,
          "required_fields": [
            "status",
            "feeds",
            "evidence",
            "impl_checklist"
          ]
        },
        "depends_on": [
          "context-compile-task046"
        ],
        "id": "ro-stack-inventory",
        "kind": "work",
        "mutation": false,
        "priority_weight": 8,
        "resource_class": "repository_recon",
        "role": "recon"
      },
      {
        "claims": [
          {
            "exclusive": false,
            "key": "repo:odoo",
            "mode": "read"
          }
        ],
        "completion": {
          "artifact_kind": "ReconReport",
          "require_base_sha_match": true,
          "require_empty_blockers": false,
          "required_fields": [
            "status",
            "feeds",
            "evidence",
            "impl_checklist"
          ]
        },
        "depends_on": [
          "context-compile-task046"
        ],
        "id": "ro-m0-gap",
        "kind": "work",
        "mutation": false,
        "priority_weight": 10,
        "resource_class": "repository_recon",
        "role": "recon"
      },
      {
        "claims": [
          {
            "exclusive": false,
            "key": "repo:owner-schemas",
            "mode": "read"
          }
        ],
        "completion": {
          "artifact_kind": "ReconReport",
          "require_base_sha_match": true,
          "require_empty_blockers": false,
          "required_fields": [
            "status",
            "feeds",
            "evidence",
            "impl_checklist"
          ]
        },
        "depends_on": [
          "context-compile-task046"
        ],
        "id": "ro-owner-schemas",
        "kind": "work",
        "mutation": false,
        "priority_weight": 9,
        "resource_class": "repository_recon",
        "role": "recon"
      },
      {
        "claims": [
          {
            "exclusive": false,
            "key": "repo:gate-actions",
            "mode": "read"
          }
        ],
        "completion": {
          "artifact_kind": "ReconReport",
          "require_base_sha_match": true,
          "require_empty_blockers": false,
          "required_fields": [
            "status",
            "feeds",
            "evidence",
            "impl_checklist"
          ]
        },
        "depends_on": [
          "context-compile-task046"
        ],
        "id": "ro-gate-actions",
        "kind": "work",
        "mutation": false,
        "priority_weight": 7,
        "resource_class": "repository_recon",
        "role": "recon"
      },
      {
        "claims": [],
        "completion": {
          "artifact_kind": "ExecutionBrief",
          "require_base_sha_match": true,
          "require_empty_blockers": true,
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
          ]
        },
        "depends_on": [
          "ro-stack-inventory",
          "ro-m0-gap",
          "ro-owner-schemas",
          "ro-gate-actions"
        ],
        "id": "synthesize-m0",
        "kind": "synthesis",
        "mutation": false,
        "priority_weight": 10,
        "resource_class": "synthesis",
        "role": "synthesis"
      },
      {
        "claims": [
          {
            "exclusive": true,
            "key": "repo:odoo",
            "mode": "write"
          },
          {
            "exclusive": true,
            "key": "branch:feat/mothball-local-intelligence",
            "mode": "write"
          }
        ],
        "completion": {
          "artifact_kind": "ExecutionResult",
          "require_base_sha_match": true,
          "require_empty_blockers": true,
          "required_fields": [
            "task_id",
            "base_sha",
            "result_sha",
            "changed_paths",
            "test_results",
            "scope_validation"
          ]
        },
        "depends_on": [
          "synthesize-m0"
        ],
        "id": "execute-m0",
        "kind": "work",
        "metadata": {
          "operations": [
            "edit_scoped",
            "run_tests",
            "commit_local"
          ]
        },
        "mutation": true,
        "priority_weight": 10,
        "resource_class": "repository_mutation",
        "role": "executor"
      },
      {
        "claims": [
          {
            "exclusive": false,
            "key": "repo:odoo",
            "mode": "read"
          }
        ],
        "completion": {
          "artifact_kind": "VerificationReport",
          "require_base_sha_match": false,
          "require_empty_blockers": true,
          "required_fields": [
            "verification_type",
            "target_sha",
            "checks",
            "verdict",
            "evidence"
          ]
        },
        "depends_on": [
          "execute-m0"
        ],
        "id": "verify-m0-scope",
        "kind": "validation",
        "mutation": false,
        "priority_weight": 9,
        "resource_class": "verification",
        "role": "verifier"
      },
      {
        "claims": [
          {
            "exclusive": false,
            "key": "docker:five-service",
            "mode": "read"
          }
        ],
        "completion": {
          "artifact_kind": "VerificationReport",
          "require_base_sha_match": false,
          "require_empty_blockers": true,
          "required_fields": [
            "verification_type",
            "target_sha",
            "checks",
            "verdict",
            "evidence",
            "live_five_service_stack_exercised"
          ]
        },
        "depends_on": [
          "execute-m0",
          "ro-stack-inventory",
          "ro-gate-actions"
        ],
        "id": "verify-m0-live",
        "kind": "validation",
        "mutation": false,
        "priority_weight": 10,
        "resource_class": "live_runtime",
        "role": "verifier"
      },
      {
        "claims": [
          {
            "exclusive": false,
            "key": "repo:odoo",
            "mode": "read"
          }
        ],
        "completion": {
          "artifact_kind": "ReviewVerdict",
          "require_base_sha_match": false,
          "require_empty_blockers": false,
          "required_fields": [
            "authority_compliance",
            "scope_compliance",
            "invariant_preservation",
            "correctness",
            "security",
            "verdict",
            "findings"
          ]
        },
        "depends_on": [
          "verify-m0-scope",
          "verify-m0-live"
        ],
        "id": "review-m0-independent",
        "independent_from": [
          "execute-m0"
        ],
        "kind": "validation",
        "mutation": false,
        "priority_weight": 10,
        "resource_class": "review",
        "role": "reviewer"
      },
      {
        "claims": [
          {
            "exclusive": false,
            "key": "pr:M0",
            "mode": "observe"
          }
        ],
        "completion": {
          "artifact_kind": "PollReport",
          "require_base_sha_match": false,
          "require_empty_blockers": false,
          "required_fields": [
            "pr_number",
            "head_sha",
            "checks",
            "review_threads",
            "terminal_state"
          ]
        },
        "conditional_on": "review-m0-independent",
        "depends_on": [
          "review-m0-independent"
        ],
        "id": "poll-m0",
        "kind": "poll",
        "mutation": false,
        "priority_weight": 8,
        "resource_class": "poll_remote",
        "role": "poller"
      },
      {
        "claims": [
          {
            "exclusive": false,
            "key": "repo:odoo",
            "mode": "read"
          }
        ],
        "completion": {
          "artifact_kind": "SentinelReport",
          "require_base_sha_match": false,
          "require_empty_blockers": false,
          "required_fields": [
            "campaign_id",
            "expected_base_sha",
            "observed_base_sha",
            "scope_drift",
            "policy_conflicts",
            "decision"
          ]
        },
        "depends_on": [
          "campaign-coordinator"
        ],
        "id": "base-sha-sentinel",
        "kind": "validation",
        "mutation": false,
        "priority_weight": 10,
        "resource_class": "sentinel",
        "role": "sentinel"
      },
      {
        "claims": [],
        "completion": {
          "artifact_kind": "EvidenceReceipt",
          "require_base_sha_match": false,
          "require_empty_blockers": true,
          "required_fields": [
            "campaign_id",
            "graph_id",
            "event_type",
            "artifact_hash",
            "previous_receipt_hash",
            "receipt_hash"
          ]
        },
        "depends_on": [
          "review-m0-independent",
          "base-sha-sentinel"
        ],
        "id": "evidence-writer",
        "kind": "work",
        "mutation": false,
        "priority_weight": 7,
        "resource_class": "evidence",
        "role": "evidence_writer"
      }
    ],
    "schema_version": "1.0.0"
  },
  "w7-campaign.json": {
    "authority": {
      "expires_at": "2026-08-03T03:00:00Z",
      "issued_at": "2026-08-02T15:00:00Z",
      "issuer": "human"
    },
    "base_state": {
      "branch": "main",
      "commit_sha": "0000000",
      "repository": "Quantum-L9/Cursor-Governance"
    },
    "budgets": {
      "max_files_changed": 80,
      "max_lines_changed": 6000,
      "max_mutation_agents": 128,
      "max_poll_agents": 64,
      "max_read_agents": 450,
      "max_runtime_minutes": 720,
      "max_tool_failures": 8
    },
    "campaign_id": "autonomy-w7-mothball-2026-08-02",
    "objective": "Execute W7 M0-M6 with enforceable subagent deployment and human-only merge.",
    "revocation": {
      "kill_switch_file": ".l9/autonomy/revoke",
      "revoke_on_base_sha_drift": true,
      "revoke_on_policy_conflict": true,
      "revoke_on_scope_drift": true
    },
    "schema_version": "1.0.0",
    "scope": {
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
      "allowed_paths": [
        "addons/plasticos_gate/**",
        "program/mothballing-cursor-contracts/**",
        "ledger/artifacts/wave7/**",
        "autonomy/**"
      ],
      "forbidden_operations": [
        "merge",
        "merge_pull_request",
        "admin_merge",
        "force_push",
        "modify_secrets",
        "weaken_tests_for_green"
      ],
      "forbidden_paths": [
        "ops/secrets/**",
        ".env",
        "**/*.pem",
        "**/*.key"
      ],
      "repositories": [
        "Quantum-L9/Cursor-Governance"
      ]
    },
    "validation": {
      "human_merge_required": true,
      "independent_review_required": true,
      "required_checks": [
        "unit_tests",
        "schema_validation",
        "governance_invariants",
        "scope_lock",
        "live_integration_proof"
      ]
    }
  },
  "w7-deployment.json": {
    "campaign_id": "autonomy-w7-mothball-2026-08-02",
    "deployment_id": "deploy-w7-task046-v1",
    "fail_closed": {
      "executor_without_synthesis": true,
      "invalid_agent_output": true,
      "missing_required_agent": true,
      "self_review": true,
      "unverified_completion": true
    },
    "graph_id": "AUTO",
    "required_roles": {
      "context_compiler": {
        "max": 64,
        "min": 1,
        "mutation": false
      },
      "coordinator": {
        "max": 8,
        "min": 1,
        "mutation": false
      },
      "evidence_writer": {
        "max": 32,
        "min": 1,
        "mutation": false
      },
      "executor": {
        "max": 128,
        "min": 1,
        "mutation": true
      },
      "failure_classifier": {
        "max": 64,
        "min": 0,
        "mutation": false
      },
      "poller": {
        "conditional_on": "pr_open",
        "max": 64,
        "min": 0,
        "mutation": false
      },
      "recon": {
        "max": 320,
        "min": 4,
        "mutation": false
      },
      "remediator": {
        "max": 96,
        "min": 0,
        "mutation": true
      },
      "reviewer": {
        "independent_from": [
          "executor"
        ],
        "max": 96,
        "min": 1,
        "mutation": false
      },
      "sentinel": {
        "max": 16,
        "min": 1,
        "mutation": false
      },
      "synthesis": {
        "max": 64,
        "min": 1,
        "mutation": false
      },
      "verifier": {
        "max": 160,
        "min": 2,
        "mutation": false
      }
    },
    "schema_version": "1.0.0"
  }
}
"""
)

_GOLDEN: dict[str, Any] = json.loads(
    """
{
  "task045-human-stop.spec.json": {
    "forbidden_events": [
      "human_gate_auto_approved",
      "autonomous_merge",
      "admin_merge"
    ],
    "maximum_counts": {
      "autonomous_merge": 0,
      "human_gate_auto_approved": 0
    },
    "required_events": [
      "campaign_bootstrapped"
    ],
    "required_sequence": [
      "campaign_bootstrapped"
    ],
    "schema_version": "1.0.0"
  },
  "task046-happy-path.spec.json": {
    "forbidden_events": [
      "autonomous_merge",
      "force_push",
      "admin_merge",
      "test_weakened"
    ],
    "maximum_counts": {
      "admin_merge": 0,
      "autonomous_merge": 0,
      "force_push": 0
    },
    "required_events": [
      "campaign_bootstrapped",
      "lease_issued",
      "agent_deployed",
      "lease_acknowledged",
      "artifact_accepted",
      "lease_released"
    ],
    "required_sequence": [
      "campaign_bootstrapped",
      "lease_issued",
      "agent_deployed",
      "lease_acknowledged",
      "lease_released",
      "artifact_accepted"
    ],
    "schema_version": "1.0.0"
  }
}
"""
)


def load_policy(name: str) -> Any:
    try:
        return copy.deepcopy(_POLICIES[name])
    except KeyError as exc:
        raise KeyError(f"Unknown policy: {name}") from exc


def load_example(name: str) -> Any:
    try:
        return copy.deepcopy(_EXAMPLES[name])
    except KeyError as exc:
        raise KeyError(f"Unknown example: {name}") from exc


def load_golden_spec(name: str) -> Any:
    try:
        return copy.deepcopy(_GOLDEN[name])
    except KeyError as exc:
        raise KeyError(f"Unknown golden spec: {name}") from exc
