from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, register_contract, run_cli


class LeaseTests(unittest.TestCase):
    def test_one_active_writer_lease_per_repository(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp, two_tasks=True)
            register_contract(temp, workspace, task_id="TASK-001", output="docs/result.txt")
            register_contract(temp, workspace, task_id="TASK-002", output="docs/second.txt")
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker-1")
            result = run_cli(
                "claim", "TASK-002", "--workspace", str(workspace), "--holder", "worker-2", expect=2
            )
            self.assertIn("active writer lease", result["error"])


if __name__ == "__main__":
    unittest.main()
