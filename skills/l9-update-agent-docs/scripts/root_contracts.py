#!/usr/bin/env python3
"""Deterministic contracts for root agent and architecture documents.

Only explicit local references and optional, machine-readable managed blocks
are assessed.  The module never derives requirements from free-form prose and
never writes a consumer root document.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from consumer_snapshot import snapshot_document

__all__ = [
    "architecture_delta",
    "assess_architecture_index",
    "assess_root_agent_contract",
]

_AGENT_BLOCK = re.compile(r"<!--\s*L9_AGENT_CONTRACT\s*\n(.*?)\n\s*-->", re.DOTALL)
_ARCHITECTURE_BLOCK = re.compile(r"<!--\s*L9_ARCHITECTURE_COMPONENTS\s*\n(.*?)\n\s*-->", re.DOTALL)
_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
_ROOT_AUTHORITY_DOCUMENTS = {
    "CANONICAL_LAW.md",
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "ARCHITECTURE.md",
    "INVARIANTS.md",
}


def _finding(
    rule_id: str,
    *,
    property_name: str,
    observed: str,
    expected: str,
    line: int | None,
    source: str,
    remediation_class: str = "HANDOFF",
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
        "source": source,
    }


def _line(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def _document_text(root: Path, rel: str) -> str | None:
    try:
        return (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _link_findings(root: Path, snapshot: dict[str, Any], rel: str) -> list[dict[str, Any]]:
    document = snapshot_document(snapshot, rel)
    if document is None:
        return []
    findings: list[dict[str, Any]] = []
    documents = snapshot.get("documents") or {}
    for link in document.get("links") or []:
        raw = str(link["raw"])
        target = link.get("target")
        line = int(link["line"])
        if target is None:
            findings.append(
                _finding(
                    "root.reference.escaped_root",
                    property_name="local_reference_resolution",
                    observed=raw,
                    expected="a repository-relative reference that remains under the root",
                    line=line,
                    source=rel,
                )
            )
            continue
        # A root document may navigate to product or generated documentation
        # that is intentionally external to this compiler's topology.  The
        # validator is authority-bounded: only references into the root
        # authority set are structural assertions; component manifests and
        # agent-contract file entries carry their own closed-world checks.
        if target not in _ROOT_AUTHORITY_DOCUMENTS:
            continue
        target_path = root / str(target)
        if not target_path.exists():
            findings.append(
                _finding(
                    "root.reference.missing",
                    property_name="local_reference_resolution",
                    observed=raw,
                    expected="a local file or directory that exists",
                    line=line,
                    source=rel,
                )
            )
            continue
        fragment = link.get("fragment")
        if fragment:
            target_doc = documents.get(target)
            anchors = {
                row.get("anchor")
                for row in (target_doc or {}).get("headings", [])
                if isinstance(row, dict)
            }
            if str(fragment) not in anchors:
                findings.append(
                    _finding(
                        "root.reference.anchor_missing",
                        property_name="local_reference_anchor",
                        observed=raw,
                        expected="a target document with the requested heading anchor",
                        line=line,
                        source=rel,
                    )
                )
    return findings


def _agent_block_findings(root: Path, rel: str) -> list[dict[str, Any]]:
    text = _document_text(root, rel)
    if text is None:
        return []
    match = _AGENT_BLOCK.search(text)
    if not match:
        return []
    line = _line(text, match.start())
    try:
        value = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return [
            _finding(
                "agents.contract.parse",
                property_name="agent_instruction_contract",
                observed=f"invalid YAML: {exc}",
                expected=(
                    "a YAML mapping with optional commands, files, environment, and authorities"
                ),
                line=line,
                source=rel,
                severity="blocking",
            )
        ]
    if not isinstance(value, dict):
        return [
            _finding(
                "agents.contract.shape",
                property_name="agent_instruction_contract",
                observed=type(value).__name__,
                expected="a YAML mapping",
                line=line,
                source=rel,
                severity="blocking",
            )
        ]
    findings: list[dict[str, Any]] = []
    make_targets: set[str] = set()
    makefile = root / "Makefile"
    if makefile.is_file():
        make_targets = {
            row.split(":", 1)[0].strip()
            for row in makefile.read_text(encoding="utf-8").splitlines()
            if ":" in row and not row.startswith(("\t", " ", "#"))
        }
    for command in value.get("commands") or []:
        if not isinstance(command, str):
            continue
        parts = command.split()
        if len(parts) == 2 and parts[0] == "make" and parts[1] not in make_targets:
            findings.append(
                _finding(
                    "agents.contract.command_missing",
                    property_name="agent_command_resolution",
                    observed=command,
                    expected="a declared Makefile target",
                    line=line,
                    source=rel,
                )
            )
    for path in value.get("files") or []:
        if isinstance(path, str) and not (root / path).is_file():
            findings.append(
                _finding(
                    "agents.contract.file_missing",
                    property_name="agent_file_resolution",
                    observed=path,
                    expected="an existing repository file",
                    line=line,
                    source=rel,
                )
            )
    for name in value.get("environment") or []:
        if not isinstance(name, str) or not _ENV_NAME.fullmatch(name):
            findings.append(
                _finding(
                    "agents.contract.environment_name",
                    property_name="agent_environment_reference",
                    observed=repr(name),
                    expected="an uppercase environment variable name without a value",
                    line=line,
                    source=rel,
                )
            )
    authorities = value.get("authorities") or []
    if authorities and not all(
        isinstance(item, str) and (root / item).is_file() for item in authorities
    ):
        findings.append(
            _finding(
                "agents.contract.authority_missing",
                property_name="agent_authority_resolution",
                observed=repr(authorities),
                expected="existing repository authority files",
                line=line,
                source=rel,
            )
        )
    return findings


def assess_root_agent_contract(
    root: Path, target: Path, snapshot: dict[str, Any]
) -> dict[str, Any]:
    rel = target.relative_to(root).as_posix()
    findings = _link_findings(root, snapshot, rel)
    if rel == "AGENTS.md":
        findings.extend(_agent_block_findings(root, rel))
    return {
        "status": "NEEDS_IMPROVEMENT" if findings else "PASS",
        "findings": findings,
        "blockers": [],
    }


def _architecture_block_findings(root: Path, rel: str) -> list[dict[str, Any]]:
    text = _document_text(root, rel)
    if text is None:
        return []
    match = _ARCHITECTURE_BLOCK.search(text)
    if not match:
        return []
    line = _line(text, match.start())
    try:
        value = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return [
            _finding(
                "architecture.components.parse",
                property_name="architecture_component_manifest",
                observed=f"invalid YAML: {exc}",
                expected="a YAML list of repository-relative component paths",
                line=line,
                source=rel,
                severity="blocking",
            )
        ]
    components = value.get("components") if isinstance(value, dict) else None
    if not isinstance(components, list):
        return [
            _finding(
                "architecture.components.shape",
                property_name="architecture_component_manifest",
                observed=type(components).__name__,
                expected="components: [<repository-relative path>, ...]",
                line=line,
                source=rel,
                severity="blocking",
            )
        ]
    findings: list[dict[str, Any]] = []
    root_resolved = root.resolve()
    for item in components:
        candidate = (root / item).resolve() if isinstance(item, str) else None
        contained = False
        if candidate is not None:
            try:
                candidate.relative_to(root_resolved)
                contained = True
            except ValueError:
                contained = False
        if candidate is None or not contained or not candidate.exists():
            findings.append(
                _finding(
                    "architecture.component_missing",
                    property_name="architecture_component_resolution",
                    observed=repr(item),
                    expected="an existing repository component path",
                    line=line,
                    source=rel,
                )
            )
    return findings


def architecture_delta(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    """Typed, source-backed architecture delta candidates for Harvest qualification."""
    changes = set(snapshot.get("changed_files") or [])
    facts = snapshot.get("facts") or []
    delta: list[dict[str, str]] = []
    for fact in facts:
        path = str(fact.get("path") or "")
        if path not in changes:
            continue
        kind = str(fact.get("kind") or "source")
        delta.append(
            {
                "action": "change",
                "kind": kind,
                "path": path,
                "evidence_id": str(fact.get("id") or path),
            }
        )
    for path in sorted(changes):
        if not any(item["path"] == path for item in delta) and (
            path == "pyproject.toml" or path == "Makefile" or path.startswith(".github/workflows/")
        ):
            delta.append(
                {
                    "action": "unknown",
                    "kind": "unclassified_contract_change",
                    "path": path,
                    "evidence_id": path,
                }
            )
    return sorted(delta, key=lambda item: (item["path"], item["kind"]))


def assess_architecture_index(root: Path, target: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    rel = target.relative_to(root).as_posix()
    findings = _link_findings(root, snapshot, rel)
    findings.extend(_architecture_block_findings(root, rel))
    return {
        "status": "NEEDS_IMPROVEMENT" if findings else "PASS",
        "findings": findings,
        "blockers": [],
    }
