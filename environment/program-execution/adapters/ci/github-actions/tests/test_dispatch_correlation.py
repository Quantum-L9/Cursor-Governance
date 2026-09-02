"""Dispatch on a ref; correlate the run to THIS dispatch, never merely to a SHA."""

from __future__ import annotations

import unittest
from pathlib import Path

from peer_execution.imports import load_module

_HERE = Path(__file__).resolve().parents[1]
dispatcher = load_module(_HERE / "dispatcher.py", "pes_test_gha_dispatcher")
monitor = load_module(_HERE / "monitor.py", "pes_test_gha_monitor")

SHA = "3" * 40


class _Result:
    exit_code = 0
    stderr = ""


class _Transport:
    def __init__(self, rows=None) -> None:
        self.rows = rows or []
        self.argv: list[list[str]] = []

    def run(self, argv):
        self.argv.append(list(argv))
        return _Result()

    def json(self, argv):
        self.argv.append(list(argv))
        return self.rows


class DispatchRefTests(unittest.TestCase):
    def test_dispatch_uses_the_contract_ref_not_the_candidate_sha(self) -> None:
        transport = _Transport()
        evidence = dispatcher.dispatch_workflow(
            transport,
            {"repository": "o/r", "workflow": "ci.yml", "candidate_sha": SHA, "ref": "feat/x"},
        )
        argv = transport.argv[0]
        self.assertEqual(argv[argv.index("--ref") + 1], "feat/x")
        self.assertNotIn(SHA, argv)
        self.assertEqual(evidence["candidate_sha"], SHA)
        self.assertTrue(evidence["dispatched_at"])

    def test_dispatch_without_a_ref_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            dispatcher.dispatch_workflow(
                _Transport(), {"repository": "o/r", "workflow": "ci.yml", "candidate_sha": SHA}
            )


class RunCorrelationTests(unittest.TestCase):
    CONTRACT = {"repository": "o/r", "workflow": "ci.yml", "candidate_sha": SHA}

    def test_a_pre_existing_run_at_the_same_sha_is_not_adopted(self) -> None:
        rows = [
            {
                "databaseId": 1,
                "headSha": SHA,
                "status": "completed",
                "conclusion": "success",
                "event": "push",
                "createdAt": "2026-01-01T00:00:00Z",
            }
        ]
        state = {"dispatch_evidence": {"dispatched_at": "2026-01-02T00:00:00+00:00"}}
        self.assertIsNone(monitor.find_run(_Transport(rows), self.CONTRACT, state=state))

    def test_only_a_dispatch_run_created_after_ours_matches(self) -> None:
        rows = [
            {
                "databaseId": 7,
                "headSha": SHA,
                "status": "in_progress",
                "conclusion": None,
                "event": "workflow_dispatch",
                "createdAt": "2026-01-02T00:00:05+00:00",
            },
            {
                "databaseId": 6,
                "headSha": SHA,
                "status": "completed",
                "conclusion": "failure",
                "event": "workflow_dispatch",
                "createdAt": "2026-01-01T00:00:00+00:00",
            },
        ]
        state = {"dispatch_evidence": {"dispatched_at": "2026-01-02T00:00:00+00:00"}}
        run = monitor.find_run(_Transport(rows), self.CONTRACT, state=state)
        self.assertEqual(run["databaseId"], 7)

    def test_a_pinned_run_id_is_followed_afterwards(self) -> None:
        rows = [
            {"databaseId": 9, "headSha": SHA, "status": "completed", "conclusion": "success"},
            {"databaseId": 7, "headSha": SHA, "status": "completed", "conclusion": "failure"},
        ]
        run = monitor.find_run(_Transport(rows), self.CONTRACT, state={"host_run_id": 7})
        self.assertEqual(run["databaseId"], 7)


if __name__ == "__main__":
    unittest.main()
