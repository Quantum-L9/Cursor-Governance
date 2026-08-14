#!/usr/bin/env python3
"""Export the complete local PR diff, including untracked pack files, without remote access."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

BASE_SHA = "0fbd477e507d33ee52f2a87c2d9eb77c15b6a492"


def _run(repo: Path, argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(argv, cwd=repo, capture_output=True, check=check)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    if head != BASE_SHA:
        raise SystemExit(f"base SHA mismatch: expected {BASE_SHA}, found {head}")

    tracked = _run(
        repo,
        ["git", "diff", "--binary", "--no-ext-diff", BASE_SHA, "--"],
    ).stdout
    untracked_raw = _run(
        repo,
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
    ).stdout
    untracked = [item.decode("utf-8") for item in untracked_raw.split(b"\0") if item]

    parts = [tracked]
    for rel in sorted(untracked):
        result = _run(
            repo,
            ["git", "diff", "--binary", "--no-index", "--", "/dev/null", rel],
            check=False,
        )
        if result.returncode not in {0, 1}:
            raise SystemExit(
                f"failed to render untracked path {rel}: {result.stderr.decode('utf-8', 'replace')}"
            )
        parts.append(result.stdout)

    target = args.output.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"".join(parts))
    print(target)
    print(f"untracked_files_included={len(untracked)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
