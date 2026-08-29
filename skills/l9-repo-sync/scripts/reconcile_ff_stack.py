#!/usr/bin/env python3
"""Build a conflict-free /ff publish stack before make pr.

Cherry-picks same-repo novel commits onto origin/main, copies other-repo
commits into that dest clone, then commits valuable dirt. Fail-closed on
merge-tree conflicts. Does not push.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "l9.repo_sync.ff_stack/v1"


def _gov_root() -> Path:
    for key in ("FF_GOV_ROOT", "CURSOR_GOVERNANCE_DIR"):
        raw = os.environ.get(key, "").strip()
        if raw:
            return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parents[3]


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _utc() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _preserve_scripts() -> Path:
    return _gov_root() / "skills" / "l9-git-work-preserve" / "scripts"


def _load_wc():
    scripts = _gov_root() / "ops" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import workspace_clean as wc  # noqa: PLC0415

    return wc


def merge_tree_clean(repo: Path, base: str, head: str) -> tuple[bool, str]:
    """True when base and head merge without conflicts."""
    ancestor = _run(repo, "merge-base", base, head)
    if ancestor.returncode != 0:
        return False, ancestor.stderr.strip() or "no merge-base — cannot reconcile"
    proc = _run(repo, "merge-tree", "--write-tree", base, head)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout).strip() or "merge-tree conflict"
    return True, proc.stdout.strip()


def _add_worktree(clone: Path, branch: str, start: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    added = _run(clone, "worktree", "add", "-b", branch, str(dest), start)
    if added.returncode != 0:
        raise SystemExit(added.stderr.strip() or f"worktree add failed for {branch}")


def _copy_commit_paths(src: Path, sha: str, dest_wt: Path, paths: list[str]) -> None:
    for rel in paths:
        blob = subprocess.run(
            ["git", "-C", str(src), "show", f"{sha}:{rel}"],
            capture_output=True,
            check=False,
        )
        if blob.returncode != 0:
            continue
        out = dest_wt / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(blob.stdout)
        _run(dest_wt, "add", "--", rel)


def _commit_if_dirty(worktree: Path, message: str) -> str:
    if not _run(worktree, "status", "--porcelain").stdout.strip():
        return _run(worktree, "rev-parse", "HEAD").stdout.strip()
    committed = _run(worktree, "commit", "-m", message)
    if committed.returncode != 0:
        raise SystemExit(committed.stderr.strip() or "reconcile commit failed")
    return _run(worktree, "rev-parse", "HEAD").stdout.strip()


def _commit_dirt(worktree: Path, src: Path, paths: list[str], message: str) -> None:
    if str(_preserve_scripts()) not in sys.path:
        sys.path.insert(0, str(_preserve_scripts()))
    from commit_valuable_dirt import commit_valuable_dirt  # noqa: PLC0415

    commit_valuable_dirt(worktree, paths, message=message, src_root=src)


def build_stack(
    repo: Path,
    classify: dict[str, Any],
    *,
    stamp: str | None = None,
) -> dict[str, Any]:
    stamp = stamp or _utc()
    wc = _load_wc()
    routing = wc.load_routing(_gov_root())
    if classify.get("blocked"):
        raise SystemExit("classify blocked — resolve mixed/ambiguous dests before reconcile")

    by_dest: dict[str, dict[str, Any]] = {}
    for row in classify.get("valuable_novel") or []:
        dest = row.get("dest") or classify.get("current_dest") or "cursor-governance"
        bucket = by_dest.setdefault(dest, {"novel": [], "dirt": []})
        bucket["novel"].append(row)
    for row in classify.get("other_repo_novel") or []:
        dest = row.get("dest")
        if not dest:
            raise SystemExit(f"other-repo novel {row.get('sha')} has no dest")
        by_dest.setdefault(dest, {"novel": [], "dirt": []})["novel"].append(row)
    for row in classify.get("valuable_dirt") or []:
        dest = row.get("dest") or classify.get("current_dest") or "cursor-governance"
        by_dest.setdefault(dest, {"novel": [], "dirt": []})["dirt"].append(row)
    for row in classify.get("other_repo_dirt") or []:
        dest = row.get("dest")
        if not dest:
            raise SystemExit(f"other-repo dirt {row.get('path')} has no dest")
        by_dest.setdefault(dest, {"novel": [], "dirt": []})["dirt"].append(row)

    hold = Path(os.environ.get("L9_FF_EXTRACT_HOME") or (Path.home() / ".l9" / "ff-extract"))
    lanes: list[dict[str, Any]] = []
    errors: list[str] = []

    dest_ids = list(by_dest)
    current = classify.get("current_dest")
    if current in dest_ids:
        dest_ids.remove(current)
        dest_ids.insert(0, current)

    for dest_id in dest_ids:
        dest_cfg = (routing.get("destinations") or {}).get(dest_id) or {}
        clone = wc.resolve_clone(dest_cfg)
        if clone is None:
            errors.append(f"{dest_id}: destination clone missing — cannot publish other-repo work")
            continue
        _run(clone, "fetch", "--quiet", "origin", "main")
        if _run(clone, "rev-parse", "--verify", "origin/main").returncode != 0:
            errors.append(f"{dest_id}: origin/main missing after fetch")
            continue
        bucket = by_dest[dest_id]
        branch = f"l9/ff-preserve-{dest_id}-{stamp}"
        worktree = hold / dest_id / branch
        if worktree.exists():
            errors.append(f"{dest_id}: extract path already exists {worktree}")
            continue
        _add_worktree(clone, branch, "origin/main", worktree)
        same_repo = dest_id == current
        for row in bucket["novel"]:
            sha = row["sha"]
            if same_repo:
                picked = _run(worktree, "cherry-pick", sha)
                if picked.returncode != 0:
                    _run(worktree, "cherry-pick", "--abort")
                    errors.append(
                        f"{dest_id}: cherry-pick {sha[:12]} conflicted — catch-up aborted"
                    )
                    break
            else:
                _copy_commit_paths(repo, sha, worktree, list(row.get("paths") or []))
                _commit_if_dirty(worktree, row.get("subject") or f"ff: port {sha[:12]}")
        else:
            dirt_paths = [row["path"] for row in bucket["dirt"]]
            if dirt_paths:
                _commit_dirt(
                    worktree,
                    repo,
                    dirt_paths,
                    f"chore(ff): valuable leftover dirt for {dest_id}",
                )
            clean, detail = merge_tree_clean(worktree, "origin/main", "HEAD")
            if not clean:
                errors.append(f"{dest_id}: reconcile conflict vs origin/main: {detail}")
                continue
            stack = "" if not lanes or lanes[-1].get("dest") != dest_id else "auto"
            pr_base = "origin/main" if stack != "auto" else f"origin/{lanes[-1]['branch']}"
            if stack == "auto":
                parent = lanes[-1]["head"]
                clean_stack, stack_detail = merge_tree_clean(worktree, parent, "HEAD")
                if not clean_stack:
                    errors.append(
                        f"{dest_id}: stack conflict vs {lanes[-1]['branch']}: {stack_detail}"
                    )
                    continue
            lanes.append(
                {
                    "dest": dest_id,
                    "github": dest_cfg.get("github"),
                    "clone": str(clone),
                    "worktree": str(worktree),
                    "branch": branch,
                    "head": _run(worktree, "rev-parse", "HEAD").stdout.strip(),
                    "pr_base": pr_base,
                    "pr_stack": stack,
                    "pr_remediate": "0",
                }
            )

    if errors:
        return {
            "schema": SCHEMA,
            "repo": str(repo.resolve()),
            "stamp": stamp,
            "lanes": lanes,
            "ok": False,
            "errors": errors,
        }
    return {
        "schema": SCHEMA,
        "repo": str(repo.resolve()),
        "stamp": stamp,
        "lanes": lanes,
        "ok": True,
        "errors": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--classify", required=True, help="classify_ff_work JSON")
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    classify = json.loads(Path(args.classify).read_text(encoding="utf-8"))
    stack = build_stack(Path(args.repo).expanduser().resolve(), classify)
    text = json.dumps(stack, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if stack.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
