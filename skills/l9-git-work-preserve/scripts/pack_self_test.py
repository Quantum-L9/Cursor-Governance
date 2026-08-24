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


def _commit(repo: Path, name: str, body: str, message: str) -> None:
    (repo / name).write_text(body, encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-m", message)


def _init(repo: Path) -> Path:
    repo.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _commit(repo, "a.txt", "a\n", "base")
    _git(repo, "branch", "-M", "main")
    return repo


def _diagnose(repo: Path, ref: str, baseline: str = "main", fetch: bool = False) -> dict:
    cmd = [
        sys.executable,
        str(SCRIPTS / "diagnose_ref_value.py"),
        "--repo",
        str(repo),
        "--ref",
        ref,
        "--baseline",
        baseline,
    ]
    if fetch:
        cmd.append("--fetch")
    proc = run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"diagnose {ref}: {proc.stderr}")
    return json.loads(proc.stdout)


def build_fixture(tmp: Path) -> Path:
    repo = _init(tmp / "repo")
    # Simulate origin/main
    _git(repo, "branch", "origin/main")
    _git(repo, "checkout", "-b", "feature/x")
    _commit(repo, "b.txt", "b\n", "unique")
    (repo / "dirty.txt").write_text("dirt\n", encoding="utf-8")
    return repo


def build_redundancy_fixture(tmp: Path) -> Path:
    """Branches whose work already reached main by two different routes."""
    repo = _init(tmp / "redundant")

    # Cherry-picked: identical patch, different sha. Main must diverge first or
    # the cherry-pick reproduces the original sha and the range goes empty.
    _git(repo, "checkout", "-b", "feature/dup")
    _commit(repo, "b.txt", "b\n", "will be cherry-picked")
    sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True, capture_output=True
    ).stdout.strip()
    _git(repo, "checkout", "main")
    _commit(repo, "unrelated.txt", "moved on\n", "unrelated main work")
    _git(repo, "cherry-pick", sha)

    # Superseded: main reimplemented the same work more fully, so the patch ids
    # differ and only content absorption can see that the branch is redundant.
    _git(repo, "checkout", "-b", "feature/superseded", "main")
    _commit(repo, "impl.py", "def f():\n    return 1\n", "add impl")
    _git(repo, "checkout", "main")
    _commit(repo, "impl.py", "def f():\n    return 1\n\ndef g():\n    return 2\n", "fuller impl")

    # Genuinely novel: nothing on main carries this.
    _git(repo, "checkout", "-b", "feature/novel", "main")
    _commit(repo, "new.txt", "brand new\n", "novel work")
    _git(repo, "checkout", "main")
    return repo


def build_remote_fixture(tmp: Path) -> Path:
    """A repo with a real (path) remote, so --fetch exercises the network-free path."""
    bare = tmp / "origin.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)], capture_output=True)
    repo = _init(tmp / "withremote")
    _git(repo, "remote", "add", "origin", str(bare))
    _git(repo, "push", "-q", "origin", "main")
    return repo


def check_inventory(repo: Path, errors: list[str]) -> None:
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
        return
    data = json.loads(inv.stdout)
    if not data.get("dirty"):
        errors.append("expected dirty fixture")
    names = {b["name"] for b in data.get("branches", [])}
    if "feature/x" not in names:
        errors.append("expected feature/x in inventory")
    ahead = [b for b in data["branches"] if b["name"] == "feature/x"]
    if not ahead or ahead[0].get("ahead_of_baseline", 0) < 1:
        errors.append("expected feature/x ahead of baseline")


def check_baseline_cases(repo: Path, errors: list[str]) -> None:
    receipt = _diagnose(repo, "feature/x")
    if receipt.get("classification") != "keep_push":
        errors.append(f"expected keep_push got {receipt.get('classification')}")
    if receipt.get("unique_commits", 0) < 1:
        errors.append("expected unique commits")

    main_vs_main = _diagnose(repo, "main")
    if main_vs_main.get("classification") != "prune_candidate":
        errors.append(
            f"main vs main expected prune_candidate got {main_vs_main.get('classification')}"
        )

    # A missing baseline must keep the ref, never fall through to prune_candidate.
    absent = _diagnose(repo, "feature/x", baseline="origin/does-not-exist")
    if absent.get("classification") != "unknown":
        errors.append(f"absent baseline expected unknown got {absent.get('classification')}")

    # --fetch on a repo with no remote degrades quietly and changes no verdict.
    degraded = _diagnose(repo, "feature/x", fetch=True)
    if degraded.get("fetched") is not False:
        errors.append("no-remote fetch should report fetched=false")
    if degraded.get("classification") != "keep_push":
        errors.append("no-remote fetch must not change classification")


def check_redundancy(repo: Path, errors: list[str]) -> None:
    dup = _diagnose(repo, "feature/dup")
    if dup.get("classification") != "archive_ref":
        errors.append(f"cherry-picked branch expected archive_ref got {dup.get('classification')}")
    if dup.get("redundancy_basis") != "patch_id":
        errors.append(f"cherry-picked basis expected patch_id got {dup.get('redundancy_basis')}")
    if dup.get("cherry_dup", 0) < 1 or dup.get("cherry_novel", 1) != 0:
        errors.append("cherry-picked branch should be all duplicate patches")

    # The regression this pack exists for: counting commits called this keep_push.
    sup = _diagnose(repo, "feature/superseded")
    if sup.get("classification") != "archive_ref":
        errors.append(f"superseded branch expected archive_ref got {sup.get('classification')}")
    if sup.get("redundancy_basis") != "content_superset":
        errors.append(
            f"superseded basis expected content_superset got {sup.get('redundancy_basis')}"
        )
    if sup.get("cherry_novel", 0) < 1:
        errors.append("superseded branch should still look novel to git cherry")

    novel = _diagnose(repo, "feature/novel")
    if novel.get("classification") != "keep_push":
        errors.append(f"novel branch expected keep_push got {novel.get('classification')}")
    if novel.get("content_contained"):
        errors.append("novel branch must not read as contained")


def check_real_fetch(repo: Path, errors: list[str]) -> None:
    inv = run(
        [
            sys.executable,
            str(SCRIPTS / "inventory_git_work.py"),
            "--repo",
            str(repo),
            "--baseline",
            "origin/main",
            "--fetch",
            "--json",
        ]
    )
    if inv.returncode != 0:
        errors.append(f"inventory --fetch failed: {inv.stderr}")
        return
    data = json.loads(inv.stdout)
    if data.get("fetched") is not True:
        errors.append(f"path remote should fetch, got {data.get('fetch_error')}")
    if not data.get("baseline_tip"):
        errors.append("fetched inventory should resolve a baseline tip")


def check_ff_pipeline(repo: Path, errors: list[str]) -> None:
    plan = run(
        [
            sys.executable,
            str(SCRIPTS / "ff_pipeline.py"),
            "--repo",
            str(repo),
            "--baseline",
            "main",
            "--mode",
            "plan",
            "--no-fetch",
        ]
    )
    if plan.returncode != 0:
        errors.append(f"ff plan failed: {plan.stderr}")
        return
    data = json.loads(plan.stdout)
    buckets = {
        "novel": {e["branch"] for e in data["novel"]},
        "superseded": {e["branch"] for e in data["superseded"]},
    }
    if "feature/novel" not in buckets["novel"]:
        errors.append("ff plan should route feature/novel to novel")
    if not {"feature/dup", "feature/superseded"} <= buckets["superseded"]:
        errors.append(f"ff plan should route both redundant branches, got {buckets['superseded']}")

    # Safe delete cannot remove a redundant-but-unmerged branch. The pipeline must
    # say so with a rollback sha rather than force it.
    applied = run(
        [
            sys.executable,
            str(SCRIPTS / "ff_pipeline.py"),
            "--repo",
            str(repo),
            "--baseline",
            "main",
            "--mode",
            "apply",
        ]
    )
    receipt = json.loads(applied.stdout)
    needs = {e["branch"] for e in receipt["needs_human"]}
    if "feature/superseded" not in needs:
        errors.append(f"superseded branch should need a human, got needs_human={needs}")
    for entry in receipt["needs_human"]:
        if not entry.get("rollback") or not entry.get("tip_sha"):
            errors.append(f"needs_human entry missing recovery data: {entry.get('branch')}")


def main() -> int:
    errors: list[str] = []
    struct = run([sys.executable, str(SCRIPTS / "validate_pack_structure.py")])
    if struct.returncode != 0:
        errors.append(struct.stderr or struct.stdout)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = build_fixture(root)
        check_inventory(repo, errors)
        check_baseline_cases(repo, errors)
        check_redundancy(build_redundancy_fixture(root), errors)
        check_real_fetch(build_remote_fixture(root), errors)
        check_ff_pipeline(build_redundancy_fixture(root / "ff"), errors)

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("PASS: self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
