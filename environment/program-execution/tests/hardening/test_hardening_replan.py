"""PE v2 Hardening Counterexamples: Authorized Work Immutability

Tests that demonstrate v2 replan rewrites tasks that are already executing.
"""

import pytest


@pytest.mark.xfail(
    strict=True,
    reason="CE-REPLAN-001: v2 replan rewrites tasks that are already in flight",
)
def test_replan_cannot_affect_inflight():
    """
    v2 Issue: A replan delta names affected tasks by id without consulting
    their runtime state. A task already EXECUTING under an authorized contract
    has its objective rewritten mid-flight, so the work that lands is not the
    work that was authorized.

    v3 Requirement: Authorized work is immutable once in flight. A delta
    touching a non-future task is rejected; the replan must wait for the task
    to terminalize or supersede it explicitly.
    """
    tasks = {"TASK-001": {"state": "EXECUTING", "objective": "original"}}
    delta = {"affected_task_ids": ["TASK-001"], "objective": "rewritten"}

    applied = apply_replan(tasks, delta)

    # v2 FAILS: the in-flight task is rewritten
    assert not applied, "Replan must not modify an in-flight task"
    assert tasks["TASK-001"]["objective"] == "original"


def apply_replan(tasks: dict, delta: dict) -> bool:
    """Mock v2 replan - applies by id, ignoring runtime state."""
    # v2: no in-flight guard
    for task_id in delta["affected_task_ids"]:
        tasks[task_id]["objective"] = delta["objective"]
    return True
