"""Deterministic remediator protocol: edit axis, ingest, plan, gates, handoff."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "skills" / "l9-pr-remediation" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import gate_receipt  # noqa: E402
import ingest_signals  # noqa: E402
import issue_handoff  # noqa: E402
import protocol  # noqa: E402
import validate_plan  # noqa: E402


def test_reviewer_class_closed_set() -> None:
    assert protocol.reviewer_class("github-code-quality[bot]") == "code_review_agent"
    assert protocol.reviewer_class("copilot") == "code_review_agent"
    assert protocol.reviewer_class("copilot-pull-request-reviewer[bot]") == "code_review_agent"
    assert protocol.reviewer_class("coderabbitai[bot]") == "bot"
    assert protocol.reviewer_class("github-actions[bot]") == "ci"
    assert protocol.reviewer_class("igor") == "human"
    assert protocol.reviewer_class("robot") == "human"
    assert protocol.reviewer_class("mystery[bot]") == "bot"
    assert protocol.is_code_review_agent("Copilot[bot]")
    assert protocol.ledger_source(author="github-code-quality[bot]", kind="review") == (
        "github-code-quality"
    )
    assert protocol.ledger_source(author="igor", kind="review") == "human"
    assert protocol.ledger_source(kind="sonar") == "sonar"


def test_edit_axis_path_only() -> None:
    assert protocol.edit_axis(".github/workflows/ci.yml") == "CI_PIPELINE"
    assert protocol.edit_axis(".github/actions/setup/action.yml") == "CI_PIPELINE"
    assert protocol.edit_axis("ops/secrets/openclaw.yaml") == "CI_PIPELINE"
    assert protocol.edit_axis(".env.local") == "CI_PIPELINE"
    assert protocol.edit_axis("skills/l9-pr-remediation/SKILL.md") == "CODEBASE"
    assert protocol.edit_axis(None) == "CODEBASE"
    # Judgment classes are never inferred from a path.
    assert protocol.edit_axis("docs/legal.md") == "CODEBASE"


def test_severity_hint_uses_required_set() -> None:
    blocking = protocol.severity_hint({"source": "ci", "gate": "lint"}, {"lint"})
    other = protocol.severity_hint({"source": "ci", "gate": "sonar"}, {"lint"})
    cra = protocol.severity_hint(
        {"source": "review_inline", "author": "github-code-quality[bot]", "severity_label": "Note"}
    )
    human = protocol.severity_hint({"source": "review_inline", "author": "igor"})
    assert blocking == "blocking"
    assert other == "actionable"
    assert cra == "discussion"
    assert human is None


def test_plan_rejects_fix_without_cause_and_finding_board() -> None:
    sha = "a" * 40
    plan = {
        "board": "fix",
        "board_reason": "required lint red",
        "head_sha": sha,
        "findings": [
            {
                "id": "ci-1",
                "source": "ci",
                "ownership": "CODEBASE",
                "disposition": "fix",
                "evidence": "ruff",
                "root_cause": "Unknown",
                "confidence": "high",
                "board": "fix",
            }
        ],
        "clusters": [{"id": "ruff", "finding_ids": ["ci-1"], "files": ["x.py"], "action": "fix"}],
        "verify": {"makefile_targets": ["precommit-repo"]},
        "commit_policy": {"commits": 1, "publish": "git push", "no_verify": False},
    }
    errors = protocol.validate_plan(plan)
    assert any("board field" in item for item in errors)
    assert any("root_cause" in item for item in errors)


def test_plan_requires_every_ingested_id() -> None:
    sha = "b" * 40
    plan = {
        "board": "merge",
        "board_reason": "green",
        "findings": [
            {
                "id": "ci-1",
                "source": "ci",
                "ownership": "CODEBASE",
                "disposition": "already_fixed",
                "evidence": "head",
                "root_cause": "already on head",
                "confidence": "high",
            }
        ],
        "clusters": [],
        "verify": {"makefile_targets": ["precommit-repo"]},
        "commit_policy": {"commits": 1, "publish": "git push", "no_verify": False},
        "head_sha": sha,
    }
    errors = protocol.validate_plan(plan, [{"id": "ci-1"}, {"id": "cq-1"}])
    assert any("cq-1" in item for item in errors)


def test_merge_keeps_thread_id_when_ci_wins() -> None:
    merged = protocol.merge_findings(
        [
            {
                "id": "thread-1",
                "source": "github-code-quality",
                "author": "github-code-quality[bot]",
                "file": "a.py",
                "line": 3,
                "raw": "note",
                "thread_id": "T1",
            },
            {
                "id": "ci-1",
                "source": "ci",
                "author": "github-actions",
                "file": "a.py",
                "line": 3,
                "raw": "ruff",
            },
        ]
    )
    assert len(merged) == 1
    assert merged[0]["source"] == "ci"
    assert merged[0]["thread_id"] == "T1"


def test_gate_b_requires_clean_worktree() -> None:
    plan = {
        "board": "fix",
        "board_reason": "lint",
        "head_sha": "d" * 40,
        "findings": [
            {
                "id": "ci-1",
                "source": "ci",
                "ownership": "CODEBASE",
                "disposition": "already_fixed",
                "evidence": "head",
                "root_cause": "already on head",
                "confidence": "high",
            }
        ],
        "clusters": [],
        "verify": {"makefile_targets": ["precommit-repo"]},
        "commit_policy": {"commits": 1, "publish": "git push", "no_verify": False},
    }
    dirty = protocol.validate_gate("B", {"execution_plan": {"cycle_scope": []}}, plan=plan)
    assert any("worktree_dirty" in item for item in dirty)
    clean = protocol.validate_gate(
        "B",
        {
            "execution_plan": {"cycle_scope": []},
            "worktree_dirty": False,
            "classified_findings": {
                "blocking": 0,
                "actionable": 1,
                "discussion": 0,
                "deferred": 0,
                "total": 1,
            },
        },
        plan=plan,
    )
    assert clean == []


def test_leftover_needs_declaration() -> None:
    errors = protocol.validate_plan(
        {
            "board": "leftover",
            "board_reason": "human",
            "findings": [],
            "verify": {"makefile_targets": ["precommit-repo"]},
            "commit_policy": {"commits": 1, "publish": "git push", "no_verify": False},
        }
    )
    assert any("board_declaration" in item for item in errors)


def test_gate_a_rejects_ceremony_verbs() -> None:
    registry = protocol.discover_gate_registry(REPO)
    assert registry["makefile"] is True
    assert registry["leftover_workflow_run"] == []
    errors = protocol.validate_gate(
        "A",
        {
            "gate_registry": registry,
            "cached_verbs": "make pr-check",
        },
    )
    assert errors


def test_gate_d_and_f() -> None:
    assert not protocol.validate_gate(
        "D",
        {
            "local_verify_log": {
                "iteration": 1,
                "command": "PR_BASE=origin/main make precommit-repo",
                "exit_code": 0,
                "result": "Passed",
            }
        },
    )
    assert protocol.validate_gate("D", {"local_verify_log": {"result": "Failed"}})
    assert protocol.validate_gate(
        "F",
        {"reply_record": {"threads_total": 2, "threads_replied": 1, "threads_resolved": 2}},
    )


def test_ingest_fixture_keeps_cra_note(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = tmp_path / "fx"
    fixture.mkdir()
    (fixture / "pr.json").write_text(json.dumps({"head": {"sha": "c" * 40}}), encoding="utf-8")
    (fixture / "reviews.json").write_text("[]", encoding="utf-8")
    (fixture / "comments.json").write_text(
        json.dumps(
            [
                {
                    "id": "1",
                    "user": {"login": "github-code-quality[bot]"},
                    "path": "src/app.py",
                    "line": 10,
                    "body": "**Note:** consider extracting this helper",
                }
            ]
        ),
        encoding="utf-8",
    )
    (fixture / "issue_comments.json").write_text("[]", encoding="utf-8")
    (fixture / "checks.json").write_text(
        json.dumps([{"name": "lint", "conclusion": "failure", "path": "src/app.py", "line": 10}]),
        encoding="utf-8",
    )
    (fixture / "threads.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "T1",
                        "isResolved": False,
                        "comments": {
                            "nodes": [
                                {
                                    "author": {"login": "github-code-quality[bot]"},
                                    "path": "src/app.py",
                                    "line": 12,
                                    "body": "Note: nit",
                                }
                            ]
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "semgrep.json").write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "rule_name": "python.lang.security",
                        "path": "a.py",
                        "start_line": 3,
                        "message": "x",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "findings.json"
    rc = ingest_signals.main(
        [
            "--repo",
            "acme/app",
            "--pr",
            "7",
            "--output",
            "findings.json",
            "--required-checks",
            "lint",
            "--fixture-dir",
            str(fixture),
            "--semgrep",
            "semgrep.json",
        ]
    )
    assert rc == 0
    snap = json.loads(out.read_text(encoding="utf-8"))
    authors = {item["author"] for item in snap["findings"]}
    assert "github-code-quality[bot]" in authors
    assert snap["completeness"]["cra_comments_ingested"] is True
    ci = next(item for item in snap["findings"] if item["source"] == "ci")
    assert ci["severity_hint"] == "blocking"
    assert any(item["source"] == "semgrep" for item in snap["findings"])
    cra = [item for item in snap["findings"] if item["source"] == "github-code-quality"]
    assert cra
    assert all(item.get("source") != "review_inline" for item in snap["findings"])


def test_validate_plan_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    plan = {
        "board": "fix",
        "board_reason": "lint",
        "head_sha": "d" * 40,
        "findings": [
            {
                "id": "ci-1",
                "source": "ci",
                "ownership": "CODEBASE",
                "disposition": "fix",
                "evidence": "ruff src/a.py",
                "root_cause": "unused import",
                "confidence": "high",
            }
        ],
        "clusters": [
            {
                "id": "unused",
                "finding_ids": ["ci-1"],
                "files": ["src/a.py"],
                "action": "drop import",
            }
        ],
        "verify": {"makefile_targets": ["precommit-repo"], "cited_paths": ["src/a.py"]},
        "commit_policy": {"commits": 1, "publish": "git push", "no_verify": False},
    }
    (tmp_path / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    (tmp_path / "findings.json").write_text(
        json.dumps({"findings": [{"id": "ci-1"}]}),
        encoding="utf-8",
    )
    assert validate_plan.main(["--plan", "plan.json", "--findings", "findings.json"]) == 0


def test_gate_receipt_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "receipt.json").write_text(
        json.dumps(
            {
                "gate_registry": {
                    "makefile": True,
                    "public": {"verify": "make precommit-repo", "publish": "git push"},
                    "leftover_workflow_run": [],
                }
            }
        ),
        encoding="utf-8",
    )
    assert gate_receipt.main(["--gate", "A", "--receipt", "receipt.json"]) == 0


def test_issue_handoff_dry_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = issue_handoff.main(
        [
            "--repo",
            "acme/app",
            "--pr",
            "9",
            "--class",
            "HUMAN",
            "--title",
            "named product decision",
            "--head",
            "e" * 40,
            "--best-effort",
            "replied and resolved the thread",
            "--why",
            "API shape is a product call",
            "--output",
            "handoff.json",
        ]
    )
    assert rc == 0
    doc = json.loads((tmp_path / "handoff.json").read_text(encoding="utf-8"))
    assert doc["created"] is False
    assert "l9-issue-remediation" in doc["body"]
    assert doc["class"] == "HUMAN"


def test_issue_handoff_rejects_codebase(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        issue_handoff.main(
            [
                "--repo",
                "acme/app",
                "--pr",
                "1",
                "--class",
                "CODEBASE",
                "--title",
                "x",
                "--head",
                "f" * 40,
                "--best-effort",
                "n",
                "--why",
                "n",
                "--output",
                "handoff.json",
            ]
        )
