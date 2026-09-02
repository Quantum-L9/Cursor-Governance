"""PE v2 Hardening Counterexamples: Gate Result Computation

Tests that demonstrate v2 records caller-supplied gate verdicts instead of
computing them from admissible evidence.
"""

import pytest


@pytest.mark.xfail(
    strict=True,
    reason="CE-GATE-001: v2 accepts a caller-supplied PASS as the gate result",
)
def test_gate_result_computed_not_supplied():
    """
    v2 Issue: The gate evaluation payload carries result, verification_method
    and evidence_ids from the caller. The Controller records the supplied
    verdict, so a task can declare its own gate PASS with nothing behind it.

    v3 Requirement: The Controller computes the gate result from admissible
    evidence. Caller-supplied result fields are display metadata at most, and
    a gate with no admissible evidence cannot evaluate to PASS.
    """
    submission = {
        "gate_id": "GATE-001",
        "result": "PASS",
        "verification_method": "command_and_inspection",
        "evidence_ids": [],
    }

    outcome = evaluate_gate(submission, evidence={})

    # v2 FAILS: echoes the supplied PASS despite zero admissible evidence
    assert outcome["result"] != "PASS", "Gate with no evidence cannot pass"


def evaluate_gate(submission: dict, evidence: dict) -> dict:
    """Mock v2 gate evaluation - trusts the caller's verdict."""
    # v2: the supplied result is recorded verbatim
    return {"gate_id": submission["gate_id"], "result": submission["result"]}
