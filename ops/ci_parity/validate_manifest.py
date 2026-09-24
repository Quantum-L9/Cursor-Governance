#!/usr/bin/env python3
"""Fail when tools.yaml is malformed or its CI evidence has moved.

Each `ci_ref` names a file and a string that pins what CI runs (a reusable
workflow commit, a requirements pin). If that string is gone, CI changed the
version it runs and the local pin no longer mirrors it: re-pin tools.yaml
(version, url, sha256, observed) in the same change. Exit 1 on any finding.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import manifest  # noqa: E402

REPO_ROOT = HERE.parents[1]


def check(repo_root: Path = REPO_ROOT, path: Path = manifest.MANIFEST) -> list[str]:
    try:
        loaded = manifest.load(path)
    except (manifest.ManifestError, OSError) as exc:
        return [f"manifest: {exc}"]
    problems: list[str] = []
    for tool in loaded.tools.values():
        ref = tool.ci_ref
        if not ref:
            continue
        target = repo_root / ref.get("path", "")
        try:
            text = target.read_text(encoding="utf-8")
        except OSError:
            problems.append(f"{tool.name}: ci_ref path {ref.get('path')!r} is unreadable")
            continue
        if ref.get("contains", "") not in text:
            problems.append(
                f"{tool.name}: {ref.get('path')} no longer contains {ref.get('contains')!r} — "
                "CI changed the version it runs; re-pin tools.yaml"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    problems = check(args.repo_root)
    for problem in problems:
        print(f"FAIL: {problem}")
    if problems:
        return 1
    print("PASS: ci-parity manifest valid and CI pins unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
