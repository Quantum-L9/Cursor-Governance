"""Purpose-built contract falsifiers. They do not authenticate external evidence."""

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

from script_loader import load_sibling

_assessment = load_sibling("check_sv_assessment")
ClaimBlocked = _assessment.ClaimBlocked
check = _assessment.check


def fixture():
    effects = [
        {
            "effect_id": "future-gross",
            "period_ref": "2027-Q1",
            "economic_class": "SFV",
            "accounting_home": "SFV",
            "amount": "100",
            "evidence_refs": ["source:counterfactual-gross"],
        },
        {
            "effect_id": "cost-20",
            "period_ref": "2027-Q1",
            "economic_class": "DC",
            "accounting_home": "DC",
            "amount": "20",
            "evidence_refs": ["source:cost-estimate"],
        },
    ]
    return {
        "schema": "l9.strategic-planner-value-claim/v1",
        "claim_type": "objective_relative_quantitative_strategic_value",
        "objective_ref": "objective:net-value",
        "utility_unit": "USD",
        "baseline_ref": "baseline:feasible-no-action",
        "horizon_ref": "2027",
        "model_revision_ref": "model:v1",
        "evidence_snapshot_ref": "evidence:v1",
        "focal_beneficiary_ref": "actor:A",
        "counterfactual_identification_ref": "study:intervention-vs-control",
        "feasibility": "admissible",
        "feasibility_evidence_refs": ["formal:constraints-pass"],
        "effects": effects,
        "declared_components": {"IEV": "0", "SFV": "100", "DC": "20", "ERL": "0", "OC": "0"},
        "declared_sv": "80",
        "method": {
            "kind": "bounded_scenarios",
            "method_ref": "numeric:scenario-v1",
            "owner": "Numerical Reasoning",
            "probabilistic": False,
        },
        "claim_strength": "declared",
    }


def net_fixture():
    a = fixture()
    a["effects"][1].update(
        accounting_home="SFV",
        amount="-20",
        embedded=True,
        net_flow_coverage_ref="coverage:cost-embedded",
    )
    a["declared_components"].update(SFV="80", DC="0")
    return a


class StrategicValueAssessmentTests(unittest.TestCase):
    def assert_blocked(self, data, reason):
        with self.assertRaisesRegex(ClaimBlocked, reason):
            check(data)

    def test_gross_partition_80(self):
        self.assertEqual(check(fixture())["calculated_sv"], "80")

    def test_reconciled_net_partition_80(self):
        self.assertEqual(check(net_fixture())["calculated_sv"], "80")

    def test_embedded_dc_double_subtraction_rejected(self):
        a = net_fixture()
        a["declared_components"]["DC"] = "20"
        a["declared_sv"] = "60"
        self.assert_blocked(a, "COMPONENT_LEDGER_MISMATCH")

    def test_duplicate_booked_effect_rejected(self):
        a = fixture()
        a["effects"].append(copy.deepcopy(a["effects"][1]))
        self.assert_blocked(a, "DUPLICATE_OR_MISSING_EFFECT_IDENTITY")

    def test_unknown_missing_component_is_not_zero(self):
        a = fixture()
        a["declared_components"].pop("OC")
        self.assert_blocked(a, "EXACT_FIVE_BUCKET")

    def test_falsifier_1_unidentified_counterfactual(self):
        a = fixture()
        a["counterfactual_identification_ref"] = ""
        self.assert_blocked(a, "counterfactual_identification_ref")
        self.assertEqual(check(fixture())["calculated_sv"], "80")

    def test_falsifier_2_unauthorized_actor_welfare(self):
        a = fixture()
        a["cross_actor_utility_material"] = True
        self.assert_blocked(a, "UNAUTHORIZED_CROSS_ACTOR_UTILITY")
        a["welfare_aggregation_ref"] = "owner:welfare-definition"
        self.assertEqual(check(a)["calculated_sv"], "80")

    def test_falsifier_3_future_observation_leakage(self):
        a = fixture()
        a["sequential_policy_material"] = True
        self.assert_blocked(a, "FUTURE_INFORMATION_LEAKAGE")
        a["nonanticipativity_evidence_ref"] = "formal:observation-timing"
        self.assertEqual(check(a)["calculated_sv"], "80")

    def test_falsifier_4_nonadditive_portfolio(self):
        a = fixture()
        a["joint_portfolio_material"] = True
        self.assert_blocked(a, "UNJUSTIFIED_PORTFOLIO_ADDITIVITY")
        a["joint_interaction_model_ref"] = "numeric:joint-constraint-model"
        self.assertEqual(check(a)["calculated_sv"], "80")

    def test_falsifier_5_preference_flips_under_uncertainty(self):
        a = fixture()
        a["preference_reversal_material"] = True
        self.assert_blocked(a, "UNSUPPORTED_PRECISE_WINNER")
        a["sensitivity_evidence_ref"] = "numeric:decision-boundary"
        self.assertEqual(check(a)["calculated_sv"], "80")

    def test_falsifier_6_claimed_verified_without_proof(self):
        a = fixture()
        a["claim_strength"] = "independently_verified"
        self.assert_blocked(a, "VERIFIED_METHOD_CLAIM_WITHOUT_REVIEWABLE_EVIDENCE")
        a["numerical_owner_execution_refs"] = ["numeric:run-v1"]
        a["independent_model_validation_refs"] = ["validation:owner-reviewed"]
        self.assertEqual(check(a)["status"], "DECLARED_INPUT_CONSISTENT_NOT_NUMERICALLY_ATTESTED")

    def test_qv_not_universal_bounded_scenarios_allowed(self):
        self.assertEqual(check(fixture())["calculated_sv"], "80")

    def test_qv_coordinates_required_only_if_qv_selected(self):
        a = fixture()
        a["method"]["kind"] = "qv_lookahead"
        self.assert_blocked(a, "QV_ONLY_METHOD_COORDINATES_MISSING")
        a["method"]["belief_state_refs"] = ["belief:model"]
        a["method"]["bounded_policy_ref"] = "policy:finite-horizon"
        self.assertEqual(check(a)["calculated_sv"], "80")

    def test_other_non_sv_claim_is_out_of_scope(self):
        a = fixture()
        a["claim_type"] = "general_ranking"
        self.assertEqual(check(a)["status"], "NOT_APPLICABLE")

    def test_formally_blocked_is_excluded(self):
        a = fixture()
        a["feasibility"] = "blocked"
        self.assertEqual(check(a)["status"], "INFEASIBLE_EXCLUDED")

    def test_unknown_formal_status_blocks_complete_claim(self):
        a = fixture()
        a["feasibility"] = "unknown"
        self.assert_blocked(a, "UNKNOWN_OR_UNPROVEN_FEASIBILITY")

    def test_missing_numerical_owner_identity_blocks(self):
        a = fixture()
        a["method"]["owner"] = "Strategic Planner"
        self.assert_blocked(a, "NUMERICAL_METHOD_OWNER_OR_ID_MISSING")

    def test_no_fake_forecast_attestation(self):
        a = fixture()
        self.assertTrue(check(a)["requires_owner_evidence_validation"])
        self.assertNotIn("CANONICAL_BINDING_VERIFIED", str(check(a)))

    def test_cli_reads_claim_inside_workdir(self):
        previous = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                os.chdir(temporary)
                Path("claim.json").write_text(json.dumps(fixture()))
                self.assertEqual(_assessment.main(["claim.json"]), 0)
                with self.assertRaises(ValueError):
                    _assessment.safe_path("/etc/passwd")
        finally:
            os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
