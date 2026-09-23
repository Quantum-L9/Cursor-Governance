"""Deterministic ADR catalog compilation and handoff regression coverage."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
SCRIPTS = PACK / "scripts"
sys.path.insert(0, str(SCRIPTS))

from adr_compile import ADR_CATALOG_SCHEMA, assess_adr_catalog, compile_adr_catalog  # noqa: E402
from repo_docs import audit_repository  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    for key, value in (("user.email", "tests@example.com"), ("user.name", "Tests")):
        subprocess.run(["git", "-C", str(root), "config", key, value], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "remote",
            "add",
            "origin",
            "https://github.com/example/consumer.git",
        ],
        check=True,
    )
    write(
        root / "README.md",
        "# Consumer\n\n## Purpose\n\nIndex.\n\n## Key Files\n\nCANONICAL_LAW.md AGENTS.md\n",
    )
    write(root / "CANONICAL_LAW.md", "# Law\n")
    write(root / "AGENTS.md", "# Agents\n")
    write(root / "CLAUDE.md", "# Load\n\n## Authority chain\n\nCANONICAL_LAW.md > AGENTS.md\n")
    write(root / "ARCHITECTURE.md", "# Architecture\n")
    write(root / "INVARIANTS.md", "# Invariants\n")


def commit(root: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", message], check=True)
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def valid_adr(number: int, *, status: str = "Accepted") -> str:
    return f"""# ADR-{number:03d}: Deterministic test decision

## Status

{status}

## Date

2026-09-22

## Context

The test repository needs a deterministic decision record.

## Options Considered

1. Preserve the existing contract.
2. Introduce an incompatible replacement.

## Decision

Preserve the compatible contract.

## Consequences

- The deterministic compiler can verify the record.
"""


def test_catalog_accepts_active_contract_and_stays_observation_only(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    path = root / "docs/decisions/ADR-001-compatible.md"
    write(path, valid_adr(1))
    before = path.read_bytes()

    catalog = compile_adr_catalog(root, changed_files=["docs/decisions/ADR-001-compatible.md"])

    assert catalog["schema"] == ADR_CATALOG_SCHEMA
    assert catalog["status"] == "PASS"
    assert catalog["enforcement"]["active_finding_count"] == 0
    assert assess_adr_catalog(root, path, catalog)["status"] == "PASS"
    assert path.read_bytes() == before


def test_historical_compatibility_is_visible_but_not_retroactively_enforced(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    path = root / "docs/decisions/ADR-001-historical.md"
    write(path, "# ADR-001: Historical record\n\nIt predates the current template.\n")

    catalog = compile_adr_catalog(root, changed_files=[])

    assert catalog["status"] == "PARTIAL"
    assert catalog["enforcement"]["active_finding_count"] == 0
    assert catalog["enforcement"]["historical_finding_count"] > 0
    assert assess_adr_catalog(root, path, catalog)["status"] == "PASS"


def test_active_nonconformant_adr_requires_authoring_skill_handoff(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    path = root / "docs/decisions/ADR-001-incomplete.md"
    write(
        path,
        "# ADR-001: Incomplete record\n\n## Status\n\nAccepted\n\n## Date\n\n2026-09-22\n",
    )

    catalog = compile_adr_catalog(root, changed_files=["docs/decisions/ADR-001-incomplete.md"])
    assessment = assess_adr_catalog(root, path, catalog)

    assert catalog["status"] == "FAIL"
    assert assessment["status"] == "NEEDS_IMPROVEMENT"
    assert {item["rule_id"] for item in assessment["findings"]} >= {
        "adr.section.context",
        "adr.options.present",
        "adr.section.decision",
        "adr.section.consequences",
    }
    assert {item["remediation_class"] for item in assessment["findings"]} == {"HANDOFF"}


def test_active_duplicate_numbers_and_broken_supersession_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    first = root / "docs/decisions/ADR-001-first.md"
    second = root / "docs/adr/ADR-001-second.md"
    write(first, valid_adr(1, status="Superseded by ADR-999"))
    write(second, valid_adr(1))
    changed = [
        "docs/decisions/ADR-001-first.md",
        "docs/adr/ADR-001-second.md",
    ]

    catalog = compile_adr_catalog(root, changed_files=changed)
    rules = {item["rule_id"] for item in catalog["findings"]}

    assert catalog["status"] == "FAIL"
    assert {"adr.number.unique", "adr.supersession.forward_link"} <= rules


def test_repo_docs_receipt_carries_catalog_and_handoffs_only_active_defects(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    base = commit(root, "base")
    adr = root / "docs/decisions/ADR-001-compatible.md"
    write(adr, valid_adr(1))
    commit(root, "valid adr")

    passing = audit_repository(root, changed_since=base)

    assert passing["final_status"] == "PASS"
    assert passing["adr_catalog"]["status"] == "PASS"
    obligation = next(item for item in passing["obligations"] if item["surface"] == "adrs")
    assert obligation["target"]["path"] == "docs/decisions/ADR-001-compatible.md"
    assert obligation["owner"]["id"] == "l9-architecture-decision-records"
    assert obligation["lifecycle"]["status"] == "PRESERVED"

    write(
        adr,
        "# ADR-001: Compatible decision\n\n## Status\n\nAccepted\n\n## Date\n\n2026-09-22\n",
    )
    commit(root, "broken adr")
    failing = audit_repository(root, changed_since=base)
    obligation = next(item for item in failing["obligations"] if item["surface"] == "adrs")

    assert failing["final_status"] == "PARTIAL"
    assert failing["adr_catalog"]["status"] == "FAIL"
    assert obligation["assessment"]["disposition"] == "HANDOFF"
    assert obligation["required_action"]["type"] == "HANDOFF"
    assert obligation["required_action"]["owner"] == "l9-architecture-decision-records"
    assert obligation["lifecycle"]["status"] == "HANDOFF_REQUIRED"
