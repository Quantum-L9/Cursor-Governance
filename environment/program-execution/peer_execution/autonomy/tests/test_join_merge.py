from __future__ import annotations

import unittest

from autonomy.join_controller import evaluate_join
from autonomy.merge_coordinator import MergeEvidence, evaluate_merge

from autonomy.models import (
    ActionRuntime,
    ActionSpec,
    ActionStatus,
    CampaignState,
    JoinBarrier,
)


class JoinAndMergeTests(unittest.TestCase):
    def test_join_requires_proof_and_integration_validation(self) -> None:
        specs = {
            "a": ActionSpec(action_id="a", objective="A"),
            "b": ActionSpec(action_id="b", objective="B"),
        }
        runtime = {
            "a": ActionRuntime(
                status=ActionStatus.VALIDATED,
                proof_bundle={"commit_sha": "1", "validation": "pass"},
            ),
            "b": ActionRuntime(
                status=ActionStatus.VALIDATED,
                proof_bundle={"commit_sha": "2", "validation": "pass"},
            ),
        }
        state = CampaignState("c", "Join", specs, runtime)
        barrier = JoinBarrier(
            join_id="join",
            member_actions=("a", "b"),
            required_proof_keys=("commit_sha", "validation"),
        )
        decision = evaluate_join(
            state,
            barrier,
            conflict_check_passed=True,
            integration_validation_passed=True,
        )
        self.assertTrue(decision.satisfied)
        blocked = evaluate_join(
            state,
            barrier,
            conflict_check_passed=True,
            integration_validation_passed=False,
        )
        self.assertFalse(blocked.satisfied)
        self.assertEqual(blocked.reason, "integration_validation_failed")

    def test_merge_gate_requires_exact_sha_and_all_evidence(self) -> None:
        evidence = MergeEvidence(
            pr_number=42,
            expected_head_sha="abc",
            current_head_sha="abc",
            required_checks={"test": "success", "lint": "success"},
            local_validation_passed=True,
            proof_bundle_complete=True,
            branch_protection_satisfied=True,
        )
        self.assertTrue(evaluate_merge(evidence).eligible)
        stale = MergeEvidence(
            pr_number=42,
            expected_head_sha="abc",
            current_head_sha="def",
            required_checks={"test": "success"},
            local_validation_passed=True,
            proof_bundle_complete=True,
            branch_protection_satisfied=True,
        )
        decision = evaluate_merge(stale)
        self.assertFalse(decision.eligible)
        self.assertIn("head_sha_mismatch_or_missing", decision.reasons)


if __name__ == "__main__":
    unittest.main()
