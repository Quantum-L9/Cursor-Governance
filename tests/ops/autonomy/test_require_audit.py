"""Same-head /l9-pr-audit bind for the remediator fleet."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "skills" / "l9-pr-remediation" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import require_audit  # noqa: E402
from protocol import normalize_audit_findings  # noqa: E402

REPO_SLUG = "Quantum-L9/Cursor-Governance"
HEAD_A = "a" * 40
HEAD_B = "b" * 40


def _handoff(*, head: str = HEAD_A, eligible: bool = True, prs: list[int] | None = None) -> dict:
    numbers = prs or [1, 2]
    return {
        "schema_version": "l9.pr-audit.remediation-handoff.v2.0",
        "audit_id": "audit.test.v1",
        "repository_binding": {"repository": REPO_SLUG, "default_branch": "main"},
        "pr_bindings": [{"pr_number": n, "head_sha": head, "base_sha": "c" * 40} for n in numbers],
        "work_units": [
            {
                "finding_id": f"F-{n}",
                "mutation_eligible": eligible,
                "affected_prs": [n],
                "write_surfaces": [f"ops/{n}.py"],
                "observed_behavior": f"broken {n}",
            }
            for n in numbers
        ],
    }


def _fleet(heads: dict[int, str]) -> dict:
    return {
        "repo": REPO_SLUG,
        "prs": [
            {"number": n, "head": {"sha": sha, "ref": f"feat/{n}"}} for n, sha in heads.items()
        ],
    }


def test_missing_handoff_does_not_hold(tmp_path: Path) -> None:
    receipt = require_audit.bind(repo=REPO_SLUG, fleet=_fleet({1: HEAD_A}), root=tmp_path)
    assert receipt["hold_merge"] is False
    assert receipt["eligible_prs"] == []
    assert receipt["reason"] == "no_handoff"


def test_same_head_eligible_units_hold_merge(tmp_path: Path) -> None:
    path = tmp_path / "WIP" / "topic" / "remediation-handoff.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_handoff()), encoding="utf-8")
    receipt = require_audit.bind(
        repo=REPO_SLUG, fleet=_fleet({1: HEAD_A, 2: HEAD_A}), root=tmp_path
    )
    assert receipt["hold_merge"] is True
    assert receipt["eligible_prs"] == [1, 2]
    assert receipt["reason"] == "same_head_mutation_eligible"
    assert receipt["path"] == str(path)


def test_stale_heads_do_not_hold(tmp_path: Path) -> None:
    path = tmp_path / "WIP" / "topic" / "remediation-handoff.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_handoff(head=HEAD_A)), encoding="utf-8")
    receipt = require_audit.bind(
        repo=REPO_SLUG, fleet=_fleet({1: HEAD_B, 2: HEAD_B}), root=tmp_path
    )
    assert receipt["hold_merge"] is False
    assert receipt["eligible_prs"] == []
    assert receipt["stale_prs"] == [1, 2]
    assert receipt["reason"] == "stale_heads"


def test_legal_defense_is_skipped(tmp_path: Path) -> None:
    path = tmp_path / "WIP" / "Legal Defense" / "remediation-handoff.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_handoff()), encoding="utf-8")
    receipt = require_audit.bind(repo=REPO_SLUG, fleet=_fleet({1: HEAD_A}), root=tmp_path)
    assert receipt["reason"] == "no_handoff"


def test_normalize_audit_findings_only_eligible_for_this_pr() -> None:
    findings = normalize_audit_findings(_handoff(), pr=1)
    assert [item["id"] for item in findings] == ["F-1"]
    assert findings[0]["source"] == "audit"
    assert findings[0]["file"] == "ops/1.py"
    skipped = normalize_audit_findings(_handoff(eligible=False), pr=1)
    assert skipped == []


def test_cli_writes_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    fleet_path = tmp_path / "fleet.json"
    fleet_path.write_text(json.dumps(_fleet({1: HEAD_A})), encoding="utf-8")
    handoff = tmp_path / "handoff.json"
    handoff.write_text(json.dumps(_handoff(prs=[1])), encoding="utf-8")
    out = tmp_path / "audit-bind.json"
    rc = require_audit.main(
        [
            "--repo",
            REPO_SLUG,
            "--fleet",
            str(fleet_path),
            "--handoff",
            str(handoff),
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["hold_merge"] is True
    assert doc["eligible_prs"] == [1]
