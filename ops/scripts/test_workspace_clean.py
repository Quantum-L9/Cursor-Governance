#!/usr/bin/env python3
"""Fixture tests for workspace_clean classify / plan / local apply."""

from __future__ import annotations

import copy
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops" / "scripts"))
import workspace_clean as wc  # noqa: E402


def _git(repo: Path, *args: str) -> None:
    proc = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr}")


def _init_repo(path: Path, remote: str) -> Path:
    path.mkdir(parents=True)
    _git(path, "init")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    (path / "README.md").write_text("base\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "base")
    _git(path, "branch", "-M", "main")
    _git(path, "remote", "add", "origin", remote)
    return path


@pytest.fixture
def routing() -> dict:
    return wc.load_routing(ROOT)


def test_classify(routing: dict) -> None:
    cases = [
        ("scripts/claude-deepseek.sh", False, "ship", "cursor-governance"),
        (".cursor/rules/claude-code-deepseek.mdc", False, "ship", "cursor-governance"),
        ("packages/bot-interop/package-lock.json", True, "ship", "website-bot"),
        (".env.local", False, "skip", ""),
        (".cursor-commands", False, "skip", ""),
        ("mystery/untracked.txt", False, "ambiguous", ""),
        ("README.md", True, "ship", "website-bot"),
    ]
    for rel, tracked, action, dest in cases:
        verdict = wc.classify_path(
            rel, routing=routing, current_dest="website-bot", tracked=tracked
        )
        assert verdict["action"] == action, f"{rel}: {verdict}"
        if dest:
            assert verdict["dest"] == dest, f"{rel}: {verdict}"


def test_plan_and_apply(tmp_path: Path, routing: dict) -> None:
    ws = _init_repo(
        tmp_path / "Website-Bot",
        "git@github.com:Quantum-L9/Website-Bot.git",
    )
    gov = _init_repo(
        tmp_path / "cursor-governance",
        "git@github.com:Quantum-L9/Cursor-Governance.git",
    )
    (ws / "scripts").mkdir()
    (ws / "scripts" / "claude-deepseek.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (ws / "packages" / "bot-interop").mkdir(parents=True)
    (ws / "packages" / "bot-interop" / "package-lock.json").write_text("{}\n", encoding="utf-8")
    (ws / ".env.local").write_text("SECRET=1\n", encoding="utf-8")
    (ws / "mystery").mkdir()
    (ws / "mystery" / "untracked.txt").write_text("nope\n", encoding="utf-8")

    routed = copy.deepcopy(routing)
    routed["destinations"]["cursor-governance"]["clone_paths"] = [str(gov)]
    routed["destinations"]["website-bot"]["clone_paths"] = [str(ws)]
    os.environ["L9_WORKSPACE_CLEAN_HOME"] = str(tmp_path / "state")

    plan = wc.build_plan(ws, ROOT, "main", routing=routed)
    assert plan["ambiguous"], "expected mystery/untracked.txt to block"
    (ws / "mystery" / "untracked.txt").unlink()
    (ws / "mystery").rmdir()
    plan = wc.build_plan(ws, ROOT, "main", routing=routed)
    assert not plan["blocked"], plan["ambiguous"]
    dests = plan["destinations"]
    assert "cursor-governance" in dests
    assert "scripts/claude-deepseek.sh" in dests["cursor-governance"]["paths"]
    assert "website-bot" in dests
    assert "packages/bot-interop/package-lock.json" in dests["website-bot"]["paths"]
    skip_paths = {row["path"] for row in plan["skipped"]}
    assert ".env.local" in skip_paths

    applied = wc.apply_plan(plan, remote=False, sweep=True)
    assert not applied.get("errors"), applied.get("errors")
    assert not (ws / "scripts" / "claude-deepseek.sh").exists()
    assert (ws / ".env.local").exists()
    shipped_gov = (applied.get("shipped") or {}).get("cursor-governance") or {}
    wt = shipped_gov.get("worktree")
    assert wt and (Path(wt) / "scripts" / "claude-deepseek.sh").is_file()
