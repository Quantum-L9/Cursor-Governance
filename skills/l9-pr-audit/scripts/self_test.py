#!/usr/bin/env python3
"""Deterministic regression tests for l9-pr-audit's evidence and PR remediation handoff gates."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

# Running this file directly puts its own directory on sys.path; pytest
# collecting it (the name matches `*_test.py`) does not. Insert it explicitly
# so the sibling imports below resolve under both, as the previous revision of
# this pack did.
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import build_audit_bundle as bab  # noqa: E402
import build_change_ledger as bcl  # noqa: E402
import deterministic_closure as dc  # noqa: E402

# This is a standalone self-test driver, not a pytest suite; pytest must not
# collect its module-level helpers as tests.
__test__ = False

A = "a" * 40
B = "b" * 40
C = "c" * 40


def evidence(
    eid: str,
    etype: str,
    revision: str,
    fact: str,
    properties: list[str],
    findings: list[str] | None = None,
    **extra: object,
) -> dict[str, object]:
    item: dict[str, object] = {
        "evidence_id": eid,
        "evidence_type": etype,
        "epistemic_state": "CONFIRMED",
        "repository": "Quantum-L9/example",
        "revision": revision,
        "path_or_check": "synthetic",
        "locator": f"fixture:{eid}",
        "fact_proven": fact,
        "properties_discriminated": properties,
        "redaction_state": "NOT_APPLICABLE",
        "findings_using_this_evidence": findings or [],
    }
    item.update(extra)
    return item


def synthetic_change_ledger() -> dict[str, object]:
    snapshot = {
        "repository": "Quantum-L9/example",
        "pr_number": 1,
        "base_sha": A,
        "head_sha": B,
        "intent": {
            "source_kind": "REPOSITORY_LAW",
            "scope_patterns": ["src/**", "tests/**"],
            "objectives": [{"objective_id": "O1"}],
            "original_pr_prompt_available": False,
        },
        "files": [
            {
                "path": "src/core.py",
                "status": "modified",
                "additions": 3,
                "deletions": 2,
                "patch": "@@ -1,2 +1,2 @@\n-def core_rule(value):\n-    return False\n+def core_rule(value):\n+    return value == 1",
            },
            {
                "path": "tests/test_core.py",
                "status": "modified",
                "additions": 2,
                "deletions": 1,
                "patch": "@@ -1,2 +1,2 @@\n-def test_rule():\n+def test_rule():\n+    assert True",
            },
        ],
        "ci_failures": [{"name": "targeted-unit", "required": True, "conclusion": "failure"}],
        "review_threads": [],
    }
    return bcl.build(snapshot)


def sync_red_team(audit: dict[str, object]) -> None:
    claims = {item["claim_id"]: item for item in audit["claim_validation_matrix"]}
    objective_status = {
        item["objective_id"]: item for item in audit["change_discipline"]["objective_closure"]
    }
    domain_status = {item["domain"]: item for item in audit["audit_coverage"]["domain_assessments"]}
    pr_verdict = {item["pr_number"]: item for item in audit["per_pr_verdicts"]}
    symbols = {item["symbol_id"]: item for item in audit["changed_symbol_ledger"]}
    for claim in claims.values():
        finding_ids: list[str] = []
        if claim["claim_kind"] == "OBJECTIVE":
            row = objective_status[claim["subject"]]
            claim["status"] = {
                "SATISFIED": "SUPPORTED",
                "UNPROVEN": "UNKNOWN",
                "NOT_IMPLEMENTED": "REFUTED",
                "CONFLICTED": "REFUTED",
            }[row["status"]]
            finding_ids = list(row["finding_ids"])
        elif claim["claim_kind"] == "AUDIT_DOMAIN":
            row = domain_status[claim["subject"]]
            claim["status"] = {
                "PASS": "SUPPORTED",
                "FAIL": "REFUTED",
                "NOT_APPLICABLE": "NOT_APPLICABLE",
                "UNKNOWN": "UNKNOWN",
            }[row["status"]]
            finding_ids = list(row["finding_ids"])
        elif claim["claim_kind"] == "CHANGED_SYMBOL":
            sid = next(
                (
                    item.get("machine_symbol_id")
                    for item in synthetic_change_ledger()["claim_seeds"]
                    if item["claim_id"] == claim["claim_id"]
                ),
                None,
            )
            row = symbols[sid]
            finding_ids = list(row["finding_ids"])
            claim["status"] = (
                "REFUTED"
                if finding_ids
                else "UNKNOWN"
                if row["scope_disposition"] == "UNKNOWN"
                else "SUPPORTED"
            )
        elif claim["claim_kind"] == "READINESS":
            num = claim["pr_numbers"][0]
            state = pr_verdict[num]["merge_readiness"]
            claim["status"] = (
                "SUPPORTED"
                if state in bab.READY_STATES
                else "REFUTED"
                if state == "NOT_READY"
                else "UNKNOWN"
            )
            finding_ids = list(pr_verdict[num]["blocking_finding_ids"])
        elif claim["claim_kind"] == "CONVERGENCE":
            state = audit["executive_verdict"]["convergence_status"]
            claim["status"] = (
                "SUPPORTED"
                if state == "CONVERGED"
                else "REFUTED"
                if state == "NOT_CONVERGED"
                else "UNKNOWN"
            )
        claim["finding_ids"] = finding_ids
        if claim["status"] == "SUPPORTED":
            claim["validation_evidence_ids"] = ["E-RED"]
            claim["validation_properties"] = [f"claim_validation:{claim['claim_id']}"]
        else:
            claim["validation_evidence_ids"] = []
            claim["validation_properties"] = []
    for probe in audit["falsification_ledger"]:
        claim = claims[probe["claim_id"]]
        probe["result"] = {
            "SUPPORTED": "SURVIVED",
            "REFUTED": "FALSIFIED",
            "NOT_APPLICABLE": "NOT_APPLICABLE",
            "UNKNOWN": "INCONCLUSIVE",
        }[claim["status"]]
        probe["finding_ids"] = list(claim["finding_ids"]) if probe["result"] == "FALSIFIED" else []


def populate_v18_closures(audit: dict[str, object], ledger: dict[str, object]) -> None:
    rows: list[dict[str, object]] = []
    for seed in ledger.get("closure_seeds", []):
        kind = seed["closure_kind"]
        payload = seed["payload"]
        if kind == "DIFF_HUNK":
            core = payload.get("path") == "src/core.py"
            rows.append(
                {
                    "closure_id": seed["closure_id"],
                    "pr_number": seed["pr_number"],
                    "closure_kind": kind,
                    "subject": seed["subject"],
                    "source": "MACHINE_SEEDED",
                    "seed_hash": seed["seed_hash"],
                    "status": "FINDING" if core else "PASS",
                    "evidence_ids": ["E-FIND" if core else "E-TEST"],
                    "finding_ids": ["F1"] if core else [],
                    "details": {
                        "disposition": "FINDING" if core else "VALIDATION_REQUIRED",
                        "objective_ids": ["O1"],
                    },
                }
            )
        elif kind == "CI_CAUSALITY":
            rows.append(
                {
                    "closure_id": seed["closure_id"],
                    "pr_number": seed["pr_number"],
                    "closure_kind": kind,
                    "subject": seed["subject"],
                    "source": "MACHINE_SEEDED",
                    "seed_hash": seed["seed_hash"],
                    "status": "FINDING",
                    "evidence_ids": ["E-TEST"],
                    "finding_ids": ["F1"],
                    "details": {"causality": "PR_CAUSED"},
                }
            )
        else:
            raise AssertionError(f"unexpected synthetic v2.0 closure seed: {kind}")
    audit["deterministic_closure_ledger"] = rows
    audit["post_judgment_closure"] = {
        "root_cause_dominance": [],
        "severity_consistency": [
            {
                "finding_id": "F1",
                "machine_floor": "High",
                "machine_ceiling": "Critical",
                "actual_severity": "High",
                "status": "CONSISTENT",
                "evidence_ids": ["E-AUTH"],
            }
        ],
        "validation_run_coverage": [
            {
                "evidence_id": "E-TEST",
                "disposition": "JUSTIFIED_NON_CLOSING",
                "claim_ids": [],
                "rationale": "Finding closure and mandatory validation evidence; not used as a positive claim validator in this failing-head fixture.",
            }
        ],
    }


def base_audit() -> dict[str, object]:
    ledger = synthetic_change_ledger()
    machine_claim_ids = [item["claim_id"] for item in ledger["claim_seeds"]]
    red_properties = (
        [f"claim:{cid}" for cid in machine_claim_ids]
        + [f"claim_validation:{cid}" for cid in machine_claim_ids]
        + [f"falsification:{cid}" for cid in machine_claim_ids]
        + ["audit_convergence"]
    )
    shared = [
        evidence(
            "E-AUTH",
            "SOURCE",
            A,
            "canonical rule exists",
            [
                "authority_resolution",
                "merge_blocking_basis",
                "audit_domain:INTENT_SCOPE",
                "audit_domain:OWNERSHIP_AUTHORITY",
                "audit_domain:LEVERAGE_SIMPLICITY",
                "audit_domain:CHANGE_DISCIPLINE",
            ],
        ),
        evidence(
            "E-GUARD",
            "CONTRACT",
            A,
            "repository mutation guard resolved",
            ["mutation_guard_resolution"],
        ),
        evidence(
            "E-VCMD",
            "CONTRACT",
            A,
            "repository validation command is authoritative",
            ["validation_procedure"],
        ),
        evidence(
            "E-CHECK",
            "CONFIGURATION",
            B,
            "required check identity resolved",
            ["required_check_identity", "audit_domain:TESTING_VALIDATION"],
        ),
        evidence(
            "E-REVIEW",
            "REVIEW_THREAD",
            B,
            "zero unresolved review threads observed",
            ["review_thread_coverage"],
        ),
        evidence(
            "E-BYPASS",
            "DIFF",
            B,
            "diff inspected for weakening surfaces",
            ["anti_bypass_coverage"]
            + [f"anti_bypass:{kind}" for kind in sorted(bab.ANTI_BYPASS_KINDS)],
        ),
        evidence(
            "E-FIND",
            "DIFF",
            B,
            "src/core.py violates canonical rule",
            ["implementation_surface", "behavior_mismatch", "finding_origin"],
            ["F1"],
        ),
        evidence(
            "E-TEST",
            "TEST",
            B,
            "targeted test fails before remediation",
            ["closure_property", "mandatory_validation"],
            ["F1"],
            source_head_sha=B,
            tested_revision_sha=B,
            validation_result="FAIL",
            path_or_check="targeted-unit",
        ),
        evidence(
            "E-RED",
            "DIFF",
            B,
            "claim-specific validation and adversarial probes were executed against the synthetic fixture",
            red_properties,
        ),
    ]
    bypass_checks = [
        {"kind": kind, "status": "PASS", "evidence_ids": ["E-BYPASS"]}
        for kind in sorted(bab.ANTI_BYPASS_KINDS)
    ]
    audit = {
        "schema_version": bab.SCHEMA_VERSION,
        "audit_id": "audit.synthetic.v1",
        "generated_at": "2026-09-11T15:00:00Z",
        "repository_binding": {
            "repository": "Quantum-L9/example",
            "default_branch": "main",
            "audited_default_branch_sha": A,
        },
        "audit_coverage": {
            "status": "COMPLETE",
            "inspection_scope": ["PR #1 full diff", "directly coupled rule and test surfaces"],
            "excluded_or_inaccessible": [],
            "domain_assessments": [
                {
                    "domain": "INTENT_SCOPE",
                    "status": "FAIL",
                    "evidence_ids": ["E-AUTH"],
                    "finding_ids": ["F1"],
                    "closing_validation": None,
                },
                {
                    "domain": "COMMUNICATION_CONTRACTS",
                    "status": "NOT_APPLICABLE",
                    "evidence_ids": ["E-AUTH"],
                    "finding_ids": [],
                    "closing_validation": None,
                },
                {
                    "domain": "ROUTING_INTEGRATION",
                    "status": "NOT_APPLICABLE",
                    "evidence_ids": ["E-AUTH"],
                    "finding_ids": [],
                    "closing_validation": None,
                },
                {
                    "domain": "OWNERSHIP_AUTHORITY",
                    "status": "FAIL",
                    "evidence_ids": ["E-AUTH"],
                    "finding_ids": ["F1"],
                    "closing_validation": None,
                },
                {
                    "domain": "STRUCTURE_SOURCE_OF_TRUTH",
                    "status": "NOT_APPLICABLE",
                    "evidence_ids": ["E-AUTH"],
                    "finding_ids": [],
                    "closing_validation": None,
                },
                {
                    "domain": "SCHEMA_CONFIGURATION",
                    "status": "NOT_APPLICABLE",
                    "evidence_ids": ["E-AUTH"],
                    "finding_ids": [],
                    "closing_validation": None,
                },
                {
                    "domain": "SECURITY",
                    "status": "NOT_APPLICABLE",
                    "evidence_ids": ["E-AUTH"],
                    "finding_ids": [],
                    "closing_validation": None,
                },
                {
                    "domain": "RELIABILITY_OBSERVABILITY",
                    "status": "NOT_APPLICABLE",
                    "evidence_ids": ["E-AUTH"],
                    "finding_ids": [],
                    "closing_validation": None,
                },
                {
                    "domain": "TESTING_VALIDATION",
                    "status": "PASS",
                    "evidence_ids": ["E-CHECK"],
                    "finding_ids": [],
                    "closing_validation": None,
                },
                {
                    "domain": "LEVERAGE_SIMPLICITY",
                    "status": "PASS",
                    "evidence_ids": ["E-AUTH"],
                    "finding_ids": [],
                    "closing_validation": None,
                },
                {
                    "domain": "CROSS_PR",
                    "status": "NOT_APPLICABLE",
                    "evidence_ids": ["E-AUTH"],
                    "finding_ids": [],
                    "closing_validation": None,
                },
                {
                    "domain": "CHANGE_DISCIPLINE",
                    "status": "PASS",
                    "evidence_ids": ["E-AUTH"],
                    "finding_ids": [],
                    "closing_validation": None,
                },
            ],
            "artifact_inventory": [
                {
                    "artifact_id": "ART-LAW",
                    "path": "CANONICAL_LAW.md",
                    "revision": A,
                    "pr_numbers": [1],
                    "classification": "DOCUMENTATION",
                    "roles": ["AUTHORITY"],
                    "responsibility": "canonical behavior law",
                    "evidence_ids": ["E-AUTH"],
                },
                {
                    "artifact_id": "ART-GUARD",
                    "path": "ops/config/mutation-guard.json",
                    "revision": A,
                    "pr_numbers": [1],
                    "classification": "CONFIGURATION",
                    "roles": ["AUTHORITY"],
                    "responsibility": "mutation guard authority",
                    "evidence_ids": ["E-GUARD"],
                },
                {
                    "artifact_id": "ART-SRC",
                    "path": "src/core.py",
                    "revision": B,
                    "pr_numbers": [1],
                    "classification": "SOURCE",
                    "roles": ["CHANGED", "COUPLED"],
                    "responsibility": "core implementation",
                    "evidence_ids": ["E-FIND"],
                },
                {
                    "artifact_id": "ART-TEST",
                    "path": "tests/test_core.py",
                    "revision": B,
                    "pr_numbers": [1],
                    "classification": "TEST",
                    "roles": ["CHANGED", "VALIDATION", "COUPLED"],
                    "responsibility": "core behavior validation",
                    "evidence_ids": ["E-TEST"],
                },
            ],
        },
        "authority_resolution": {
            "status": "RESOLVED",
            "sources": [
                {
                    "authority_id": "A1",
                    "kind": "REPOSITORY_LAW",
                    "source": "CANONICAL_LAW.md",
                    "scope": "src/core.py behavior and validation",
                    "precedence": 1,
                    "evidence_ids": ["E-AUTH", "E-VCMD"],
                },
                {
                    "authority_id": "A-GUARD",
                    "kind": "MUTATION_GUARD",
                    "source": "ops/config/mutation-guard.json",
                    "scope": "repository mutation admissibility",
                    "precedence": 2,
                    "evidence_ids": ["E-GUARD"],
                },
            ],
            "conflicts": [],
        },
        "architecture_policy_adapters": {
            "status": "NOT_APPLICABLE",
            "adapters": [],
            "conflicts": [],
        },
        "boundary_map": {
            "status": "COMPLETE",
            "components": [
                {
                    "component_id": "core",
                    "responsibilities": ["canonical core behavior"],
                    "authority_ids": ["A1"],
                    "evidence_ids": ["E-AUTH"],
                },
                {
                    "component_id": "tests",
                    "responsibilities": ["behavior validation"],
                    "authority_ids": ["A1"],
                    "evidence_ids": ["E-TEST"],
                },
            ],
            "boundaries": [
                {
                    "boundary_id": "B-VALIDATION",
                    "kind": "VALIDATION",
                    "owner_component_id": "core",
                    "subject": "core behavior is validated by the canonical targeted test",
                    "participants": ["core", "tests"],
                    "authority_ids": ["A1"],
                    "evidence_ids": ["E-AUTH", "E-TEST"],
                }
            ],
        },
        "pr_bindings": [
            {
                "pr_number": 1,
                "url": "https://github.com/Quantum-L9/example/pull/1",
                "state": "open",
                "draft": False,
                "base_branch": "main",
                "base_sha": A,
                "head_branch": "feature",
                "head_sha": B,
                "mergeability": "MERGEABLE",
                "changed_files": [
                    {"path": "src/core.py", "status": "modified", "additions": 3, "deletions": 2},
                    {
                        "path": "tests/test_core.py",
                        "status": "modified",
                        "additions": 2,
                        "deletions": 1,
                    },
                ],
                "required_check_resolution": {
                    "status": "RESOLVED",
                    "checks": ["ci"],
                    "evidence_ids": ["E-CHECK"],
                },
                "review_thread_coverage": {
                    "unresolved_discovered": 0,
                    "classified": 0,
                    "unresolved_remaining": 0,
                    "status": "COMPLETE",
                    "evidence_ids": ["E-REVIEW"],
                },
            }
        ],
        "executive_verdict": {
            "audit_status": "SUCCEEDED",
            "readiness_status": "NOT_READY",
            "convergence_status": "CONVERGED",
            "summary": "One confirmed code defect blocks merge.",
            "minimum_safe_next_action": {
                "action": "Repair F1 within the strict write allowlist.",
                "rationale": "F1 is the only confirmed merge blocker.",
                "expected_evidence": "Targeted closure test passes on the resulting revision.",
            },
        },
        "per_pr_verdicts": [
            {
                "pr_number": 1,
                "completeness": "FAIL",
                "correctness": "FAIL",
                "architecture_alignment": "FAIL",
                "validation_sufficiency": "PASS",
                "mandatory_validation_evidence_ids": ["E-TEST"],
                "merge_readiness": "NOT_READY",
                "blocking_finding_ids": ["F1"],
                "blocking_unknown_ids": [],
            }
        ],
        "findings": [
            {
                "finding_id": "F1",
                "finding_class": "CORRECTNESS",
                "severity": "High",
                "confidence": "Confirmed",
                "affected_prs": [1],
                "repository_revision": A,
                "pr_head_bindings": [{"pr_number": 1, "head_sha": B}],
                "governing_authority": {
                    "authority_id": "A1",
                    "rule": "core behavior must satisfy the canonical contract",
                    "source": {"path": "CANONICAL_LAW.md"},
                    "enforcement_refs": ["tests/test_core.py"],
                },
                "ownership": {
                    "semantic_owner": "core",
                    "execution_owner": "fable-remediator",
                    "mutation_guard": "A-GUARD",
                    "remediation_owner_class": "CODEBASE",
                },
                "evidence_ids": ["E-FIND", "E-TEST"],
                "observed_behavior": "Current source violates the rule.",
                "expected_behavior": "Current source satisfies the rule.",
                "proof_of_mismatch": "Diff evidence plus targeted failing test proves the mismatch.",
                "impact": "Merge would ship incorrect behavior.",
                "root_cause": "The implementation takes the wrong branch.",
                "root_cause_state": "CONFIRMED",
                "behavioral_closure_condition": "The correct branch is selected for the governed input.",
                "closing_validation": [
                    {
                        "property": "closure_property",
                        "command_or_check": "python -m pytest tests/test_core.py -q",
                        "required_result": "PASS",
                        "execution_kind": "COMMAND",
                        "authority_id": "A1",
                        "evidence_ids": ["E-VCMD"],
                    }
                ],
                "origin": "PR_INTRODUCED",
                "origin_evidence_ids": ["E-FIND"],
                "merge_blocking_basis": {
                    "status": "BLOCKING",
                    "authority_id": "A1",
                    "rationale": "The canonical contract is violated on the PR head and the defect would ship if merged.",
                    "evidence_ids": ["E-AUTH", "E-FIND"],
                },
                "merge_blocking": True,
            }
        ],
        "shared_evidence_index": shared,
        "remediation_surface_index": [
            {
                "finding_id": "F1",
                "authoritative_surfaces": ["CANONICAL_LAW.md"],
                "implementation_surfaces": ["src/core.py"],
                "coupled_surfaces": ["tests/test_core.py"],
                "excluded_false_leads": [],
                "surface_evidence": [
                    {
                        "path": "src/core.py",
                        "role": "IMPLEMENTATION",
                        "evidence_ids": ["E-FIND"],
                        "reason": "Diff evidence locates the incorrect branch.",
                    }
                ],
            }
        ],
        "finding_dependency_graph": [
            {
                "finding_id": "F1",
                "depends_on_findings": [],
                "shared_root_cause": None,
                "affected_prs": [1],
                "remediation_order_class": "ROOT_CAUSE_FIRST",
            }
        ],
        "failed_check_evidence": [
            {
                "pr_number": 1,
                "source_head_sha": B,
                "tested_revision_sha": B,
                "check": "targeted-unit",
                "workflow_job": None,
                "failing_step": None,
                "failure_class": "CODEBASE",
                "local_reproducibility": "CONFIRMED",
                "local_reproduction_command": "python -m pytest tests/test_core.py -q",
                "evidence_ids": ["E-TEST"],
                "affected_finding_ids": ["F1"],
            }
        ],
        "regression_proof": [
            {
                "finding_id": "F1",
                "existing_regression_test": "tests/test_core.py::test_rule",
                "missing_negative_boundary": None,
                "reproduction_command": "python -m pytest tests/test_core.py -q",
                "pre_remediation_result": "FAIL",
                "expected_post_remediation_result": "PASS",
                "evidence_ids": ["E-TEST"],
            }
        ],
        "preservation_obligations": [],
        "anti_bypass_checks": [{"pr_number": 1, "checks": bypass_checks}],
        "cross_pr_evidence_pack": {
            "status": "NOT_APPLICABLE",
            "relationships": [],
            "merge_order": [],
        },
        "residual_unknowns": [],
        "combined_merge_readiness": "NOT_READY",
    }
    audit["intent_contract"] = {
        "status": "RESOLVED",
        "sources": [
            {
                "source_id": "I1",
                "kind": "REPOSITORY_LAW",
                "locator": "CANONICAL_LAW.md",
                "scope": "core behavior objective",
                "evidence_ids": ["E-AUTH"],
            }
        ],
        "objectives": [
            {
                "objective_id": "O1",
                "description": "Core behavior satisfies the canonical rule.",
                "source_ids": ["I1"],
                "status": "ACTIVE",
                "explicit_scope": ["src/core.py", "tests/test_core.py"],
                "explicit_non_goals": [],
                "acceptance_criteria": ["targeted validation passes"],
            }
        ],
        "original_pr_prompt": {
            "availability": "NOT_AVAILABLE",
            "source_id": None,
            "evidence_ids": [],
            "used_for": [],
        },
    }
    ledger_bytes = (json.dumps(ledger, indent=2, sort_keys=True) + "\n").encode("utf-8")
    audit["deterministic_census_binding"] = {
        "ledger_schema_version": bcl.SCHEMA,
        "generator_version": bcl.GENERATOR_VERSION,
        "ledger_bindings": [
            {"pr_number": 1, "head_sha": B, "ledger_sha256": bab.sha256_bytes(ledger_bytes)}
        ],
    }
    symbol_claim_by_machine_id = {
        item.get("machine_symbol_id"): item["claim_id"]
        for item in ledger["claim_seeds"]
        if item.get("machine_symbol_id")
    }
    audit["changed_symbol_ledger"] = []
    for item in ledger["changed_symbols"]:
        is_source = item["path"] == "src/core.py"
        audit["changed_symbol_ledger"].append(
            {
                "symbol_id": item["symbol_id"],
                "pr_number": item["pr_number"],
                "path": item["path"],
                "symbol_name": item["symbol_name"],
                "symbol_kind": item["symbol_kind"],
                "change_type": item["change_type"],
                "detection_method": item["detection_method"],
                "detection_confidence": item["detection_confidence"],
                "source": "MACHINE",
                "scope_disposition": "REQUIRED" if is_source else "VALIDATION_REQUIRED",
                "objective_ids": ["O1"],
                "evidence_ids": ["E-FIND"] if is_source else ["E-TEST"],
                "claim_ids": [symbol_claim_by_machine_id[item["symbol_id"]]],
                "finding_ids": ["F1"] if is_source else [],
            }
        )
    audit["claim_validation_matrix"] = []
    for seed in ledger["claim_seeds"]:
        audit["claim_validation_matrix"].append(
            {
                "claim_id": seed["claim_id"],
                "pr_numbers": [1],
                "claim_kind": seed["claim_kind"],
                "subject": seed["subject"],
                "assertion": seed["assertion"],
                "materiality": seed["materiality"],
                "source": seed["source"],
                "status": "UNKNOWN",
                "authority_ids": ["A1"],
                "evidence_ids": ["E-RED"],
                "validation_evidence_ids": [],
                "validation_properties": [],
                "finding_ids": [],
                "falsification_ids": [
                    item["falsification_id"]
                    for item in ledger["falsification_seeds"]
                    if item["claim_id"] == seed["claim_id"]
                ],
            }
        )
    audit["falsification_ledger"] = [
        {
            "falsification_id": seed["falsification_id"],
            "claim_id": seed["claim_id"],
            "source": seed["source"],
            "attack_class": seed["attack_class"],
            "hypothesis": seed["hypothesis"],
            "method": seed["suggested_method"],
            "execution_kind": "HYBRID",
            "result": "INCONCLUSIVE",
            "evidence_ids": ["E-RED"],
            "finding_ids": [],
            "judgment_required": True,
            "judgment_rationale": "The deterministic census enumerates the attack; semantic interpretation of whether the evidence defeats the claim requires bounded model judgment.",
        }
        for seed in ledger["falsification_seeds"]
    ]

    audit["change_discipline"] = {
        "objective_closure": [
            {
                "objective_id": "O1",
                "status": "NOT_IMPLEMENTED",
                "implementation_evidence_ids": ["E-FIND"],
                "validation_evidence_ids": ["E-TEST"],
                "finding_ids": ["F1"],
            }
        ],
        "scope_fidelity": {
            "changed_surfaces": [
                {
                    "pr_number": 1,
                    "path": "src/core.py",
                    "disposition": "REQUIRED",
                    "objective_ids": ["O1"],
                    "evidence_ids": ["E-FIND"],
                    "finding_ids": ["F1"],
                },
                {
                    "pr_number": 1,
                    "path": "tests/test_core.py",
                    "disposition": "VALIDATION_REQUIRED",
                    "objective_ids": ["O1"],
                    "evidence_ids": ["E-TEST"],
                    "finding_ids": [],
                },
            ]
        },
        "complexity_delta": [
            {
                "pr_number": 1,
                "files_added": 0,
                "files_deleted": 0,
                "files_modified": 2,
                "architectural_objects_added": 0,
                "dependencies_added": 0,
                "config_surfaces_added": 0,
                "execution_paths_added": 0,
                "evidence_ids": ["E-FIND"],
            }
        ],
        "architectural_economy": [],
        "supersession_closure": [],
        "failure_path_coverage": [],
        "test_discrimination": [
            {
                "test_obligation_id": "TD1",
                "pr_number": 1,
                "production_surface": "src/core.py",
                "test_surface": "tests/test_core.py",
                "status": "DISCRIMINATING",
                "objective_ids": ["O1"],
                "evidence_ids": ["E-TEST"],
                "finding_ids": [],
            }
        ],
        "control_adequacy": [
            {
                "control_id": "CA1",
                "pr_number": 1,
                "control_type": "VALIDATION",
                "requirement": "The canonical core behavior must have a discriminating validation control.",
                "status": "ADEQUATE",
                "boundary_ids": ["B-VALIDATION"],
                "evidence_ids": ["E-TEST"],
                "finding_ids": [],
            }
        ],
    }
    audit["audit_obligation_ledger"] = [
        {
            "obligation_id": "OB-O1",
            "pr_number": 1,
            "kind": "OBJECTIVE",
            "subject": "O1",
            "status": "FINDING",
            "evidence_ids": ["E-FIND"],
            "finding_ids": ["F1"],
        },
        {
            "obligation_id": "OB-S1",
            "pr_number": 1,
            "kind": "CHANGED_SURFACE",
            "subject": "src/core.py",
            "status": "FINDING",
            "evidence_ids": ["E-FIND"],
            "finding_ids": ["F1"],
        },
        {
            "obligation_id": "OB-S2",
            "pr_number": 1,
            "kind": "CHANGED_SURFACE",
            "subject": "tests/test_core.py",
            "status": "PASS",
            "evidence_ids": ["E-TEST"],
            "finding_ids": [],
        },
        {
            "obligation_id": "OB-T1",
            "pr_number": 1,
            "kind": "TEST_DISCRIMINATION",
            "subject": "TD1",
            "status": "PASS",
            "evidence_ids": ["E-TEST"],
            "finding_ids": [],
        },
        {
            "obligation_id": "OB-CA1",
            "pr_number": 1,
            "kind": "CONTROL_ADEQUACY",
            "subject": "CA1",
            "status": "PASS",
            "evidence_ids": ["E-TEST"],
            "finding_ids": [],
        },
        {
            "obligation_id": "OB-CI1",
            "pr_number": 1,
            "kind": "CI_FAILURE",
            "subject": "targeted-unit",
            "status": "FINDING",
            "evidence_ids": ["E-TEST"],
            "finding_ids": ["F1"],
        },
    ]
    for symbol in audit["changed_symbol_ledger"]:
        audit["audit_obligation_ledger"].append(
            {
                "obligation_id": f"OB-{symbol['symbol_id']}",
                "pr_number": 1,
                "kind": "CHANGED_SYMBOL",
                "subject": symbol["symbol_id"],
                "status": "FINDING" if symbol["finding_ids"] else "PASS",
                "evidence_ids": symbol["evidence_ids"],
                "finding_ids": symbol["finding_ids"],
            }
        )
    sync_red_team(audit)
    populate_v18_closures(audit, ledger)
    all_obligations = [item["obligation_id"] for item in audit["audit_obligation_ledger"]]
    all_claims = [item["claim_id"] for item in audit["claim_validation_matrix"]]
    all_falsifications = [item["falsification_id"] for item in audit["falsification_ledger"]]
    all_closures = [item["closure_id"] for item in audit["deterministic_closure_ledger"]]
    audit["audit_passes"] = [
        {
            "pass_number": 1,
            "pass_type": "DISCOVERY",
            "objective": "Bind exact scope, run deterministic census, and discover evidence-backed findings.",
            "evidence_ids": ["E-FIND", "E-TEST"],
            "observed_finding_ids": ["F1"],
            "observed_obligation_ids": all_obligations,
            "observed_claim_ids": all_claims,
            "observed_falsification_ids": all_falsifications,
            "observed_closure_ids": all_closures,
            "new_information_count": 6,
            "measurable_result": "One retained finding and six canonical obligations established.",
            "next_pass_objective": "Adversarially recheck every finding and obligation against exact current evidence.",
        },
        {
            "pass_number": 2,
            "pass_type": "VERIFICATION",
            "objective": "Recheck every final finding and obligation and search for contradictory or omitted evidence.",
            "evidence_ids": ["E-FIND", "E-TEST", "E-AUTH"],
            "observed_finding_ids": ["F1"],
            "observed_obligation_ids": all_obligations,
            "observed_claim_ids": all_claims,
            "observed_falsification_ids": all_falsifications,
            "observed_closure_ids": all_closures,
            "new_information_count": 0,
            "measurable_result": "No new material finding, obligation, or Unknown discovered; retained audit state reconfirmed.",
            "next_pass_objective": None,
        },
    ]
    return audit


def assert_has(errors: list[str], needle: str) -> None:
    if not any(needle in error for error in errors):
        raise AssertionError(f"expected error containing {needle!r}; got {errors}")


def main() -> int:
    script_root = Path(__file__).resolve().parent
    residue = sorted(
        str(path.relative_to(script_root.parent)) for path in script_root.parent.rglob("*.pyc")
    ) + sorted(
        str(path.relative_to(script_root.parent))
        for path in script_root.parent.rglob("__pycache__")
        if path.is_dir()
    )
    if residue:
        raise AssertionError(
            "skill tree contains bytecode/cache residue before validation: " + ", ".join(residue)
        )

    audit = base_audit()
    errors = bab.validate_audit(audit)
    if errors:
        raise AssertionError("positive fixture failed:\n" + "\n".join(errors))

    bad = copy.deepcopy(audit)
    bad["audit_coverage"]["artifact_inventory"] = [
        item
        for item in bad["audit_coverage"]["artifact_inventory"]
        if item["path"] != "src/core.py"
    ]
    assert_has(
        bab.validate_audit(bad),
        "src/core.py must appear exactly once as CHANGED in artifact_inventory",
    )

    bad = copy.deepcopy(audit)
    bad["audit_passes"] = bad["audit_passes"][:1]
    assert_has(bab.validate_audit(bad), "audit_passes")

    bad = copy.deepcopy(audit)
    bad["audit_passes"][-1]["new_information_count"] = 1
    assert_has(bab.validate_audit(bad), "new_information_count == 0")

    bad = copy.deepcopy(audit)
    bad["audit_passes"][-1]["observed_obligation_ids"] = bad["audit_passes"][-1][
        "observed_obligation_ids"
    ][:-1]
    assert_has(
        bab.validate_audit(bad), "final VERIFICATION pass must re-observe every audit obligation"
    )

    bad = copy.deepcopy(audit)
    bad["audit_passes"][-1]["observed_claim_ids"] = bad["audit_passes"][-1]["observed_claim_ids"][
        :-1
    ]
    assert_has(bab.validate_audit(bad), "final VERIFICATION pass must re-observe every claim")

    bad = copy.deepcopy(audit)
    bad["audit_passes"][-1]["observed_falsification_ids"] = bad["audit_passes"][-1][
        "observed_falsification_ids"
    ][:-1]
    assert_has(
        bab.validate_audit(bad), "final VERIFICATION pass must re-observe every falsification probe"
    )

    bad = copy.deepcopy(audit)
    supported = next(
        item
        for item in bad["claim_validation_matrix"]
        if item["status"] == "SUPPORTED" and item["materiality"] == "MATERIAL"
    )
    supported["falsification_ids"] = []
    assert_has(bab.validate_audit(bad), "requires a SURVIVED falsification probe")

    bad = copy.deepcopy(audit)
    probe = next(item for item in bad["falsification_ledger"] if item["result"] == "SURVIVED")
    probe["evidence_ids"] = ["E-AUTH"]
    assert_has(bab.validate_audit(bad), "lacks claim-specific discriminating evidence")

    bad = copy.deepcopy(audit)
    probe = bad["falsification_ledger"][0]
    probe["judgment_required"] = True
    probe["judgment_rationale"] = None
    assert_has(bab.validate_audit(bad), "judgment_required requires judgment_rationale")

    ledger = synthetic_change_ledger()
    ledger_bytes = (json.dumps(ledger, indent=2, sort_keys=True) + "\n").encode("utf-8")
    external_ledgers = {1: {"ledger": ledger, "sha256": bab.sha256_bytes(ledger_bytes)}}
    if bab.validate_audit(audit, change_ledgers=external_ledgers):
        raise AssertionError(
            "bound deterministic census fixture should validate:\n"
            + "\n".join(bab.validate_audit(audit, change_ledgers=external_ledgers))
        )

    bad = copy.deepcopy(audit)
    bad["changed_symbol_ledger"] = bad["changed_symbol_ledger"][:-1]
    assert_has(
        bab.validate_audit(bad, change_ledgers=external_ledgers),
        "machine changed-symbol ledger must exactly match deterministic census",
    )

    bad = copy.deepcopy(audit)
    seeded_claim_id = ledger["claim_seeds"][0]["claim_id"]
    bad["claim_validation_matrix"] = [
        item for item in bad["claim_validation_matrix"] if item["claim_id"] != seeded_claim_id
    ]
    assert_has(
        bab.validate_audit(bad, change_ledgers=external_ledgers),
        "claim matrix omitted deterministic claim seeds",
    )

    bad = copy.deepcopy(audit)
    seeded_fal_id = ledger["falsification_seeds"][0]["falsification_id"]
    bad["falsification_ledger"] = [
        item for item in bad["falsification_ledger"] if item["falsification_id"] != seeded_fal_id
    ]
    assert_has(
        bab.validate_audit(bad, change_ledgers=external_ledgers),
        "falsification ledger omitted deterministic seeds",
    )

    # v2.0 deterministic-closure regressions.
    bad = copy.deepcopy(audit)
    bad["audit_passes"][-1]["observed_closure_ids"] = bad["audit_passes"][-1][
        "observed_closure_ids"
    ][:-1]
    assert_has(
        bab.validate_audit(bad),
        "final VERIFICATION pass must re-observe every deterministic closure",
    )

    bad = copy.deepcopy(audit)
    bad["deterministic_closure_ledger"] = bad["deterministic_closure_ledger"][:-1]
    assert_has(
        bab.validate_audit(bad, change_ledgers=external_ledgers),
        "deterministic_closure_ledger missing machine seeds",
    )

    bad = copy.deepcopy(audit)
    bad["deterministic_closure_ledger"].append(
        {
            "closure_id": "C-PUBLIC",
            "pr_number": 1,
            "closure_kind": "PUBLIC_CONTRACT",
            "subject": "public-x",
            "source": "AUDITOR_ADDED",
            "seed_hash": None,
            "status": "PASS",
            "evidence_ids": ["E-AUTH"],
            "finding_ids": [],
            "details": {"disposition": "PRESERVED"},
        }
    )
    for ap in bad["audit_passes"]:
        ap["observed_closure_ids"] = list(dict.fromkeys(ap["observed_closure_ids"] + ["C-PUBLIC"]))
    assert_has(
        bab.validate_audit(bad), "public-contract delta requires preservation_obligation_ids"
    )

    bad = copy.deepcopy(audit)
    bad["deterministic_closure_ledger"].append(
        {
            "closure_id": "C-SSOT",
            "pr_number": 1,
            "closure_kind": "SSOT_UNIQUENESS",
            "subject": "ssot-x",
            "source": "AUDITOR_ADDED",
            "seed_hash": None,
            "status": "PASS",
            "evidence_ids": ["E-AUTH"],
            "finding_ids": [],
            "details": {"disposition": "COMPETING_AUTHORITY"},
        }
    )
    for ap in bad["audit_passes"]:
        ap["observed_closure_ids"] = list(dict.fromkeys(ap["observed_closure_ids"] + ["C-SSOT"]))
    assert_has(bab.validate_audit(bad), "competing authority requires finding")

    bad = copy.deepcopy(audit)
    bad["deterministic_closure_ledger"].append(
        {
            "closure_id": "C-BYPASS",
            "pr_number": 1,
            "closure_kind": "BYPASS_PATH",
            "subject": "bp-x",
            "source": "AUDITOR_ADDED",
            "seed_hash": None,
            "status": "PASS",
            "evidence_ids": ["E-AUTH"],
            "finding_ids": [],
            "details": {"disposition": "BYPASS_FINDING"},
        }
    )
    for ap in bad["audit_passes"]:
        ap["observed_closure_ids"] = list(dict.fromkeys(ap["observed_closure_ids"] + ["C-BYPASS"]))
    assert_has(bab.validate_audit(bad), "bypass finding requires finding")

    bad = copy.deepcopy(audit)
    bad["deterministic_closure_ledger"].append(
        {
            "closure_id": "C-SUP",
            "pr_number": 1,
            "closure_kind": "SUPERSESSION_LIVENESS",
            "subject": "sup-x",
            "source": "AUDITOR_ADDED",
            "seed_hash": None,
            "status": "PASS",
            "evidence_ids": ["E-AUTH"],
            "finding_ids": [],
            "details": {"classification": "LIVE"},
        }
    )
    for ap in bad["audit_passes"]:
        ap["observed_closure_ids"] = list(dict.fromkeys(ap["observed_closure_ids"] + ["C-SUP"]))
    assert_has(bab.validate_audit(bad), "LIVE supersession reference requires finding")

    bad = copy.deepcopy(audit)
    bad["deterministic_closure_ledger"].append(
        {
            "closure_id": "C-CFG",
            "pr_number": 1,
            "closure_kind": "CONFIG_PRECEDENCE",
            "subject": "cfg-x",
            "source": "AUDITOR_ADDED",
            "seed_hash": None,
            "status": "PASS",
            "evidence_ids": ["E-AUTH"],
            "finding_ids": [],
            "details": {"disposition": "SINGLE_WINNER", "winner_path": "config.yml"},
        }
    )
    for ap in bad["audit_passes"]:
        ap["observed_closure_ids"] = list(dict.fromkeys(ap["observed_closure_ids"] + ["C-CFG"]))
    assert_has(bab.validate_audit(bad), "winner_path must be a discovered source")

    bad = copy.deepcopy(audit)
    bad["deterministic_closure_ledger"].append(
        {
            "closure_id": "C-DEP",
            "pr_number": 1,
            "closure_kind": "DEPENDENCY_CAUSALITY",
            "subject": "dep-x",
            "source": "AUDITOR_ADDED",
            "seed_hash": None,
            "status": "FINDING",
            "evidence_ids": ["E-AUTH"],
            "finding_ids": [],
            "details": {"disposition": "UNJUSTIFIED"},
        }
    )
    for ap in bad["audit_passes"]:
        ap["observed_closure_ids"] = list(dict.fromkeys(ap["observed_closure_ids"] + ["C-DEP"]))
    assert_has(bab.validate_audit(bad), "FINDING requires finding_ids")

    bad = copy.deepcopy(audit)
    bad["deterministic_closure_ledger"].append(
        {
            "closure_id": "C-PAIR",
            "pr_number": 1,
            "closure_kind": "DEPENDENCY_PAIRING",
            "subject": "pair-x",
            "source": "AUDITOR_ADDED",
            "seed_hash": None,
            "status": "FINDING",
            "evidence_ids": ["E-AUTH"],
            "finding_ids": [],
            "details": {"disposition": "MISMATCH"},
        }
    )
    for ap in bad["audit_passes"]:
        ap["observed_closure_ids"] = list(dict.fromkeys(ap["observed_closure_ids"] + ["C-PAIR"]))
    assert_has(bab.validate_audit(bad), "FINDING requires finding_ids")

    bad = copy.deepcopy(audit)
    bad["deterministic_closure_ledger"].append(
        {
            "closure_id": "C-HUNK",
            "pr_number": 1,
            "closure_kind": "DIFF_HUNK",
            "subject": "hunk-x",
            "source": "AUDITOR_ADDED",
            "seed_hash": None,
            "status": "PASS",
            "evidence_ids": ["E-AUTH"],
            "finding_ids": [],
            "details": {"disposition": "REQUIRED", "objective_ids": []},
        }
    )
    for ap in bad["audit_passes"]:
        ap["observed_closure_ids"] = list(dict.fromkeys(ap["observed_closure_ids"] + ["C-HUNK"]))
    assert_has(bab.validate_audit(bad), "substantive hunk requires objective_ids")

    bad = copy.deepcopy(audit)
    bad["deterministic_closure_ledger"].append(
        {
            "closure_id": "C-CI",
            "pr_number": 1,
            "closure_kind": "CI_CAUSALITY",
            "subject": "ci-x",
            "source": "AUDITOR_ADDED",
            "seed_hash": None,
            "status": "PASS",
            "evidence_ids": ["E-AUTH"],
            "finding_ids": [],
            "details": {"causality": "PRE_EXISTING"},
        }
    )
    for ap in bad["audit_passes"]:
        ap["observed_closure_ids"] = list(dict.fromkeys(ap["observed_closure_ids"] + ["C-CI"]))
    assert_has(bab.validate_audit(bad), "requires ci_baseline evidence")

    bad = copy.deepcopy(audit)
    bad["deterministic_closure_ledger"].append(
        {
            "closure_id": "C-GEN",
            "pr_number": 1,
            "closure_kind": "GENERATED_PROVENANCE",
            "subject": "gen-x",
            "source": "AUDITOR_ADDED",
            "seed_hash": None,
            "status": "PASS",
            "evidence_ids": ["E-AUTH"],
            "finding_ids": [],
            "details": {"disposition": "MATCHED"},
        }
    )
    for ap in bad["audit_passes"]:
        ap["observed_closure_ids"] = list(dict.fromkeys(ap["observed_closure_ids"] + ["C-GEN"]))
    assert_has(
        bab.validate_audit(bad), "MATCHED generated provenance requires generator/source/command"
    )

    bad = copy.deepcopy(audit)
    bad["deterministic_closure_ledger"].append(
        {
            "closure_id": "C-ARCH",
            "pr_number": 1,
            "closure_kind": "ARCHITECTURE_ECONOMY",
            "subject": "arch-x",
            "source": "AUDITOR_ADDED",
            "seed_hash": None,
            "status": "PASS",
            "evidence_ids": ["E-AUTH"],
            "finding_ids": [],
            "details": {
                "justification_basis": "VERIFIED_PATTERN_EXTENSION",
                "objective_ids": [],
                "authority_ids": [],
            },
        }
    )
    for ap in bad["audit_passes"]:
        ap["observed_closure_ids"] = list(dict.fromkeys(ap["observed_closure_ids"] + ["C-ARCH"]))
    assert_has(
        bab.validate_audit(bad), "justified architecture requires objective_ids or authority_ids"
    )

    # v2.0 deterministic-closure seed census.
    v19_snapshot = {
        "repository": "Quantum-L9/example",
        "pr_number": 7,
        "base_sha": A,
        "head_sha": B,
        "repository_files_complete": True,
        "files": [
            {
                "path": "src/api.py",
                "status": "modified",
                "additions": 3,
                "deletions": 2,
                "base_content": "def public(x):\n    return x == 1\n",
                "head_content": "def public(x, y=0):\n    return x != 1\n",
                "patch": "@@ -1,2 +1,2 @@\n-def public(x):\n-    return x == 1\n+def public(x, y=0):\n+    return x != 1",
            },
            {
                "path": "src/new_adapter.py",
                "status": "added",
                "additions": 2,
                "deletions": 0,
                "head_content": "class NewAdapter:\n    pass\n",
                "patch": "@@ -0,0 +1,2 @@\n+class NewAdapter:\n+    pass",
            },
        ],
        "repository_files": [
            {"path": "src/api.py", "content": "def public(x, y=0):\n    return x != 1\n"},
            {
                "path": "src/consumer.py",
                "content": "from src.api import public\nvalue = public(1)\n",
            },
            {"path": "src/new_adapter.py", "content": "class NewAdapter:\n    pass\n"},
        ],
        "review_threads": [
            {
                "thread_id": "RT-7",
                "is_resolved": False,
                "author": "reviewer",
                "path": "src/api.py",
                "body": "Check compatibility",
            }
        ],
        "ci_failures": [],
    }
    v19_ledger = bcl.build(v19_snapshot)
    v19_kinds = [x["closure_kind"] for x in v19_ledger["closure_seeds"]]
    for expected_kind in (
        "PRODUCER_CONSUMER",
        "MUTATION_EXECUTION",
        "REVIEW_THREAD_SEMANTIC",
        "ORPHAN_ARTIFACT",
    ):
        if expected_kind not in v19_kinds:
            raise AssertionError(f"v2.0 census missing {expected_kind}")
    pc = [x for x in v19_ledger["closure_seeds"] if x["closure_kind"] == "PRODUCER_CONSUMER"]
    if not any(x["payload"].get("consumer_path") == "src/consumer.py" for x in pc):
        raise AssertionError("producer/consumer census failed to enumerate known consumer")
    muts = [x for x in v19_ledger["closure_seeds"] if x["closure_kind"] == "MUTATION_EXECUTION"]
    if not any(x["payload"].get("mutation_kind") == "COMPARE_OPERATOR_SWAP" for x in muts):
        raise AssertionError("mutation census failed to enumerate changed compare operator")
    orphans = [x for x in v19_ledger["closure_seeds"] if x["closure_kind"] == "ORPHAN_ARTIFACT"]
    if not any(
        x["payload"].get("path") == "src/new_adapter.py" and x["payload"].get("consumer_count") == 0
        for x in orphans
    ):
        raise AssertionError("orphan census failed to enumerate added unreferenced artifact")

    bad = copy.deepcopy(audit)
    bad["deterministic_closure_ledger"].append(
        {
            "closure_id": "C-PC",
            "pr_number": 1,
            "closure_kind": "PRODUCER_CONSUMER",
            "subject": "pc-x",
            "source": "AUDITOR_ADDED",
            "seed_hash": None,
            "status": "PASS",
            "evidence_ids": ["E-AUTH"],
            "finding_ids": [],
            "details": {"disposition": "MIGRATION_REQUIRED", "preservation_obligation_ids": []},
        }
    )
    for ap in bad["audit_passes"]:
        ap["observed_closure_ids"] = list(dict.fromkeys(ap["observed_closure_ids"] + ["C-PC"]))
    assert_has(
        bab.validate_audit(bad), "MIGRATION_REQUIRED requires finding or preservation obligation"
    )

    bad = copy.deepcopy(audit)
    bad["deterministic_closure_ledger"].append(
        {
            "closure_id": "C-MUT",
            "pr_number": 1,
            "closure_kind": "MUTATION_EXECUTION",
            "subject": "mut-x",
            "source": "AUDITOR_ADDED",
            "seed_hash": None,
            "status": "PASS",
            "evidence_ids": ["E-TEST"],
            "finding_ids": [],
            "details": {
                "result": "KILLED",
                "baseline_exit_code": 0,
                "mutant_exit_code": 0,
                "original_repository_unchanged": True,
            },
        }
    )
    for ap in bad["audit_passes"]:
        ap["observed_closure_ids"] = list(dict.fromkeys(ap["observed_closure_ids"] + ["C-MUT"]))
    assert_has(bab.validate_audit(bad), "KILLED requires baseline pass and mutant failure")

    bad = copy.deepcopy(audit)
    bad["deterministic_closure_ledger"].append(
        {
            "closure_id": "C-REV",
            "pr_number": 1,
            "closure_kind": "REVIEW_THREAD_SEMANTIC",
            "subject": "RT-X",
            "source": "AUDITOR_ADDED",
            "seed_hash": None,
            "status": "PASS",
            "evidence_ids": ["E-AUTH"],
            "finding_ids": [],
            "details": {"disposition": "FIXED_BY_FINDING"},
        }
    )
    for ap in bad["audit_passes"]:
        ap["observed_closure_ids"] = list(dict.fromkeys(ap["observed_closure_ids"] + ["C-REV"]))
    assert_has(bab.validate_audit(bad), "FIXED_BY_FINDING requires finding")

    bad = copy.deepcopy(audit)
    bad["deterministic_closure_ledger"].append(
        {
            "closure_id": "C-ORPH",
            "pr_number": 1,
            "closure_kind": "ORPHAN_ARTIFACT",
            "subject": "src/new.py",
            "source": "AUDITOR_ADDED",
            "seed_hash": None,
            "status": "FINDING",
            "evidence_ids": ["E-AUTH"],
            "finding_ids": [],
            "details": {"disposition": "ORPHAN"},
        }
    )
    for ap in bad["audit_passes"]:
        ap["observed_closure_ids"] = list(dict.fromkeys(ap["observed_closure_ids"] + ["C-ORPH"]))
    assert_has(bab.validate_audit(bad), "FINDING requires finding_ids")

    bad = copy.deepcopy(audit)
    bad["post_judgment_closure"]["severity_consistency"][0]["machine_floor"] = "Low"
    assert_has(bab.validate_audit(bad), "does not match deterministic bounds")

    bad = copy.deepcopy(audit)
    bad["post_judgment_closure"]["validation_run_coverage"] = []
    assert_has(bab.validate_audit(bad), "validation_run_coverage must exactly cover")

    bad = copy.deepcopy(audit)
    bad["post_judgment_closure"]["root_cause_dominance"] = [
        {
            "finding_a": "F1",
            "finding_b": "F1",
            "disposition": "INDEPENDENT",
            "evidence_ids": ["E-AUTH"],
        }
    ]
    assert_has(
        bab.validate_audit(bad), "root_cause_dominance must exactly cover machine candidate pairs"
    )

    # Enhanced symbol census and bypass token parsing are executable, not etiquette.
    rich = bcl.build(
        {
            "repository": "Quantum-L9/example",
            "pr_number": 2,
            "base_sha": A,
            "head_sha": B,
            "intent": {"objectives": [{"objective_id": "O2"}]},
            "files": [
                {
                    "path": "src/api.py",
                    "status": "modified",
                    "additions": 4,
                    "deletions": 3,
                    "base_content": "LIMIT = 1\ndef ping(x):\n    return x\n",
                    "head_content": "LIMIT = 2\n@app.get('/ping')\ndef ping(x, y=1):\n    return x+y\n",
                    "patch": "@@ -1,3 +1,4 @@\n-LIMIT = 1\n-def ping(x):\n-    return x\n+LIMIT = 2\n+@app.get('/ping')\n+def ping(x, y=1):\n+    return x+y",
                },
                {
                    "path": "config/app.yaml",
                    "status": "modified",
                    "additions": 1,
                    "deletions": 1,
                    "patch": "@@ -1 +1 @@\n-timeout: 1\n+timeout: 2",
                },
            ],
            "ci_failures": [],
            "review_threads": [],
        }
    )
    kinds = {x["symbol_kind"] for x in rich["changed_symbols"]}
    if not {"CONSTANT", "API_ROUTE", "CONFIG_KEY"}.issubset(kinds):
        raise AssertionError(f"enhanced changed-symbol census missing expected kinds: {kinds}")
    if dc.code_token_present("src/x.py", "# gateway\nvalue='gateway'\n", "gateway"):
        raise AssertionError(
            "Python comments/strings must not satisfy bypass boundary token presence"
        )

    handoff = bab.make_handoff(audit, autoremediate=0)
    unit = handoff["work_units"][0]
    assert unit["mutation_eligible"] is True
    assert unit["write_surfaces"] == ["src/core.py"]
    assert unit["governing_authority"]["authority_id"] == "A1"
    assert unit["observed_behavior"] == audit["findings"][0]["observed_behavior"]
    assert handoff["architecture_policy_adapters"]["status"] == "NOT_APPLICABLE"
    assert handoff["boundary_map"]["status"] == "COMPLETE"

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        audit_path = td_path / "audit.json"
        audit_path.write_text(json.dumps(audit), encoding="utf-8")
        ledger_path = td_path / "change-ledger-pr-1.json"
        ledger_path.write_text(
            json.dumps(synthetic_change_ledger(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        ledgers = bab.load_change_ledger_paths([ledger_path])
        zip_path = bab.build_bundle(audit_path, td_path / "out", ledgers)
        zip_path_2 = bab.build_bundle(audit_path, td_path / "out", ledgers)
        assert zip_path.name != zip_path_2.name
        assert zip_path.name.startswith("l9-pr-audit__example__pr-1__")
        assert zip_path.exists() and zip_path_2.exists()
        assert not bab.verify_zip(zip_path)
        with __import__("zipfile").ZipFile(zip_path) as zf:
            contract = zf.read("PR_REMEDIATION_CONTRACT.md").decode("utf-8")
            assert "SCOPE_EXTENSION_REQUIRED" in contract
            assert "scope_law:" in contract
            manifest = json.loads(zf.read("MANIFEST.json"))
            ledger_set = json.loads(zf.read("change-ledger.json"))
            assert ledger_set["schema_version"] == bab.CHANGE_LEDGER_SET_SCHEMA
            assert manifest["change_ledger_set_sha256"] == bab.sha256_bytes(
                zf.read("change-ledger.json")
            )
            assert manifest["autoremediate"] == 0
            assert handoff["autoremediate"] == 0
            assert handoff["publication"]["command"] == "make pr"
            assert handoff["publication"]["makefile_authority"] == "SSOT_MAKEFILE"
            assert handoff["publication"]["target_repository_makefile_authorized"] is False
            assert "invoke_make_pr_from_the_target_repository_Makefile" in contract
            assert "PUBLICATION_BLOCKED" in contract
            assert "primary_objective: RESOLVE_AUDIT_FINDINGS" in contract
            assert "ci_failures:" in contract
            assert "code_review_threads:" in contract
            assert "authorized: false" in contract
            assert "STOP_BEFORE_MERGE" in contract
            assert (
                handoff["convergence_requirements"]["primary_objective"] == "RESOLVE_AUDIT_FINDINGS"
            )
            assert handoff["convergence_requirements"]["merge_authorized"] is False
            assert set(handoff["convergence_requirements"]["additional_requirements"]) == {
                "RESOLVE_CURRENT_CI_FAILURES",
                "RESOLVE_ALL_CURRENT_CODE_REVIEW_THREADS",
            }
            assert handoff["publication"]["merge_authorized"] is False
            assert manifest["audit_schema_sha256"] == bab.sha256(bab.schema_path())
            assert manifest["canonical_audit_sha256"] == bab.sha256_bytes(zf.read("audit.json"))
            assert manifest["builder_sha256"] == bab.sha256(bab.builder_path())

        # Exact bundle membership is part of integrity: an injected extra file must fail verification.
        import zipfile

        extra_zip = td_path / "extra-file.zip"
        with (
            zipfile.ZipFile(zip_path, "r") as source,
            zipfile.ZipFile(extra_zip, "w", zipfile.ZIP_DEFLATED) as target,
        ):
            for name in source.namelist():
                target.writestr(name, source.read(name))
            target.writestr("UNDECLARED.txt", "not part of the bundle contract")
        assert_has(bab.verify_zip(extra_zip), "bundle file set mismatch")

        # A modified canonical audit must fail even when the ZIP remains readable.
        tampered_zip = td_path / "tampered-audit.zip"
        with (
            zipfile.ZipFile(zip_path, "r") as source,
            zipfile.ZipFile(tampered_zip, "w", zipfile.ZIP_DEFLATED) as target,
        ):
            for name in source.namelist():
                payload = source.read(name)
                if name == "audit.json":
                    tampered = json.loads(payload)
                    tampered["executive_verdict"]["summary"] = "tampered but structurally valid"
                    payload = (json.dumps(tampered, indent=2, sort_keys=True) + "\n").encode()
                target.writestr(name, payload)
        assert_has(bab.verify_zip(tampered_zip), "canonical_audit_sha256 mismatch")

        # Re-hashing a manually edited projection is not enough: projections are re-derived from canonical truth.
        projection_zip = td_path / "tampered-projection.zip"
        with zipfile.ZipFile(zip_path, "r") as source:
            payloads = {name: source.read(name) for name in source.namelist()}
        payloads["PR_REMEDIATION_CONTRACT.md"] += b"\nmanual drift\n"
        manifest = json.loads(payloads["MANIFEST.json"])
        manifest["files"]["PR_REMEDIATION_CONTRACT.md"] = {
            "sha256": bab.sha256_bytes(payloads["PR_REMEDIATION_CONTRACT.md"]),
            "bytes": len(payloads["PR_REMEDIATION_CONTRACT.md"]),
        }
        payloads["MANIFEST.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        with zipfile.ZipFile(projection_zip, "w", zipfile.ZIP_DEFLATED) as target:
            for name, payload in payloads.items():
                target.writestr(name, payload)
        assert_has(
            bab.verify_zip(projection_zip),
            "derived projection mismatch: PR_REMEDIATION_CONTRACT.md",
        )

        auto_zip = bab.build_bundle(audit_path, td_path / "auto", ledgers, autoremediate=1)
        assert not bab.verify_zip(auto_zip)
        with zipfile.ZipFile(auto_zip) as zf:
            auto_handoff = json.loads(zf.read("remediation-handoff.json"))
            auto_manifest = json.loads(zf.read("MANIFEST.json"))
            auto_contract = zf.read("PR_REMEDIATION_CONTRACT.md").decode("utf-8")
            assert auto_handoff["autoremediate"] == 1
            assert auto_manifest["autoremediate"] == 1
            assert "autoremediate: 1" in auto_contract

    # Deterministic change census enumerates facts/candidates before LLM judgment.
    snapshot = {
        "repository": "Quantum-L9/example",
        "pr_number": 1,
        "base_sha": A,
        "head_sha": B,
        "intent": {
            "source_kind": "ORIGINAL_PR_PROMPT",
            "original_pr_prompt_available": True,
            "scope_patterns": ["src/**", "tests/**"],
        },
        "files": [
            {
                "path": "src/core.py",
                "status": "modified",
                "additions": 6,
                "deletions": 1,
                "patch": "+++ b/src/core.py\n+class NewAdapter:\n+    pass\n+try:\n+    call()\n+except RuntimeError:\n+    raise",
            },
            {
                "path": "tests/test_core.py",
                "status": "deleted",
                "additions": 0,
                "deletions": 8,
                "patch": "",
            },
        ],
        "ci_failures": [{"name": "ci", "required": True, "conclusion": "failure"}],
        "review_threads": [{"thread_id": "RT1", "is_resolved": False, "author": "bot"}],
    }
    census = bcl.build(snapshot)
    kinds = {item["kind"] for item in census["obligations"]}
    assert {
        "CHANGED_SURFACE",
        "ARCHITECTURAL_GROWTH",
        "FAILURE_PATH",
        "TEST_DISCRIMINATION",
        "CI_FAILURE",
        "REVIEW_THREAD",
    }.issubset(kinds)
    candidate_kinds = {item["kind"] for item in census["deterministic_candidates"]}
    assert "NEW_ADAPTER" in candidate_kinds
    assert "DELETED_TEST" in candidate_kinds
    assert census["original_pr_prompt_available"] is True

    bad = copy.deepcopy(audit)
    bad["unexpected"] = True
    assert_has(bab.validate_audit(bad), "Additional properties are not allowed")

    # Canonical domain outcomes are closed-world and evidence-backed.
    bad = copy.deepcopy(audit)
    bad["audit_coverage"]["domain_assessments"] = bad["audit_coverage"]["domain_assessments"][:-1]
    assert_has(bab.validate_audit(bad), "domain_assessments")

    bad = copy.deepcopy(audit)
    for item in bad["shared_evidence_index"]:
        if item["evidence_id"] == "E-AUTH":
            item["properties_discriminated"] = [
                p for p in item["properties_discriminated"] if p != "audit_domain:INTENT_SCOPE"
            ]
    assert_has(bab.validate_audit(bad), "audit_domain:INTENT_SCOPE")

    # Architecture-policy adapter law must be explicitly authoritative and scoped.
    bad = copy.deepcopy(audit)
    bad["architecture_policy_adapters"] = {
        "status": "RESOLVED",
        "adapters": [
            {
                "adapter_id": "P1",
                "name": "synthetic policy",
                "revision": "r1",
                "status": "APPLIED",
                "governing_authority_ids": ["MISSING"],
                "scope": ["src/core.py"],
                "rule_domains": ["OWNERSHIP_AUTHORITY"],
                "validation_methods": ["manual inspection"],
                "evidence_ids": ["E-AUTH"],
            }
        ],
        "conflicts": [],
    }
    assert_has(bab.validate_audit(bad), "architecture adapter P1 references unknown authority")

    # Semantic ownership must resolve through the canonical boundary map.
    bad = copy.deepcopy(audit)
    bad["findings"][0]["ownership"]["semantic_owner"] = "ghost-owner"
    assert_has(bab.validate_audit(bad), "absent from boundary_map.components")

    bad = copy.deepcopy(audit)
    bad["boundary_map"]["boundaries"][0]["owner_component_id"] = "ghost-owner"
    assert_has(bab.validate_audit(bad), "references unknown owner component")

    # Merge-blocking is an evidence-backed policy/risk decision, not severity rhetoric.
    bad = copy.deepcopy(audit)
    bad["findings"][0]["merge_blocking_basis"]["evidence_ids"] = ["E-FIND"]
    assert_has(bab.validate_audit(bad), "blocking basis lacks merge_blocking_basis evidence")

    bad = copy.deepcopy(audit)
    bad["findings"][0]["origin"] = "PRE_EXISTING"
    assert_has(bab.validate_audit(bad), "pre-existing finding F1 cannot block merge")

    bad = copy.deepcopy(audit)
    bad["findings"][0]["origin_evidence_ids"] = ["E-AUTH"]
    assert_has(bab.validate_audit(bad), "lacks finding_origin discriminating evidence")

    bad = copy.deepcopy(audit)
    bad["change_discipline"]["control_adequacy"][0]["boundary_ids"] = []
    assert_has(
        bab.validate_audit(bad), "control_adequacy must cover every material control boundary"
    )

    preexisting = copy.deepcopy(audit)
    preexisting["findings"][0]["origin"] = "PRE_EXISTING"
    preexisting["shared_evidence_index"][0]["properties_discriminated"].append(
        "pre_existing_blocking_relevance"
    )
    if bab.validate_audit(preexisting):
        raise AssertionError(
            "pre-existing fixture should be valid when blocking relevance is proven:\n"
            + "\n".join(bab.validate_audit(preexisting))
        )
    unit = bab.make_handoff(preexisting)["work_units"][0]
    assert unit["mutation_eligible"] is False
    assert "origin=PRE_EXISTING_requires_separate_authority" in unit["mutation_block_reasons"]

    # Underbuilt required controls must become explicit findings and obligations.
    bad = copy.deepcopy(audit)
    bad["change_discipline"]["control_adequacy"][0]["status"] = "UNDERBUILT"
    bad["change_discipline"]["control_adequacy"][0]["finding_ids"] = []
    assert_has(bab.validate_audit(bad), "UNDERBUILT requires finding_ids")

    bad = copy.deepcopy(audit)
    bad["change_discipline"]["scope_fidelity"]["changed_surfaces"] = bad["change_discipline"][
        "scope_fidelity"
    ]["changed_surfaces"][:-1]
    assert_has(
        bab.validate_audit(bad), "scope_fidelity must disposition every changed file exactly once"
    )

    bad = copy.deepcopy(audit)
    bad["audit_obligation_ledger"] = [
        o
        for o in bad["audit_obligation_ledger"]
        if not (o["kind"] == "CHANGED_SURFACE" and o["subject"] == "tests/test_core.py")
    ]
    assert_has(
        bab.validate_audit(bad), "CHANGED_SURFACE obligations must exactly match changed_files"
    )

    bad = copy.deepcopy(audit)
    bad["change_discipline"]["objective_closure"] = []
    assert_has(bab.validate_audit(bad), "objective_closure")

    bad = copy.deepcopy(audit)
    bad["pr_bindings"][0]["required_check_resolution"]["evidence_ids"] = []
    assert_has(
        bab.validate_audit(bad),
        "required_check_resolution status RESOLVED requires CONFIRMED evidence",
    )

    bad = copy.deepcopy(audit)
    bad["remediation_surface_index"][0]["surface_evidence"] = []
    assert_has(bab.validate_audit(bad), "lacks IMPLEMENTATION surface_evidence")

    probable = copy.deepcopy(audit)
    probable["findings"][0]["confidence"] = "Probable"
    probable["findings"][0]["root_cause_state"] = "INFERENCE"
    unit = bab.make_handoff(probable)["work_units"][0]
    assert unit["mutation_eligible"] is False
    assert not unit["write_surfaces"]
    assert "confidence=Probable" in unit["mutation_block_reasons"]

    secret = copy.deepcopy(audit)
    secret["findings"][0]["impact"] = "api_key=abcdefghijklmnopqrstuvwx"
    assert_has(bab.validate_audit(secret), "high-confidence secret material")
    # Claim/evidence fit: confirmed evidence must discriminate the exact property it authorizes.
    bad = copy.deepcopy(audit)
    for item in bad["shared_evidence_index"]:
        if item["evidence_id"] == "E-FIND":
            item["properties_discriminated"] = ["behavior_mismatch"]
    assert_has(bab.validate_audit(bad), "lacks evidence that discriminates implementation_surface")

    bad = copy.deepcopy(audit)
    for item in bad["shared_evidence_index"]:
        if item["evidence_id"] == "E-VCMD":
            item["properties_discriminated"] = ["authority_resolution"]
    assert_has(
        bab.validate_audit(bad), "closing validation lacks validation_procedure provenance evidence"
    )

    bad = copy.deepcopy(audit)
    for item in bad["shared_evidence_index"]:
        if item["evidence_id"] == "E-BYPASS":
            item["properties_discriminated"] = ["anti_bypass_coverage"]
    assert_has(bab.validate_audit(bad), "lacks claim-specific discriminating evidence")

    # Mutation guard must resolve through an admitted mutation-guard authority.
    bad_guard = copy.deepcopy(audit)
    bad_guard["findings"][0]["ownership"]["mutation_guard"] = "UNKNOWN"
    assert_has(
        bab.validate_audit(bad_guard),
        "mutation_guard must be NOT_APPLICABLE or a known authority_id",
    )
    unit = bab.make_handoff(bad_guard)["work_units"][0]
    assert unit["mutation_eligible"] is False
    assert "mutation_guard_unresolved" in unit["mutation_block_reasons"]

    # COMPLETE coverage and RESOLVED authority cannot conceal blocking gaps.
    bad = copy.deepcopy(audit)
    bad["audit_coverage"]["excluded_or_inaccessible"] = [
        {"surface": "protected/runtime", "reason": "unavailable", "impact": "BLOCKS_READINESS"}
    ]
    assert_has(bab.validate_audit(bad), "COMPLETE cannot contain blocking exclusions")

    bad = copy.deepcopy(audit)
    bad["authority_resolution"]["conflicts"] = [
        {
            "description": "two owners conflict",
            "authority_ids": ["A1", "A-GUARD"],
            "status": "BLOCKING",
        }
    ]
    assert_has(bab.validate_audit(bad), "RESOLVED cannot retain UNKNOWN/BLOCKING conflicts")

    # Convergence-blocking Unknowns cannot coexist with CONVERGED.
    bad = copy.deepcopy(audit)
    bad["residual_unknowns"] = [
        {
            "unknown_id": "U1",
            "description": "consumer behavior unavailable",
            "affected_prs": [1],
            "affected_conclusion": "cross-boundary correctness",
            "blocks_readiness": False,
            "blocks_convergence": True,
            "evidence_needed": "consumer contract",
            "owner_class": "HUMAN",
        }
    ]
    assert_has(
        bab.validate_audit(bad), "CONVERGED cannot retain convergence-blocking residual Unknowns"
    )

    # A READY state must be backed by exact green mandatory evidence and mergeable non-draft state.
    ready = copy.deepcopy(audit)
    ready["findings"][0]["merge_blocking"] = False
    ready["findings"][0]["merge_blocking_basis"] = {
        "status": "NON_BLOCKING",
        "authority_id": "A1",
        "rationale": "Synthetic ready-state fixture removes the blocker after closure.",
        "evidence_ids": ["E-AUTH"],
    }
    ready["per_pr_verdicts"][0]["blocking_finding_ids"] = []
    ready["per_pr_verdicts"][0]["merge_readiness"] = "READY"
    ready["combined_merge_readiness"] = "READY"
    ready["executive_verdict"]["readiness_status"] = "READY"
    ready["shared_evidence_index"].append(
        evidence(
            "E-CI",
            "CI",
            B,
            "required ci check passed",
            ["mandatory_validation", "required_check_result"],
            source_head_sha=B,
            tested_revision_sha=C,
            validation_result="PASS",
            path_or_check="ci",
        )
    )
    ready["per_pr_verdicts"][0]["mandatory_validation_evidence_ids"] = ["E-CI"]
    ready["change_discipline"]["objective_closure"][0]["status"] = "SATISFIED"
    for domain in ready["audit_coverage"]["domain_assessments"]:
        if domain["status"] == "FAIL":
            domain["status"] = "PASS"
            domain["finding_ids"] = []
    for obligation in ready["audit_obligation_ledger"]:
        if obligation["status"] == "FINDING":
            obligation["status"] = "PASS"
            obligation["finding_ids"] = []
    for symbol in ready["changed_symbol_ledger"]:
        symbol["finding_ids"] = []
    sync_red_team(ready)
    ready["post_judgment_closure"]["severity_consistency"][0].update(
        {
            "machine_floor": "Low",
            "machine_ceiling": "High",
            "actual_severity": "High",
            "status": "CONSISTENT",
        }
    )
    ready["post_judgment_closure"]["validation_run_coverage"].append(
        {
            "evidence_id": "E-CI",
            "disposition": "JUSTIFIED_NON_CLOSING",
            "claim_ids": [],
            "rationale": "Required-check PASS evidence supports readiness gates directly; the red-team claim validator remains E-RED in this synthetic fixture.",
        }
    )
    if bab.validate_audit(ready):
        raise AssertionError(
            "ready fixture should validate:\n" + "\n".join(bab.validate_audit(ready))
        )

    bad = copy.deepcopy(ready)
    bad["pr_bindings"][0]["draft"] = True
    assert_has(bab.validate_audit(bad), "while draft=true")

    bad = copy.deepcopy(ready)
    bad["pr_bindings"][0]["mergeability"] = "UNKNOWN"
    assert_has(bab.validate_audit(bad), "unless mergeability is MERGEABLE")

    bad = copy.deepcopy(ready)
    for item in bad["shared_evidence_index"]:
        if item["evidence_id"] == "E-CI":
            item["validation_result"] = "FAIL"
    assert_has(bab.validate_audit(bad), "required check 'ci' lacks CONFIRMED PASS evidence")

    bad = copy.deepcopy(ready)
    bad["pr_bindings"][0]["review_thread_coverage"]["unresolved_remaining"] = 1
    assert_has(bab.validate_audit(bad), "unresolved review threads remaining")

    # A redaction token must not blind the secret tripwire to another live token in the same string.
    secret = copy.deepcopy(audit)
    secret["findings"][0]["impact"] = "REDACTED note; api_key=abcdefghijklmnopqrstuvwx"
    assert_has(bab.validate_audit(secret), "high-confidence secret material")

    cycle = copy.deepcopy(audit)
    f2 = copy.deepcopy(cycle["findings"][0])
    f2["finding_id"] = "F2"
    f2["evidence_ids"] = ["E-FIND2"]
    cycle["findings"].append(f2)
    cycle["shared_evidence_index"].append(
        evidence("E-FIND2", "DIFF", B, "second coupled defect", ["implementation_surface"], ["F2"])
    )
    cycle["audit_coverage"]["artifact_inventory"].append(
        {
            "artifact_id": "ART-SRC2",
            "path": "src/other.py",
            "revision": B,
            "pr_numbers": [1],
            "classification": "SOURCE",
            "roles": ["COUPLED"],
            "responsibility": "second coupled implementation surface",
            "evidence_ids": ["E-FIND2"],
        }
    )
    for audit_pass in cycle["audit_passes"]:
        if "F2" not in audit_pass["observed_finding_ids"]:
            audit_pass["observed_finding_ids"].append("F2")
    cycle["remediation_surface_index"].append(
        {
            "finding_id": "F2",
            "authoritative_surfaces": ["CANONICAL_LAW.md"],
            "implementation_surfaces": ["src/other.py"],
            "coupled_surfaces": [],
            "excluded_false_leads": [],
            "surface_evidence": [
                {
                    "path": "src/other.py",
                    "role": "IMPLEMENTATION",
                    "evidence_ids": ["E-FIND2"],
                    "reason": "Synthetic confirmed location.",
                }
            ],
        }
    )
    cycle["finding_dependency_graph"] = [
        {
            "finding_id": "F1",
            "depends_on_findings": ["F2"],
            "shared_root_cause": "R1",
            "affected_prs": [1],
            "remediation_order_class": "DEPENDENT",
        },
        {
            "finding_id": "F2",
            "depends_on_findings": ["F1"],
            "shared_root_cause": "R1",
            "affected_prs": [1],
            "remediation_order_class": "DEPENDENT",
        },
    ]
    cycle["per_pr_verdicts"][0]["blocking_finding_ids"] = ["F1", "F2"]
    cycle["executive_verdict"]["audit_status"] = "PARTIALLY_SUCCEEDED"
    cycle["executive_verdict"]["convergence_status"] = "NOT_CONVERGED"
    cycle["post_judgment_closure"]["severity_consistency"].append(
        {
            "finding_id": "F2",
            "machine_floor": "High",
            "machine_ceiling": "Critical",
            "actual_severity": "High",
            "status": "CONSISTENT",
            "evidence_ids": ["E-AUTH"],
        }
    )
    sync_red_team(cycle)
    errors = bab.validate_audit(cycle)
    if errors:
        raise AssertionError(
            "cycle fixture should be representable as non-converged:\n" + "\n".join(errors)
        )
    units = bab.make_handoff(cycle)["work_units"]
    assert all(not unit["mutation_eligible"] for unit in units)
    assert set(bab.make_handoff(cycle)["dependency_blocked_findings"]) == {"F1", "F2"}

    # Mutation executor v2.0: fail closed, no implicit shell, structured outcomes, and truthful exit status.
    with tempfile.TemporaryDirectory(prefix="l9-pr-audit-mut-selftest-") as td:
        mut_root = Path(td)
        repo = mut_root / "repo"
        repo.mkdir()
        source = repo / "a.py"
        source.write_text("def flag(x):\n    return x == 1\n", encoding="utf-8")
        src = source.read_text(encoding="utf-8")
        line_text = src.splitlines()[1]
        col = line_text.index("==")
        candidate = {
            "mutation_id": "MUT-SELFTEST",
            "path": "a.py",
            "line": 2,
            "column": col,
            "end_line": 2,
            "end_column": col + 2,
            "original_source": "==",
            "mutant_source": "!=",
            "source_sha256": hashlib.sha256(src.encode()).hexdigest(),
        }
        candidate_path = mut_root / "candidate.json"
        candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
        executor = script_root / "execute_mutation_probe.py"

        def run_probe(
            command: str, *, timeout: int = 10, output: Path | None = None
        ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
            argv = [
                sys.executable,
                str(executor),
                "--repo-root",
                str(repo),
                "--candidate",
                str(candidate_path),
                "--test-command",
                command,
                "--timeout",
                str(timeout),
            ]
            if output is not None:
                argv += ["--output", str(output)]
            cp = subprocess.run(argv, text=True, capture_output=True, check=False)
            payload = json.loads(
                output.read_text(encoding="utf-8") if output is not None else cp.stdout
            )
            return cp, payload

        killed_cp, killed = run_probe("python -c 'import a; assert a.flag(1)'")
        assert killed_cp.returncode == 0 and killed["result"] == "KILLED"
        assert killed["execution_mode"] == "ARGV_NO_SHELL"
        assert killed["original_repository_unchanged"] is True

        nested_output = mut_root / "nested" / "survived.json"
        survived_cp, survived = run_probe("python -c 'import a; assert True'", output=nested_output)
        assert survived_cp.returncode == 1 and survived["result"] == "SURVIVED"
        assert nested_output.is_file()

        baseline_cp, baseline = run_probe("python -c 'raise SystemExit(3)'")
        assert baseline_cp.returncode == 2 and baseline["result"] == "BASELINE_FAILED"

        marker = repo / "SHOULD_NOT_EXIST"
        shellish_cp, shellish = run_probe(
            "python -c 'import a; assert True' ; touch SHOULD_NOT_EXIST"
        )
        assert shellish_cp.returncode == 1 and shellish["result"] == "SURVIVED"
        assert not marker.exists(), (
            "implicit shell execution created a marker in the audited repository"
        )

        timeout_cp, timeout_result = run_probe("python -c 'import time; time.sleep(2)'", timeout=1)
        assert timeout_cp.returncode == 2 and timeout_result["result"] == "BASELINE_FAILED"
        assert timeout_result["baseline"]["timed_out"] is True

    residue_after = [str(path) for path in script_root.parent.rglob("*.pyc")] + [
        str(path) for path in script_root.parent.rglob("__pycache__") if path.is_dir()
    ]
    if residue_after:
        raise AssertionError(
            "validation created bytecode/cache residue: " + ", ".join(sorted(residue_after))
        )
    print("PASS: l9-pr-audit self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
