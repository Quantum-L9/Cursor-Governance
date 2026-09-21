"""Regression tests for the migration executor's fail-closed execution boundary."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

EXECUTOR_PATH = Path(__file__).resolve().parents[2] / "workflows" / "migrate_executor.py"


def _module():
    spec = importlib.util.spec_from_file_location("l9_migrate_executor", EXECUTOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class MigrateExecutorSafetyTests(unittest.TestCase):
    def test_index_pattern_is_never_interpreted_by_a_shell(self) -> None:
        mod = _module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "sample.py").write_text("value = 'safe'\n", encoding="utf-8")
            sentinel = root / "must-not-exist"
            state = mod.MigrateState(
                old_pattern='safe"; touch must-not-exist; #',
                new_pattern="updated",
                started_at="now",
                current_step="index_analysis",
            )
            executor = mod.MigrateExecutor()
            executor.state = state
            with patch.object(mod, "REPO_ROOT", root):
                self.assertTrue(executor._step_index_analysis())
            self.assertFalse(sentinel.exists())

    def test_apply_rejects_path_traversal_from_persisted_state(self) -> None:
        mod = _module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            root.mkdir()
            outside = Path(temp) / "outside.py"
            outside.write_text("old\n", encoding="utf-8")
            state = mod.MigrateState(
                old_pattern="old",
                new_pattern="new",
                started_at="now",
                current_step="apply_changes",
                files_modified=["../outside.py"],
            )
            executor = mod.MigrateExecutor()
            executor.state = state
            with patch.object(mod, "REPO_ROOT", root):
                self.assertFalse(executor._step_apply_changes())
            self.assertEqual(outside.read_text(encoding="utf-8"), "old\n")

    def test_missing_report_generator_blocks_mutation_before_apply(self) -> None:
        mod = _module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "sample.py"
            target.write_text("old\n", encoding="utf-8")
            executor = mod.MigrateExecutor()
            with (
                patch.object(mod, "REPO_ROOT", root),
                patch.object(mod, "STATE_FILE", root / ".migration-state.json"),
                patch.object(mod, "REPORT_GENERATOR", root / "missing_report_generator.py"),
            ):
                self.assertFalse(executor.run("old", "new"))
            self.assertEqual(target.read_text(encoding="utf-8"), "old\n")

    def test_commit_failure_is_not_reported_as_success(self) -> None:
        mod = _module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "sample.py").write_text("new\n", encoding="utf-8")
            executor = mod.MigrateExecutor()
            executor.state = mod.MigrateState(
                old_pattern="old",
                new_pattern="new",
                started_at="now",
                current_step="commit",
                files_modified=["sample.py"],
            )
            responses = iter(
                [
                    (0, "", ""),  # git add
                    (0, "before\n", ""),  # git rev-parse HEAD
                    (1, "", "pre-commit rejected the change"),  # git commit
                ]
            )
            with (
                patch.object(mod, "REPO_ROOT", root),
                patch.object(executor, "_run_command", side_effect=lambda *_args: next(responses)),
            ):
                self.assertFalse(executor._step_commit())
            self.assertEqual(executor.state.commit_hash, "")


if __name__ == "__main__":
    raise SystemExit(unittest.main())
