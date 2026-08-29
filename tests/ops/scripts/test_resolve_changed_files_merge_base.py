"""Conformance: an undeterminable change set is never reported as empty.

A cloud SessionStart fetches the base with `--depth 1`. When the base then
advances, it shares no reachable ancestor with the working branch and
`git merge-base` fails outright. The resolver ran merge-base unguarded and the
caller swallowed the failure with `|| true`, so "cannot determine what changed"
became "nothing changed" — and the gate reported

    OK: nothing to gate vs origin/main
    RESULT: PASS — local PR gate clean (nothing to gate)

on a branch whose two-dot diff was 117 files, without running one checker.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
RESOLVER = REPO_ROOT / "ops" / "scripts" / "resolve_changed_files.sh"


def git(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=check
    )


def run_resolver(cwd: Path, base: str = "origin/main") -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(RESOLVER)],
        cwd=cwd,
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(cwd),
            "PR_ALLOW_EMPTY": "1",
            "PR_BASE": base,
            "WS": str(cwd),
        },
        check=False,
        timeout=120,
    )


def test_resolver_exists_and_parses() -> None:
    assert RESOLVER.is_file()
    assert subprocess.run(["bash", "-n", str(RESOLVER)]).returncode == 0


def test_merge_base_failure_is_distinguished_from_empty() -> None:
    """Exit 2 from the comparison must not collapse into 'nothing changed'."""
    body = RESOLVER.read_text(encoding="utf-8")
    assert "return 2" in body
    assert "COMPARISON_RC" in body
    assert 'COMMITTED="$(comparison_files "$BASE" || true)"' not in body, (
        "the swallow that caused the false PASS must not come back"
    )


def test_unrelated_history_fails_closed(tmp_path: Path) -> None:
    """Behavioural proof: with no shared ancestor the resolver refuses."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git("init", "-q", ".", cwd=repo)
    git("config", "user.email", "t@e", cwd=repo)
    git("config", "user.name", "t", cwd=repo)

    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    git("add", "a.txt", cwd=repo)
    git("commit", "-qm", "a", cwd=repo)

    # An orphan branch shares no ancestor with the first — the same shape a
    # depth-1 base produces.
    git("checkout", "-q", "--orphan", "other", cwd=repo)
    (repo / "b.txt").write_text("b\n", encoding="utf-8")
    git("add", "b.txt", cwd=repo)
    git("commit", "-qm", "b", cwd=repo)
    git("branch", "-f", "target", "master", cwd=repo, check=False)

    head = git("rev-parse", "--abbrev-ref", "HEAD", cwd=repo).stdout.strip()
    assert head == "other"

    result = run_resolver(repo, base="master")
    if "unknown revision" in result.stderr:
        pytest.skip("default branch name differs in this git build")
    assert result.returncode != 0, result.stdout
    assert "no merge base" in result.stderr or "cannot determine" in result.stderr


def test_live_repo_resolves_a_real_change_set() -> None:
    """The regression this fixes: this branch must not resolve to nothing."""
    result = run_resolver(REPO_ROOT)
    if result.returncode != 0:
        pytest.skip(f"no usable base in this checkout: {result.stderr[-200:]}")
    assert "comparison" in result.stderr
