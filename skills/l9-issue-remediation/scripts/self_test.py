#!/usr/bin/env python3
"""Contract tests for l9-issue-remediation remediator automation. Stdlib only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[3]
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
REFS = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / "references").glob("*.md")}
ISSUES_CMD = (REPO / "commands" / "issues.md").read_text(encoding="utf-8")
_REMEDIATE_PATH = REPO / "commands" / "l9-issue-remediation.md"
if not _REMEDIATE_PATH.is_file():
    _REMEDIATE_PATH = REPO / "commands" / "_archived" / "l9-issue-remediation.md"
REMEDIATE_CMD = _REMEDIATE_PATH.read_text(encoding="utf-8")

sys.path.insert(0, str(ROOT / "scripts"))
import close_resolved_issue  # noqa: E402
import cluster_rank  # noqa: E402
import open_issues_gate  # noqa: E402
import pr_landing  # noqa: E402


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        _fail(f"{where} missing required string: {needle!r}")


def _forbid(text: str, needle: str, where: str) -> None:
    if needle in text:
        _fail(f"{where} contains forbidden string: {needle!r}")


def test_close_gates() -> None:
    try:
        close_resolved_issue.validate_close(
            ownership="HUMAN",
            status="fixed",
            reason=None,
            merged_pr=None,
            commit=None,
            proof=None,
            on_pr=None,
        )
        _fail("HUMAN close without proof should be blocked")
    except SystemExit as exc:
        if "HUMAN/EXTERNAL" not in str(exc) and "evidence" not in str(exc):
            _fail(f"unexpected HUMAN block: {exc}")

    try:
        close_resolved_issue.validate_close(
            ownership="CODEBASE",
            status="partial",
            reason=None,
            merged_pr="https://github.com/org/repo/pull/1",
            commit=None,
            proof=None,
            on_pr=None,
        )
        _fail("partial status must not close")
    except SystemExit as exc:
        if "fixed" not in str(exc):
            _fail(f"unexpected partial block: {exc}")

    reason = close_resolved_issue.validate_close(
        ownership="CODEBASE",
        status="fixed",
        reason=None,
        merged_pr="https://github.com/org/repo/pull/9",
        commit=None,
        proof=None,
        on_pr=None,
    )
    if reason != "already-fixed":
        _fail(f"merged-PR close reason={reason!r}")

    reason = close_resolved_issue.validate_close(
        ownership="HUMAN",
        status="fixed",
        reason="superseded",
        merged_pr="https://github.com/org/repo/pull/9",
        commit=None,
        proof=None,
        on_pr=None,
    )
    if reason != "superseded":
        _fail(f"HUMAN superseded reason={reason!r}")

    reason = close_resolved_issue.validate_close(
        ownership="CODEBASE",
        status="fixed",
        reason="not-reproducible",
        merged_pr=None,
        commit=None,
        proof="gh issue view + rg found no matching defect",
        on_pr=None,
    )
    if reason != "not-reproducible":
        _fail(f"not-reproducible reason={reason!r}")

    reason = close_resolved_issue.validate_close(
        ownership="CODEBASE",
        status="fixed",
        reason="does-not-exist",
        merged_pr=None,
        commit=None,
        proof="claimed path absent from owning repo",
        on_pr=None,
    )
    if reason != "does-not-exist":
        _fail(f"does-not-exist reason={reason!r}")


def test_cluster_rank_shared_cause_first() -> None:
    issues = [
        {
            "id": "Quantum-L9/a#1",
            "repo": "Quantum-L9/a",
            "severity": "low",
            "updated_at": "2026-08-01T00:00:00Z",
            "linked_issues": ["Quantum-L9/b#2"],
            "ownership": "CODEBASE",
        },
        {
            "id": "Quantum-L9/b#2",
            "repo": "Quantum-L9/b",
            "severity": "low",
            "updated_at": "2026-08-02T00:00:00Z",
            "linked_issues": ["Quantum-L9/a#1"],
            "ownership": "CODEBASE",
        },
        {
            "id": "Quantum-L9/c#9",
            "repo": "Quantum-L9/c",
            "severity": "low",
            "updated_at": "2026-01-01T00:00:00Z",
            "linked_issues": [],
            "ownership": "CODEBASE",
        },
    ]
    clusters = cluster_rank.cluster_issues(issues)
    if not clusters:
        _fail("expected clusters")
    top = clusters[0]
    if top.get("issue_count") != 2:
        _fail(f"shared-cause cluster should rank first: {json.dumps(clusters)}")
    if set(top.get("issues") or []) != {"Quantum-L9/a#1", "Quantum-L9/b#2"}:
        _fail(f"top cluster issues unexpected: {top}")


def test_command_open_issues_gate() -> None:
    _forbid(ISSUES_CMD, "Never run Converge", "commands/issues.md")
    _need(ISSUES_CMD, "open_issues == 0", "commands/issues.md")
    _need(ISSUES_CMD, "open_issues_gate.py", "commands/issues.md")
    _need(ISSUES_CMD, "/issues diagnose", "commands/issues.md")
    _need(ISSUES_CMD, "same turn", "commands/issues.md")
    _need(ISSUES_CMD, "never", "commands/issues.md")
    if "Diagnose **never** invokes" not in ISSUES_CMD and "never invokes" not in ISSUES_CMD.lower():
        _fail("commands/issues.md must say Diagnose never invokes /l9-pr-remediation")
    _need(REMEDIATE_CMD, "open_issues=0", "commands/l9-issue-remediation.md")
    _need(REMEDIATE_CMD, "open_issues_gate.py", "commands/l9-issue-remediation.md")
    _forbid(REMEDIATE_CMD, "Diagnose-only stop is required", "commands/l9-issue-remediation.md")


def test_pr_landing() -> None:
    issue = "Quantum-L9/demo#5"
    matching = [
        {
            "number": 12,
            "body": "Fixes #5\n\nIssue remediator",
            "createdAt": "2026-08-01T00:00:00Z",
            "url": "https://github.com/Quantum-L9/demo/pull/12",
            "headRefName": "feat/fix-5",
        },
        {
            "number": 20,
            "body": "unrelated",
            "createdAt": "2026-08-20T00:00:00Z",
            "url": "https://github.com/Quantum-L9/demo/pull/20",
            "headRefName": "feat/other",
        },
    ]
    decision = pr_landing.decide_landing(issue, matching)
    if decision.get("action") != "push_existing" or decision.get("pr") != 12:
        _fail(f"matching open PR should win: {decision}")
    if decision.get("make_pr") is not False:
        _fail("existing PR must not force make pr")

    newest_only = [
        {
            "number": 20,
            "body": "unrelated",
            "createdAt": "2026-08-20T00:00:00Z",
            "headRefName": "feat/other",
        },
        {
            "number": 11,
            "body": "older",
            "createdAt": "2026-08-01T00:00:00Z",
            "headRefName": "feat/old",
        },
    ]
    stacked = pr_landing.decide_landing(issue, newest_only)
    if stacked.get("action") != "stack_new" or stacked.get("base_pr") != 20:
        _fail(f"should stack on newest PR: {stacked}")
    if stacked.get("pr_stack") != "auto":
        _fail(f"stack_new must set PR_STACK=auto: {stacked}")

    first = pr_landing.decide_landing(issue, [])
    if first.get("action") != "first_pr" or first.get("base") != "origin/main":
        _fail(f"empty open PRs should first_pr origin/main: {first}")


def test_open_issues_gate() -> None:
    diagnose = open_issues_gate.may_chain_pr_remediation(0, "diagnose")
    if diagnose.get("chain") is not False:
        _fail("Diagnose must never chain")
    blocked = open_issues_gate.may_chain_pr_remediation(2, "converge")
    if blocked.get("status") != "BLOCKED_OPEN_ISSUES" or blocked.get("chain"):
        _fail(f"open_issues>0 must block: {blocked}")
    human_left = open_issues_gate.may_chain_pr_remediation(1, "converge")
    if human_left.get("chain"):
        _fail("leftover OPEN (including HUMAN) must not chain")
    ok = open_issues_gate.may_chain_pr_remediation(0, "converge")
    if not ok.get("chain") or ok.get("status") != "CHAIN_PR_REMEDIATION":
        _fail(f"open_issues=0 converge must chain: {ok}")


def test_comment_sends_user_agent() -> None:
    src = (ROOT / "scripts" / "post_issue_comment.py").read_text(encoding="utf-8")
    _need(src, "User-Agent", "post_issue_comment.py")
    _need(src, "Quantum-L9-l9-issue-remediation", "post_issue_comment.py")


def test_skill_defaults() -> None:
    _need(SKILL, "max_clusters_per_invoke: all", "SKILL.md")
    _need(SKILL, "chain_pr_remediation: after_open_issues_zero", "SKILL.md")
    _need(SKILL, "make_pr: true", "SKILL.md")
    _need(SKILL, "close_resolved: true", "SKILL.md")
    _need(SKILL, "close_now_same_turn: true", "SKILL.md")
    _need(SKILL, "Close-now law", "SKILL.md")
    _need(REFS["issue-verify.md"], "skill failure", "issue-verify.md")
    _need(REFS["unblock-breadcrumb.md"], "same turn", "unblock-breadcrumb.md")
    _need(SKILL, "verify_before_trust: true", "SKILL.md")
    _need(SKILL, "max_autonomy: until_human_blocker", "SKILL.md")
    _need(SKILL, "recommend_letter: A", "SKILL.md")
    _need(SKILL, "issue-verify.md", "SKILL.md")
    _need(SKILL, "human-blocker-mcq.md", "SKILL.md")
    _need(SKILL, "open_issues=0", "SKILL.md")
    _need(REFS["issue-verify.md"], "Recreate the live issue", "issue-verify.md")
    _need(REFS["human-blocker-mcq.md"], "**A) [RECOMMENDED]**", "human-blocker-mcq.md")
    _need(SKILL, "pr-landing.md", "SKILL.md")
    _need(SKILL, "close_resolved_issue.py", "SKILL.md")
    _need(REFS["handoff-to-pr-remediation.md"], "open_issues == 0", "handoff-to-pr-remediation.md")
    _need(REFS["unblock-breadcrumb.md"], "must not stay OPEN", "unblock-breadcrumb.md")
    _forbid(SKILL, "max_clusters_per_invoke: 1", "SKILL.md")
    _need(REFS["validation-checklist.md"], "/issues diagnose", "validation-checklist.md")
    if "Sticky cluster ≤ 1" in REFS["validation-checklist.md"]:
        _fail("validation-checklist still requires sticky ≤ 1")
    if "delegates Diagnose only" in REFS["validation-checklist.md"]:
        _fail("validation-checklist still says Diagnose only")


def main() -> int:
    test_close_gates()
    test_cluster_rank_shared_cause_first()
    test_command_open_issues_gate()
    test_pr_landing()
    test_open_issues_gate()
    test_comment_sends_user_agent()
    test_skill_defaults()
    print("PASS: l9-issue-remediation self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
