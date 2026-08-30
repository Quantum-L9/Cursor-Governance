"""Tests for L4 local autonomy phase machine + remote gate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import git_in

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from l4_local import (  # noqa: E402
    authorize_release,
    begin,
    receipt_path,
    record_kernels,
    release_allows_remote,
    resolve_pr_template,
    state_path,
    status_dict,
    workspace_from_event,
    workspace_identity,
)
from local_execution_gate import evaluate  # noqa: E402


def test_denies_remote_without_release(stacked_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    allowed, reason = release_allows_remote(stacked_repo)
    assert not allowed
    assert "mid-execution" in reason or "L4" in reason


def test_begin_kernels_authorize_allows_push(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    begin(stacked_repo, contract_id="c1")
    assert release_allows_remote(stacked_repo)[0] is False
    record_kernels(stacked_repo)
    assert release_allows_remote(stacked_repo)[0] is False
    receipt = authorize_release(stacked_repo)
    assert receipt["phase"] == "release_authorized"
    allowed, reason = release_allows_remote(stacked_repo)
    assert allowed
    assert "release_authorized" in reason


def test_gate_denies_mid_execution_remote_mutation(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L4 still gates remote mutation — but not by blocking git itself.

    `git push` is exempt from execution denial
    (ops/autonomy/git_execution_exemption.py), so the L4 remote gate is pinned
    here on `make pr`, the sanctioned publish path it actually governs.
    """
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    reason = evaluate("Bash", {"command": "make pr"}, root=stacked_repo)
    assert reason is not None

    assert evaluate("Bash", {"command": "git push -u origin HEAD"}, root=stacked_repo) is None


def test_gate_allows_local_commit(stacked_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    reason = evaluate(
        "Bash",
        {"command": "git commit -m 'local only'"},
        root=stacked_repo,
    )
    assert reason is None


def test_breakglass_allows(stacked_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_LOCAL_PUSH_AUTHORIZED", "human override")
    allowed, _ = release_allows_remote(stacked_repo)
    assert allowed


def test_workspace_from_event_uses_workspace_roots_when_cwd_empty(
    stacked_repo: Path,
) -> None:
    """Cursor beforeShellExecution often sends cwd="" and the checkout in workspace_roots."""
    event = {
        "cwd": "",
        "workspace_roots": [str(stacked_repo)],
        "transcript_path": "unused",
    }
    assert workspace_from_event(event) == stacked_repo.resolve()


def test_cli_check_remote_exit_codes(stacked_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    cli = ROOT / "ops" / "autonomy" / "l4_local.py"
    denied = subprocess.run(
        [sys.executable, str(cli), "--workspace", str(stacked_repo), "check-remote"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "L9_L4_LOCAL_AUTONOMY": "1"},
    )
    assert denied.returncode == 2
    begin(stacked_repo)
    record_kernels(stacked_repo)
    authorize_release(stacked_repo)
    ok = subprocess.run(
        [sys.executable, str(cli), "--workspace", str(stacked_repo), "check-remote"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "L9_L4_LOCAL_AUTONOMY": "1"},
    )
    assert ok.returncode == 0
    assert json.loads(ok.stdout)["allowed"] is True


# -- CI-016 / IMP-14: pr_template resolves against the RELEASED repo ----------
# The field was the literal "PULL_REQUEST_TEMPLATE.md" in every receipt, so a
# receipt written in a repository with no template named the governance clone's
# default as if it were that repo's own.


def test_pr_template_is_none_when_the_released_repo_has_none(tmp_path: Path) -> None:
    assert resolve_pr_template(tmp_path) is None


@pytest.mark.parametrize(
    "rel",
    [
        "PULL_REQUEST_TEMPLATE.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/pull_request_template.md",
        "docs/PULL_REQUEST_TEMPLATE.md",
    ],
)
def test_pr_template_found_at_each_standard_location(tmp_path: Path, rel: str) -> None:
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("## Summary\n", encoding="utf-8")
    assert resolve_pr_template(tmp_path) == rel


def test_pr_template_prefers_repo_root_over_dot_github(tmp_path: Path) -> None:
    (tmp_path / "PULL_REQUEST_TEMPLATE.md").write_text("root", encoding="utf-8")
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "PULL_REQUEST_TEMPLATE.md").write_text("gh", encoding="utf-8")
    # Same precedence as ops/scripts/open_pr_after_gate.sh, which searches
    # $WS/PULL_REQUEST_TEMPLATE.md before $WS/.github/PULL_REQUEST_TEMPLATE.md.
    assert resolve_pr_template(tmp_path) == "PULL_REQUEST_TEMPLATE.md"


def test_pr_template_never_reports_the_governance_default_for_a_bare_repo(
    stacked_repo: Path,
) -> None:
    """The done_when: a receipt in a repo without a template says null."""
    for rel in (
        "PULL_REQUEST_TEMPLATE.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/pull_request_template.md",
        "docs/PULL_REQUEST_TEMPLATE.md",
    ):
        assert not (stacked_repo / rel).exists(), f"fixture unexpectedly ships {rel}"
    begin(stacked_repo, contract_id="ci-016")
    record_kernels(stacked_repo)
    receipt = authorize_release(stacked_repo)
    assert receipt["pr_template"] is None
    assert status_dict(stacked_repo)["pr_template"] is None


def test_status_dict_exposes_stale_when_head_moves(stacked_repo: Path) -> None:
    begin(stacked_repo, contract_id="ci-016-stale")
    record_kernels(stacked_repo)
    authorize_release(stacked_repo)
    status = status_dict(stacked_repo)
    assert status["stale"] is False
    subprocess.run(
        ["git", "-C", str(stacked_repo), "commit", "--allow-empty", "-m", "move head"],
        check=True,
        capture_output=True,
    )
    moved = status_dict(stacked_repo)
    assert moved["stale"] is True
    assert moved["head"] != (moved["receipt"] or {}).get("head_sha")


def test_pr_template_names_the_released_repos_own_template(stacked_repo: Path) -> None:
    (stacked_repo / ".github").mkdir(exist_ok=True)
    (stacked_repo / ".github" / "pull_request_template.md").write_text("x", encoding="utf-8")
    begin(stacked_repo, contract_id="ci-016b")
    record_kernels(stacked_repo)
    receipt = authorize_release(stacked_repo)
    assert receipt["pr_template"] == ".github/pull_request_template.md"


# ---------------------------------------------------------------------------
# Workspace-scoped state: one repo's release never authorizes another's push
# ---------------------------------------------------------------------------


def _sibling_repo(tmp_path: Path, name: str, branch: str) -> Path:
    """A second checkout carrying the SAME branch name as `stacked_repo`."""
    repo = tmp_path / name
    repo.mkdir()
    git_in(repo, "init")
    git_in(repo, "config", "user.email", "test@example.com")
    git_in(repo, "config", "user.name", "test")
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    git_in(repo, "add", "README.md")
    git_in(repo, "commit", "-m", "init")
    git_in(repo, "branch", "-M", "main")
    git_in(repo, "checkout", "-b", branch)
    return repo


def test_release_in_one_workspace_does_not_authorize_another(
    stacked_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reported hole: a shared state dir + a shared branch name.

    Every repository in the fleet carries the same branch name, so matching on
    `stacked_branch` alone let an authorize-release in one checkout satisfy the
    gate in every other checkout that shared the machine-wide state directory.
    """
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    shared = tmp_path / "shared-state"
    monkeypatch.setenv("L9_AUTONOMY_STATE_DIR", str(shared))

    begin(stacked_repo, contract_id="ci-scope")
    record_kernels(stacked_repo)
    authorize_release(stacked_repo)
    assert release_allows_remote(stacked_repo)[0] is True

    other = _sibling_repo(tmp_path, "other", "feat/l4-stack")
    allowed, reason = release_allows_remote(other)
    assert allowed is False, reason
    assert "mid-execution" in reason or "workspace" in reason


def test_relocated_state_dir_is_namespaced_per_workspace(
    stacked_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shared = tmp_path / "shared-state"
    monkeypatch.setenv("L9_AUTONOMY_STATE_DIR", str(shared))
    other = _sibling_repo(tmp_path, "other-ns", "feat/l4-stack")

    mine = receipt_path(stacked_repo)
    theirs = receipt_path(other)
    assert mine != theirs, "two workspaces must not share one receipt file"
    assert shared in mine.parents and shared in theirs.parents


def test_unstamped_legacy_receipt_is_refused(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A receipt from before workspace stamping cannot prove it belongs here.

    It was written when one directory served every repository, so it is exactly
    the file that must not be trusted. Failing closed costs a re-authorize.
    """
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    monkeypatch.delenv("L9_AUTONOMY_STATE_DIR", raising=False)

    begin(stacked_repo, contract_id="ci-legacy")
    record_kernels(stacked_repo)
    authorize_release(stacked_repo)
    assert release_allows_remote(stacked_repo)[0] is True

    for path in (receipt_path(stacked_repo), state_path(stacked_repo)):
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc.pop("workspace", None)
        path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    allowed, reason = release_allows_remote(stacked_repo)
    assert allowed is False
    assert "no workspace stamp" in reason


def test_receipt_and_phase_carry_the_workspace_they_authorize(stacked_repo: Path) -> None:
    begin(stacked_repo, contract_id="ci-stamp")
    record_kernels(stacked_repo)
    receipt = authorize_release(stacked_repo)
    identity = workspace_identity(stacked_repo)
    assert receipt["workspace"] == identity
    assert json.loads(state_path(stacked_repo).read_text(encoding="utf-8"))["workspace"] == identity
