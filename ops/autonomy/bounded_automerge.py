#!/usr/bin/env python3
"""Bounded exact-PR exact-head automerge for PR_AUTOMERGE=1 make pr.

Standing unbounded merge stays forbidden. This module may merge only when:

  * PR_AUTOMERGE=1 (PR_AUTOMERGE=0 is a reliable opt-out)
  * authorization is for this exact PR number
  * the observed head SHA matches the PR head
  * the PR is not a draft
  * required checks are green
  * GitHub reports mergeable
  * no blocking review remains

Force-push and admin-merge are never authorized here.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from authorize_merge import auth_path, write_authorization

SOURCE = "pr_automerge"
REASON = "PR_AUTOMERGE=1 exact-PR exact-head green mergeable"


@dataclass(frozen=True)
class PullRequestState:
    repo: str
    number: int
    head_sha: str
    is_draft: bool
    mergeable: bool
    review_decision: str
    required_checks_green: bool


FetchFn = Callable[[str, int], PullRequestState]


def evaluate(
    state: PullRequestState,
    *,
    observed_head: str,
    automerge: bool,
) -> tuple[bool, list[str]]:
    """Return (allowed, deny_reasons). Empty reasons means the transition may run."""
    reasons: list[str] = []
    if not automerge:
        reasons.append("PR_AUTOMERGE=0")
        return False, reasons
    if not observed_head or state.head_sha != observed_head:
        reasons.append("head_mismatch")
    if state.is_draft:
        reasons.append("draft")
    if not state.mergeable:
        reasons.append("not_mergeable")
    if not state.required_checks_green:
        reasons.append("checks_not_green")
    decision = (state.review_decision or "").upper()
    if decision in {"CHANGES_REQUESTED", "REVIEW_REQUIRED"}:
        reasons.append("blocking_review")
    return (not reasons), reasons


def fetch_pull_request(repo: str, number: int) -> PullRequestState:
    """Load PR state from gh. Fail closed when the payload is incomplete."""
    proc = subprocess.run(
        [
            "gh",
            "pr",
            "view",
            str(number),
            "--repo",
            repo,
            "--json",
            "number,isDraft,mergeable,reviewDecision,headRefOid,statusCheckRollup",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "gh pr view failed")
    payload = json.loads(proc.stdout)
    return _state_from_payload(repo, number, payload)


def _state_from_payload(repo: str, number: int, payload: dict[str, Any]) -> PullRequestState:
    rollup = payload.get("statusCheckRollup") or []
    required_green = True
    if isinstance(rollup, list) and rollup:
        required_green = all(
            str(item.get("conclusion") or item.get("state") or "").upper()
            in {"SUCCESS", "SKIPPED", "NEUTRAL"}
            for item in rollup
            if isinstance(item, dict)
        )
    mergeable = str(payload.get("mergeable") or "").upper() in {"MERGEABLE", "TRUE"}
    if payload.get("mergeable") is True:
        mergeable = True
    return PullRequestState(
        repo=repo,
        number=int(payload.get("number") or number),
        head_sha=str(payload.get("headRefOid") or ""),
        is_draft=bool(payload.get("isDraft")),
        mergeable=mergeable,
        review_decision=str(payload.get("reviewDecision") or ""),
        required_checks_green=required_green,
    )


def write_exact_head_authorization(
    *,
    repo: str,
    pr: int,
    head_sha: str,
    path: Any = None,
) -> dict[str, Any]:
    entry = write_authorization(
        repo=repo,
        pr=pr,
        reason=REASON,
        source=SOURCE,
        path=path if path is not None else auth_path(""),
    )
    # Re-read and stamp the exact head onto this PR-scoped receipt.
    auth_file = path if path is not None else auth_path("")
    payload = json.loads(auth_file.read_text(encoding="utf-8"))
    for item in payload.get("authorizations", []):
        if (
            isinstance(item, dict)
            and str(item.get("repo")) == repo
            and str(item.get("pr")) == str(pr)
        ):
            item["head_sha"] = head_sha
            item["source"] = SOURCE
    auth_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    entry["head_sha"] = head_sha
    entry["source"] = SOURCE
    return entry


def merge_if_allowed(
    *,
    repo: str,
    pr: int,
    observed_head: str,
    automerge: bool,
    fetch: FetchFn = fetch_pull_request,
    merge_fn: Callable[[str, int], None] | None = None,
    auth_file: Any = None,
) -> dict[str, Any]:
    state = fetch(repo, pr)
    allowed, reasons = evaluate(state, observed_head=observed_head, automerge=automerge)
    result: dict[str, Any] = {
        "allowed": allowed,
        "reasons": reasons,
        "repo": repo,
        "pr": pr,
        "observed_head": observed_head,
        "pr_head": state.head_sha,
        "merged": False,
    }
    if not allowed:
        return result
    write_exact_head_authorization(repo=repo, pr=pr, head_sha=observed_head, path=auth_file)
    if merge_fn is None:
        merge_fn = _gh_squash_merge
    merge_fn(repo, pr)
    result["merged"] = True
    return result


def _gh_squash_merge(repo: str, pr: int) -> None:
    proc = subprocess.run(
        ["gh", "pr", "merge", str(pr), "--repo", repo, "--squash"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "gh pr merge --squash failed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--head", required=True)
    parser.add_argument("--merge", action="store_true")
    parser.add_argument("--auth-file", default="")
    args = parser.parse_args()
    automerge = os.environ.get("PR_AUTOMERGE", "0").strip() == "1"
    if not args.merge:
        state = fetch_pull_request(args.repo, args.pr)
        allowed, reasons = evaluate(state, observed_head=args.head, automerge=automerge)
        print(json.dumps({"allowed": allowed, "reasons": reasons}, indent=2))
        return 0 if allowed else 2
    try:
        result = merge_if_allowed(
            repo=args.repo,
            pr=args.pr,
            observed_head=args.head,
            automerge=automerge,
            auth_file=auth_path(args.auth_file) if args.auth_file else None,
        )
    except RuntimeError as exc:
        print(f"FAIL: bounded automerge: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result["merged"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
