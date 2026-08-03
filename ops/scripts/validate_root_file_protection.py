#!/usr/bin/env python3
"""Fail-closed append-only gate for repository-root files.

Enforces ops/config/root-file-protection.json against a pull request: a protected
root file may be freely ADDED to, but any deletion or in-place overwrite of existing
content fails the gate unless a matching justification marker is recorded in the PR's
commit messages. Machine-generated `regenerable` files are exempt from the additive
check (they are rewritten wholesale by tooling) but remain CODEOWNERS-reviewed.

Justification marker (in any commit message in the PR range):

    ALLOW-ROOT-DELETION: <root-relative-path> — <reason with proof of necessity>

The marker authorizes the CI gate only; human CODEOWNERS approval is still required
(CODEOWNERS + ORG_INVARIANTS.yaml protected_paths). This script is read-only and
never edits repository files.

Usage:
    validate_root_file_protection.py [--base <ref>] [--head <ref>] [--repo <path>]

Exit 0 = compliant. Nonzero = at least one protected root file was rewritten/deleted
without a justification marker (or the invocation was malformed — fail closed).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_BASE = os.environ.get("ROOT_PROTECT_BASE", "origin/main")
CONFIG_RELPATH = "ops/config/root-file-protection.json"

# ALLOW-ROOT-DELETION: <path> — <reason>   (em-dash or " - " separator; reason required)
_MARKER_RE = re.compile(
    r"^\s*ALLOW-ROOT-DELETION:\s*(?P<path>.+?)\s*(?:—|-)\s+(?P<reason>\S.*)$",
)


class ProtectionError(Exception):
    """Malformed invocation or unreadable inputs. Always fail closed."""


def run_git(repo: Path, args: list[str]) -> str:
    result = subprocess.run(  # noqa: S603 - fixed git argv, no shell
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = f"git {' '.join(args)} failed: {result.stderr.strip()}"
        raise ProtectionError(msg)
    return result.stdout


def load_config(repo: Path) -> dict:
    path = repo / CONFIG_RELPATH
    if not path.is_file():
        msg = f"protection config not found: {CONFIG_RELPATH}"
        raise ProtectionError(msg)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"protection config is not valid JSON: {exc}"
        raise ProtectionError(msg) from exc
    files = data.get("protected_files")
    if not isinstance(files, list) or not files:
        msg = "protection config has no protected_files"
        raise ProtectionError(msg)
    for entry in files:
        if not isinstance(entry, dict) or "path" not in entry or "rule" not in entry:
            msg = "each protected_files entry needs a path and a rule"
            raise ProtectionError(msg)
        if entry["rule"] not in ("additive_only", "regenerable"):
            msg = f"unknown rule for {entry['path']!r}: {entry['rule']}"
            raise ProtectionError(msg)
    return data


def merge_base(repo: Path, base: str, head: str) -> str:
    try:
        return run_git(repo, ["merge-base", base, head]).strip()
    except ProtectionError:
        # No common ancestor reachable (e.g. shallow clone): compare against base tip.
        return base


def numstat(repo: Path, base: str, head: str, path: str) -> tuple[int, int] | str | None:
    """Return (added, deleted), 'binary', or None if the file is unchanged."""
    out = run_git(repo, ["diff", "--numstat", f"{base}..{head}", "--", path]).strip()
    if not out:
        return None
    first = out.splitlines()[0].split("\t")
    if len(first) < 2:
        return None
    added, deleted = first[0], first[1]
    if added == "-" or deleted == "-":
        return "binary"
    return int(added), int(deleted)


def collect_justified_paths(repo: Path, base: str, head: str) -> set[str]:
    body = run_git(repo, ["log", "--format=%B", f"{base}..{head}"])
    justified: set[str] = set()
    for line in body.splitlines():
        match = _MARKER_RE.match(line)
        if match and match.group("reason").strip():
            justified.add(match.group("path").strip())
    return justified


def check(repo: Path, config: dict, base: str, head: str) -> list[dict]:
    mb = merge_base(repo, base, head)
    justified = collect_justified_paths(repo, mb, head)
    findings: list[dict] = []
    for entry in config["protected_files"]:
        path, rule = entry["path"], entry["rule"]
        stat = numstat(repo, mb, head, path)
        if stat is None:
            continue  # unchanged
        if rule == "regenerable":
            findings.append({"path": path, "verdict": "exempt", "detail": "regenerable"})
            continue
        if isinstance(stat, tuple):
            added, deleted = stat
            if deleted == 0:
                findings.append({"path": path, "verdict": "ok", "detail": f"+{added} additive"})
                continue
            detail = f"+{added} -{deleted}"
        else:
            deleted, detail = 1, "binary overwrite"
        # Non-additive change to an additive_only file: needs a justification marker.
        if path in justified:
            findings.append(
                {"path": path, "verdict": "justified", "detail": f"{detail} (ALLOW-ROOT-DELETION)"}
            )
        else:
            findings.append(
                {
                    "path": path,
                    "verdict": "violation",
                    "detail": f"{detail}; removed/overwrote existing content without "
                    f"an ALLOW-ROOT-DELETION justification",
                }
            )
    return findings


def added_root_files_outside_policy(repo: Path, base: str, head: str, config: dict) -> list[str]:
    protected = {e["path"] for e in config["protected_files"]}
    mb = merge_base(repo, base, head)
    out = run_git(repo, ["diff", "--name-status", "--diff-filter=A", f"{mb}..{head}"])
    new_root: list[str] = []
    for line in out.splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        name = parts[1]
        if "/" not in name and name not in protected:
            new_root.append(name)
    return new_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append-only gate for repo-root files.")
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--repo", default=None)
    ns = parser.parse_args(argv)

    try:
        if ns.repo:
            repo = Path(ns.repo)
        else:
            repo = Path(run_git(Path.cwd(), ["rev-parse", "--show-toplevel"]).strip())
        config = load_config(repo)
        findings = check(repo, config, ns.base, ns.head)
        advisories = added_root_files_outside_policy(repo, ns.base, ns.head, config)
    except ProtectionError as exc:
        print(f"[root-protect] FATAL: {exc}", file=sys.stderr)
        return 2

    violations = [f for f in findings if f["verdict"] == "violation"]
    tags = {"ok": "OK  ", "justified": "JUST", "exempt": "EXMPT", "violation": "FAIL"}
    count = len(config["protected_files"])
    print(f"[root-protect] base={ns.base} head={ns.head} protected={count}")
    for f in findings:
        print(f"[root-protect]   {tags[f['verdict']]} {f['path']}: {f['detail']}")
    for name in advisories:
        print(
            f"[root-protect]   WARN new root file not in protection policy: {name} "
            f"(add it to {CONFIG_RELPATH})"
        )
    if violations:
        print(f"[root-protect] FAILED: {len(violations)} protected root file(s) rewritten/deleted")
        print(
            "[root-protect] To proceed, add a commit message line: "
            "'ALLOW-ROOT-DELETION: <path> — <reason>' and obtain CODEOWNERS approval."
        )
        return 1
    print("[root-protect] OK: no unjustified deletion/overwrite of protected root files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
