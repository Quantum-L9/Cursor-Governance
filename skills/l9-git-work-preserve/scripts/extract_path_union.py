#!/usr/bin/env python3
"""Path-union extract of leftover committed paths vs a fetched baseline.

Report-only by default. Never cherry-picks. Never deletes the source ref.
Copy a path iff it is in the allowlist copy set (or the derived copy set)
and ``git cat-file -e <baseline>:<path>`` fails. Path-absent, not blob-absent.
An empty copy set is a valid stop.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

SCHEMA = "l9.git_work_preserve.extract_path_union/v1"


class ExtractError(Exception):
    """Fail-closed extract/apply error. ``code`` is the process exit status."""

    def __init__(self, message: str, code: int = 2) -> None:
        super().__init__(message)
        self.code = code


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def path_on_baseline(repo: Path, baseline: str, rel: str) -> bool:
    return _run(repo, "cat-file", "-e", f"{baseline}:{rel}").returncode == 0


def name_status(repo: Path, baseline: str, ref: str) -> list[tuple[str, str]]:
    """Return (status_letter, path) for baseline...ref. Renames use the new path."""
    proc = _run(repo, "diff", "--name-status", f"{baseline}...{ref}")
    rows: list[tuple[str, str]] = []
    if proc.returncode != 0:
        raise ExtractError(
            (proc.stderr or "").strip() or f"git diff failed ({baseline}...{ref})",
        )
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0][:1]
        if status == "R" and len(parts) >= 3:
            rows.append((status, parts[2].replace("\\", "/")))
        elif len(parts) >= 2:
            rows.append((status, parts[1].replace("\\", "/")))
    return rows


def load_allowlist(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("allowlist must be a JSON object")
    copy_rows = raw.get("copy") or []
    skip_rows = raw.get("skip") or []
    if not isinstance(copy_rows, list) or not isinstance(skip_rows, list):
        raise ValueError("allowlist copy/skip must be lists")
    return {
        "copy": [str(item.get("path") if isinstance(item, dict) else item) for item in copy_rows],
        "skip": [str(item.get("path") if isinstance(item, dict) else item) for item in skip_rows],
        "copy_reasons": {
            str(item["path"]): str(item.get("reason") or "")
            for item in copy_rows
            if isinstance(item, dict) and item.get("path")
        },
        "skip_reasons": {
            str(item["path"]): str(item.get("reason") or "")
            for item in skip_rows
            if isinstance(item, dict) and item.get("path")
        },
    }


def classify_rows(
    repo: Path,
    baseline: str,
    rows: list[tuple[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    copy: list[dict[str, str]] = []
    skip: list[dict[str, str]] = []
    seen: set[str] = set()
    for status, rel in rows:
        if not rel or rel in seen:
            continue
        seen.add(rel)
        on_base = path_on_baseline(repo, baseline, rel)
        if status == "D" or (status != "A" and status != "R" and on_base):
            reason = "baseline_delete" if status == "D" else "already_on_baseline"
            skip.append({"path": rel, "reason": reason, "status": status})
            continue
        if on_base:
            skip.append({"path": rel, "reason": "already_on_baseline", "status": status})
            continue
        copy.append({"path": rel, "reason": "path_absent", "status": status})
    return copy, skip


def apply_allowlist(
    derived_copy: list[dict[str, str]],
    derived_skip: list[dict[str, str]],
    allowlist: dict[str, Any] | None,
) -> tuple[list[dict[str, str]], list[dict[str, str]], bool]:
    if allowlist is None:
        return derived_copy, derived_skip, False
    copy_set = [p for p in allowlist["copy"] if p]
    skip_set = set(allowlist["skip"])
    if copy_set == [] and "copy" in allowlist:
        # Explicit empty copy set is a valid stop.
        stopped = list(derived_copy)
        skip = list(derived_skip)
        for row in stopped:
            skip.append(
                {
                    "path": row["path"],
                    "reason": allowlist["skip_reasons"].get(row["path"]) or "allowlist_empty",
                    "status": row.get("status", ""),
                }
            )
        return [], skip, True

    allowed = set(copy_set)
    copy: list[dict[str, str]] = []
    skip: list[dict[str, str]] = list(derived_skip)
    derived_by_path = {row["path"]: row for row in derived_copy}
    for rel in copy_set:
        row = derived_by_path.get(rel)
        if row is None:
            skip.append({"path": rel, "reason": "not_path_absent_on_ref", "status": ""})
            continue
        if rel in skip_set:
            skip.append(
                {
                    "path": rel,
                    "reason": allowlist["skip_reasons"].get(rel) or "allowlist_skip",
                    "status": row.get("status", ""),
                }
            )
            continue
        reason = allowlist["copy_reasons"].get(rel) or row["reason"]
        copy.append({"path": rel, "reason": reason, "status": row.get("status", "")})
    for row in derived_copy:
        if row["path"] not in allowed:
            skip.append(
                {
                    "path": row["path"],
                    "reason": "not_in_allowlist_copy",
                    "status": row.get("status", ""),
                }
            )
    return copy, skip, False


def show_blob(repo: Path, ref: str, rel: str) -> bytes | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), "show", f"{ref}:{rel}"],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def _tree_mode(repo: Path, ref: str, rel: str) -> str:
    proc = _run(repo, "ls-tree", "-z", ref, "--", rel)
    if proc.returncode != 0 or not (proc.stdout or "").strip("\0"):
        return "100644"
    meta = proc.stdout.split("\0", 1)[0].split("\t", 1)[0]
    parts = meta.split()
    return parts[0] if parts else "100644"


def apply_copy(repo: Path, ref: str, dest: Path, copy: list[dict[str, str]]) -> list[str]:
    written: list[str] = []
    dest = dest.resolve()
    collisions = [row["path"] for row in copy if row.get("path") and (dest / row["path"]).exists()]
    if collisions:
        raise ExtractError(
            "refuse apply: destination already has " + ", ".join(sorted(collisions)),
        )
    for row in copy:
        rel = row["path"]
        blob = show_blob(repo, ref, rel)
        if blob is None:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = _tree_mode(repo, ref, rel)
        if mode == "120000":
            target.symlink_to(os.fsdecode(blob).rstrip("\n"))
        else:
            target.write_bytes(blob)
            if mode == "100755":
                target.chmod(target.stat().st_mode | 0o111)
        written.append(rel)
    return written


def extract_plan(
    repo: Path,
    *,
    ref: str,
    baseline: str,
    allowlist: dict[str, Any] | None,
) -> dict[str, Any]:
    rows = name_status(repo, baseline, ref)
    derived_copy, derived_skip = classify_rows(repo, baseline, rows)
    copy, skip, stop = apply_allowlist(derived_copy, derived_skip, allowlist)
    mixed = any(
        item["reason"] in {"baseline_delete", "already_on_baseline"} for item in derived_skip
    )
    return {
        "schema": SCHEMA,
        "mode": "extract",
        "repo": str(repo.resolve()),
        "ref": ref,
        "baseline": baseline,
        "copy": copy,
        "skip": skip,
        "stop": stop,
        "mixed_range": mixed,
        "cherry_pick": False,
        "counts": {
            "copy": len(copy),
            "skip": len(skip),
            "name_status": len(rows),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Git directory holding the leftover ref")
    parser.add_argument("--ref", required=True, help="Leftover ref (keep_push / preserve tip)")
    parser.add_argument("--baseline", default="origin/main")
    parser.add_argument("--allowlist", default=None, help="JSON {copy, skip} with path/reason rows")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write copy-set blobs into --dest (default: report-only)",
    )
    parser.add_argument(
        "--dest",
        default=None,
        help="Destination worktree for --apply (required when applying)",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON (default)")
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    allowlist = load_allowlist(Path(args.allowlist).expanduser()) if args.allowlist else None
    try:
        data = extract_plan(repo, ref=args.ref, baseline=args.baseline, allowlist=allowlist)
        if args.apply:
            if not args.dest:
                print(json.dumps({"status": "FAIL", "error": "--dest is required with --apply"}))
                return 2
            dest = Path(args.dest).expanduser().resolve()
            if dest == repo:
                print(
                    json.dumps(
                        {
                            "status": "FAIL",
                            "error": (
                                "refuse apply onto --repo; use a dedicated destination worktree"
                            ),
                        }
                    )
                )
                return 2
            data["written"] = apply_copy(repo, args.ref, dest, data["copy"])
            data["dest"] = str(dest)
    except ExtractError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return exc.code
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
