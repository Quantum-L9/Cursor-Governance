#!/usr/bin/env python3
"""Fail-closed unique open-PR stack-tip resolver.

Same rule for start and publish. File overlap is not required.

- the branch already has an open PR → that PR's base (reason open_pr_base);
  the board's shape is not consulted, because the base is already a fact
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
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

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
    # Every open-PR head on the walk from the main-rooted PR to the tip, root
    # first, tip last. A child's PR body must not tell commits that belong to any
    # of these — a parent cut before its own base was refreshed inherits commits
    # the child then sees in `parent..HEAD` (PR #602 was titled with one).
    chain: tuple[str, ...] = ()


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


def resolve_from_prs(
    prs: list[OpenPR], *, default_ref: str, branch: str | None = None
) -> TipResult:
    """Pure topology. Callers supply the live PR list.

    When ``branch`` already has an open PR, that PR's base *is* the base: it is
    a fact GitHub holds, not a choice left to make, so the chain-tip walk is not
    consulted. Without this, a second ``make pr`` on the stack root resolved the
    tip — its own descendant — and a sibling PR opened by someone else mid-run
    fail-closed a publish whose base was never in question (PR #602).
    """
    if not prs:
        return TipResult(ref=default_ref, sha="", reason="no_open_prs")

    by_head = {pr.head: pr for pr in prs}
    if len(by_head) != len(prs):
        raise TipError("duplicate open-PR heads; refuse to pick a tip")

    if branch and branch in by_head:
        return _open_pr_base(by_head, by_head[branch], default_ref=default_ref)

    roots = [pr for pr in prs if _is_main(pr.base)]
    if not roots:
        heads = ", ".join(sorted(by_head))
        raise TipError(f"open PRs exist but none target main: {heads}")
    if len(roots) > 1:
        named = ", ".join(f"#{pr.number}:{pr.head}" for pr in sorted(roots, key=lambda p: p.number))
        raise TipError(f"sibling open-PR chains target main: {named}")

    current = roots[0]
    seen: set[str] = {current.head}
    chain: list[str] = [current.head]
    while True:
        children = [pr for pr in prs if pr.base == current.head]
        if not children:
            return TipResult(
                ref=current.head,
                sha=current.sha,
                reason="unique_chain_tip",
                chain=tuple(chain),
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
        chain.append(nxt.head)
        current = nxt


def _open_pr_base(by_head: dict[str, OpenPR], mine: OpenPR, *, default_ref: str) -> TipResult:
    """The base of the branch's own open PR, with the chain of open PRs above it.

    The chain is walked *upward* from that base (head → its PR's base → …) until
    main, so it is independent of sibling chains elsewhere on the board and of
    the tip walk's fail-closed rules. An ancestor whose PR has since merged has
    no open PR to continue through; the chain stops there.
    """
    if _is_main(mine.base):
        return TipResult(ref=default_ref, sha="", reason="open_pr_base")
    chain: list[str] = []
    seen: set[str] = {mine.head}
    current = mine.base
    while current and not _is_main(current):
        if current in seen:
            raise TipError(f"open-PR chain cycles at {current}")
        seen.add(current)
        chain.append(current)
        parent = by_head.get(current)
        current = parent.base if parent else ""
    chain.reverse()
    base_pr = by_head.get(mine.base)
    return TipResult(
        ref=mine.base,
        sha=base_pr.sha if base_pr else "",
        reason="open_pr_base",
        chain=tuple(chain),
    )


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
    branch: str | None = None,
) -> TipResult:
    if branch is None:
        branch = current_branch(repo)
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
    result = resolve_from_prs(prs, default_ref=default_ref, branch=branch)
    if result.ref == default_ref and not result.sha:
        return TipResult(
            ref=default_ref,
            sha=resolve_default_sha(repo, default_ref),
            reason=result.reason,
            chain=result.chain,
        )
    return result


def current_branch(repo: Path) -> str:
    """The checked-out branch name, or "" on a detached HEAD."""
    probe = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    name = probe.stdout.strip() if probe.returncode == 0 else ""
    return "" if name == "HEAD" else name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument(
        "--default-ref",
        default=os.environ.get("L9_STACK_DEFAULT_REF", "origin/main"),
    )
    parser.add_argument(
        "--branch",
        default=None,
        help="Branch being published (default: the checked-out branch). Its open PR, "
        "if any, decides the base.",
    )
    args = parser.parse_args(argv)
    try:
        result = resolve_stack_tip(
            args.workspace.resolve(), default_ref=args.default_ref, branch=args.branch
        )
    except TipError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return exc.exit_code
    print(f"STACK_TIP={result.ref}")
    print(f"STACK_TIP_SHA={result.sha}")
    print(f"REASON={result.reason}")
    print(f"STACK_CHAIN={' '.join(result.chain)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
