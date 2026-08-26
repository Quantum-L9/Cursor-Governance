"""CI-002 ownership guard for the LLM rule-adapter reconciler.

A repository-owned (git-tracked) `.claude/rules` tree must never be replaced by
the generated directory symlink — that deletes the tracked files and dirties the
consumer checkout (measured on Cognitive.Engine.Graphs: 9 tracked-file
deletions). The reconciler must refuse and leave the tracked tree intact. An
untracked target still gets the mount (unchanged behavior).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

import reconcile_llm_rule_adapters as rr  # noqa: E402


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True)


def _init_workspace(tmp_path: Path, *, track_rules: bool) -> Path:
    ws = tmp_path / "consumer"
    (ws / ".claude" / "rules").mkdir(parents=True)
    (ws / ".claude" / "rules" / "00-local.md").write_text("# consumer-owned\n", encoding="utf-8")
    _git("init", "-q", cwd=ws)
    _git("config", "user.email", "t@t", cwd=ws)
    _git("config", "user.name", "t", cwd=ws)
    if track_rules:
        _git("add", ".claude/rules/00-local.md", cwd=ws)
        _git("commit", "-qm", "own rules", cwd=ws)
    return ws


def _fake_ssot(tmp_path: Path) -> Path:
    gov = tmp_path / "gov"
    ssot = gov / "environment" / "generated" / "llm-rules"
    ssot.mkdir(parents=True)
    (ssot / "00-global.md").write_text("# generated\n", encoding="utf-8")
    return gov


def test_tracked_rules_tree_is_not_replaced(tmp_path: Path) -> None:
    ws = _init_workspace(tmp_path, track_rules=True)
    gov = _fake_ssot(tmp_path)
    target = ws / ".claude" / "rules"
    ssot = gov / "environment" / "generated" / "llm-rules"

    result = rr.reconcile_one(target, ssot, root=gov, check=False)

    assert result["status"] == "blocked", result
    # The tracked tree survives untouched — real dir, its committed file present.
    assert target.is_dir() and not target.is_symlink()
    assert (target / "00-local.md").read_text(encoding="utf-8") == "# consumer-owned\n"


def test_untracked_rules_target_still_gets_the_mount(tmp_path: Path) -> None:
    ws = _init_workspace(tmp_path, track_rules=False)  # .claude/rules NOT committed
    gov = _fake_ssot(tmp_path)
    target = ws / ".claude" / "rules"
    # Remove the untracked dir so the mount can be created where nothing is owned.
    for child in target.iterdir():
        child.unlink()
    target.rmdir()
    ssot = gov / "environment" / "generated" / "llm-rules"

    result = rr.reconcile_one(target, ssot, root=gov, check=False)

    assert result["status"] == "ok", result
    assert target.is_symlink()
    assert target.resolve() == ssot.resolve()


def test_is_tracked_detects_committed_path(tmp_path: Path) -> None:
    ws = _init_workspace(tmp_path, track_rules=True)
    assert rr.is_tracked(ws / ".claude" / "rules" / "00-local.md") is True
    # A path outside any repo is not tracked (git unavailable / no repo).
    assert rr.is_tracked(tmp_path / "nowhere" / "x.md") is False
