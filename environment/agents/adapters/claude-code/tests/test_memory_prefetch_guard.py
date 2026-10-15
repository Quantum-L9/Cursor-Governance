#!/usr/bin/env python3
"""memory_prefetch must no-op outside a canonical Claude surface."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

CLAUDE_DIR = Path(__file__).resolve().parents[1]
ROOT = CLAUDE_DIR.parents[3]
PREFETCH = CLAUDE_DIR / "hooks" / "memory_prefetch.py"

_MARKERS = (
    "CURSOR_AGENT",
    "CLAUDECODE",
    "CLAUDE_CODE_REMOTE",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_SESSION_ID",
    "L9_GOVERNANCE_SURFACE",
)


def _run(env_extra: dict[str, str], stdin: str = "{}") -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in _MARKERS}
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(PREFETCH)],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env=env,
    )


class PrefetchRuntimeGuardTests(unittest.TestCase):
    def test_unknown_no_session_id_skips_with_no_context(self) -> None:
        proc = _run({})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "", "must emit no additionalContext")
        self.assertIn("skipped", proc.stderr)
        self.assertIn("canonical surface detector", proc.stderr)

    def test_cursor_wins_over_projected_claude_surface(self) -> None:
        proc = _run(
            {"CURSOR_AGENT": "1", "L9_GOVERNANCE_SURFACE": "claude-code"},
            stdin=json.dumps({"session_id": "cursor"}),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "", "Cursor must receive no Claude hydrate context")
        self.assertIn("skipped", proc.stderr)

    def test_claude_marker_does_not_take_the_skip_branch(self) -> None:
        # Empty contract dir means main() may still exit 0 early, but the
        # canonical surface skip line must not be the reason.
        proc = _run({"CLAUDECODE": "1"}, stdin=json.dumps({"session_id": "t"}))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("canonical surface detector says this is not Claude", proc.stderr)

    def test_explicit_session_id_remains_a_repair_override(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(PREFETCH), "--session-id", "repair-session"],
            input="{}",
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
            env={k: v for k, v in os.environ.items() if k not in _MARKERS},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("canonical surface detector says this is not Claude", proc.stderr)

    def test_session_start_never_compiles_hydrates_or_searches(self) -> None:
        """SessionStart is health-only: no hydrate, search, conflicts or packet compile."""
        text = PREFETCH.read_text(encoding="utf-8")
        for forbidden in (
            "compile_and_format",
            "canonical_hydrate",
            ".hydrate(",
            ".search(",
            ".conflicts(",
            "classify_hydrate_state",
        ):
            self.assertNotIn(forbidden, text)
        self.assertIn("client.health()", text)
        self.assertNotIn("_claude_runtime_marker_present", text)
        self.assertNotIn('agent_id="claude-code"', text)
        self.assertNotIn('or ["cursor-governance"]', text)

    def test_prefetch_agent_id_follows_canonical_surface(self) -> None:
        sys.path.insert(0, str(PREFETCH.parent))
        import memory_prefetch as prefetch

        self.assertEqual(prefetch.prefetch_agent_id({"CURSOR_AGENT": "1"}), "cursor")
        self.assertEqual(
            prefetch.prefetch_agent_id(
                {"CURSOR_AGENT": "1", "L9_GOVERNANCE_SURFACE": "claude-code"}
            ),
            "cursor",
        )
        # DERIVED from host markers, never configured (ops/memory/agent_identity.py).
        self.assertEqual(prefetch.prefetch_agent_id({"CLAUDECODE": "1"}), "claude-code")
        self.assertEqual(
            prefetch.prefetch_agent_id(
                {
                    "CLAUDECODE": "1",
                    "CLAUDE_CODE_REMOTE": "true",
                    "CLAUDE_CODE_ENTRYPOINT": "remote_mobile",
                }
            ),
            "claude-code",
        )
        # No host marker, no identity: a governance-surface string is not evidence.
        self.assertEqual(prefetch.prefetch_agent_id({"L9_GOVERNANCE_SURFACE": "claude-code"}), "")
        # A cloud session with an unadmitted entrypoint derives no actor: the
        # identity owner's contract (tests/ops/memory/test_agent_identity.py,
        # ``{**CLAUDE, "CLAUDE_CODE_REMOTE": "true"} -> ""``) is authoritative.
        self.assertEqual(
            prefetch.prefetch_agent_id({"CLAUDECODE": "1", "CLAUDE_CODE_REMOTE": "true"}),
            "",
        )

    def test_a_degraded_read_is_shown_to_the_user(self) -> None:
        """Degraded memory health is a user-visible systemMessage."""
        sys.path.insert(0, str(PREFETCH.parent))
        import memory_prefetch as prefetch

        quiet = prefetch.hook_session_start_payload("ctx")
        self.assertNotIn("systemMessage", quiet, "a healthy session adds nothing")
        loud = prefetch.hook_session_start_payload(
            "ctx", prefetch._loud_status("DEGRADED at session start: x")
        )
        self.assertEqual(loud["systemMessage"], "L9 MEMORY — DEGRADED at session start: x")

    def test_additional_context_is_a_string_not_an_array(self) -> None:
        """SESSION_START_SPEC §3: ``additionalContext`` is a string.

        An array is not concatenated by the host — it is not injected at all,
        so the prefetch can hydrate successfully and still deliver nothing.
        The wire type is therefore asserted directly, since that is the
        property the host contract turns on.
        """
        sys.path.insert(0, str(PREFETCH.parent))
        import memory_prefetch as prefetch

        context = (
            "L9 memory: HEALTH-ONLY at SessionStart (no records read, nothing hydrated)\n"
            "transport=memory-control-plane/v1\n"
            "namespace=cursor-governance\n"
            "law=CANONICAL_LAW §8"
        )
        payload = prefetch.hook_session_start_payload(context)
        emitted = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIsInstance(emitted, str)
        self.assertNotIsInstance(emitted, list)
        self.assertEqual(emitted, context)
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "SessionStart")

        # Assert the shape on the wire form too — that is what the host parses.
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
        reparsed = json.loads(rendered)
        self.assertIsInstance(reparsed["hookSpecificOutput"]["additionalContext"], str)
        self.assertEqual(reparsed["hookSpecificOutput"]["additionalContext"], context)

        # Readability of the *content* is still guaranteed: ensure_ascii=False
        # keeps the section sign literal rather than §-escaped.
        self.assertIn("CANONICAL_LAW §8", rendered)
        self.assertNotIn("\\u00a7", rendered)

    def test_false_packet_boolean_is_not_degraded(self) -> None:
        sys.path.insert(0, str(ROOT / "ops" / "scripts"))
        from classify_hydrate_state import classify

        markdown = '```json\n{"degraded": false, "hydrate_stats": {"close_gap": false}}\n```'
        self.assertEqual(classify(markdown), (False, ""))


class _RecordingClient:
    """Stands in for MemoryControlPlaneClient; records every operation called."""

    def __init__(self, calls: list[str], healthy: bool) -> None:
        self.calls = calls
        self.healthy = healthy
        self.binding = type("Binding", (), {"ok": True, "reasons": []})()

    def health(self):
        self.calls.append("health")
        status = type("Status", (), {"value": "OK" if self.healthy else "CANONICAL_UNAVAILABLE"})()
        return type(
            "Outcome",
            (),
            {"ok": self.healthy, "status": status, "error": None if self.healthy else "store down"},
        )()

    def __getattr__(self, name: str):
        def _record(*_args, **_kwargs):
            self.calls.append(name)
            raise AssertionError(f"SessionStart must not call memory.{name}")

        return _record


class HealthOnlySessionStartTests(unittest.TestCase):
    """M01: the intercepted call list at SessionStart is exactly ``health``."""

    def _run_main(self, *, healthy: bool, namespaces: list[str]):
        import contextlib
        import io
        import tempfile
        from unittest import mock

        sys.path.insert(0, str(PREFETCH.parent))
        import memory_prefetch as prefetch

        calls: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "repo"
            (workspace / ".git").mkdir(parents=True)
            out = io.StringIO()
            event = json.dumps({"session_id": "chat-1", "transcript_path": ""})
            with (
                mock.patch.dict(
                    os.environ, {"CLAUDE_PROJECT_DIR": str(workspace), "CLAUDECODE": "1"}
                ),
                mock.patch.object(prefetch, "is_claude_gate_surface", return_value=True),
                mock.patch.object(
                    prefetch.mb, "memory_client", lambda *_a, **_k: _RecordingClient(calls, healthy)
                ),
                mock.patch.object(prefetch.mb, "ensure_importable", lambda *_a, **_k: None),
                mock.patch.object(prefetch, "_local_namespaces", lambda _roots: list(namespaces)),
                mock.patch.object(sys, "argv", ["memory_prefetch.py"]),
                mock.patch.object(sys, "stdin", io.StringIO(event)),
                contextlib.redirect_stdout(out),
            ):
                self.assertEqual(prefetch.main(), 0)
                receipts = sorted((workspace / ".l9" / "memory" / "receipts").glob("*.json"))
                receipt = json.loads(receipts[0].read_text()) if receipts else {}
        return calls, json.loads(out.getvalue()), receipt

    def test_healthy_session_start_calls_only_health(self) -> None:
        calls, payload, receipt = self._run_main(healthy=True, namespaces=["repo-ns"])
        self.assertEqual(calls, ["health"])
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("HEALTH-ONLY", context)
        self.assertIn("health=OK", context)
        self.assertNotIn("### memory hydrate", context)
        self.assertNotIn("facts_preview", context)
        self.assertNotIn("systemMessage", payload)
        self.assertEqual(receipt["status"], "health_only")
        self.assertEqual(receipt["memory_health"]["status"], "OK")
        self.assertNotIn("packet_ids", receipt)
        self.assertNotIn("hydrated_roots", receipt)
        self.assertTrue(receipt["roots"])

    def test_unhealthy_memory_is_degraded_and_loud_not_a_hydrate(self) -> None:
        calls, payload, receipt = self._run_main(healthy=False, namespaces=["repo-ns"])
        self.assertEqual(calls, ["health"])
        self.assertEqual(receipt["status"], "degraded")
        self.assertIn("CANONICAL_UNAVAILABLE", payload["systemMessage"])
        self.assertIn("Repository work is unaffected", payload["systemMessage"])

    def test_no_namespace_is_degraded_never_health_only(self) -> None:
        calls, _payload, receipt = self._run_main(healthy=True, namespaces=[])
        self.assertEqual(calls, ["health"])
        self.assertEqual(receipt["status"], "degraded")


if __name__ == "__main__":
    unittest.main()
