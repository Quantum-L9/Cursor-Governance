from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_SUBSYSTEM = Path(__file__).resolve().parents[3]
if str(_SUBSYSTEM) not in sys.path:
    sys.path.insert(0, str(_SUBSYSTEM))


class ClaudeProviderSourceTests(unittest.TestCase):
    def _permission_renderer(self):
        path = Path(__file__).resolve().parents[1] / "permission_renderer.py"
        spec = importlib.util.spec_from_file_location("claude_permission_renderer_test", path)
        if spec is None or spec.loader is None:
            self.fail(f"cannot load permission renderer: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _stream_parser(self):
        path = Path(__file__).resolve().parents[1] / "stream_parser.py"
        spec = importlib.util.spec_from_file_location("claude_stream_parser_test", path)
        if spec is None or spec.loader is None:
            self.fail(f"cannot load stream parser: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_provider_is_thin_and_permission_safe(self) -> None:
        root = Path(__file__).resolve().parents[1]
        provider = (root / "provider.py").read_text(encoding="utf-8")
        self.assertIn("PROVIDER_CLASS", provider)
        self.assertNotIn("BaseExecutionAdapter", provider)
        self.assertNotIn("attempt_receipt", provider)
        self.assertNotIn("dangerously-skip-permissions", provider)
        self.assertIn("--output-format", provider)

    def test_validation_command_cannot_regrant_remote_mutation(self) -> None:
        renderer = self._permission_renderer()
        profile = {
            "allowed_actions": ["inspect", "local_write"],
            "denied_actions": ["push"],
        }
        contract = {"validation_commands": ["git push origin HEAD"]}
        with self.assertRaisesRegex(ValueError, "allowlist"):
            renderer.render_permissions(profile, contract)

    def test_compound_validation_command_cannot_hide_push(self) -> None:
        renderer = self._permission_renderer()
        profile = {
            "allowed_actions": ["inspect", "local_write"],
            "denied_actions": ["push"],
        }
        contract = {"validation_commands": ["python -m pytest && git push origin HEAD"]}
        with self.assertRaisesRegex(ValueError, "multiple shell operations"):
            renderer.render_permissions(profile, contract)

    def test_read_only_git_validation_is_allowed(self) -> None:
        renderer = self._permission_renderer()
        profile = {"allowed_actions": ["inspect"], "denied_actions": ["push"]}
        contract = {"validation_commands": ["git diff --check"]}
        permissions = renderer.render_permissions(profile, contract)
        self.assertIn("Bash(git diff --check)", permissions["allowed"])

    def test_stream_parser_accepts_structured_result_object(self) -> None:
        parser = self._stream_parser()
        value = parser.parse_claude_json('{"result":{"changed_files":[]}}')
        self.assertEqual(value["result_payload"], {"changed_files": []})

    def test_stream_parser_rejects_empty_output(self) -> None:
        parser = self._stream_parser()
        with self.assertRaisesRegex(ValueError, "non-empty"):
            parser.parse_claude_json("")

    def _provider(self):
        path = Path(__file__).resolve().parents[1] / "provider.py"
        spec = importlib.util.spec_from_file_location("claude_provider_test", path)
        if spec is None or spec.loader is None:
            self.fail(f"cannot load provider: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_binding_probe_blocks_without_claude_executable(self) -> None:
        module = self._provider()
        repo_root = Path(__file__).resolve().parents[5]
        with tempfile.TemporaryDirectory() as temporary:
            provider = module.ClaudeCodeProvider(temporary, repo_root)
            with patch.object(module.shutil, "which", return_value=None):
                probe = provider.probe(None)
        self.assertEqual(probe.status, "BLOCKED")
        self.assertEqual(probe.blocked_reason, "claude executable is absent")
        self.assertIn({"type": "executable", "path": None}, probe.evidence)
        self.assertIn({"type": "path_probe", "missing": []}, probe.evidence)
        self.assertTrue(any(item.get("type") == "provider_metadata" for item in probe.evidence))


if __name__ == "__main__":
    unittest.main()
