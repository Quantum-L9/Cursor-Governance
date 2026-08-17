from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from autonomy.worker_lane import GitWorktreeLane


@unittest.skipUnless(shutil.which("git"), "git is required")
class WorkerLaneTests(unittest.TestCase):
    def test_create_run_and_remove_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            lanes = root / "lanes"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=repo,
                check=True,
            )
            (repo / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", "base"], cwd=repo, check=True, capture_output=True
            )

            lane = GitWorktreeLane(
                repo=repo,
                lane_root=lanes,
                campaign_id="campaign",
                action_id="action",
            )
            path = lane.create()
            self.assertTrue(path.is_dir())
            self.assertTrue((path / ".cursor-commands").is_symlink())
            self.assertTrue((path / ".cursor/plans").is_symlink())
            self.assertTrue((path / ".cursor/governance/CANONICAL_LAW.md").is_symlink())
            result = lane.run(["git", "status", "--short"])
            self.assertEqual(result.returncode, 0)
            lane.remove(force=True)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
