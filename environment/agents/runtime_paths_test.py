#!/usr/bin/env python3
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/runtime_paths_test.py
#   layer: test
#   owner: governance-control-plane
#   status: active
#   version: 1.0.0
#   updated: 2026-08-12
"""Unit tests for runtime_paths (canonical + discover-legacy; no migrate)."""

from __future__ import annotations

import importlib.util
import inspect
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("runtime_paths", HERE / "runtime_paths.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RuntimePathsTests(unittest.TestCase):
    def test_canonical_layout_under_l9_runtime_root(self) -> None:
        module = _load()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "l9root"
            os.environ["L9_RUNTIME_ROOT"] = str(root)
            os.environ.pop("L9_PROGRAM_HOME", None)
            try:
                self.assertEqual(module.runtime_root(), root.resolve())
                self.assertEqual(module.program_runtime_root(), (root / "programs").resolve())
                self.assertEqual(
                    module.program_worktree_root(), (root / "program-worktrees").resolve()
                )
                self.assertEqual(module.agent_runtime_root(), (root / "agents").resolve())
                self.assertEqual(
                    module.deployment_receipt_root(),
                    (root / "agents" / "deployments").resolve(),
                )
                self.assertEqual(
                    module.assignment_root(), (root / "agents" / "assignments").resolve()
                )
                self.assertEqual(
                    module.subagent_receipt_root(),
                    (root / "agents" / "subagent-receipts").resolve(),
                )
                self.assertEqual(
                    module.peer_readiness_root(), (root / "agents" / "readiness").resolve()
                )
                self.assertEqual(
                    module.canonical_generated_data_database(),
                    (root / "generated-data" / "pipeline.sqlite3").resolve(),
                )
                self.assertEqual(
                    module.generated_data_quarantine_root(),
                    (root / "generated-data" / "quarantine").resolve(),
                )
                self.assertEqual(
                    module.generated_data_outbox_root(),
                    (root / "generated-data" / "outbox").resolve(),
                )
            finally:
                os.environ.pop("L9_RUNTIME_ROOT", None)

    def test_l9_program_home_override(self) -> None:
        module = _load()
        with tempfile.TemporaryDirectory() as td:
            programs = Path(td) / "programs-home"
            os.environ["L9_PROGRAM_HOME"] = str(programs)
            try:
                self.assertEqual(module.program_runtime_root(), programs.resolve())
            finally:
                os.environ.pop("L9_PROGRAM_HOME", None)

    def test_discover_existing_generated_data_database(self) -> None:
        module = _load()
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            legacy = repo / ".l9" / "subagent-generated-data" / "pipeline.sqlite3"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("ok", encoding="utf-8")
            os.environ["L9_RUNTIME_ROOT"] = str(Path(td) / "empty-runtime")
            try:
                found = module.discover_existing_generated_data_database(repo_root=repo)
                self.assertEqual(found, legacy.resolve())
            finally:
                os.environ.pop("L9_RUNTIME_ROOT", None)

    def test_no_destructive_migrate_helpers(self) -> None:
        module = _load()
        source = inspect.getsource(module)
        for banned in ("shutil.move", "os.replace", "rename(", "unlink(", "rmtree"):
            self.assertNotIn(banned, source)


if __name__ == "__main__":
    unittest.main()
