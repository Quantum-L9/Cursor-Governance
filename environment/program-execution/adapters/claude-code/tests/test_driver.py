from __future__ import annotations

import hashlib
import importlib.util
import json
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

    def test_stream_parser_coerces_string_changed_files(self) -> None:
        parser = self._stream_parser()
        value = parser.parse_claude_json(
            '{"result":{"changed_files":"ops/scripts/claude_projection.py"}}'
        )
        self.assertEqual(
            value["result_payload"]["changed_files"],
            ["ops/scripts/claude_projection.py"],
        )

    def test_stream_parser_extracts_fenced_json_result(self) -> None:
        parser = self._stream_parser()
        result = '```json\n{"changed_files":["a.py"],"candidate_sha":null}\n```'
        value = parser.parse_claude_json('{"result":' + json.dumps(result) + "}")
        self.assertEqual(value["result_payload"]["changed_files"], ["a.py"])

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

    def _excerpts(self):
        path = Path(__file__).resolve().parents[1] / "excerpts.py"
        spec = importlib.util.spec_from_file_location("claude_excerpts_test", path)
        if spec is None or spec.loader is None:
            self.fail(f"cannot load excerpts: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_excerpt_redacts_token_shapes(self) -> None:
        excerpts = self._excerpts()
        # Assembled at runtime rather than written as one literal: a tracked
        # file containing `sk-` followed by 20+ alphanumerics trips the repo
        # credential scan (repo-hygiene and governance-self-check), and this
        # fixture is a fake token, not a secret. Splitting it keeps the scan
        # honest without weakening what the test asserts.
        token = "sk-" + "abcdefghijklmnopqrstuvwxyz"
        text = excerpts.redacted_excerpt(f"fail {token} stderr")
        self.assertIsNotNone(text)
        self.assertNotIn(token, text)
        self.assertIn("<redacted>", text)

    def test_invoke_persists_host_excerpts_on_failure(self) -> None:
        from peer_execution.context import build_context_manifest
        from peer_execution.permissions import resolve_permission_profile
        from peer_execution.provider import CanonicalExecutionRequest
        from peer_execution.subprocess_runner import CommandResult

        module = self._provider()
        host = {
            "type": "result",
            "subtype": "error_max_turns",
            "is_error": True,
            "num_turns": 13,
            "errors": ["Reached maximum number of turns (12)"],
            "result": {"changed_files": "ops/scripts/claude_projection.py"},
        }
        stdout = json.dumps(host)
        stderr = "error: max turns exceeded\n"

        def _digest(text: str) -> str:
            return "sha256:" + hashlib.sha256(text.encode()).hexdigest()

        fake = CommandResult(
            argv=("claude", "-p", "x", "--max-turns", "12"),
            executable="/usr/bin/claude",
            exit_code=1,
            stdout=stdout,
            stderr=stderr,
            stdout_digest=_digest(stdout),
            stderr_digest=_digest(stderr),
            duration_seconds=1.0,
            timed_out=False,
            environment_fingerprint="sha256:test",
        )
        contract = {
            "task_id": "task-1",
            "program_digest": "a" * 64,
            "contract_digest": "b" * 64,
            "base_sha": "c" * 40,
            "worktree": "/tmp/w",
            "objective": "tiny edit",
            "writable_paths": ["src/**"],
            "validation_commands": ["git diff --check"],
            "required_evidence_ids": [],
            "requested_actions": ["inspect", "local_write"],
        }
        manifest = build_context_manifest(contract)
        permission = resolve_permission_profile("repo-local-bounded", ["inspect", "local_write"])
        request = CanonicalExecutionRequest(
            execution_id="exec-excerpt",
            task_id="task-1",
            program_lock_digest="a" * 64,
            rendered_contract_digest="b" * 64,
            worktree_ref="/tmp",
            objective="tiny edit",
            context_manifest_ref="/tmp/context.json",
            context_manifest_digest=str(manifest["manifest_digest"]),
            rendered_contract=dict(manifest["rendered_contract"]),
            worker_instruction=str(manifest["worker_instruction"]),
            permission_profile_ref="repo-local-bounded",
            permission_profile=permission,
            inference_budget={"max_turns": 12},
            timeout_budget={"dispatch_seconds": 1800, "poll_seconds": 30},
            requested_capabilities=("inspect", "local_write"),
            telemetry_context={"provider_ref": "claude-code-direct"},
            provider_ref="claude-code-direct",
            execution_profile_ref="worker-default",
            # A mutating window must carry root authority: the provider refuses
            # to launch one that cannot authorize its own effects.
            autonomy_authority={
                "schema": "l9.program-execution.autonomy-authority.v1",
                "owns_program_state": False,
                "task_id": "task-1",
                "adapter_session_id": "adapter-session-fixture",
                "lease_id": "lease-fixture",
                "agent_id": "agent-fixture",
                "runtime_database": "/tmp/autonomy-runtime.sqlite3",
                "repository_root": "/tmp",
                "workspace": "/tmp/workspace",
            },
        )
        repo_root = Path(__file__).resolve().parents[5]
        with tempfile.TemporaryDirectory() as temporary:
            provider = module.ClaudeCodeProvider(temporary, repo_root)
            with patch.object(module, "run_argv", return_value=fake):
                invocation = provider.invoke(request)
        self.assertEqual(invocation.status, "FAIL")
        evidence = invocation.evidence[0]
        self.assertEqual(evidence["subtype"], "error_max_turns")
        self.assertEqual(evidence["num_turns"], 13)
        self.assertIn("error: max turns exceeded", evidence["stderr_excerpt"])
        self.assertIn("error_max_turns", evidence["stdout_excerpt"])
        self.assertEqual(evidence["stderr_text"], evidence["stderr_excerpt"])
        self.assertEqual(evidence["stdout_text"], evidence["stdout_excerpt"])
        self.assertTrue(str(evidence["stderr_digest"]).startswith("sha256:"))
        self.assertTrue(str(evidence["stdout_digest"]).startswith("sha256:"))
        self.assertEqual(
            invocation.result.structured_payload["changed_files"],
            ["ops/scripts/claude_projection.py"],
        )
        error = invocation.result.errors[0]
        self.assertEqual(error["subtype"], "error_max_turns")
        self.assertIn("stderr_excerpt", error)
        self.assertIn("error: max turns exceeded", str(error["stderr_text"]))
        transport = invocation.result.transport_evidence_refs[0]
        self.assertIn("error: max turns exceeded", str(transport["stderr_text"]))
        self.assertTrue(str(transport["stderr_digest"]).startswith("sha256:"))

    def test_worker_cannot_git_commit_and_must_return_null_candidate_sha(self) -> None:
        renderer = self._permission_renderer()
        profile = {"allowed_actions": ["inspect", "local_write"], "denied_actions": ["push"]}
        permissions = renderer.render_permissions(profile, {"validation_commands": []})
        self.assertIn("Bash(git add:*)", permissions["denied"])
        self.assertIn("Bash(git commit:*)", permissions["denied"])
        self.assertIn("Bash(gh:*)", permissions["denied"])
        self.assertNotIn("Bash(git push:*)", permissions["allowed"])
        from peer_execution.context import build_context_manifest

        manifest = build_context_manifest(
            {
                "task_id": "task-1",
                "program_digest": "a" * 64,
                "contract_digest": "b" * 64,
                "base_sha": "c" * 40,
                "worktree": "/tmp/w",
                "objective": "tiny edit",
                "writable_paths": ["src/one.py"],
                "validation_commands": [],
                "required_evidence_ids": [],
                "requested_actions": ["inspect", "local_write"],
            }
        )
        instruction = str(manifest["worker_instruction"])
        self.assertIn("candidate_sha MUST be JSON null", instruction)
        self.assertIn("do not git add or git commit", instruction)


if __name__ == "__main__":
    unittest.main()
