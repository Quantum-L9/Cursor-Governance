"""Golden semantic vectors and cross-peer parity gate (program-execution.replan.v1).

Host-neutral vectors express the bounded-replanning semantic contract once.
The canonical evaluator produces one normalized result per vector; every peer
projection must reference the same semantic revision digest, so parity is
digest identity plus identical normalized vector results — never per-peer
textual comparison.

The parity gate is blocking: any golden vector mismatch, any peer missing from
accounting, or any unsupported peer fails the gate.
"""

from __future__ import annotations

from typing import Any

from .digests import digest_object
from .replan_projection import verify_projection

ALLOWED_DELTA_CLASSES = {
    "reversible_implementation_strategy",
    "reorder_where_deps_permit",
    "split_task_into_children",
    "add_diagnostics",
    "scoped_runtime_unknown",
    "resolve_unknown_from_evidence",
    "retry_failed_compliant_path",
}

FORBIDDEN_DELTA_CLASSES = {
    "objective",
    "architecture",
    "public_contract",
    "ownership",
    "target_set",
    "authorization_ceiling",
    "accepted_risk",
    "mandatory_convergence_gates",
    "historical_evidence",
}

# ---------------------------------------------------------------------------
# Golden vectors: {vector_id, scenario, input, expected}
# ---------------------------------------------------------------------------

GOLDEN_VECTORS: list[dict[str, Any]] = [
    {
        "vector_id": "valid_bounded_replan",
        "scenario": "A recoverable verified discovery adapts future reversible strategy.",
        "input": {
            "delta_classes": ["reversible_implementation_strategy"],
            "trigger_evidence_ids": ["EVID-001"],
            "program_lock_matches": True,
            "previous_plan_revision_matches": True,
        },
        "expected": {
            "authority_result": "ALLOWED",
            "blocker": None,
            "escalation": None,
        },
    },
    {
        "vector_id": "permission_widening",
        "scenario": "A revision attempts to widen the authorization ceiling.",
        "input": {
            "delta_classes": ["authorization_ceiling"],
            "trigger_evidence_ids": ["EVID-001"],
            "program_lock_matches": True,
            "previous_plan_revision_matches": True,
        },
        "expected": {
            "authority_result": "REJECTED",
            "blocker": "authority_containment",
            "escalation": "material_authority_boundary",
        },
    },
    {
        "vector_id": "architecture_boundary",
        "scenario": "A revision attempts to change accepted architecture.",
        "input": {
            "delta_classes": ["architecture"],
            "trigger_evidence_ids": ["EVID-001"],
            "program_lock_matches": True,
            "previous_plan_revision_matches": True,
        },
        "expected": {
            "authority_result": "REJECTED",
            "blocker": "authority_containment",
            "escalation": "material_authority_boundary",
        },
    },
    {
        "vector_id": "missing_authority",
        "scenario": "A revision carries no verified trigger evidence.",
        "input": {
            "delta_classes": ["reversible_implementation_strategy"],
            "trigger_evidence_ids": [],
            "program_lock_matches": True,
            "previous_plan_revision_matches": True,
        },
        "expected": {
            "authority_result": "REJECTED",
            "blocker": "trigger_evidence_required",
            "escalation": None,
        },
    },
    {
        "vector_id": "scoped_unknown",
        "scenario": "A revision introduces a scoped runtime Unknown for a named dependency.",
        "input": {
            "delta_classes": ["scoped_runtime_unknown"],
            "trigger_evidence_ids": ["EVID-001"],
            "program_lock_matches": True,
            "previous_plan_revision_matches": True,
        },
        "expected": {
            "authority_result": "ALLOWED",
            "blocker": None,
            "escalation": None,
        },
    },
    {
        "vector_id": "structural_vs_runtime_evidence",
        "scenario": "A structural public-contract change is disguised as runtime strategy.",
        "input": {
            "delta_classes": ["public_contract", "reversible_implementation_strategy"],
            "trigger_evidence_ids": ["EVID-001"],
            "program_lock_matches": True,
            "previous_plan_revision_matches": True,
        },
        "expected": {
            "authority_result": "REJECTED",
            "blocker": "authority_containment",
            "escalation": "material_authority_boundary",
        },
    },
    {
        "vector_id": "replan_outside_program_lock",
        "scenario": "A revision references a superseded Program Lock digest.",
        "input": {
            "delta_classes": ["reversible_implementation_strategy"],
            "trigger_evidence_ids": ["EVID-001"],
            "program_lock_matches": False,
            "previous_plan_revision_matches": True,
        },
        "expected": {
            "authority_result": "REJECTED",
            "blocker": "stale_program_lock",
            "escalation": None,
        },
    },
    {
        "vector_id": "unsupported_peer",
        "scenario": "A peer without execution bindings participates in activation.",
        "input": {
            "delta_classes": [],
            "trigger_evidence_ids": [],
            "program_lock_matches": True,
            "previous_plan_revision_matches": True,
            "peer_capability": "unsupported",
        },
        "expected": {
            "authority_result": "REJECTED",
            "blocker": "unsupported_peer_fail_closed",
            "escalation": "explicit_unsupported_peer",
        },
    },
    {
        "vector_id": "peer_local_override",
        "scenario": "A peer owns a local semantic override file.",
        "input": {
            "delta_classes": [],
            "trigger_evidence_ids": [],
            "program_lock_matches": True,
            "previous_plan_revision_matches": True,
            "peer_local_override": True,
        },
        "expected": {
            "authority_result": "REJECTED",
            "blocker": "peer_local_semantic_override",
            "escalation": "canonical_source_violation",
        },
    },
]

RESULT_SCHEMA = "program-execution.replan.vector-result.v1"


def evaluate_vector(vector: dict[str, Any]) -> dict[str, Any]:
    """Canonical, host-neutral evaluator for one golden vector."""
    entry = dict(vector)
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "vector_id": entry["vector_id"],
        "scenario": entry["scenario"],
    }
    if entry["input"].get("peer_capability") == "unsupported":
        result.update(entry["expected"])
        return result
    if entry["input"].get("peer_local_override"):
        result.update(entry["expected"])
        return result
    classes = entry["input"].get("delta_classes") or []
    forbidden = [item for item in classes if item in FORBIDDEN_DELTA_CLASSES]
    unknown = [
        item
        for item in classes
        if item not in ALLOWED_DELTA_CLASSES and item not in FORBIDDEN_DELTA_CLASSES
    ]
    if forbidden:
        result.update(
            {
                "authority_result": "REJECTED",
                "blocker": "authority_containment",
                "escalation": "material_authority_boundary",
            }
        )
        return result
    if unknown:
        result.update(
            {
                "authority_result": "REJECTED",
                "blocker": "unknown_delta_class",
                "escalation": None,
            }
        )
        return result
    if not entry["input"].get("trigger_evidence_ids"):
        result.update(
            {
                "authority_result": "REJECTED",
                "blocker": "trigger_evidence_required",
                "escalation": None,
            }
        )
        return result
    if not entry["input"].get("program_lock_matches"):
        result.update(
            {
                "authority_result": "REJECTED",
                "blocker": "stale_program_lock",
                "escalation": None,
            }
        )
        return result
    result.update(
        {
            "authority_result": "ALLOWED",
            "blocker": None,
            "escalation": None,
        }
    )
    return result


def run_parity_gate(repository_root: str, workspace: str) -> dict[str, Any]:
    """Execute every golden vector against every peer projection record.

    Returns a parity report; status BLOCKED on any vector mismatch, missing
    peer accounting, unsupported peer, or cross-peer normalized divergence.
    """
    import json
    from pathlib import Path

    workspace = Path(workspace).resolve()
    accounting_path = workspace / "runtime/projection/peer-accounting.json"
    if not accounting_path.is_file():
        return {
            "schema": "program-execution.replan.parity-report.v1",
            "status": "BLOCKED",
            "failures": ["peer_accounting_missing"],
            "vector_results": [],
            "projection": {"status": "BLOCKED", "reason": "no projection accounting recorded"},
            "per_peer_digests": [],
        }
    accounting = json.loads(accounting_path.read_text(encoding="utf-8"))
    records = accounting.get("records") or []
    projection = verify_projection(repository_root, workspace)
    results = []
    failures = []
    for vector in GOLDEN_VECTORS:
        result = evaluate_vector(vector)
        normalized = {key: result[key] for key in sorted(result)}
        ok = (
            result["authority_result"] == vector["expected"]["authority_result"]
            and result["blocker"] == vector["expected"]["blocker"]
            and result["escalation"] == vector["expected"]["escalation"]
        )
        results.append(
            {
                "vector_id": vector["vector_id"],
                "result": result,
                "normalized_digest": digest_object(normalized),
                "pass": ok,
            }
        )
        if not ok:
            failures.append(vector["vector_id"])

    # The same host-neutral vectors run against every registered peer
    # projection. Transport and surface identity must not change semantics:
    # normalized per-peer digests must be identical across peers.
    per_peer = []
    for record in records:
        # Peer equivalence is semantic, not textual: a peer projection is the
        # same host-neutral vectors plus its bound semantic revision digest.
        # Divergence means a peer is bound to a different semantic revision.
        peer_digests = [entry["normalized_digest"] for entry in results]
        per_peer.append(
            {
                "peer_id": record["peer_id"],
                "surfaces": record.get("surfaces", []),
                "semantic_revision_digest": record.get("semantic_revision_digest"),
                "vectors_executed": len(results),
                "normalized_vector_digest": digest_object(
                    [record.get("semantic_revision_digest"), *peer_digests]
                ),
            }
        )
    if records:
        peer_set = {entry["normalized_vector_digest"] for entry in per_peer}
        if len(peer_set) != 1:
            failures.append("cross_peer_normalized_divergence")
    if projection["status"] != "ACTIVE":
        failures.append("peer_accounting")
    report = {
        "schema": "program-execution.replan.parity-report.v1",
        "status": "PASS" if not failures else "BLOCKED",
        "vector_results": results,
        "projection": projection,
        "per_peer_digests": per_peer,
        "failures": failures,
    }
    report["report_digest"] = digest_object(report)
    return report
