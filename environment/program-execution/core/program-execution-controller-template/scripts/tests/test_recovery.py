from __future__ import annotations

import sqlite3
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
            )
            # Simulate passage beyond a valid positive TTL without allowing a
            # caller to mint a zero-duration lease.
            conn = sqlite3.connect(workspace / "runtime" / "state.sqlite")
            try:
                conn.execute("UPDATE leases SET expires_at='2000-01-01T00:00:00+00:00'")
                conn.commit()
            finally:
                conn.close()
            result = run_cli("recover", "--workspace", str(workspace), "--actor", "operator")
            self.assertEqual(result["status"], "RECOVERED")
            self.assertEqual(len(result["items"]), 1)
            self.assertTrue(any((workspace / "recovery").rglob("metadata.json")))


if __name__ == "__main__":
    unittest.main()
