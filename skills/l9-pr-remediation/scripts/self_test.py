#!/usr/bin/env python3
"""Contract tests for l9-pr-remediation 5.0.0. Stdlib only.

Structural and wiring checks: every link resolves, every deterministic owner
the pack names exists, the pre-v5 contradictions stay gone, and the pack never
re-acquires a campaign, admission-token, or lane-count dependency. Behavioral
coverage of the fleet planner lives in tests/ops/autonomy/test_pr_fleet.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[3]
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
REFS = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / "references").glob("*.md")}
PACK = "\n".join([SKILL, *REFS.values()])

OWNERS = (
    "ops/autonomy/pr_fleet.py",
    "ops/autonomy/pr_board.py",
    "ops/autonomy/stack_safe_merge.py",
    "ops/autonomy/merge_gate.py",
    "ops/autonomy/authorize_merge.py",
    "ops/autonomy/execution_profile.py",
    "ops/scripts/lib/gh_subscribe_pr.sh",
    "environment/agents/cursor-subagents/DELEGATION_CONTRACT.yaml",
    "environment/agents/cursor-subagents/schemas/cursor-subagent-result.schema.json",
    "environment/agents/cursor-subagents/result_bridge.py",
    "environment/agents/results/gateway.py",
    "environment/contracts/autonomy/MANIFEST.yaml",
    "skills/l9-issue-remediation/SKILL.md",
    "tests/ops/autonomy/test_pr_fleet.py",
)

#: Pre-v5 text that re-introduced a contradiction or a dead dependency.
STALE = (
    "mint_admission",
    "L9_ADMISSION_TOKEN",
    "the public local gate **is** `pr-check`",
    "Raw `git push` when Makefile `pr` exists",
    "PUBLIC verbs recorded when a Makefile exists (`pr-check`",
    "every 15s (cap `max_wait_snapshots`)",
    "PR **not merged**",
    "gh run watch",
    "8 minutes",
    "HUMAN / CI_PIPELINE leftovers still stop that PR",
    "Only `CI_PIPELINE` / `HUMAN` / `ENVIRONMENT` blockers remain",
    "leave true human-decision threads open",
    "except open HUMAN decisions",
    "Lazy: only if configured **and** check failing",
)


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        _fail(f"{where} missing required string: {needle!r}")


def _forbid(text: str, needle: str, where: str) -> None:
    if needle in text:
        _fail(f"{where} contains forbidden string: {needle!r}")


def test_frontmatter_and_map() -> None:
    _need(SKILL, "version: 5.0.0", "SKILL.md")
    _need(SKILL, "disable-model-invocation: true", "SKILL.md")
    match = re.search(r"^description: (.+)$", SKILL, re.M)
    if match is None or not (150 <= len(match.group(1)) <= 500):
        _fail("SKILL.md description must be 150-500 characters")
    _need(match.group(1), "use when", "SKILL.md description")
    for name in (
        "run-contract.md",
        "fleet-waves.md",
        "diagnose-workflow.md",
        "remediation-plan.md",
        "finding-classifier.md",
        "fix-engine.md",
        "convergence-loop.md",
        "ownership-boundary.md",
        "merge-advise.md",
        "issue-handoff.md",
        "code-review-agents.md",
        "generated-heal.md",
        "review-replies.md",
        "signal-ingestion.md",
        "validation-gates.md",
        "sonarcloud-remediation.md",
        "codeql-remediation.md",
        "debt-remediation.md",
        "review-angles.md",
    ):
        if name not in REFS:
            _fail(f"references/{name} missing")
        _need(SKILL, f"references/{name}", "SKILL.md resource map")
    scripts = (
        "self_test.py",
        "reply_threads.py",
        "sonar_fetch.py",
        "codeql_fetch.py",
        "debt_audit.py",
    )
    for script in scripts:
        if not (ROOT / "scripts" / script).is_file():
            _fail(f"scripts/{script} missing")
    if not (ROOT / "agents" / "meta.yaml").is_file():
        _fail("agents/meta.yaml missing")
    if (ROOT / "scripts" / "fixtures").exists():
        _fail("scripts/fixtures is dead weight; fleet fixtures live in tests/ops/autonomy")


def test_links_resolve() -> None:
    for name, text in {"SKILL.md": SKILL, **REFS}.items():
        base = ROOT if name == "SKILL.md" else ROOT / "references"
        for target in re.findall(r"\]\(([^)#]+)\)", text):
            if target.startswith(("http://", "https://")):
                continue
            if not (base / target).exists():
                _fail(f"{name} links to a missing path: {target}")
    for name in REFS:
        if name == "review-angles.md":
            continue
        _need(REFS[name], "L9_META", f"references/{name}")


def test_owners_exist_and_are_named() -> None:
    for rel in OWNERS:
        if not (REPO / rel).exists():
            _fail(f"deterministic owner missing on disk: {rel}")
    for rel in (
        "ops/autonomy/pr_fleet.py",
        "ops/autonomy/pr_board.py",
        "ops/autonomy/stack_safe_merge.py",
        "ops/autonomy/authorize_merge.py",
        "ops/autonomy/execution_profile.py",
        "environment/agents/cursor-subagents/DELEGATION_CONTRACT.yaml",
        "environment/contracts/autonomy/MANIFEST.yaml",
    ):
        _need(SKILL, rel, "SKILL.md")
    board = (REPO / "ops/autonomy/pr_board.py").read_text(encoding="utf-8")
    _need(board, "rules/branches", "pr_board.py")
    _need(board, "/protection", "pr_board.py")
    _forbid(board, "gh pr merge", "pr_board.py")
    fleet = (REPO / "ops/autonomy/pr_fleet.py").read_text(encoding="utf-8")
    for needle in (
        "claim_scopes_conflict",
        "execution_profile",
        "validate_result_against_assignment",
        "gateway.accept",
        "is_generated_path",
        "L9_PR_FLEET_PROBE_FILE",
    ):
        _need(fleet, needle, "pr_fleet.py")
    for needle in ("gh pr merge", "mint_admission", "program-execution", "leases.issue"):
        _forbid(fleet, needle, "pr_fleet.py")
    subscribe = (REPO / "ops/scripts/lib/gh_subscribe_pr.sh").read_text(encoding="utf-8")
    _need(subscribe, "updateSubscription", "gh_subscribe_pr.sh")
    _forbid(subscribe, "gh api -X PUT", "gh_subscribe_pr.sh")
    reply = (ROOT / "scripts" / "reply_threads.py").read_text(encoding="utf-8")
    reply_needles = (
        "GH_TIMEOUT_SEC = 30",
        "addPullRequestReviewThreadReply",
        "flush=True",
        "inspected",
    )
    for needle in reply_needles:
        _need(reply, needle, "reply_threads.py")
    sonar = (ROOT / "scripts" / "sonar_fetch.py").read_text(encoding="utf-8")
    _need(sonar, "SONAR_TOKEN", "sonar_fetch.py")
    _forbid(sonar, "require_trusted(", "sonar_fetch.py")
    for helper in ("sonar_fetch.py", "codeql_fetch.py", "debt_audit.py"):
        _need((ROOT / "scripts" / helper).read_text(encoding="utf-8"), "_validated_output", helper)


def test_no_second_plane() -> None:
    for needle in STALE:
        _forbid(PACK, needle, "l9-pr-remediation pack")
    for name in ("SKILL.md", "remediation-plan.md"):
        text = SKILL if name == "SKILL.md" else REFS[name]
        _forbid(text, "pre-commit run --all-files", name)
    for needle in ("max_wait_snapshots", "poll_interval_seconds", "Max 4 total", "max 2 mutation"):
        _forbid(PACK, needle, "l9-pr-remediation pack (lane caps belong to execution_profile.py)")
    _need(SKILL, "concurrency_caps_owner: ops/autonomy/execution_profile.py", "SKILL.md")
    _need(SKILL, "no campaign, no Program Execution", "SKILL.md")
    for word in ("surface_profile.yaml", "lease", "scheduler"):
        if word in SKILL.lower() and "environment/contracts/autonomy" not in SKILL:
            _fail(f"SKILL.md mentions {word!r} without pointing at the canonical owner")


def test_verbs_and_publish() -> None:
    _need(SKILL, "L9_REMEDIATOR=1 PR_BASE=origin/main make precommit-repo", "SKILL.md")
    _need(SKILL, "publish: git push", "SKILL.md")
    _need(SKILL, "do not run `make pr`", "SKILL.md")
    _need(SKILL, "must not invoke `make pr`", "SKILL.md")
    _need(SKILL, "Do not run `make pr-check`", "SKILL.md")
    _need(SKILL, "PR_REMEDIATE=0 make pr", "SKILL.md")
    _need(REFS["run-contract.md"], "L9_REMEDIATOR=1", "run-contract.md")
    _need(REFS["run-contract.md"], 'publish: "git push"', "run-contract.md")
    _need(REFS["fix-engine.md"], "Makefile:precommit-repo", "fix-engine.md")
    _forbid(REFS["fix-engine.md"], "Makefile:pr-check", "fix-engine.md")
    _need(REFS["merge-advise.md"], "already-open PR branch is `git push`", "merge-advise.md")
    _need(
        REFS["signal-ingestion.md"],
        "`make precommit-repo` verify, `git push` publish",
        "signal-ingestion.md",
    )
    _need(SKILL, "require_precommit_all_files: false", "SKILL.md")
    _need(SKILL, "forbid_no_verify: true", "SKILL.md")


def test_fleet_and_waves() -> None:
    _need(SKILL, "pr_fleet.py plan --repo {owner}/{repo} --board --json", "SKILL.md")
    _need(SKILL, "fleet_receipt: .l9/pr/fleet.json", "SKILL.md")
    _need(SKILL, "replan_on: fingerprint_change", "SKILL.md")
    _need(SKILL, "wave_launch: all_ready_non_conflicting", "SKILL.md")
    _need(SKILL, "result_acceptance: pr_fleet.py accept", "SKILL.md")
    _need(SKILL, "in **one** message", "SKILL.md")
    _need(SKILL, "never idles on a background wave", "SKILL.md")
    _need(SKILL, "Results are documents, not sentences", "SKILL.md")
    _need(SKILL, "l9.cursor-subagent.result.v1", "SKILL.md")
    _need(REFS["run-contract.md"], "P_fleet", "run-contract.md")
    _need(REFS["run-contract.md"], "pr_fleet.py plan", "run-contract.md")
    waves = REFS["fleet-waves.md"]
    for needle in (
        "claim_scopes_conflict",
        "pr_fleet.py assign",
        "pr_fleet.py accept",
        "ACCEPTED_INCOMPLETE",
        "REJECTED",
        "l9-pr-remediation",
        "l9-recon",
        "execution_profile.py",
        "never states a number",
    ):
        _need(waves, needle, "fleet-waves.md")
    _need(REFS["fix-engine.md"], "pr_fleet.py plan", "fix-engine.md")
    _need(REFS["convergence-loop.md"], "pr_fleet.py assign --kind watch", "convergence-loop.md")
    _need(REFS["issue-handoff.md"], "above_paygrade_handoff", "issue-handoff.md")
    _need(REFS["issue-handoff.md"], "not a sixth Cursor role", "issue-handoff.md")


def test_board_and_merge() -> None:
    for needle in (
        "board_authority: ops/autonomy/pr_board.py",
        "board_values: [merge, fix, wait, leftover]",
        "leftover_requires_declaration: true",
        "done_predicate: open_prs=0",
        "The board is computed, not judged",
        "ownership is not the board",
        "--human-decision",
        "--unfixable-check",
        "FIRST_MERGE_GATE",
        "MERGE_TRAIN",
        "REMEDIATE_ALL",
        "oldest_created_at_default: true",
        "stack_safe_merge.py --run",
        "never `gh pr update-branch`",
        "is merge authorization",
        "merge_on_converge: true",
        "isResolved: false",
        "any author",
        "Paginate threads",
        "Never add `continue-on-error`",
        "Poll workers and watchers never merge",
        "Never finish with",
        "forbid_reinvoke_handoff: true",
    ):
        _need(SKILL, needle, "SKILL.md")
    if "not merge authorization" in SKILL.lower() or "never merge authorization" in SKILL.lower():
        _fail("SKILL.md must not negate merge authorization")
    _need(SKILL, "**never** commit/push/merge", "SKILL.md")
    _forbid(REFS["diagnose-workflow.md"], "gh pr merge {number}", "diagnose-workflow.md")
    _need(REFS["diagnose-workflow.md"], "Diagnose never merges", "diagnose-workflow.md")
    _need(REFS["merge-advise.md"], "Never merge", "merge-advise.md")
    _need(REFS["merge-advise.md"], "oldest `createdAt` first", "merge-advise.md")
    _forbid(REFS["merge-advise.md"], "git checkout main", "merge-advise.md")
    _need(REFS["remediation-plan.md"], "board_declaration", "remediation-plan.md")
    _need(REFS["ownership-boundary.md"], "edit axis", "ownership-boundary.md")


def test_sonar_directive() -> None:
    _need(SKILL, "SonarCloud: resolve fully, block never", "SKILL.md")
    _need(SKILL, "merge_blocking: false", "SKILL.md")
    _need(SKILL, "Always when `sonar-project.properties` exists", "SKILL.md")
    sonar = REFS["sonarcloud-remediation.md"]
    _need(sonar, "## When (always, never blocking)", "sonarcloud-remediation.md")
    _need(sonar, "never paste a token", "sonarcloud-remediation.md")
    _need(REFS["signal-ingestion.md"], "never blocks merge", "signal-ingestion.md")


def test_venv_and_counters() -> None:
    rc = REFS["run-contract.md"]
    venv_needles = (
        "UV_PYTHON",
        "uv python find --system",
        "conda",
        "symlink a failing SSOT venv",
        "ensure_gov_python.sh",
    )
    for needle in venv_needles:
        _need(rc, needle, "run-contract.md")
    _forbid(rc, "pip install cryptography==", "run-contract.md")
    _need(REFS["ownership-boundary.md"], "## ENVIRONMENT", "ownership-boundary.md")
    for key in (
        "time_to_first_useful_action",
        "blocked_command_attempts",
        "environment_repair_count",
        "ci_run_count",
        "merge_conflict_count",
        "repeated_command_count",
    ):
        _need(SKILL, key, "SKILL.md")
        _need(rc, key, "run-contract.md")


def main() -> None:
    test_frontmatter_and_map()
    test_links_resolve()
    test_owners_exist_and_are_named()
    test_no_second_plane()
    test_verbs_and_publish()
    test_fleet_and_waves()
    test_board_and_merge()
    test_sonar_directive()
    test_venv_and_counters()
    print("l9-pr-remediation self_test: PASS")


if __name__ == "__main__":
    main()
