#!/usr/bin/env python3
"""Validate Cursor-Governance normative organization-policy artifacts.

This validator intentionally validates repository-owned policy semantics.
It does not claim that GitHub rulesets, required checks, external assurance,
or consumer bindings are deployed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "PyYAML is required. Install repository development dependencies "
        "or run in the repository CI environment."
    ) from exc

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "ORG_INVARIANTS.yaml"
ASSERTIONS_PATH = ROOT / "governance" / "ASSERTION_TYPES.yaml"
SCHEMA_PATH = ROOT / "schemas" / "org-invariants.schema.json"
RELEASE_SCHEMA_PATH = ROOT / "releases" / "POLICY_RELEASE.schema.yaml"

INVARIANT_ID = re.compile(r"^L9-ORG-[0-9]{3}$")
CONTROL_ID = re.compile(r"^L9-CTRL-[0-9]{3}$")
ASSERTION_TYPE = re.compile(r"^[a-z][a-z0-9_]*$")

ALLOWED_SEVERITIES = {"critical", "high", "medium", "low"}
ALLOWED_POLICY_STATES = {"proposed", "active", "deprecated", "retired"}
ALLOWED_IMPLEMENTATION_STATES = {
    "absent",
    "planned",
    "implemented",
    "verified",
    "degraded",
    "disabled",
}
ALLOWED_ENFORCEMENT_STATES = {
    "unenforced",
    "advisory",
    "blocking",
    "bypassed",
    "indeterminate",
}


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(
                f"duplicate YAML mapping key {key!r} at line {key_node.start_mark.line + 1}"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    path: str

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "path": self.path,
        }


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.load(handle, Loader=UniqueKeyLoader)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def require_mapping(value: Any, path: str, findings: list[Finding]) -> dict[str, Any]:
    if not isinstance(value, dict):
        findings.append(Finding("TYPE_MAPPING_REQUIRED", "expected a mapping", path))
        return {}
    return value


def require_list(value: Any, path: str, findings: list[Finding]) -> list[Any]:
    if not isinstance(value, list):
        findings.append(Finding("TYPE_LIST_REQUIRED", "expected a list", path))
        return []
    return value


def duplicate_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def validate_schema_document(schema: Any, findings: list[Finding]) -> None:
    schema_map = require_mapping(schema, "schema", findings)
    if schema_map.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        findings.append(
            Finding(
                "SCHEMA_DRAFT_INVALID",
                "policy schema must declare JSON Schema draft 2020-12",
                "schemas/org-invariants.schema.json.$schema",
            )
        )
    if schema_map.get("additionalProperties") is not False:
        findings.append(
            Finding(
                "SCHEMA_TOP_LEVEL_OPEN",
                "top-level policy schema must reject unknown fields",
                "schemas/org-invariants.schema.json.additionalProperties",
            )
        )


def assertion_versions(registry: Any, findings: list[Finding]) -> set[tuple[str, int]]:
    registry_map = require_mapping(registry, "assertion_registry", findings)
    entries = require_list(
        registry_map.get("assertion_types"),
        "assertion_registry.assertion_types",
        findings,
    )

    resolved: set[tuple[str, int]] = set()
    for index, raw_entry in enumerate(entries):
        path = f"assertion_registry.assertion_types[{index}]"
        entry = require_mapping(raw_entry, path, findings)
        assertion_type = entry.get("type")
        version = entry.get("version")
        if not isinstance(assertion_type, str) or not ASSERTION_TYPE.fullmatch(assertion_type):
            findings.append(
                Finding(
                    "ASSERTION_TYPE_INVALID",
                    "assertion type must match ^[a-z][a-z0-9_]*$",
                    f"{path}.type",
                )
            )
            continue
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            findings.append(
                Finding(
                    "ASSERTION_VERSION_INVALID",
                    "assertion version must be a positive integer",
                    f"{path}.version",
                )
            )
            continue
        key = (assertion_type, version)
        if key in resolved:
            findings.append(
                Finding(
                    "ASSERTION_DUPLICATE",
                    f"duplicate assertion registration {assertion_type}@{version}",
                    path,
                )
            )
        resolved.add(key)
        for required_field in (
            "purpose",
            "required_inputs",
            "normalization",
            "pass_condition",
            "fail_condition",
            "unknown_condition",
            "fail_behavior",
            "compatibility_rules",
        ):
            if required_field not in entry:
                findings.append(
                    Finding(
                        "ASSERTION_FIELD_MISSING",
                        f"missing required assertion field {required_field}",
                        path,
                    )
                )
    return resolved


def validate_policy(
    policy: Any,
    registered_assertions: set[tuple[str, int]],
    findings: list[Finding],
) -> None:
    policy_map = require_mapping(policy, "policy", findings)

    required_top_level = {
        "l9_schema",
        "artifact_type",
        "status",
        "canonical",
        "metadata",
        "invariants",
    }
    for field in sorted(required_top_level - set(policy_map)):
        findings.append(
            Finding(
                "POLICY_FIELD_MISSING",
                f"missing required top-level field {field}",
                f"policy.{field}",
            )
        )
    if policy_map.get("artifact_type") != "governance_policy":
        findings.append(
            Finding(
                "POLICY_ARTIFACT_TYPE_INVALID",
                "artifact_type must be governance_policy",
                "policy.artifact_type",
            )
        )
    if policy_map.get("canonical") is not True:
        findings.append(
            Finding(
                "POLICY_NOT_CANONICAL",
                "canonical policy must declare canonical: true",
                "policy.canonical",
            )
        )
    status = policy_map.get("status")
    if status not in ALLOWED_POLICY_STATES:
        findings.append(
            Finding(
                "POLICY_STATUS_INVALID",
                f"status must be one of {sorted(ALLOWED_POLICY_STATES)}",
                "policy.status",
            )
        )
    metadata = require_mapping(policy_map.get("metadata"), "policy.metadata", findings)
    if not metadata.get("policy_id"):
        findings.append(
            Finding(
                "POLICY_ID_MISSING",
                "metadata.policy_id is required",
                "policy.metadata.policy_id",
            )
        )
    if not metadata.get("policy_version"):
        findings.append(
            Finding(
                "POLICY_VERSION_MISSING",
                "metadata.policy_version is required",
                "policy.metadata.policy_version",
            )
        )
    invariants = require_list(
        policy_map.get("invariants"),
        "policy.invariants",
        findings,
    )
    invariant_ids: list[str] = []
    referenced_assertions: list[tuple[str, int, str]] = []
    for index, raw_invariant in enumerate(invariants):
        path = f"policy.invariants[{index}]"
        invariant = require_mapping(raw_invariant, path, findings)
        invariant_id = invariant.get("id")
        if not isinstance(invariant_id, str) or not INVARIANT_ID.fullmatch(invariant_id):
            findings.append(
                Finding(
                    "INVARIANT_ID_INVALID",
                    "invariant id must match ^L9-ORG-[0-9]{3}$",
                    f"{path}.id",
                )
            )
        else:
            invariant_ids.append(invariant_id)
        if not isinstance(invariant.get("title"), str) or not invariant.get("title", "").strip():
            findings.append(
                Finding(
                    "INVARIANT_TITLE_MISSING",
                    "invariant title is required",
                    f"{path}.title",
                )
            )
        severity = invariant.get("severity")
        if severity not in ALLOWED_SEVERITIES:
            findings.append(
                Finding(
                    "INVARIANT_SEVERITY_INVALID",
                    f"severity must be one of {sorted(ALLOWED_SEVERITIES)}",
                    f"{path}.severity",
                )
            )
        policy_state = invariant.get("policy_state", invariant.get("status"))
        if policy_state is not None and policy_state not in ALLOWED_POLICY_STATES:
            findings.append(
                Finding(
                    "INVARIANT_POLICY_STATE_INVALID",
                    f"policy state must be one of {sorted(ALLOWED_POLICY_STATES)}",
                    f"{path}.policy_state",
                )
            )
        if severity == "critical":
            violation = invariant.get("violation")
            if not isinstance(violation, dict):
                findings.append(
                    Finding(
                        "CRITICAL_VIOLATION_MISSING",
                        "critical invariant requires a violation mapping",
                        f"{path}.violation",
                    )
                )
            else:
                if not violation.get("code"):
                    findings.append(
                        Finding(
                            "CRITICAL_VIOLATION_CODE_MISSING",
                            "critical invariant requires violation.code",
                            f"{path}.violation.code",
                        )
                    )
                if not violation.get("action"):
                    findings.append(
                        Finding(
                            "CRITICAL_VIOLATION_ACTION_MISSING",
                            "critical invariant requires violation.action",
                            f"{path}.violation.action",
                        )
                    )
        assertion = invariant.get("assertion")
        if assertion is not None:
            assertion_map = require_mapping(
                assertion,
                f"{path}.assertion",
                findings,
            )
            assertion_type = assertion_map.get("type")
            assertion_version = assertion_map.get("version")
            if not isinstance(assertion_type, str):
                findings.append(
                    Finding(
                        "ASSERTION_REFERENCE_TYPE_MISSING",
                        "assertion.type is required",
                        f"{path}.assertion.type",
                    )
                )
            if (
                not isinstance(assertion_version, int)
                or isinstance(assertion_version, bool)
                or assertion_version < 1
            ):
                findings.append(
                    Finding(
                        "ASSERTION_REFERENCE_VERSION_INVALID",
                        "assertion.version must be a positive integer",
                        f"{path}.assertion.version",
                    )
                )
            if isinstance(assertion_type, str) and isinstance(assertion_version, int):
                referenced_assertions.append((assertion_type, assertion_version, path))
        assurance = invariant.get("assurance")
        if isinstance(assurance, dict):
            enforcement_state = assurance.get("effective_enforcement_state")
            if (
                enforcement_state is not None
                and enforcement_state not in ALLOWED_ENFORCEMENT_STATES
            ):
                findings.append(
                    Finding(
                        "ASSURANCE_ENFORCEMENT_STATE_INVALID",
                        "unsupported effective enforcement state",
                        f"{path}.assurance.effective_enforcement_state",
                    )
                )
    for duplicate in duplicate_values(invariant_ids):
        findings.append(
            Finding(
                "INVARIANT_ID_DUPLICATE",
                f"duplicate invariant id {duplicate}",
                "policy.invariants",
            )
        )
    for assertion_type, version, path in referenced_assertions:
        if (assertion_type, version) not in registered_assertions:
            findings.append(
                Finding(
                    "ASSERTION_REFERENCE_UNRESOLVED",
                    f"unregistered assertion {assertion_type}@{version}",
                    f"{path}.assertion",
                )
            )
    controls = policy_map.get("control_registry", [])
    if controls is not None:
        controls_list = require_list(controls, "policy.control_registry", findings)
        control_ids: list[str] = []
        for index, raw_control in enumerate(controls_list):
            path = f"policy.control_registry[{index}]"
            control = require_mapping(raw_control, path, findings)
            control_id = control.get("id")
            if not isinstance(control_id, str) or not CONTROL_ID.fullmatch(control_id):
                findings.append(
                    Finding(
                        "CONTROL_ID_INVALID",
                        "control id must match ^L9-CTRL-[0-9]{3}$",
                        f"{path}.id",
                    )
                )
            else:
                control_ids.append(control_id)
            implementation_state = control.get("implementation_state")
            if (
                implementation_state is not None
                and implementation_state not in ALLOWED_IMPLEMENTATION_STATES
            ):
                findings.append(
                    Finding(
                        "CONTROL_IMPLEMENTATION_STATE_INVALID",
                        "unsupported control implementation state",
                        f"{path}.implementation_state",
                    )
                )
            enforcement_state = control.get("enforcement_state")
            if (
                enforcement_state is not None
                and enforcement_state not in ALLOWED_ENFORCEMENT_STATES
            ):
                findings.append(
                    Finding(
                        "CONTROL_ENFORCEMENT_STATE_INVALID",
                        "unsupported control enforcement state",
                        f"{path}.enforcement_state",
                    )
                )
            if enforcement_state == "blocking":
                evidence = control.get("evidence")
                if not isinstance(evidence, list) or not evidence:
                    findings.append(
                        Finding(
                            "FALSE_BLOCKING_CLAIM",
                            "blocking control requires non-empty evidence",
                            f"{path}.evidence",
                        )
                    )
                if implementation_state != "verified":
                    findings.append(
                        Finding(
                            "FALSE_BLOCKING_IMPLEMENTATION_STATE",
                            "blocking control must have implementation_state verified",
                            f"{path}.implementation_state",
                        )
                    )
            covers = control.get("covers", [])
            if isinstance(covers, list):
                known_ids = set(invariant_ids)
                for covered_id in covers:
                    if covered_id not in known_ids:
                        findings.append(
                            Finding(
                                "CONTROL_REFERENCE_UNRESOLVED",
                                f"control references unknown invariant {covered_id}",
                                f"{path}.covers",
                            )
                        )
        for duplicate in duplicate_values(control_ids):
            findings.append(
                Finding(
                    "CONTROL_ID_DUPLICATE",
                    f"duplicate control id {duplicate}",
                    "policy.control_registry",
                )
            )


def validate_release_schema(schema: Any, findings: list[Finding]) -> None:
    schema_map = require_mapping(schema, "release_schema", findings)
    if schema_map.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        findings.append(
            Finding(
                "RELEASE_SCHEMA_DRAFT_INVALID",
                "release schema must declare JSON Schema draft 2020-12",
                "releases/POLICY_RELEASE.schema.yaml.$schema",
            )
        )

    properties = require_mapping(
        schema_map.get("properties"),
        "release_schema.properties",
        findings,
    )
    commit_schema = require_mapping(
        properties.get("canonical_commit"),
        "release_schema.properties.canonical_commit",
        findings,
    )
    if commit_schema.get("pattern") != "^[0-9a-f]{40}$":
        findings.append(
            Finding(
                "RELEASE_COMMIT_NOT_IMMUTABLE",
                "canonical_commit must require a full 40-character lowercase SHA",
                "release_schema.properties.canonical_commit.pattern",
            )
        )
    if schema_map.get("additionalProperties") is not False:
        findings.append(
            Finding(
                "RELEASE_SCHEMA_OPEN",
                "release schema must reject unknown top-level fields",
                "release_schema.additionalProperties",
            )
        )


def run_validation(root: Path = ROOT) -> list[Finding]:
    findings: list[Finding] = []

    required_paths = (
        root / "ORG_INVARIANTS.yaml",
        root / "governance" / "ASSERTION_TYPES.yaml",
        root / "schemas" / "org-invariants.schema.json",
        root / "releases" / "POLICY_RELEASE.schema.yaml",
    )
    for path in required_paths:
        if not path.is_file():
            findings.append(
                Finding(
                    "REQUIRED_FILE_MISSING",
                    "required normative artifact is missing",
                    str(path.relative_to(root)),
                )
            )
    if findings:
        return findings
    try:
        policy = load_yaml(root / "ORG_INVARIANTS.yaml")
        assertions = load_yaml(root / "governance" / "ASSERTION_TYPES.yaml")
        schema = load_json(root / "schemas" / "org-invariants.schema.json")
        release_schema = load_yaml(root / "releases" / "POLICY_RELEASE.schema.yaml")
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        return [
            Finding(
                "PARSE_FAILURE",
                str(exc),
                "repository",
            )
        ]
    validate_schema_document(schema, findings)
    registered = assertion_versions(assertions, findings)
    validate_policy(policy, registered, findings)
    validate_release_schema(release_schema, findings)
    return findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    findings = run_validation()

    if args.format == "json":
        print(
            json.dumps(
                {
                    "result": "pass" if not findings else "fail",
                    "finding_count": len(findings),
                    "findings": [finding.as_dict() for finding in findings],
                },
                indent=2,
                sort_keys=True,
            )
        )
    elif findings:
        for finding in findings:
            print(
                f"{finding.code}: {finding.path}: {finding.message}",
                file=sys.stderr,
            )
    else:
        print("Organization policy validation passed.")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
