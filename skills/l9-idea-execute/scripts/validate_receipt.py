#!/usr/bin/env python3
from __future__ import annotations

import sys
from typing import Any

from _common import ContractError, load_data, nonempty_string, require_mapping, semantic_digest
from validate_envelope import validate_envelope
from validate_graph import validate_graph

SCHEMA = "l9.idea-execution-receipt/v1"

# States that explicitly do NOT claim a downstream owner ran. Everything else is read as
# a terminal completion claim and must join to canonical downstream receipt/state
# evidence, so an unrecognized or invented state fails closed instead of passing as
# "not really a claim". Keep this the declared failure/reason vocabulary only.
NON_COMPLETION_STATES = frozenset(
    {
        # declared skill failure states
        "IDEAOS_DECISION_REQUIRED",
        "ENVELOPE_INVALID",
        "CAPABILITY_OWNER_UNKNOWN",
        "EXECUTION_TOPOLOGY_UNSUPPORTED",
        "ADAPTER_CONTRACT_UNAVAILABLE",
        "EXECUTOR_CAPABILITY_GAP",
        "OWNER_NATIVE_INPUT_INVALID",
        "DOWNSTREAM_EXECUTION_FAILED",
        "DOWNSTREAM_RECEIPT_INVALID",
        "PROTECTED_ACTION_REQUIRES_AUTHORITY",
        # canonical reconciliation reason codes
        "DERIVED_ARTIFACT_STALE",
        "PARENT_DIGEST_MISMATCH",
        "SOURCE_REVISION_CHANGED",
        "GRAPH_REQUIREMENT_COVERAGE_MISMATCH",
        "ADAPTER_SNAPSHOT_INVALID",
        "ADAPTER_SNAPSHOT_STALE",
        "ADAPTER_CONTRACT_CONFLICT",
        "ADAPTER_CAPABILITY_UNKNOWN",
        # explicit not-run / not-yet-invoked representations
        "NOT_RUN",
        "PENDING",
        "PENDING_HANDOFF",
        "BLOCKED",
        "SKIPPED",
        "NOT_APPLICABLE",
    }
)


def _claims_completion(state: Any) -> bool:
    return nonempty_string(state) and state.strip().upper() not in NON_COMPLETION_STATES


def _validate_reconciliation(value: Any, errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append("reconciliation must be a mapping")
        return
    for bucket in ("reused", "regenerated", "superseded"):
        items = value.get(bucket, [])
        if not isinstance(items, list):
            errors.append(f"reconciliation.{bucket} must be a list")
            continue
        for idx, item in enumerate(items):
            label = f"reconciliation.{bucket}[{idx}]"
            if not isinstance(item, dict):
                errors.append(f"{label} must be a mapping")
                continue
            if not nonempty_string(item.get("ref")):
                errors.append(f"{label}.ref must be a non-empty string")
            if not nonempty_string(item.get("reason")):
                errors.append(f"{label}.reason must be a non-empty string")
            replacement = item.get("replacement_ref")
            if replacement is not None and not nonempty_string(replacement):
                errors.append(f"{label}.replacement_ref must be a non-empty string when present")


def validate_receipt(data: Any, graph: Any, envelope: Any) -> dict[str, Any]:
    root = require_mapping(data, "idea execution receipt")
    validated_envelope = validate_envelope(envelope)
    validated_graph = validate_graph(graph, validated_envelope)
    graph_by_id = {unit["id"]: unit for unit in validated_graph["units"]}
    errors: list[str] = []

    if root.get("schema") != SCHEMA:
        errors.append(f"schema must equal {SCHEMA}")
    if root.get("idea_id") != validated_envelope["idea"]["id"]:
        errors.append("idea_id does not match envelope idea.id")

    expected_envelope = semantic_digest(validated_envelope)
    if root.get("envelope_digest") != expected_envelope:
        errors.append("DERIVED_ARTIFACT_STALE: receipt envelope_digest does not match envelope")
    expected_graph = semantic_digest(validated_graph)
    if root.get("graph_digest") != expected_graph:
        errors.append("DERIVED_ARTIFACT_STALE: receipt graph_digest does not match graph")

    if not nonempty_string(root.get("status")):
        errors.append("status must be a non-empty string")
    if not nonempty_string(root.get("next_legal_transition")):
        errors.append("next_legal_transition must be a non-empty string")

    units = root.get("units")
    if not isinstance(units, list):
        errors.append("units must be a list")
        units = []
    receipt_ids: set[str] = set()
    for idx, unit in enumerate(units):
        label = f"units[{idx}]"
        if not isinstance(unit, dict):
            errors.append(f"{label} must be a mapping")
            continue
        uid = unit.get("unit_id")
        if not nonempty_string(uid):
            errors.append(f"{label}.unit_id must be a non-empty string")
            continue
        if uid in receipt_ids:
            errors.append(f"duplicate receipt unit {uid}")
        receipt_ids.add(uid)
        for key in ("owner", "adapter", "requested_terminal_state", "resulting_state"):
            if not nonempty_string(unit.get(key)):
                errors.append(f"{label}.{key} must be a non-empty string")
        graph_unit = graph_by_id.get(uid)
        if graph_unit is not None:
            if unit.get("owner") != graph_unit.get("owner"):
                errors.append(f"{label}.owner does not match graph unit {uid}")
            if unit.get("adapter") != graph_unit.get("adapter"):
                errors.append(f"{label}.adapter does not match graph unit {uid}")
        refs = unit.get("evidence_refs", [])
        if not isinstance(refs, list) or not all(nonempty_string(x) for x in refs):
            errors.append(f"{label}.evidence_refs must be a string list")
            refs = []
        if _claims_completion(unit.get("resulting_state")):
            if not refs:
                errors.append(
                    f"DOWNSTREAM_EVIDENCE_MISSING: {label} claims terminal state "
                    f"{unit.get('resulting_state')!r} without referencing any canonical "
                    "downstream owner receipt/state in evidence_refs"
                )
            if graph_unit is not None and graph_unit.get("admission_status") == "BLOCKED":
                errors.append(
                    f"RECEIPT_SEMANTIC_CONTRADICTION: {label} claims terminal state "
                    f"{unit.get('resulting_state')!r} while graph unit {uid} "
                    "admission_status is BLOCKED"
                )

    graph_ids = set(graph_by_id)
    if receipt_ids != graph_ids:
        errors.append(
            "receipt units must exactly match graph units "
            f"(receipt={sorted(receipt_ids)}, graph={sorted(graph_ids)})"
        )

    blockers = root.get("blockers")
    blocker_codes: set[str] = set()
    if not isinstance(blockers, list):
        errors.append("blockers must be a list")
    else:
        for idx, blocker in enumerate(blockers):
            if not isinstance(blocker, dict) or not nonempty_string(blocker.get("code")):
                errors.append(f"blockers[{idx}] must be a mapping with non-empty code")
                continue
            blocker_codes.add(blocker["code"])

    # The Receipt is a lineage join, so its overall claim must agree with its own units,
    # its own blockers, and the bound Graph. A terminal claim standing over unresolved
    # blockers, incomplete units, or a BLOCKED graph is a contradiction, not a status.
    overall_status = root.get("status")
    if _claims_completion(overall_status):
        if blocker_codes:
            errors.append(
                f"RECEIPT_SEMANTIC_CONTRADICTION: status {overall_status!r} claims completion "
                f"while unresolved receipt blockers remain ({sorted(blocker_codes)})"
            )
        incomplete = sorted(
            str(u.get("unit_id"))
            for u in units
            if isinstance(u, dict)
            and nonempty_string(u.get("unit_id"))
            and not _claims_completion(u.get("resulting_state"))
        )
        if incomplete:
            errors.append(
                f"RECEIPT_SEMANTIC_CONTRADICTION: status {overall_status!r} claims completion "
                f"while units did not reach a terminal state ({incomplete})"
            )
        if validated_graph.get("status") == "BLOCKED":
            errors.append(
                f"RECEIPT_SEMANTIC_CONTRADICTION: status {overall_status!r} claims completion "
                "while the bound graph status is BLOCKED"
            )

    # A blocked Graph stays blocked in the join. Dropping its blockers would let the
    # Receipt narrate a cleaner state than the lineage it binds to.
    graph_blocker_codes = {
        blocker["code"]
        for blocker in validated_graph.get("blockers", [])
        if isinstance(blocker, dict) and nonempty_string(blocker.get("code"))
    }
    unrepresented = sorted(graph_blocker_codes - blocker_codes)
    if unrepresented:
        errors.append(
            "RECEIPT_SEMANTIC_CONTRADICTION: receipt does not represent graph blockers "
            f"{unrepresented}"
        )

    _validate_reconciliation(root.get("reconciliation"), errors)

    if errors:
        raise ContractError("; ".join(errors))
    return root


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: validate_receipt.py <IDEA_EXECUTION_RECEIPT.yaml|json> "
            "<EXECUTION_GRAPH.yaml|json> <IDEA_EXECUTION_ENVELOPE.yaml|json>",
            file=sys.stderr,
        )
        return 2
    try:
        validate_receipt(load_data(sys.argv[1]), load_data(sys.argv[2]), load_data(sys.argv[3]))
    except ContractError as exc:
        print(f"IDEA_EXECUTION_RECEIPT: FAIL\n- {exc}", file=sys.stderr)
        return 1
    print("IDEA_EXECUTION_RECEIPT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
