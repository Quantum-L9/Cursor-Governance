"""Controller verify accepts committed task work (union diff semantics)."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, cleanup_worktree, prepare_attempt, register_contract, run_cli


class VerifyCommittedWorkTest(unittest.TestCase):
    def test_verify_passes_with_committed_task_work(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            _contract, prepared = prepare_attempt(temp, workspace)
            worktree = Path(prepared["worktree"])

            # Worker commits the task work instead of leaving it dirty.
            subprocess.run(
                ["git", "-C", str(worktree), "config", "user.email", "worker@example.com"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(worktree), "config", "user.name", "worker"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(worktree), "add", "docs/result.txt"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(worktree), "commit", "-m", "task work"],
                check=True,
                capture_output=True,
            )

            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(verification["verdict"], "PASSED_LOCAL")
            self.assertEqual(
                verification["observed_changed_files"], ["docs/result.txt"]
            )
            cleanup_worktree(repo, workspace)


if __name__ == "__main__":
    unittest.main()
