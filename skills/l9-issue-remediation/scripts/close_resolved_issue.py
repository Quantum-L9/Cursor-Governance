#!/usr/bin/env python3
"""Close a GitHub issue that is already resolved — evidence-gated.

Posts the canonical unblock comment (status=fixed) then `gh issue close`.
HUMAN/EXTERNAL require superseded|duplicate|already-fixed|not-reproducible|does-not-exist plus proof.
Never prints tokens. Stdlib + gh CLI.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import post_issue_comment as comment  # noqa: E402

HUMANISH = frozenset({"HUMAN", "EXTERNAL"})
ALLOWED_HUMAN_REASONS = frozenset(
    {"superseded", "duplicate", "already-fixed", "not-reproducible", "does-not-exist"}
)
PROOF_REASONS = frozenset(
    {"superseded", "duplicate", "already-fixed", "not-reproducible", "does-not-exist"}
)


def validate_close(
    *,
    ownership: str,
    status: str,
    reason: str | None,
    merged_pr: str | None,
    commit: str | None,
    proof: str | None,
    on_pr: str | None,
) -> str:
    """Return the resolved reason or raise SystemExit."""
    if status != "fixed":
        raise SystemExit("BLOCKED: close requires --status fixed")
    evidence = merged_pr or commit or proof or on_pr
    if not evidence:
        raise SystemExit(
            "BLOCKED: close requires evidence (--merged-pr, --commit, --on-pr, or --proof)"
        )
    own = (ownership or "").upper()
    if own in HUMANISH:
        if reason not in ALLOWED_HUMAN_REASONS:
            raise SystemExit(
                "BLOCKED: HUMAN/EXTERNAL close requires --reason "
                "superseded|duplicate|already-fixed|not-reproducible|does-not-exist plus proof"
            )
        if not evidence:
            raise SystemExit("BLOCKED: HUMAN/EXTERNAL close requires proof")
    if reason and reason not in PROOF_REASONS:
        raise SystemExit(
            "BLOCKED: --reason must be superseded|duplicate|already-fixed|"
            "not-reproducible|does-not-exist"
        )
    return reason or "already-fixed"


def _gh_close(owner: str, repo: str, number: int) -> None:
    if not shutil.which("gh"):
        raise SystemExit("BLOCKED: gh CLI not found on PATH")
    try:
        subprocess.check_call(
            [
                "gh",
                "issue",
                "close",
                str(number),
                "--repo",
                f"{owner}/{repo}",
                "--reason",
                "completed",
            ],
            timeout=60,
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"BLOCKED: gh issue close failed: {exc}") from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f"BLOCKED: gh issue close error: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", required=True, help="owner/repo#number")
    parser.add_argument("--cluster-id", required=True)
    parser.add_argument("--ownership", required=True)
    parser.add_argument("--owning-repo", required=True)
    parser.add_argument("--change", required=True)
    parser.add_argument("--resume", required=True)
    parser.add_argument("--remaining", default="none")
    parser.add_argument("--cycle", type=int, default=1)
    parser.add_argument("--status", choices=["fixed", "partial", "blocked"], default="fixed")
    parser.add_argument(
        "--reason",
        choices=sorted(PROOF_REASONS),
        help="required for HUMAN/EXTERNAL",
    )
    parser.add_argument("--merged-pr", default="")
    parser.add_argument("--commit", default="")
    parser.add_argument("--on-pr", default="", help="open PR URL that already carries the fix")
    parser.add_argument("--proof", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    owner, repo, number = comment._parse_issue(args.issue)
    ownership = comment._require_safe("ownership", args.ownership)
    resolved_reason = validate_close(
        ownership=ownership,
        status=args.status,
        reason=args.reason,
        merged_pr=args.merged_pr or None,
        commit=args.commit or None,
        proof=args.proof or None,
        on_pr=args.on_pr or None,
    )

    cluster_id = comment._require_safe("cluster-id", args.cluster_id)
    owning_repo = comment._require_safe("owning-repo", args.owning_repo)
    change = comment._require_safe("change", args.change)
    resume = comment._require_safe("resume", args.resume)
    remaining = comment._require_safe("remaining", args.remaining)

    marker = (
        f"<!-- l9-issue-remediation: cluster={cluster_id}; "
        f"cycle={args.cycle}; status={args.status}; close={resolved_reason} -->"
    )
    body = f"""## l9-issue-remediation unblock

**Cluster:** {cluster_id}
**Ownership:** {ownership}
**Owning repo:** {owning_repo}
**Change:** {change}
**Unblocked for resume:** {resume}
**Remaining:** {remaining}

{marker}
"""
    payload = {
        "ok": True,
        "issue": f"{owner}/{repo}#{number}",
        "action": "close",
        "reason": resolved_reason,
        "dry_run": args.dry_run,
    }
    if args.dry_run:
        print(body)
        print(json.dumps(payload))
        return 0

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("BLOCKED: GITHUB_TOKEN or GH_TOKEN required to close issues")

    comment._post_comment(owner, repo, number, body, token)
    _gh_close(owner, repo, number)
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
