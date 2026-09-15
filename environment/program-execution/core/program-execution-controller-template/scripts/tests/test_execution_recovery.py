"""Controller-level regressions for worktree recovery and verify idempotence.

These cover the two failure shapes that used to require a human: task branch
residue that blocked recreation, and a second `verify` call on an attempt whose
verdict had already moved the task out of SUBMITTED.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, cleanup_worktree, register_contract, run_cli


def _attempt_rows(workspace: Path) -> list[tuple[int, str]]:
    conn = sqlite3.connect(workspace / "runtime" / "state.sqlite")
    try:
        return [
            (int(number), str(status))
            for number, status in conn.execute(
                "SELECT attempt_number, status FROM attempts ORDER BY attempt_number"
            )
        ]
    finally:
        conn.close()


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


class ScopedFreshWorkspaceTests(unittest.TestCase):
    def test_task_scoped_reset_leaves_the_other_task_alone(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp, two_tasks=True)
            register_contract(temp, workspace)
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            first = run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            # A whole-workspace sweep used to delete every worktree directory and
            # every pec/* branch regardless of --task-id.
            other = workspace / "worktrees" / "TASK-002"
            other.mkdir(parents=True)
            (other / "in-flight.txt").write_text("keep\n", encoding="utf-8")
            run_cli(
                "fresh-workspace",
                "--workspace",
                str(workspace),
                "--repository",
                str(repo),
                "--task-id",
                "TASK-001",
            )
            self.assertFalse(Path(first["worktree"]).exists())
            self.assertTrue((other / "in-flight.txt").is_file())

    def test_task_scoped_reset_of_a_dispatched_task_keeps_its_generation(self) -> None:
        """Recovering a dispatched task cleans the worktree, not the ledger of generations.

        The front door recovers a KNOWN_TERMINAL attempt through this same
        command. The consumed generation must survive it: the `attempts`
        reservation stays, the evidence directory stays, and the next claim
        renders attempt 2 rather than re-issuing attempt 1.
        """
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            prepared = run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
            started = run_cli(
                "start", "TASK-001", "--workspace", str(workspace), "--actor", "worker"
            )
            self.assertEqual(started["attempt_number"], 1)
            self.assertEqual(_attempt_rows(workspace), [(1, "DISPATCHED")])
            evidence = workspace / "attempts" / "TASK-001" / "attempt-001"
            evidence.mkdir(parents=True, exist_ok=True)
            (evidence / "provider.log").write_text("KNOWN_TERMINAL\n", encoding="utf-8")

            report = run_cli(
                "fresh-workspace",
                "--workspace",
                str(workspace),
                "--repository",
                str(repo),
                "--task-id",
                "TASK-001",
                "--actor",
                "make-campaign",
                "--reason",
                "peer attempt ended KNOWN_TERMINAL",
            )
            self.assertEqual([t["task_id"] for t in report["tasks_cleaned"]], ["TASK-001"])
            self.assertFalse(Path(prepared["worktree"]).exists())
            self.assertTrue((evidence / "provider.log").is_file(), "evidence was erased")
            self.assertEqual(_attempt_rows(workspace), [(1, "DISPATCHED")])

            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            rendered = run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
            contract = json.loads(Path(rendered["contract"]).read_text(encoding="utf-8"))
            self.assertEqual(contract["attempt_number"], 2)
            cleanup_worktree(repo, workspace)

    def test_dispatched_unsubmitted_generation_consumes_a_t4_budget(self) -> None:
        """A KNOWN_TERMINAL window that never submits still spends the T4 attempt."""
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace, risk_tier="T4")
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
            started = run_cli(
                "start", "TASK-001", "--workspace", str(workspace), "--actor", "worker"
            )
            self.assertEqual(started["attempt_number"], 1)
            run_cli(
                "fresh-workspace",
                "--workspace",
                str(workspace),
                "--repository",
                str(repo),
                "--task-id",
                "TASK-001",
                "--actor",
                "make-campaign",
                "--reason",
                "peer attempt ended KNOWN_TERMINAL",
            )
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
            refused = run_cli(
                "start", "TASK-001", "--workspace", str(workspace), "--actor", "worker", expect=2
            )
            self.assertIn("retry budget exhausted", refused["error"])
            cleanup_worktree(repo, workspace)

    def test_task_id_cannot_escape_the_worktrees_directory(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            sentinel = temp / "sentinel.txt"
            sentinel.write_text("do not delete\n", encoding="utf-8")
            for bad in ("../..", "../../sentinel.txt", "TASK-999"):
                run_cli(
                    "fresh-workspace",
                    "--workspace",
                    str(workspace),
                    "--repository",
                    str(repo),
                    "--task-id",
                    bad,
                    expect=2,
                )
            self.assertTrue(sentinel.is_file())
            self.assertTrue((workspace / "runtime" / "state.sqlite").is_file())


if __name__ == "__main__":
    unittest.main()
