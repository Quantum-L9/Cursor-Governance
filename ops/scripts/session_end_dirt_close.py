#!/usr/bin/env python3
"""Classify, clean, and prune leftover session-workspace dirt.

Dirty files are novel unique porcelain paths only — not copies already on
origin/main, not an open-PR blob at the same path, not generated noise, and
not secrets / Legal Defense. After --apply, dirty_files is 0 when every
closable path was processed. Novel unique bytes live on one rolling
refs/heads/l9/dirt-shelf. Absorbed shelf tips are deleted after the tip SHA
is recorded.

This is the sessionEnd closer. It does not call /ff, make pr, or merge.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parents[1]
for _path in (SCRIPTS, SCRIPTS / "lib"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
_HARVEST = REPO / "skills" / "l9-git-work-preserve" / "scripts"
if str(_HARVEST) not in sys.path:
    sys.path.insert(0, str(_HARVEST))

import harvest_worktree_dirt  # noqa: E402
import prune_open_pr_copies  # noqa: E402
import repo_hygiene  # noqa: E402
from dirtiness import porcelain_path  # noqa: E402
from sync_generated_artifacts import is_generated_path  # noqa: E402

DIRT_SHELF_REF = "refs/heads/l9/dirt-shelf"
WORKTREE_DIRT_GLOB = "refs/l9/preserved/worktree-dirt/*"
MAX_NOVEL_PATHS = 200
DEFAULT_QUIET_SECONDS = 120
DEFAULT_BASELINE = "origin/main"
SECRET_PREFIXES = ("WIP/Legal Defense/",)
SECRET_GLOBS = (
    "WIP/*oauth*.json",
    "WIP/*credentials*.json",
    "WIP/*client_secret*.json",
)
LEAVE_CLASSES = frozenset({"skip_noise", "wiring_noise", "secret"})
LANDED_CLASSES = frozenset({"already_on_baseline", "already_on_open_pr", "generated"})
NOVEL_CLASS = "unique_novel"


def _git(root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
        env=merged,
    )


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_secret_path(rel: str) -> bool:
    norm = rel.replace("\\", "/")
    if any(norm == p.rstrip("/") or norm.startswith(p) for p in SECRET_PREFIXES):
        return True
    return any(fnmatch.fnmatch(norm, pat) for pat in SECRET_GLOBS)


def lock_id(workspace: Path) -> str:
    proc = subprocess.run(  # noqa: S603
        ["cksum"],
        input=str(workspace),
        capture_output=True,
        text=True,
        check=False,
    )
    return (proc.stdout.split() or [""])[0]


def repo_write_lock_held(workspace: Path) -> bool:
    if os.environ.get("L9_REPO_WRITE_LOCK", "1") in {"0", "false", "no"}:
        return False
    ident = lock_id(workspace)
    if not ident:
        return False
    owner = Path.home() / ".cursor" / f"l9-repo-write.{ident}.lock.d" / "owner"
    return owner.is_file() and bool(owner.read_text(encoding="utf-8").strip())


def parse_payload(raw: str) -> dict[str, Any]:
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def kill_switch_off() -> bool:
    return os.environ.get("L9_HYGIENE_DIRT_CLOSE", "1") in {"0", "false", "no"}


def gate_skip_reason(payload: dict[str, Any], workspace: Path, closable: list[str]) -> str:
    if kill_switch_off():
        return "L9_HYGIENE_DIRT_CLOSE=0"
    reason = str(payload.get("reason") or "")
    if reason in {"aborted", "error"}:
        return f"sessionEnd reason={reason}"
    if payload.get("is_background_agent") is True:
        return "background agent session"
    if repo_write_lock_held(workspace):
        return "repo-write lock held"
    quiet = int(os.environ.get("L9_DIRT_CLOSE_QUIET_SECONDS", DEFAULT_QUIET_SECONDS))
    if quiet > 0 and _newest_age_seconds(workspace, closable) < quiet:
        return f"quiet window {quiet}s"
    return ""


def _newest_age_seconds(workspace: Path, rels: list[str]) -> float:
    newest = 0.0
    now = time.time()
    for rel in rels:
        path = workspace / rel
        try:
            newest = max(newest, path.stat().st_mtime)
        except OSError:
            continue
    if newest <= 0:
        return float("inf")
    return now - newest


def porcelain_rels(root: Path) -> list[tuple[str, str]]:
    proc = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in proc.stdout.splitlines():
        if not line:
            continue
        status = line[:2] if len(line) >= 2 else ""
        rel = porcelain_path(line)
        if not rel or rel in seen:
            continue
        seen.add(rel)
        rows.append((status, rel))
    return rows


def blob_equals_baseline(root: Path, baseline: str, rel: str) -> bool:
    if not _git(root, "cat-file", "-e", f"{baseline}:{rel}").returncode == 0:
        return False
    wt = _sha256_file(root / rel)
    if wt is None:
        return False
    blob = prune_open_pr_copies.sha256_blob(root, baseline, rel)
    return blob is not None and blob == wt


def classify_rel(
    rel: str,
    *,
    root: Path,
    baseline: str,
    blob_index: dict[str, set[str]],
    pr_index_error: str,
) -> str:
    if harvest_worktree_dirt.is_skip_noise(rel):
        return "skip_noise"
    if harvest_worktree_dirt.is_wiring_noise(rel):
        return "wiring_noise"
    if is_secret_path(rel):
        return "secret"
    if is_generated_path(rel):
        return "generated"
    if blob_equals_baseline(root, baseline, rel):
        return "already_on_baseline"
    if not pr_index_error:
        digest = _sha256_file(root / rel)
        hashes = blob_index.get(prune_open_pr_copies.path_key(rel), set())
        if digest and digest in hashes:
            return "already_on_open_pr"
    return NOVEL_CLASS


def classify_workspace(
    root: Path,
    *,
    baseline: str,
    blob_index: dict[str, set[str]],
    pr_index_error: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for status, rel in porcelain_rels(root):
        klass = classify_rel(
            rel,
            root=root,
            baseline=baseline,
            blob_index=blob_index,
            pr_index_error=pr_index_error,
        )
        rows.append({"path": rel, "status": status, "class": klass})
    return rows


def load_open_pr_index(
    git: repo_hygiene.Git,
    *,
    baseline: str,
    blob_index_path: str,
    pr_heads: list[str],
) -> tuple[dict[str, set[str]], str]:
    if blob_index_path:
        return prune_open_pr_copies.load_blob_index(Path(blob_index_path)), ""
    heads = list(pr_heads)
    slug = repo_hygiene.origin_slug(git.out("remote", "get-url", "origin"))
    if slug:
        prs, err = repo_hygiene.pr_index(slug)
        if err:
            return {}, err
        for name, rec in prs.items():
            if str(rec.get("state") or "") == "OPEN" and name not in heads:
                heads.append(name)
    if not heads:
        return {}, ""
    return prune_open_pr_copies.build_blob_index(git, heads, baseline), ""


def head_has_path(root: Path, rel: str) -> bool:
    return _git(root, "cat-file", "-e", f"HEAD:{rel}").returncode == 0


def restore_or_remove(root: Path, rel: str) -> str:
    if head_has_path(root, rel):
        proc = _git(root, "restore", "--source=HEAD", "--staged", "--worktree", "--", rel)
        return "restored" if proc.returncode == 0 else f"restore-failed:{proc.stderr.strip()[:120]}"
    path = root / rel
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()
        return "removed"
    except OSError as exc:
        return f"remove-failed:{exc}"


def ref_exists(root: Path, ref: str) -> bool:
    return _git(root, "show-ref", "--verify", "--quiet", ref).returncode == 0


def ref_sha(root: Path, ref: str) -> str:
    return _git(root, "rev-parse", ref).stdout.strip()


def tree_paths(root: Path, rev: str) -> list[str]:
    proc = _git(root, "ls-tree", "-r", "--name-only", rev)
    return [ln for ln in proc.stdout.splitlines() if ln]


def park_novel(root: Path, rels: list[str]) -> tuple[str, str]:
    """Park unique paths onto l9/dirt-shelf. Returns (ref, commit_sha or skip)."""
    if not rels:
        return DIRT_SHELF_REF, ""
    with tempfile.TemporaryDirectory(prefix="l9-dirt-close-") as tmp:
        index = Path(tmp) / "index"
        env = {"GIT_INDEX_FILE": str(index)}
        add = _git(root, "add", "-f", "--", *rels, env=env)
        if add.returncode != 0:
            return DIRT_SHELF_REF, f"add-failed:{add.stderr.strip()[:160]}"
        tree = _git(root, "write-tree", env=env).stdout.strip()
        if not tree:
            return DIRT_SHELF_REF, "write-tree-failed"
        if ref_exists(root, DIRT_SHELF_REF):
            current_tree = _git(root, "rev-parse", f"{DIRT_SHELF_REF}^{{tree}}").stdout.strip()
            if current_tree == tree:
                return DIRT_SHELF_REF, "unchanged"
            parent = ref_sha(root, DIRT_SHELF_REF)
        else:
            parent = _git(root, "rev-parse", "HEAD").stdout.strip()
        commit = _git(
            root,
            "commit-tree",
            tree,
            "-p",
            parent,
            "-m",
            "park: session-end dirt",
        ).stdout.strip()
        if not commit:
            return DIRT_SHELF_REF, "commit-tree-failed"
        upd = _git(root, "update-ref", DIRT_SHELF_REF, commit)
        if upd.returncode != 0:
            return DIRT_SHELF_REF, f"update-ref-failed:{upd.stderr.strip()[:160]}"
        return DIRT_SHELF_REF, commit


def path_on_rev(root: Path, rev: str, rel: str) -> bool:
    return _git(root, "cat-file", "-e", f"{rev}:{rel}").returncode == 0


def shelf_path_absorbed(
    root: Path,
    rev: str,
    rel: str,
    *,
    baseline: str,
    blob_index: dict[str, set[str]],
    pr_index_error: str,
) -> bool:
    blob = prune_open_pr_copies.sha256_blob(root, rev, rel)
    if blob is None:
        return False
    base = prune_open_pr_copies.sha256_blob(root, baseline, rel)
    if base is not None and base == blob:
        return True
    if not pr_index_error:
        hashes = blob_index.get(prune_open_pr_copies.path_key(rel), set())
        if blob in hashes:
            return True
    return False


def prune_absorbed_refs(
    root: Path,
    *,
    baseline: str,
    blob_index: dict[str, set[str]],
    pr_index_error: str,
) -> list[dict[str, str]]:
    pruned: list[dict[str, str]] = []
    refs = [DIRT_SHELF_REF] if ref_exists(root, DIRT_SHELF_REF) else []
    listed = _git(root, "for-each-ref", "--format=%(refname)", WORKTREE_DIRT_GLOB)
    refs.extend(ln for ln in listed.stdout.splitlines() if ln)
    for ref in refs:
        tip = ref_sha(root, ref)
        paths = tree_paths(root, ref)
        if not paths:
            continue
        leftover = [
            rel
            for rel in paths
            if not shelf_path_absorbed(
                root,
                ref,
                rel,
                baseline=baseline,
                blob_index=blob_index,
                pr_index_error=pr_index_error,
            )
        ]
        if leftover and leftover != paths and ref == DIRT_SHELF_REF:
            rewrite_shelf(root, ref, leftover)
            continue
        if leftover:
            continue
        pruned.append({"ref": ref, "tip": tip})
        _git(root, "update-ref", "-d", ref)
    return pruned


def rewrite_shelf(root: Path, ref: str, rels: list[str]) -> None:
    if not rels:
        return
    with tempfile.TemporaryDirectory(prefix="l9-dirt-rewrite-") as tmp:
        index = Path(tmp) / "index"
        env = {"GIT_INDEX_FILE": str(index)}
        for rel in rels:
            blob = _git(root, "rev-parse", f"{ref}:{rel}").stdout.strip()
            if not blob:
                continue
            _git(root, "update-index", "--add", "--cacheinfo", f"100644,{blob},{rel}", env=env)
        tree = _git(root, "write-tree", env=env).stdout.strip()
        if not tree:
            return
        parent = ref_sha(root, ref)
        commit = _git(
            root,
            "commit-tree",
            tree,
            "-p",
            parent,
            "-m",
            "park: session-end dirt rewrite (absorbed paths dropped)",
        ).stdout.strip()
        if commit:
            _git(root, "update-ref", ref, commit)


def novel_parked_paths(root: Path) -> list[str]:
    if not ref_exists(root, DIRT_SHELF_REF):
        return []
    return tree_paths(root, DIRT_SHELF_REF)


def build_status(
    rows: list[dict[str, str]],
    *,
    parked: list[str],
    absorbed: list[dict[str, str]],
    skipped: str,
    leftover_novel: list[str],
) -> dict[str, Any]:
    return {
        "dirty_files": list(leftover_novel),
        "already_landed": [r["path"] for r in rows if r["class"] in LANDED_CLASSES],
        "left_in_tree": [r["path"] for r in rows if r["class"] in LEAVE_CLASSES],
        "novel_parked": parked,
        "absorbed_pruned": absorbed,
        "skipped": skipped,
        "dirty_unique": len(leftover_novel),
    }


def apply_close(
    root: Path,
    rows: list[dict[str, str]],
    *,
    baseline: str,
    blob_index: dict[str, set[str]],
    pr_index_error: str,
    skip: str,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema": "l9.session_end_dirt_close/v1",
        "workspace": str(root),
        "created_at": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        "baseline": baseline,
        "applied": False,
        "skip": skip,
        "actions": [],
        "shelf_ref": DIRT_SHELF_REF,
        "shelf_commit": "",
    }
    leftover_novel = [r["path"] for r in rows if r["class"] == NOVEL_CLASS]
    parked: list[str] = novel_parked_paths(root)
    absorbed: list[dict[str, str]] = []
    if skip:
        receipt["status"] = build_status(
            rows, parked=parked, absorbed=absorbed, skipped=skip, leftover_novel=leftover_novel
        )
        return receipt

    for row in rows:
        if row["class"] not in LANDED_CLASSES:
            continue
        row["action"] = restore_or_remove(root, row["path"])
        receipt["actions"].append({"path": row["path"], "class": row["class"], "action": row["action"]})

    overflow = leftover_novel[MAX_NOVEL_PATHS:]
    novel = leftover_novel[:MAX_NOVEL_PATHS]
    cleaned: list[str] = []
    if novel:
        _ref, commit = park_novel(root, novel)
        receipt["shelf_commit"] = commit
        if commit.startswith("add-failed") or commit.endswith("-failed"):
            receipt["errors"] = [commit]
        else:
            for rel in novel:
                if path_on_rev(root, DIRT_SHELF_REF, rel):
                    restore_or_remove(root, rel)
                    cleaned.append(rel)
                    receipt["actions"].append(
                        {"path": rel, "class": NOVEL_CLASS, "action": "parked+cleaned"}
                    )
    leftover_novel = overflow + [p for p in novel if p not in cleaned]
    absorbed = prune_absorbed_refs(
        root, baseline=baseline, blob_index=blob_index, pr_index_error=pr_index_error
    )
    parked = novel_parked_paths(root)
    receipt["applied"] = True
    receipt["status"] = build_status(
        rows, parked=parked, absorbed=absorbed, skipped="", leftover_novel=leftover_novel
    )
    return receipt


def write_receipt(root: Path, payload: dict[str, Any]) -> Path:
    dest = root / ".l9" / "hygiene"
    dest.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = dest / f"dirt-close-{stamp}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run(
    workspace: Path,
    *,
    apply: bool,
    payload: dict[str, Any],
    baseline: str,
    blob_index_path: str,
    pr_heads: list[str],
) -> dict[str, Any]:
    git = repo_hygiene.Git(workspace)
    top = git.out("rev-parse", "--show-toplevel")
    if not top:
        raise SystemExit(f"not a git work tree: {workspace}")
    git.root = Path(top)
    root = git.root
    blob_index, pr_err = load_open_pr_index(
        git, baseline=baseline, blob_index_path=blob_index_path, pr_heads=pr_heads
    )
    rows = classify_workspace(root, baseline=baseline, blob_index=blob_index, pr_index_error=pr_err)
    closable = [r["path"] for r in rows if r["class"] in LANDED_CLASSES or r["class"] == NOVEL_CLASS]
    skip = gate_skip_reason(payload, root, closable) if apply else ""
    if apply:
        receipt = apply_close(
            root,
            rows,
            baseline=baseline,
            blob_index=blob_index,
            pr_index_error=pr_err,
            skip=skip,
        )
        receipt["pr_index_error"] = pr_err
        receipt["hygiene_receipt"] = str(write_receipt(root, receipt))
        return receipt
    parked = novel_parked_paths(root)
    status = build_status(
        rows,
        parked=parked,
        absorbed=[],
        skipped="",
        leftover_novel=[r["path"] for r in rows if r["class"] == NOVEL_CLASS],
    )
    status["pr_index_error"] = pr_err
    status["workspace"] = str(root)
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".", help="session workspace (git root)")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--status", action="store_true", help="report only (default)")
    parser.add_argument("--baseline", default=DEFAULT_BASELINE)
    parser.add_argument("--payload", default="", help="sessionEnd JSON payload")
    parser.add_argument("--payload-file", default="", help="path to sessionEnd JSON")
    parser.add_argument("--blob-index", default="", help="test fixture: path -> [sha256]")
    parser.add_argument("--pr-head", action="append", default=[], help="local open-PR head (tests)")
    args = parser.parse_args(argv)

    raw = args.payload
    if args.payload_file:
        raw = Path(args.payload_file).read_text(encoding="utf-8")
    elif not raw and not sys.stdin.isatty():
        peek = sys.stdin.read()
        if peek.strip().startswith("{"):
            raw = peek
    payload = parse_payload(raw)

    workspace = Path(args.workspace).expanduser().resolve()
    try:
        result = run(
            workspace,
            apply=args.apply,
            payload=payload,
            baseline=args.baseline,
            blob_index_path=args.blob_index,
            pr_heads=list(args.pr_head),
        )
    except SystemExit:
        raise
    except Exception as exc:  # fail-open for the hook
        print(f"WARN: dirt-close failed: {exc}", file=sys.stderr)
        print(json.dumps({"dirty_files": [], "skipped": f"error:{exc}", "dirty_unique": -1}))
        return 0

    print(json.dumps(result, indent=2, sort_keys=True))
    status = result.get("status") or result
    print(
        "dirt-close dirty_unique=%s already_landed=%s novel_parked=%s absorbed_pruned=%s"
        % (
            status.get("dirty_unique", len(status.get("dirty_files") or [])),
            len(status.get("already_landed") or []),
            len(status.get("novel_parked") or []),
            len(status.get("absorbed_pruned") or []),
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
