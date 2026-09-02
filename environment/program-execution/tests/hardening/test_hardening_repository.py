"""PE v2 Hardening Counterexamples: Repository Generation Genealogy

Tests that demonstrate v2 advances the repository baseline out from under a
live lease.
"""

import pytest


@pytest.mark.xfail(
    strict=True,
    reason="CE-REPOSITORY-001: v2 advances the repository generation under a live lease",
)
def test_generation_advance_fenced_by_lease():
    """
    v2 Issue: Reconcile recomputes the repository baseline whenever it runs.
    A task holding a lease pinned to the previous generation keeps executing
    against a baseline that no longer exists, and its verification is recorded
    against the new one.

    v3 Requirement: Generation genealogy is explicit and leases are fenced. A
    reconcile that would advance the generation under a live lease is rejected,
    or the lease is revoked before the advance.
    """
    repository = {"generation": 7}
    lease = {"lease_id": "LEASE-001", "generation": 7, "active": True}

    advanced = reconcile(repository, leases=[lease])

    # v2 FAILS: generation moves to 8 with LEASE-001 still pinned to 7
    assert not advanced, "Reconcile must not advance generation under a live lease"


def reconcile(repository: dict, leases: list) -> bool:
    """Mock v2 reconcile - advances unconditionally."""
    # v2: does not consult live leases
    repository["generation"] += 1
    return True
