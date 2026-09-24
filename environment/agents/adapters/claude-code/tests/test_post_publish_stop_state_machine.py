#!/usr/bin/env python3
"""The two post-publish Stop hooks, driven together as one state machine.

``ops/memory/HANDOFF_CONTRACT.md`` ("Lifecycle: once per publication"):

1. First Stop after the publication: if either brief is missing or invalid,
   ``memory_writeback.py`` blocks ONCE; ``governance_handoff_writeback.py``
   only arms its ledger and stays silent. Only the repository hook ever blocks.
2. Next Stop: the repository close runs (with the brief if valid, otherwise
   without it, loudly); the governance hook writes or reports.
3. After that: nothing more for that publication. Each hook keeps its own
   ledger (``.l9/memory/handoffs/`` and ``.l9/memory/governance-handoffs/``).

A subagent or background Stop never closes or hands off; a degraded hydration
still closes.

Both hooks' real ``main()`` run here, in either order, against a temporary
repository. Only the two effects are stubbed and counted: ``close_session``
(the repository continuation close) and the memory client's ``write`` (the
governance record). The strongest assertion, checked on every sequence and by a
seeded random walk over hundreds more: the same publication and any number of
Stop events produce at most ONE repository close, at most ONE governance
result, and at most ONE block — and the persisted result does not depend on
which hook ran first.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import random
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

SESSION = "sess-state-machine"
PR = 42
REPO = "Org/website-bot"
REPO_HOOK, GOV_HOOK = "repo", "gov"
BOTH_ORDERS = ((REPO_HOOK, GOV_HOOK), (GOV_HOOK, REPO_HOOK))


def _load(name: str, rel: str, deps: dict | None = None) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    with mock.patch.dict(sys.modules, {**(deps or {}), name: module}):
        spec.loader.exec_module(module)
    return module


# The tree under test, never the SSOT copy the hooks' ensure_importable() adds.
HANDOFF = _load("ops.memory.session_handoff", "ops/memory/session_handoff.py")
GOVERNANCE = _load(
    "ops.memory.governance_handoff",
    "ops/memory/governance_handoff.py",
    {"ops.memory.session_handoff": HANDOFF},
)

#: What the agent may have written for each brief at a given Stop.
MISSING, INVALID, VALID = "missing", "invalid", "valid"


def repo_brief(state: str) -> dict | None:
    if state == MISSING:
        return None
    if state == INVALID:  # no objective / status: refused by the runtime
        return {"schema": HANDOFF.HANDOFF_SCHEMA, "pr_number": PR}
    return HANDOFF.example(PR)


def gov_brief(state: str) -> dict | None:
    if state == MISSING:
        return None
    if state == INVALID:  # a repository section in the governance file
        return {"schema": GOVERNANCE.GOVERNANCE_SCHEMA, "pr_number": PR, "decisions": []}
    return GOVERNANCE.example(PR)


class _Outcome:
    ok = True
    status = "OK"
    error = None

    def __init__(self, n: int) -> None:
        self.receipt = types.SimpleNamespace(record_id=f"rec-gov-{n}", receipt_id=None)


class Harness:
    """One repository, one session, one publication; both hooks on every Stop."""

    def __init__(self, base: Path, *, degraded: bool = False) -> None:
        self.repo = base / "website-bot"
        (self.repo / ".git").mkdir(parents=True)
        self.gov = base / "gov"
        self.gov.mkdir()
        self.skip_log = base / "hook-skips.log"
        self.closes: list[dict] = []
        self.gov_writes: list[dict] = []
        #: Per Stop: {hook: [parsed stdout lines]}.
        self.stops: list[dict[str, list[dict]]] = []
        self._prefetch(degraded)
        self.publish("c" * 40)

    # -- environment --------------------------------------------------------
    def env(self) -> dict[str, str]:
        """ONE environment for stamping and reading: the receipt key is writer-scoped."""
        return {
            "CLAUDE_PROJECT_DIR": str(self.repo),
            "L9_MEMORY_AGENT_ID": "claude-code",
            "L9_HOOK_SKIP_LOG": str(self.skip_log),
        }

    def _prefetch(self, degraded: bool) -> None:
        with mock.patch.dict(os.environ, self.env()):
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

    def publish(self, head_sha: str) -> None:
        pr = self.repo / ".l9" / "pr"
        pr.mkdir(parents=True, exist_ok=True)
        time.sleep(0.01)  # the publish receipt post-dates this session's prefetch
        (pr / "pr-summary.json").write_text(
            json.dumps({"repo": REPO, "number": PR, "head_sha": head_sha, "url": "u"}),
            encoding="utf-8",
        )

    def write(self, repo_state: str, gov_state: str) -> None:
        """What the agent has on disk before the next Stop."""
        memory = self.repo / ".l9" / "memory"
        memory.mkdir(parents=True, exist_ok=True)
        for name, doc in (
            ("handoff.json", repo_brief(repo_state)),
            ("governance-handoff.json", gov_brief(gov_state)),
        ):
            path = memory / name
            if doc is None:
                path.unlink(missing_ok=True)
            else:
                path.write_text(json.dumps(doc), encoding="utf-8")

    # -- running the hooks ----------------------------------------------------
    def _close(self, **kwargs: object) -> dict:
        self.closes.append(kwargs)
        n = len(self.closes)
        return {
            "status": "closed_canonically",
            "group_id": "website-bot",
            "writes": [{"kind": "session_continuation", "written": True, "record_id": f"c{n}"}],
            "continuation": {"record_id": f"c{n}"},
        }

    def _run(self, hook: str, event: dict) -> list[dict]:
        harness = self

        class _Client:
            def write(self, content: str, **kwargs: object) -> _Outcome:
                harness.gov_writes.append({"content": content, **kwargs})
                return _Outcome(len(harness.gov_writes))

        stub = types.ModuleType("ops.graphiti.hydration.close_session")
        stub.close_session = self._close
        modules = {
            "ops.graphiti.hydration.close_session": stub,
            "ops.memory.session_handoff": HANDOFF,
            "ops.memory.governance_handoff": GOVERNANCE,
        }
        name = "memory_writeback" if hook == REPO_HOOK else "governance_handoff_writeback"
        out = io.StringIO()
        # Each hook is its own process in production: its own environment and
        # module state, so neither can leak into the other through either.
        with mock.patch.dict(sys.modules, modules), mock.patch.dict(os.environ, self.env()):
            sys.modules.pop(name, None)
            module = __import__(name)
            patches = [
                mock.patch.object(sys, "stdin", io.StringIO(json.dumps(event))),
                mock.patch.object(module.mb, "ensure_importable", lambda *a, **k: self.gov),
            ]
            if hook == GOV_HOOK:
                patches += [
                    mock.patch.object(module.mb, "memory_client", lambda *a, **k: _Client()),
                    mock.patch.object(module.mb, "find_governance_root", lambda: self.gov),
                    mock.patch.object(module, "_observe_bootstrap", lambda: None),
                ]
            with redirect_stdout(out):
                for patch in patches:
                    patch.start()
                try:
                    assert module.main() == 0, f"{name} must exit 0 (fail-open Stop hook)"
                finally:
                    for patch in reversed(patches):
                        patch.stop()
        return [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]

    def stop(self, order: tuple[str, str] = BOTH_ORDERS[0], **event: object) -> dict:
        payload = {"session_id": SESSION, **event}
        outputs = {hook: self._run(hook, payload) for hook in order}
        self.stops.append(outputs)
        return outputs

    # -- observations -----------------------------------------------------------
    def blocks(self, hook: str | None = None) -> list[dict]:
        return [
            line
            for stop in self.stops
            for name, lines in stop.items()
            if hook in (None, name)
            for line in lines
            if line.get("decision") == "block"
        ]

    def gov_results(self) -> list[str]:
        """Every governance announcement: WRITTEN, PARTIAL, NOT CAPTURED, NOTHING TO REPORT."""
        return [
            line["systemMessage"]
            for stop in self.stops
            for line in stop.get(GOV_HOOK, [])
            if str(line.get("systemMessage", "")).startswith("L9 GOVERNANCE HANDOFF")
        ]

    def persisted(self) -> dict:
        """Both ledgers, minus wall-clock stamps: the state machine's durable state."""
        state: dict = {}
        for rel in (".l9/memory/handoffs", ".l9/memory/governance-handoffs"):
            for path in sorted((self.repo / rel).glob("*.json")):
                data = json.loads(path.read_text(encoding="utf-8"))
                data.pop("updated_at", None)
                state[f"{rel}/{path.name}"] = data
        return state

    def assert_at_most_once(self, case: unittest.TestCase) -> None:
        case.assertLessEqual(len(self.closes), 1, "more than one repository close")
        case.assertLessEqual(len(self.gov_writes), 1, "more than one governance record")
        case.assertLessEqual(len(self.gov_results()), 1, "more than one governance result")
        case.assertLessEqual(len(self.blocks()), 1, "more than one block")
        case.assertEqual(self.blocks(GOV_HOOK), [], "the governance hook never blocks")


class StopStateMachineTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()

    def harness(self, name: str = "h", *, degraded: bool = False) -> Harness:
        base = self.base / name
        base.mkdir()
        return Harness(base, degraded=degraded)

    def settle(self, h: Harness, stops: int = 2) -> None:
        """Third and fourth Stops (and beyond): nothing may happen."""
        closes, writes, results = len(h.closes), len(h.gov_writes), len(h.gov_results())
        before = h.persisted()
        for _ in range(stops):
            outputs = h.stop()
            self.assertEqual(outputs, {REPO_HOOK: [], GOV_HOOK: []}, "silent once done")
        self.assertEqual(
            (len(h.closes), len(h.gov_writes), len(h.gov_results())), (closes, writes, results)
        )
        self.assertEqual(h.persisted(), before)
        h.assert_at_most_once(self)

    # -- the sequences --------------------------------------------------------
    def test_valid_repo_and_valid_governance_on_the_first_stop(self) -> None:
        h = self.harness()
        h.write(VALID, VALID)
        outputs = h.stop()
        self.assertEqual(h.blocks(), [], "nothing to ask for")
        self.assertEqual(len(h.closes), 1)
        self.assertEqual(h.closes[0]["handoff"]["objective"], HANDOFF.example(PR)["objective"])
        self.assertEqual(len(h.gov_writes), 1)
        self.assertEqual(h.gov_writes[0]["namespace"], "cursor-governance")
        self.assertIn("L9 MEMORY HANDOFF — WRITTEN", outputs[REPO_HOOK][0]["systemMessage"])
        self.assertIn("L9 GOVERNANCE HANDOFF — WRITTEN", outputs[GOV_HOOK][0]["systemMessage"])
        self.settle(h)

    def test_a_missing_repository_brief_blocks_exactly_once(self) -> None:
        h = self.harness()
        h.write(MISSING, VALID)
        outputs = h.stop()
        self.assertEqual(len(h.blocks(REPO_HOOK)), 1)
        self.assertIn(str(HANDOFF.HANDOFF_REL), outputs[REPO_HOOK][0]["reason"])
        self.assertEqual(h.closes, [], "no close on the blocked Stop")
        # The governance brief was already valid: its hook writes it now, once.
        self.assertEqual(len(h.gov_writes), 1)
        h.write(VALID, VALID)
        h.stop(stop_hook_active=True)
        self.assertEqual(len(h.blocks()), 1, "never a second block")
        self.assertEqual(len(h.closes), 1)
        self.assertIsNotNone(h.closes[0]["handoff"])
        self.settle(h)

    def test_an_invalid_governance_brief_is_asked_for_only_by_the_repository_hook(self) -> None:
        h = self.harness()
        h.write(VALID, INVALID)
        outputs = h.stop()
        self.assertEqual(len(h.blocks(REPO_HOOK)), 1)
        reason = outputs[REPO_HOOK][0]["reason"]
        self.assertIn(str(GOVERNANCE.GOVERNANCE_REL), reason)
        self.assertIn("decisions belongs in .l9/memory/handoff.json", reason)
        self.assertNotIn(f"1) {HANDOFF.HANDOFF_REL}", reason, "the valid brief is not re-asked")
        self.assertEqual(outputs[GOV_HOOK], [], "armed: silent, never blocks")
        self.assertEqual((h.closes, h.gov_writes), ([], []))
        ledger = h.persisted()[f".l9/memory/governance-handoffs/{self._key_file()}"]
        self.assertTrue(ledger["armed"])
        self.assertNotIn("done", ledger)

    def test_after_correction_the_second_stop_closes_once_and_records_once(self) -> None:
        h = self.harness()
        h.write(MISSING, MISSING)
        h.stop()
        self.assertEqual(len(h.blocks()), 1)
        h.write(VALID, VALID)
        outputs = h.stop(stop_hook_active=True)
        self.assertEqual(len(h.closes), 1)
        self.assertEqual(h.closes[0]["handoff"]["status"], HANDOFF.example(PR)["status"])
        self.assertEqual(len(h.gov_writes), 1)
        self.assertIn("environment friction:", h.gov_writes[0]["content"])
        self.assertIn("— WRITTEN", outputs[REPO_HOOK][0]["systemMessage"])
        self.assertIn("— WRITTEN", outputs[GOV_HOOK][0]["systemMessage"])
        self.settle(h)

    def test_a_brief_still_missing_on_the_second_stop_closes_without_it_and_never_reblocks(
        self,
    ) -> None:
        # With and without the platform's stop_hook_active flag: the ledger alone
        # must prevent a second block.
        for flag in (True, False):
            with self.subTest(stop_hook_active=flag):
                h = self.harness(f"flag-{flag}")
                h.write(MISSING, MISSING)
                h.stop()
                outputs = h.stop(stop_hook_active=flag)
                self.assertEqual(len(h.blocks()), 1, "asked once, never again")
                self.assertEqual(len(h.closes), 1)
                self.assertIsNone(h.closes[0]["handoff"])
                message = outputs[REPO_HOOK][0]["systemMessage"]
                self.assertIn("HANDOFF NOT CAPTURED", message)
                gov = outputs[GOV_HOOK][0]["systemMessage"]
                self.assertIn("L9 GOVERNANCE HANDOFF — NOT CAPTURED", gov)
                self.assertEqual(h.gov_writes, [], "nothing observed, nothing reported")
                self.settle(h)

    def test_third_and_fourth_stops_never_duplicate_anything(self) -> None:
        for repo_state in (MISSING, INVALID, VALID):
            for gov_state in (MISSING, INVALID, VALID):
                with self.subTest(repo=repo_state, gov=gov_state):
                    h = self.harness(f"{repo_state}-{gov_state}")
                    h.write(repo_state, gov_state)
                    h.stop()
                    h.stop(stop_hook_active=True)
                    self.assertEqual(len(h.closes), 1, "closed by the second Stop at the latest")
                    self.assertEqual(len(h.gov_results()), 1)
                    # The agent rewriting the briefs afterwards changes nothing.
                    h.write(VALID, VALID)
                    self.settle(h, stops=3)

    def test_the_hook_order_does_not_change_the_persisted_result(self) -> None:
        for sequence in (
            [(VALID, VALID)],
            [(MISSING, VALID), (VALID, VALID)],
            [(VALID, INVALID), (VALID, VALID)],
            [(MISSING, MISSING), (MISSING, MISSING)],
            [(INVALID, MISSING), (VALID, INVALID)],
        ):
            with self.subTest(sequence=sequence):
                results = []
                for order in BOTH_ORDERS:
                    h = self.harness(f"{'-'.join(order)}-{len(results)}-{id(sequence)}")
                    for index, (repo_state, gov_state) in enumerate(sequence):
                        h.write(repo_state, gov_state)
                        h.stop(order, stop_hook_active=index > 0)
                    h.stop(order)
                    h.assert_at_most_once(self)
                    results.append(self._summary(h))
                self.assertEqual(results[0], results[1])

    def test_a_subagent_or_background_stop_neither_closes_nor_writes(self) -> None:
        for event in ({"agent_type": "subagent"}, {"is_background_agent": True}):
            with self.subTest(event=event):
                h = self.harness(next(iter(event)))
                h.write(VALID, VALID)
                for _ in range(3):
                    outputs = h.stop(**event)
                    self.assertEqual(outputs, {REPO_HOOK: [], GOV_HOOK: []})
                self.assertEqual((h.closes, h.gov_writes), ([], []))
                self.assertEqual(h.persisted(), {}, "no ledger advanced by a subagent")
                # The parent's own first Stop is still the first Stop.
                h.write(MISSING, VALID)
                h.stop()
                self.assertEqual(len(h.blocks(REPO_HOOK)), 1)

    def test_a_degraded_but_usable_hydration_still_closes(self) -> None:
        h = self.harness(degraded=True)
        h.write(VALID, MISSING)
        h.stop()  # asks for the governance brief
        outputs = h.stop(stop_hook_active=True)
        self.assertEqual(len(h.closes), 1)
        self.assertNotIn("no SessionStart prefetch receipt", outputs[REPO_HOOK][0]["systemMessage"])
        # The degradation itself is observed and recorded, though the agent wrote nothing.
        self.assertEqual(len(h.gov_writes), 1)
        self.assertIn('memory_prefetch: {"status": "degraded"', h.gov_writes[0]["content"])
        self.assertIn("— PARTIAL", outputs[GOV_HOOK][0]["systemMessage"])
        self.settle(h)

    # -- boundaries of "the same publication" --------------------------------
    def test_a_new_publication_gets_exactly_one_more_cycle(self) -> None:
        h = self.harness()
        h.write(VALID, VALID)
        h.stop()
        self.settle(h)
        h.publish("d" * 40)  # a new head on the same PR is a new publication
        h.write(VALID, VALID)
        h.stop()
        self.assertEqual(len(h.closes), 2)
        self.assertEqual(len(h.gov_writes), 2)
        self.assertNotEqual(h.closes[0]["publication"], h.closes[1]["publication"])
        self.assertEqual(len(h.blocks()), 0)
        for _ in range(2):
            self.assertEqual(h.stop(), {REPO_HOOK: [], GOV_HOOK: []})

    def test_if_a_ledger_is_lost_the_retry_is_a_replay_of_the_same_publication(self) -> None:
        """Second line of defence: the store's idempotency keys are the publication.

        A lost ledger (disk full, deleted directory) makes each hook act again;
        the store then sees the SAME publication-scoped key and replays instead
        of writing twice (close_session: one close per publication; governance:
        ``governance-handoff:<publication>``).
        """
        h = self.harness()
        h.write(VALID, VALID)
        h.stop()
        for rel in (".l9/memory/handoffs", ".l9/memory/governance-handoffs"):
            for path in (h.repo / rel).glob("*.json"):
                path.unlink()
        h.stop()
        self.assertEqual(len(h.closes), 2)
        self.assertEqual(h.closes[0]["publication"], h.closes[1]["publication"])
        self.assertEqual(h.closes[0]["session_id"], h.closes[1]["session_id"])
        self.assertEqual(len(h.gov_writes), 2)
        self.assertEqual(h.gov_writes[0]["idempotency_key"], h.gov_writes[1]["idempotency_key"])

    # -- the property -------------------------------------------------------------
    def test_no_stop_sequence_does_anything_twice_in_either_order(self) -> None:
        """Seeded random walk: any briefs, any flags, any count of Stops."""
        rng = random.Random(20260924)
        states = (MISSING, INVALID, VALID)
        for walk in range(120):
            steps = [
                (
                    rng.choice(states),
                    rng.choice(states),
                    rng.random() < 0.2,  # subagent Stop
                    rng.random() < 0.5,  # stop_hook_active
                )
                for _ in range(rng.randint(1, 6))
            ]
            outcomes = []
            for order in BOTH_ORDERS:
                h = self.harness(f"walk-{walk}-{order[0]}")
                parent_stops = 0
                for repo_state, gov_state, subagent, active in steps:
                    h.write(repo_state, gov_state)
                    event: dict = {"stop_hook_active": active}
                    if subagent:
                        event["agent_type"] = "subagent"
                    else:
                        parent_stops += 1
                    h.stop(order, **event)
                    h.assert_at_most_once(self)
                # Invariants that hold whatever the sequence was:
                if parent_stops >= 2:
                    self.assertEqual(len(h.closes), 1, steps)
                    self.assertEqual(len(h.gov_results()), 1, steps)
                if parent_stops == 0:
                    self.assertEqual((h.closes, h.gov_writes, h.persisted()), ([], [], {}))
                for block in h.blocks():
                    self.assertIn("L9 post-publish handoffs required", block["reason"])
                outcomes.append(self._summary(h))
            self.assertEqual(outcomes[0], outcomes[1], steps)

    # -- helpers ------------------------------------------------------------------
    def _key_file(self) -> str:
        return f"{REPO}#{PR}@{'c' * 12}".replace("/", "_").replace("#", "_").replace("@", "_") + (
            ".json"
        )

    @staticmethod
    def _summary(h: Harness) -> dict:
        """Everything observable, with this harness's own temp path factored out.

        Each order runs in its own directory, and announcements name the repository
        path; only that path may differ between orders.
        """
        summary = {
            "persisted": h.persisted(),
            "closes": [(c["publication"], c["handoff"]) for c in h.closes],
            "gov_writes": [(w["idempotency_key"], w["content"]) for w in h.gov_writes],
            "blocks": [b["reason"] for b in h.blocks()],
            "gov_results": h.gov_results(),
        }
        return json.loads(json.dumps(summary).replace(str(h.repo.parent), "<base>"))


if __name__ == "__main__":
    unittest.main()
