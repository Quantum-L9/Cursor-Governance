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

    def test_report_generation_uses_a_confined_local_receipt(self) -> None:
        mod = _module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            executor = mod.MigrateExecutor()
            executor.state = mod.MigrateState(
                old_pattern="old",
                new_pattern="new",
                started_at="now",
                current_step="generate_report",
                files_modified=["sample.py"],
                validation_results=[{"check": "py_compile", "status": "✅"}],
            )
            with (
                patch.object(mod, "REPO_ROOT", root),
                patch.object(mod, "STATE_FILE", root / ".migration-state.json"),
            ):
                self.assertTrue(executor._step_generate_report())
            self.assertEqual(executor.state.report_path, "reports/migration-old.md")
            self.assertTrue((root / executor.state.report_path).is_file())

    def test_apply_is_idempotent_for_a_previously_migrated_file(self) -> None:
        mod = _module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "sample.py"
            target.write_text("new\n", encoding="utf-8")
            executor = mod.MigrateExecutor()
            executor.state = mod.MigrateState(
                old_pattern="old",
                new_pattern="new",
                started_at="now",
                current_step="apply_changes",
                files_modified=["sample.py"],
                matches=[{"file": "sample.py"}],
            )
            with patch.object(mod, "REPO_ROOT", root):
                self.assertTrue(executor._step_apply_changes())
            self.assertEqual(target.read_text(encoding="utf-8"), "new\n")
            self.assertTrue(executor.state.matches[0]["migrated"])

    def test_index_and_confirmation_fall_back_when_ripgrep_is_unavailable(self) -> None:
        mod = _module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "sample.py").write_text("value = 'old'\n", encoding="utf-8")
            executor = mod.MigrateExecutor()
            executor.state = mod.MigrateState(
                old_pattern="old",
                new_pattern="new",
                started_at="now",
                current_step="index_analysis",
            )
            with (
                patch.object(mod, "REPO_ROOT", root),
                patch.object(executor, "_run_command", return_value=(127, "", "rg unavailable")),
            ):
                self.assertTrue(executor._step_index_analysis())
                self.assertEqual(executor._fixed_string_file_count("old"), 1)
            self.assertEqual(executor.state.matches[0]["file"], "sample.py")

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
