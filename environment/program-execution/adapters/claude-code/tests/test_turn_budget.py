"""Workers have no turn ceiling unless a profile deliberately sets one.

`worker-default` sat at 12 and then 24 turns, so nontrivial BUILD tasks ran out
of turns and the workaround was to split one task into several one-file tasks.
Program Execution exists to run long campaigns, so no registered profile caps
turns and the worker is launched without `--max-turns`. A profile that still
sets max_turns gets exactly that value forwarded, and a value below 1 is refused.
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

REGISTERED_PROFILES = ("worker-default", "worker-read-only", "reviewer-default")


def _provider_module():
    path = Path(__file__).resolve().parents[1] / "provider.py"
    spec = importlib.util.spec_from_file_location("claude_provider_turns_test", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot load provider: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProfileRegistryTurnBudgetTests(unittest.TestCase):
    def test_no_registered_profile_caps_turns(self) -> None:
        for ref in REGISTERED_PROFILES:
            with self.subTest(profile=ref):
                self.assertNotIn("max_turns", load_profile(PE_ROOT, ref)["inference_budget"])

    def test_no_retry_or_profile_selection_mechanism_was_added(self) -> None:
        for ref in REGISTERED_PROFILES:
            with self.subTest(profile=ref):
                profile = load_profile(PE_ROOT, ref)
                self.assertEqual(profile["retry_policy"]["max_attempts"], 1)
                self.assertEqual(profile["retry_policy"]["backoff_seconds"], 0)

    def test_canonical_request_accepts_no_cap_and_large_caps(self) -> None:
        self.assertEqual(_request(None).inference_budget, {})
        self.assertEqual(_request(10_000).inference_budget["max_turns"], 10_000)

    def test_canonical_request_still_refuses_a_cap_below_one(self) -> None:
        for value in (0, -1):
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
    "attempt_number": 1,
    "authority_digest": "sha256:" + "0" * 64,
}


def _request(max_turns: int | None) -> CanonicalExecutionRequest:
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
        inference_budget={} if max_turns is None else {"max_turns": max_turns},
        timeout_budget={"dispatch_seconds": 1800, "poll_seconds": 30},
        requested_capabilities=("local_write",),
        telemetry_context={},
        provider_ref="claude-code",
        execution_profile_ref="worker-default",
        autonomy_authority=dict(AUTHORITY),
    )


class ClaudeArgvTurnBudgetTests(unittest.TestCase):
    """No live Claude invocation: the subprocess seam is stubbed."""

    def _argv_for(self, max_turns: int | None) -> list[str]:
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

    def test_unbounded_worker_is_launched_without_max_turns(self) -> None:
        self.assertNotIn("--max-turns", self._argv_for(None))

    def test_registry_profiles_forward_no_turn_cap(self) -> None:
        """End to end: registry -> canonical request -> argv."""
        for ref in REGISTERED_PROFILES:
            with self.subTest(profile=ref):
                budget = load_profile(PE_ROOT, ref)["inference_budget"]
                self.assertNotIn("--max-turns", self._argv_for(budget.get("max_turns")))

    def test_an_explicit_cap_is_still_forwarded(self) -> None:
        argv = self._argv_for(500)
        self.assertEqual(argv[argv.index("--max-turns") + 1], "500")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
