#!/usr/bin/env python3
"""Verify the live branch protection matches the required belt-and-suspenders config.

Run this before the orchestrator relies on native auto-merge: if the branch isn't actually protected
as required, auto-merge could fire on a weaker gate. Fail-closed.

    python verify_branch_protection.py <config.yaml> <live_protection.json>

<live_protection.json> is the response of GET /repos/{owner}/{repo}/branches/{branch}/protection
(fetch via `gh api` or the GitHub MCP). Exit 0 = protection satisfies the config, 1 = gaps, 2 = load error.
"""

import json
import pathlib
import sys


def load(p):
    text = pathlib.Path(p).read_text()
    if str(p).endswith((".yaml", ".yml")):
        import yaml

        return yaml.safe_load(text)
    return json.loads(text)


def verify(cfg, live):
    bp = cfg.get("branch_protection", {})
    gaps = []
    # 1) required status checks: every required context must be present
    want = set((bp.get("required_status_checks") or {}).get("contexts", []))
    got = set(((live.get("required_status_checks") or {}).get("contexts")) or [])
    missing = want - got
    if missing:
        gaps.append(f"missing required status checks: {sorted(missing)}")
    if (bp.get("required_status_checks") or {}).get("strict") and not (
        live.get("required_status_checks") or {}
    ).get("strict"):
        gaps.append("required_status_checks.strict is not enabled")
    # 2) conversation resolution
    if bp.get("required_conversation_resolution") and not (
        live.get("required_conversation_resolution") or {}
    ).get("enabled", live.get("required_conversation_resolution")):
        gaps.append("required_conversation_resolution is not enabled")
    # 3) reviews: count + code-owner
    want_rpr = bp.get("required_pull_request_reviews") or {}
    got_rpr = live.get("required_pull_request_reviews") or {}
    if want_rpr.get("required_approving_review_count", 0) > got_rpr.get(
        "required_approving_review_count", 0
    ):
        gaps.append(
            f"required_approving_review_count < {want_rpr.get('required_approving_review_count')}"
        )
    if want_rpr.get("require_code_owner_reviews") and not got_rpr.get("require_code_owner_reviews"):
        gaps.append("require_code_owner_reviews (agent-as-owner approval) is not enabled")
    return gaps


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    cfg, live = load(argv[1]), load(argv[2])
    gaps = verify(cfg, live)
    if gaps:
        print(
            "BLOCKED: branch protection does NOT satisfy the belt-and-suspenders config:",
            file=sys.stderr,
        )
        for g in gaps:
            print(f"  - {g}", file=sys.stderr)
        return 1
    print(
        "OK: branch protection satisfies the required config (checks + conversation-resolution + code-owner approval)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
