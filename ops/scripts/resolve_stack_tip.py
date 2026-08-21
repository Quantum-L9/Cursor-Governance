#!/usr/bin/env python3
"""Fail-closed unique open-PR stack-tip resolver.

Same rule for start and publish. File overlap is not required.

- no open PRs → origin/main (or --default-ref)
- one unique chain → that chain's tip head
- sibling chains or an unreadable topology → exit 2
- gh / identity / fetch failure → exit 2 (do not guess main while PRs exist)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

MAIN_ALIASES = {"main", "origin/main"}
_PAGE_SIZE = 100
_MAX_PAGES = 30


class TipError(RuntimeError):
    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class OpenPR:
    number: int
    head: str
    base: str
    sha: str


@dataclass(frozen=True)
class TipResult:
    ref: str
    sha: str
    reason: str
    siblings: tuple[str, ...] = ()


def gh_available() -> bool:
    return shutil.which("gh") is not None


def run_gh(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


def resolve_repo_slug(repo: Path) -> str | None:
    remote = run_git(repo, "remote", "get-url", "origin")
    if remote.returncode != 0:
        return None
    url = remote.stdout.strip()
    if url.endswith(".git"):
        url = url[:-4]
    if "github.com" not in url:
        return None
    tail = url.split("github.com", 1)[1].lstrip(":/")
    parts = [part for part in tail.split("/") if part]
    if len(parts) < 2:
        return None
    return f"{parts[0]}/{parts[1]}"


def _paginated_lines(path: str, jq: str) -> list[str] | None:
    lines: list[str] = []
    separator = "&" if "?" in path else "?"
    for page in range(1, _MAX_PAGES + 1):
        result = run_gh(
            "api",
            f"{path}{separator}per_page={_PAGE_SIZE}&page={page}",
            "--jq",
            jq,
        )
        if result.returncode != 0:
            return None
        page_lines = [line for line in result.stdout.splitlines() if line]
        lines.extend(page_lines)
        if len(page_lines) < _PAGE_SIZE:
            return lines
    return None


def list_open_prs(slug: str) -> list[OpenPR] | None:
    rows = _paginated_lines(
        f"repos/{slug}/pulls?state=open",
        ".[] | [.number, .head.ref, .base.ref, .head.sha] | @tsv",
    )
    if rows is None:
        return None
    prs: list[OpenPR] = []
    for line in rows:
        parts = line.split("\t")
        if len(parts) != 4:
            return None
        number, head, base, sha = parts
        try:
            prs.append(OpenPR(number=int(number), head=head, base=base, sha=sha))
        except ValueError:
            return None
    return prs


def _is_main(ref: str) -> bool:
    return ref.strip().removeprefix("origin/") in MAIN_ALIASES or ref.strip() in MAIN_ALIASES


def resolve_from_prs(prs: list[OpenPR], *, default_ref: str) -> TipResult:
    """Pure topology. Callers supply the live PR list."""
    if not prs:
        return TipResult(ref=default_ref, sha="", reason="no_open_prs")

    by_head = {pr.head: pr for pr in prs}
    if len(by_head) != len(prs):
        raise TipError("duplicate open-PR heads; refuse to pick a tip")

    roots = [pr for pr in prs if _is_main(pr.base)]
    if not roots:
        heads = ", ".join(sorted(by_head))
        raise TipError(f"open PRs exist but none target main: {heads}")
    if len(roots) > 1:
        named = ", ".join(f"#{pr.number}:{pr.head}" for pr in sorted(roots, key=lambda p: p.number))
        raise TipError(f"sibling open-PR chains target main: {named}")

    current = roots[0]
    seen: set[str] = {current.head}
    while True:
        children = [pr for pr in prs if pr.base == current.head]
        if not children:
            return TipResult(
                ref=current.head,
                sha=current.sha,
                reason="unique_chain_tip",
            )
        if len(children) > 1:
            named = ", ".join(
                f"#{pr.number}:{pr.head}" for pr in sorted(children, key=lambda p: p.number)
            )
            raise TipError(f"sibling open-PR chains fork at {current.head}: {named}")
        nxt = children[0]
        if nxt.head in seen:
            raise TipError(f"open-PR chain cycles at {nxt.head}")
        seen.add(nxt.head)
        current = nxt


def resolve_default_sha(repo: Path, default_ref: str) -> str:
    fetched = run_git(repo, "rev-parse", "--verify", default_ref)
    if fetched.returncode == 0 and fetched.stdout.strip():
        return fetched.stdout.strip()
    raise TipError(f"cannot resolve {default_ref} in {repo}")


def resolve_stack_tip(
    repo: Path,
    *,
    default_ref: str = "origin/main",
    prs: list[OpenPR] | None = None,
    list_prs: Callable[[str], list[OpenPR] | None] | None = None,
) -> TipResult:
    if prs is None:
        if not gh_available() and list_prs is None:
            raise TipError("gh CLI unavailable; refuse to guess the stack tip")
        slug = resolve_repo_slug(repo)
        if not slug:
            raise TipError("cannot resolve repository identity (owner/repo)")
        lister = list_prs or list_open_prs
        loaded = lister(slug)
        if loaded is None:
            raise TipError("could not enumerate open PRs (gh api failed)")
        prs = loaded
    result = resolve_from_prs(prs, default_ref=default_ref)
    if result.reason == "no_open_prs":
        return TipResult(
            ref=default_ref,
            sha=resolve_default_sha(repo, default_ref),
            reason=result.reason,
        )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--default-ref", default=os.environ.get("L9_STACK_DEFAULT_REF", "origin/main"))
    args = parser.parse_args(argv)
    try:
        result = resolve_stack_tip(args.workspace.resolve(), default_ref=args.default_ref)
    except TipError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return exc.exit_code
    print(f"STACK_TIP={result.ref}")
    print(f"STACK_TIP_SHA={result.sha}")
    print(f"REASON={result.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
