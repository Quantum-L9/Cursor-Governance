"""PE v2 Hardening Counterexamples: Evidence Admissibility

Tests that demonstrate v2 evidence can be substituted across claims.
"""

import pytest


@pytest.mark.xfail(
    strict=True,
    reason="CE-EVIDENCE-001: v2 allows unrelated evidence to satisfy claim",
)
def test_evidence_claim_scoped():
    """
    v2 Issue: _evidence_valid() checks if evidence exists, is not stale, not expired.
    Does not establish that evidence proves the specific claim consuming it.
    
    v3 Requirement: Evidence admissibility must check subject, content identity,
    claim scope. Cross-claim substitution rejected.
    """
    # Evidence collected for TASK-001 candidate CAND-001
    evidence = {
        "evidence_id": "EVID-001",
        "subject": {"task_id": "TASK-001", "candidate_id": "CAND-001"},
        "result": "PASS",
    }
    
    # Try to use for TASK-002 claim
    claim = {
        "task_id": "TASK-002",
        "candidate_id": "CAND-002",
        "required_evidence": ["EVID-001"],
    }
    
    # v2 FAILS: accepts unrelated evidence
    admissible = admit_evidence(evidence, claim)
    assert not admissible, "Evidence for TASK-001 should not satisfy TASK-002"


@pytest.mark.xfail(
    strict=True,
    reason="CE-EVIDENCE-002: v2 allows FAIL evidence for positive claim",
)
def test_fail_evidence_rejected_for_positive_claim():
    """
    v2 Issue: Evidence validity doesn't check result polarity. FAIL test is
    valid evidence and can satisfy claim.
    
    v3 Requirement: Result polarity semantic. FAIL evidence may prove negative
    path, cannot satisfy "prove gate passes" claim.
    """
    evidence = {
        "evidence_id": "EVID-002",
        "result": "FAIL",
        "claim": "prove_completion_gate_passes",
    }
    
    claim = {"statement": "gate passes", "required_result": "PASS"}
    
    # v2 FAILS: polarity not checked
    admissible = admit_evidence(evidence, claim)
    assert not admissible, "FAIL evidence cannot satisfy PASS claim"


@pytest.mark.xfail(
    strict=True,
    reason="CE-EVIDENCE-003: v2 overwrites verification receipts with INSERT OR REPLACE",
)
def test_evidence_artifacts_immutable():
    """
    v2 Issue: Evidence persistence uses INSERT OR REPLACE. Retry overwrites
    old verification artifact.
    
    v3 Requirement: Evidence artifacts append-only. Retry creates new artifact
    with attempt number. Old artifacts preserved.
    """
    # First attempt verification
    verify_attempt(task_id="TASK-001", attempt=1, result="FAIL")
    
    # Retry - second attempt
    verify_attempt(task_id="TASK-001", attempt=2, result="PASS")
    
    # v2 FAILS: attempt 1 artifact replaced
    artifacts = get_all_verification_artifacts("TASK-001")
    assert len(artifacts) == 2
    assert artifacts[0]["attempt"] == 1
    assert artifacts[1]["attempt"] == 2


def admit_evidence(evidence: dict, claim: dict) -> bool:
    """Mock v2 admissibility - too permissive."""
    # v2: checks exists, not expired, ignores subject/polarity/claim-scope
    return evidence.get("evidence_id") is not None


def verify_attempt(task_id: str, attempt: int, result: str):
    """Mock v2 verification - replaces evidence."""
    pass  # v2: INSERT OR REPLACE


def get_all_verification_artifacts(task_id: str) -> list:
    """Mock retrieval."""
    return [{"attempt": 2}]  # v2: only latest
