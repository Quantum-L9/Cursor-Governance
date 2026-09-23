#!/usr/bin/env python3
"""Compile and assess architecture decision records without authoring them.

The ADR authoring skill remains the semantic and execution owner.  This module
only observes the repository convention, models the ADR corpus, and assesses
records that are in the evaluated change set.  Historical records are retained
as compatibility evidence: their format may be incomplete or duplicated, but
they never block an unrelated change or trigger a history rewrite.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

ADR_CATALOG_SCHEMA = "l9.repo-docs.adr-catalog.v1"
ADR_ANALYZER_ID = "adr-catalog-contract-v1"

__all__ = [
    "ADR_ANALYZER_ID",
    "ADR_CATALOG_SCHEMA",
    "assess_adr_catalog",
    "compile_adr_catalog",
    "format_findings",
]

_ADR_PATHS = ("docs/adr", "docs/decisions")
_ADR_FILENAME = re.compile(r"^ADR-(?P<number>\d{3,})(?:[-_].+)?\.md$")
_TITLE = re.compile(r"^#\s+ADR-(?P<number>\d+):\s+(?P<title>\S.*)\s*$", re.MULTILINE)
_H2 = re.compile(r"^##\s+(?P<heading>.+?)\s*#*\s*$", re.MULTILINE)
_NUMBERED_OPTION = re.compile(r"^\s*\d+[.)]\s+\S", re.MULTILINE)
_OPTION_HEADING = re.compile(r"^###\s+\S", re.MULTILINE)
_ADR_REFERENCE = re.compile(r"\bADR-(\d{3,})\b", re.IGNORECASE)
_ALLOWED_STATUSES = frozenset({"proposed", "accepted", "deprecated"})


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _finding(
    rule_id: str,
    *,
    property_name: str,
    observed: str,
    expected: str,
    source: str,
    line: int | None,
    severity: str = "material",
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "property": property_name,
        "observed_state": observed,
        "expected_state": expected,
        "source": source,
        "line": line,
        "remediation_class": "HANDOFF",
    }


def _section(text: str, name: str) -> tuple[str | None, int | None]:
    """Return a level-two section body and heading line without Markdown execution."""
    matches = list(_H2.finditer(text))
    normalized = name.casefold()
    for index, match in enumerate(matches):
        if match.group("heading").strip().casefold() != normalized:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        return text[match.end() : end].strip(), _line(text, match.start())
    return None, None


def _first_content_line(text: str) -> str | None:
    return next((line.strip() for line in text.splitlines() if line.strip()), None)


def _record_paths(root: Path) -> list[Path]:
    records: list[Path] = []
    for directory in _ADR_PATHS:
        base = root / directory
        if not base.is_dir():
            continue
        records.extend(
            path
            for path in base.glob("*.md")
            if path.is_file() and _ADR_FILENAME.fullmatch(path.name)
        )
    return sorted(set(records), key=lambda path: path.relative_to(root).as_posix())


def _parse_record(root: Path, path: Path, *, active: bool) -> dict[str, Any]:
    rel = path.relative_to(root).as_posix()
    filename = _ADR_FILENAME.fullmatch(path.name)
    assert filename is not None
    number = filename.group("number")
    findings: list[dict[str, Any]] = []
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        findings.append(
            _finding(
                "adr.file.readable",
                property_name="ADR source readability",
                observed=str(exc),
                expected="a UTF-8 readable ADR Markdown file",
                source=rel,
                line=None,
                severity="blocking",
            )
        )
        return {
            "path": rel,
            "number": number,
            "title": None,
            "status": None,
            "date": None,
            "headings": [],
            "content_digest": None,
            "active": active,
            "validation": {"status": "BLOCKED", "findings": findings},
        }

    title_match = _TITLE.search(text)
    title: str | None = None
    if title_match is None:
        findings.append(
            _finding(
                "adr.title.contract",
                property_name="ADR title",
                observed="no '# ADR-NNN: title' heading",
                expected=f"a level-one heading whose ADR number is {number}",
                source=rel,
                line=1,
            )
        )
    else:
        title = title_match.group("title").strip()
        if title_match.group("number") != number:
            findings.append(
                _finding(
                    "adr.number.title_alignment",
                    property_name="ADR identifier alignment",
                    observed=f"filename ADR-{number}, title ADR-{title_match.group('number')}",
                    expected="the filename and title use the same ADR number",
                    source=rel,
                    line=_line(text, title_match.start()),
                )
            )

    headings = [match.group("heading").strip() for match in _H2.finditer(text)]
    status_section, status_line = _section(text, "Status")
    status = _first_content_line(status_section or "")
    if status is None:
        findings.append(
            _finding(
                "adr.status.present",
                property_name="ADR status",
                observed="missing or empty Status section",
                expected="Proposed, Accepted, Deprecated, or Superseded by ADR-NNN",
                source=rel,
                line=status_line,
            )
        )
    else:
        normalized_status = status.casefold()
        valid_status = normalized_status in _ALLOWED_STATUSES or bool(
            re.fullmatch(r"superseded\s+by\s+ADR-\d{3,}", status, re.IGNORECASE)
        )
        if not valid_status:
            findings.append(
                _finding(
                    "adr.status.vocabulary",
                    property_name="ADR status",
                    observed=status,
                    expected="Proposed, Accepted, Deprecated, or Superseded by ADR-NNN",
                    source=rel,
                    line=status_line,
                )
            )

    date_section, date_line = _section(text, "Date")
    date_value = _first_content_line(date_section or "")
    if date_value is None:
        findings.append(
            _finding(
                "adr.date.present",
                property_name="ADR decision date",
                observed="missing or empty Date section",
                expected="an ISO-8601 calendar date (YYYY-MM-DD)",
                source=rel,
                line=date_line,
            )
        )
    else:
        try:
            date.fromisoformat(date_value)
        except ValueError:
            findings.append(
                _finding(
                    "adr.date.iso8601",
                    property_name="ADR decision date",
                    observed=date_value,
                    expected="an ISO-8601 calendar date (YYYY-MM-DD)",
                    source=rel,
                    line=date_line,
                )
            )

    required = ("Context", "Decision", "Consequences")
    for section in required:
        value, section_line = _section(text, section)
        if not value:
            findings.append(
                _finding(
                    f"adr.section.{section.casefold()}",
                    property_name=f"ADR {section} section",
                    observed="missing or empty",
                    expected=f"a non-empty '## {section}' section",
                    source=rel,
                    line=section_line,
                )
            )

    options, options_line = _section(text, "Options Considered")
    if not options:
        findings.append(
            _finding(
                "adr.options.present",
                property_name="ADR options",
                observed="missing or empty Options Considered section",
                expected="a '## Options Considered' section with at least two viable options",
                source=rel,
                line=options_line,
            )
        )
    else:
        count = len(_NUMBERED_OPTION.findall(options))
        if count < 2:
            count = len(_OPTION_HEADING.findall(options))
        if count < 2:
            findings.append(
                _finding(
                    "adr.options.minimum",
                    property_name="ADR options",
                    observed=f"{count} detectable option(s)",
                    expected="at least two numbered or level-three options",
                    source=rel,
                    line=options_line,
                )
            )

    return {
        "path": rel,
        "number": number,
        "title": title,
        "status": status,
        "date": date_value,
        "headings": headings,
        "content_digest": _digest(raw),
        "active": active,
        "validation": {
            "status": "PASS" if not findings else "NEEDS_IMPROVEMENT",
            "findings": findings,
        },
    }


def _catalog_findings(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach cross-record findings to the affected ADRs only."""
    findings: list[dict[str, Any]] = []
    by_number: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_number.setdefault(str(record["number"]), []).append(record)
    known_numbers = set(by_number)
    for number, rows in sorted(by_number.items(), key=lambda item: int(item[0])):
        if len(rows) <= 1:
            continue
        paths = ", ".join(row["path"] for row in rows)
        for row in rows:
            finding = _finding(
                "adr.number.unique",
                property_name="ADR sequential identifier",
                observed=f"ADR-{number} is shared by {paths}",
                expected="one ADR file per number across docs/adr and docs/decisions",
                source=row["path"],
                line=1,
            )
            row["validation"]["findings"].append(finding)
            row["validation"]["status"] = "NEEDS_IMPROVEMENT"
            findings.append(finding)
    for row in records:
        status = row.get("status")
        if not isinstance(status, str) or not status.casefold().startswith("superseded"):
            continue
        references = _ADR_REFERENCE.findall(status)
        if (
            len(references) != 1
            or references[0] == row["number"]
            or references[0] not in known_numbers
        ):
            finding = _finding(
                "adr.supersession.forward_link",
                property_name="ADR supersession link",
                observed=status,
                expected="a status that references one different, existing ADR-NNN",
                source=row["path"],
                line=None,
            )
            row["validation"]["findings"].append(finding)
            row["validation"]["status"] = "NEEDS_IMPROVEMENT"
            findings.append(finding)
    return findings


def compile_adr_catalog(root: Path, *, changed_files: list[str]) -> dict[str, Any]:
    """Compile deterministic ADR evidence for the current repository revision.

    Only `changed_files` activate strict enforcement. Existing historical ADRs
    remain visible as compatibility evidence, so adopting this compiler never
    demands a wholesale decision-history rewrite.
    """
    root = root.resolve()
    active_paths = set(changed_files)
    records = [
        _parse_record(root, path, active=path.relative_to(root).as_posix() in active_paths)
        for path in _record_paths(root)
    ]
    findings = [finding for record in records for finding in record["validation"]["findings"]]
    findings.extend(_catalog_findings(records))
    active_findings = [
        finding
        for record in records
        if record["active"]
        for finding in record["validation"]["findings"]
    ]
    historical_findings = [
        finding
        for record in records
        if not record["active"]
        for finding in record["validation"]["findings"]
    ]
    if not records:
        status = "NotApplicable"
    elif active_findings:
        status = "FAIL"
    elif historical_findings:
        status = "PARTIAL"
    else:
        status = "PASS"
    identity = {
        "schema": ADR_CATALOG_SCHEMA,
        "records": [
            {key: value for key, value in record.items() if key not in {"active", "validation"}}
            for record in records
        ],
        "conventions": {
            "directories": list(_ADR_PATHS),
            "filename": "ADR-NNN[-slug].md",
            "active_contract": [
                "title",
                "status",
                "date",
                "context",
                "options_considered",
                "decision",
                "consequences",
                "unique_number",
                "supersession_forward_link",
            ],
        },
    }
    digest = _digest(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return {
        "schema": ADR_CATALOG_SCHEMA,
        "status": status,
        "conventions": identity["conventions"],
        "records": records,
        "findings": findings,
        "enforcement": {
            "active_paths": sorted(
                path for path in active_paths if path in {row["path"] for row in records}
            ),
            "historical_paths": sorted(row["path"] for row in records if not row["active"]),
            "active_finding_count": len(active_findings),
            "historical_finding_count": len(historical_findings),
        },
        "digest": digest,
    }


def assess_adr_catalog(root: Path, target: Path, catalog: dict[str, Any]) -> dict[str, Any]:
    """Return an obligation assessment for one ADR target from compiled evidence."""
    try:
        target_rel = target.relative_to(root).as_posix()
    except ValueError:
        return {
            "status": "BLOCKED",
            "findings": [],
            "blockers": ["ADR assessment target escapes the repository root"],
        }
    records = catalog.get("records") or []
    record = next((item for item in records if item.get("path") == target_rel), None)
    if record is None:
        return {"status": "PASS", "findings": [], "blockers": []}
    findings = list((record.get("validation") or {}).get("findings") or [])
    if not record.get("active"):
        return {"status": "PASS", "findings": [], "blockers": []}
    if any(item.get("severity") == "blocking" for item in findings):
        return {
            "status": "BLOCKED",
            "findings": [],
            "blockers": [
                f"{item['rule_id']}: {item['observed_state']}"
                for item in findings
                if item.get("severity") == "blocking"
            ],
        }
    return {
        "status": "NEEDS_IMPROVEMENT" if findings else "PASS",
        "findings": findings,
        "blockers": [],
    }


def format_findings(catalog: dict[str, Any]) -> list[str]:
    """Render receipt-validator detail without inventing a second finding type."""
    return [
        f"{item['source']}:{item.get('line') or '?'}: {item['rule_id']}: {item['expected_state']}"
        for item in catalog.get("findings") or []
    ]
