"""PE v2 Hardening Counterexamples: Terminal Verdict Authority

Tests that demonstrate v2 lets a Controller recommendation complete a program,
and refuses INCONCLUSIVE as a terminal verdict.
"""

import pytest


@pytest.mark.xfail(
    strict=True,
    reason="CE-CLOSEOUT-001: v2 lets a Controller handoff terminalize the program",
)
def test_controller_cannot_terminalize():
    """
    v2 Issue: The Controller emits a convergence handoff carrying a
    recommendation, and closeout treats that recommendation as the program's
    terminal verdict. No owner ever renders one.

    v3 Requirement: The Controller recommends; only an owner verdict receipt
    terminalizes a program. A handoff without one leaves the program open.
    """
    handoff = {"recommendation": "CONVERGED", "owner_verdict": None}

    state = close_out(handoff)

    # v2 FAILS: the recommendation alone completes the program
    assert state != "COMPLETE", "Owner verdict is required to terminalize"


@pytest.mark.xfail(
    strict=True,
    reason="CE-CLOSEOUT-002: v2 refuses INCONCLUSIVE as a terminal verdict",
)
def test_inconclusive_is_terminal_verdict():
    """
    v2 Issue: Closeout accepts CONVERGED and FAILED as terminal. An owner who
    renders INCONCLUSIVE — the honest verdict when the evidence cannot decide —
    is rejected, so the program is either forced to a verdict it did not earn
    or left open forever.

    v3 Requirement: INCONCLUSIVE is a first-class terminal verdict. It closes
    execution and records that the evidence did not decide.
    """
    verdict = {"owner_verdict": "INCONCLUSIVE", "rendered_by": "PRINCIPAL-001"}

    accepted = accept_terminal_verdict(verdict)

    # v2 FAILS: INCONCLUSIVE is not in the accepted terminal set
    assert accepted, "INCONCLUSIVE must terminalize execution"


def close_out(handoff: dict) -> str:
    """Mock v2 closeout - promotes the recommendation to a verdict."""
    # v2: recommendation drives completion
    return "COMPLETE" if handoff["recommendation"] == "CONVERGED" else "OPEN"


def accept_terminal_verdict(verdict: dict) -> bool:
    """Mock v2 terminal verdict check - INCONCLUSIVE is not terminal."""
    # v2: only these two terminalize
    return verdict["owner_verdict"] in {"CONVERGED", "FAILED"}
