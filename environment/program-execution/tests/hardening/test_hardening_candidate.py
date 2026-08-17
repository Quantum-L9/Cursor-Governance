"""PE v2 Hardening Counterexamples: Candidate Identity

Tests that demonstrate v2 lacks immutable candidate identity for dirty worktrees.
"""

import pytest


@pytest.mark.xfail(
    strict=True,
    reason="CE-CANDIDATE-001: v2 verifies dirty worktree with HEAD as candidate",
)
def test_dirty_candidate_immutable_identity():
    """
    v2 Issue: Task worktree can be dirty. Verification Receipt carries nullable
    candidate_sha. Dirty content has no immutable identity separate from HEAD.
    
    v3 Requirement: Dirty candidate must get immutable snapshot identity via
    git write-tree technique before verification.
    """
    # Simulate task execution leaving dirty worktree
    task_state = {
        "worktree": "dirty",
        "uncommitted_changes": ["file.py"],
    }
    
    # Submit for verification
    submission = submit_candidate(task_state)
    
    # v2 FAILS: candidate_sha is None or HEAD, not immutable snapshot
    assert submission["candidate_identity"]["snapshot_commit_sha"] is not None
    assert submission["candidate_identity"]["tree_sha"] is not None
    assert submission["candidate_identity"]["working_tree_was_dirty"] is True


@pytest.mark.xfail(
    strict=True,
    reason="CE-CANDIDATE-002: v2 allows candidate mutation between submit and verify",
)
def test_candidate_immutable_after_submission():
    """
    v2 Issue: Worker submits from mutable worktree. Verifier verifies the
    same mutable worktree. Content can change between submission and verification.
    
    v3 Requirement: Submission freezes immutable snapshot S. Verifier verifies
    S in fresh isolated worktree, not worker's mutable worktree.
    """
    # Submit candidate
    submitted = submit_candidate({"content": "version1"})
    submitted_tree_sha = submitted["tree_sha"]
    
    # Worker modifies worktree after submission (v2 allows this)
    modify_worktree({"content": "version2"})
    
    # Verify
    verified = verify_candidate(submitted["candidate_id"])
    
    # v2 FAILS: verified tree != submitted tree
    assert verified["tree_sha"] == submitted_tree_sha


def submit_candidate(state: dict) -> dict:
    """Mock v2 submission - no snapshot freezing."""
    return {
        "candidate_id": "CAND-001",
        "tree_sha": None,  # v2: no immutable snapshot
        "candidate_identity": {"snapshot_commit_sha": None},
    }


def verify_candidate(candidate_id: str) -> dict:
    """Mock v2 verification - verifies mutable worktree."""
    return {"tree_sha": "different"}  # Content changed


def modify_worktree(new_state: dict):
    """Mock worktree mutation."""
    pass
