from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

RESULT_SCHEMA = "l9.cursor-subagent.result.v1"
RESULT_SCHEMA_VERSION = "1.0.0"
ROLE_TO_RESULT_KIND = {
    "recon": "ReconReport",
    "pr_remediation": "PRRemediationReport",
    "test": "TestReport",
    "documentation": "DocumentationReport",
    "verifier_reviewer": "VerificationReviewReport",
}
ROLE_TO_GENERATED_DATA_ROLE = {
    "recon": "recon",
    "pr_remediation": "remediator",
    "test": "executor",
    "documentation": "evidence_writer",
    "verifier_reviewer": "reviewer",
}
READ_ONLY_ROLES = {"recon", "verifier_reviewer"}
VALID_STATUSES = {"completed", "partial", "blocked", "failed"}
VALID_PRIMARY_CLASSES = {
    "repository_fact",
    "architecture_boundary",
    "ownership_finding",
    "dependency_finding",
    "implementation_surface",
    "execution_procedure",
    "validation_procedure",
    "failure_pattern",
    "rejected_approach",
    "context_requirement",
    "context_waste",
    "task_contract_gap",
    "policy_candidate",
    "invariant_candidate",
    "regression_candidate",
    "reusable_pattern_candidate",
    "artifact_lineage",
    "unresolved_unknown",
    "follow_on_opportunity",
    "evidence_only",
}
VALID_EPISTEMIC_STATUSES = {
    "observed",
    "derived",
    "hypothesized",
    "disproven",
    "contested",
    "unresolved",
}
VALID_ROUTES = {
    "memory",
    "contracts",
    "validation",
    "patterns",
    "architecture",
    "opportunities",
    "unknowns",
    "evidence",
    "reject",
}
VALID_VISIBILITY = {
    "campaign_local",
    "repository_local",
    "project_group",
    "constellation_internal",
    "restricted",
}
VALID_EVIDENCE_TYPES = {
    "repository_path",
    "file_hash",
    "commit",
    "test_result",
    "command_receipt",
    "typed_artifact",
    "runtime_probe",
    "review_finding",
    "governed_external_source",
}
VALID_UNKNOWN_CLASSES = {
    "blocking",
    "validation",
    "harmless",
    "stale",
    "evidence_available_but_uninspected",
}
VALID_BLOCKING_STATUSES = {"blocking", "non_blocking"}
_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")
_CAMPAIGN_ACTION_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ResultValidationError(ValueError):
    """Raised when a Cursor subagent result violates the document contract."""


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def compute_artifact_digest(document: Mapping[str, Any]) -> str:
    """Compute SHA-256 without making the digest self-referential."""
    payload = copy.deepcopy(dict(document))
    provenance = payload.get("provenance")
    if isinstance(provenance, dict):
        provenance.pop("artifact_digest", None)
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def with_artifact_digest(document: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy containing the canonical result-document digest."""
    result = copy.deepcopy(dict(document))
    provenance = result.setdefault("provenance", {})
    if not isinstance(provenance, dict):
        raise ResultValidationError("provenance must be an object")
    provenance["artifact_digest"] = compute_artifact_digest(result)
    validate_result_document(result)
    return result


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ResultValidationError(f"{path} must be an object")
    return value


def _require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ResultValidationError(f"{path} must be an array")
    return value


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResultValidationError(f"{path} must be a non-empty string")
    return value


def _require_keys(
    value: Mapping[str, Any],
    required: set[str],
    path: str,
) -> None:
    missing = sorted(required - set(value))
    if missing:
        raise ResultValidationError(f"{path} is missing required fields: {', '.join(missing)}")


def _reject_extra_keys(
    value: Mapping[str, Any],
    allowed: set[str],
    path: str,
) -> None:
    extra = sorted(set(value) - allowed)
    if extra:
        raise ResultValidationError(f"{path} contains unsupported fields: {', '.join(extra)}")


def _validate_evidence_ref(value: Mapping[str, Any], path: str) -> None:
    _require_keys(value, {"source_id", "source_type"}, path)
    _require_string(value["source_id"], f"{path}.source_id")
    source_type = _require_string(value["source_type"], f"{path}.source_type")
    if source_type not in VALID_EVIDENCE_TYPES:
        raise ResultValidationError(f"{path}.source_type is unsupported: {source_type}")


def _validate_finding(value: Mapping[str, Any], path: str) -> None:
    _require_keys(
        value,
        {
            "finding_id",
            "primary_class",
            "epistemic_status",
            "statement",
            "scope",
            "confidence",
        },
        path,
    )
    finding_id = _require_string(value["finding_id"], f"{path}.finding_id")
    if not _ID_PATTERN.fullmatch(finding_id):
        raise ResultValidationError(f"{path}.finding_id has invalid characters")
    primary_class = _require_string(
        value["primary_class"],
        f"{path}.primary_class",
    )
    if primary_class not in VALID_PRIMARY_CLASSES:
        raise ResultValidationError(f"{path}.primary_class is unsupported: {primary_class}")
    epistemic_status = _require_string(
        value["epistemic_status"],
        f"{path}.epistemic_status",
    )
    if epistemic_status not in VALID_EPISTEMIC_STATUSES:
        raise ResultValidationError(f"{path}.epistemic_status is unsupported: {epistemic_status}")
    _require_string(value["statement"], f"{path}.statement")
    scope = _require_mapping(value["scope"], f"{path}.scope")
    if not scope:
        raise ResultValidationError(f"{path}.scope must not be empty")
    confidence = value["confidence"]
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise ResultValidationError(f"{path}.confidence must be numeric")
    if not 0 <= float(confidence) <= 1:
        raise ResultValidationError(f"{path}.confidence must be between 0 and 1")
    for index, evidence in enumerate(value.get("evidence", [])):
        _validate_evidence_ref(
            _require_mapping(evidence, f"{path}.evidence[{index}]"),
            f"{path}.evidence[{index}]",
        )
    routes = _require_list(value.get("proposed_routes", []), f"{path}.proposed_routes")
    unsupported_routes = sorted(set(routes) - VALID_ROUTES)
    if unsupported_routes:
        raise ResultValidationError(
            f"{path}.proposed_routes contains unsupported routes: " + ", ".join(unsupported_routes)
        )


def _validate_unknown(value: Mapping[str, Any], path: str) -> None:
    required = {
        "unknown_id",
        "description",
        "class",
        "blocking_status",
        "owner",
        "next_action",
        "evidence_needed",
        "source_action",
    }
    _require_keys(value, required, path)
    unknown_id = _require_string(value["unknown_id"], f"{path}.unknown_id")
    if not _ID_PATTERN.fullmatch(unknown_id):
        raise ResultValidationError(f"{path}.unknown_id has invalid characters")
    unknown_class = _require_string(value["class"], f"{path}.class")
    if unknown_class not in VALID_UNKNOWN_CLASSES:
        raise ResultValidationError(f"{path}.class is unsupported: {unknown_class}")
    blocking_status = _require_string(
        value["blocking_status"],
        f"{path}.blocking_status",
    )
    if blocking_status not in VALID_BLOCKING_STATUSES:
        raise ResultValidationError(f"{path}.blocking_status is unsupported: {blocking_status}")
    for field in (
        "description",
        "owner",
        "next_action",
        "evidence_needed",
        "source_action",
    ):
        _require_string(value[field], f"{path}.{field}")


def validate_result_document(document: Mapping[str, Any]) -> None:
    """Validate the campaign-bound Cursor subagent result contract."""
    root = _require_mapping(document, "document")
    allowed_root = {
        "schema",
        "schema_version",
        "result_id",
        "result_kind",
        "status",
        "identity",
        "assignment",
        "deliverable",
        "provenance",
    }
    _require_keys(root, allowed_root, "document")
    _reject_extra_keys(root, allowed_root, "document")
    if root["schema"] != RESULT_SCHEMA:
        raise ResultValidationError(f"document.schema must be {RESULT_SCHEMA!r}")
    if root["schema_version"] != RESULT_SCHEMA_VERSION:
        raise ResultValidationError(f"document.schema_version must be {RESULT_SCHEMA_VERSION!r}")
    result_id = _require_string(root["result_id"], "document.result_id")
    if not _ID_PATTERN.fullmatch(result_id):
        raise ResultValidationError("document.result_id has invalid characters")
    status = _require_string(root["status"], "document.status")
    if status not in VALID_STATUSES:
        raise ResultValidationError(f"document.status is unsupported: {status}")
    identity = _require_mapping(root["identity"], "document.identity")
    identity_fields = {
        "campaign_id",
        "graph_id",
        "action_id",
        "agent_id",
        "lease_id",
        "base_sha",
    }
    _require_keys(identity, identity_fields, "document.identity")
    _reject_extra_keys(identity, identity_fields, "document.identity")
    campaign_id = _require_string(
        identity["campaign_id"],
        "document.identity.campaign_id",
    )
    action_id = _require_string(
        identity["action_id"],
        "document.identity.action_id",
    )
    if not _CAMPAIGN_ACTION_PATTERN.fullmatch(campaign_id):
        raise ResultValidationError("document.identity.campaign_id has invalid characters")
    if not _CAMPAIGN_ACTION_PATTERN.fullmatch(action_id):
        raise ResultValidationError("document.identity.action_id has invalid characters")
    for field in ("graph_id", "agent_id", "lease_id"):
        _require_string(identity[field], f"document.identity.{field}")
    base_sha = _require_string(identity["base_sha"], "document.identity.base_sha")
    if not _SHA_PATTERN.fullmatch(base_sha):
        raise ResultValidationError(
            "document.identity.base_sha must be an exact 40-character Git SHA"
        )
    assignment = _require_mapping(root["assignment"], "document.assignment")
    required_assignment = {
        "role",
        "objective",
        "input_artifact_ids",
        "allowed_paths",
        "forbidden_paths",
    }
    allowed_assignment = required_assignment | {"subject_agent_id"}
    _require_keys(assignment, required_assignment, "document.assignment")
    _reject_extra_keys(assignment, allowed_assignment, "document.assignment")
    role = _require_string(assignment["role"], "document.assignment.role")
    if role not in ROLE_TO_RESULT_KIND:
        raise ResultValidationError(f"document.assignment.role is unsupported: {role}")
    expected_kind = ROLE_TO_RESULT_KIND[role]
    if root["result_kind"] != expected_kind:
        raise ResultValidationError(
            f"document.result_kind must be {expected_kind!r} for role {role!r}"
        )
    _require_string(assignment["objective"], "document.assignment.objective")
    for field in ("input_artifact_ids", "allowed_paths", "forbidden_paths"):
        values = _require_list(assignment[field], f"document.assignment.{field}")
        for index, value in enumerate(values):
            _require_string(value, f"document.assignment.{field}[{index}]")
    if role == "verifier_reviewer":
        subject_agent_id = _require_string(
            assignment.get("subject_agent_id"),
            "document.assignment.subject_agent_id",
        )
        if subject_agent_id == identity["agent_id"]:
            raise ResultValidationError("verifier_reviewer must not review its own work")
    deliverable = _require_mapping(root["deliverable"], "document.deliverable")
    deliverable_fields = {
        "summary",
        "findings",
        "files_read",
        "files_changed",
        "evidence",
        "commands_executed",
        "validations",
        "unresolved_items",
        "recommended_next_actions",
        "reuse_assessment",
        "visibility",
    }
    _require_keys(deliverable, deliverable_fields, "document.deliverable")
    _reject_extra_keys(deliverable, deliverable_fields, "document.deliverable")
    _require_string(deliverable["summary"], "document.deliverable.summary")
    findings = _require_list(
        deliverable["findings"],
        "document.deliverable.findings",
    )
    for index, finding in enumerate(findings):
        _validate_finding(
            _require_mapping(
                finding,
                f"document.deliverable.findings[{index}]",
            ),
            f"document.deliverable.findings[{index}]",
        )
    for field in ("files_read", "files_changed", "recommended_next_actions"):
        values = _require_list(
            deliverable[field],
            f"document.deliverable.{field}",
        )
        for index, value in enumerate(values):
            _require_string(value, f"document.deliverable.{field}[{index}]")
    if role in READ_ONLY_ROLES and deliverable["files_changed"]:
        raise ResultValidationError(f"role {role!r} must not report changed files")
    evidence = _require_list(
        deliverable["evidence"],
        "document.deliverable.evidence",
    )
    for index, item in enumerate(evidence):
        _validate_evidence_ref(
            _require_mapping(
                item,
                f"document.deliverable.evidence[{index}]",
            ),
            f"document.deliverable.evidence[{index}]",
        )
    commands = _require_list(
        deliverable["commands_executed"],
        "document.deliverable.commands_executed",
    )
    for index, item in enumerate(commands):
        command = _require_mapping(
            item,
            f"document.deliverable.commands_executed[{index}]",
        )
        _require_keys(
            command,
            {"command", "exit_code"},
            f"document.deliverable.commands_executed[{index}]",
        )
        _require_string(
            command["command"],
            f"document.deliverable.commands_executed[{index}].command",
        )
        if not isinstance(command["exit_code"], int) or isinstance(
            command["exit_code"],
            bool,
        ):
            raise ResultValidationError(
                f"document.deliverable.commands_executed[{index}].exit_code must be an integer"
            )
    validations = _require_list(
        deliverable["validations"],
        "document.deliverable.validations",
    )
    for index, item in enumerate(validations):
        validation = _require_mapping(
            item,
            f"document.deliverable.validations[{index}]",
        )
        _require_keys(
            validation,
            {"validation_id", "method", "result"},
            f"document.deliverable.validations[{index}]",
        )
        for field in ("validation_id", "method", "result"):
            _require_string(
                validation[field],
                f"document.deliverable.validations[{index}].{field}",
            )
        if validation["result"] not in {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}:
            raise ResultValidationError(
                f"document.deliverable.validations[{index}].result is unsupported"
            )
    unresolved = _require_list(
        deliverable["unresolved_items"],
        "document.deliverable.unresolved_items",
    )
    for index, item in enumerate(unresolved):
        _validate_unknown(
            _require_mapping(
                item,
                f"document.deliverable.unresolved_items[{index}]",
            ),
            f"document.deliverable.unresolved_items[{index}]",
        )
    reuse = _require_mapping(
        deliverable["reuse_assessment"],
        "document.deliverable.reuse_assessment",
    )
    _require_keys(
        reuse,
        {"reusable_data_found", "confidence"},
        "document.deliverable.reuse_assessment",
    )
    if not isinstance(reuse["reusable_data_found"], bool):
        raise ResultValidationError(
            "document.deliverable.reuse_assessment.reusable_data_found must be boolean"
        )
    confidence = reuse["confidence"]
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise ResultValidationError(
            "document.deliverable.reuse_assessment.confidence must be numeric"
        )
    if not 0 <= float(confidence) <= 1:
        raise ResultValidationError(
            "document.deliverable.reuse_assessment.confidence must be between 0 and 1"
        )
    visibility = _require_string(
        deliverable["visibility"],
        "document.deliverable.visibility",
    )
    if visibility not in VALID_VISIBILITY:
        raise ResultValidationError(f"document.deliverable.visibility is unsupported: {visibility}")
    provenance = _require_mapping(root["provenance"], "document.provenance")
    _require_keys(provenance, {"produced_at"}, "document.provenance")
    _reject_extra_keys(
        provenance,
        {"produced_at", "artifact_digest"},
        "document.provenance",
    )
    _require_string(
        provenance["produced_at"],
        "document.provenance.produced_at",
    )
    digest = provenance.get("artifact_digest")
    if digest is not None:
        digest_text = _require_string(
            digest,
            "document.provenance.artifact_digest",
        )
        if not _DIGEST_PATTERN.fullmatch(digest_text):
            raise ResultValidationError(
                "document.provenance.artifact_digest must be lowercase SHA-256"
            )
        expected_digest = compute_artifact_digest(root)
        if digest_text != expected_digest:
            raise ResultValidationError(
                "document.provenance.artifact_digest does not match document"
            )


def _typed_artifact_evidence(
    *,
    result_id: str,
    repository: str,
    repository_class: str,
    base_sha: str,
    artifact_digest: str,
) -> dict[str, Any]:
    return {
        "source_id": result_id,
        "source_type": "typed_artifact",
        "repository": repository,
        "repository_class": repository_class,
        "base_sha": base_sha,
        "locator": f"sha256:{artifact_digest}",
        "description": "Validated Cursor subagent result document",
    }


def to_generated_data_packet(
    document: Mapping[str, Any],
    *,
    repository: str,
    repository_class: str = "governed_repository",
) -> dict[str, Any]:
    """Project one accepted result into the existing generated-data packet."""
    repository = _require_string(repository, "repository")
    repository_class = _require_string(
        repository_class,
        "repository_class",
    )
    normalized = with_artifact_digest(document)
    identity = normalized["identity"]
    assignment = normalized["assignment"]
    deliverable = normalized["deliverable"]
    provenance = normalized["provenance"]
    role = assignment["role"]
    generated_data_role = ROLE_TO_GENERATED_DATA_ROLE[role]
    result_id = normalized["result_id"]
    artifact_digest = provenance["artifact_digest"]
    artifact_evidence = _typed_artifact_evidence(
        result_id=result_id,
        repository=repository,
        repository_class=repository_class,
        base_sha=identity["base_sha"],
        artifact_digest=artifact_digest,
    )
    generated_units: list[dict[str, Any]] = []
    for finding in deliverable["findings"]:
        scope = {
            **dict(finding["scope"]),
            "repository": repository,
            "repository_class": repository_class,
            "campaign": identity["campaign_id"],
            "role": role,
        }
        source_evidence = [dict(item) for item in finding.get("evidence", [])]
        source_evidence.append(dict(artifact_evidence))
        generated_units.append(
            {
                "unit_id": f"{result_id}:{finding['finding_id']}",
                "primary_class": finding["primary_class"],
                "secondary_tags": list(finding.get("secondary_tags", [])),
                "epistemic_status": finding["epistemic_status"],
                "statement": finding["statement"],
                "source_evidence": source_evidence,
                "scope": scope,
                "confidence": float(finding["confidence"]),
                "freshness": {
                    "observed_at": provenance["produced_at"],
                    "base_sha": identity["base_sha"],
                    "expires_at": None,
                },
                "proposed_routes": list(finding.get("proposed_routes", [])),
                "expected_reuse": dict(
                    finding.get(
                        "expected_reuse",
                        {
                            "task_local": True,
                            "cross_task": False,
                            "cross_campaign": False,
                            "cross_repository": False,
                            "description": "No broader reuse was asserted.",
                        },
                    )
                ),
                "invalidation_conditions": [
                    dict(item)
                    for item in finding.get(
                        "invalidation_conditions",
                        [],
                    )
                ],
                "self_promoted": False,
                "visibility": deliverable["visibility"],
            }
        )
    evidence_ids = {
        str(item["source_id"])
        for item in deliverable["evidence"]
        if isinstance(item, Mapping) and item.get("source_id")
    }
    evidence_ids.add(result_id)
    commands = [str(item["command"]) for item in deliverable["commands_executed"]]
    reusable = bool(deliverable["reuse_assessment"]["reusable_data_found"])
    reason = deliverable["reuse_assessment"].get("reason")
    if not reason:
        reason = (
            "The producing subagent identified reusable generated data."
            if reusable
            else "The producing subagent identified no reusable generated data."
        )
    return {
        "schema_version": "1.0.0",
        "packet_id": f"cursor-result:{result_id}",
        "identity": {
            "campaign_id": identity["campaign_id"],
            "graph_id": identity["graph_id"],
            "repository": repository,
            "repository_class": repository_class,
            "base_sha": identity["base_sha"],
            "action_id": identity["action_id"],
            "agent_id": identity["agent_id"],
            "role": generated_data_role,
            "lease_id": identity["lease_id"],
        },
        "primary_result": {
            "artifact_id": result_id,
            "artifact_kind": normalized["result_kind"],
            "completion_status": normalized["status"],
        },
        "generated_data_units": generated_units,
        "generated_data_assessment": {
            "reusable_data_found": reusable,
            "reason": reason,
        },
        "unresolved_unknowns": [dict(item) for item in deliverable["unresolved_items"]],
        "provenance": {
            "repository": repository,
            "repository_class": repository_class,
            "base_sha": identity["base_sha"],
            "input_artifacts": list(assignment["input_artifact_ids"]),
            "evidence_artifacts": sorted(evidence_ids),
            "inspected_paths": list(deliverable["files_read"]),
            "executed_commands": commands,
            "generated_at": provenance["produced_at"],
        },
        "reuse_assessment": dict(deliverable["reuse_assessment"]),
        "visibility": deliverable["visibility"],
        "generated_at": provenance["produced_at"],
    }


class AssignmentCorrelationError(ResultValidationError):
    """Raised when a structurally valid result does not match its assignment."""


ASSIGNMENT_IDENTITY_FIELDS = (
    "campaign_id",
    "graph_id",
    "action_id",
    "agent_id",
    "lease_id",
    "base_sha",
)


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a path glob into a regex. ``**`` spans directories; ``*`` and
    ``?`` do not cross ``/``."""
    out: list[str] = []
    i, n = 0, len(pattern)
    while i < n:
        char = pattern[i]
        if char == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif char == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(char))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def _path_matches_any(path: str, patterns: list[str]) -> bool:
    return any(_glob_to_regex(pattern).fullmatch(path) for pattern in patterns)


def validate_result_against_assignment(
    document: Mapping[str, Any],
    assignment: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a result document and prove it belongs to its exact assignment.

    Structural validity alone cannot prove correlation: a well-formed document
    could report the wrong campaign, agent, lease, base SHA, role, or paths.
    This narrows acceptance to the exact rendered assignment and returns the
    normalized (digest-bound) document. Raises on any mismatch.
    """
    validate_result_document(document)
    normalized = with_artifact_digest(document)
    spec = _require_mapping(assignment, "assignment")
    identity = normalized["identity"]
    doc_assignment = normalized["assignment"]
    deliverable = normalized["deliverable"]

    for field in ASSIGNMENT_IDENTITY_FIELDS:
        expected = _require_string(spec.get(field), f"assignment.{field}")
        if identity[field] != expected:
            raise AssignmentCorrelationError(
                f"identity.{field} {identity[field]!r} does not match assignment {expected!r}"
            )

    expected_role = _require_string(spec.get("role"), "assignment.role")
    if doc_assignment["role"] != expected_role:
        raise AssignmentCorrelationError(
            f"assignment.role {doc_assignment['role']!r} does not match "
            f"assignment {expected_role!r}"
        )

    allowed = _require_list(spec.get("allowed_paths", []), "assignment.allowed_paths")
    forbidden = _require_list(spec.get("forbidden_paths", []), "assignment.forbidden_paths")
    for index, changed in enumerate(deliverable["files_changed"]):
        if forbidden and _path_matches_any(changed, forbidden):
            raise AssignmentCorrelationError(
                f"files_changed[{index}] {changed!r} touches a forbidden path"
            )
        if allowed and not _path_matches_any(changed, allowed):
            raise AssignmentCorrelationError(
                f"files_changed[{index}] {changed!r} is outside the allowed paths"
            )

    if expected_role == "verifier_reviewer":
        expected_subject = _require_string(
            spec.get("subject_agent_id"),
            "assignment.subject_agent_id",
        )
        if doc_assignment.get("subject_agent_id") != expected_subject:
            raise AssignmentCorrelationError(
                "assignment.subject_agent_id does not match the rendered subject"
            )
        if expected_subject == identity["agent_id"]:
            raise AssignmentCorrelationError("verifier_reviewer must not review its own work")

    return normalized
