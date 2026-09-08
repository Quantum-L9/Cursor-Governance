"""Deterministic Makefile operational-contract checks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_PYTHON_ASSIGNMENT = re.compile(r"^\s*PYTHON\s*[:?+]?=", re.MULTILINE)
_DIRECT_PYTHON = re.compile(
    r"^(?:[@+\-]\s*)?(?:[A-Za-z_][A-Za-z0-9_]*=[^\s]+\s+)*(?:/usr/bin/)?python(?:3(?:\.\d+)?)?\b"
)
_SCRIPT_REF = re.compile(r"(?<![A-Za-z0-9_$])([A-Za-z0-9_./-]+\.py)(?![A-Za-z0-9_])")


def _finding(
    rule_id: str,
    *,
    property_name: str,
    observed: str,
    expected: str,
    line: int | None,
    remediation_class: str = "SURGICAL",
    severity: str = "material",
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "property": property_name,
        "observed_state": observed,
        "expected_state": expected,
        "line": line,
        "remediation_class": remediation_class,
    }


def analyze(root: Path, target: Path) -> dict[str, Any]:
    if not target.is_file():
        return {
            "status": "BLOCKED",
            "findings": [],
            "blockers": [f"Makefile target is missing: {target.relative_to(root)}"],
        }

    text = target.read_text(encoding="utf-8")
    findings: list[dict[str, Any]] = []
    has_locked_python = bool(_PYTHON_ASSIGNMENT.search(text))

    for lineno, raw in enumerate(text.splitlines(), start=1):
        if not raw.startswith("\t"):
            continue
        recipe = raw[1:].strip()
        if has_locked_python and "$(PYTHON)" not in recipe and _DIRECT_PYTHON.match(recipe):
            findings.append(
                _finding(
                    "make.recipe.locked_python",
                    property_name="python_runner_consistency",
                    observed=recipe,
                    expected="recipe invokes $(PYTHON) when the Makefile declares a locked PYTHON runner",
                    line=lineno,
                )
            )

        for match in _SCRIPT_REF.finditer(recipe):
            rel = match.group(1)
            if rel.startswith("/") or "$" in rel:
                continue
            if not (root / rel).is_file():
                findings.append(
                    _finding(
                        "make.recipe.script_resolution",
                        property_name="referenced_script_resolves",
                        observed=rel,
                        expected="literal repository-local script reference resolves to an existing file",
                        line=lineno,
                    )
                )

    return {
        "status": "NEEDS_IMPROVEMENT" if findings else "PASS",
        "findings": findings,
        "blockers": [],
    }
