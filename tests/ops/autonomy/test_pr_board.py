"""pr_board.py must not call an optional red check a blocker, and must find
required checks on a ruleset-only repository.

Each case here is a real observation from the 2026-08-30 nine-repo convergence
run, where the first pass parked six PRs that the second pass merged on the
first attempt.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HELPER = REPO / "ops" / "autonomy" / "pr_board.py"
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import pr_board  # noqa: E402
from pr_board import FIX, LEFTOVER, MERGE, WAIT, board_for, decide, required_checks  # noqa: E402

TARGET = "Quantum-L9/Cursor-Governance"
REQUIRED = ["Lint and Type Check", "Test Suite"]


def _facts(
    *,
    rollup: list[dict],
    required: list[str] | None = None,
    strict: bool = False,
    conflicts: list[str] | None = None,
    merge_state: str = "CLEAN",
    mergeable: str = "MERGEABLE",
    review_decision: str = "APPROVED",
    threads: list[dict] | None = None,
) -> dict:
    return {
        "view": {
            "number": 427,
            "headRefName": "agent/cursor/example",
            "baseRefName": "main",
            "mergeable": mergeable,
            "mergeStateStatus": merge_state,
            "reviewDecision": review_decision,
            "statusCheckRollup": rollup,
            "reviewThreads": {"nodes": threads or []},
        },
        "required": REQUIRED if required is None else required,
        "strict": strict,
        "conflicted_paths": conflicts or [],
    }


def _green() -> list[dict]:
    return [{"name": name, "conclusion": "SUCCESS"} for name in REQUIRED]


def _probe(tmp_path: Path, entry: dict, pr: str = "427") -> str:
    path = tmp_path / "board-probe.json"
    path.write_text(json.dumps({f"{TARGET}#{pr}": entry}), encoding="utf-8")
    return str(path)


def test_optional_red_check_still_merges() -> None:
    """A non-required scanner failing on a bad API key is not a merge blocker."""
    rollup = [*_green(), {"name": "GitGuardian Security Checks", "conclusion": "FAILURE"}]
    verdict = decide(_facts(rollup=rollup, merge_state="UNSTABLE"))
    assert verdict["board"] == MERGE
    assert verdict["failing_required"] == []
    assert "UNSTABLE" in verdict["reason"]


def test_generated_only_conflict_is_work_not_a_wall() -> None:
    verdict = decide(
        _facts(
            rollup=_green(),
            mergeable="CONFLICTING",
            merge_state="DIRTY",
            conflicts=["ops/generated/skill-registry.json"],
        )
    )
    assert verdict["board"] == FIX
    assert verdict["generated_only_conflict"] is True
    assert "regenerate" in verdict["reason"]


def test_source_conflict_names_paths() -> None:
    verdict = decide(
        _facts(
            rollup=_green(),
            mergeable="CONFLICTING",
            merge_state="DIRTY",
            conflicts=["ops/autonomy/pr_board.py"],
        )
    )
    assert verdict["board"] == FIX
    assert verdict["generated_only_conflict"] is False
    assert "ops/autonomy/pr_board.py" in verdict["reason"]


def test_strict_policy_behind_base_is_fix_not_leftover() -> None:
    """Strict required checks plus a stale head means catch up, never park."""
    verdict = decide(_facts(rollup=_green(), strict=True, merge_state="BEHIND"))
    assert verdict["board"] == FIX
    assert "catch up" in verdict["reason"]


def test_pending_required_waits() -> None:
    rollup = [
        {"name": "Lint and Type Check", "conclusion": "SUCCESS"},
        {"name": "Test Suite", "status": "IN_PROGRESS"},
    ]
    verdict = decide(_facts(rollup=rollup, merge_state="BLOCKED"))
    assert verdict["board"] == WAIT
    assert verdict["pending_required"] == ["Test Suite"]


def test_required_context_that_never_reported_waits() -> None:
    """A required context absent from the rollup is expected, not passing."""
    verdict = decide(_facts(rollup=[{"name": "Lint and Type Check", "conclusion": "SUCCESS"}]))
    assert verdict["board"] == WAIT
    assert verdict["pending_required"] == ["Test Suite"]


def test_failing_required_is_fix() -> None:
    rollup = [
        {"name": "Lint and Type Check", "conclusion": "FAILURE"},
        {"name": "Test Suite", "conclusion": "SUCCESS"},
    ]
    verdict = decide(_facts(rollup=rollup, merge_state="BLOCKED"))
    assert verdict["board"] == FIX
    assert verdict["failing_required"] == ["Lint and Type Check"]


def test_leftover_requires_a_declaration() -> None:
    """Leftover is an input backed by evidence, never an inference."""
    rollup = [
        {"name": "Lint and Type Check", "conclusion": "FAILURE"},
        {"name": "Test Suite", "conclusion": "SUCCESS"},
    ]
    facts = _facts(rollup=rollup, merge_state="BLOCKED")
    assert decide(facts)["board"] == FIX
    declared = decide(facts, unfixable_checks=("Lint and Type Check",))
    assert declared["board"] == LEFTOVER
    assert "unfixable without editing CI" in declared["reason"]


def test_named_human_decision_is_leftover() -> None:
    verdict = decide(_facts(rollup=_green()), human_decision="ADR needed for retention window")
    assert verdict["board"] == LEFTOVER
    assert "ADR needed" in verdict["reason"]


def test_human_decision_does_not_park_fixable_conflict() -> None:
    verdict = decide(
        _facts(
            rollup=_green(),
            mergeable="CONFLICTING",
            merge_state="DIRTY",
            conflicts=["ops/autonomy/pr_board.py"],
        ),
        human_decision="ADR needed",
    )
    assert verdict["board"] == FIX
    assert "ops/autonomy/pr_board.py" in verdict["reason"]


def test_review_required_is_leftover_not_fix() -> None:
    verdict = decide(
        _facts(rollup=_green(), merge_state="BLOCKED", review_decision="REVIEW_REQUIRED")
    )
    assert verdict["board"] == LEFTOVER
    assert "required approval" in verdict["reason"]


def test_pinned_app_id_beats_same_named_foreign_check() -> None:
    rollup = [
        {"name": "Lint and Type Check", "conclusion": "SUCCESS", "app_id": "999"},
        {"name": "Lint and Type Check", "conclusion": "FAILURE", "app_id": "42"},
        {"name": "Test Suite", "conclusion": "SUCCESS"},
    ]
    facts = _facts(rollup=rollup, merge_state="BLOCKED")
    facts["required_apps"] = {"Lint and Type Check": "42"}
    verdict = decide(facts)
    assert verdict["board"] == FIX
    assert verdict["failing_required"] == ["Lint and Type Check"]


def test_unresolved_thread_is_fix() -> None:
    verdict = decide(
        _facts(rollup=_green(), merge_state="BLOCKED", threads=[{"isResolved": False}])
    )
    assert verdict["board"] == FIX
    assert verdict["unresolved_threads"] == 1


def test_unprotected_base_with_no_required_checks_merges() -> None:
    """A PR stacked on an unprotected agent branch requires nothing.

    Observed on Cursor-Governance #426 and #427, whose bases are agent branches
    carrying neither a ruleset nor branch protection. Calling that `wait` would
    invent the blocker this module exists to delete: an empty required set here
    is an answer, because a failed protection probe degrades to WAIT upstream.
    """
    verdict = decide(_facts(rollup=[], required=[], merge_state="CLEAN"))
    assert verdict["board"] == MERGE
    assert "no required check on this base" in verdict["reason"]


def test_blocked_with_no_required_is_still_not_a_merge() -> None:
    blocked = decide(_facts(rollup=[], required=[], merge_state="BLOCKED"))
    assert blocked["board"] == FIX
    assert "unresolved conversation or a missing approval" in blocked["reason"]


def test_no_evidence_at_all_waits() -> None:
    verdict = decide(_facts(rollup=[], required=[], merge_state=""))
    assert verdict["board"] == WAIT
    assert "never merge on unknown" in verdict["reason"]


def test_blocked_with_green_required_is_not_a_merge() -> None:
    """The observed shape when a conversation is unresolved but checks are green."""
    verdict = decide(_facts(rollup=_green(), merge_state="BLOCKED"))
    assert verdict["board"] == FIX
    assert verdict["failing_required"] == []


def test_draft_is_fix() -> None:
    facts = _facts(rollup=_green())
    facts["view"]["isDraft"] = True
    assert decide(facts)["board"] == FIX


def test_unknown_merge_state_waits() -> None:
    verdict = decide(_facts(rollup=_green(), merge_state="UNKNOWN"))
    assert verdict["board"] == WAIT
    assert "not finished computing" in verdict["reason"]


def test_ruleset_only_repo_reports_required_checks(monkeypatch) -> None:
    """The regression that matters: no branch protection, gates in a ruleset.

    Reading protection alone returns zero contexts, and zero contexts reads as
    "nothing is blocking" — which is how an unready PR gets called mergeable.
    """
    rules = [
        {"type": "deletion"},
        {
            "type": "required_status_checks",
            "parameters": {
                "strict_required_status_checks_policy": True,
                "required_status_checks": [
                    {"context": "Ruff Lint & Format"},
                    {"context": "Static Analysis"},
                    {"context": "Pure Python Tests"},
                ],
            },
        },
    ]

    def fake_gh(args: list[str]):
        if args[0] == "api" and "/rules/branches/" in args[1]:
            return rules
        if args[0] == "api" and "/protection" in args[1]:
            raise RuntimeError("HTTP 404: Branch not protected")
        raise AssertionError(f"unexpected gh call: {args}")

    monkeypatch.setattr(pr_board, "_gh_json", fake_gh)
    contexts, strict = required_checks("cryptoxdog/IB-Odoo_19", "Staging")
    assert contexts == ["Ruff Lint & Format", "Static Analysis", "Pure Python Tests"]
    assert strict is True


def test_workflows_rule_paths_are_collected() -> None:
    """Org ruleset 21895545 shape: a required *workflow*, not a named context.

    Observed 2026-09-01 on the Quantum-L9 convergence run: the board reported
    `required_checks: []` on repos gated by the org-ci workflows rule, and the
    BLOCKED reason blamed reviews instead of the unrun required workflow.
    """
    rules = [
        {"type": "deletion"},
        {
            "type": "workflows",
            "parameters": {
                "do_not_enforce_on_create": True,
                "workflows": [
                    {
                        "repository_id": 1285564308,
                        "path": ".github/workflows/org-ci.yml",
                        "ref": "refs/heads/main",
                    }
                ],
            },
        },
    ]
    assert pr_board.ruleset_required_workflows(rules) == [
        {"path": ".github/workflows/org-ci.yml", "repository_id": "1285564308"}
    ]


def test_unmatched_required_workflow_blocked_is_pending_not_reviews() -> None:
    """BLOCKED + a workflows rule the probe could not match = pending workflow."""
    facts = _facts(rollup=_green(), merge_state="BLOCKED")
    facts["required_workflows"] = [".github/workflows/org-ci.yml"]
    verdict = decide(facts)
    assert verdict["board"] == WAIT
    assert "org-ci.yml" in verdict["reason"]
    assert "unresolved conversation" not in verdict["reason"]
    assert verdict["pending_workflows"] == [".github/workflows/org-ci.yml"]


def test_matched_required_workflow_failing_job_is_fix() -> None:
    rollup = [
        *_green(),
        {
            "name": "Analyze (central Core)",
            "conclusion": "FAILURE",
            "workflowName": "L9 Org CI",
        },
    ]
    facts = _facts(rollup=rollup, merge_state="BLOCKED")
    facts["required_workflows"] = [".github/workflows/org-ci.yml"]
    facts["required_workflow_names"] = {".github/workflows/org-ci.yml": "L9 Org CI"}
    verdict = decide(facts)
    assert verdict["board"] == FIX
    assert "Analyze (central Core)" in verdict["reason"]
    assert verdict["failing_workflow_jobs"] == {
        ".github/workflows/org-ci.yml": ["Analyze (central Core)"]
    }


def test_same_named_optional_red_does_not_override_required_green() -> None:
    """Display-name collision: required SUCCESS + optional FAILURE → keep SUCCESS."""
    rollup = [
        {
            "name": "Analyze (central Core)",
            "conclusion": "SUCCESS",
            "workflowName": "L9 Org CI",
        },
        {
            "name": "Analyze (central Core)",
            "conclusion": "FAILURE",
            "workflowName": "L9 Org CI",
        },
    ]
    facts = _facts(rollup=rollup, required=[], merge_state="UNSTABLE")
    facts["required_workflows"] = [".github/workflows/org-ci.yml"]
    facts["required_workflow_names"] = {".github/workflows/org-ci.yml": "L9 Org CI"}
    verdict = decide(facts)
    assert verdict["board"] == MERGE
    assert verdict["failing_workflow_jobs"] == {}


def test_unfixable_declaration_covers_required_workflow_job() -> None:
    rollup = [
        {
            "name": "Analyze (central Core)",
            "conclusion": "FAILURE",
            "workflowName": "L9 Org CI",
        }
    ]
    facts = _facts(rollup=rollup, required=[], merge_state="BLOCKED")
    facts["required_workflows"] = [".github/workflows/org-ci.yml"]
    facts["required_workflow_names"] = {".github/workflows/org-ci.yml": "L9 Org CI"}
    assert decide(facts)["board"] == FIX
    leftover = decide(facts, unfixable_checks=(".github/workflows/org-ci.yml",))
    assert leftover["board"] == LEFTOVER
    assert "unfixable without editing CI" in leftover["reason"]


def test_branch_rules_non_list_is_board_error(monkeypatch) -> None:
    def fake_gh(_args: list[str]):
        return {"message": "Not Found"}

    monkeypatch.setattr(pr_board, "_gh_json", fake_gh)
    try:
        pr_board._branch_rules(TARGET, "main")
        raise AssertionError("expected BoardError")
    except pr_board.BoardError as exc:
        assert "non-list" in str(exc)


def test_matched_required_workflow_pending_job_waits() -> None:
    rollup = [
        *_green(),
        {
            "name": "Analyze (central Core)",
            "status": "IN_PROGRESS",
            "workflowName": "L9 Org CI",
        },
    ]
    facts = _facts(rollup=rollup, merge_state="BLOCKED")
    facts["required_workflows"] = [".github/workflows/org-ci.yml"]
    facts["required_workflow_names"] = {".github/workflows/org-ci.yml": "L9 Org CI"}
    verdict = decide(facts)
    assert verdict["board"] == WAIT
    assert verdict["pending_workflows"] == [".github/workflows/org-ci.yml"]


def test_satisfied_workflow_merge_reason_never_claims_unprotected_base() -> None:
    rollup = [
        {
            "name": "Analyze (central Core)",
            "conclusion": "SUCCESS",
            "workflowName": "L9 Org CI",
        }
    ]
    facts = _facts(rollup=rollup, required=[], merge_state="UNSTABLE")
    facts["required_workflows"] = [".github/workflows/org-ci.yml"]
    facts["required_workflow_names"] = {".github/workflows/org-ci.yml": "L9 Org CI"}
    verdict = decide(facts)
    assert verdict["board"] == MERGE
    assert "no required check on this base" not in verdict["reason"]
    assert "org-ci.yml" in verdict["reason"]


def test_unmatched_workflow_on_merge_ready_state_still_merges() -> None:
    """UNSTABLE means GitHub itself says required gates are green; an unmatched
    workflow must not invent a wait, only rewrite the unprotected-base reason."""
    facts = _facts(rollup=[], required=[], merge_state="UNSTABLE")
    facts["required_workflows"] = [".github/workflows/org-ci.yml"]
    verdict = decide(facts)
    assert verdict["board"] == MERGE
    assert "no required check on this base" not in verdict["reason"]
    assert "satisfied" not in verdict["reason"]
    assert "rollup unmatched" in verdict["reason"]


def test_both_protection_sources_union_without_duplicates(monkeypatch) -> None:
    def fake_gh(args: list[str]):
        if "/rules/branches/" in args[1]:
            return [
                {
                    "type": "required_status_checks",
                    "parameters": {"required_status_checks": [{"context": "Test Suite"}]},
                }
            ]
        return {
            "required_status_checks": {"contexts": ["Test Suite", "Legacy Gate"], "strict": True}
        }

    monkeypatch.setattr(pr_board, "_gh_json", fake_gh)
    contexts, strict = required_checks(TARGET, "main")
    assert contexts == ["Test Suite", "Legacy Gate"]
    assert strict is True


def test_unknown_telemetry_degrades_to_wait(tmp_path: Path, monkeypatch) -> None:
    probe = tmp_path / "empty.json"
    probe.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("L9_PR_BOARD_PROBE_FILE", str(probe))
    verdict = board_for(TARGET, "427")
    assert verdict["board"] == WAIT
    assert "never merge on unknown" in verdict["reason"]


def test_cli_json_and_receipt(tmp_path: Path) -> None:
    entry = {
        "pr": {
            "number": 427,
            "headRefName": "agent/cursor/example",
            "baseRefName": "main",
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "UNSTABLE",
            "reviewDecision": "APPROVED",
            "statusCheckRollup": [*_green(), {"name": "Optional Scanner", "conclusion": "FAILURE"}],
            "reviewThreads": {"nodes": []},
        },
        "required_checks": REQUIRED,
        "strict": False,
    }
    env = {**os.environ, "L9_PR_BOARD_PROBE_FILE": _probe(tmp_path, entry)}
    proc = subprocess.run(
        [sys.executable, str(HELPER), "--repo", TARGET, "--pr", "427", "--json"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["board"] == MERGE
    receipt = tmp_path / ".l9" / "pr" / "board-427.json"
    assert receipt.is_file()
    assert json.loads(receipt.read_text(encoding="utf-8"))["board"] == MERGE


def test_helper_never_merges() -> None:
    """This module advises. stack_safe_merge.py --run is the only executor."""
    source = HELPER.read_text(encoding="utf-8")
    assert "gh pr merge" not in source
    assert "stack_safe_merge.py --run" in source


# --- GraphQL-refusing surfaces -------------------------------------------
# A model-controlled surface serves REST and 403s GraphQL wholesale. `gh pr
# view` is GraphQL, so the single call that fed the whole ladder took every
# verdict to "telemetry unavailable" -> WAIT: a merge gate no correct action
# could clear. These pin the REST reconstruction that keeps the board computed.

GRAPHQL_403 = (
    "HTTP 403: This GraphQL query is not enabled for this session — only the "
    "pinned set of PR-review operations is served."
)


def _rest_only_gh(pull, *, check_runs=(), runs=(), statuses=(), reviews=()):
    """A gh double that answers REST and refuses every GraphQL entry point."""

    def fake_gh(args: list[str]):
        if args[0] == "pr":
            raise RuntimeError(GRAPHQL_403)
        if args[0] == "api" and args[1] == "graphql":
            raise RuntimeError(GRAPHQL_403)
        endpoint = args[1] if len(args) > 1 else ""
        if endpoint.endswith("/pulls/512"):
            return pull
        if "/pulls/512/reviews" in endpoint:
            return list(reviews)
        if "/check-runs" in endpoint:
            return {"check_runs": list(check_runs)}
        if "/actions/runs" in endpoint:
            return {"workflow_runs": list(runs)}
        if endpoint.endswith("/status"):
            return {"statuses": list(statuses)}
        raise AssertionError(f"unexpected gh call: {args}")

    return fake_gh


_PULL = {
    "number": 512,
    "draft": False,
    "mergeable": True,
    "mergeable_state": "clean",
    "head": {"ref": "feat/x", "sha": "deadbeef"},
    "base": {"ref": "main"},
}


def test_rest_fallback_answers_when_graphql_is_refused(monkeypatch) -> None:
    """The regression: GraphQL 403 must not read as unknown telemetry."""
    monkeypatch.setattr(
        pr_board,
        "_gh_json",
        _rest_only_gh(
            _PULL,
            check_runs=[
                {"name": "Test Suite", "status": "completed", "conclusion": "success"},
            ],
        ),
    )
    view = pr_board._pr_view("Quantum-L9/Cursor-Governance", "512")
    assert view["mergeStateStatus"] == "CLEAN"
    assert view["mergeable"] == "MERGEABLE"
    assert view["headRefOid"] == "deadbeef"
    assert view["baseRefName"] == "main"
    assert view["isDraft"] is False
    assert _rollup_states_of(view) == {"Test Suite": "SUCCESS"}


def _rollup_states_of(view) -> dict:
    return pr_board._rollup_states(view, {})


def test_rest_fallback_running_check_is_pending_not_success(monkeypatch) -> None:
    """No conclusion yet must rank pending; a blank must never read as green."""
    monkeypatch.setattr(
        pr_board,
        "_gh_json",
        _rest_only_gh(
            _PULL,
            check_runs=[
                {"name": "Test Suite", "status": "in_progress", "conclusion": None},
            ],
        ),
    )
    view = pr_board._pr_view("Quantum-L9/Cursor-Governance", "512")
    assert _rollup_states_of(view) == {"Test Suite": "IN_PROGRESS"}
    assert "IN_PROGRESS" in pr_board.PENDING_STATES


def test_rest_fallback_carries_app_identity_and_workflow_name(monkeypatch) -> None:
    """Pinned-app matching and required-workflow matching both need identity."""
    monkeypatch.setattr(
        pr_board,
        "_gh_json",
        _rest_only_gh(
            _PULL,
            check_runs=[
                {
                    "name": "gates",
                    "status": "completed",
                    "conclusion": "success",
                    "app": {"id": 15368},
                    "check_suite": {"id": 77},
                }
            ],
            runs=[{"check_suite_id": 77, "name": "org-ci"}],
        ),
    )
    view = pr_board._pr_view("Quantum-L9/Cursor-Governance", "512")
    node = view["statusCheckRollup"][0]
    assert pr_board._rollup_app_id(node) == "15368"
    assert pr_board._workflow_job_states(view, "org-ci") == {"gates": "SUCCESS"}


def test_rest_fallback_legacy_status_contexts_are_kept(monkeypatch) -> None:
    """Commit statuses are rollup nodes too; dropping them loses a gate."""
    monkeypatch.setattr(
        pr_board,
        "_gh_json",
        _rest_only_gh(_PULL, statuses=[{"context": "semgrep/scan", "state": "success"}]),
    )
    view = pr_board._pr_view("Quantum-L9/Cursor-Governance", "512")
    assert _rollup_states_of(view)["semgrep/scan"] == "SUCCESS"


def test_rest_fallback_conflicting_pull_is_not_mergeable(monkeypatch) -> None:
    """mergeable:false is CONFLICTING, which the ladder turns into FIX."""
    pull = {**_PULL, "mergeable": False, "mergeable_state": "dirty"}
    monkeypatch.setattr(pr_board, "_gh_json", _rest_only_gh(pull))
    view = pr_board._pr_view("Quantum-L9/Cursor-Governance", "512")
    assert view["mergeable"] == "CONFLICTING"
    assert view["mergeStateStatus"] == "DIRTY"


def test_rest_fallback_unknown_mergeable_stays_unknown(monkeypatch) -> None:
    """GitHub computes mergeability async; null must degrade to WAIT, not MERGE."""
    pull = {**_PULL, "mergeable": None, "mergeable_state": "unknown"}
    monkeypatch.setattr(pr_board, "_gh_json", _rest_only_gh(pull))
    view = pr_board._pr_view("Quantum-L9/Cursor-Governance", "512")
    assert view["mergeable"] == "UNKNOWN"
    assert view["mergeStateStatus"] not in pr_board.MERGE_READY_STATES


def test_rest_fallback_changes_requested_survives(monkeypatch) -> None:
    """reviewDecision is a real blocker and REST must still surface it."""
    monkeypatch.setattr(
        pr_board,
        "_gh_json",
        _rest_only_gh(
            _PULL,
            reviews=[
                {"user": {"login": "alice"}, "state": "APPROVED"},
                {"user": {"login": "bob"}, "state": "CHANGES_REQUESTED"},
            ],
        ),
    )
    view = pr_board._pr_view("Quantum-L9/Cursor-Governance", "512")
    assert view["reviewDecision"] == "CHANGES_REQUESTED"


def test_rest_fallback_dismissed_review_clears_that_reviewer(monkeypatch) -> None:
    """A dismissed block is the reviewer's latest word, not a standing wall."""
    monkeypatch.setattr(
        pr_board,
        "_gh_json",
        _rest_only_gh(
            _PULL,
            reviews=[
                {"user": {"login": "bob"}, "state": "CHANGES_REQUESTED"},
                {"user": {"login": "bob"}, "state": "DISMISSED"},
            ],
        ),
    )
    view = pr_board._pr_view("Quantum-L9/Cursor-Governance", "512")
    assert view["reviewDecision"] == ""


def test_both_transports_dead_is_still_a_board_error(monkeypatch) -> None:
    """Fail closed: no telemetry at all must never become a merge."""

    def dead_gh(args: list[str]):
        raise RuntimeError("gh not on PATH")

    monkeypatch.setattr(pr_board, "_gh_json", dead_gh)
    try:
        pr_board._pr_view("Quantum-L9/Cursor-Governance", "512")
    except pr_board.BoardError as exc:
        assert "REST fallback failed" in str(exc)
    else:
        raise AssertionError("dead telemetry must raise BoardError")


def test_protection_403_is_a_silent_source_not_lost_telemetry(monkeypatch) -> None:
    """An App token cannot read classic protection; rulesets still answer.

    Failing closed here parked every PR in the repo on a token scope. The
    BLOCKED backstop above is what keeps that safe, not the protection read.
    """
    rules = [
        {
            "type": "required_status_checks",
            "parameters": {"required_status_checks": [{"context": "Test Suite"}]},
        }
    ]

    def fake_gh(args: list[str]):
        if args[0] == "api" and "/rules/branches/" in args[1]:
            return rules
        if args[0] == "api" and "/protection" in args[1]:
            raise RuntimeError("gh: Resource not accessible by integration (HTTP 403)")
        raise AssertionError(f"unexpected gh call: {args}")

    monkeypatch.setattr(pr_board, "_gh_json", fake_gh)
    contexts, strict = required_checks("Quantum-L9/Cursor-Governance", "main")
    assert contexts == ["Test Suite"]
    assert strict is False


def test_protection_probe_real_break_still_fails_closed(monkeypatch) -> None:
    """A 500 or a network fault is unknown telemetry and must still raise."""

    def fake_gh(args: list[str]):
        if args[0] == "api" and "/rules/branches/" in args[1]:
            return []
        raise RuntimeError("HTTP 500: Internal Server Error")

    monkeypatch.setattr(pr_board, "_gh_json", fake_gh)
    try:
        pr_board.protection_required("Quantum-L9/Cursor-Governance", "main")
    except pr_board.BoardError:
        pass
    else:
        raise AssertionError("a broken protection probe must raise BoardError")
