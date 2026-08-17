"""PE v2 Hardening Counterexamples: Compiler Semantic Loss

Tests that demonstrate v2 compiler semantic drift - source semantics
that are dropped or misbind during compilation.
"""

import pytest


@pytest.mark.xfail(
    strict=True,
    reason="CE-COMPILER-001: v2 compiler drops retry_policy from source",
)
def test_retry_policy_preserved():
    """
    v2 Issue: Campaign Source contains retry_policy with max_attempts,
    retryable/nonretryable classifications. Compiler emits Blueprint
    without these semantics.
    
    v3 Requirement: Semantic model must represent and preserve retry policy.
    Compilation must fail if retry policy cannot be represented.
    """
    # This test will PASS in v3 (xfail removed), FAIL in v2
    source = {
        "retry_policy": {
            "max_attempts": 2,
            "retryable_classifications": ["temp_adapter_failure"],
        }
    }
    
    # Mock compilation
    blueprint = compile_source_to_blueprint(source)
    
    # v2 FAILS: retry_policy absent
    assert "retry_policy" in blueprint
    assert blueprint["retry_policy"]["max_attempts"] == 2


@pytest.mark.xfail(
    strict=True,
    reason="CE-COMPILER-002: v2 uses first_target shortcut for authority binding",
)
def test_first_target_binding():
    """
    v2 Issue: Compiler uses first_target for authority/workstream/traceability
    placement rather than exact binding from source semantics.
    
    v3 Requirement: Authority binding must be exact from source, not inferred
    from target list order.
    """
    source = {
        "authorities": [
            {"id": "AUTH-001", "scope": ["TARGET-002"]},
        ],
        "targets": [
            {"id": "TARGET-001"},
            {"id": "TARGET-002"},
        ],
    }
    
    blueprint = compile_source_to_blueprint(source)
    
    # v2 FAILS: binds to TARGET-001 (first)
    auth = blueprint["authorities"][0]
    assert auth["scope"] == ["TARGET-002"]


def compile_source_to_blueprint(source: dict) -> dict:
    """Mock compiler - v2 behavior drops semantics."""
    # Simulate v2: drops retry_policy, uses first_target
    return {
        "authorities": [
            {"id": "AUTH-001", "scope": [source["targets"][0]["id"]]}
        ]
        if "targets" in source
        else [],
    }
