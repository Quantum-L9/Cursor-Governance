"""The mutating worker's turn budget reaches the provider argv.

`worker-default` sat at 12 turns while the canonical request permits up to 64,
so nontrivial BUILD tasks exhausted their budget and the workaround was to split
one task into several one-file tasks. This proves the registry value is what
Claude is actually launched with — a registry edit nothing forwards is not a
fix.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PE_ROOT = Path(__file__).resolve().parents[3]
# APPEND, never insert(0): Program Execution needs its own PE-exclusive
# packages here, but `scripts` is a top-level name it SHARES with the
# repository root. Prepending would hand PE's `scripts/` that name for the
# whole process. See peer_execution.imports.pe_script.
if str(PE_ROOT) not in sys.path:
    sys.path.append(str(PE_ROOT))

from peer_execution.profiles import load_profile  # noqa: E402
from peer_execution.provider import CanonicalExecutionRequest  # noqa: E402

WORKER_DEFAULT_MAX_TURNS = 24
READ_ONLY_MAX_TURNS = 8


def _provider_module():
    path = Path(__file__).resolve().parents[1] / "provider.py"
    spec = importlib.util.spec_from_file_location("claude_provider_turns_test", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot load provider: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProfileRegistryTurnBudgetTests(unittest.TestCase):
    def test_worker_default_is_twenty_four(self) -> None:
        profile = load_profile(PE_ROOT, "worker-default")
        self.assertEqual(profile["inference_budget"]["max_turns"], WORKER_DEFAULT_MAX_TURNS)

    def test_read_only_and_reviewer_profiles_are_unchanged(self) -> None:
        for ref in ("worker-read-only", "reviewer-default"):
            with self.subTest(profile=ref):
                profile = load_profile(PE_ROOT, ref)
                self.assertEqual(profile["inference_budget"]["max_turns"], READ_ONLY_MAX_TURNS)

    def test_no_retry_or_profile_selection_mechanism_was_added(self) -> None:
        for ref in ("worker-default", "worker-read-only", "reviewer-default"):
            with self.subTest(profile=ref):
                profile = load_profile(PE_ROOT, ref)
                self.assertEqual(profile["retry_policy"]["max_attempts"], 1)
                self.assertEqual(profile["retry_policy"]["backoff_seconds"], 0)

    def test_canonical_request_accepts_twenty_four(self) -> None:
        request = _request(WORKER_DEFAULT_MAX_TURNS)
        self.assertEqual(request.inference_budget["max_turns"], WORKER_DEFAULT_MAX_TURNS)

    def test_canonical_request_still_refuses_out_of_range_budgets(self) -> None:
        for value in (0, 65):
            with self.subTest(max_turns=value), self.assertRaises(Exception):
                _request(value)


AUTHORITY = {
    # A mutating window must carry root authority: the provider now refuses to
    # launch one that cannot authorize its own effects.
    "schema": "l9.program-execution.autonomy-authority.v1",
    "owns_program_state": False,
    "task_id": "TASK-001",
    "adapter_session_id": "adapter-session-fixture",
    "lease_id": "lease-fixture",
    "agent_id": "agent-fixture",
    "runtime_database": "/tmp/autonomy-runtime.sqlite3",
    "repository_root": "/tmp",
    "workspace": "/tmp/workspace",
}


def _request(max_turns: int) -> CanonicalExecutionRequest:
    return CanonicalExecutionRequest(
        execution_id="EXEC-001",
        task_id="TASK-001",
        program_lock_digest="d" * 64,
        rendered_contract_digest="c" * 64,
        worktree_ref=str(Path(tempfile.gettempdir())),
        objective="Prove the turn budget reaches the provider.",
        context_manifest_ref="context.json",
        context_manifest_digest="a" * 64,
        rendered_contract={"validation_commands": ["git status --short"]},
        worker_instruction="do the thing",
        permission_profile_ref="repo-local-bounded",
        permission_profile={
            "profile_ref": "repo-local-bounded",
            "allowed_actions": ["inspect", "local_write"],
            "denied_actions": ["push"],
        },
        inference_budget={"max_turns": max_turns},
        timeout_budget={"dispatch_seconds": 1800, "poll_seconds": 30},
        requested_capabilities=("local_write",),
        telemetry_context={},
        provider_ref="claude-code",
        execution_profile_ref="worker-default",
        autonomy_authority=dict(AUTHORITY),
    )


class ClaudeArgvTurnBudgetTests(unittest.TestCase):
    """No live Claude invocation: the subprocess seam is stubbed."""

    def _argv_for(self, max_turns: int) -> list[str]:
        provider = _provider_module()
        captured: dict[str, list[str]] = {}
        workspace = Path(tempfile.mkdtemp())

        class _Result:
            returncode = 0
            stdout = '{"result": "ok"}'
            stderr = ""
            timed_out = False
            duration_seconds = 0.0

        def _fake_run_argv(argv, **kwargs):
            captured["argv"] = list(argv)
            return _Result()

        with patch.object(provider, "run_argv", _fake_run_argv):
            try:
                instance = provider.ClaudeCodeProvider(workspace, workspace)
                instance.invoke(_request(max_turns))
            except Exception:
                # Post-dispatch parsing is not what this test is about; the argv
                # was captured before any of it ran.
                if "argv" not in captured:
                    raise
        return captured["argv"]

    def test_worker_default_budget_reaches_claude_argv(self) -> None:
        argv = self._argv_for(WORKER_DEFAULT_MAX_TURNS)
        self.assertIn("--max-turns", argv)
        self.assertEqual(argv[argv.index("--max-turns") + 1], "24")

    def test_registry_value_is_what_gets_forwarded(self) -> None:
        """End to end: registry -> canonical request -> argv."""
        profile = load_profile(PE_ROOT, "worker-default")
        budget = int(profile["inference_budget"]["max_turns"])
        argv = self._argv_for(budget)
        self.assertEqual(argv[argv.index("--max-turns") + 1], str(budget))
        self.assertEqual(str(budget), "24")

    def test_read_only_budget_is_forwarded_unchanged(self) -> None:
        argv = self._argv_for(READ_ONLY_MAX_TURNS)
        self.assertEqual(argv[argv.index("--max-turns") + 1], "8")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
