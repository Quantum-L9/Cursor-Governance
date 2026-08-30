#!/usr/bin/env python3
"""Hard gate: remediator may chain /l9-pr-remediation only at open_issues=0.

Diagnose never chains. Zero means zero — leftover HUMAN/EXTERNAL blocks.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def may_chain_pr_remediation(open_issue_count: int, intent: str) -> dict:
    intent_norm = (intent or "").strip().lower()
    if intent_norm in {"diagnose", "auditor"}:
        return {
            "chain": False,
            "status": "DIAGNOSE_NO_CHAIN",
            "open_issues": open_issue_count,
            "reason": "diagnose_never_chains",
        }
    if intent_norm not in {"converge", "remediator"}:
        raise SystemExit("BLOCKED: --intent must be converge|remediator|diagnose|auditor")
    if open_issue_count < 0:
        raise SystemExit("BLOCKED: open_issue_count must be >= 0")
    if open_issue_count != 0:
        return {
            "chain": False,
            "status": "BLOCKED_OPEN_ISSUES",
            "open_issues": open_issue_count,
            "reason": "open_issues_not_zero",
        }
    return {
        "chain": True,
        "status": "CHAIN_PR_REMEDIATION",
        "open_issues": 0,
        "reason": "open_issues_zero",
    }


def _count_from_issues_json(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        if "open_issues" in payload:
            return int(payload["open_issues"])
        if "issue_count" in payload:
            return int(payload["issue_count"])
        issues = payload.get("issues") or []
        if isinstance(issues, list):
            return len(issues)
    if isinstance(payload, list):
        return len(payload)
    raise SystemExit("BLOCKED: cannot read open issue count from issues JSON")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--intent",
        required=True,
        choices=["converge", "remediator", "diagnose", "auditor"],
    )
    parser.add_argument("--open-issues", type=int, help="explicit open issue count")
    parser.add_argument("--issues", help="issues.json from issue_ingest.py")
    args = parser.parse_args()
    if args.open_issues is None and not args.issues:
        raise SystemExit("BLOCKED: provide --open-issues or --issues")
    if args.open_issues is not None:
        count = args.open_issues
    else:
        path = Path(args.issues)
        if not path.is_file():
            raise SystemExit(f"BLOCKED: issues file missing: {path}")
        count = _count_from_issues_json(path)
    decision = may_chain_pr_remediation(count, args.intent)
    print(json.dumps(decision))
    return 0 if decision["chain"] or decision["status"] == "DIAGNOSE_NO_CHAIN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
