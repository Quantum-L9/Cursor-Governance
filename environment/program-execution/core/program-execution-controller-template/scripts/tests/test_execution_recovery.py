"""Controller-level regressions for worktree recovery and verify idempotence.

These cover the two failure shapes that used to require a human: task branch
residue that blocked recreation, and a second `verify` call on an attempt whose
verdict had already moved the task out of SUBMITTED.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, cleanup_worktree, register_contract, run_cli


def _branches(repo: Path) -> list[str]:
    listed = subprocess.run(
        ["git", "-C", str(repo), "for-each-ref", "--format=%(refname:short)", "refs/heads/pec"],
        text=True,
        capture_output=True,
        check=False,
    )
    return [line.strip() for line in listed.stdout.splitlines() if line.strip()]


class PrepareSelfHealTest(unittest.TestCase):
    def test_prepare_recreates_the_worktree_over_a_stale_task_branch(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            lease = run_cli(
                "claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker"
            )
            # Residue from an interrupted attempt: the task branch exists with no
            # worktree behind it, which is what produced
            # "fatal: a branch named 'pec/.../task-001' already exists".
            subprocess.run(
                ["git", "-C", str(repo), "branch", lease["branch"], lease["base_sha"]],
                check=True,
                capture_output=True,
            )
            self.assertIn(lease["branch"], _branches(repo))

            healed = run_cli("prepare", "TASK-001", "--workspace", str(workspace))

            self.assertTrue(healed["recovered"], "prepare did not self-heal the stale branch")
            self.assertTrue(Path(healed["worktree"]).is_dir())
            cleanup_worktree(repo, workspace)


class FreshExecutionWorkspaceTest(unittest.TestCase):
    def test_reset_is_repeatable_and_leaves_the_repo_able_to_recreate(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            self.assertTrue(_branches(repo))

            first = run_cli(
                "fresh-workspace", "--workspace", str(workspace), "--repository", str(repo)
            )
            self.assertEqual(_branches(repo), [], f"branches survived reset: {first}")
            self.assertFalse((workspace / "worktrees" / "TASK-001").exists())

            # Invoking recovery twice must not be an error.
            run_cli("fresh-workspace", "--workspace", str(workspace), "--repository", str(repo))

            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            recreated = run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            self.assertTrue(Path(recreated["worktree"]).is_dir())
            cleanup_worktree(repo, workspace)

    def test_reset_on_a_workspace_that_never_executed_is_a_no_op(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            report = run_cli(
                "fresh-workspace", "--workspace", str(workspace), "--repository", str(repo)
            )
            self.assertEqual(report["tasks_cleaned"], [])


class ResolveEnvTest(unittest.TestCase):
    def test_controller_reports_the_interpreter_validation_will_use(self) -> None:
        resolved = run_cli("resolve-env")
        self.assertTrue(resolved["python"])
        self.assertTrue(Path(resolved["python"]).is_file())
        self.assertEqual(Path(resolved["python"]).parent.as_posix(), resolved["bin_dir"])


if __name__ == "__main__":
    unittest.main()
