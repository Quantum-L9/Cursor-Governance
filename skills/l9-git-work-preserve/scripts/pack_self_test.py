#!/usr/bin/env python3
"""Fixture self-test for l9-git-work-preserve scripts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd or ROOT), text=True, capture_output=True)


def _git(repo: Path, *args: str) -> None:
    proc = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr}")


def build_fixture(tmp: Path) -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-m", "base")
    _git(repo, "branch", "-M", "main")
    # Simulate origin/main
    _git(repo, "branch", "origin/main")
    _git(repo, "checkout", "-b", "feature/x")
    (repo / "b.txt").write_text("b\n", encoding="utf-8")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-m", "unique")
    (repo / "dirty.txt").write_text("dirt\n", encoding="utf-8")
    return repo


def main() -> int:
    errors: list[str] = []
    struct = run([sys.executable, str(SCRIPTS / "validate_pack_structure.py")])
    if struct.returncode != 0:
        errors.append(struct.stderr or struct.stdout)

    with tempfile.TemporaryDirectory() as tmp:
        repo = build_fixture(Path(tmp))
        inv = run(
            [
                sys.executable,
                str(SCRIPTS / "inventory_git_work.py"),
                "--repo",
                str(repo),
                "--baseline",
                "main",
                "--json",
            ]
        )
        if inv.returncode != 0:
            errors.append(f"inventory failed: {inv.stderr}")
        else:
            data = json.loads(inv.stdout)
            if not data.get("dirty"):
                errors.append("expected dirty fixture")
            names = {b["name"] for b in data.get("branches", [])}
            if "feature/x" not in names:
                errors.append("expected feature/x in inventory")
            ahead = [b for b in data["branches"] if b["name"] == "feature/x"]
            if not ahead or ahead[0].get("ahead_of_baseline", 0) < 1:
                errors.append("expected feature/x ahead of baseline")

        diag = run(
            [
                sys.executable,
                str(SCRIPTS / "diagnose_ref_value.py"),
                "--repo",
                str(repo),
                "--ref",
                "feature/x",
                "--baseline",
                "main",
            ]
        )
        if diag.returncode != 0:
            errors.append(f"diagnose failed: {diag.stderr}")
        else:
            receipt = json.loads(diag.stdout)
            if receipt.get("classification") != "keep_push":
                errors.append(f"expected keep_push got {receipt.get('classification')}")
            if receipt.get("unique_commits", 0) < 1:
                errors.append("expected unique commits")

        diag_main = run(
            [
                sys.executable,
                str(SCRIPTS / "diagnose_ref_value.py"),
                "--repo",
                str(repo),
                "--ref",
                "main",
                "--baseline",
                "main",
            ]
        )
        if diag_main.returncode == 0:
            r2 = json.loads(diag_main.stdout)
            if r2.get("classification") != "prune_candidate":
                got = r2.get("classification")
                errors.append(f"main vs main expected prune_candidate got {got}")

        extra = Path(tmp) / "wts"
        extra.mkdir()
        wt = extra / "unique"
        _git(repo, "worktree", "add", str(wt), "main")
        (wt / "WIP").mkdir()
        (wt / "WIP" / "note.md").write_text("wip leftover\n", encoding="utf-8")
        skill = wt / ".claude" / "skills" / "l9-fake"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("wiring\n", encoding="utf-8")
        (wt / "feat.py").write_text("print(1)\n", encoding="utf-8")
        harvest = run(
            [
                sys.executable,
                str(SCRIPTS / "harvest_worktree_dirt.py"),
                "--repo",
                str(repo),
                "--baseline",
                "main",
                "--extra-root",
                str(extra),
                "--include-wip",
                "--json",
            ]
        )
        if harvest.returncode != 0:
            errors.append(f"harvest failed: {harvest.stderr or harvest.stdout}")
        else:
            plan = json.loads(harvest.stdout)
            by_class = {row["class"] for row in plan.get("harvestable", [])}
            if "unique_wip" not in by_class:
                errors.append("expected unique_wip in harvestable")
            if "unique_product" not in by_class:
                errors.append("expected unique_product in harvestable")
            skipped_classes = {row["class"] for row in plan.get("skipped", [])}
            if "wiring_noise" not in skipped_classes:
                errors.append("expected wiring_noise skipped")
            if plan.get("schema") != "l9.git_work_preserve.harvest/v1":
                errors.append("expected harvest schema")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("PASS: self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
