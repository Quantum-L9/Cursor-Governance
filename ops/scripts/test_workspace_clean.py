#!/usr/bin/env python3
"""Fixture tests for workspace_clean classify / plan / local apply."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ops" / "scripts" / "workspace_clean.py"
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


def test_classify(routing: dict) -> list[str]:
    errors: list[str] = []
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
        if verdict["action"] != action or (dest and verdict["dest"] != dest):
            errors.append(f"classify {rel}: got {verdict} want action={action} dest={dest}")
    return errors


def test_plan_and_apply(tmp: Path, routing: dict) -> list[str]:
    del routing
    errors: list[str] = []
    ws = _init_repo(
        tmp / "Website-Bot",
        "git@github.com:Quantum-L9/Website-Bot.git",
    )
    gov = _init_repo(
        tmp / "cursor-governance",
        "git@github.com:Quantum-L9/Cursor-Governance.git",
    )
    (ws / "scripts").mkdir()
    (ws / "scripts" / "claude-deepseek.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (ws / "packages" / "bot-interop").mkdir(parents=True)
    (ws / "packages" / "bot-interop" / "package-lock.json").write_text("{}\n", encoding="utf-8")
    (ws / ".env.local").write_text("SECRET=1\n", encoding="utf-8")
    (ws / "mystery").mkdir()
    (ws / "mystery" / "untracked.txt").write_text("nope\n", encoding="utf-8")

    # Point routing clones at the fixtures.
    routing_path = ROOT / "ops" / "config" / "workspace-clean-routing.yaml"
    original = routing_path.read_text(encoding="utf-8")
    patched = original.replace("$HOME/.cursor-governance", str(gov)).replace(
        "$HOME/Website-Bot", str(ws)
    )
    routing_path.write_text(patched, encoding="utf-8")
    os.environ["L9_WORKSPACE_CLEAN_HOME"] = str(tmp / "state")
    try:
        plan = wc.build_plan(ws, ROOT, "main")
        if not plan["ambiguous"]:
            errors.append("expected mystery/untracked.txt to block")
        (ws / "mystery" / "untracked.txt").unlink()
        (ws / "mystery").rmdir()
        plan = wc.build_plan(ws, ROOT, "main")
        if plan["blocked"]:
            errors.append(f"expected unblocked plan after removing mystery: {plan['ambiguous']}")
        dests = plan["destinations"]
        if "cursor-governance" not in dests or "scripts/claude-deepseek.sh" not in dests[
            "cursor-governance"
        ]["paths"]:
            errors.append(f"deepseek not routed to governance: {dests}")
        if "website-bot" not in dests or "packages/bot-interop/package-lock.json" not in dests[
            "website-bot"
        ]["paths"]:
            errors.append(f"interop not routed to website-bot: {dests}")
        skip_paths = {row["path"] for row in plan["skipped"]}
        if ".env.local" not in skip_paths:
            errors.append("expected .env.local skipped")

        applied = wc.apply_plan(plan, remote=False, sweep=True)
        if applied.get("errors"):
            errors.append(f"apply errors: {applied['errors']}")
        if (ws / "scripts" / "claude-deepseek.sh").exists():
            errors.append("expected deepseek swept from Website-Bot after ship")
        if (ws / ".env.local").exists() is False:
            errors.append("must not sweep secrets")
        shipped_gov = (applied.get("shipped") or {}).get("cursor-governance") or {}
        wt = shipped_gov.get("worktree")
        if not wt or not (Path(wt) / "scripts" / "claude-deepseek.sh").is_file():
            errors.append(f"governance worktree missing shipped script: {shipped_gov}")
    finally:
        routing_path.write_text(original, encoding="utf-8")
    return errors


def main() -> int:
    routing = wc.load_routing(ROOT)
    errors = test_classify(routing)
    with tempfile.TemporaryDirectory() as tmp:
        errors.extend(test_plan_and_apply(Path(tmp), routing))
    if errors:
        print("FAIL")
        for err in errors:
            print(f"  {err}")
        return 1
    print("PASS: test_workspace_clean")
    print(json.dumps({"schema": wc.SCHEMA, "cases": 7}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
