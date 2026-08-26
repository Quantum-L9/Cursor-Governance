from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, register_contract, run_cli


class DecisionUnknownTest(unittest.TestCase):
    def test_blockers_require_evidence_bound_resolution(self):
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp, with_decision_unknown=True)
            register_contract(temp, workspace)
            view = run_cli("next", "--workspace", str(workspace))
            joined = json.dumps(view)
            self.assertIn("required_decision_not_accepted:DEC-001", joined)
            self.assertIn("blocking_unknown:UNK-001", joined)
            # These are genuine blockers (ADR-0023): the task is blocked, not
            # merely waiting, and both reasons survive in the blockers output.
            blocked = next(item for item in view["blocked"] if item["id"] == "TASK-001")
            self.assertIn("required_decision_not_accepted:DEC-001", blocked["blockers"])
            self.assertIn("blocking_unknown:UNK-001", blocked["blockers"])
            self.assertNotIn("TASK-001", [item["id"] for item in view["waiting"]])
            run_cli(
                "set-decision",
                "DEC-001",
                "accepted",
                "--workspace",
                str(workspace),
                "--evidence-id",
                "EVID-PLAN",
                "--actor",
                "operator",
            )
            run_cli(
                "set-unknown",
                "UNK-001",
                "resolved",
                "--workspace",
                str(workspace),
                "--evidence-id",
                "EVID-PLAN",
                "--actor",
                "operator",
            )
            self.assertEqual(
                [x["id"] for x in run_cli("next", "--workspace", str(workspace))["ready"]],
                ["TASK-001"],
            )


if __name__ == "__main__":
    unittest.main()
