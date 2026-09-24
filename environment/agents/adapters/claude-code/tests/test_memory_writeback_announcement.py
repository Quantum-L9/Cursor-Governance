#!/usr/bin/env python3
"""Post-publish handoff: fires once after a publication, announces what it wrote.

The contract these pin:

* No publication in this session -> no close, no output (an ordinary turn).
* The first Stop after a publication, with either handoff missing -> the hook
  asks ONCE, for both (Stop ``decision: block`` carrying the l9.session_handoff.v1
  and l9.governance_handoff.v1 shapes). It is the only hook that blocks.
* The next Stop, with the handoff -> ONE close to the in-scope repository
  carrying the comprehensive brief; a formal announcement names every section
  and record. The governance handoff is NOT written here — its own parallel
  hook (governance_handoff_writeback.py) writes it to cursor-governance.
* Asked and still missing -> close anyway, announce LOUDLY that the handoff
  was not captured.
* After the close -> nothing further for that publication.
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

SESSION = "sess-handoff"
PR = 42


def _load(name: str, rel: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    with mock.patch.dict(sys.modules, {name: module}):
        spec.loader.exec_module(module)
    return module


# The tree under test, never the SSOT copy the hook's ensure_importable() adds.
HANDOFF = _load("ops.memory.session_handoff", "ops/memory/session_handoff.py")
with mock.patch.dict(sys.modules, {"ops.memory.session_handoff": HANDOFF}):
    GOVERNANCE = _load("ops.memory.governance_handoff", "ops/memory/governance_handoff.py")


def _brief(**extra: object) -> dict:
    return {
        "schema": "l9.session_handoff.v1",
        "pr_number": PR,
        "objective": "Ship the checkout flow",
        "status": "PR open, CI green, waiting on review",
        "published": ["checkout API"],
        "completed": ["unit tests"],
        "not_completed": [{"item": "refund path", "reason": "out of scope"}],
        "blocked": [{"item": "payments", "blocker": "no API key", "unblock": "add key"}],
        "decisions": [{"decision": "use Stripe", "rationale": "existing contract"}],
        "conflicts": [{"conflict": "two retry policies", "resolution": "kept the SDK one"}],
        "human_actions": [
            {"action": "add STRIPE_KEY", "where": "Infisical", "why": "payments", "then": "rerun"}
        ],
        "next_actions": ["merge after review"],
        "open_questions": ["webhook retries?"],
        "risks": ["rate limits"],
        "verification": ["pytest: 120 passed"],
        **extra,
    }


def _governance(**extra: object) -> dict:
    return {
        "schema": "l9.governance_handoff.v1",
        "pr_number": PR,
        "environment_friction": [{"item": "SessionStart budget tight", "detail": "cold 27s"}],
        **extra,
    }


class PostPublishHandoffTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name).resolve()
        (self.repo / ".git").mkdir()
        self.closes: list[dict] = []
        self.close_status = "closed_canonically"

    # -- fixtures -----------------------------------------------------------
    def _env(self) -> dict[str, str]:
        """ONE environment for stamping and reading: the receipt key is writer-scoped."""
        return {
            "CLAUDE_PROJECT_DIR": str(self.repo),
            "CLAUDECODE": "1",
            "CLAUDE_CODE_REMOTE": "false",
            "CLAUDE_CODE_ENTRYPOINT": "cli",
            "CURSOR_AGENT": "",
        }

    def _prefetch(self, degraded: bool = False) -> None:
        with mock.patch.dict(os.environ, self._env()):
            contract = st.load_contract()
            st.write_receipt(
                contract,
                st.resolve_receipt_id(event={"session_id": SESSION}),
                {
                    "status": "degraded" if degraded else "prefetched",
                    "degraded": degraded,
                    "hydrated_roots": [str(self.repo)],
                },
            )

    def _publish(self) -> None:
        pr = self.repo / ".l9" / "pr"
        pr.mkdir(parents=True, exist_ok=True)
        time.sleep(0.01)  # the publish receipt post-dates this session's prefetch
        (pr / "pr-summary.json").write_text(
            json.dumps(
                {
                    "repo": "Org/website-bot",
                    "number": PR,
                    "head_sha": "b" * 40,
                    "url": "https://example.test/pr/42",
                }
            ),
            encoding="utf-8",
        )

    def _write_handoff(self, brief: dict, name: str = "handoff.json") -> None:
        path = self.repo / ".l9" / "memory" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(brief), encoding="utf-8")

    def _write_both(self, brief: dict | None = None) -> None:
        self._write_handoff(brief or _brief())
        self._write_handoff(_governance(), "governance-handoff.json")

    def _stop(self, **event: object) -> tuple[dict | None, dict]:
        def _close(**kwargs):
            self.closes.append(kwargs)
            return {
                "status": self.close_status,
                "group_id": "website-bot",
                "writes": [
                    {"kind": "session_continuation", "written": True, "record_id": "rec-cont"},
                    {"kind": "close", "written": True, "record_id": "rec-close"},
                ],
                "continuation": {"record_id": "rec-cont"},
            }

        stub = types.ModuleType("ops.graphiti.hydration.close_session")
        stub.close_session = _close
        env = self._env()
        with (
            mock.patch.dict(
                sys.modules,
                {
                    "ops.graphiti.hydration.close_session": stub,
                    "ops.memory.session_handoff": HANDOFF,
                    "ops.memory.governance_handoff": GOVERNANCE,
                },
            ),
            mock.patch.dict(os.environ, env, clear=False),
        ):
            sys.modules.pop("memory_writeback", None)
            import memory_writeback as wb  # noqa: PLC0415

            out = io.StringIO()
            payload = json.dumps({"session_id": SESSION, **event})
            with mock.patch.object(sys, "stdin", io.StringIO(payload)), redirect_stdout(out):
                self.assertEqual(wb.main(), 0)
            contract = st.load_contract()
            receipt = json.loads(
                st.receipt_path(contract, f"{SESSION}{wb.WRITEBACK_RECEIPT_SUFFIX}").read_text(
                    encoding="utf-8"
                )
            )
        text = out.getvalue().strip()
        return (json.loads(text) if text else None), receipt

    # -- contract -----------------------------------------------------------
    def test_an_ordinary_turn_without_a_publication_is_silent(self) -> None:
        self._prefetch()
        output, receipt = self._stop()
        self.assertIsNone(output)
        self.assertEqual(self.closes, [])
        self.assertEqual(receipt["status"], "no_publication")

    def test_a_degraded_hydration_still_closes_after_publish(self) -> None:
        """Regression: fresh_receipt() is False when degraded; that skipped the close."""
        self._prefetch(degraded=True)
        self._publish()
        self._write_both()
        output, receipt = self._stop()
        self.assertEqual(len(self.closes), 1)
        assert output is not None
        self.assertNotIn("no SessionStart prefetch receipt", output["systemMessage"])
        self.assertEqual(receipt["status"], "ran")

    def test_a_publication_from_before_this_session_is_not_this_sessions(self) -> None:
        self._publish()
        time.sleep(0.01)
        self._prefetch()  # the session started after that publication
        output, _ = self._stop()
        self.assertIsNone(output)
        self.assertEqual(self.closes, [])

    def test_the_first_stop_after_publish_asks_once_for_both_handoffs(self) -> None:
        self._prefetch()
        self._publish()
        output, receipt = self._stop()
        assert output is not None
        self.assertEqual(output["decision"], "block")
        reason = output["reason"]
        self.assertIn("l9.session_handoff.v1", reason)
        self.assertIn("l9.governance_handoff.v1", reason)
        self.assertIn(".l9/memory/governance-handoff.json", reason)
        self.assertIn('"pr_number": 42', reason)
        self.assertEqual(self.closes, [], "nothing is closed before the brief exists")
        self.assertEqual(receipt["status"], "handoff_requested")

    def test_a_missing_governance_handoff_alone_is_requested(self) -> None:
        self._prefetch()
        self._publish()
        self._write_handoff(_brief())
        output, _ = self._stop()
        assert output is not None
        self.assertEqual(output["decision"], "block")
        self.assertIn("l9.governance_handoff.v1", output["reason"])
        self.assertNotIn("1) .l9/memory/handoff.json", output["reason"])

    def test_both_handoffs_present_close_without_asking(self) -> None:
        self._prefetch()
        self._publish()
        self._write_both()
        output, _ = self._stop()
        assert output is not None
        self.assertNotIn("decision", output)
        self.assertEqual(len(self.closes), 1)

    def test_friction_in_the_repository_handoff_is_refused_and_named(self) -> None:
        self._prefetch()
        self._publish()
        self._write_both(_brief(governance_friction=[{"item": "x"}]))
        output, _ = self._stop()
        assert output is not None
        self.assertEqual(output["decision"], "block")
        self.assertIn(
            "governance_friction belongs in .l9/memory/governance-handoff.json", output["reason"]
        )

    def test_the_handoff_is_written_once_with_everything_and_announced(self) -> None:
        self._prefetch()
        self._publish()
        self._stop()  # asks
        self._write_both()
        output, receipt = self._stop(stop_hook_active=True)

        self.assertEqual(len(self.closes), 1, "exactly one close for the publication")
        close = self.closes[0]
        self.assertEqual(close["publication"], "Org/website-bot#42@" + "b" * 12)
        brief = close["handoff"]
        self.assertEqual(brief["objective"], "Ship the checkout flow")
        self.assertEqual(brief["human_actions"][0]["where"], "Infisical")

        assert output is not None
        message = output["systemMessage"]
        self.assertIn("L9 MEMORY HANDOFF — WRITTEN", message)
        for fragment in (
            "session_continuation: written, id rec-cont",
            "status: PR open, CI green",
            "refund path — out of scope",
            "payments — no API key (unblock: add key)",
            "use Stripe — existing contract",
            "two retry policies — kept the SDK one",
            "YOUR ACTIONS ELSEWHERE",
            "add STRIPE_KEY @ Infisical",
            "pytest: 120 passed",
            "governance handoff → namespace cursor-governance: written separately",
        ):
            self.assertIn(fragment, message)
        self.assertNotIn("SessionStart budget tight", message, "governance is not this hook's")
        self.assertEqual(receipt["announcement"], message)

        # And never again for this publication.
        again, _ = self._stop()
        self.assertIsNone(again)
        self.assertEqual(len(self.closes), 1)

    def test_a_handoff_still_missing_after_the_request_is_announced_loudly(self) -> None:
        self._prefetch()
        self._publish()
        self._stop()  # asks
        output, _ = self._stop(stop_hook_active=True)  # agent did not write it
        self.assertEqual(len(self.closes), 1, "the session still closes")
        self.assertIsNone(self.closes[0]["handoff"])
        assert output is not None
        message = output["systemMessage"]
        self.assertIn("HANDOFF NOT CAPTURED", message)
        self.assertIn("— PARTIAL", message)

    def test_a_handoff_for_another_publication_is_not_accepted(self) -> None:
        self._prefetch()
        self._publish()
        self._write_both(_brief(pr_number=7))
        output, _ = self._stop()
        assert output is not None
        self.assertEqual(output["decision"], "block", "a stale brief is not this PR's")

    def test_a_failed_close_is_not_announced_as_written(self) -> None:
        self.close_status = "close_incomplete"
        self._prefetch()
        self._publish()
        self._write_both()
        output, _ = self._stop()
        assert output is not None
        # writes were reported by the stub, so the close is PARTIAL, not WRITTEN
        self.assertNotIn("— WRITTEN", output["systemMessage"])
        self.assertIn("— PARTIAL", output["systemMessage"])


class HandoffFormatTest(unittest.TestCase):
    def test_normalize_keeps_every_section(self) -> None:
        brief = HANDOFF.normalize(_brief(), pr_number=PR)
        for key in ("published", "blocked", "decisions", "conflicts", "human_actions"):
            self.assertTrue(brief[key], key)

    def test_the_32kb_cap_is_enforced(self) -> None:
        huge = _brief(risks=["x" * 1100] * 40, verification=["y" * 1100] * 40)
        with self.assertRaises(HANDOFF.HandoffError):
            HANDOFF.normalize(huge, pr_number=PR)

    def test_render_shows_every_section(self) -> None:
        text = HANDOFF.render(HANDOFF.normalize(_brief(), pr_number=PR))
        for fragment in ("objective:", "blocked:", "human actions:", "verification:"):
            self.assertIn(fragment, text)


if __name__ == "__main__":
    unittest.main()
