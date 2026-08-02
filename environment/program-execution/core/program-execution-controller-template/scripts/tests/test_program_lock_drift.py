from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, register_contract, run_cli


class ProgramLockDriftTest(unittest.TestCase):
    def test_claim_rejects_blueprint_source_drift_without_manual_validation(self):
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            blueprint, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            with (blueprint / "PROGRAM.yaml").open("a", encoding="utf-8") as h:
                h.write("# source drift\n")
            result = run_cli(
                "claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker", expect=2
            )
            self.assertIn("program_lock_stale_or_invalid", result["error"])


if __name__ == "__main__":
    unittest.main()
