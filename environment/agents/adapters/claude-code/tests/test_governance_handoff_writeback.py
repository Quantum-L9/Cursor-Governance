#!/usr/bin/env python3
"""Governance handoff Stop hook: parallel, never blocking, cursor-governance only.

The contract these pin:

* No publication in this session -> nothing written, nothing said.
* First Stop after a publication with no governance brief -> ARM only, silent
  (memory_writeback, running in parallel, is the one that asks).
* The next Stop -> ONE observation record to namespace cursor-governance through
  surface claude-governance-handoff, carrying the agent's brief plus receipt-
  copied degradation; a formal announcement names every section and the record.
* Still no brief -> the observed degradation is still written (PARTIAL) and the
  missing brief is announced; with nothing observed either, NOT CAPTURED.
* A brief that reports nothing, with nothing observed -> NOTHING TO REPORT,
  no record (no clutter).
* A failed write -> FAILED. After the outcome -> nothing further.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import time
import types
import unittest
import unittest.mock as mock
from contextlib import redirect_stdout
from pathlib import Path

CLAUDE_DIR = Path(__file__).resolve().parent.parent
HOOKS = CLAUDE_DIR / "hooks"
MEM = CLAUDE_DIR / "memory"
REPO_ROOT = CLAUDE_DIR.parents[3]
for _p in (str(MEM), str(HOOKS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import memory_state as st  # noqa: E402

SESSION = "sess-governance"
PR = 42
KEY = "Org/website-bot#42@" + "c" * 12


def _load(name: str, rel: str, deps: dict | None = None) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    with mock.patch.dict(sys.modules, {**(deps or {}), name: module}):
        spec.loader.exec_module(module)
    return module


# The tree under test, never the SSOT copy the hook's ensure_importable() adds.
SESSION_HANDOFF = _load("ops.memory.session_handoff", "ops/memory/session_handoff.py")
GOVERNANCE = _load(
    "ops.memory.governance_handoff",
    "ops/memory/governance_handoff.py",
    {"ops.memory.session_handoff": SESSION_HANDOFF},
)


class _Outcome:
    def __init__(self, ok: bool) -> None:
        self.ok = ok
        self.status = "OK" if ok else "REJECTED"
        self.error = None if ok else "store unavailable"
        self.receipt = types.SimpleNamespace(record_id="rec-gov" if ok else None, receipt_id=None)


def _brief(**extra: object) -> dict:
    return {
        "schema": "l9.governance_handoff.v1",
        "pr_number": PR,
        "environment_friction": [
            {"item": "SessionStart budget tight", "detail": "cold 27s", "impact": "no hydrate"}
        ],
        "blockers": [{"item": "first push", "blocker": "publication gate", "unblock": "make pr"}],
        "degraded_bootstrap": [{"component": "memory_mcp", "detail": "DEGRADED"}],
        "workarounds": [{"item": "docs lookup", "workaround": "official docs GET"}],
        "governance_actions": [
            {"action": "populate CONTEXT7_API_KEY", "where": "Infisical", "why": "Context7 401"}
        ],
        **extra,
    }


class GovernanceHandoffHookTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name).resolve()
        self.repo = base / "website-bot"
        (self.repo / ".git").mkdir(parents=True)
        self.gov = base / "gov"
        self.gov.mkdir()
        self.skip_log = base / "hook-skips.log"
        self.writes: list[dict] = []
        self.clients: list[dict] = []
        self.write_ok = True
        self.bootstrap: dict | None = None

    def _env(self) -> dict[str, str]:
        return {
            "CLAUDE_PROJECT_DIR": str(self.repo),
            # Claude Code Desktop, stated: the identity is derived from host markers
            "CLAUDECODE": "1",
            "CLAUDE_CODE_REMOTE": "false",
            "CLAUDE_CODE_ENTRYPOINT": "cli",
            "CURSOR_AGENT": "",
            "L9_HOOK_SKIP_LOG": str(self.skip_log),
        }

    def _prefetch(self, degraded: bool = False) -> None:
        with mock.patch.dict(os.environ, self._env()):
            st.write_receipt(
                st.load_contract(),
                st.resolve_receipt_id(event={"session_id": SESSION}),
                {
                    "status": "degraded" if degraded else "prefetched",
                    "degraded": degraded,
                    "memory_statuses": {"website-bot": "DEGRADED"} if degraded else {},
                    "hydrated_roots": [str(self.repo)],
                },
            )

    def _publish(self) -> None:
        pr = self.repo / ".l9" / "pr"
        pr.mkdir(parents=True, exist_ok=True)
        time.sleep(0.01)
        (pr / "pr-summary.json").write_text(
            json.dumps({"repo": "Org/website-bot", "number": PR, "head_sha": "c" * 40, "url": "u"}),
            encoding="utf-8",
        )

    def _write_brief(self, brief: dict) -> None:
        path = self.repo / ".l9" / "memory" / "governance-handoff.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(brief), encoding="utf-8")

    def _stop(self, **event: object) -> tuple[dict | None, dict]:
        test = self

        class _Client:
            def write(self, content, **kwargs):
                test.writes.append({"content": content, **kwargs})
                return _Outcome(test.write_ok)

        def _client(session_id=None, *, surface):
            self.clients.append({"session_id": session_id, "surface": surface})
            return _Client()

        with (
            mock.patch.dict(
                sys.modules,
                {
                    "ops.memory.session_handoff": SESSION_HANDOFF,
                    "ops.memory.governance_handoff": GOVERNANCE,
                },
            ),
            mock.patch.dict(os.environ, self._env(), clear=False),
        ):
            sys.modules.pop("governance_handoff_writeback", None)
            import governance_handoff_writeback as gw  # noqa: PLC0415

            out = io.StringIO()
            payload = json.dumps({"session_id": SESSION, **event})
            with (
                mock.patch.object(gw.mb, "memory_client", _client),
                mock.patch.object(gw.mb, "find_governance_root", lambda: self.gov),
                mock.patch.object(gw.mb, "ensure_importable", lambda *a, **k: self.gov),
                mock.patch.object(gw, "_observe_bootstrap", lambda: self.bootstrap),
                mock.patch.object(sys, "stdin", io.StringIO(payload)),
                redirect_stdout(out),
            ):
                self.assertEqual(gw.main(), 0)
            receipt_path = st.receipt_path(st.load_contract(), f"{SESSION}{gw.RECEIPT_SUFFIX}")
            receipt = (
                json.loads(receipt_path.read_text(encoding="utf-8"))
                if receipt_path.is_file()
                else {}
            )
        text = out.getvalue().strip()
        return (json.loads(text) if text else None), receipt

    # -- contract -----------------------------------------------------------
    def test_no_publication_is_silent_and_writes_nothing(self) -> None:
        self._prefetch()
        output, receipt = self._stop()
        self.assertIsNone(output)
        self.assertEqual(self.writes, [])
        self.assertEqual(receipt["status"], "no_publication")

    def test_the_first_stop_without_a_brief_only_arms_and_never_blocks(self) -> None:
        self._prefetch()
        self._publish()
        output, receipt = self._stop()
        self.assertIsNone(output, "this hook never blocks and never speaks while armed")
        self.assertEqual(self.writes, [])
        self.assertEqual(receipt["status"], "armed")

    def test_the_brief_is_written_once_to_cursor_governance_and_announced(self) -> None:
        self.bootstrap = {"state": "DEGRADED", "not_ready": {"memory_mcp": "DEGRADED"}}
        self._prefetch()
        self._publish()
        self._stop()  # armed; memory_writeback asks in parallel
        self._write_brief(_brief())
        output, receipt = self._stop(stop_hook_active=True)

        self.assertEqual(
            self.clients, [{"session_id": SESSION, "surface": "claude-governance-handoff"}]
        )
        self.assertEqual(len(self.writes), 1, "exactly one record")
        write = self.writes[0]
        self.assertEqual(write["namespace"], "cursor-governance")
        self.assertEqual(write["workspace"], str(self.gov))
        self.assertEqual(write["memory_class"], "observation")
        self.assertEqual(write["idempotency_key"], f"governance-handoff:{KEY}")
        self.assertIn("SessionStart budget tight — detail: cold 27s", write["content"])
        self.assertIn('bootstrap_receipt: {"state": "DEGRADED"', write["content"])

        assert output is not None
        message = output["systemMessage"]
        for fragment in (
            "L9 GOVERNANCE HANDOFF — WRITTEN (Org/website-bot#42",
            "target: namespace cursor-governance ONLY",
            "observation record: written, id rec-gov",
            "environment friction:",
            "first push — blocker: publication gate; unblock: make pr",
            "memory_mcp — detail: DEGRADED",
            "docs lookup — workaround: official docs GET",
            "populate CONTEXT7_API_KEY — where: Infisical; why: Context7 401",
            "observed by the hook (verbatim from receipts, not agent-authored):",
            "verify (any later session)",
        ):
            self.assertIn(fragment, message)
        self.assertEqual(receipt["announcement"], message)

        again, _ = self._stop()
        self.assertIsNone(again, "never again for this publication")
        self.assertEqual(len(self.writes), 1)

    def test_a_brief_present_at_the_first_stop_is_written_immediately(self) -> None:
        self._prefetch()
        self._publish()
        self._write_brief(_brief())
        output, _ = self._stop()
        assert output is not None
        self.assertIn("— WRITTEN", output["systemMessage"])
        self.assertEqual(len(self.writes), 1)

    def test_observed_degradation_is_written_even_without_a_brief(self) -> None:
        self._prefetch(degraded=True)
        self._publish()
        self._stop()  # armed
        output, _ = self._stop(stop_hook_active=True)
        self.assertEqual(len(self.writes), 1)
        self.assertIn("agent governance handoff: NOT CAPTURED", self.writes[0]["content"])
        self.assertIn('memory_prefetch: {"status": "degraded"', self.writes[0]["content"])
        assert output is not None
        message = output["systemMessage"]
        self.assertIn("L9 GOVERNANCE HANDOFF — PARTIAL", message)
        self.assertIn("AGENT GOVERNANCE HANDOFF NOT CAPTURED", message)

    def test_nothing_reported_and_nothing_observed_writes_nothing_but_says_so(self) -> None:
        self._prefetch()
        self._publish()
        self._write_brief({"schema": "l9.governance_handoff.v1", "pr_number": PR})
        output, _ = self._stop()
        self.assertEqual(self.writes, [], "no empty record clutters the store")
        assert output is not None
        self.assertIn("L9 GOVERNANCE HANDOFF — NOTHING TO REPORT", output["systemMessage"])
        self.assertIn("no record written", output["systemMessage"])

    def test_no_brief_and_nothing_observed_is_announced_not_captured(self) -> None:
        self._prefetch()
        self._publish()
        self._stop()  # armed
        output, _ = self._stop(stop_hook_active=True)
        self.assertEqual(self.writes, [])
        assert output is not None
        self.assertIn("L9 GOVERNANCE HANDOFF — NOT CAPTURED", output["systemMessage"])

    def test_a_failed_write_is_announced_as_failed(self) -> None:
        self.write_ok = False
        self._prefetch()
        self._publish()
        self._write_brief(_brief())
        output, _ = self._stop()
        assert output is not None
        message = output["systemMessage"]
        self.assertIn("L9 GOVERNANCE HANDOFF — FAILED", message)
        self.assertIn("NOT written (REJECTED: store unavailable)", message)

    def test_hook_skips_since_the_session_started_are_observed(self) -> None:
        self.skip_log.write_text(
            "2000-01-01T00:00:00Z observer memory_writeback.py old skip\n", encoding="utf-8"
        )
        self._prefetch()
        with self.skip_log.open("a", encoding="utf-8") as log:
            stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 5))
            log.write(f"{stamp} observer memory_prefetch.py locked interpreter missing\n")
        self._publish()
        self._write_brief({"schema": "l9.governance_handoff.v1", "pr_number": PR})
        self._stop()
        self.assertEqual(len(self.writes), 1)
        content = self.writes[0]["content"]
        self.assertIn("locked interpreter missing", content)
        self.assertNotIn("old skip", content)

    def test_a_subagent_stop_is_ignored(self) -> None:
        self._prefetch()
        self._publish()
        self._write_brief(_brief())
        output, _ = self._stop(agent_type="subagent")
        self.assertIsNone(output)
        self.assertEqual(self.writes, [])


class BootstrapObservationTest(unittest.TestCase):
    def _hook(self) -> types.ModuleType:
        sys.modules.pop("governance_handoff_writeback", None)
        import governance_handoff_writeback as gw  # noqa: PLC0415

        return gw

    def test_a_ready_verdict_is_not_observed(self) -> None:
        gw = self._hook()
        self.assertIsNone(
            gw.bootstrap_observation({"state": "ready", "components": {}}, ready="ready")
        )

    def test_a_degraded_verdict_copies_only_what_is_not_ready(self) -> None:
        gw = self._hook()
        seen = gw.bootstrap_observation(
            {
                "state": "degraded",
                "reason": "degraded: memory_mcp",
                "components": {"settings": "READY", "memory_mcp": "DEGRADED"},
                "reasons": {"settings": "", "memory_mcp": "server unbound"},
            },
            ready="ready",
        )
        assert seen is not None
        self.assertEqual(seen["not_ready"], {"memory_mcp": "DEGRADED"})
        self.assertEqual(seen["reasons"], {"memory_mcp": "server unbound"})

    def test_the_live_reader_on_this_tree_loads(self) -> None:
        """The reader imports a sibling by bare name; loading it must not fail."""
        gw = self._hook()
        result = gw.collect_observed({}, "", 0.0)
        self.assertNotIn("collector failed", json.dumps(result.get("bootstrap_receipt", "")))


if __name__ == "__main__":
    unittest.main()
