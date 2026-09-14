from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PE_ROOT = Path(__file__).resolve().parents[2]


def load_runner():
    path = PE_ROOT / "scripts" / "run_campaign.py"
    spec = importlib.util.spec_from_file_location("pe_pre_birth_workspace", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PreBirthWorkspaceTests(unittest.TestCase):
    def test_pre_birth_workspace_is_committed_and_has_no_remote(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw) / "source"
            result = runner.default_ensure_pre_birth_workspace(workspace)
            self.assertEqual(result, workspace.resolve())
            head = subprocess.run(
                ["git", "-C", str(workspace), "rev-parse", "HEAD"], text=True, capture_output=True
            )
            self.assertEqual(head.returncode, 0, head.stderr)
            origin = subprocess.run(
                ["git", "-C", str(workspace), "remote", "get-url", "origin"],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(origin.returncode, 0)

    def test_pre_birth_workspace_rejects_remote(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw) / "source"
            runner.default_ensure_pre_birth_workspace(workspace)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(workspace),
                    "remote",
                    "add",
                    "origin",
                    "https://github.com/Quantum-L9/example.git",
                ],
                check=True,
            )
            with self.assertRaises(runner.CampaignError):
                runner.default_ensure_pre_birth_workspace(workspace)

    def test_pre_birth_workspace_rejects_non_origin_remote(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw) / "source"
            runner.default_ensure_pre_birth_workspace(workspace)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(workspace),
                    "remote",
                    "add",
                    "upstream",
                    "https://github.com/Quantum-L9/example.git",
                ],
                check=True,
            )
            with self.assertRaises(runner.CampaignError) as ctx:
                runner.default_ensure_pre_birth_workspace(workspace)
            self.assertIn("upstream", str(ctx.exception))

    def test_pre_birth_missing_workspace_path_is_campaign_error(self) -> None:
        runner = load_runner()
        with self.assertRaises(runner.CampaignError) as ctx:
            runner.pre_birth_target_worktree({"lifecycle": "pre_birth_local_execution_workspace"})
        self.assertIn("workspace_path", str(ctx.exception))

    def test_pre_birth_alias_contradiction_is_refused(self) -> None:
        compile_path = PE_ROOT / "scripts" / "compile_campaign_source.py"
        spec = importlib.util.spec_from_file_location("pe_pre_birth_compile", compile_path)
        assert spec and spec.loader
        compiler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(compiler)
        source = {
            "targets": [
                {
                    "lifecycle": "pre_birth_local_execution_workspace",
                    "logical_target_id": "future-product",
                    "workspace_path": "/tmp/pre-birth",
                    "future_repository_intent": "future-product",
                }
            ],
            "program": {"target_repository_id": "Quantum-L9/other"},
        }
        with self.assertRaises(compiler.CompileError) as ctx:
            compiler.resolve_campaign_target_repository(source)
        self.assertIn("program.target_repository_id", str(ctx.exception))
        self.assertIn("Quantum-L9/other", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
