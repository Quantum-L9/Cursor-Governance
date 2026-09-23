"""Deterministic pyproject.toml operational-contract assessment.

Two halves, kept apart on purpose. `python_project` observes what a
Python project declares. This module resolves what *this repository*
expects those declarations to mean, and assesses one against the other.

Repo Docs does not become the semantic owner of Python packaging by
detecting a defect here. `ops/config/python-contract.json` remains the
repository's test-suite topology authority; this module reads it and
never duplicates or extends it.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .python_project import (
    PythonProjectState,
    inspect_python_project,
    path_is_collection_guarded,
    pytest_ignored_paths,
)

__all__ = ["PythonRepoPolicy", "analyze", "assess_python_project", "load_python_repo_policy"]

PYTHON_CONTRACT_REL = "ops/config/python-contract.json"
#: Where this repository keeps skill self-tests. Repository shape, so it
#: lives with the policy rather than in the generic inspector.
SELF_TEST_GLOBS = ("skills/*/scripts/self_test.py",)


@dataclass(frozen=True)
class PythonRepoPolicy:
    """What this repository's own authorities require of its Python surface."""

    require_uv_lock: bool | None = None
    self_test_roots: frozenset[str] | None = None
    contract_source: str | None = None
    contract_unreadable: bool = False
    self_test_globs: tuple[str, ...] = field(default=SELF_TEST_GLOBS)


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


def load_python_repo_policy(root: Path) -> PythonRepoPolicy:
    """Resolve repository-native Python policy. No universal Python laws.

    `require_uv_lock` is left UNKNOWN unless the repository's own
    automation declares a locked-environment workflow. `[tool.uv]` alone
    never implies it: many uv projects deliberately do not commit a lock,
    and encoding one repository's habit as a law is how folklore gets
    enforced everywhere.
    """
    contract_path = root / PYTHON_CONTRACT_REL
    if not contract_path.is_file():
        return PythonRepoPolicy(contract_source=None)
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return PythonRepoPolicy(contract_source=PYTHON_CONTRACT_REL, contract_unreadable=True)
    if not isinstance(contract, dict):
        return PythonRepoPolicy(contract_source=PYTHON_CONTRACT_REL, contract_unreadable=True)

    # `non_test_exclusions` is deliberately not read. It declares which
    # test-shaped paths are meant to be excluded, and a declaration is not
    # a guard — which is the exact distinction `guard_unknown` exists to
    # keep. Consulting it as evidence of exclusion would reintroduce the
    # bug, and requiring membership in it would invent a rule the
    # repository's own validator does not enforce.
    roots = contract.get("skill_self_test_roots")
    declared_lock = contract.get("uv_lock_required")
    return PythonRepoPolicy(
        require_uv_lock=declared_lock if isinstance(declared_lock, bool) else None,
        self_test_roots=frozenset(str(item) for item in roots) if isinstance(roots, list) else None,
        contract_source=PYTHON_CONTRACT_REL,
    )


def _version_findings(state: PythonProjectState, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if state.floor.status == "invalid":
        findings.append(
            _finding(
                "python.interpreter.requires_python_invalid",
                property_name="project.requires-python",
                observed=f"{state.requires_python!r} ({state.floor.detail})",
                expected="a valid PEP 440 version specifier",
                line=_line_for(text, "requires-python"),
                remediation_class="HANDOFF",
                severity="blocking",
                source="pyproject.toml",
            )
        )
        return findings

    declared = {
        "ruff": state.ruff_target,
        "mypy": state.mypy_python_version,
        "pyright": state.pyright_python_version,
    }
    if state.floor.status == "unknown":
        # Never a silent pass: if a tool pins a version and no floor can be
        # derived, say the alignment is undecidable rather than aligned.
        if state.requires_python and any(value is not None for value in declared.values()):
            findings.append(
                _finding(
                    "python.interpreter.floor_unknown",
                    property_name="project.requires-python",
                    observed=f"{state.requires_python!r}: {state.floor.detail}",
                    expected=(
                        "a specifier whose lowest supported minor version can be derived, "
                        "so Ruff/mypy/Pyright alignment is decidable"
                    ),
                    line=_line_for(text, "requires-python"),
                    remediation_class="HANDOFF",
                    severity="material",
                    source="pyproject.toml",
                )
            )
        return findings

    floor = state.floor.value
    assert floor is not None
    expected_by_section = {
        "ruff": ("target-version", "py" + floor.replace(".", "")),
        "mypy": ("python_version", floor),
        "pyright": ("pythonVersion", floor),
    }
    for section, observed in declared.items():
        if observed is None:
            # An absent optional tool setting is not a defect on its own.
            continue
        key, expected = expected_by_section[section]
        if observed != expected:
            findings.append(
                _finding(
                    "python.interpreter.version_alignment",
                    property_name=f"tool.{section}.{key}",
                    observed=observed,
                    expected=expected,
                    line=_line_for(text, key),
                    source="pyproject.toml",
                )
            )
    return findings


def _lock_findings(
    state: PythonProjectState, policy: PythonRepoPolicy, text: str
) -> list[dict[str, Any]]:
    required = policy.require_uv_lock
    if required is None:
        required = state.lock_workflow_declared and state.uv_declared
    if not required or state.uv_lock_present:
        return []
    return [
        _finding(
            "python.uv.lock_presence",
            property_name="uv_lock_consistency",
            observed="uv.lock is absent",
            expected=(
                "uv.lock exists because this repository's own automation runs a "
                "locked-environment workflow"
            ),
            line=_line_for(text, "[tool.uv]"),
            source="pyproject.toml",
        )
    ]


def _self_test_findings(
    root: Path,
    state: PythonProjectState,
    policy: PythonRepoPolicy,
    text: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if policy.contract_unreadable:
        return [
            _finding(
                "python.self_test.contract_parse",
                property_name="python_contract_parseability",
                observed=f"{PYTHON_CONTRACT_REL} could not be parsed",
                expected="canonical Python contract is valid JSON",
                line=None,
                remediation_class="HANDOFF",
                severity="blocking",
                source=PYTHON_CONTRACT_REL,
            )
        ]

    if not state.pytest_addopts_resolved or not state.collect_guards_resolved:
        findings.append(
            _finding(
                "python.self_test.guard_unknown",
                property_name="root_pytest_collection_guard",
                observed="pytest addopts or conftest collection guards are not statically readable",
                expected=(
                    "addopts is a string or list of strings and collection guards are "
                    "literal lists, so exclusion can be verified rather than assumed"
                ),
                line=_line_for(text, "addopts"),
                remediation_class="HANDOFF",
                severity="material",
                source="pyproject.toml",
            )
        )

    ignored = pytest_ignored_paths(state.pytest_addopts)
    discovered: list[str] = []
    for pattern in policy.self_test_globs:
        discovered.extend(path.relative_to(root).as_posix() for path in sorted(root.glob(pattern)))

    for rel in sorted(set(discovered)):
        skill_root = "/".join(rel.split("/")[:2])
        if policy.self_test_roots is not None and skill_root not in policy.self_test_roots:
            findings.append(
                _finding(
                    "python.self_test.registry",
                    property_name="self_test_registry_coverage",
                    observed=f"{skill_root} missing from skill_self_test_roots",
                    expected=(
                        f"every live skill self_test.py is registered in {PYTHON_CONTRACT_REL}"
                    ),
                    line=None,
                    source=PYTHON_CONTRACT_REL,
                )
            )
        guarded = path_is_collection_guarded(
            rel,
            addopts_ignored=ignored,
            collect_ignore=state.collect_ignore,
            collect_ignore_glob=state.collect_ignore_glob,
        )
        if not guarded:
            findings.append(
                _finding(
                    "python.self_test.collection_guard",
                    property_name="root_pytest_collection_guard",
                    observed=f"{rel} is collectable by root pytest",
                    expected=(
                        "self_test.py is excluded by pyproject addopts --ignore or a literal "
                        "root conftest collect_ignore / collect_ignore_glob entry"
                    ),
                    line=_line_for(text, "addopts"),
                    source="pyproject.toml",
                )
            )
    return findings


def _entrypoint_findings(root: Path, state: PythonProjectState, text: str) -> list[dict[str, Any]]:
    """Verify only declared Python module entrypoints, never infer package layout."""
    findings: list[dict[str, Any]] = []
    for name, value in state.project_scripts:
        module = value.split(":", 1)[0].strip()
        rel = module.replace(".", "/")
        candidates = (
            root / f"{rel}.py",
            root / rel / "__init__.py",
            root / "src" / f"{rel}.py",
            root / "src" / rel / "__init__.py",
        )
        if not any(candidate.is_file() for candidate in candidates):
            findings.append(
                _finding(
                    "python.project_script.module_resolution",
                    property_name="project.scripts",
                    observed=f"{name} = {value}",
                    expected="a module path that resolves in the repository root or src/ layout",
                    line=_line_for(text, name),
                    remediation_class="HANDOFF",
                    source="pyproject.toml",
                )
            )
    return findings


def _testpath_findings(root: Path, state: PythonProjectState, text: str) -> list[dict[str, Any]]:
    if not state.pytest_testpaths_resolved:
        return [
            _finding(
                "python.pytest.testpaths_unknown",
                property_name="tool.pytest.ini_options.testpaths",
                observed="testpaths is not a string or list of strings",
                expected="a statically readable pytest test-root declaration",
                line=_line_for(text, "testpaths"),
                remediation_class="HANDOFF",
                source="pyproject.toml",
            )
        ]
    return [
        _finding(
            "python.pytest.testpath_missing",
            property_name="tool.pytest.ini_options.testpaths",
            observed=path,
            expected="an existing repository test path",
            line=_line_for(text, path),
            source="pyproject.toml",
        )
        for path in state.pytest_testpaths
        if not (root / path).exists()
    ]


def assess_python_project(
    root: Path,
    state: PythonProjectState,
    policy: PythonRepoPolicy,
    text: str,
) -> list[dict[str, Any]]:
    """Judge observed state against repository policy."""
    findings = _version_findings(state, text)
    findings.extend(_lock_findings(state, policy, text))
    findings.extend(_self_test_findings(root, state, policy, text))
    findings.extend(_entrypoint_findings(root, state, text))
    findings.extend(_testpath_findings(root, state, text))
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

    state = inspect_python_project(root, data)
    policy = load_python_repo_policy(root)
    findings = assess_python_project(root, state, policy, text)
    return {
        "status": "NEEDS_IMPROVEMENT" if findings else "PASS",
        "findings": findings,
        "blockers": [],
    }
