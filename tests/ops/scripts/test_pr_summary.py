"""Publish summary receipt + the PostToolUse hook that surfaces it.

The behaviour under test is "a publish always reports what it shipped", so the
cases that matter are the ones where reporting silently stops: no receipt, a
stale receipt, a second Bash call, and an API outage that would otherwise let a
local diff pass for the PR's own file list.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "scripts"))

import write_pr_summary as wps  # noqa: E402

HOOK = (
    ROOT
    / "environment"
    / "agents"
    / "adapters"
    / "claude-code"
    / "hooks"
    / "pr_summary_posttool.py"
)


def _hook_fresh_seconds() -> float:
    """The hook's own staleness window, so the test cannot drift from it."""
    spec = importlib.util.spec_from_file_location("_pr_summary_hook", HOOK)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return float(module.FRESH_SECONDS)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "ws"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-m", "base")
    return repo


def _run_hook(workspace: Path) -> str:
    proc = subprocess.run(  # noqa: S603
        [sys.executable, str(HOOK)],
        input=json.dumps({"cwd": str(workspace), "tool_name": "Bash"}),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def _write_receipt(workspace: Path, **overrides: object) -> Path:
    doc = {
        "schema": wps.SCHEMA,
        "repo": "Quantum-L9/Cursor-Governance",
        "number": 999,
        "url": "https://github.com/Quantum-L9/Cursor-Governance/pull/999",
        "title": "fix(x): something",
        "base": "main",
        "head": "feat/x",
        "head_sha": "deadbeef",
        "commits": 2,
        "changed_files": 1,
        "additions": 3,
        "deletions": 1,
        "files": [{"path": "ops/x.py", "status": "modified", "additions": 3, "deletions": 1}],
        "files_truncated": False,
        "source": "github_api",
    }
    doc.update(overrides)
    path = workspace / wps.RECEIPT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_hook_is_silent_without_a_receipt(tmp_path: Path) -> None:
    """The overwhelmingly common case: every Bash call that is not a publish."""
    assert _run_hook(_repo(tmp_path)) == ""


def test_hook_emits_the_publish_facts(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write_receipt(repo)
    payload = json.loads(_run_hook(repo))
    out = payload["hookSpecificOutput"]
    assert out["hookEventName"] == "PostToolUse"
    context = out["additionalContext"]
    for needle in ("PR #999", "main", "feat/x", "ops/x.py", "+3/-1"):
        assert needle in context, needle


def test_hook_emits_once_per_head_then_again_after_a_new_push(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write_receipt(repo)
    assert _run_hook(repo) != "", "first call must emit"
    assert _run_hook(repo) == "", "same (pr, head_sha) must not repeat"
    _write_receipt(repo, head_sha="cafebabe")
    assert _run_hook(repo) != "", "a new head is a new publish"


def test_hook_ignores_a_stale_receipt(tmp_path: Path) -> None:
    """A receipt from an earlier publish must not be reported as this turn's."""
    repo = _repo(tmp_path)
    path = _write_receipt(repo)
    stale = time.time() - _hook_fresh_seconds() - 60
    os.utime(path, (stale, stale))
    assert _run_hook(repo) == ""


def test_hook_flags_a_local_diff_source(tmp_path: Path) -> None:
    """A degraded list must never be presented as the PR's own."""
    repo = _repo(tmp_path)
    _write_receipt(repo, source="local_diff")
    context = json.loads(_run_hook(repo))["hookSpecificOutput"]["additionalContext"]
    assert "local_diff" in context
    assert "not the GitHub API" in context


def test_hook_survives_a_malformed_receipt(tmp_path: Path) -> None:
    """Observer class: a bad receipt reports nothing, it never fails the tool."""
    repo = _repo(tmp_path)
    path = repo / wps.RECEIPT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    assert _run_hook(repo) == ""


def test_summary_falls_back_to_the_local_diff_when_the_api_is_down(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _git(repo, "branch", "-M", "main")
    _git(repo, "checkout", "-b", "feat/x")
    (repo / "b.txt").write_text("b\n", encoding="utf-8")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-m", "work")

    monkeypatch.setattr(wps, "_gh_json", lambda endpoint: None)
    summary = wps.build_summary(
        workspace=repo,
        repo="o/n",
        number=7,
        base="main",
        branch="feat/x",
        url="",
        head_sha="abc",
    )
    assert summary["source"] == "local_diff"
    assert [f["path"] for f in summary["files"]] == ["b.txt"]
    assert summary["base"] == "main"


def test_summary_reports_unavailable_rather_than_an_empty_list(tmp_path: Path, monkeypatch) -> None:
    """No API and no diff must be named, not rendered as 'zero files changed'."""
    repo = _repo(tmp_path)
    monkeypatch.setattr(wps, "_gh_json", lambda endpoint: None)
    monkeypatch.setattr(wps, "_git_files", lambda workspace, base: [])
    summary = wps.build_summary(
        workspace=repo, repo="o/n", number=7, base="main", branch="b", url="", head_sha="abc"
    )
    assert summary["source"] == "unavailable"


def test_publish_path_writes_the_receipt() -> None:
    """open_pr_after_gate.sh must call the emitter, or nothing is ever written."""
    text = (ROOT / "ops" / "scripts" / "open_pr_after_gate.sh").read_text(encoding="utf-8")
    assert "write_pr_summary.py" in text
    assert "--head-sha" in text


def test_hook_is_registered_as_an_observer_on_posttooluse() -> None:
    """A hook nobody runs reports nothing; gate class must stay observer."""
    template = json.loads(
        (
            ROOT / "environment" / "agents" / "adapters" / "claude-code" / "settings.template.json"
        ).read_text(encoding="utf-8")
    )
    entries = template["hooks"]["PostToolUse"]
    commands = [h["command"] for entry in entries for h in entry["hooks"]]
    registered = [c for c in commands if "pr_summary_posttool.py" in c]
    assert registered, "pr_summary_posttool.py must be registered on PostToolUse"
    assert all("--class observer" in c for c in registered), "must never gate a tool call"
