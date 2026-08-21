"""Worker handoff: unmodified trees fail closed; already-modified trees do not."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PE_ROOT / "scripts/pe_worker.py"


def _load():
    spec = importlib.util.spec_from_file_location("pe_worker_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PeWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load()

    def _repo(self, root: Path) -> Path:
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
        (root / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        )
        return head.stdout.strip()

    def test_unmodified_tree_without_worker_is_not_changed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            worktree = Path(raw) / "wt"
            workspace = Path(raw) / "ws"
            worktree.mkdir()
            base = self._repo(worktree)
            outcome = self.mod.invoke_worker(
                {"id": "TASK-001", "execution_kind": "repo_local"},
                {"base_sha": base, "writable_paths": ["ops/scripts/resolve_stack_tip.py"]},
                worktree,
                workspace=workspace,
                command="",
            )
            self.assertFalse(outcome.changed)
            self.assertEqual(outcome.reason, "no_worker_configured")

    def test_already_modified_tree_counts_as_work(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            worktree = Path(raw) / "wt"
            workspace = Path(raw) / "ws"
            worktree.mkdir()
            base = self._repo(worktree)
            (worktree / "ops" / "scripts").mkdir(parents=True)
            (worktree / "ops" / "scripts" / "resolve_stack_tip.py").write_text(
                "print('tip')\n", encoding="utf-8"
            )
            outcome = self.mod.invoke_worker(
                {"id": "TASK-001", "execution_kind": "repo_local"},
                {"base_sha": base, "writable_paths": ["ops/scripts/resolve_stack_tip.py"]},
                worktree,
                workspace=workspace,
                command="",
            )
            self.assertTrue(outcome.changed)
            self.assertEqual(outcome.reason, "worktree_already_modified")


if __name__ == "__main__":
    raise SystemExit(unittest.main())
