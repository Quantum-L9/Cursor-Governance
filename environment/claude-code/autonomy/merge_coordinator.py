"""Exact-SHA merge eligibility gate for PR-convergence campaigns."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MergeEvidence:
    pr_number: int
    expected_head_sha: str
    current_head_sha: str
    required_checks: dict[str, str] = field(default_factory=dict)
    merge_conflicts: bool = False
    blocking_review_threads: int = 0
    dependencies_merged: bool = True
    local_validation_passed: bool = False
    proof_bundle_complete: bool = False
    branch_protection_satisfied: bool = False


@dataclass(frozen=True, slots=True)
class MergeDecision:
    eligible: bool
    reasons: tuple[str, ...]


def evaluate_merge(evidence: MergeEvidence) -> MergeDecision:
    reasons: list[str] = []
    if not evidence.expected_head_sha or evidence.expected_head_sha != evidence.current_head_sha:
        reasons.append("head_sha_mismatch_or_missing")
    non_success = {
        name: conclusion
        for name, conclusion in evidence.required_checks.items()
        if conclusion != "success"
    }
    if not evidence.required_checks:
        reasons.append("required_checks_missing")
    elif non_success:
        reasons.append(
            "required_checks_not_green:"
            + ",".join(f"{name}={value}" for name, value in sorted(non_success.items()))
        )
    if evidence.merge_conflicts:
        reasons.append("merge_conflicts_present")
    if evidence.blocking_review_threads:
        reasons.append(f"blocking_review_threads={evidence.blocking_review_threads}")
    if not evidence.dependencies_merged:
        reasons.append("dependencies_not_merged")
    if not evidence.local_validation_passed:
        reasons.append("local_validation_not_passed")
    if not evidence.proof_bundle_complete:
        reasons.append("proof_bundle_incomplete")
    if not evidence.branch_protection_satisfied:
        reasons.append("branch_protection_not_satisfied")
    return MergeDecision(not reasons, tuple(reasons))
