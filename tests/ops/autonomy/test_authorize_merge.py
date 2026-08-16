"""Tests for ops/autonomy/authorize_merge.py"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

from authorize_merge import write_authorization  # noqa: E402


def test_defaults_to_repo_scope(tmp_path: Path) -> None:
    path = tmp_path / "merge-authorization.json"
    entry = write_authorization(
        repo="Quantum-L9/Cursor-Governance",
        reason="l9-pr-remediation invoked",
        path=path,
        now=1_000_000,
        ttl_seconds=100,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert entry["pr"] == "*"
    assert entry["source"] == "l9-pr-remediation"
    assert entry["expires_at"] == 1_000_100
    assert payload["authorizations"][0]["pr"] == "*"


def test_replaces_same_repo_scope(tmp_path: Path) -> None:
    path = tmp_path / "merge-authorization.json"
    write_authorization(
        repo="Quantum-L9/Cursor-Governance",
        reason="first",
        path=path,
        now=1,
    )
    write_authorization(
        repo="Quantum-L9/Cursor-Governance",
        reason="second",
        path=path,
        now=2,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert len(payload["authorizations"]) == 1
    assert payload["authorizations"][0]["reason"] == "second"


def test_keeps_other_repo_entries(tmp_path: Path) -> None:
    path = tmp_path / "merge-authorization.json"
    write_authorization(
        repo="Quantum-L9/SEO-Bot",
        reason="other",
        path=path,
        now=1,
    )
    write_authorization(
        repo="Quantum-L9/Cursor-Governance",
        reason="here",
        path=path,
        now=2,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    repos = {item["repo"] for item in payload["authorizations"]}
    assert repos == {"Quantum-L9/SEO-Bot", "Quantum-L9/Cursor-Governance"}


def test_single_pr_still_supported(tmp_path: Path) -> None:
    path = tmp_path / "merge-authorization.json"
    entry = write_authorization(
        repo="Quantum-L9/Cursor-Governance",
        pr="42",
        reason="one pr",
        path=path,
        now=1,
    )
    assert entry["pr"] == 42


def test_rejects_bad_repo(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="owner/name"):
        write_authorization(
            repo="not-a-repo",
            reason="x",
            path=tmp_path / "auth.json",
        )
