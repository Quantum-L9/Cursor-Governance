#!/usr/bin/env python3
"""/ff engine: prove branch novelty, fast-forward the baseline, prune the redundant.

Publishing is deliberately absent. ``make pr`` is the only sanctioned way to reach
GitHub because it is the only one that runs the checkers, so this script never
pushes and never opens a PR -- it reports which branches are worth publishing and
``commands/ff.md`` drives the publish leg from there.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from diagnose_ref_value import diagnose
from git_fetch import fetch_origin

PRUNE_AUTH_ENV = "L9_GIT_PRUNE_AUTHORIZED"
PROTECTED = {"main", "master", "HEAD"}


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _held_elsewhere(repo: Path) -> set[str]:
    """Branches checked out in some other worktree.

    Another worktree's branch is not ours to switch to or delete; git refuses the
    checkout anyway, and deleting it would strand that tree on a missing ref.
    """
    held: set[str] = set()
    current: str | None = None
    for line in _run(repo, "worktree", "list", "--porcelain").stdout.splitlines():
        if line.startswith("worktree "):
            current = line.split(" ", 1)[1]
        elif line.startswith("branch ") and current:
            if Path(current).resolve() != repo.resolve():
                held.add(line.split(" ", 1)[1].removeprefix("refs/heads/"))
    return held


def _local_branches(repo: Path) -> list[str]:
    out = _run(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads")
    return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]


def build_plan(repo: Path, baseline: str, do_fetch: bool = True) -> dict:
    """Read-only: classify every local branch against a freshly fetched baseline."""
    dirty = [ln for ln in _run(repo, "status", "--porcelain").stdout.splitlines() if ln.strip()]
    fetch = (
        fetch_origin(repo, baseline)
        if do_fetch
        else dict({"fetched": False, "error": None, "baseline_tip": ""})
    )

    plan: dict = {
        "schema": "l9.ff.plan/v1",
        "repo": str(repo.resolve()),
        "baseline": baseline,
        "baseline_tip": fetch["baseline_tip"],
        "fetched": fetch["fetched"],
        "fetch_error": fetch["error"],
        "dirty": bool(dirty),
        "dirty_paths": dirty,
        "blocked": None,
        "novel": [],
        "superseded": [],
        "review": [],
        "merged": [],
        "held_elsewhere": sorted(_held_elsewhere(repo)),
        "unproven": [],
    }

    if dirty:
        # A dirty tree makes the later switch to the baseline unsafe, and dirt is
        # /clean's job to route, not this script's to guess at.
        plan["blocked"] = "dirty worktree -- commit, stash, or run /clean first"
        return plan

    if _run(repo, "rev-parse", "--verify", "--quiet", baseline).returncode != 0:
        plan["blocked"] = f"baseline {baseline} does not resolve -- novelty is unprovable"
        return plan

    held = set(plan["held_elsewhere"])
    for branch in _local_branches(repo):
        if branch in PROTECTED:
            continue
        receipt = diagnose(repo, branch, baseline)
        entry = {
            "branch": branch,
            "tip_sha": receipt["tip_sha"],
            "classification": receipt["classification"],
            "confidence": receipt["confidence"],
            "unique_commits": receipt["unique_commits"],
            "cherry_novel": receipt["cherry_novel"],
            "cherry_dup": receipt["cherry_dup"],
            "content_contained": receipt["content_contained"],
            "redundancy_basis": receipt["redundancy_basis"],
            "held_elsewhere": branch in held,
        }
        cls = receipt["classification"]
        if cls == "keep_push":
            plan["novel"].append(entry)
        elif cls == "archive_ref":
            # Only patch-id evidence is exact enough to put a branch on the prune
            # path. Absorption is a line comparison: a one-line addition that
            # happens to exist elsewhere upstream reads as absorbed while the
            # commit is genuinely unlanded. Those go to `review`, which is
            # reported and never deleted or suggested for force-delete.
            if receipt["redundancy_basis"] == "patch_id":
                plan["superseded"].append(entry)
            else:
                plan["review"].append(entry)
        elif cls == "prune_candidate":
            plan["merged"].append(entry)
        else:
            plan["unproven"].append(entry)
    return plan


def apply_plan(repo: Path, baseline: str, prune_superseded: bool = False) -> dict:
    """Fast-forward the baseline branch, then delete what the plan proved redundant."""
    plan = build_plan(repo, baseline, do_fetch=True)
    receipt: dict = {
        "schema": "l9.ff.receipt/v1",
        "repo": str(repo.resolve()),
        "baseline": baseline,
        "fetched": plan["fetched"],
        "fetch_error": plan["fetch_error"],
        "blocked": plan["blocked"],
        "ff": {},
        "pruned": [],
        "needs_human": [],
        "review": plan.get("review", []),
        "skipped": [],
        "errors": [],
    }
    if plan["blocked"]:
        return receipt

    local = baseline.split("/", 1)[1] if "/" in baseline else baseline
    before = _run(repo, "rev-parse", "--short", "HEAD").stdout.strip()

    started_on = _run(repo, "branch", "--show-current").stdout.strip()
    if started_on != local:
        if local in set(plan["held_elsewhere"]):
            receipt["errors"].append(f"{local} is checked out in another worktree")
            return receipt
        switch = _run(repo, "switch", local)
        if switch.returncode != 0:
            receipt["errors"].append(f"cannot switch to {local}: {switch.stderr.strip()}")
            return receipt

    merge = _run(repo, "merge", "--ff-only", baseline)
    if merge.returncode != 0:
        receipt["errors"].append(f"fast-forward refused: {merge.stderr.strip()}")
        # Put the checkout back. Failing here must leave no trace, or the caller
        # resumes on a branch it never asked to be on.
        if started_on and started_on != local:
            back = _run(repo, "switch", started_on)
            if back.returncode != 0:
                receipt["errors"].append(f"could not return to {started_on}: {back.stderr.strip()}")
        return receipt
    receipt["ff"] = {
        "branch": local,
        "before": before,
        "after": _run(repo, "rev-parse", "--short", "HEAD").stdout.strip(),
    }

    # Prune only after the fast-forward: `git branch -d` asks whether a branch is
    # merged into HEAD, so the answer is wrong until HEAD is current.
    authorized = bool(os.environ.get(PRUNE_AUTH_ENV, "").strip())
    for entry in plan["merged"] + plan["superseded"]:
        branch = entry["branch"]
        if entry["held_elsewhere"]:
            receipt["skipped"].append({**entry, "reason": "checked out in another worktree"})
            continue
        delete = _run(repo, "branch", "-d", branch)
        if delete.returncode == 0:
            receipt["pruned"].append({**entry, "method": "branch -d"})
            continue
        # Safe delete refuses anything not reachable from HEAD. A branch whose work
        # landed squashed or on a different parent is exactly that shape: provably
        # redundant, yet not an ancestor. Forcing it is a separate authority.
        stale = not plan["fetched"] and _run(repo, "remote", "get-url", "origin").returncode == 0
        item = {
            **entry,
            "reason": delete.stderr.strip() or "git refused the safe delete",
            "rollback": f"git branch {branch} {entry['tip_sha']}",
            "stale_evidence": stale,
            "authorized": authorized and prune_superseded and not stale,
        }
        if stale:
            # prune-policy.md: redundancy judged against a baseline we could not
            # refresh is not judged. Withhold the command rather than hand over a
            # force-delete backed by evidence we know is out of date.
            item["force_command"] = None
            item["reason"] += " (fetch failed -- evidence stale, no command offered)"
        else:
            item["force_command"] = f"git -C {repo} branch -D {branch}"
        receipt["needs_human"].append(item)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Git work tree")
    parser.add_argument("--baseline", default="origin/main")
    parser.add_argument("--mode", choices=("plan", "apply"), default="plan")
    parser.add_argument("--no-fetch", action="store_true", help="Trust local refs (plan only)")
    parser.add_argument(
        "--prune-superseded",
        action="store_true",
        help=f"Mark force-delete candidates as authorized (also needs {PRUNE_AUTH_ENV})",
    )
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()

    if args.mode == "plan":
        out = build_plan(repo, args.baseline, do_fetch=not args.no_fetch)
    else:
        out = apply_plan(repo, args.baseline, prune_superseded=args.prune_superseded)

    print(json.dumps(out, indent=2, sort_keys=True))
    return 2 if out.get("blocked") or out.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
