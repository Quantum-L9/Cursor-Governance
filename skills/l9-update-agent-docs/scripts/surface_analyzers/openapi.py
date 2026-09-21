"""Deterministic structural OpenAPI contract assessment.

This analyzer identifies malformed or incomplete API contracts but never authors
an API repair. All findings hand off to the declared API contract owner.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

_HTTP_METHODS = frozenset({"get", "put", "post", "delete", "options", "head", "patch", "trace"})


def _finding(
    rule_id: str,
    *,
    property_name: str,
    observed: str,
    expected: str,
    line: int | None,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": "material",
        "property": property_name,
        "observed_state": observed,
        "expected_state": expected,
        "line": line,
        "remediation_class": "HANDOFF",
    }


def _line_for(text: str, needle: str) -> int | None:
    for number, row in enumerate(text.splitlines(), start=1):
        if needle in row:
            return number
    return None


def _load(path: Path, text: str) -> Any:
    return json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)


def analyze(root: Path, target: Path) -> dict[str, Any]:
    del root
    if not target.is_file():
        return {
            "status": "BLOCKED",
            "findings": [],
            "blockers": [f"OpenAPI target is missing: {target}"],
        }
    try:
        text = target.read_text(encoding="utf-8")
        data = _load(target, text)
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        return {
            "status": "BLOCKED",
            "findings": [],
            "blockers": [f"OpenAPI document is unreadable: {exc}"],
        }
    if not isinstance(data, dict):
        return {"status": "BLOCKED", "findings": [], "blockers": ["OpenAPI root must be a mapping"]}

    findings: list[dict[str, Any]] = []
    version = data.get("openapi")
    if not isinstance(version, str) or not version.startswith("3."):
        findings.append(
            _finding(
                "openapi.version.supported",
                property_name="openapi",
                observed=repr(version),
                expected="an OpenAPI 3.x version string",
                line=_line_for(text, "openapi"),
            )
        )
    paths = data.get("paths")
    if not isinstance(paths, dict):
        findings.append(
            _finding(
                "openapi.paths.mapping",
                property_name="paths",
                observed=type(paths).__name__,
                expected="a mapping of slash-prefixed paths to operations",
                line=_line_for(text, "paths"),
            )
        )
    else:
        for path_name, path_item in paths.items():
            if not isinstance(path_name, str) or not path_name.startswith("/"):
                findings.append(
                    _finding(
                        "openapi.path.absolute",
                        property_name="paths key",
                        observed=repr(path_name),
                        expected="every OpenAPI path begins with '/'",
                        line=_line_for(text, str(path_name)),
                    )
                )
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method.lower() not in _HTTP_METHODS or not isinstance(operation, dict):
                    continue
                if not isinstance(operation.get("responses"), dict) or not operation["responses"]:
                    findings.append(
                        _finding(
                            "openapi.operation.responses",
                            property_name="operation.responses",
                            observed=f"{method.upper()} {path_name} has no responses",
                            expected=(
                                "every declared operation contains a non-empty responses mapping"
                            ),
                            line=_line_for(text, method),
                        )
                    )
    return {
        "status": "NEEDS_IMPROVEMENT" if findings else "PASS",
        "findings": findings,
        "blockers": [],
    }
