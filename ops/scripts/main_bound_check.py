#!/usr/bin/env python3
"""Pre-publication main-bound execution gate (invariants E2, E3, E4).

Runs inside ``open_pr_after_gate.sh`` — the sole sanctioned publish path — after
the base ref has been refreshed from the remote and before the overlap gate.
Proves three things about the branch about to be published:

  E2  ordinary task branches originate from fetched ``origin/main``;
  E3  agents do not directly push ``main``;
  E4  ordinary PRs target ``main``.

Each is a property of Git state, not of memory state. Nothing here consults a
lock: the publication decision is made from ancestry and refs alone.

Exceptions are explicit, never inferred:

  ``L9_TASK_BASE_AUTHORIZED=<reason>``  stacked / campaign ancestry (§2)
  ``PR_BASE=origin/<branch>``           targeting a non-main base, which is only
                                        accepted alongside the authorization
                                        above or an explicit ``PR_STACK=auto``
                                        decision made by the overlap gate.

Failure policy: fail-closed. A branch whose ancestry cannot be established is
not publishable autonomously (§14) — the local work stays valid and isolated.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

PROTECTED_BRANCHES = ("main", "master")


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _fail(message: str) -> int:
    print(f"BLOCK: {message}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--base", default="origin/main", help="PR base ref (PR_BASE)")
    args = parser.parse_args()

    repo = args.workspace.resolve()
    base = args.base
    base_authorized = os.environ.get("L9_TASK_BASE_AUTHORIZED", "").strip()
    stacking = os.environ.get("PR_STACK", "").strip().lower() == "auto"

    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if not branch or branch == "HEAD":
        return _fail("detached HEAD — publication requires a named task branch (E2)")

    # E3 — never publish main itself.
    if branch in PROTECTED_BRANCHES:
        return _fail(
            f"on '{branch}' — agents must not push an integration branch directly (E3). "
            "Start a task with ops/scripts/agent_worktree_start.sh."
        )

    # E4 — ordinary PRs target main.
    if base not in ("origin/main", "main"):
        if not (base_authorized or stacking):
            return _fail(
                f"PR base is '{base}', not origin/main (E4). Ordinary main-bound execution "
                "targets main. Stacking on an open PR head requires PR_STACK=auto; a "
                "campaign base requires L9_TASK_BASE_AUTHORIZED=<reason>."
            )
        why = base_authorized or "PR_STACK=auto"
        print(f"NOTE: non-main PR base '{base}' authorized ({why})")

    # E2 — ancestry. The task branch must descend from the base we are about to
    # target, evaluated against the ref as *just fetched* by the caller.
    if git(repo, "rev-parse", "--verify", "--quiet", base).returncode != 0:
        return _fail(f"cannot resolve base ref '{base}' — ancestry unverifiable, failing closed")

    merge_base = git(repo, "merge-base", base, "HEAD").stdout.strip()
    if not merge_base:
        return _fail(
            f"no merge base between HEAD and '{base}' — this branch does not share history "
            "with its integration target (E2), failing closed"
        )

    # Ancestry evidence recorded at task start, when present, must agree.
    recorded = _recorded_base_sha(repo, branch)
    if recorded:
        reachable = git(repo, "merge-base", "--is-ancestor", recorded, "HEAD").returncode == 0
        if not reachable:
            return _fail(
                f"recorded base_sha {recorded[:12]} for branch '{branch}' is not an ancestor of "
                "HEAD — the branch was re-pointed after task start (E2), failing closed"
            )
        print(f"OK: branch descends from its recorded task base {recorded[:12]}")
    else:
        print(
            "NOTE: no .l9/agent-tasks record for this branch — ancestry checked against the "
            "fetched base ref only (task started outside agent_worktree_start.sh)"
        )

    behind = git(repo, "rev-list", "--count", f"{merge_base}..{base}").stdout.strip() or "0"
    print(
        f"PASS: main-bound (branch='{branch}' base='{base}' merge-base={merge_base[:12]}; "
        f"base is {behind} commit(s) ahead of the fork point)"
    )
    return 0


def _recorded_base_sha(repo: Path, branch: str) -> str:
    """base_sha recorded by agent_worktree_start.sh for this branch, if any."""
    import json

    meta_dir = repo / ".l9" / "agent-tasks"
    if not meta_dir.is_dir():
        return ""
    for path in sorted(meta_dir.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if str(doc.get("branch") or "") == branch:
            return str(doc.get("base_sha") or "")
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
