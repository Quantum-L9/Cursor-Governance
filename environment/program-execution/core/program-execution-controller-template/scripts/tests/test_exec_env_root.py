"""The provisioned validation environment lives beside the runtime, not in the candidate."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from helpers import SCRIPTS

sys.path.insert(0, str(SCRIPTS))
from pec.exec_env import exec_env_root


class ExecEnvRootTests(unittest.TestCase):
    def test_consumer_worktree_maps_beside_the_runtime(self) -> None:
        l9 = Path.home() / ".l9"
        worktree = l9 / "programs" / "demo-v1" / "worktrees" / "TASK-002"
        self.assertEqual(
            exec_env_root(worktree),
            (l9 / "programs" / "demo-v1" / "runtime" / "exec-env" / "TASK-002").resolve(),
        )

    def test_nested_paths_inside_the_worktree_map_to_the_same_root(self) -> None:
        l9 = Path.home() / ".l9"
        inner = l9 / "programs" / "demo-v1" / "worktrees" / "TASK-002" / "src" / "pkg"
        self.assertEqual(exec_env_root(inner), exec_env_root(inner.parents[1]))

    def test_non_consumer_paths_have_no_provisioned_root(self) -> None:
        self.assertIsNone(exec_env_root(Path("/tmp/somewhere")))
        self.assertIsNone(exec_env_root(Path.home() / ".l9" / "gov-worktrees" / "x"))
        self.assertIsNone(exec_env_root(Path.home() / ".l9" / "programs" / "demo-v1"))
