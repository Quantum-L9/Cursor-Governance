"""PE v2 Hardening Counterexamples: Temporal Authority

Tests that demonstrate v2 validates lease expiry at acquisition only.
"""

import pytest


@pytest.mark.xfail(
    strict=True,
    reason="CE-LEASE-001: v2 checks lease expiry at acquisition, not at use",
)
def test_expired_lease_rejected():
    """
    v2 Issue: Lease expiry is validated when the lease is taken, not when it is
    used. A long-running task keeps writing, verifying and recording receipts
    under a lease whose window closed hours earlier.

    v3 Requirement: Temporal authority is enforced at every use boundary —
    write, verify, receipt, promote — not once at acquisition.
    """
    lease = {"lease_id": "LEASE-001", "acquired_at": 900, "expires_at": 1000}

    accepted = use_lease(lease, now=5000, boundary="write")

    # v2 FAILS: the expired lease is still accepted at the write boundary
    assert not accepted, "Expired lease must be rejected at every use boundary"


def use_lease(lease: dict, now: int, boundary: str) -> bool:
    """Mock v2 lease use - expiry is not re-checked per boundary."""
    # v2: acquisition already succeeded, so every later boundary passes
    return lease["acquired_at"] < lease["expires_at"]
