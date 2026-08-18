#!/usr/bin/env python3
"""Pre-open PR overlap gate (PR_OVERLAP_GUARDRAIL_V1).

Runs inside open_pr_after_gate.sh — the sole sanctioned publish path — between
the L4 release check and `git push`. Detects whether the current branch
textually conflicts with any already-open PR in the same repo, BEFORE the push,
and blocks with routing instructions.

Collision detection is decided from Git state (invariant E5): the caller
refreshes the base ref, and this gate evaluates the task branch against the
*current* origin/main plus every open PR targeting it — not against the task's
original BASE_SHA. Same-file overlap alone is never a collision; the
`git merge-tree` probe distinguishes disjoint hunks from a real conflict.

Failure policy (invariant E6 — "unable to determine collision state = publication
denied"):
  * **autonomous publication fails CLOSED on missing telemetry.** gh absent, a
    gh api failure, an unresolvable repo identity or unreadable changed-file
    set all mean the collision state is unknown, and an unknown collision state
    is not publishable. Local isolated work stays valid: only the push is
    blocked;
  * fail-open on precision, fail-closed on the decision: a filename overlap
    whose textual probe is unavailable still blocks;
  * fail-closed on a detected non-generated textual conflict.

An interactive human run keeps the old fail-open behaviour, because a person can
see the WARN and judge it. Autonomy is detected from L9_AUTONOMY_ENABLED /
CI / a non-tty stdin, and is overridable both ways:

  PR_OVERLAP_TELEMETRY=closed   always deny on undeterminable state
  PR_OVERLAP_TELEMETRY=open     degrade to WARN (state a justification)

Modes via PR_OVERLAP env: block (default, exit 1) | warn (exit 0 + WARN) |
ignore (skip). PR_STACK=auto: instead of blocking on an unambiguous single open
PR chain, print `STACK_BASE=<head-branch>` and exit 0 — open_pr_after_gate.sh
then re-resolves the PR base to that head (never main). Automatic stacking is
therefore opt-in only: under ordinary main-bound execution the base stays main.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from sync_generated_artifacts import GENERATED_PATH_PREFIXES
except Exception as exc:  # pragma: no cover — degraded interpreter without yaml
    print(
        f"WARN: cannot import GENERATED_PATH_PREFIXES ({exc}); "
        "generated paths are not exempted this run"
    )
    GENERATED_PATH_PREFIXES = ()


def autonomous_publication() -> bool:
    """True when no human is watching this publish decision.

    Under autonomy an undeterminable collision state must deny (E6); an
    interactive operator may instead read the WARN and decide.
    """
    if os.environ.get("L9_AUTONOMY_ENABLED", "").strip().lower() in {"1", "true", "yes"}:
        return True
    if os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}:
        return True
    try:
        return not sys.stdin.isatty()
    except (AttributeError, ValueError):
        return True


def telemetry_failure(what: str) -> int:
    """Handle an undeterminable collision state.

    Returns the process exit code: 1 (deny) under autonomous publication or an
    explicit PR_OVERLAP_TELEMETRY=closed, else 0 with a WARN.
    """
    policy = os.environ.get("PR_OVERLAP_TELEMETRY", "").strip().lower()
    if policy == "open":
        print(f"WARN: {what} — overlap gate skipped (PR_OVERLAP_TELEMETRY=open)")
        return 0
    if policy == "closed" or autonomous_publication():
        print(f"BLOCK: {what} — collision state undeterminable, so publication is denied (E6).")
        print("  Local work is unaffected: only the push is blocked.")
        print("  Restore telemetry (gh auth/network), then re-run make pr.")
        print("  A human may override with a stated justification: PR_OVERLAP_TELEMETRY=open")
        return 1
    print(f"WARN: {what} — overlap gate skipped (interactive run, fail-open)")
    return 0


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", "-C", str(repo), *args])


def gh(*args: str) -> subprocess.CompletedProcess[str]:
    return _run(["gh", *args])


def is_generated_prefix_path(rel: str) -> bool:
    """Mirror sync_generated_artifacts.is_generated_path minus the orphan-heal
    SKILL.md rule: overlap exemptions are the canonical generated prefixes only."""
    return any(
        rel.startswith(prefix) or rel == prefix.rstrip(".") for prefix in GENERATED_PATH_PREFIXES
    )


def gh_available() -> bool:
    return gh("--version").returncode == 0


def current_branch(repo: Path) -> str:
    return git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def changed_files(repo: Path, base: str) -> list[str] | None:
    result = git(repo, "diff", "--name-only", f"{base}...HEAD")
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line]


def resolve_repo_slug(repo: Path) -> str | None:
    """Remote-URL parse first (no API call), then the gh repo view convenience
    (GraphQL) exactly like open_pr_after_gate.sh — optional, never required."""
    url = git(repo, "config", "--get", "remote.origin.url").stdout.strip()
    if url:
        clean = url[:-4] if url.endswith(".git") else url
        if "://" in clean:
            parts = clean.split("://", 1)[1].rstrip("/").split("/")
            if len(parts) >= 3:  # scheme://host/owner/name
                after = "/".join(parts[-2:])
            else:
                after = ""
        else:
            # scp-like: git@host:owner/name (check @ before the colon split)
            after = clean.split("@", 1)[-1]
            if ":" in after.split("/", 1)[0]:
                after = after.split(":", 1)[1]
        if after.count("/") == 1 and after and " " not in after:
            return after
    result = gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner")
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


def open_prs(slug: str) -> list[dict[str, str | int]] | None:
    """REST-only: repos/<o>/<n>/pulls, paginated via gh --paginate."""
    result = gh(
        "api",
        "--paginate",
        f"repos/{slug}/pulls?state=open&per_page=100",
        "--jq",
        ".[] | [.number, .head.ref, .base.ref] | @tsv",
    )
    if result.returncode != 0:
        return None
    prs: list[dict[str, str | int]] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        number, head, base = parts
        try:
            prs.append({"number": int(number), "head": head, "base": base})
        except ValueError:
            continue
    return prs


def pr_files(slug: str, number: int) -> list[str] | None:
    """REST-only: repos/<o>/<n>/pulls/<N>/files, paginated."""
    result = gh(
        "api",
        "--paginate",
        f"repos/{slug}/pulls/{number}/files?per_page=100",
        "--jq",
        ".[].filename",
    )
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line]


def merge_tree_conflicts(repo: Path, pr_number: int) -> list[str] | None:
    """Fetch pull/<N>/head and probe with git merge-tree --write-tree (needs
    git >= 2.38). Returns conflicting paths, [] for a clean merge, or None when
    the probe is unavailable (fetch/unsupported git) — callers degrade to
    filename-overlap blocking."""
    fetch = git(repo, "fetch", "--quiet", "origin", f"pull/{pr_number}/head")
    if fetch.returncode != 0:
        return None
    result = git(repo, "merge-tree", "--write-tree", "--name-only", "HEAD", "FETCH_HEAD")
    if result.returncode == 0:
        return []
    if result.returncode == 1:
        # --name-only emits conflicted paths as bare lines; informational lines
        # ("Auto-merging X", "CONFLICT (content): ...") and content hashes carry
        # spaces or are 40-hex/digit tokens — paths in this repo never do.
        conflicts: list[str] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or " " in line or line.isdigit():
                continue
            if len(line) == 40 and all(c in "0123456789abcdef" for c in line):
                continue
            conflicts.append(line)
        return conflicts
    return None


def stack_chain(entries: list[dict]) -> list[dict] | None:
    """Bottom-up chain over the blocking PR set; None when ambiguous (siblings
    or a partial chain). One entry is trivially a chain."""
    if len(entries) == 1:
        return list(entries)
    by_head = {str(e["pr"]["head"]): e for e in entries}
    bases = {str(e["pr"]["base"]) for e in entries}
    tops = [e for e in entries if str(e["pr"]["head"]) not in bases]
    if len(tops) != 1:
        return None
    chain: list[dict] = []
    current: dict | None = tops[0]
    seen: set[str] = set()
    while current is not None:
        head = str(current["pr"]["head"])
        if head in seen:
            return None  # cycle
        seen.add(head)
        chain.append(current)
        current = by_head.get(str(current["pr"]["base"]))
    if len(chain) != len(entries):
        return None  # some blocking PRs live outside the chain
    return list(reversed(chain))  # bottom-up


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Repo to gate")
    parser.add_argument("--base", default="origin/main", help="PR base ref (PR_BASE)")
    args = parser.parse_args()

    mode = os.environ.get("PR_OVERLAP", "block").strip().lower() or "block"
    auto_stack = os.environ.get("PR_STACK", "").strip().lower() == "auto"

    if mode == "ignore":
        print("NOTE: PR_OVERLAP=ignore — overlap gate skipped")
        return 0
    if mode not in ("block", "warn"):
        print(f"WARN: unknown PR_OVERLAP={mode!r} — treating as block")
        mode = "block"

    repo = args.workspace.resolve()

    if not gh_available():
        return telemetry_failure("gh CLI unavailable")

    branch = current_branch(repo)
    changed = changed_files(repo, args.base)
    if changed is None:
        return telemetry_failure(f"cannot compute changed files vs {args.base}")

    slug = resolve_repo_slug(repo)
    if not slug:
        return telemetry_failure("cannot resolve repository identity (owner/repo)")

    prs = open_prs(slug)
    if prs is None:
        return telemetry_failure("could not enumerate open PRs (gh api failed)")

    candidates = [pr for pr in prs if pr["head"] != branch]
    if not candidates:
        print("PASS: no other open PRs to overlap")
        return 0

    # (c)+(d) filename intersection minus generated paths.
    overlap_by_pr: dict[int, dict] = {}
    for pr in candidates:
        number = int(pr["number"])
        files = pr_files(slug, number)
        if files is None:
            # Unknown file set for a live open PR is an unknown collision state.
            rc = telemetry_failure(f"could not fetch file list for PR #{number}")
            if rc:
                return rc
            continue
        common = sorted(set(changed) & set(files))
        common = [path for path in common if not is_generated_prefix_path(path)]
        if common:
            overlap_by_pr[number] = {"pr": pr, "files": common}

    if not overlap_by_pr:
        print("PASS: no non-generated file overlap with open PRs")
        return 0

    # (e) textual probe: distinguish same-file/disjoint-hunks from real conflict.
    blockers: dict[int, dict] = {}
    for number, entry in overlap_by_pr.items():
        pr = entry["pr"]
        conflicts = merge_tree_conflicts(repo, number)
        if conflicts is None:
            entry["note"] = "textual probe unavailable (fetch or merge-tree failed)"
            blockers[number] = entry
            continue
        real = sorted({path for path in conflicts if not is_generated_prefix_path(path)})
        if real:
            entry["conflicts"] = real
            blockers[number] = entry
        else:
            print(
                f"NOTE: overlap with PR #{number} ({pr['head']}) is disjoint hunks or "
                "generated-only conflicts — proceeding"
            )

    if not blockers:
        print("PASS: overlapping files merge cleanly (disjoint hunks)")
        return 0

    if auto_stack:
        chain = stack_chain(list(blockers.values()))
        if chain is not None:
            top = chain[-1]["pr"]
            print(f"STACK_BASE={top['head']}")
            print(
                f"NOTE: PR_STACK=auto — stacking on open PR #{top['number']} "
                f"head '{top['head']}' (never main)"
            )
            return 0
        print("NOTE: PR_STACK=auto — no unambiguous single chain to stack on; blocking instead")

    header = (
        "WARN: PR overlap (non-generated files)"
        if mode == "warn"
        else "BLOCK: PR overlap (non-generated files)"
    )
    print(header)
    for number in sorted(blockers):
        entry = blockers[number]
        pr = entry["pr"]
        print(f"  PR #{number} (head branch '{pr['head']}')")
        for path in entry.get("conflicts") or entry["files"]:
            print(f"    - {path}")
        if entry.get("note"):
            print(f"    ({entry['note']})")
    print("Routing options (preferred first):")
    print("  1) commit this work into the overlapping open PR branch instead of a sibling PR")
    print("  2) stack on the open PR head: PR_STACK=auto (or PR_BASE=origin/<open-pr-head>)")
    print("  3) bypass with stated justification: PR_OVERLAP=ignore")
    return 0 if mode == "warn" else 1


if __name__ == "__main__":
    raise SystemExit(main())
