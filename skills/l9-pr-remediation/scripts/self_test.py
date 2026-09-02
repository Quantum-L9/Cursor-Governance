#!/usr/bin/env python3
"""Contract tests for l9-pr-remediation 4.5.1. Stdlib only."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
REFS = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / "references").glob("*.md")}
CMD = Path(__file__).resolve().parents[3] / "commands" / "l9-pr-remediation.md"
CMD_TEXT = CMD.read_text(encoding="utf-8") if CMD.is_file() else ""


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        _fail(f"{where} missing required string: {needle!r}")


def _forbid(text: str, needle: str, where: str) -> None:
    if needle in text:
        _fail(f"{where} contains forbidden string: {needle!r}")


def test_version_and_map() -> None:
    _need(SKILL, "version: 4.5.1", "SKILL.md")
    if not (ROOT / "scripts" / "reply_threads.py").is_file():
        _fail("scripts/reply_threads.py missing")
    _need(SKILL, "Kernel bind", "SKILL.md")
    _need(SKILL, "Diagnose First", "SKILL.md")
    _need(SKILL, "Passed` / `Failed` / `Unknown", "SKILL.md")
    _need(SKILL, "references/run-contract.md", "SKILL.md")
    _need(SKILL, "scripts/self_test.py", "SKILL.md")
    _need(SKILL, "references/generated-heal.md", "SKILL.md")
    if "run-contract.md" not in REFS:
        _fail("references/run-contract.md missing")
    if "generated-heal.md" not in REFS:
        _fail("references/generated-heal.md missing")
    if not (ROOT / "agents" / "meta.yaml").is_file():
        _fail("agents/meta.yaml missing")


def test_makefile_surface() -> None:
    _need(SKILL, "make precommit-repo", "SKILL.md")
    _need(SKILL, "merge_on_converge: true", "SKILL.md")
    _need(SKILL, "makefile_primary: precommit-repo", "SKILL.md")
    _need(SKILL, "publish: git push", "SKILL.md")
    _need(SKILL, "make improve", "SKILL.md")
    _need(SKILL, "do not run `make pr`", "SKILL.md")
    _need(SKILL, "must not invoke `make pr`", "SKILL.md")
    _need(SKILL, "not the remediator publish", "SKILL.md")
    _need(SKILL, "make pr-check", "SKILL.md")
    _need(SKILL, "L9_REMEDIATOR=1", "SKILL.md")
    _need(REFS["run-contract.md"], "L9_REMEDIATOR=1", "run-contract.md")
    _need(SKILL, "PR_REMEDIATE=0 make pr", "SKILL.md")
    _need(REFS["run-contract.md"], "make precommit-repo", "run-contract.md")
    _need(REFS["run-contract.md"], "make pr-check", "run-contract.md")
    _need(REFS["run-contract.md"], "PR_REMEDIATE=0 make pr", "run-contract.md")
    _need(REFS["run-contract.md"], 'publish: "git push"', "run-contract.md")
    _need(REFS["fix-engine.md"], "sanctioned publish", "fix-engine.md")
    _need(REFS["remediation-plan.md"], "sanctioned publish", "remediation-plan.md")
    _need(REFS["remediation-plan.md"], "make precommit-repo", "remediation-plan.md")
    _forbid(SKILL, "pre-commit run --all-files", "SKILL.md")
    _forbid(REFS["remediation-plan.md"], "pre-commit run --all-files", "remediation-plan.md")
    _need(SKILL, "require_precommit_all_files: false", "SKILL.md")
    _need(SKILL, "require_precommit_all_hooks: false", "SKILL.md")
    _need(REFS["convergence-loop.md"], "require_precommit_all_hooks: false", "convergence-loop.md")
    _forbid(REFS["fix-engine.md"], "find .github/workflows", "fix-engine.md")
    if "git push (ONE push)" in REFS["fix-engine.md"]:
        _fail("fix-engine.md still instructs git push (ONE push)")
    if "git push origin main" in REFS["merge-advise.md"]:
        _fail("merge-advise.md still instructs git push origin main")
    _need(REFS["run-contract.md"], "git add -u", "run-contract.md")


def test_speed_contract() -> None:
    pack = "\n".join([SKILL, *REFS.values()])
    _forbid(pack, "8 minutes", "l9-pr-remediation pack")
    _forbid(pack, "gh run watch", "l9-pr-remediation pack")
    _forbid(pack, "Local verify is `make pr-check`", "l9-pr-remediation pack")
    _forbid(REFS["convergence-loop.md"], "Wait Protocol", "convergence-loop.md")
    _need(REFS["convergence-loop.md"], "make precommit-repo", "convergence-loop.md")
    _need(REFS["convergence-loop.md"], "merge_on_converge: true", "convergence-loop.md")
    _need(SKILL, "is merge authorization", "SKILL.md")
    if "not merge authorization" in SKILL.lower() or "never merge authorization" in SKILL.lower():
        _fail("SKILL.md must not negate merge authorization")
    if CMD_TEXT:
        _need(CMD_TEXT, "is merge authorization", "commands/l9-pr-remediation.md")


def test_merge_train() -> None:
    _need(SKILL, "FIRST_MERGE_GATE", "SKILL.md")
    _need(SKILL, "MERGE_TRAIN", "SKILL.md")
    _need(SKILL, "REMEDIATE_ALL", "SKILL.md")
    _need(SKILL, "oldest_created_at_default: true", "SKILL.md")
    _need(SKILL, "oldest `createdAt` first", "SKILL.md")
    _need(SKILL, "stack-safe", "SKILL.md")
    _need(REFS["merge-advise.md"], "oldest `createdAt` first", "merge-advise.md")
    _need(REFS["merge-advise.md"], "stack-safe", "merge-advise.md")
    _need(REFS["run-contract.md"], "FIRST_MERGE_GATE", "run-contract.md")
    _need(REFS["run-contract.md"], "oldest `createdAt` first", "run-contract.md")
    _need(REFS["convergence-loop.md"], "FIRST_MERGE_GATE", "convergence-loop.md")
    _forbid(REFS["merge-advise.md"], "git checkout main", "merge-advise.md")
    _need(SKILL, "Never `gh pr update-branch` after a squash of a parent", "SKILL.md")


def test_diagnose_never_merges() -> None:
    _need(SKILL, "**never** commit/push/merge", "SKILL.md")
    _forbid(REFS["diagnose-workflow.md"], "gh pr merge {number}", "diagnose-workflow.md")
    _need(REFS["diagnose-workflow.md"], "Diagnose never merges", "diagnose-workflow.md")
    _need(REFS["merge-advise.md"], "Never merge", "merge-advise.md")


def test_venv() -> None:
    rc = REFS["run-contract.md"]
    _need(rc, "UV_PYTHON", "run-contract.md")
    _need(rc, "ENVIRONMENT", "run-contract.md")
    _need(rc, "uv python find --system", "run-contract.md")
    _need(rc, "conda", "run-contract.md")
    _need(SKILL, "ENVIRONMENT", "SKILL.md")
    _need(REFS["ownership-boundary.md"], "## ENVIRONMENT", "ownership-boundary.md")
    _need(REFS["finding-classifier.md"], "ENVIRONMENT", "finding-classifier.md")
    _forbid(rc, "pip install cryptography==", "run-contract.md")
    _need(rc, "symlink a failing SSOT venv", "run-contract.md")
    _need(rc, ".cursor-commands/.venv", "run-contract.md")
    _need(rc, "ensure_gov_python.sh", "run-contract.md")


def test_no_gate_weakening() -> None:
    _forbid(REFS["convergence-loop.md"], "continue-on-error", "convergence-loop.md")
    _need(SKILL, "Never add `continue-on-error`", "SKILL.md")


def test_conversations() -> None:
    _need(SKILL, "isResolved: false", "SKILL.md")
    _need(SKILL, "any author", "SKILL.md")
    _need(SKILL, "Paginate threads", "SKILL.md")
    _forbid(SKILL, "leave true human-decision threads open", "SKILL.md")
    _forbid(REFS["ownership-boundary.md"], "leave the thread open", "ownership-boundary.md")
    _forbid(REFS["review-replies.md"], "except open HUMAN decisions", "review-replies.md")
    _forbid(REFS["validation-gates.md"], "except open HUMAN decisions", "validation-gates.md")
    _need(REFS["code-review-agents.md"], "isResolved", "code-review-agents.md")
    _need(REFS["review-replies.md"], "hasNextPage", "review-replies.md")
    _need(REFS["review-replies.md"], "HUMAN Deferred", "review-replies.md")
    _need(REFS["review-replies.md"], "reply_threads.py", "review-replies.md")
    _need(REFS["review-replies.md"], "python3 -u", "review-replies.md")
    _need(REFS["review-replies.md"], "inspected: true", "review-replies.md")
    _need(SKILL, "reply_threads.py", "SKILL.md")
    helper = (ROOT / "scripts" / "reply_threads.py").read_text(encoding="utf-8")
    _need(helper, "GH_TIMEOUT_SEC = 30", "reply_threads.py")
    _need(helper, "addPullRequestReviewThreadReply", "reply_threads.py")
    _need(helper, "flush=True", "reply_threads.py")
    _need(helper, "inspected", "reply_threads.py")


def test_fast_path() -> None:
    _need(SKILL, "Min preflight", "SKILL.md")
    _need(REFS["validation-gates.md"], "cited", "validation-gates.md")
    _need(REFS["signal-ingestion.md"], "$PWD", "signal-ingestion.md")
    _need(REFS["signal-ingestion.md"], "make pr-check", "signal-ingestion.md")
    _need(REFS["run-contract.md"], "P_diag", "run-contract.md")
    _need(REFS["diagnose-workflow.md"], "Root cause", "diagnose-workflow.md")
    _forbid(REFS["convergence-loop.md"], "CI SHOULD pass", "convergence-loop.md")
    _need(REFS["finding-classifier.md"], "unverified root cause", "finding-classifier.md")


def test_ci_and_poll() -> None:
    _need(SKILL, "Poll workers never merge", "SKILL.md")
    _need(SKILL, "Own until merged", "SKILL.md")
    _need(SKILL, "subscribe/own", "SKILL.md")
    _need(SKILL, "updateSubscription", "SKILL.md")
    _need(SKILL, "gh_subscribe_pr.sh", "SKILL.md")
    _need(REFS["convergence-loop.md"], "updateSubscription", "convergence-loop.md")
    _need(REFS["convergence-loop.md"], "gh_subscribe_pr.sh", "convergence-loop.md")
    helper = Path(__file__).resolve().parents[3] / "ops" / "scripts" / "lib" / "gh_subscribe_pr.sh"
    if not helper.is_file():
        _fail("ops/scripts/lib/gh_subscribe_pr.sh missing")
    helper_text = helper.read_text(encoding="utf-8")
    _need(helper_text, "updateSubscription", "gh_subscribe_pr.sh")
    if "gh api -X PUT" in helper_text:
        _fail("gh_subscribe_pr.sh must not call PUT issues/subscription")
    _need(SKILL, "own_until_merged: true", "SKILL.md")
    _need(SKILL, "forbid_reinvoke_handoff: true", "SKILL.md")
    _need(REFS["convergence-loop.md"], "Own until merged", "convergence-loop.md")
    _need(REFS["convergence-loop.md"], "viewerSubscription", "convergence-loop.md")
    _need(SKILL, "Never finish with", "SKILL.md")
    _need(REFS["run-contract.md"], "merge_eligible", "run-contract.md")
    _need(REFS["remediation-plan.md"], "companion", "remediation-plan.md")


def test_board_axis() -> None:
    """The board verdict is computed, not judged from an ownership class.

    Reading `statusCheckRollup` (every check, required or not) as a merge
    verdict parked six mergeable PRs on 2026-08-30. The pack must point at the
    helper that resolves required-check identity instead.
    """
    helper = Path(__file__).resolve().parents[3] / "ops" / "autonomy" / "pr_board.py"
    if not helper.is_file():
        _fail("ops/autonomy/pr_board.py missing (board authority)")
    source = helper.read_text(encoding="utf-8")
    _need(source, "rules/branches", "pr_board.py")  # ruleset-protected repos
    _need(source, "/protection", "pr_board.py")  # classic branch protection
    if "gh pr merge" in source:
        _fail("pr_board.py must advise only; stack_safe_merge.py --run executes")

    _need(SKILL, "ops/autonomy/pr_board.py", "SKILL.md")
    _need(SKILL, "board_authority: ops/autonomy/pr_board.py", "SKILL.md")
    _need(SKILL, "board_values: [merge, fix, wait, leftover]", "SKILL.md")
    _need(SKILL, "leftover_requires_declaration: true", "SKILL.md")
    _need(SKILL, "done_predicate: open_prs=0", "SKILL.md")
    _need(SKILL, "The board is computed, not judged", "SKILL.md")
    _need(SKILL, "ownership is not the board", "SKILL.md")
    _need(SKILL, "--human-decision", "SKILL.md")
    _need(SKILL, "--unfixable-check", "SKILL.md")
    _need(REFS["run-contract.md"], "P_board", "run-contract.md")
    _need(REFS["run-contract.md"], "pr_board.py", "run-contract.md")
    _need(REFS["convergence-loop.md"], "pr_board.py", "convergence-loop.md")
    _need(REFS["finding-classifier.md"], "ops/autonomy/pr_board.py", "finding-classifier.md")
    _need(REFS["ownership-boundary.md"], "edit axis", "ownership-boundary.md")
    _need(REFS["remediation-plan.md"], "board_declaration", "remediation-plan.md")

    # The leftover factory: an ownership class read as a PR outcome.
    pack = "\n".join([SKILL, *REFS.values()])
    _forbid(pack, "HUMAN / CI_PIPELINE leftovers still stop that PR", "l9-pr-remediation pack")
    _forbid(pack, "HUMAN / CI_PIPELINE leftovers stop that PR", "l9-pr-remediation pack")
    _forbid(
        REFS["convergence-loop.md"],
        "Only `CI_PIPELINE` / `HUMAN` / `ENVIRONMENT` blockers remain",
        "convergence-loop.md",
    )
    _forbid(REFS["ownership-boundary.md"], "**Do not merge that PR**", "ownership-boundary.md")
    _forbid(REFS["finding-classifier.md"], "do not merge that PR", "finding-classifier.md")


def test_counters() -> None:
    for key in (
        "time_to_first_useful_action",
        "blocked_command_attempts",
        "environment_repair_count",
        "ci_run_count",
        "merge_conflict_count",
        "repeated_command_count",
    ):
        _need(SKILL, key, "SKILL.md")
        _need(REFS["run-contract.md"], key, "run-contract.md")


def main() -> None:
    test_version_and_map()
    test_makefile_surface()
    test_speed_contract()
    test_merge_train()
    test_diagnose_never_merges()
    test_venv()
    test_no_gate_weakening()
    test_conversations()
    test_fast_path()
    test_ci_and_poll()
    test_board_axis()
    test_counters()
    print("l9-pr-remediation self_test: PASS")


if __name__ == "__main__":
    main()
