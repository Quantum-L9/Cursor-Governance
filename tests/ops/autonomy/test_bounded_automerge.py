"""Bounded exact-PR exact-head automerge — capability and negative cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

from bounded_automerge import (  # noqa: E402
    PullRequestState,
    evaluate,
    merge_if_allowed,
)
from merge_gate import evaluate as merge_evaluate  # noqa: E402


def _green(head: str = "abc123") -> PullRequestState:
    return PullRequestState(
        repo="Quantum-L9/Cursor-Governance",
        number=42,
        head_sha=head,
        is_draft=False,
        mergeable=True,
        review_decision="",
        required_checks_green=True,
    )


def test_automerge_zero_is_opt_out() -> None:
    allowed, reasons = evaluate(_green(), observed_head="abc123", automerge=False)
    assert allowed is False
    assert "PR_AUTOMERGE=0" in reasons


def test_exact_head_green_mergeable_allows() -> None:
    allowed, reasons = evaluate(_green(), observed_head="abc123", automerge=True)
    assert allowed is True
    assert reasons == []


def test_head_mismatch_denies() -> None:
    allowed, reasons = evaluate(_green("aaa"), observed_head="bbb", automerge=True)
    assert allowed is False
    assert "head_mismatch" in reasons


def test_draft_denies() -> None:
    state = PullRequestState(
        repo="Quantum-L9/Cursor-Governance",
        number=42,
        head_sha="abc123",
        is_draft=True,
        mergeable=True,
        review_decision="",
        required_checks_green=True,
    )
    allowed, reasons = evaluate(state, observed_head="abc123", automerge=True)
    assert allowed is False
    assert "draft" in reasons


def test_blocking_review_denies() -> None:
    state = PullRequestState(
        repo="Quantum-L9/Cursor-Governance",
        number=42,
        head_sha="abc123",
        is_draft=False,
        mergeable=True,
        review_decision="CHANGES_REQUESTED",
        required_checks_green=True,
    )
    allowed, reasons = evaluate(state, observed_head="abc123", automerge=True)
    assert allowed is False
    assert "blocking_review" in reasons


def test_merge_if_allowed_writes_exact_head_and_merges(tmp_path: Path) -> None:
    merged: list[tuple[str, int]] = []
    auth = tmp_path / "merge-authorization.json"
    result = merge_if_allowed(
        repo="Quantum-L9/Cursor-Governance",
        pr=42,
        observed_head="abc123",
        automerge=True,
        fetch=lambda repo, pr: _green(),
        merge_fn=lambda repo, pr: merged.append((repo, pr)),
        auth_file=auth,
    )
    assert result["merged"] is True
    assert merged == [("Quantum-L9/Cursor-Governance", 42)]
    payload = json.loads(auth.read_text(encoding="utf-8"))
    entry = payload["authorizations"][0]
    assert entry["pr"] == 42
    assert entry["head_sha"] == "abc123"
    assert entry["source"] == "pr_automerge"


def test_merge_if_allowed_does_not_merge_when_denied() -> None:
    merged: list[tuple[str, int]] = []
    result = merge_if_allowed(
        repo="Quantum-L9/Cursor-Governance",
        pr=42,
        observed_head="abc123",
        automerge=False,
        fetch=lambda repo, pr: _green(),
        merge_fn=lambda repo, pr: merged.append((repo, pr)),
    )
    assert result["merged"] is False
    assert merged == []


def test_pr_automerge_env_alone_does_not_authorize_merge_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PR_AUTOMERGE", "1")
    monkeypatch.delenv("L9_MERGE_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_MERGE_AUTHORIZATION_FILE", "/tmp/does-not-exist-merge-auth.json")
    reason = merge_evaluate(
        "Bash",
        {"command": "gh pr merge 42 --repo Quantum-L9/Cursor-Governance --squash"},
    )
    assert reason is not None


def test_exact_head_receipt_allows_matching_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth = tmp_path / "merge-authorization.json"
    merge_if_allowed(
        repo="Quantum-L9/Cursor-Governance",
        pr=42,
        observed_head="abc123",
        automerge=True,
        fetch=lambda repo, pr: _green(),
        merge_fn=lambda repo, pr: None,
        auth_file=auth,
    )
    monkeypatch.setenv("L9_MERGE_AUTHORIZATION_FILE", str(auth))
    monkeypatch.setenv("L9_MERGE_HEAD_SHA", "abc123")
    monkeypatch.delenv("L9_MERGE_AUTHORIZED", raising=False)
    reason = merge_evaluate(
        "Bash",
        {"command": "gh pr merge 42 --repo Quantum-L9/Cursor-Governance --squash"},
    )
    assert reason is None


def test_exact_head_receipt_denies_other_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth = tmp_path / "merge-authorization.json"
    merge_if_allowed(
        repo="Quantum-L9/Cursor-Governance",
        pr=42,
        observed_head="abc123",
        automerge=True,
        fetch=lambda repo, pr: _green(),
        merge_fn=lambda repo, pr: None,
        auth_file=auth,
    )
    monkeypatch.setenv("L9_MERGE_AUTHORIZATION_FILE", str(auth))
    monkeypatch.setenv("L9_MERGE_HEAD_SHA", "other")
    monkeypatch.delenv("L9_MERGE_AUTHORIZED", raising=False)
    reason = merge_evaluate(
        "Bash",
        {"command": "gh pr merge 42 --repo Quantum-L9/Cursor-Governance --squash"},
    )
    assert reason is not None


def test_admin_merge_still_denied_with_automerge_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth = tmp_path / "merge-authorization.json"
    merge_if_allowed(
        repo="Quantum-L9/Cursor-Governance",
        pr=42,
        observed_head="abc123",
        automerge=True,
        fetch=lambda repo, pr: _green(),
        merge_fn=lambda repo, pr: None,
        auth_file=auth,
    )
    monkeypatch.setenv("L9_MERGE_AUTHORIZATION_FILE", str(auth))
    monkeypatch.setenv("L9_MERGE_HEAD_SHA", "abc123")
    reason = merge_evaluate(
        "Bash",
        {"command": "gh pr merge 42 --repo Quantum-L9/Cursor-Governance --admin"},
    )
    assert reason is not None
