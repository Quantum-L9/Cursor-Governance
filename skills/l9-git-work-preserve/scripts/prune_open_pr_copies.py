#!/usr/bin/env python3
"""Unlink untracked shipped copies of open-PR blobs across sibling worktrees.

Report-only by default. ``--apply`` unlinks an **untracked** file whose sha256
equals an open-PR blob at the same path (casefold for ``docs/plans/built`` vs
``BUILT``). A tracked path at ``HEAD:path`` is never unlinked.

`` M`` overlays whose working-tree bytes match an open-PR blob are restored to
that leftover worktree's HEAD (duplicate dirt dropped; unique committed bytes
kept).

Receipts land in ``.l9/hygiene/``, not ``WIP/_receipts/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = "l9.git_work_preserve.receipt/v1"
SKIP_PREFIXES = ("WIP/Legal Defense/",)
SSOT = Path.home() / ".cursor-governance"


def _ops_scripts() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "ops" / "scripts" / "repo_hygiene.py"
        if candidate.is_file():
            return candidate.parent
    raise SystemExit("cannot locate ops/scripts/repo_hygiene.py")


sys.path.insert(0, str(_ops_scripts()))
import repo_hygiene  # noqa: E402


def _run_bytes(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
    )


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_blob(repo: Path, rev: str, rel: str) -> str | None:
    proc = _run_bytes(repo, "cat-file", "blob", f"{rev}:{rel}")
    if proc.returncode != 0:
        return None
    return hashlib.sha256(proc.stdout).hexdigest()


def path_key(rel: str) -> str:
    return rel.replace("\\", "/").casefold()


def skip_path(rel: str) -> bool:
    norm = rel.replace("\\", "/")
    return any(norm.startswith(prefix) for prefix in SKIP_PREFIXES)


def head_has_path(repo: Path, rel: str) -> bool:
    return _run_bytes(repo, "cat-file", "-e", f"HEAD:{rel}").returncode == 0


def porcelain_path(line: str) -> tuple[str, str]:
    status = line[:2] if len(line) >= 2 else ""
    raw = line[3:] if len(line) >= 3 else line
    raw = raw.strip().strip('"')
    if " -> " in raw:
        raw = raw.split(" -> ", 1)[1]
    return status, raw.replace("\\", "/")


def load_blob_index(path: Path) -> dict[str, set[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    index: dict[str, set[str]] = {}
    for rel, hashes in data.items():
        key = path_key(str(rel))
        index.setdefault(key, set()).update(str(h) for h in hashes)
    return index


def build_blob_index(git: repo_hygiene.Git, heads: list[str], baseline: str) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for head in heads:
        if not git.ok("rev-parse", "--verify", head):
            alt = f"origin/{head.removeprefix('origin/')}"
            if not git.ok("rev-parse", "--verify", alt):
                continue
            head = alt
        changed = git.out("diff", "--name-only", "--diff-filter=ACMR", f"{baseline}...{head}")
        for rel in changed.splitlines():
            if not rel or skip_path(rel):
                continue
            digest = sha256_blob(git.root, head, rel)
            if not digest:
                continue
            index.setdefault(path_key(rel), set()).add(digest)
    return index


def discover_worktrees(git: repo_hygiene.Git) -> list[Path]:
    found: list[Path] = []
    for line in git.out("worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            found.append(Path(line[len("worktree ") :]))
    return found


def classify_worktree(
    wt: Path,
    blob_index: dict[str, set[str]],
) -> list[dict]:
    rows: list[dict] = []
    if not wt.exists():
        return rows
    if SSOT.exists() and wt.resolve() == SSOT.resolve():
        return rows
    porcelain = subprocess.run(  # noqa: S603
        ["git", "-C", str(wt), "status", "--porcelain=v1", "--untracked-files=all"],
        capture_output=True,
        text=True,
        check=False,
    )
    for line in porcelain.stdout.splitlines():
        if not line:
            continue
        status, rel = porcelain_path(line)
        if not rel or skip_path(rel):
            continue
        hashes = blob_index.get(path_key(rel))
        if not hashes:
            continue
        full = wt / rel
        digest = sha256_file(full)
        if digest is None or digest not in hashes:
            continue
        tracked = head_has_path(wt, rel)
        if tracked:
            if status.strip() and "?" not in status:
                rows.append(
                    {
                        "worktree": str(wt),
                        "path": rel,
                        "status": status,
                        "sha256": digest,
                        "action": "restore-head",
                        "detail": "modified overlay matches open-PR blob; restore leftover HEAD",
                    }
                )
            else:
                rows.append(
                    {
                        "worktree": str(wt),
                        "path": rel,
                        "status": status,
                        "sha256": digest,
                        "action": "keep",
                        "detail": "HEAD:path exists; never unlink tracked",
                    }
                )
            continue
        rows.append(
            {
                "worktree": str(wt),
                "path": rel,
                "status": status,
                "sha256": digest,
                "action": "unlink",
                "detail": "untracked sha256 matches open-PR blob",
            }
        )
    return rows


def apply_rows(rows: list[dict]) -> None:
    for row in rows:
        wt = Path(row["worktree"])
        rel = row["path"]
        full = wt / rel
        if row["action"] == "unlink":
            if head_has_path(wt, rel):
                row["action"] = "keep"
                row["detail"] = "HEAD:path appeared; refused unlink"
                continue
            try:
                full.unlink()
                row["action"] = "unlinked"
            except OSError as exc:
                row["action"] = "unlink-failed"
                row["detail"] = str(exc)
        elif row["action"] == "restore-head":
            proc = subprocess.run(  # noqa: S603
                ["git", "-C", str(wt), "restore", "--worktree", "--source=HEAD", "--", rel],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                row["action"] = "restore-failed"
                row["detail"] = (proc.stderr or proc.stdout).strip()[:200]
            else:
                row["action"] = "restored"


def _write_hygiene_receipt(repo: Path, payload: dict) -> Path:
    dest = repo / ".l9" / "hygiene"
    dest.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = dest / f"prune-open-pr-copies-{stamp}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _open_pr_heads(git: repo_hygiene.Git, extra: list[str]) -> list[str]:
    heads: list[str] = []
    seen: set[str] = set()
    for name in extra:
        if name and name not in seen:
            seen.add(name)
            heads.append(name)
    slug = repo_hygiene.origin_slug(git.out("remote", "get-url", "origin"))
    prs, err = repo_hygiene.pr_index(slug) if slug else ({}, "empty origin slug")
    if err:
        return heads
    for name, rec in prs.items():
        if str(rec.get("state") or "") == "OPEN" and name not in seen:
            seen.add(name)
            heads.append(name)
    return heads


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="anchor git work tree")
    parser.add_argument("--baseline", default="origin/main")
    parser.add_argument("--json", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--blob-index",
        help="JSON map of path -> [sha256] (tests; skips GitHub/PR fetch)",
    )
    parser.add_argument(
        "--pr-head",
        action="append",
        default=[],
        help="local ref treated as an open PR head (repeatable; tests)",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="do not fetch (fixtures)",
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo).expanduser().resolve()
    git = repo_hygiene.Git(repo)
    top = git.out("rev-parse", "--show-toplevel")
    if not top:
        print(f"not a git work tree: {repo}", file=sys.stderr)
        return 2
    git.root = Path(top)

    has_remote = git.ok("remote", "get-url", "origin")
    if args.apply and has_remote and not args.skip_fetch and not args.blob_index:
        if not git.ok("fetch", "--prune", "origin"):
            print("fetch --prune origin failed; refusing --apply", file=sys.stderr)
            return 2

    if args.blob_index:
        blob_index = load_blob_index(Path(args.blob_index).expanduser())
        heads = list(args.pr_head)
    else:
        heads = _open_pr_heads(git, args.pr_head)
        if not heads and not args.pr_head:
            print("no open PR heads to index; nothing to prune", file=sys.stderr)
        blob_index = build_blob_index(git, heads, args.baseline)

    rows: list[dict] = []
    for wt in discover_worktrees(git):
        rows.extend(classify_worktree(wt, blob_index))

    applied = False
    if args.apply:
        apply_rows(rows)
        applied = True

    payload = {
        "schema": SCHEMA,
        "mode": "prune-open-pr-copies",
        "repo": str(git.root),
        "created_at": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        "baseline_ref": args.baseline,
        "applied": applied,
        "pr_heads": heads,
        "blob_paths": len(blob_index),
        "candidates": rows,
        "counts": {
            "unlink": sum(1 for r in rows if r.get("action") in {"unlink", "unlinked"}),
            "restore-head": sum(1 for r in rows if r.get("action") in {"restore-head", "restored"}),
            "keep": sum(1 for r in rows if r.get("action") == "keep"),
            "unlinked": sum(1 for r in rows if r.get("action") == "unlinked"),
            "restored": sum(1 for r in rows if r.get("action") == "restored"),
        },
    }
    if applied:
        payload["hygiene_receipt"] = str(_write_hygiene_receipt(git.root, payload))
    print(json.dumps(payload, indent=2, sort_keys=True))
    failed = any(r.get("action", "").endswith("-failed") for r in rows)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
