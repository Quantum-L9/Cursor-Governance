"""Deterministic pyproject.toml operational-contract checks."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

_PYTHON_FLOOR = re.compile(r">=\s*(\d+)\.(\d+)")


def _finding(
    rule_id: str,
    *,
    property_name: str,
    observed: str,
    expected: str,
    line: int | None,
    remediation_class: str = "SURGICAL",
    severity: str = "material",
    source: str | None = None,
) -> dict[str, Any]:
    finding = {
        "rule_id": rule_id,
        "severity": severity,
        "property": property_name,
        "observed_state": observed,
        "expected_state": expected,
        "line": line,
        "remediation_class": remediation_class,
    }
    if source is not None:
        finding["source"] = source
    return finding


def _line_for(text: str, needle: str) -> int | None:
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if needle in raw:
            return lineno
    return None


def _python_floor(requires_python: str) -> str | None:
    match = _PYTHON_FLOOR.search(requires_python)
    return f"{match.group(1)}.{match.group(2)}" if match else None


def _self_test_findings(
    root: Path,
    data: dict[str, Any],
    text: str,
) -> list[dict[str, Any]]:
    self_tests = sorted(root.glob("skills/*/scripts/self_test.py"))
    contract_rel = "ops/config/python-contract.json"
    contract_path = root / contract_rel
    registered_roots: set[str] | None = None
    findings: list[dict[str, Any]] = []

    if contract_path.is_file():
        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            findings.append(
                _finding(
                    "python.self_test.contract_parse",
                    property_name="python_contract_parseability",
                    observed=f"{contract_rel} could not be parsed",
                    expected="canonical Python contract is valid JSON",
                    line=None,
                    remediation_class="HANDOFF",
                    severity="blocking",
                    source=contract_rel,
                )
            )
        else:
            registered_roots = set(contract.get("skill_self_test_roots") or [])

    pytest_options = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    addopts = str(pytest_options.get("addopts") or "")
    conftest_path = root / "conftest.py"
    conftest = conftest_path.read_text(encoding="utf-8") if conftest_path.is_file() else ""

    for path in self_tests:
        rel = path.relative_to(root).as_posix()
        skill_root = "/".join(rel.split("/")[:2])
        if registered_roots is not None and skill_root not in registered_roots:
            findings.append(
                _finding(
                    "python.self_test.registry",
                    property_name="self_test_registry_coverage",
                    observed=f"{skill_root} missing from skill_self_test_roots",
                    expected=(
                        "every live skill self_test.py is registered in "
                        "ops/config/python-contract.json"
                    ),
                    line=None,
                    source=contract_rel,
                )
            )
        if f"--ignore={rel}" not in addopts and rel not in conftest:
            findings.append(
                _finding(
                    "python.self_test.collection_guard",
                    property_name="root_pytest_collection_guard",
                    observed=f"{rel} is collectable by root pytest",
                    expected=(
                        "self_test.py is excluded by pyproject addopts or root "
                        "conftest collect_ignore"
                    ),
                    line=_line_for(text, "addopts"),
                    source="pyproject.toml",
                )
            )
    return findings


def analyze(root: Path, target: Path) -> dict[str, Any]:
    if not target.is_file():
        return {
            "status": "BLOCKED",
            "findings": [],
            "blockers": [f"pyproject target is missing: {target.relative_to(root)}"],
        }

    text = target.read_text(encoding="utf-8")
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        return {
            "status": "BLOCKED",
            "findings": [],
            "blockers": [f"pyproject.toml is invalid TOML: {exc}"],
        }

    findings: list[dict[str, Any]] = []
    project = data.get("project", {})
    tool = data.get("tool", {})
    requires_python = str(project.get("requires-python") or "")
    floor = _python_floor(requires_python)
    if floor:
        expected_ruff = "py" + floor.replace(".", "")
        version_fields = (
            ("mypy", "python_version", floor, "python_version"),
            ("pyright", "pythonVersion", floor, "pythonVersion"),
            ("ruff", "target-version", expected_ruff, "target-version"),
        )
        for section, key, expected, needle in version_fields:
            value = tool.get(section, {}).get(key)
            if value is None:
                continue
            observed = str(value)
            if observed != expected:
                findings.append(
                    _finding(
                        "python.interpreter.version_alignment",
                        property_name=f"tool.{section}.{key}",
                        observed=observed,
                        expected=expected,
                        line=_line_for(text, needle),
                    )
                )

    if "uv" in tool and not (root / "uv.lock").is_file():
        findings.append(
            _finding(
                "python.uv.lock_presence",
                property_name="uv_lock_consistency",
                observed="[tool.uv] is declared but uv.lock is absent",
                expected=(
                    "uv.lock exists when the repository declares uv as its "
                    "project environment contract"
                ),
                line=_line_for(text, "[tool.uv]"),
            )
        )

    findings.extend(_self_test_findings(root, data, text))
    return {
        "status": "NEEDS_IMPROVEMENT" if findings else "PASS",
        "findings": findings,
        "blockers": [],
    }
