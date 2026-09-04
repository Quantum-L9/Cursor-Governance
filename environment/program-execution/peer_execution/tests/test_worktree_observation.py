"""A worktree that cannot be observed is a failed observation, not "no changes"."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from peer_execution.execution import WorktreeObservationError, _observe_worktree_changes


class WorktreeObservationTests(unittest.TestCase):
    def test_a_named_worktree_that_is_not_a_directory_raises(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            missing = Path(raw) / "no-such-worktree"
            with self.assertRaises(WorktreeObservationError) as ctx:
                _observe_worktree_changes({"worktree": str(missing)})
            self.assertIn("not a directory", str(ctx.exception))

    def test_a_named_worktree_that_is_a_file_raises(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            file_path = Path(raw) / "worktree"
            file_path.write_text("not a directory\n", encoding="utf-8")
            with self.assertRaises(WorktreeObservationError):
                _observe_worktree_changes({"worktree": str(file_path)})

    def test_a_contract_without_a_worktree_has_nothing_to_observe(self) -> None:
        self.assertEqual(_observe_worktree_changes({}), [])
        self.assertEqual(_observe_worktree_changes({"worktree": "   "}), [])

    def test_a_real_worktree_is_still_observed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            (root / "edited.py").write_text("hello\n", encoding="utf-8")
            self.assertIn("edited.py", _observe_worktree_changes({"worktree": str(root)}))


if __name__ == "__main__":
    unittest.main()
