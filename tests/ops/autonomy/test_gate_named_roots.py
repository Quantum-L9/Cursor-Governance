"""L4 gate named-root resolution: campaigns in other worktrees may publish."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from l4_local import authorize_release, begin, record_kernels  # noqa: E402
from local_execution_gate import evaluate  # noqa: E402


def _session_root(tmp_path: Path) -> Path:
    """A session workspace (like Website-Bot) that is a git repo with NO L4 state."""
    root = tmp_path / "session"
    root.mkdir()
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "config", "user.name", "test"], check=True, capture_output=True
    )
    (root / "README.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(root), "commit", "-m", "init"], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(root), "branch", "-M", "main"], check=True, capture_output=True
    )
    return root


def test_named_root_with_release_receipt_is_allowed(
    stacked_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    begin(stacked_repo, contract_id="c1")
    record_kernels(stacked_repo)
    authorize_release(stacked_repo)

    session = _session_root(tmp_path)
    command = f"cd {stacked_repo} && make push pr=1"
    assert evaluate("Bash", {"command": command}, root=session) is None

    command_git = f"git -C {stacked_repo} push origin HEAD"
    assert evaluate("Bash", {"command": command_git}, root=session) is None


def test_named_root_without_receipt_stays_denied(
    stacked_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")

    session = _session_root(tmp_path)
    reason = evaluate("Bash", {"command": f"cd {stacked_repo} && git push"}, root=session)
    assert reason is not None


def test_unresolvable_named_root_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")

    session = _session_root(tmp_path)
    missing = tmp_path / "does-not-exist"
    reason = evaluate("Bash", {"command": f"cd {missing} && git push"}, root=session)
    assert reason is not None
    assert "could not be resolved" in reason


def test_session_root_fallback_unchanged(
    stacked_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Commands that name no root still evaluate against the session workspace."""
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")

    session = _session_root(tmp_path)
    reason = evaluate("Bash", {"command": "git push"}, root=session)
    assert reason is not None
    # and a session root WITH a receipt still allows as before
    begin(stacked_repo, contract_id="c2")
    record_kernels(stacked_repo)
    authorize_release(stacked_repo)
    assert evaluate("Bash", {"command": "git push"}, root=stacked_repo) is None
