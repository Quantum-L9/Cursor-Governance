from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, cleanup_worktree, prepare_attempt, register_contract, run_cli


class ControllerSuccessTest(unittest.TestCase):
    def test_local_attempt_gate_completion_and_handoff(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            prepare_attempt(temp, workspace)
            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(verification["verdict"], "PASSED_LOCAL")
            evidence_id = verification["evidence_id"]
            run_cli(
                "evaluate-gate",
                "GATE-001",
                "PASS",
                "--workspace",
                str(workspace),
                "--evidence-id",
                evidence_id,
                "--method",
                "independent verification",
                "--actor",
                "controller",
            )
            run_cli(
                "complete",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--actor",
                "operator",
                "--evidence-id",
                evidence_id,
            )
            output = temp / "handoff.json"
            receipt = run_cli(
                "export-handoff",
                "--workspace",
                str(workspace),
                "--actor",
                "operator",
                "--output",
                str(output),
            )
            self.assertEqual(receipt["recommended_program_verdict"], "CONVERGED")
            self.assertEqual(run_cli("validate", "--workspace", str(workspace))["status"], "PASS")
            cleanup_worktree(repo, workspace)


if __name__ == "__main__":
    unittest.main()
