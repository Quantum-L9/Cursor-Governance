from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, register_contract, run_cli


class LeaseTests(unittest.TestCase):
    """Task-scoped writer leases (PHASE-6 part D).

    Repository-global serialization is retired: two disjoint same-repository
    tasks may hold concurrent leases, each with its own worktree and branch,
    sharing the same initial campaign base. What stays unique is the active
    lease per *task*; scope collision safety lives in the root-Autonomy claim
    plane, not in a repository mutex.
    """

    def test_two_disjoint_tasks_same_repository_can_claim(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp, two_tasks=True)
            register_contract(temp, workspace, task_id="TASK-001", output="docs/result.txt")
            register_contract(temp, workspace, task_id="TASK-002", output="docs/second.txt")
            lease_a = run_cli(
                "claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker-1"
            )
            lease_b = run_cli(
                "claim", "TASK-002", "--workspace", str(workspace), "--holder", "worker-2"
            )
            self.assertNotEqual(lease_a["lease_id"], lease_b["lease_id"])
            self.assertNotEqual(lease_a["branch"], lease_b["branch"])
            self.assertEqual(lease_a["base_sha"], lease_b["base_sha"])
            prepared_a = run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            prepared_b = run_cli("prepare", "TASK-002", "--workspace", str(workspace))
            self.assertNotEqual(prepared_a["worktree"], prepared_b["worktree"])
            status = run_cli("status", "--workspace", str(workspace))
            self.assertEqual(len(status["active_leases"]), 2)

    def test_duplicate_active_lease_for_same_task_is_denied(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            lease = run_cli(
                "claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker-1"
            )
            # The readiness gate refuses a second claim of a LEASED task.
            result = run_cli(
                "claim",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--holder",
                "worker-2",
                expect=2,
            )
            self.assertIn("runtime_state_not_claimable", result["error"])
            # The unique index is the transactional backstop underneath it.
            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            from pec.state import StateDB

            db = StateDB(workspace / "runtime" / "state.sqlite")
            try:
                with self.assertRaises(sqlite3.IntegrityError):
                    db.create_lease(
                        {
                            "lease_id": "lease-duplicate",
                            "task_id": "TASK-001",
                            "repository_id": lease["repository_id"],
                            "holder": "worker-2",
                            "base_sha": lease["base_sha"],
                            "branch": lease["branch"],
                            "issued_at": lease["issued_at"],
                            "expires_at": lease["expires_at"],
                        }
                    )
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
