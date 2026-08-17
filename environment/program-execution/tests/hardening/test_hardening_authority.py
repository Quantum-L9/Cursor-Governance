"""PE v2 Hardening Counterexamples: Authority Binding

Tests that demonstrate v2 uses actor strings instead of principal contexts.
"""

import pytest


@pytest.mark.xfail(
    strict=True,
    reason="CE-AUTHORITY-001: v2 accepts arbitrary approved_by string as authority",
)
def test_actor_string_insufficient():
    """
    v2 Issue: Approval schema accepts approved_by as any nonempty string.
    Controller records it as ledger actor. No principal context, authority grant,
    or expiry enforcement.

    v3 Requirement: PrincipalContext with principal_id, principal_type, authority_grant_ids.
    Actor string is display metadata only, never authority.
    """
    # v2 approval with just string
    approval = {
        "approved_by": "random_string",
        "action": "destructive_operation",
    }

    # Try to perform privileged operation
    authorized = check_authority(approval)

    # v2 FAILS: accepts string
    assert not authorized, "Actor string should not confer authority"


@pytest.mark.xfail(
    strict=True,
    reason="CE-AUTHORITY-002: v2 allows delegation of nondelegable authority",
)
def test_nondelegable_authority_enforced():
    """
    v2 Issue: Campaign source has may_delegate: false, but runtime doesn't
    enforce it. Generic authority string can be passed down.

    v3 Requirement: Authority grant immutable. If may_delegate: false,
    no delegation chain accepted.
    """
    # Authority defined as nondelegable
    authority = {
        "id": "AUTH-001",
        "responsibility": "terminal_verdict",
        "may_delegate": False,
    }

    # Someone tries to delegate
    delegated = {
        "parent_grant": "GRANT-001",
        "delegated_to": "someone_else",
    }

    # v2 FAILS: delegation accepted
    valid = validate_delegation(authority, delegated)
    assert not valid, "Nondelegable authority cannot be delegated"


def check_authority(approval: dict) -> bool:
    """Mock v2 authority check - accepts string."""
    # v2: nonempty string = authorized
    return bool(approval.get("approved_by"))


def validate_delegation(authority: dict, delegation: dict) -> bool:
    """Mock v2 delegation check - doesn't enforce may_delegate."""
    # v2: doesn't check may_delegate
    return True
