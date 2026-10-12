"""Tests for ops/autonomy/authorize_merge.py — human merge grants (§6.2.12).

A grant is one repository, one PR, one exact head, expiring, issuer ``human``,
and it is written only after a human confirms the target on a terminal.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "ops" / "autonomy" / "authorize_merge.py"
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import authorize_merge  # noqa: E402
from authorize_merge import MAX_TTL_SECONDS, write_authorization  # noqa: E402
from merge_gate import grant_matches  # noqa: E402

SHA = "abcdef1234567890abcdef1234567890abcdef12"
SLUG = "Quantum-L9/Cursor-Governance"


def _grant(path: Path, **overrides) -> dict:
    kwargs = {
        "repo": SLUG,
        "pr": "42",
        "head_sha": SHA,
        "reason": "reviewed",
        "path": path,
        "now": 1_000_000,
        "ttl_seconds": 100,
    }
    kwargs.update(overrides)
    return write_authorization(**kwargs)


def test_grant_binds_repo_pr_head_issuer_and_expiry(tmp_path: Path) -> None:
    path = tmp_path / "merge-authorization.json"
    entry = _grant(path, head_sha=SHA.upper())
    assert entry == {
        "repo": SLUG,
        "pr": 42,
        "head_sha": SHA,
        "issuer": "human",
        "issued_at": 1_000_000,
        "expires_at": 1_000_100,
        "reason": "reviewed",
    }
    assert json.loads(path.read_text(encoding="utf-8"))["authorizations"] == [entry]


def test_written_grant_is_one_the_gate_accepts(tmp_path: Path) -> None:
    """Issuer and gate agree on the schema: what one writes, the other matches."""
    entry = _grant(tmp_path / "auth.json")
    assert grant_matches(entry, SLUG, "42", SHA, now=1_000_050)
    assert not grant_matches(entry, SLUG, "42", SHA, now=1_000_100)  # expired
    assert not grant_matches(entry, SLUG, "43", SHA, now=1_000_050)  # other PR
    assert not grant_matches(entry, SLUG, "42", "b" * 40, now=1_000_050)  # moved head


def test_replaces_same_pr_and_keeps_others(tmp_path: Path) -> None:
    path = tmp_path / "auth.json"
    _grant(path, reason="first")
    _grant(path, reason="second")
    _grant(path, repo="Quantum-L9/SEO-Bot", reason="other")
    entries = json.loads(path.read_text(encoding="utf-8"))["authorizations"]
    assert [(e["repo"], e["reason"]) for e in entries] == [
        (SLUG, "second"),
        ("Quantum-L9/SEO-Bot", "other"),
    ]


@pytest.mark.parametrize("pr", ["*", "all", "", "0", "x"])
def test_repository_wide_scope_is_not_issuable(tmp_path: Path, pr: str) -> None:
    with pytest.raises(ValueError, match="not issuable"):
        _grant(tmp_path / "auth.json", pr=pr)


@pytest.mark.parametrize("sha", ["", "zzzz", "abcdef1", "a" * 39])
def test_head_must_be_a_full_sha(tmp_path: Path, sha: str) -> None:
    with pytest.raises(ValueError, match="40-hex"):
        _grant(tmp_path / "auth.json", head_sha=sha)


def test_rejects_bad_repo(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="owner/name"):
        _grant(tmp_path / "auth.json", repo="not-a-repo")


@pytest.mark.parametrize("ttl", [0, -1, MAX_TTL_SECONDS + 1])
def test_ttl_must_be_positive_and_bounded(tmp_path: Path, ttl: int) -> None:
    with pytest.raises(ValueError, match="expire|exceed"):
        _grant(tmp_path / "auth.json", ttl_seconds=ttl)


# --- issuance: a human at a terminal, never an agent --------------------------


def _cli(tmp_path: Path, *extra: str) -> list[str]:
    return ["--repo", SLUG, "--auth-file", str(tmp_path / "auth.json"), *extra]


def test_cli_without_a_terminal_refuses_and_writes_nothing(tmp_path: Path) -> None:
    """An agent tool shell has no controlling terminal: self-issuance fails."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *_cli(tmp_path, "--pr", "42", "--head-sha", SHA)],
        capture_output=True,
        text=True,
        input="Quantum-L9/Cursor-Governance#42@abcdef123456\n",  # piped stdin is not a tty
        start_new_session=True,  # detach from any controlling terminal
        check=False,
    )
    assert proc.returncode == authorize_merge.NOT_CONFIRMED_EXIT, proc.stderr
    assert "MERGE_PENDING" in proc.stderr
    assert not (tmp_path / "auth.json").exists()


@pytest.mark.parametrize("extra", [("--all-open",), ("--pr", "*"), ()])
def test_cli_refuses_repository_wide_authority(tmp_path: Path, extra: tuple[str, ...]) -> None:
    asked: list[str] = []
    code = authorize_merge.main(
        _cli(tmp_path, *extra, "--head-sha", SHA), confirm=lambda t: asked.append(t) or True
    )
    assert code == 2
    assert asked == []  # refused before any confirmation is even requested
    assert not (tmp_path / "auth.json").exists()


def test_cli_wrong_confirmation_refuses(tmp_path: Path) -> None:
    code = authorize_merge.main(
        _cli(tmp_path, "--pr", "42", "--head-sha", SHA), confirm=lambda _t: False
    )
    assert code == authorize_merge.NOT_CONFIRMED_EXIT
    assert not (tmp_path / "auth.json").exists()


def test_cli_confirmed_by_human_writes_bound_grant(tmp_path: Path) -> None:
    seen: list[str] = []

    def confirm(token: str) -> bool:
        seen.append(token)
        return True

    code = authorize_merge.main(_cli(tmp_path, "--pr", "42", "--head-sha", SHA), confirm=confirm)
    assert code == 0
    assert seen == [f"{SLUG}#42@{SHA[:12]}"]
    (entry,) = json.loads((tmp_path / "auth.json").read_text(encoding="utf-8"))["authorizations"]
    assert (entry["repo"], entry["pr"], entry["head_sha"], entry["issuer"]) == (
        SLUG,
        42,
        SHA,
        "human",
    )
