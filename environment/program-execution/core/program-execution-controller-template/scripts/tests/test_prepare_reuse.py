from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, cleanup_worktree, register_contract, run_cli


class PrepareReuseTest(unittest.TestCase):
    """A stopped campaign leaves its task worktree behind; prepare must reuse it."""

    def test_prepare_reuses_worktree_matching_the_lease(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            lease = run_cli(
                "claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker"
            )
            worktree = workspace / "worktrees" / "TASK-001"
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "worktree",
                    "add",
                    "-b",
                    lease["branch"],
                    str(worktree),
                    lease["base_sha"],
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            prepared = run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            self.assertTrue(prepared["reused"])
            self.assertEqual(Path(prepared["worktree"]), worktree)
            cleanup_worktree(repo, workspace)

    def test_prepare_refuses_a_worktree_on_a_foreign_base(self) -> None:
        """Right branch name, wrong lineage: the leftover belongs to an older lease."""
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            lease = run_cli(
                "claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker"
            )
            # An orphan commit shares no ancestry with the lease base. Built
            # with commit-tree so the repository's HEAD is never moved.
            env = {
                **os.environ,
                "GIT_AUTHOR_NAME": "t",
                "GIT_AUTHOR_EMAIL": "t@example.com",
                "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@example.com",
            }
            tree = subprocess.run(
                ["git", "-C", str(repo), "write-tree"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            ).stdout.strip()
            foreign = subprocess.run(
                ["git", "-C", str(repo), "commit-tree", tree, "-m", "foreign"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            ).stdout.strip()
            worktree = workspace / "worktrees" / "TASK-001"
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "worktree",
                    "add",
                    "-b",
                    lease["branch"],
                    str(worktree),
                    foreign,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            # The worktree sits on the lease branch name but not on the lease
            # base: it belongs to an older lease and is refused, never reused.
            refused = run_cli("prepare", "TASK-001", "--workspace", str(workspace), expect=2)
            self.assertIn("worktree already exists", refused["error"])
            cleanup_worktree(repo, workspace)

    def test_prepare_refuses_foreign_directory(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            worktree = workspace / "worktrees" / "TASK-001"
            worktree.mkdir(parents=True)
            (worktree / "junk.txt").write_text("not a worktree\n", encoding="utf-8")
            run_cli("prepare", "TASK-001", "--workspace", str(workspace), expect=2)


if __name__ == "__main__":
    unittest.main()
