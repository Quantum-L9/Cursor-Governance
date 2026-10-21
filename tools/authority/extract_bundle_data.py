#!/usr/bin/env python3
"""Extract a committed directory from an untrusted commit as plain data, failing closed.

The trusted architecture-intelligence replay reads a pull request's bundle without checking
out or executing anything from it. ``git archive | tar -x`` would materialize whatever the
tree holds: a symlink pointing outside the extraction root, a gitlink, an executable file. This
extractor inspects every tree entry under the requested path first and refuses the whole
extraction unless each one is a regular, non-executable blob (mode 100644) at a safe relative
path. Only then does it write the blob bytes, owner-only (0600), into a fresh destination.

Exit codes: 0 extracted, 1 refused, 2 usage error. The report is JSON on stdout.
Standard library only, so it runs before any dependency is installed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

_SHA = re.compile(r"^[0-9a-f]{40}$")
REGULAR_FILE = "100644"


class Refused(Exception):
    def __init__(self, reason: str, **detail: object) -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


def _git(git_dir: Path, *args: str) -> bytes:
    completed = subprocess.run(["git", "-C", str(git_dir), *args], capture_output=True, check=False)
    if completed.returncode != 0:
        raise Refused("GIT_OBJECT_UNRESOLVED", args=list(args))
    return completed.stdout


def _safe_relative(path: str) -> PurePosixPath:
    pure = PurePosixPath(path)
    if (
        not path
        or pure.is_absolute()
        or any(part in ("", ".", "..") for part in path.split("/"))
        or "\\" in path
        or "\x00" in path
    ):
        raise Refused("UNSAFE_PATH", path=path)
    return pure


def entries(git_dir: Path, commit: str, root: str) -> list[tuple[str, str, str, str]]:
    """Every tree entry under *root* as (mode, type, oid, path); refuses anything irregular."""
    if not _SHA.match(commit):
        raise Refused("COMMIT_MALFORMED", commit=commit)
    if _git(git_dir, "cat-file", "-t", commit).strip() != b"commit":
        raise Refused("NOT_A_COMMIT", commit=commit)
    root_path = _safe_relative(root)
    # The root itself must be a tree reached through trees only: a symlinked or gitlinked
    # ancestor would make ls-tree list nothing below it, which is refused as absent.
    listed = _git(git_dir, "ls-tree", "-r", "-t", "-z", "--full-tree", commit, "--", str(root_path))
    found: list[tuple[str, str, str, str]] = []
    irregular: list[dict[str, str]] = []
    for record in listed.split(b"\x00"):
        if not record:
            continue
        meta, _, raw_path = record.partition(b"\t")
        mode, kind, oid = meta.decode("ascii").split(" ")
        path = raw_path.decode("utf-8")
        if kind == "tree":
            continue
        _safe_relative(path)
        if not (path == str(root_path) or path.startswith(f"{root_path}/")):
            raise Refused("ENTRY_OUTSIDE_ROOT", path=path)
        if kind != "blob" or mode != REGULAR_FILE:
            irregular.append({"path": path, "mode": mode, "type": kind})
            continue
        found.append((mode, kind, oid, path))
    if irregular:
        raise Refused("NON_REGULAR_ENTRY", entries=irregular)
    if not found:
        raise Refused("BUNDLE_ABSENT", root=str(root_path))
    if any(path == str(root_path) for _, _, _, path in found):
        raise Refused("ROOT_IS_NOT_A_DIRECTORY", root=str(root_path))
    return found


def extract(git_dir: Path, commit: str, root: str, dest: Path) -> int:
    found = entries(git_dir, commit, root)
    if dest.exists() or dest.is_symlink():
        raise Refused("DESTINATION_EXISTS", dest=str(dest))
    dest.mkdir(parents=True)
    base = dest.resolve()
    for _, _, oid, path in found:
        relative = PurePosixPath(path).relative_to(root)
        target = base.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.parent.resolve().is_relative_to(base):
            raise Refused("UNSAFE_PATH", path=path)
        data = _git(git_dir, "cat-file", "blob", oid)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.chmod(target, 0o600)
    return len(found)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract a committed directory from an untrusted commit as plain data."
    )
    parser.add_argument("--git-dir", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--dest", type=Path, required=True)
    args = parser.parse_args(argv)
    report: dict[str, object] = {"commit": args.commit, "path": args.path}
    try:
        report.update(
            status="EXTRACTED", files=extract(args.git_dir, args.commit, args.path, args.dest)
        )
        code = 0
    except Refused as refused:
        report.update(status="REFUSED", reason=refused.reason, detail=refused.detail)
        code = 1
    print(json.dumps(report, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
