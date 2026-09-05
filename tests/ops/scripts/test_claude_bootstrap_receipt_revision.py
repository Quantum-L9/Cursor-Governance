"""Conformance: readiness is revision-bound, not only time-bound.

Observed defect: a receipt written against governance b618338 reported its
DEGRADED verdict as current 21 hours later at governance 0fc6ee6, because the
only expiry rule was a 24h TTL — 24x the governance refresh TTL.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "ops" / "scripts"))

import claude_bootstrap_receipt as receipt  # noqa: E402

NOW = datetime(2026, 8, 29, 1, 47, 0, tzinfo=UTC)


def make(state: str = "READY", *, revision: str = "a" * 40, age_seconds: int = 60) -> dict:
    written = NOW - timedelta(seconds=age_seconds)
    return {
        "schema": receipt.SCHEMA,
        "state": state,
        "stage": "receipt",
        "generated_at": written.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ttl_seconds": 86400,
        "governance_revision": revision,
        "workspace": "/home/user",
        **{key: "READY" for key in receipt.COMPONENTS},
    }


def test_matching_revision_keeps_the_recorded_state() -> None:
    result = receipt.evaluate(make(), now=NOW, governance_revision="a" * 40)
    assert result["state"] == receipt.READY


def test_superseded_revision_is_unknown_even_while_the_ttl_says_fresh() -> None:
    result = receipt.evaluate(make(), now=NOW, governance_revision="b" * 40)
    assert result["state"] == receipt.UNKNOWN
    assert "superseded" in result["reason"]


def test_superseded_revision_overrides_a_degraded_verdict() -> None:
    """The real regression: a DEGRADED verdict from a dead revision was reported
    as this session's state, remediation printed and never run."""
    stale = make("DEGRADED", revision="b618338" + "0" * 33)
    stale["mcp"] = "DEGRADED"
    result = receipt.evaluate(stale, now=NOW, governance_revision="0fc6ee6" + "f" * 33)
    assert result["state"] == receipt.UNKNOWN
    assert result["components"]["mcp"] == "DEGRADED"  # carried, not lost


def test_undeterminable_live_revision_never_invalidates() -> None:
    """A missing probe must not manufacture UNKNOWN out of a current receipt."""
    for live in ("", None):
        result = receipt.evaluate(make(), now=NOW, governance_revision=live)
        assert result["state"] == receipt.READY


def test_receipt_without_a_recorded_revision_is_not_invalidated() -> None:
    payload = make()
    payload.pop("governance_revision")
    result = receipt.evaluate(payload, now=NOW, governance_revision="b" * 40)
    assert result["state"] == receipt.READY


def test_ttl_expiry_still_wins_when_the_revision_matches() -> None:
    result = receipt.evaluate(make(age_seconds=90_000), now=NOW, governance_revision="a" * 40)
    assert result["state"] == receipt.UNKNOWN
    assert "expired" in result["reason"]


def test_reprobe_attaches_reason_and_log_path() -> None:
    payload = make("DEGRADED")
    payload["mcp"] = "DEGRADED"
    result = receipt.evaluate(payload, now=NOW, governance_revision="a" * 40)
    probed = receipt.reprobe_degraded(result)
    assert probed["log_path"]
    assert "mcp" in probed["reasons"]
    assert "DEGRADED" in probed["reasons"]["mcp"]


def test_missing_receipt_is_never_ran_not_ready(tmp_path: Path) -> None:
    result = receipt.read(tmp_path / "absent.json", now=NOW, governance_revision="a" * 40)
    assert result["state"] == receipt.NEVER_RAN


def test_live_revision_reads_a_detached_head(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("c" * 40 + "\n", encoding="utf-8")
    assert receipt.live_governance_revision(tmp_path) == "c" * 40


def test_live_revision_follows_a_symbolic_ref(tmp_path: Path) -> None:
    git = tmp_path / ".git"
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git / "refs" / "heads" / "main").write_text("d" * 40 + "\n", encoding="utf-8")
    assert receipt.live_governance_revision(tmp_path) == "d" * 40


def test_live_revision_falls_back_to_packed_refs(tmp_path: Path) -> None:
    git = tmp_path / ".git"
    git.mkdir()
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git / "packed-refs").write_text(
        "# pack-refs with: peeled\n" + "e" * 40 + " refs/heads/main\n", encoding="utf-8"
    )
    assert receipt.live_governance_revision(tmp_path) == "e" * 40


def test_live_revision_is_empty_when_undeterminable(tmp_path: Path) -> None:
    assert receipt.live_governance_revision(tmp_path) == ""


def test_live_revision_follows_a_worktree_gitdir(tmp_path: Path) -> None:
    git_dir = tmp_path / "gitdir"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("f" * 40 + "\n", encoding="utf-8")
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text(f"gitdir: {git_dir}\n", encoding="utf-8")
    assert receipt.live_governance_revision(worktree) == "f" * 40


def test_receipt_is_workspace_bound_when_it_can_say_so() -> None:
    """A receipt for one repository is not evidence about a sibling.

    A cloud container holds several repositories side by side, so the single
    `workspace` field records whichever root the installer was invoked with.
    Observed: a receipt stamped /home/user/Website-Bot reporting READY was read
    as authoritative by a session whose workspace was the container root.
    """
    base = make(revision="c" * 40)
    base["covered_roots"] = ["/home/user", "/home/user/Website-Bot"]

    covered = receipt.evaluate(base, now=NOW, governance_revision="c" * 40, workspace="/home/user")
    assert covered["state"] == receipt.READY
    assert covered["workspace_covered"] is True

    other = receipt.evaluate(
        base, now=NOW, governance_revision="c" * 40, workspace="/home/user/l9-harness"
    )
    assert other["state"] == receipt.UNKNOWN
    assert other["workspace_covered"] is False
    assert "not evidence about this workspace" in other["reason"]


def test_workspace_binding_is_back_compatible() -> None:
    """A receipt predating covered_roots must not be demoted on a guess."""
    legacy = make(revision="d" * 40)
    legacy.pop("covered_roots", None)

    # No workspace asked about: behaviour is exactly as before.
    assert receipt.evaluate(legacy, now=NOW, governance_revision="d" * 40)["state"] == receipt.READY

    # Asked about, but the receipt cannot say — None, and no demotion.
    asked = receipt.evaluate(legacy, now=NOW, governance_revision="d" * 40, workspace="/anywhere")
    assert asked["workspace_covered"] is None
    assert asked["state"] == receipt.READY
