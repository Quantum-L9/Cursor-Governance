"""A workspace reset may only delete branches it can prove are its own.

Two campaigns can share one repository, so a `pec/` prefix says nothing about
ownership. The sweep deleted every `pec/...` branch with no attached worktree
as "residue by definition", which took out the other campaign's task branches.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pec import workspace_reset  # noqa: E402 - path is set above


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def _repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "README.md").write_text("x\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "init")
    return root


def _workspace(root: Path, branches: dict[str, str]) -> Path:
    """A pec workspace whose runtime records `task_id -> branch`."""
    runtime = root / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    (root / "worktrees").mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(runtime / "state.sqlite")
    conn.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY, branch TEXT)")
    conn.executemany("INSERT INTO tasks(id, branch) VALUES (?, ?)", sorted(branches.items()))
    conn.commit()
    conn.close()
    return root


def _branches(repo: Path) -> set[str]:
    return {
        line.strip()
        for line in _git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").split("\n")
        if line.strip()
    }


class WorkspaceResetOwnershipTest(unittest.TestCase):
    def test_workspace_reset_preserves_other_campaign_branch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = _repo(root / "repo")
            _git(repo, "branch", "pec/a/task-001")
            _git(repo, "branch", "pec/b/task-001")
            campaign_a = _workspace(root / "programs/a", {"TASK-001": "pec/a/task-001"})

            workspace_reset.fresh_execution_workspace(
                campaign_a, repo, task_ids=["TASK-001"], release_leases=False
            )

            remaining = _branches(repo)
            self.assertNotIn("pec/a/task-001", remaining, "own branch was not cleaned")
            self.assertIn("pec/b/task-001", remaining, "another campaign's branch was deleted")

    def test_workspace_reset_removes_owned_task_branch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = _repo(root / "repo")
            _git(repo, "branch", "pec/a/task-001")
            campaign = _workspace(root / "programs/a", {"TASK-001": "pec/a/task-001"})

            result = workspace_reset.fresh_execution_workspace(
                campaign, repo, task_ids=["TASK-001"], release_leases=False
            )

            self.assertNotIn("pec/a/task-001", _branches(repo))
            reported = set(result["orphaned_branches"])
            for entry in result["tasks_cleaned"]:
                reported.update(entry["branches"])
            self.assertIn("pec/a/task-001", reported, "the reset did not report what it removed")

    def test_workspace_reset_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = _repo(root / "repo")
            _git(repo, "branch", "pec/a/task-001")
            _git(repo, "branch", "pec/b/task-001")
            campaign = _workspace(root / "programs/a", {"TASK-001": "pec/a/task-001"})

            first = workspace_reset.fresh_execution_workspace(
                campaign, repo, task_ids=["TASK-001"], release_leases=False
            )
            second = workspace_reset.fresh_execution_workspace(
                campaign, repo, task_ids=["TASK-001"], release_leases=False
            )

            self.assertEqual(first["workspace"], second["workspace"])
            self.assertIn("pec/b/task-001", _branches(repo))

    def test_ownership_is_not_inferred_from_branch_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = _repo(root / "repo")
            _git(repo, "branch", "pec/a/task-001")
            _git(repo, "branch", "pec/b/task-001")
            campaign = _workspace(root / "programs/a", {"TASK-001": "pec/a/task-001"})

            owned = workspace_reset.workspace_owned_branches(campaign, repo)

            self.assertEqual(owned, {"pec/a/task-001"})

    def test_a_workspace_with_no_runtime_owns_nothing(self) -> None:
        """No record is not a licence to delete; it is the absence of proof."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = _repo(root / "repo")
            _git(repo, "branch", "pec/b/task-001")
            bare = root / "programs/empty"
            (bare / "worktrees").mkdir(parents=True)

            workspace_reset.fresh_execution_workspace(bare, repo, release_leases=False)

            self.assertIn("pec/b/task-001", _branches(repo))

    def test_same_task_id_across_campaigns_matches_only_the_owner(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = _repo(root / "repo")
            _git(repo, "branch", "pec/a/task-001")
            _git(repo, "branch", "pec/b/task-001")
            campaign = _workspace(root / "programs/a", {"TASK-001": "pec/a/task-001"})
            owned = workspace_reset.workspace_owned_branches(campaign, repo)

            self.assertEqual(
                workspace_reset.task_branches(repo, "TASK-001", owned), ["pec/a/task-001"]
            )
            self.assertEqual(
                sorted(workspace_reset.task_branches(repo, "TASK-001")),
                ["pec/a/task-001", "pec/b/task-001"],
                msg="unscoped matching still reaches across campaigns",
            )


if __name__ == "__main__":
    unittest.main()
