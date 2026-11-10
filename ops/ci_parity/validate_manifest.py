#!/usr/bin/env python3
"""Fail when tools.yaml is malformed or its CI evidence has moved.

Each `ci_ref` names a file and a string that pins what CI runs (a reusable
workflow commit, a requirements pin). If that string is gone, CI changed the
version it runs and the local pin no longer mirrors it: re-pin tools.yaml
(version, url, sha256, observed) in the same change. Exit 1 on any finding.

A ci_ref with `repo:` points into l9-ci-core, which pins what Analyze (central
Core) runs. The offline check skips it; `--remote` reads it at `ref` through
docker_sandbox's Core reader.

A tool with `track: ci_ref` follows that file instead of its hand pin, so a
moved pin is not a finding: it passes while `ci_ref.extract` still names exactly
one revision there (an INFO line says which), and fails when it no longer does,
because then install.py can only fall back to the hand pin.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import manifest  # noqa: E402

REPO_ROOT = HERE.parents[1]


def _remote_text(ref: dict[str, str]) -> str:
    """The ci_ref file at the named ref of l9-ci-core, over REST or git.

    Reuses docker_sandbox's Core reader, the one reader of Core's files.
    """
    scripts = HERE.parent / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import docker_sandbox  # noqa: PLC0415

    if ref.get("repo") != docker_sandbox.CORE_REPO:
        raise OSError(f"only {docker_sandbox.CORE_REPO} is readable, not {ref.get('repo')!r}")
    try:
        sha = docker_sandbox.core_commit(ref.get("ref") or "main")
        return docker_sandbox.core_file(sha, ref.get("path", ""))
    except docker_sandbox.SandboxError as exc:
        raise OSError(str(exc)) from exc


def check(
    repo_root: Path = REPO_ROOT,
    path: Path = manifest.MANIFEST,
    *,
    remote: bool = False,
    notes: list[str] | None = None,
) -> list[str]:
    try:
        loaded = manifest.load(path)
    except (manifest.ManifestError, OSError) as exc:
        return [f"manifest: {exc}"]
    problems: list[str] = []
    for tool in loaded.tools.values():
        ref = tool.ci_ref
        if not ref:
            continue
        where = ref.get("path", "")
        try:
            if ref.get("repo"):
                if not remote:
                    continue  # another repository: checked with --remote only
                where = f"{ref['repo']}@{ref.get('ref') or 'main'}:{where}"
                text = _remote_text(ref)
            else:
                text = (repo_root / where).read_text(encoding="utf-8")
        except OSError as exc:
            problems.append(f"{tool.name}: ci_ref {where!r} is unreadable ({exc})")
            continue
        if tool.track:
            problems.extend(_check_tracked(tool, where, text, notes))
            continue
        if ref.get("contains", "") not in text:
            problems.append(
                f"{tool.name}: {where} no longer contains {ref.get('contains')!r} — "
                "CI changed the version it runs; re-pin tools.yaml"
            )
    problems.extend(_blocking_identity(loaded))
    return problems


def _check_tracked(
    tool: manifest.Tool, where: str, text: str, notes: list[str] | None
) -> list[str]:
    version = manifest.tracked_version(tool, text)
    if version is None:
        return [
            f"{tool.name}: {where} no longer names exactly one revision matching "
            "ci_ref.extract — CI changed how it pins the tool; fix extract in tools.yaml"
        ]
    if notes is not None and version != tool.fallback_version:
        notes.append(
            f"{tool.name}: tracks {where} at {version} (hand pin {tool.fallback_version}; "
            "install.py installs the tracked revision)"
        )
    return []


_RANGE = re.compile(r">=|<=|<|>")


def _blocking_identity(loaded: manifest.Manifest) -> list[str]:
    """A blocking lane needs an exact CI pin. A version range is not an identity."""
    problems: list[str] = []
    seen: set[str] = set()
    for lane in loaded.lanes.values():
        if not lane.block or lane.tool in seen:
            continue
        seen.add(lane.tool)
        ref = loaded.tools[lane.tool].ci_ref
        contains = ref.get("contains", "")
        if not ref or not contains:
            problems.append(
                f"{lane.name}: blocking lane has no exact ci_ref — "
                "keep it advisory or bind an exact CI pin"
            )
            continue
        if _RANGE.search(contains):
            problems.append(
                f"{lane.name}: ci_ref {contains!r} is a version range, not an exact pin"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--remote",
        action="store_true",
        help="also read ci_refs that name another repository (network)",
    )
    args = parser.parse_args(argv)
    notes: list[str] = []
    problems = check(args.repo_root, remote=args.remote, notes=notes)
    for note in notes:
        print(f"INFO: {note}")
    for problem in problems:
        print(f"FAIL: {problem}")
    if problems:
        return 1
    print("PASS: ci-parity manifest valid and CI pins unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
