from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, register_contract, run_cli


class RecoveryTest(unittest.TestCase):
    def test_expired_lease_recovered_with_evidence(self):
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            run_cli(
                "claim",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--holder",
                "worker",
                "--ttl-hours",
                "0",
            )
            result = run_cli("recover", "--workspace", str(workspace), "--actor", "operator")
            self.assertEqual(result["status"], "RECOVERED")
            self.assertEqual(len(result["items"]), 1)
            self.assertTrue(any((workspace / "recovery").rglob("metadata.json")))


if __name__ == "__main__":
    unittest.main()
