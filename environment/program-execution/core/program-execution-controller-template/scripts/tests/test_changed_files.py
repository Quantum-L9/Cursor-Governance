from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, cleanup_worktree, prepare_attempt, register_contract, run_cli


class ChangedFilesTest(unittest.TestCase):
    def test_declared_changed_files_must_equal_observed(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            prepare_attempt(temp, workspace, declared_changed=["docs/not-result.txt"])
            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(verification["verdict"], "FAILED")
            self.assertEqual(verification["gates"]["changed_files_exact"], "FAIL")
            run_cli(
                "release-lease",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--reason",
                "test cleanup",
                "--actor",
                "test",
            )
            cleanup_worktree(repo, workspace)


if __name__ == "__main__":
    unittest.main()
