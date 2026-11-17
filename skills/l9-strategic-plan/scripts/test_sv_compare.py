import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

from script_loader import load_sibling

_claims = load_sibling("compare_sv_claims")
ClaimBlocked = _claims.ClaimBlocked
compare = _claims.compare
fixture = load_sibling("test_sv_assessment").fixture


def alternatives():
    a = fixture()
    a["action_ref"] = "A"
    b = copy.deepcopy(a)
    b["action_ref"] = "B"
    b["effects"][0]["amount"] = "90"
    b["declared_components"]["SFV"] = "90"
    b["declared_sv"] = "70"
    return [a, b]


class ComparisonTests(unittest.TestCase):
    def test_declared_ranking(self):
        out = compare(alternatives())
        self.assertEqual(out["unique_preferred_if_all_resolved"], "A")
        self.assertEqual(out["status"], "DECLARED_VALUES_ONLY_NOT_NUMERICALLY_ATTESTED")

    def test_tie_frontier_no_arbitrary_winner(self):
        a, b = alternatives()
        b["effects"][0]["amount"] = "100"
        b["declared_components"]["SFV"] = "100"
        b["declared_sv"] = "80"
        out = compare([a, b])
        self.assertEqual(out["frontier_if_all_resolved"], ["A", "B"])
        self.assertIsNone(out["unique_preferred_if_all_resolved"])

    def test_unknown_alternative_withholds_winner(self):
        a, b = alternatives()
        b.pop("counterfactual_identification_ref")
        out = compare([a, b])
        self.assertIsNone(out["unique_preferred_if_all_resolved"])
        self.assertEqual(len(out["unresolved_actions"]), 1)

    def test_infeasible_excluded_not_unknown(self):
        a, b = alternatives()
        b["feasibility"] = "blocked"
        out = compare([a, b])
        self.assertEqual(out["unique_preferred_if_all_resolved"], "A")
        self.assertEqual(out["excluded_infeasible_actions"], ["B"])

    def test_incompatible_context_blocks(self):
        a, b = alternatives()
        b["utility_unit"] = "hours"
        with self.assertRaisesRegex(ClaimBlocked, "INCOMPATIBLE"):
            compare([a, b])

    def test_duplicate_ref_blocks(self):
        a, b = alternatives()
        b["action_ref"] = "A"
        with self.assertRaisesRegex(ClaimBlocked, "DUPLICATE_ACTION"):
            compare([a, b])

    def test_fewer_than_two_blocks(self):
        with self.assertRaisesRegex(ClaimBlocked, "TWO_OR_MORE"):
            compare([alternatives()[0]])

    def test_cli_reads_candidates_inside_workdir(self):
        previous = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                os.chdir(temporary)
                Path("claims.json").write_text(json.dumps(alternatives()))
                self.assertEqual(_claims.main(["claims.json"]), 0)
                with self.assertRaises(ValueError):
                    _claims.safe_path("/etc/passwd")
        finally:
            os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
