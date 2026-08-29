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

    # The case git cherry structurally cannot see: every ordinary commit on the
    # branch is patch-duplicated upstream, but a merge commit carries resolution
    # content that landed nowhere. cherry skips merges, so the range reads as
    # fully absorbed. The merge is of a side branch, not of main -- merging main
    # would make all of main reachable and leave cherry nothing to compare
    # against, which reports every commit novel and hides this case instead.
    _git(repo, "checkout", "-b", "feature/dup-merge", "main")
    _commit(repo, "m.txt", "m\n", "dup-merge: ordinary commit")
    msha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True, capture_output=True
    ).stdout.strip()
    _git(repo, "checkout", "-b", "feature/dup-side", "main")
    _commit(repo, "s.txt", "s\n", "dup-merge: side commit")
    ssha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True, capture_output=True
    ).stdout.strip()
    _git(repo, "checkout", "feature/dup-merge")
    _git(repo, "merge", "--no-ff", "feature/dup-side", "-m", "merge side branch")
    # Fold unique content into the merge commit itself.
    (repo / "resolution.txt").write_text("resolution only on this merge\n", encoding="utf-8")
    _git(repo, "add", "resolution.txt")
    _git(repo, "commit", "--amend", "--no-edit")
    # Main independently acquires both ordinary patches, but never the merge's
    # resolution.
    _git(repo, "checkout", "main")
    _git(repo, "cherry-pick", msha)
    _git(repo, "cherry-pick", ssha)

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

    # A merge git cherry never examined must not earn the exact patch_id basis:
    # prune-policy lets that basis authorise a delete, and the merge resolution
    # has not landed anywhere.
    dm = _diagnose(repo, "feature/dup-merge")
    if dm.get("merge_commits_unexamined", 0) < 1:
        errors.append("dup-merge fixture should carry an unexamined merge commit")
    if dm.get("redundancy_basis") == "patch_id":
        errors.append("unexamined merge must not yield the patch_id basis")
    if dm.get("classification") == "archive_ref" and dm.get("redundancy_basis") == "patch_id":
        errors.append("unexamined merge must not be auto-prunable")

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


def _park(repo: Path, ref: str, committish: str) -> None:
    """Create a preserve ref the way skills/l9-repo-sync/scripts/ff.sh does."""
    _git(repo, "update-ref", ref, committish)


def check_triage(repo: Path, errors: list[str]) -> None:
    """The /ff handoff: park refs, then classify them by evidence, deleting nothing."""
    # Mirror all three shapes ff.sh parks, each pointing at a branch whose
    # classification is already pinned by check_redundancy.
    _park(repo, "refs/l9/preserved/ff/20260827T000000Z", "feature/novel")
    _park(repo, "refs/heads/l9/ff-preserve-20260827T000000Z", "feature/dup")
    _park(repo, "refs/l9/preserved/ff-dirty/20260827T000000Z", "feature/superseded")

    proc = run(
        [
            sys.executable,
            str(SCRIPTS / "triage_preserved_refs.py"),
            "--repo",
            str(repo),
            "--baseline",
            "main",
        ]
    )
    if proc.returncode != 0:
        errors.append(f"triage failed: {proc.stderr}")
        return
    data = json.loads(proc.stdout)

    if data.get("preserved_total") != 3:
        errors.append(f"triage should find 3 parked refs, got {data.get('preserved_total')}")
    buckets = data["buckets"]
    if "refs/l9/preserved/ff/20260827T000000Z" not in buckets["novel"]:
        errors.append(f"unlanded parked ref belongs in novel, got {buckets['novel']}")
    # Exact patch-id evidence may authorise a later prune; heuristic absorption may not.
    if "refs/heads/l9/ff-preserve-20260827T000000Z" not in buckets["superseded"]:
        errors.append(f"patch_id ref belongs in superseded, got {buckets['superseded']}")
    if "refs/l9/preserved/ff-dirty/20260827T000000Z" not in buckets["review"]:
        errors.append(f"content_superset ref belongs in review, got {buckets['review']}")
    if set(buckets["superseded"]) & set(buckets["review"]):
        errors.append("a ref must not occupy both superseded and review")

    # Every entry must carry the recovery data that makes parking reversible.
    for entry in data["refs"]:
        if not entry.get("tip_sha") or not entry.get("restore"):
            errors.append(f"triage entry missing recovery data: {entry.get('ref')}")

    # The safety property: triage is read-only. Nothing it classified may vanish.
    if data.get("deletes_performed") != 0:
        errors.append("triage must never delete")
    after = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "for-each-ref",
            "--format=%(refname)",
            "refs/l9/preserved/*/*",
            "refs/heads/l9/ff-preserve-*",
        ],
        text=True,
        capture_output=True,
    ).stdout.split()
    if len(after) != 3:
        errors.append(f"triage removed parked refs: {after}")


def check_extract_path_union(tmp: Path, errors: list[str]) -> None:
    """Mixed leftover refs extract by path-union; they never cherry-pick."""
    repo = _init(tmp / "extract-union")
    _git(repo, "checkout", "-b", "feature/mixed")
    _commit(repo, "unique.txt", "only on leftover\n", "add unique")
    (repo / "a.txt").unlink()
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-m", "delete baseline file")

    dest = tmp / "extract-dest"
    _git(repo, "worktree", "add", str(dest), "main")
    dest_head = subprocess.run(
        ["git", "-C", str(dest), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()

    plan = run(
        [
            sys.executable,
            str(SCRIPTS / "extract_path_union.py"),
            "--repo",
            str(repo),
            "--ref",
            "feature/mixed",
            "--baseline",
            "main",
            "--json",
        ]
    )
    if plan.returncode != 0:
        errors.append(f"extract_path_union plan failed: {plan.stderr or plan.stdout}")
        return
    data = json.loads(plan.stdout)
    copy_paths = {row["path"] for row in data.get("copy", [])}
    skip_by_path = {row["path"]: row["reason"] for row in data.get("skip", [])}
    if "unique.txt" not in copy_paths:
        errors.append(f"path-absent unique.txt should copy, got {data.get('copy')}")
    if skip_by_path.get("a.txt") != "baseline_delete":
        errors.append(f"baseline delete a.txt should skip, got {data.get('skip')}")
    if data.get("cherry_pick") is not False:
        errors.append("extract_path_union must never cherry-pick")
    if not data.get("mixed_range"):
        errors.append("delete-plus-add leftover ref is a mixed range")

    applied = run(
        [
            sys.executable,
            str(SCRIPTS / "extract_path_union.py"),
            "--repo",
            str(repo),
            "--ref",
            "feature/mixed",
            "--baseline",
            "main",
            "--apply",
            "--dest",
            str(dest),
        ]
    )
    if applied.returncode != 0:
        errors.append(f"extract_path_union apply failed: {applied.stderr or applied.stdout}")
        return
    if not (dest / "unique.txt").is_file():
        errors.append("apply should write the path-absent file")
    if not (dest / "a.txt").is_file():
        errors.append("apply must not delete a path that exists on baseline")
    after_head = subprocess.run(
        ["git", "-C", str(dest), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    if after_head != dest_head:
        errors.append("apply must not cherry-pick or otherwise move destination HEAD")

    empty = tmp / "empty-allowlist.json"
    empty.write_text(json.dumps({"copy": [], "skip": []}), encoding="utf-8")
    stopped = run(
        [
            sys.executable,
            str(SCRIPTS / "extract_path_union.py"),
            "--repo",
            str(repo),
            "--ref",
            "feature/mixed",
            "--baseline",
            "main",
            "--allowlist",
            str(empty),
        ]
    )
    if stopped.returncode != 0:
        errors.append(f"empty allowlist should succeed: {stopped.stderr or stopped.stdout}")
        return
    stopped_data = json.loads(stopped.stdout)
    if stopped_data.get("copy"):
        errors.append("empty copy set must copy nothing")
    if not stopped_data.get("stop"):
        errors.append("empty copy set is a valid stop")

    overwrite = _init(tmp / "extract-present")
    _git(overwrite, "checkout", "-b", "feature/overwrite")
    _commit(overwrite, "a.txt", "rewritten\n", "overwrite baseline path")
    blocked = run(
        [
            sys.executable,
            str(SCRIPTS / "extract_path_union.py"),
            "--repo",
            str(overwrite),
            "--ref",
            "feature/overwrite",
            "--baseline",
            "main",
        ]
    )
    if blocked.returncode != 0:
        errors.append(f"overwrite classify failed: {blocked.stderr or blocked.stdout}")
        return
    blocked_data = json.loads(blocked.stdout)
    if any(row["path"] == "a.txt" for row in blocked_data.get("copy", [])):
        errors.append("path present on baseline must not enter the copy set")
    if blocked_data.get("cherry_pick") is not False:
        errors.append("overwrite leftover must not cherry-pick")

    same_tree = run(
        [
            sys.executable,
            str(SCRIPTS / "extract_path_union.py"),
            "--repo",
            str(repo),
            "--ref",
            "feature/mixed",
            "--baseline",
            "main",
            "--apply",
            "--dest",
            str(repo),
        ]
    )
    if same_tree.returncode == 0:
        errors.append("apply onto --repo must be refused")


def check_harvest(repo: Path, tmp: Path, errors: list[str]) -> None:
    """Sibling-worktree dirt still classifies; triage did not displace harvest."""
    extra = tmp / "wts"
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
        return
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


def check_mode_change(tmp: Path, errors: list[str]) -> None:
    """A permission-only change has no lines, so absorption must refuse to judge it."""
    repo = _init(tmp / "modechange")
    _commit(repo, "s.sh", "#!/bin/sh\necho hi\n", "add script")
    _git(repo, "checkout", "-b", "feature/exec")
    (repo / "s.sh").chmod(0o755)
    _git(repo, "add", "s.sh")
    _git(repo, "commit", "-m", "make executable")
    receipt = _diagnose(repo, "feature/exec")
    if receipt.get("content_contained"):
        errors.append("mode-only change must not read as absorbed")
    if receipt.get("classification") != "keep_push":
        errors.append(f"mode-only change expected keep_push got {receipt.get('classification')}")


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
        check_mode_change(root, errors)
        check_harvest(repo, root, errors)
        check_extract_path_union(root, errors)
        check_triage(build_redundancy_fixture(root / "triage"), errors)

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("PASS: self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
