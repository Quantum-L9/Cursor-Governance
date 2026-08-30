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
