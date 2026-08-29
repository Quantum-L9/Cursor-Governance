#!/usr/bin/env python3
"""Fail-closed append-only gate for repository-root files.

Enforces ops/config/root-file-protection.json against a pull request: a protected
root file may be freely ADDED to, but any deletion or in-place overwrite of existing
content fails the gate unless a matching justification marker is recorded in the PR's
commit messages. Machine-generated `regenerable` files are exempt from the additive
check (they are rewritten wholesale by tooling) but remain CODEOWNERS-reviewed.

Justification marker (in any commit message in the PR range):

    ALLOW-ROOT-DELETION: <root-relative-path> — <reason with proof of necessity>

The marker authorizes the CI gate. Ownership mode is solo_ruleset: CODEOWNERS
auto-request is disabled, so the enforced controls are this gate plus the marker,
not a guaranteed CODEOWNERS approval (CODEOWNERS/ORG_INVARIANTS.yaml protected_paths
are the dormant ownership map, live again under codeowners_enforced). This script
is read-only and never edits repository files.

Usage:
    validate_root_file_protection.py [--base <ref>] [--head <ref>] [--repo <path>]
        [--pr-body-file <path>] [--require-pr-body] [--list-touched-additive-only]

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
GIT_TIMEOUT_SECONDS = 120
# Machine stamp. Required in the PR body when any additive_only root file is in
# the diff. make pr injects .github/PULL_REQUEST_TEMPLATE/protected-root.md.
PROTECTED_ROOT_PR_STAMP = "<!-- L9_PROTECTED_ROOT_PR -->"
PROTECTED_ROOT_PR_TEMPLATE = ".github/PULL_REQUEST_TEMPLATE/protected-root.md"

# ALLOW-ROOT-DELETION: <path> — <reason>   (em-dash or " - " separator; reason required)
_MARKER_RE = re.compile(
    r"^\s*ALLOW-ROOT-DELETION:\s*(?P<path>.+?)\s*(?:—|-)\s+(?P<reason>\S.*)$",
)

# Allowlists for untrusted values (CLI refs, config paths) that flow into git
# subcommands or filesystem reads. Validating them before they reach an OS command
# or a path keeps this fail-closed gate injection- and traversal-safe.
_SAFE_REF = re.compile(r"\A[0-9A-Za-z._/+@^~-]{1,255}\Z")
_SAFE_ROOT_RELPATH = re.compile(r"\A[0-9A-Za-z._ +@^~/-]{1,255}\Z")


class ProtectionError(Exception):
    """Malformed invocation or unreadable inputs. Always fail closed."""


def _require_safe(pattern: re.Pattern[str], value: object, kind: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value) or ".." in value.split("/"):
        msg = f"unsafe {kind}: {value!r}"
        raise ProtectionError(msg)
    return value


def run_git(repo: Path, args: list[str]) -> str:
    # args are fixed git subcommands built internally; the only externally-derived
    # values they can carry (refs and repo-relative paths) are allowlist-validated by
    # callers before reaching this point. No shell is used.
    try:
        result = subprocess.run(  # noqa: S603 - fixed git argv, no shell
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        msg = f"git {' '.join(args)} timed out after {GIT_TIMEOUT_SECONDS}s"
        raise ProtectionError(msg) from exc
    if result.returncode != 0:
        msg = f"git {' '.join(args)} failed: {result.stderr.strip()}"
        raise ProtectionError(msg)
    return result.stdout


def load_config(repo: Path) -> dict:
    # Confine the config read to a fixed relative path under the (resolved) repo root
    # so a caller-supplied repo cannot be steered outside it.
    root = repo.resolve()
    path = (root / CONFIG_RELPATH).resolve()
    if root != path.parent.parent.parent or not path.is_file():
        msg = f"protection config not found under repo root: {CONFIG_RELPATH}"
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
        # Protected paths flow into `git diff -- <path>`; allowlist-validate them.
        _require_safe(_SAFE_ROOT_RELPATH, entry["path"], "protected path")
        if entry["rule"] not in ("additive_only", "managed", "regenerable"):
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


def additive_only_touched(repo: Path, config: dict, base: str, head: str) -> list[str]:
    """additive_only protected paths that differ in base..head (any delta)."""
    mb = merge_base(repo, base, head)
    touched: list[str] = []
    for entry in config["protected_files"]:
        if entry["rule"] != "additive_only":
            continue
        if numstat(repo, mb, head, entry["path"]) is None:
            continue
        touched.append(entry["path"])
    return touched


def load_pr_body(*, body_file: str | None = None) -> str | None:
    """PR body from --pr-body-file, L9_PR_BODY, or GITHUB_EVENT_PATH.

    Returns None when no source is present (local make pr). Empty string
    means a source existed but the body was blank.
    """
    if body_file:
        path = Path(body_file)
        if not path.is_file():
            msg = f"--pr-body-file is not a file: {body_file}"
            raise ProtectionError(msg)
        return path.read_text(encoding="utf-8")
    env_body = os.environ.get("L9_PR_BODY")
    if env_body is not None:
        return env_body
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path:
        path = Path(event_path)
        if path.is_file():
            try:
                event = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                msg = f"GITHUB_EVENT_PATH is not valid JSON: {exc}"
                raise ProtectionError(msg) from exc
            if isinstance(event, dict):
                pr = event.get("pull_request")
                if isinstance(pr, dict):
                    body = pr.get("body")
                    return body if isinstance(body, str) else ""
            return ""
    return None


def has_protected_template_stamp(body: str) -> bool:
    return PROTECTED_ROOT_PR_STAMP in body


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
        if rule in ("regenerable", "managed"):
            # Exempt from the additive check; CODEOWNERS review still applies.
            note = "regenerable" if rule == "regenerable" else "managed (review-only)"
            findings.append({"path": path, "verdict": "exempt", "detail": note})
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


def tracked_root_files(repo: Path) -> set[str]:
    """Every tracked repository-root file (top level only), case-exact."""
    out = run_git(repo, ["ls-files", "-z"])
    return {name for name in out.split("\0") if name and "/" not in name}


def reconcile_root_inventory(repo: Path, config: dict) -> tuple[list[str], list[str]]:
    """Return (unregistered, stale) — the complete-inventory reconciliation.

    Delta-based checks only see files changed in the PR, so a root file that
    predates the PR and was never classified stays invisible forever (P2-11).
    This compares the FULL tracked root inventory against the registry every run:
      tracked_root_files == registered_root_files ∪ exempt_root_files
    Comparison is case-sensitive, so a casing drift is a mismatch, not a match.
    """
    tracked = tracked_root_files(repo)
    registered = {e["path"] for e in config["protected_files"]}
    exempt = set(config.get("exempt_root_files", []))
    for value in exempt:
        _require_safe(_SAFE_ROOT_RELPATH, value, "exempt root path")
    known = registered | exempt
    unregistered = sorted(tracked - known)
    stale = sorted(known - tracked)
    return unregistered, stale


def added_root_files_outside_policy(repo: Path, base: str, head: str, config: dict) -> list[str]:
    protected = {e["path"] for e in config["protected_files"]}
    mb = merge_base(repo, base, head)
    # Include added (A), copied (C) and renamed (R): a file can be introduced into the
    # repo root by a move/copy too, and its destination path is the LAST tab field.
    out = run_git(repo, ["diff", "--name-status", "--diff-filter=ACR", f"{mb}..{head}"])
    new_root: list[str] = []
    for line in out.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        name = fields[-1]  # destination path (A: only field; R/C: the new path)
        if "/" not in name and name not in protected:
            new_root.append(name)
    return new_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append-only gate for repo-root files.")
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--pr-body-file",
        default=None,
        help="PR body to check for the protected-root template stamp",
    )
    parser.add_argument(
        "--require-pr-body",
        action="store_true",
        help="Fail when additive_only files changed and no PR body source exists",
    )
    parser.add_argument(
        "--list-touched-additive-only",
        action="store_true",
        help="Print additive_only paths in the range and exit 0",
    )
    ns = parser.parse_args(argv)

    try:
        # Validate untrusted refs before they are embedded in any git command.
        base = _require_safe(_SAFE_REF, ns.base, "base ref")
        head = _require_safe(_SAFE_REF, ns.head, "head ref")
        if ns.repo:
            repo = Path(ns.repo).resolve()
            if not repo.is_dir():
                msg = f"--repo is not a directory: {ns.repo}"
                raise ProtectionError(msg)
        else:
            repo = Path(run_git(Path.cwd(), ["rev-parse", "--show-toplevel"]).strip())
        config = load_config(repo)
        if ns.list_touched_additive_only:
            for path in additive_only_touched(repo, config, base, head):
                print(path)
            return 0
        findings = check(repo, config, base, head)
        # Complete-inventory reconciliation (authoritative; not delta-based).
        inv_unregistered, inv_stale = reconcile_root_inventory(repo, config)
        # Delta view kept for a PR-scoped message; its hits are a subset of
        # inv_unregistered, so de-duplicate below.
        delta_unregistered = added_root_files_outside_policy(repo, base, head, config)
        unregistered = sorted(set(inv_unregistered) | set(delta_unregistered))
    except ProtectionError as exc:
        print(f"[root-protect] FATAL: {exc}", file=sys.stderr)
        return 2

    violations = [f for f in findings if f["verdict"] == "violation"]
    tags = {"ok": "OK  ", "justified": "JUST", "exempt": "EXMPT", "violation": "FAIL"}
    count = len(config["protected_files"])
    print(f"[root-protect] base={ns.base} head={ns.head} protected={count}")
    for f in findings:
        print(f"[root-protect]   {tags[f['verdict']]} {f['path']}: {f['detail']}")
    # A brand-new repository-root file that is not registered in the policy would be
    # unprotected. Fail closed: every root file must be classified into a tier, so the
    # guarantee "every root file is protected" cannot be silently bypassed.
    for name in unregistered:
        print(f"[root-protect]   FAIL {name}: root file not registered in {CONFIG_RELPATH}")
    # Stale registry entries: a path is registered/exempt but no longer a tracked
    # root file. The registry must describe reality exactly (P2-11).
    for name in inv_stale:
        print(f"[root-protect]   FAIL {name}: registry entry references a non-tracked root file")

    require_body = bool(ns.require_pr_body) or os.environ.get("GITHUB_ACTIONS") == "true"
    template_missing = False
    touched_additive = additive_only_touched(repo, config, base, head)
    if touched_additive:
        try:
            pr_body = load_pr_body(body_file=ns.pr_body_file)
        except ProtectionError as exc:
            print(f"[root-protect] FATAL: {exc}", file=sys.stderr)
            return 2
        if pr_body is None and not require_body:
            print(
                "[root-protect] NOTE: additive_only touched "
                f"({', '.join(touched_additive)}); PR-body template check skipped "
                "(no body source; CI / --require-pr-body enforces "
                f"{PROTECTED_ROOT_PR_STAMP})"
            )
        elif pr_body is None or not has_protected_template_stamp(pr_body):
            template_missing = True
            print(
                "[root-protect]   FAIL PR body: touches additive_only "
                f"{', '.join(touched_additive)} but is missing "
                f"{PROTECTED_ROOT_PR_STAMP} — use {PROTECTED_ROOT_PR_TEMPLATE} "
                "(make pr injects it)"
            )

    failures = len(violations) + len(unregistered) + len(inv_stale) + int(template_missing)
    if failures:
        print(f"[root-protect] FAILED: {failures} issue(s)")
        if violations:
            print(
                "[root-protect] For a rewrite/deletion: add a commit message line "
                "'ALLOW-ROOT-DELETION: <path> — <reason>' and obtain CODEOWNERS approval."
            )
        if unregistered:
            print(
                "[root-protect] For a new root file: register it in "
                f"{CONFIG_RELPATH} with a tier (additive_only / managed / regenerable)."
            )
        if inv_stale:
            print(
                "[root-protect] For a stale entry: remove it from "
                f"{CONFIG_RELPATH} (runtime/gitignored artifacts must not be registered)."
            )
        if template_missing:
            print(
                "[root-protect] For a PR that touches additive_only root files: "
                f"use {PROTECTED_ROOT_PR_TEMPLATE} so the body contains "
                f"{PROTECTED_ROOT_PR_STAMP}. make pr injects this template."
            )
        return 1
    print(
        "[root-protect] OK: complete root inventory reconciled "
        f"({len(tracked_root_files(repo))} tracked root files) and compliant"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
