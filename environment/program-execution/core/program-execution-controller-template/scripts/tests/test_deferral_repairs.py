"""Regressions for the controller findings executed from the PR #461 deferral list."""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import (
    SCRIPTS,
    bootstrap_repo,
    cleanup_worktree,
    register_contract,
    run_cli,
    write_json,
)

sys.path.insert(0, str(SCRIPTS))
from pec.controller import _preflight2_gates, _verified_this_attempt  # noqa: E402
from pec.preflight import ACTOR_INPUT, TASK_INPUT, _next_action  # noqa: E402
from pec.state import ALLOWED_TRANSITIONS  # noqa: E402


class SubmitRequiresStartTests(unittest.TestCase):
    """PEC-F12: an attempt is recorded only for a task `pec start` moved to EXECUTING."""

    def test_submitted_is_reachable_only_from_executing(self) -> None:
        sources = {
            state for state, targets in ALLOWED_TRANSITIONS.items() if "SUBMITTED" in targets
        }
        self.assertEqual(sources, {"EXECUTING"})

    def test_record_attempt_from_contracted_is_refused(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            rendered = run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
            contract = json.loads(Path(rendered["contract"]).read_text(encoding="utf-8"))
            receipt = write_json(
                temp / "attempt.json",
                {
                    "schema": "program-execution-controller.attempt-receipt.v2",
                    "task_id": "TASK-001",
                    "contract_digest": contract["contract_digest"],
                    "program_digest": contract["program_digest"],
                    "base_sha": contract["base_sha"],
                    "candidate_sha": None,
                    "changed_files": [],
                    "validation_results": [],
                    "produced_evidence": [],
                    "residual_unknowns": [],
                    "claimed_status": "completed",
                },
            )
            refused = run_cli(
                "record-attempt",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--receipt",
                str(receipt),
                expect=2,
            )
            self.assertEqual(refused["status"], "ERROR")
            self.assertEqual(refused["error_type"], "ControllerError")
            self.assertIn("CONTRACTED", refused["error"])
            cleanup_worktree(repo, workspace)


class ReplayBindsToTheAttemptTests(unittest.TestCase):
    """PEC-F14: a verification receipt replays only for the attempt it verified."""

    def test_receipt_from_an_earlier_attempt_is_not_replayed(self) -> None:
        with TemporaryDirectory() as raw:
            workspace = Path(raw)
            task = {"id": "TASK-001", "rendered_contract_digest": None}
            receipt_dir = workspace / "receipts" / "verification"
            receipt_dir.mkdir(parents=True)
            (receipt_dir / "TASK-001.json").write_text(
                json.dumps({"task_id": "TASK-001", "evidence_id": "EVID-RUNTIME-TASK-001-001"}),
                encoding="utf-8",
            )
            self.assertIsNotNone(_verified_this_attempt(workspace, task, {"attempt_number": 1}))
            self.assertIsNone(_verified_this_attempt(workspace, task, {"attempt_number": 2}))


class Preflight2GatesTests(unittest.TestCase):
    """PEC-F15: inventory and coverage are computed, never the literal PASS."""

    def test_uncovered_declared_validation_is_incomplete(self) -> None:
        gates = _preflight2_gates(["python3 -V"], declared=["python3 -V", "make test"])
        self.assertEqual(gates["preflight2_coverage"], "INCOMPLETE")
        covered = _preflight2_gates(["python3 -V", "make test"], declared=["make test"])
        self.assertEqual(covered["preflight2_coverage"], "PASS")

    def test_malformed_command_fails_inventory(self) -> None:
        self.assertEqual(_preflight2_gates(["   "])["preflight2_inventory"], "INCOMPLETE")
        self.assertEqual(_preflight2_gates(["python3 -V"])["preflight2_inventory"], "PASS")


class NextActionTests(unittest.TestCase):
    """PEC-F18: preflight names what it knows and what the caller must supply."""

    def test_unknown_actor_and_task_are_required_inputs_not_literals(self) -> None:
        with unittest.mock.patch.dict(os.environ, {"L9_MEMORY_AGENT_ID": "", "PEC_ACTOR": ""}):
            action = _next_action(
                None,
                workspace=Path("/ws"),
                task_id=None,
                receipt_workspace=Path("/repo"),
                surface="cursor",
            )
        self.assertEqual(action["args"][0], "claim")
        self.assertIn(TASK_INPUT, action["args"])
        self.assertIn(ACTOR_INPUT, action["args"])
        self.assertEqual(action["required_inputs"], sorted({ACTOR_INPUT, TASK_INPUT}))
        self.assertNotIn("worker", action["args"])
        self.assertNotIn("TASK-001", action["args"])

    def test_known_actor_and_repository_are_used(self) -> None:
        with unittest.mock.patch.dict(os.environ, {"PEC_ACTOR": "alice"}):
            action = _next_action(
                "repository_not_reconciled",
                workspace=Path("/ws"),
                task_id="TASK-002",
                receipt_workspace=Path("/repo"),
                surface="cursor",
                repository_ids=["repo-main"],
            )
        self.assertEqual(action["args"][-1], "repo-main=/repo")
        self.assertNotIn("required_inputs", action)
        with unittest.mock.patch.dict(os.environ, {"L9_MEMORY_AGENT_ID": "", "PEC_ACTOR": ""}):
            claim = _next_action(
                "lease_missing",
                workspace=Path("/ws"),
                task_id="TASK-002",
                receipt_workspace=Path("/repo"),
                surface="cursor",
            )
        self.assertEqual(claim["args"][-1], ACTOR_INPUT)
        self.assertEqual(claim["required_inputs"], [ACTOR_INPUT])


class CliErrorTypingTests(unittest.TestCase):
    """PEC-F20: the CLI reports what kind of failure it is."""

    def test_unsupported_command_error_carries_its_type(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            refused = run_cli("verify", "TASK-404", "--workspace", str(workspace), expect=2)
            self.assertEqual(refused["status"], "ERROR")
            self.assertEqual(refused["error_type"], "ControllerError")


if __name__ == "__main__":
    unittest.main()
