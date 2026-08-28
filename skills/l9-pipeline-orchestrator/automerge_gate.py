#!/usr/bin/env python3
"""Auto-merge gate — deterministic predicate that replaces the human tap before merge.

A PR is ELIGIBLE to auto-merge ONLY when ALL three conditions hold:
  1. ci_green                    — every check run / status is success|neutral|skipped, none pending/failed
  2. review_flags_resolved       — no standing CHANGES_REQUESTED; required approvals met
  3. review_comments_resolved    — all review threads resolved (or outdated) AND remediation_ran == true
                                   (the PR-remediation / autofix loop actually executed)

Input: a PR-state JSON (fetch it with the GitHub MCP tools / gh, then pass the file or pipe stdin).
Output: ELIGIBLE, or BLOCKED with the exact failing condition(s). Exit 0 = eligible, 1 = blocked, 2 = load error.

Determinism lives HERE. The orchestrator session reads this verdict; if ELIGIBLE it performs the merge
(merge_pull_request) and runs `advance.py set <id> merged`. The build session never merges its own work.

Expected PR-state shape (all optional unless noted):
  {
    "pr": 123,
    "check_runs":   [{"name": "...", "conclusion": "success|failure|neutral|skipped|null"}],
    "statuses":     [{"context": "...", "state": "success|failure|pending|error"}],
    "reviews":      [{"state": "APPROVED|CHANGES_REQUESTED|COMMENTED|DISMISSED", "author": "...", "is_bot": false}],
    "review_threads":[{"is_resolved": true, "is_outdated": false, "author": "..."}],
    "required_approvals": 1,
    "remediation_ran": true,
    "mergeable_state": "clean|blocked|behind|dirty|unstable"
  }
"""

import json
import pathlib
import sys

OK_CHECK = {"success", "neutral", "skipped"}
PENDING_CHECK = {None, "", "in_progress", "queued", "pending", "waiting", "action_required"}


def _ci_green(pr):
    reasons = []
    for c in pr.get("check_runs", []):
        concl = c.get("conclusion")
        if concl in PENDING_CHECK:
            reasons.append(f"check '{c.get('name')}' pending")
        elif concl not in OK_CHECK:
            reasons.append(f"check '{c.get('name')}' = {concl}")
    for s in pr.get("statuses", []):
        st = s.get("state")
        if st == "pending":
            reasons.append(f"status '{s.get('context')}' pending")
        elif st not in ("success",):
            reasons.append(f"status '{s.get('context')}' = {st}")
    ms = pr.get("mergeable_state")
    if ms in ("dirty", "blocked", "behind"):
        reasons.append(f"mergeable_state = {ms}")
    return (not reasons), reasons


def _review_flags_resolved(pr):
    reasons = []
    # latest review per author decides; a standing CHANGES_REQUESTED blocks
    latest = {}
    for r in pr.get("reviews", []):
        latest[r.get("author")] = r.get("state")
    changes = [a for a, st in latest.items() if st == "CHANGES_REQUESTED"]
    if changes:
        reasons.append(f"CHANGES_REQUESTED unresolved from: {sorted(changes)}")
    required = pr.get("required_approvals", 0)
    approvals = sum(1 for st in latest.values() if st == "APPROVED")
    if approvals < required:
        reasons.append(f"approvals {approvals} < required {required}")
    return (not reasons), reasons


def _review_comments_resolved(pr):
    reasons = []
    unresolved = [
        t
        for t in pr.get("review_threads", [])
        if not (t.get("is_resolved") or t.get("is_outdated"))
    ]
    if unresolved:
        reasons.append(f"{len(unresolved)} unresolved review thread(s)")
    if not pr.get("remediation_ran", False):
        reasons.append("remediation_ran=false (PR remediation / autofix loop has not run)")
    return (not reasons), reasons


def evaluate(pr):
    conds = {
        "ci_green": _ci_green(pr),
        "review_flags_resolved": _review_flags_resolved(pr),
        "review_comments_resolved": _review_comments_resolved(pr),
    }
    blocked = {k: v[1] for k, v in conds.items() if not v[0]}
    return (len(blocked) == 0), conds, blocked


def main(argv):
    if len(argv) == 2:
        text = pathlib.Path(argv[1]).read_text()
    elif len(argv) == 1 and not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print(__doc__)
        return 2
    try:
        pr = json.loads(text)
    except Exception as e:
        print(f"LOAD ERROR: {e}", file=sys.stderr)
        return 2

    eligible, conds, blocked = evaluate(pr)
    pr_no = pr.get("pr", "?")
    if eligible:
        print(
            f"ELIGIBLE: PR #{pr_no} may auto-merge (ci_green + review_flags_resolved + review_comments_resolved)"
        )
        return 0
    print(f"BLOCKED: PR #{pr_no} NOT eligible to auto-merge", file=sys.stderr)
    for cond, why in blocked.items():
        for r in why:
            print(f"  - {cond}: {r}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
