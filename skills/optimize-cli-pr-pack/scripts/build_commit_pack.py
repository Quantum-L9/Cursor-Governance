#!/usr/bin/env python3
"""Build a deterministic optimization CLI PR commit pack from a Git worktree."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

from validate_decision_ledger import validate_decision_contract

GENERATOR = "optimize-cli-pr-pack"
SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"

try:
    import jsonschema as _jsonschema
except ImportError as _exc:  # pragma: no cover - environment dependency
    _jsonschema = None
    _JSONSCHEMA_IMPORT_ERROR = _exc


def schema_validate(instance: Any, schema_filename: str, label: str) -> None:
    """Validate an instance against a bundled JSON Schema. jsonschema is a hard
    dependency so the schemas are authoritative, not decorative."""
    if _jsonschema is None:
        raise PackError(
            "jsonschema is required for schema-authoritative validation; "
            f"install it (pip install jsonschema): {_JSONSCHEMA_IMPORT_ERROR}"
        )
    schema = json.loads((SCHEMA_DIR / schema_filename).read_text(encoding="utf-8"))
    try:
        _jsonschema.validate(instance, schema)
    except _jsonschema.ValidationError as exc:
        location = "/".join(str(part) for part in exc.absolute_path) or "<root>"
        raise PackError(f"{label} violates {schema_filename} at {location}: {exc.message}") from exc


def improvement_from_measurements(baseline_value, candidate_value, direction):
    """Recompute improvement percent from the two measurements with metric
    direction. Returns (percent | None, error | None). A None percent with no
    error is a valid 0->N activation (higher-is-better from a zero baseline)."""
    if (
        not isinstance(baseline_value, (int, float))
        or isinstance(baseline_value, bool)
        or not isinstance(candidate_value, (int, float))
        or isinstance(candidate_value, bool)
    ):
        return (None, "baseline and candidate values must be numeric")
    b = float(baseline_value)
    c = float(candidate_value)
    if direction == "higher_is_better":
        if b == 0:
            return (None, None) if c > 0 else (None, "candidate does not exceed a zero baseline")
        return (round(100.0 * (c - b) / abs(b), 2), None)
    if b <= 0:
        return (None, "baseline value must be > 0 for a lower-is-better metric")
    return (round(100.0 * (b - c) / b, 2), None)


SCHEMA_VERSION = "2.0.0"
VALID_STATUSES = {"PR_READY", "BLOCKED"}
WIRING_STRATEGIES = {
    "activate_latent_capability",
    "repair_wiring",
    "connect_signal_consumer",
    "surface_existing_cli_path",
}
WIRING_CLASSES = {
    "inactive_component",
    "miswired_file",
    "dormant_capability",
    "unused_signal",
    "orphaned_config_schema",
    "broken_partial_wiring",
}
LEVERAGE_WEIGHTS = {
    "future_action_acceleration": 0.22,
    "existing_asset_amplification": 0.20,
    "reusable_system_value": 0.18,
    "multi_domain_benefit": 0.14,
    "optionality_gain": 0.10,
    "energy_load_inverse": 0.08,
    "social_or_network_gain": 0.08,
}


class PackError(RuntimeError):
    """Raised when the pack cannot be built safely."""


# Only `git` is invoked via run(); refuse any other binary (Sonar command-injection).
_ALLOWED_RUN_BINARIES = frozenset({"git"})


def run(
    command: list[str], cwd: Path, *, allow_codes: set[int] | None = None
) -> subprocess.CompletedProcess[str]:
    if not command or Path(command[0]).name not in _ALLOWED_RUN_BINARIES:
        raise PackError(f"disallowed command binary: {command[:1]!r}")
    # argv after the binary are git subcommands/flags/paths — never a shell string.
    result = subprocess.run(list(command), cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode not in (allow_codes or {0}):
        raise PackError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{result.stderr.strip()}"
        )
    return result


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_spec(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackError(f"cannot read JSON spec {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PackError("spec root must be a JSON object")
    return data


def require_string(data: dict[str, Any], key: str, prefix: str = "spec") -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PackError(f"{prefix}.{key} must be a non-empty string")
    return value.strip()


def safe_relative(value: str) -> Path:
    posix = PurePosixPath(value)
    if posix.is_absolute() or not posix.parts or ".." in posix.parts or "." in posix.parts:
        raise PackError(f"unsafe repository-relative path: {value!r}")
    if posix.parts[0] == ".git":
        raise PackError(f".git content is forbidden: {value!r}")
    return Path(*posix.parts)


def validate_measurement(data: Any, label: str) -> None:
    if not isinstance(data, dict):
        raise PackError(f"spec.performance.{label} must be an object")
    for key in ("command", "metric", "unit", "evidence"):
        require_string(data, key, f"spec.performance.{label}")
    value = data.get("value")
    samples = data.get("samples")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise PackError(f"spec.performance.{label}.value must be numeric")
    if not isinstance(samples, int) or isinstance(samples, bool) or samples < 1:
        raise PackError(f"spec.performance.{label}.samples must be a positive integer")


def calculate_leverage_score(dimensions: dict[str, Any]) -> float:
    if set(dimensions) != set(LEVERAGE_WEIGHTS):
        missing = sorted(set(LEVERAGE_WEIGHTS) - set(dimensions))
        extra = sorted(set(dimensions) - set(LEVERAGE_WEIGHTS))
        raise PackError(f"leverage dimensions mismatch; missing={missing}, extra={extra}")
    score = 0.0
    for key, weight in LEVERAGE_WEIGHTS.items():
        value = dimensions.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 5:
            raise PackError(f"leverage dimension {key} must be numeric from 0 to 5")
        score += float(value) * weight
    return round(score, 2)


def leverage_decision(score: float) -> str:
    if score < 2.5:
        return "reject_or_reframe"
    if score < 3.5:
        return "defer"
    if score < 4.0:
        return "approve"
    return "prioritize"


def validate_revision_synthesis(spec: dict[str, Any], optimization: dict[str, Any]) -> None:
    synthesis = spec.get("revision_synthesis")
    if not isinstance(synthesis, dict):
        raise PackError("spec.revision_synthesis must be an object")
    for key in (
        "findings",
        "targets",
        "options",
        "selected_option_ids",
        "unresolved_divergence_ids",
        "unknowns",
    ):
        if not isinstance(synthesis.get(key), list):
            raise PackError(f"spec.revision_synthesis.{key} must be an array")
    if synthesis.get("synthesis_version") != "1.0.0":
        raise PackError("spec.revision_synthesis.synthesis_version must be 1.0.0")
    if synthesis.get("leverage_policy_version") != "1.0.0":
        raise PackError("spec.revision_synthesis.leverage_policy_version must be 1.0.0")
    if synthesis.get("synthesis_status") not in {"complete", "partial", "blocked"}:
        raise PackError("spec.revision_synthesis.synthesis_status is invalid")
    if not isinstance(synthesis.get("all_material_findings_synthesized"), bool):
        raise PackError("spec.revision_synthesis.all_material_findings_synthesized must be boolean")
    require_string(synthesis, "selection_rationale", "spec.revision_synthesis")

    findings: dict[str, dict[str, Any]] = {}
    divergence_ids: set[str] = set()
    for index, finding in enumerate(synthesis["findings"], start=1):
        prefix = f"spec.revision_synthesis.findings[{index}]"
        if not isinstance(finding, dict):
            raise PackError(f"{prefix} must be an object")
        finding_id = require_string(finding, "id", prefix)
        if not re.fullmatch(r"CLI-FND-[0-9]{3}", finding_id):
            raise PackError(f"{prefix}.id must match CLI-FND-NNN")
        if finding_id in findings:
            raise PackError(f"duplicate revision finding id: {finding_id}")
        if finding.get("kind") not in {
            "docs_code_divergence",
            "performance_bottleneck",
            "latent_capability",
            "configuration_misalignment",
            "resource_risk",
            "external_limit",
            "validation_gap",
            "deployment_gap",
            "other",
        }:
            raise PackError(f"{prefix}.kind is invalid")
        severity = finding.get("severity")
        if not isinstance(severity, int) or isinstance(severity, bool) or not 1 <= severity <= 5:
            raise PackError(f"{prefix}.severity must be 1..5")
        for key in ("summary", "owner", "recommended_action"):
            require_string(finding, key, prefix)
        for key in ("evidence", "related_source_ids"):
            if not isinstance(finding.get(key), list):
                raise PackError(f"{prefix}.{key} must be an array")
        if not finding["evidence"] or not all(
            isinstance(item, str) and item.strip() for item in finding["evidence"]
        ):
            raise PackError(f"{prefix}.evidence must contain non-empty strings")
        if finding.get("scope") not in {"in_scope", "out_of_scope", "unknown"}:
            raise PackError(f"{prefix}.scope is invalid")
        if finding.get("status") not in {"open", "reconciled", "deferred", "unknown"}:
            raise PackError(f"{prefix}.status is invalid")
        if not isinstance(finding.get("blocks_release"), bool):
            raise PackError(f"{prefix}.blocks_release must be boolean")
        if finding["kind"] == "docs_code_divergence":
            divergence_ids.add(finding_id)
            for key in ("docs_claim", "code_observation"):
                require_string(finding, key, prefix)
            if finding.get("divergence_type") not in {
                "documented_not_implemented",
                "implemented_not_documented",
                "behavior_mismatch",
                "config_default_mismatch",
                "entrypoint_mismatch",
                "unknown",
            }:
                raise PackError(f"{prefix}.divergence_type is invalid")
            if finding.get("reconciliation") not in {
                "fixed_in_scope",
                "out_of_scope_finding",
                "deferred",
                "unknown",
            }:
                raise PackError(f"{prefix}.reconciliation is invalid")
        findings[finding_id] = finding

    targets: dict[str, dict[str, Any]] = {}
    finding_refs: set[str] = set()
    for index, target in enumerate(synthesis["targets"], start=1):
        prefix = f"spec.revision_synthesis.targets[{index}]"
        if not isinstance(target, dict):
            raise PackError(f"{prefix} must be an object")
        target_id = require_string(target, "id", prefix)
        if not re.fullmatch(r"CLI-TGT-[0-9]{3}", target_id):
            raise PackError(f"{prefix}.id must match CLI-TGT-NNN")
        if target_id in targets:
            raise PackError(f"duplicate revision target id: {target_id}")
        for key in ("title", "objective"):
            require_string(target, key, prefix)
        for key in (
            "source_finding_ids",
            "affected_surfaces",
            "constraints",
            "success_evidence",
            "option_ids",
        ):
            value = target.get(key)
            if not isinstance(value, list) or not value:
                raise PackError(f"{prefix}.{key} must be a non-empty array")
        if target.get("scope") not in {"implement_now", "defer", "downstream", "unknown"}:
            raise PackError(f"{prefix}.scope is invalid")
        missing = set(target["source_finding_ids"]) - set(findings)
        if missing:
            raise PackError(f"{prefix} references missing findings: {sorted(missing)}")
        finding_refs.update(target["source_finding_ids"])
        targets[target_id] = target

    if finding_refs != set(findings):
        raise PackError(
            f"every finding must map to a target; unmapped={sorted(set(findings) - finding_refs)}"
        )

    options: dict[str, dict[str, Any]] = {}
    target_refs: set[str] = set()
    for index, option in enumerate(synthesis["options"], start=1):
        prefix = f"spec.revision_synthesis.options[{index}]"
        if not isinstance(option, dict):
            raise PackError(f"{prefix} must be an object")
        option_id = require_string(option, "id", prefix)
        if not re.fullmatch(r"CLI-OPT-[0-9]{3}", option_id):
            raise PackError(f"{prefix}.id must match CLI-OPT-NNN")
        if option_id in options:
            raise PackError(f"duplicate revision option id: {option_id}")
        for key in ("strategy", "description", "recurring_drag_risk"):
            require_string(option, key, prefix)
        if option.get("scope") not in {"in_scope", "out_of_scope", "unknown"}:
            raise PackError(f"{prefix}.scope is invalid")
        target_ids = option.get("target_ids")
        if not isinstance(target_ids, list) or not target_ids:
            raise PackError(f"{prefix}.target_ids must be a non-empty array")
        missing = set(target_ids) - set(targets)
        if missing:
            raise PackError(f"{prefix} references missing targets: {sorted(missing)}")
        target_refs.update(target_ids)
        dimensions = option.get("leverage_dimensions")
        if not isinstance(dimensions, dict):
            raise PackError(f"{prefix}.leverage_dimensions must be an object")
        calculated = calculate_leverage_score(dimensions)
        recorded = option.get("leverage_score")
        if (
            not isinstance(recorded, (int, float))
            or isinstance(recorded, bool)
            or abs(float(recorded) - calculated) > 0.001
        ):
            raise PackError(f"{prefix}.leverage_score must equal calculated score {calculated}")
        expected = leverage_decision(calculated)
        if option.get("decision") != expected:
            raise PackError(f"{prefix}.decision must be {expected} for score {calculated}")
        for key in (
            "future_actions_accelerated",
            "current_assets_strengthened",
            "reusable_outputs_created",
            "multi_domain_benefits",
            "unknowns",
        ):
            if not isinstance(option.get(key), list):
                raise PackError(f"{prefix}.{key} must be an array")
        for key in (
            "future_actions_accelerated",
            "current_assets_strengthened",
            "reusable_outputs_created",
        ):
            if not option[key]:
                raise PackError(f"{prefix}.{key} must not be empty")
        if not isinstance(option.get("selected"), bool):
            raise PackError(f"{prefix}.selected must be boolean")
        options[option_id] = option

    if target_refs != set(targets):
        raise PackError(
            f"every target must map to an option; unmapped={sorted(set(targets) - target_refs)}"
        )
    for target_id, target in targets.items():
        declared = set(target["option_ids"])
        actual = {
            option_id for option_id, option in options.items() if target_id in option["target_ids"]
        }
        if declared != actual:
            raise PackError(
                f"target {target_id} option_ids mismatch: declared={sorted(declared)}, actual={sorted(actual)}"
            )

    selected = synthesis["selected_option_ids"]
    if not all(
        isinstance(item, str) and re.fullmatch(r"CLI-OPT-[0-9]{3}", item) for item in selected
    ):
        raise PackError(
            "spec.revision_synthesis.selected_option_ids must contain CLI-OPT-NNN strings"
        )
    if len(selected) != len(set(selected)):
        raise PackError("spec.revision_synthesis.selected_option_ids contains duplicates")
    selected_flags = {option_id for option_id, option in options.items() if option["selected"]}
    if set(selected) != selected_flags:
        raise PackError("selected_option_ids must exactly match options with selected=true")
    for option_id in selected:
        option = options.get(option_id)
        if option is None:
            raise PackError(f"selected revision option missing: {option_id}")
        if option["scope"] != "in_scope":
            raise PackError(f"selected option must be in_scope: {option_id}")
        if option["decision"] not in {"approve", "prioritize"} or option["leverage_score"] < 3.5:
            raise PackError(f"selected option must be leverage-approved: {option_id}")
        if option["unknowns"]:
            raise PackError(f"selected option cannot retain unknowns: {option_id}")

    unresolved = synthesis["unresolved_divergence_ids"]
    if set(unresolved) - divergence_ids:
        raise PackError("unresolved_divergence_ids must reference docs_code_divergence findings")
    expected_unresolved = {
        fid for fid in divergence_ids if findings[fid].get("reconciliation") != "fixed_in_scope"
    }
    if set(unresolved) != expected_unresolved:
        raise PackError(
            f"unresolved_divergence_ids mismatch: expected={sorted(expected_unresolved)}"
        )
    for finding_id in unresolved:
        finding = findings[finding_id]
        if finding["scope"] == "unknown" or finding.get("reconciliation") == "unknown":
            if spec.get("status") == "PR_READY":
                raise PackError(
                    f"PR_READY cannot retain unknown docs-code divergence: {finding_id}"
                )
        if finding["owner"].strip().lower() == "unknown":
            raise PackError(f"unresolved divergence requires an owner: {finding_id}")

    if optimization.get("selected_revision_option_ids") != selected:
        raise PackError(
            "spec.optimization.selected_revision_option_ids must match revision_synthesis.selected_option_ids"
        )
    if optimization.get("revision_synthesis_path") != "evidence/CLI_REVISION_SYNTHESIS.json":
        raise PackError("spec.optimization.revision_synthesis_path is invalid")

    if spec.get("status") == "PR_READY":
        if (
            synthesis["synthesis_status"] != "complete"
            or synthesis["all_material_findings_synthesized"] is not True
        ):
            raise PackError("PR_READY requires complete synthesis of all material findings")
        if synthesis["unknowns"]:
            raise PackError("PR_READY revision synthesis cannot retain material unknowns")
        if not selected:
            raise PackError("PR_READY requires at least one selected revision option")
        blocking = [
            fid
            for fid, finding in findings.items()
            if finding["blocks_release"] and finding["status"] != "reconciled"
        ]
        if blocking:
            raise PackError(f"PR_READY has unresolved release-blocking findings: {blocking}")


def validate_wiring(spec: dict[str, Any], optimization: dict[str, Any]) -> None:
    wiring = spec.get("wiring")
    active = optimization.get("strategy") in WIRING_STRATEGIES
    if wiring is None:
        if active:
            raise PackError("latent-capability strategies require spec.wiring")
        return
    if not isinstance(wiring, dict):
        raise PackError("spec.wiring must be an object")
    for key in (
        "entrypoints",
        "registries",
        "feature_flags",
        "signal_consumers",
        "findings",
        "edges",
        "selected_finding_ids",
        "unresolved_unknowns",
    ):
        if not isinstance(wiring.get(key), list):
            raise PackError(f"spec.wiring.{key} must be an array")
    if not isinstance(wiring.get("analysis_performed"), bool):
        raise PackError("spec.wiring.analysis_performed must be boolean")
    passes = wiring.get("convergence_passes")
    if not isinstance(passes, int) or isinstance(passes, bool) or not 1 <= passes <= 3:
        raise PackError("spec.wiring.convergence_passes must be an integer from 1 to 3")
    if wiring.get("convergence_status") not in {"converged", "partial", "failed"}:
        raise PackError("spec.wiring.convergence_status is invalid")

    findings_by_id: dict[str, dict[str, Any]] = {}
    for index, finding in enumerate(wiring["findings"], start=1):
        prefix = f"spec.wiring.findings[{index}]"
        if not isinstance(finding, dict):
            raise PackError(f"{prefix} must be an object")
        finding_id = require_string(finding, "id", prefix)
        if not re.fullmatch(r"DWA-[0-9]{3}", finding_id):
            raise PackError(f"{prefix}.id must match DWA-NNN")
        if finding_id in findings_by_id:
            raise PackError(f"duplicate wiring finding id: {finding_id}")
        if finding.get("defect_class") not in WIRING_CLASSES:
            raise PackError(f"{prefix}.defect_class is invalid")
        severity = finding.get("severity")
        if not isinstance(severity, int) or isinstance(severity, bool) or not 1 <= severity <= 5:
            raise PackError(f"{prefix}.severity must be 1..5")
        for key in (
            "definition_evidence",
            "consumer_evidence",
            "feature_flag_intent",
            "impact",
            "correction",
            "owner_layer",
            "leverage",
            "downstream_capability",
        ):
            require_string(finding, key, prefix)
        if not isinstance(finding.get("dynamic_dispatch_checked"), bool):
            raise PackError(f"{prefix}.dynamic_dispatch_checked must be boolean")
        if not isinstance(finding.get("dormant_by_design"), bool):
            raise PackError(f"{prefix}.dormant_by_design must be boolean")
        if not isinstance(finding.get("blocks_release"), bool):
            raise PackError(f"{prefix}.blocks_release must be boolean")
        if finding.get("verdict") not in {"activate", "remove", "unknown"}:
            raise PackError(f"{prefix}.verdict is invalid")
        findings_by_id[finding_id] = finding

    for index, edge in enumerate(wiring["edges"], start=1):
        prefix = f"spec.wiring.edges[{index}]"
        if not isinstance(edge, dict):
            raise PackError(f"{prefix} must be an object")
        for key in ("producer", "consumer", "evidence"):
            require_string(edge, key, prefix)
        for key in ("connected_before", "connected_after"):
            if not isinstance(edge.get(key), bool):
                raise PackError(f"{prefix}.{key} must be boolean")

    selected = wiring["selected_finding_ids"]
    if not all(isinstance(item, str) and re.fullmatch(r"DWA-[0-9]{3}", item) for item in selected):
        raise PackError("spec.wiring.selected_finding_ids must contain DWA-NNN strings")
    if len(set(selected)) != len(selected):
        raise PackError("spec.wiring.selected_finding_ids contains duplicates")
    missing = set(selected) - set(findings_by_id)
    if missing:
        raise PackError(f"selected wiring findings are missing: {sorted(missing)}")
    if not all(isinstance(item, str) and item.strip() for item in wiring["unresolved_unknowns"]):
        raise PackError("spec.wiring.unresolved_unknowns must contain non-empty strings")

    if active:
        if wiring["analysis_performed"] is not True:
            raise PackError("latent-capability strategies require completed wiring analysis")
        if wiring["convergence_status"] != "converged":
            raise PackError("latent-capability strategies require converged wiring analysis")
        if not selected or not wiring["edges"]:
            raise PackError(
                "latent-capability strategies require selected findings and producer-consumer edges"
            )

    if spec.get("status") == "PR_READY" and active:
        if wiring["unresolved_unknowns"]:
            raise PackError("PR_READY latent-capability packs cannot retain wiring unknowns")
        for finding_id in selected:
            finding = findings_by_id[finding_id]
            if finding["verdict"] != "activate":
                raise PackError(f"selected finding {finding_id} must have verdict=activate")
            if finding["dynamic_dispatch_checked"] is not True:
                raise PackError(f"selected finding {finding_id} requires dynamic-dispatch review")
            evidence = f"{finding['definition_evidence']} {finding['consumer_evidence']}".lower()
            if "unknown" in evidence:
                raise PackError(f"selected finding {finding_id} has unknown bidirectional evidence")
            if finding["feature_flag_intent"].strip().lower() == "unknown":
                raise PackError(f"selected finding {finding_id} has unknown feature-flag intent")
            if finding["dormant_by_design"] is True:
                raise PackError(
                    f"selected finding {finding_id} is dormant by design and cannot be activated"
                )


def validate_spec(spec: dict[str, Any]) -> None:
    for key in (
        "pack_name",
        "version",
        "repository",
        "base_ref",
        "branch",
        "status",
        "summary",
        "commit_message",
        "pr_body",
    ):
        require_string(spec, key)
    if spec["status"] not in VALID_STATUSES:
        raise PackError(f"spec.status must be one of {sorted(VALID_STATUSES)}")

    changed = spec.get("changed_files")
    if (
        not isinstance(changed, list)
        or not changed
        or not all(isinstance(item, str) for item in changed)
    ):
        raise PackError("spec.changed_files must be a non-empty string array")
    if len(set(changed)) != len(changed):
        raise PackError("spec.changed_files contains duplicates")
    for item in changed:
        safe_relative(item)

    deleted = spec.get("deleted_files", [])
    if not isinstance(deleted, list) or not all(isinstance(item, str) for item in deleted):
        raise PackError("spec.deleted_files must be a string array when present")
    for item in deleted:
        safe_relative(item)
    if set(deleted) - set(changed):
        raise PackError("every deleted_files entry must also appear in changed_files")

    optimization = spec.get("optimization")
    if not isinstance(optimization, dict):
        raise PackError("spec.optimization must be an object")
    for key in (
        "utilization_gap_class",
        "ownership",
        "evidence",
        "strategy",
        "rollback_trigger",
        "revision_synthesis_path",
    ):
        require_string(optimization, key, "spec.optimization")
    selected_revision_options = optimization.get("selected_revision_option_ids")
    if not isinstance(selected_revision_options, list) or not selected_revision_options:
        raise PackError("spec.optimization.selected_revision_option_ids must be a non-empty array")
    for key in ("preserved_constraints", "external_limits_not_bypassed"):
        value = optimization.get(key)
        if (
            not isinstance(value, list)
            or not value
            or not all(isinstance(item, str) and item.strip() for item in value)
        ):
            raise PackError(f"spec.optimization.{key} must be a non-empty string array")
    envelope = optimization.get("resource_envelope")
    if not isinstance(envelope, dict) or not envelope:
        raise PackError("spec.optimization.resource_envelope must be a non-empty object")

    decision_errors = validate_decision_contract(spec)
    if decision_errors:
        raise PackError("adaptive reasoning contract failed: " + "; ".join(decision_errors))

    route = spec["execution_route"]
    if route.get("utilization_gap_class") != optimization.get("utilization_gap_class"):
        raise PackError("execution_route utilization_gap_class must match optimization plan")
    if route.get("ownership") != optimization.get("ownership"):
        raise PackError("execution_route ownership must match optimization plan")

    validate_revision_synthesis(spec, optimization)
    validate_wiring(spec, optimization)

    performance = spec.get("performance")
    if not isinstance(performance, dict):
        raise PackError("spec.performance must be an object")
    validate_measurement(performance.get("baseline"), "baseline")
    require_string(performance, "comparison_method", "spec.performance")
    for key in ("correctness_checks", "resource_checks"):
        value = performance.get(key)
        if (
            not isinstance(value, list)
            or not value
            or not all(isinstance(item, str) and item.strip() for item in value)
        ):
            raise PackError(f"spec.performance.{key} must be a non-empty string array")
    candidate = performance.get("candidate")
    improvement = performance.get("improvement_percent")
    if candidate is not None:
        validate_measurement(candidate, "candidate")
    if improvement is not None and (
        not isinstance(improvement, (int, float)) or isinstance(improvement, bool)
    ):
        raise PackError("spec.performance.improvement_percent must be numeric when present")
    direction = performance.get("direction", "lower_is_better")
    if direction not in {"lower_is_better", "higher_is_better"}:
        raise PackError("spec.performance.direction must be lower_is_better or higher_is_better")

    activation = False
    if candidate is not None:
        base = performance["baseline"]
        if base.get("metric") != candidate.get("metric") or base.get("unit") != candidate.get(
            "unit"
        ):
            raise PackError(
                "performance baseline and candidate must share the same metric and unit"
            )
        computed, error = improvement_from_measurements(
            base["value"], candidate["value"], direction
        )
        if error:
            raise PackError(f"spec.performance: {error}")
        if computed is None:
            activation = True  # valid 0->N capability activation
        else:
            if improvement is None:
                raise PackError(
                    "spec.performance.improvement_percent is required when a candidate is present"
                )
            if abs(float(improvement) - computed) > 0.5:
                raise PackError(
                    f"spec.performance.improvement_percent {improvement} does not match recomputed {computed}"
                )

    if spec["status"] == "PR_READY":
        if optimization["ownership"] != "repository_owned":
            raise PackError("PR_READY requires repository_owned bottleneck ownership")
        if candidate is None:
            raise PackError("PR_READY requires a candidate measurement")
        if not activation and (improvement is None or float(improvement) <= 0):
            raise PackError(
                "PR_READY requires a positive measured improvement (or a 0->N activation proof)"
            )
        if optimization["strategy"] == "none":
            raise PackError("PR_READY cannot use optimization.strategy=none")
    if optimization["ownership"] in {"external", "unknown"} and spec["status"] != "BLOCKED":
        raise PackError("external or unknown bottleneck ownership must produce BLOCKED status")

    validation = spec.get("validation")
    if not isinstance(validation, dict) or not isinstance(validation.get("commands"), list):
        raise PackError("spec.validation.commands must be an array")
    require_string(validation, "summary", "spec.validation")

    for key in ("deploy", "rollback", "handoff"):
        if not isinstance(spec.get(key), dict):
            raise PackError(f"spec.{key} must be an object")
    require_string(spec["deploy"], "playbook", "spec.deploy")
    require_string(spec["deploy"], "release_checklist", "spec.deploy")
    require_string(spec["rollback"], "playbook", "spec.rollback")
    require_string(spec["handoff"], "markdown", "spec.handoff")
    if not isinstance(spec["handoff"].get("next_agent_task"), dict):
        raise PackError("spec.handoff.next_agent_task must be an object")

    issues = spec.get("issues", [])
    if not isinstance(issues, list) or not all(isinstance(item, dict) for item in issues):
        raise PackError("spec.issues must be an object array when present")
    if spec["status"] == "BLOCKED" and not issues:
        raise PackError("BLOCKED packs require at least one independent issue artifact")


def ensure_git_repo(repo_root: Path) -> None:
    if not repo_root.is_dir():
        raise PackError(f"repository path does not exist: {repo_root}")
    actual = Path(run(["git", "rev-parse", "--show-toplevel"], repo_root).stdout.strip()).resolve()
    if actual != repo_root.resolve():
        raise PackError(
            f"repo_root must be the Git top level: expected {actual}, got {repo_root.resolve()}"
        )


def is_tracked(repo_root: Path, relative: Path) -> bool:
    return (
        run(
            ["git", "ls-files", "--error-unmatch", "--", relative.as_posix()],
            repo_root,
            allow_codes={0, 1},
        ).returncode
        == 0
    )


def _split_git_patches(blob: bytes) -> list[bytes]:
    """Split a concatenated git patch into per-file patch blobs."""
    if not blob:
        return []
    marker = b"diff --git "
    first = blob.find(marker)
    if first < 0:
        return []
    parts: list[bytes] = []
    start = first
    while True:
        nxt = blob.find(marker, start + len(marker))
        if nxt < 0:
            parts.append(blob[start:])
            break
        parts.append(blob[start:nxt])
        start = nxt
    return [p for p in parts if p.strip()]


def _patch_paths(patch: bytes) -> set[str]:
    """Extract a/ and b/ paths from a single ``diff --git`` header."""
    first = patch.split(b"\n", 1)[0]
    pieces = first.split(b" ")
    if len(pieces) < 4:
        return set()
    out: set[str] = set()
    for raw in pieces[2:4]:
        s = raw.decode(errors="replace")
        if s.startswith(("a/", "b/")):
            s = s[2:]
        if s != "/dev/null":
            out.add(s)
    return out


def _filter_patches(blob: bytes, allowed: set[str]) -> bytes:
    keep = [p for p in _split_git_patches(blob) if _patch_paths(p) & allowed]
    return b"".join(keep)


def build_patch(repo_root: Path, base_ref: str, changed_files: list[str]) -> bytes:
    run(["git", "rev-parse", "--verify", f"{base_ref}^{{commit}}"], repo_root)
    tracked: list[str] = []
    untracked: list[str] = []
    for raw in changed_files:
        relative = safe_relative(raw)
        if is_tracked(repo_root, relative):
            tracked.append(relative.as_posix())
        elif (repo_root / relative).is_file():
            untracked.append(relative.as_posix())
        else:
            raise PackError(f"untracked changed file is missing: {raw}")

    chunks: list[bytes] = []
    if tracked:
        # Binary patch — no user paths on argv (Sonar S6350). Diff whole tree, filter.
        if Path("git").name not in _ALLOWED_RUN_BINARIES:
            raise PackError("disallowed command binary: ['git']")
        result = subprocess.run(
            ["git", "diff", "--binary", "--no-ext-diff", base_ref],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise PackError(f"git diff failed: {result.stderr.decode(errors='replace').strip()}")
        filtered = _filter_patches(result.stdout, set(tracked))
        if not filtered.strip():
            raise PackError("tracked changed_files produced an empty filtered patch")
        chunks.append(filtered)
    for relative in untracked:
        # Fixed argv operands only; rewrite headers to the real relative path.
        staging_name = "_optimize_cli_pr_pack_untracked_staging"
        staging = repo_root / staging_name
        source = under_root(repo_root, repo_root / relative, label="untracked")
        try:
            payload = source.read_bytes()
            with open(staging, "wb") as handle:
                handle.write(payload)
            result = subprocess.run(
                [
                    "git",
                    "diff",
                    "--no-index",
                    "--binary",
                    "--",
                    "/dev/null",
                    staging_name,
                ],
                cwd=repo_root,
                capture_output=True,
                check=False,
            )
            if result.returncode not in {0, 1}:
                raise PackError(f"git diff for untracked file failed: {relative}")
            chunks.append(result.stdout.replace(staging_name.encode(), relative.encode()))
        finally:
            if staging.exists():
                staging.unlink()
    patch = b"".join(chunks)
    if not patch.strip():
        raise PackError("generated patch is empty; changed_files do not differ from base_ref")
    return patch


def under_root(root: Path, path: Path, *, label: str = "path") -> Path:
    """Resolve ``path`` and require it stays under ``root`` (commonpath gate)."""
    base = os.path.realpath(root)
    target = os.path.realpath(path)
    try:
        if os.path.commonpath([base, target]) != base:
            raise PackError(f"{label} escapes root {root}: {path}")
    except ValueError as exc:  # different drives / empty
        raise PackError(f"{label} escapes root {root}: {path}") from exc
    return Path(target)


def write_text(root: Path, path: Path, content: str) -> None:
    """Write ``path`` only after confirming it resolves under ``root``."""
    target = under_root(root, path, label="write_text")
    target.parent.mkdir(parents=True, exist_ok=True)
    # open() after commonpath — same sanitizer pattern as agents/tools render_principals.
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(content.rstrip() + "\n")


def created_utc(spec: dict[str, Any]) -> str:
    explicit = spec.get("created_utc")
    if explicit is not None:
        if not isinstance(explicit, str) or not explicit.strip():
            raise PackError("created_utc must be a non-empty RFC3339 string")
        return explicit.strip()
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if not epoch:
        print(
            "WARNING: neither spec.created_utc nor SOURCE_DATE_EPOCH is set; the pack "
            "timestamp uses wall-clock time, so MANIFEST.json and the .tar.gz are NOT "
            "byte-reproducible. Pin one of them for deterministic packaging.",
            file=sys.stderr,
        )
    try:
        timestamp = (
            dt.datetime.fromtimestamp(int(epoch), tz=dt.UTC)
            if epoch
            else dt.datetime.now(tz=dt.UTC)
        )
    except ValueError as exc:
        raise PackError("SOURCE_DATE_EPOCH must be an integer") from exc
    return timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def render_readme(spec: dict[str, Any]) -> str:
    improvement = spec["performance"].get("improvement_percent")
    delta = "UNKNOWN" if improvement is None else f"{improvement:.2f}%"
    steps = [
        "Start from a clean worktree at the recorded base ref.",
        "Review `evidence/EXECUTION_ROUTE.json`, `evidence/DECISION_LEDGER.json`, and `evidence/DECISION_RECORD.md`.",
        "Review `evidence/CLI_REVISION_SYNTHESIS.json`, `evidence/CLI_REVISION_PLAN.md`, and `evidence/DOCS_CODE_DIVERGENCE_FINDINGS.md`.",
    ]
    if (spec.get("wiring") or {}).get("analysis_performed"):
        steps.append(
            "Review `evidence/WIRING_MAP.md` and `evidence/LATENT_CAPABILITY_FINDINGS.json`."
        )
    steps += [
        "Review `change/OPTIMIZATION_PLAN.json` and `evidence/PERFORMANCE.md`.",
        "Apply `change/commit.patch` with `git apply --index change/commit.patch`.",
        "Run the checks recorded in `evidence/VALIDATION.md`.",
        "Commit using `pr/COMMIT_MESSAGE.txt`.",
        "Use `pr/PR_BODY.md` when opening the pull request.",
        "Deploy only through `deploy/DEPLOY_PLAYBOOK.md`.",
    ]
    apply_block = "\n".join(f"{index}. {step}" for index, step in enumerate(steps, start=1))
    return f"""# {spec["pack_name"]}

Status: `{spec["status"]}`

Repository: `{spec["repository"]}`  
Base ref: `{spec["base_ref"]}`  
Branch: `{spec["branch"]}`  
Utilization gap: `{spec["optimization"]["utilization_gap_class"]}`  
Measured improvement: `{delta}`

## Summary

{spec["summary"]}

## Apply

{apply_block}

Read `handoff/AGENT_HANDOFF.md` before continuing the work.
"""


def render_pr_checklist(spec: dict[str, Any]) -> str:
    mark = "x" if spec["status"] == "PR_READY" else " "
    wiring_line = (
        f"- [{mark}] Reachability converged with bidirectional evidence and selected activate findings\n"
        if (spec.get("wiring") or {}).get("analysis_performed")
        else ""
    )
    return f"""# PR Checklist

- [{mark}] Adaptive execution route matches ownership, evidence state, and risk
- [{mark}] Every routed proof obligation is satisfied or explicitly blocked
- [{mark}] Decision ledger selection matches the revision synthesis
- [{mark}] All material findings map to revision targets and options
- [{mark}] Selected revision options pass leverage and scope gates
- [{mark}] Docs-code divergence is reconciled or explicitly disclosed
- [{mark}] Bottleneck ownership is repository-owned
- [{mark}] Baseline and candidate evidence are comparable
- [{mark}] Performance improvement is recorded
- [{mark}] Correctness and resource-safety checks pass
- [{mark}] Changed files and binary-safe patch agree
- [{mark}] Deployment and rollback playbooks are executable
- [{mark}] Agent handoff is complete
{wiring_line}- [ ] Required human approvals are complete
"""


def render_validation(spec: dict[str, Any]) -> str:
    lines = [
        "# Validation",
        "",
        f"Status: `{spec['status']}`",
        "",
        spec["validation"]["summary"],
        "",
        "## Commands",
        "",
    ]
    commands = spec["validation"]["commands"]
    if not commands:
        lines.append(
            "No commands were executed. This pack cannot be classified PR_READY without equivalent evidence."
        )
    for index, record in enumerate(commands, start=1):
        lines.extend(
            [
                f"### {index}. `{record.get('command', 'UNKNOWN')}`",
                "",
                f"- Status: `{record.get('status', 'UNKNOWN')}`",
                f"- Evidence: {record.get('evidence', 'UNKNOWN')}",
                "",
            ]
        )
    return "\n".join(lines)


def render_performance(spec: dict[str, Any]) -> str:
    perf = spec["performance"]
    base = perf["baseline"]
    candidate = perf.get("candidate")
    improvement = perf.get("improvement_percent")
    lines = [
        "# Performance Evidence",
        "",
        f"Bottleneck class: `{spec['optimization']['utilization_gap_class']}`",
        "",
        "## Baseline",
        "",
        f"- Command: `{base['command']}`",
        f"- Metric: `{base['metric']}`",
        f"- Value: `{base['value']} {base['unit']}`",
        f"- Samples: `{base['samples']}`",
        f"- Evidence: {base['evidence']}",
        "",
        "## Candidate",
        "",
    ]
    if candidate:
        lines.extend(
            [
                f"- Command: `{candidate['command']}`",
                f"- Metric: `{candidate['metric']}`",
                f"- Value: `{candidate['value']} {candidate['unit']}`",
                f"- Samples: `{candidate['samples']}`",
                f"- Evidence: {candidate['evidence']}",
            ]
        )
    else:
        lines.append("- Candidate measurement: `UNKNOWN`")
    lines.extend(
        [
            "",
            f"Improvement: `{'UNKNOWN' if improvement is None else str(improvement) + '%'}`",
            "",
            "## Comparison Method",
            "",
            perf["comparison_method"],
            "",
            "## Correctness Checks",
            "",
            *[f"- {item}" for item in perf["correctness_checks"]],
            "",
            "## Resource Checks",
            "",
            *[f"- {item}" for item in perf["resource_checks"]],
        ]
    )
    if perf.get("limitations"):
        lines.extend(["", "## Limitations", "", *[f"- {item}" for item in perf["limitations"]]])
    return "\n".join(lines)


def render_decision_record(spec: dict[str, Any]) -> str:
    route = spec["execution_route"]
    ledger = spec["decision_ledger"]
    decision = ledger["decision"]
    convergence = ledger["convergence"]
    lines = [
        "# Adaptive Decision Record",
        "",
        f"Reasoning depth: `{route['reasoning_depth']}`",
        f"Initial action: `{route['initial_action']}`",
        f"Final action: `{decision['final_action']}`",
        f"Cycle: `{ledger['cycle']}` of `{route['max_cycles']}`",
        f"Convergence: `{convergence['status']}`",
        "",
        "## Objective",
        "",
        ledger["objective"],
        "",
        "## Active Proof Obligations",
        "",
        "| ID | Status | Evidence |",
        "|---|---|---|",
    ]
    for proof in ledger["proof_obligations"]:
        evidence = "; ".join(proof.get("evidence", [])).replace("|", "\\|") or "None"
        lines.append(f"| {proof['id']} | {proof['status']} | {evidence} |")
    lines.extend(
        ["", "## Selected Options", "", *[f"- {item}" for item in ledger["selected_option_ids"]]]
    )
    lines.extend(["", "## Material Unknowns", ""])
    material = [
        item
        for item in ledger["unknowns"]
        if item.get("material") and item.get("disposition") != "resolved"
    ]
    lines.extend(
        [f"- {item['id']}: {item['description']} ({item['disposition']})" for item in material]
        or ["- None"]
    )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            decision["rationale"],
            "",
            "### Trade-offs",
            "",
            *([f"- {item}" for item in decision["tradeoffs"]] or ["- None"]),
            "",
            "### Rollback or Containment",
            "",
            decision["rollback_or_containment"],
            "",
            "## Stop Reason",
            "",
            convergence["stop_reason"],
        ]
    )
    return "\n".join(lines)


def render_revision_plan(synthesis: dict[str, Any]) -> str:
    findings = {item["id"]: item for item in synthesis["findings"]}
    lines = [
        "# CLI Revision Plan",
        "",
        f"Synthesis status: `{synthesis['synthesis_status']}`",
        f"All material findings synthesized: `{synthesis['all_material_findings_synthesized']}`",
        "",
        "## Selection Rationale",
        "",
        synthesis["selection_rationale"],
        "",
        "## Findings",
        "",
        "| ID | Kind | Severity | Scope | Status | Blocks release | Summary |",
        "|---|---|---:|---|---|---:|---|",
    ]
    for finding in synthesis["findings"]:
        summary = finding["summary"].replace("|", "\\|")
        lines.append(
            f"| {finding['id']} | {finding['kind']} | {finding['severity']} | {finding['scope']} | {finding['status']} | {finding['blocks_release']} | {summary} |"
        )
    lines.extend(["", "## Revision Targets", ""])
    for target in synthesis["targets"]:
        lines.extend(
            [
                f"### {target['id']}: {target['title']}",
                "",
                f"- Scope: `{target['scope']}`",
                f"- Source findings: {', '.join(target['source_finding_ids'])}",
                f"- Objective: {target['objective']}",
                f"- Options: {', '.join(target['option_ids'])}",
                "",
            ]
        )
    lines.extend(
        [
            "## Options and Leverage",
            "",
            "| ID | Targets | Scope | Score | Decision | Selected | Strategy |",
            "|---|---|---|---:|---|---:|---|",
        ]
    )
    for option in synthesis["options"]:
        strategy = option["strategy"].replace("|", "\\|")
        lines.append(
            f"| {option['id']} | {', '.join(option['target_ids'])} | {option['scope']} | {option['leverage_score']:.2f} | {option['decision']} | {option['selected']} | {strategy} |"
        )
    lines.extend(
        [
            "",
            "## Selected Options",
            "",
            *([f"- {item}" for item in synthesis["selected_option_ids"]] or ["- None"]),
            "",
            "## Unresolved Documentation-Code Divergence",
            "",
            *(
                [
                    f"- {item}: {findings[item]['summary']}"
                    for item in synthesis["unresolved_divergence_ids"]
                ]
                or ["- None"]
            ),
            "",
            "## Unknowns",
            "",
            *([f"- {item}" for item in synthesis["unknowns"]] or ["- None"]),
        ]
    )
    return "\n".join(lines)


def render_divergence_findings(synthesis: dict[str, Any]) -> str:
    findings = {item["id"]: item for item in synthesis["findings"]}
    unresolved = synthesis["unresolved_divergence_ids"]
    lines = ["# Documentation-Code Capability Divergence Findings", ""]
    if not unresolved:
        lines.append("No unresolved documentation-code capability divergence was recorded.")
        return "\n".join(lines)
    for finding_id in unresolved:
        finding = findings[finding_id]
        lines.extend(
            [
                f"## {finding_id}: {finding['summary']}",
                "",
                f"- Severity: `{finding['severity']}`",
                f"- Scope: `{finding['scope']}`",
                f"- Owner: `{finding['owner']}`",
                f"- Blocks release: `{finding['blocks_release']}`",
                f"- Divergence type: `{finding['divergence_type']}`",
                f"- Reconciliation: `{finding['reconciliation']}`",
                f"- Documentation claim: {finding['docs_claim']}",
                f"- Code observation: {finding['code_observation']}",
                f"- Recommended action: {finding['recommended_action']}",
                "- Evidence:",
                *[f"  - {item}" for item in finding["evidence"]],
                "",
            ]
        )
    return "\n".join(lines)


def render_pr_body(spec: dict[str, Any]) -> str:
    body = spec["pr_body"].rstrip()
    synthesis = spec["revision_synthesis"]
    findings = {item["id"]: item for item in synthesis["findings"]}
    unresolved = synthesis["unresolved_divergence_ids"]
    route = spec["execution_route"]
    ledger = spec["decision_ledger"]
    body += "\n\n## Adaptive Execution Decision\n\n"
    body += f"Initial action: `{route['initial_action']}`. Final action: `{ledger['decision']['final_action']}`. Reasoning depth: `{route['reasoning_depth']}`. Convergence: `{ledger['convergence']['status']}` after cycle `{ledger['cycle']}`. See `evidence/DECISION_RECORD.md`."
    body += "\n\n## CLI Revision Selection\n\n"
    body += f"Selected options: {', '.join(synthesis['selected_option_ids'])}. {synthesis['selection_rationale']}"
    body += "\n\n## Unresolved Documentation-Code Capability Divergence\n\n"
    if unresolved:
        for finding_id in unresolved:
            finding = findings[finding_id]
            body += f"- **{finding_id}** ({finding['scope']}, owner: `{finding['owner']}`): {finding['summary']} Next action: {finding['recommended_action']}\n"
    else:
        body += "- None.\n"
    return body


def render_wiring_map(wiring: dict[str, Any]) -> str:
    lines = [
        "# Wiring Map",
        "",
        f"Convergence: `{wiring['convergence_status']}` after `{wiring['convergence_passes']}` pass(es)",
        "",
        "## Entrypoints",
        "",
        *([f"- {item}" for item in wiring["entrypoints"]] or ["- None recorded"]),
        "",
        "## Registries and Dynamic Dispatch",
        "",
        *(
            [f"- {item}" for item in wiring["registries"]]
            or ["- None recorded; explicit inspection still required"]
        ),
        "",
        "## Feature Flags",
        "",
        *([f"- {item}" for item in wiring["feature_flags"]] or ["- None recorded"]),
        "",
        "## Signal Consumers",
        "",
        *([f"- {item}" for item in wiring["signal_consumers"]] or ["- None recorded"]),
        "",
        "## Producer to Consumer Edges",
        "",
        "| Producer | Consumer | Before | After | Evidence |",
        "|---|---|---:|---:|---|",
    ]
    for edge in wiring["edges"]:
        evidence = str(edge["evidence"]).replace("|", "\\|")
        lines.append(
            f"| {edge['producer']} | {edge['consumer']} | {edge['connected_before']} | {edge['connected_after']} | {evidence} |"
        )
    lines.extend(
        [
            "",
            "## Selected Findings",
            "",
            *([f"- {item}" for item in wiring["selected_finding_ids"]] or ["- None"]),
            "",
            "## Unresolved Unknowns",
            "",
            *([f"- {item}" for item in wiring["unresolved_unknowns"]] or ["- None"]),
        ]
    )
    return "\n".join(lines)


def issue_filename(issue: dict[str, Any], index: int) -> str:
    raw = str(issue.get("fingerprint", f"issue-{index}"))
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in raw).strip("-")
    return f"ISSUE-{safe or index}.md"


def render_issue(issue: dict[str, Any], index: int) -> str:
    if isinstance(issue.get("markdown"), str) and issue["markdown"].strip():
        return issue["markdown"]
    return f"""# {issue.get("title", f"Blocked root cause {index}")}

- Owner: `{issue.get("owner", "UNKNOWN")}`
- Observed failure: {issue.get("observed_failure", "UNKNOWN")}
- Evidence: {issue.get("evidence", "UNKNOWN")}
- Acceptance criteria: {issue.get("acceptance_criteria", "UNKNOWN")}
"""


def generate_checksums(pack_root: Path) -> None:
    checksum_path = pack_root / "evidence" / "checksums.sha256"
    lines = []
    for path in sorted(pack_root.rglob("*")):
        if path.is_file() and path != checksum_path and path.suffix != ".gz":
            under_root(pack_root, path, label="checksums")
            lines.append(f"{sha256_file(path)}  {path.relative_to(pack_root).as_posix()}")
    write_text(pack_root, checksum_path, "\n".join(lines))


def add_deterministic(tar: tarfile.TarFile, source: Path, arcname: str, *, pack_root: Path) -> None:
    """Add ``source`` under ``arcname``, confining every path to ``pack_root``.

    File bytes are read after an ``under_root`` gate and fed via BytesIO so the
    tar writer never joins unsanitized archive-entry names onto a filesystem path.
    """
    root = pack_root.resolve()
    resolved = under_root(root, source, label="archive source")
    if resolved.is_file():
        payload = resolved.read_bytes()
        info = tarfile.TarInfo(name=arcname)
        info.size = len(payload)
        info.mtime = 0
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        tar.addfile(info, io.BytesIO(payload))
        return
    if not resolved.is_dir():
        raise PackError(f"archive source is neither file nor directory: {source}")
    info = tarfile.TarInfo(name=arcname)
    info.type = tarfile.DIRTYPE
    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mode = 0o755
    tar.addfile(info)
    for child in sorted(resolved.iterdir(), key=lambda p: p.name):
        segment = child.name.replace("/", "_").replace("\\", "_")
        if segment in ("", ".", ".."):
            raise PackError(f"refusing unsafe archive segment: {child.name!r}")
        add_deterministic(tar, child, f"{arcname}/{segment}", pack_root=root)


def create_archive(pack_root: Path, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with archive_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tar:
                add_deterministic(tar, pack_root, pack_root.name, pack_root=pack_root)


def build(spec_path: Path, repo_root: Path, output_parent: Path) -> tuple[Path, Path]:
    spec = load_spec(spec_path)
    schema_validate(spec, "pack-spec.schema.json", "spec")
    validate_spec(spec)
    ensure_git_repo(repo_root)
    pack_name = require_string(spec, "pack_name")
    pack_root = output_parent / pack_name
    if pack_root.exists():
        shutil.rmtree(pack_root)
    pack_root.mkdir(parents=True)

    changed_files = list(spec["changed_files"])
    deleted_files = set(spec.get("deleted_files", []))
    patch = build_patch(repo_root, spec["base_ref"], changed_files)
    copied: list[str] = []
    for raw in changed_files:
        if raw in deleted_files:
            continue
        relative = safe_relative(raw)
        source = repo_root / relative
        if not source.is_file():
            raise PackError(f"changed file does not exist: {raw}; mark it deleted when appropriate")
        destination = pack_root / "change" / "files" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(raw)

    patch_path = pack_root / "change" / "commit.patch"
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.write_bytes(patch)
    write_text(
        pack_root,
        pack_root / "change" / "OPTIMIZATION_PLAN.json",
        json.dumps(spec["optimization"], indent=2, sort_keys=True),
    )
    write_text(
        pack_root,
        pack_root / "evidence" / "EXECUTION_ROUTE.json",
        json.dumps(spec["execution_route"], indent=2, sort_keys=True),
    )
    write_text(
        pack_root,
        pack_root / "evidence" / "DECISION_LEDGER.json",
        json.dumps(spec["decision_ledger"], indent=2, sort_keys=True),
    )
    write_text(
        pack_root, pack_root / "evidence" / "DECISION_RECORD.md", render_decision_record(spec)
    )
    write_text(
        pack_root,
        pack_root / "evidence" / "CLI_REVISION_SYNTHESIS.json",
        json.dumps(spec["revision_synthesis"], indent=2, sort_keys=True),
    )
    write_text(
        pack_root,
        pack_root / "evidence" / "CLI_REVISION_PLAN.md",
        render_revision_plan(spec["revision_synthesis"]),
    )
    write_text(
        pack_root,
        pack_root / "evidence" / "DOCS_CODE_DIVERGENCE_FINDINGS.md",
        render_divergence_findings(spec["revision_synthesis"]),
    )
    write_text(pack_root, pack_root / "README.md", render_readme(spec))
    write_text(pack_root, pack_root / "pr" / "COMMIT_MESSAGE.txt", spec["commit_message"])
    write_text(pack_root, pack_root / "pr" / "PR_BODY.md", render_pr_body(spec))
    write_text(pack_root, pack_root / "pr" / "PR_CHECKLIST.md", render_pr_checklist(spec))
    write_text(pack_root, pack_root / "deploy" / "DEPLOY_PLAYBOOK.md", spec["deploy"]["playbook"])
    write_text(
        pack_root,
        pack_root / "deploy" / "RELEASE_CHECKLIST.md",
        spec["deploy"]["release_checklist"],
    )
    write_text(
        pack_root, pack_root / "deploy" / "ROLLBACK_PLAYBOOK.md", spec["rollback"]["playbook"]
    )
    write_text(pack_root, pack_root / "handoff" / "AGENT_HANDOFF.md", spec["handoff"]["markdown"])
    write_text(
        pack_root,
        pack_root / "handoff" / "NEXT_AGENT_TASK.json",
        json.dumps(spec["handoff"]["next_agent_task"], indent=2, sort_keys=True),
    )
    write_text(pack_root, pack_root / "evidence" / "VALIDATION.md", render_validation(spec))
    write_text(pack_root, pack_root / "evidence" / "PERFORMANCE.md", render_performance(spec))
    wiring = spec.get("wiring")
    if isinstance(wiring, dict) and wiring.get("analysis_performed"):
        write_text(pack_root, pack_root / "evidence" / "WIRING_MAP.md", render_wiring_map(wiring))
        write_text(
            pack_root,
            pack_root / "evidence" / "LATENT_CAPABILITY_FINDINGS.json",
            json.dumps(wiring, indent=2, sort_keys=True),
        )

    commands_path = pack_root / "evidence" / "commands.jsonl"
    commands_path.parent.mkdir(parents=True, exist_ok=True)
    with commands_path.open("w", encoding="utf-8") as handle:
        for record in spec["validation"]["commands"]:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    for index, issue in enumerate(spec.get("issues", []), start=1):
        write_text(
            pack_root,
            pack_root / "issues" / issue_filename(issue, index),
            render_issue(issue, index),
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "pack_name": pack_name,
        "version": spec["version"],
        "repository": spec["repository"],
        "base_ref": spec["base_ref"],
        "branch": spec["branch"],
        "status": spec["status"],
        "changed_files": changed_files,
        "copied_files": copied,
        "deleted_files": sorted(deleted_files),
        "patch_sha256": sha256_bytes(patch),
        "created_utc": created_utc(spec),
        "reproducible": bool(spec.get("created_utc")) or bool(os.environ.get("SOURCE_DATE_EPOCH")),
        "generator": GENERATOR,
        "utilization_gap_class": spec["optimization"]["utilization_gap_class"],
        "ownership": spec["optimization"]["ownership"],
        "improvement_percent": spec["performance"].get("improvement_percent"),
        "performance": {
            "metric": spec["performance"]["baseline"]["metric"],
            "unit": spec["performance"]["baseline"]["unit"],
            "direction": spec["performance"].get("direction", "lower_is_better"),
            "baseline_value": spec["performance"]["baseline"]["value"],
            "candidate_value": (spec["performance"].get("candidate") or {}).get("value"),
            "improvement_percent": spec["performance"].get("improvement_percent"),
        },
        "wiring_analysis_performed": bool((spec.get("wiring") or {}).get("analysis_performed")),
        "selected_wiring_findings": list(
            (spec.get("wiring") or {}).get("selected_finding_ids", [])
        ),
        "unresolved_wiring_unknowns": list(
            (spec.get("wiring") or {}).get("unresolved_unknowns", [])
        ),
        "revision_synthesis_status": spec["revision_synthesis"]["synthesis_status"],
        "revision_finding_count": len(spec["revision_synthesis"]["findings"]),
        "revision_target_count": len(spec["revision_synthesis"]["targets"]),
        "revision_option_count": len(spec["revision_synthesis"]["options"]),
        "selected_revision_options": list(spec["revision_synthesis"]["selected_option_ids"]),
        "unresolved_docs_code_divergences": list(
            spec["revision_synthesis"]["unresolved_divergence_ids"]
        ),
        "highest_selected_leverage_score": max(
            (
                option["leverage_score"]
                for option in spec["revision_synthesis"]["options"]
                if option["id"] in spec["revision_synthesis"]["selected_option_ids"]
            ),
            default=None,
        ),
        "reasoning_depth": spec["execution_route"]["reasoning_depth"],
        "initial_action": spec["execution_route"]["initial_action"],
        "final_action": spec["decision_ledger"]["decision"]["final_action"],
        "proof_obligation_count": len(spec["decision_ledger"]["proof_obligations"]),
        "satisfied_proof_obligation_count": sum(
            1
            for item in spec["decision_ledger"]["proof_obligations"]
            if item["status"] == "satisfied"
        ),
        "unresolved_material_unknowns": list(
            spec["decision_ledger"]["convergence"]["remaining_material_unknown_ids"]
        ),
        "decision_convergence_status": spec["decision_ledger"]["convergence"]["status"],
    }
    schema_validate(manifest, "pack-manifest.schema.json", "manifest")
    write_text(
        pack_root, pack_root / "MANIFEST.json", json.dumps(manifest, indent=2, sort_keys=True)
    )
    generate_checksums(pack_root)
    archive_path = output_parent / f"{pack_name}.tar.gz"
    if archive_path.exists():
        archive_path.unlink()
    create_archive(pack_root, archive_path)
    return pack_root, archive_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        pack_root, archive_path = build(
            args.spec.resolve(), args.repo_root.resolve(), args.output.resolve()
        )
    except PackError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"pack_root": str(pack_root), "archive": str(archive_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
