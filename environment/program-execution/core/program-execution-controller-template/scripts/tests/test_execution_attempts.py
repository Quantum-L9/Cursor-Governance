"""PEC-P0-003: every dispatch has a durable attempt and an immutable baseline.

At no point may the Controller be unable to answer: which exact attempt caused
(or may have caused) the current worktree effects, and what did the worktree
look like immediately before it? These tests pin that at the Controller.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from helpers import (
    SCRIPTS,
    bootstrap_repo,
    cleanup_worktree,
    register_contract,
    run_cli,
    write_json,
)

sys.path.insert(0, str(SCRIPTS))
from pec.attempts import (  # noqa: E402
    baseline_artifact_path,
    effected_paths,
    load_baseline_artifact,
)
from pec.common import ControllerError  # noqa: E402
from pec.state import StateDB  # noqa: E402


def _rows(workspace: Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(workspace / "runtime" / "state.sqlite")
    conn.row_factory = sqlite3.Row
    try:
        return [
            dict(r)
            for r in conn.execute("SELECT * FROM execution_attempts ORDER BY attempt_number")
        ]
    finally:
        conn.close()


def _start(temp: Path, workspace: Path) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    """claim -> prepare -> render -> start; returns (started, worktree, contract)."""
    run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
    prepared = run_cli("prepare", "TASK-001", "--workspace", str(workspace))
    rendered = run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
    started = run_cli("start", "TASK-001", "--workspace", str(workspace), "--actor", "worker")
    contract = json.loads(Path(rendered["contract"]).read_text(encoding="utf-8"))
    return started, Path(prepared["worktree"]), contract


def _receipt(temp: Path, contract: dict[str, Any], **overrides: Any) -> Path:
    receipt = {
        "schema": "program-execution-controller.attempt-receipt.v2",
        "task_id": "TASK-001",
        "contract_digest": contract["contract_digest"],
        "program_digest": contract["program_digest"],
        "base_sha": contract["base_sha"],
        "candidate_sha": None,
        "changed_files": ["docs/result.txt"],
        "validation_results": [
            {"command": command, "status": "PASS", "exit_code": 0, "evidence": "worker output"}
            for command in contract["validation_commands"]
        ],
        "produced_evidence": [],
        "residual_unknowns": [],
        "claimed_status": "completed",
        **overrides,
    }
    return write_json(temp / "attempt.json", receipt)


class DurableAttemptTests(unittest.TestCase):
    def test_start_mints_an_attempt_and_a_baseline_before_any_provider_could_run(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            started, worktree, _ = _start(temp, workspace)
            self.assertTrue(started["attempt_id"].startswith("attempt-"))
            self.assertEqual(started["attempt_number"], 1)
            rows = _rows(workspace)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["state"], "DISPATCHING")
            self.assertEqual(rows[0]["fence_status"], "none")
            self.assertEqual(rows[0]["baseline_digest"], started["baseline_digest"])
            artifact = baseline_artifact_path(workspace, "TASK-001", started["attempt_id"])
            self.assertTrue(artifact.is_file())
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            self.assertEqual(payload["attempt_id"], started["attempt_id"])
            self.assertEqual(payload["lease_id"], started["lease_id"])
            status = run_cli("status", "--workspace", str(workspace))
            task = next(item for item in status["tasks"] if item["id"] == "TASK-001")
            self.assertEqual(task["execution_attempt"]["attempt_id"], started["attempt_id"])
            self.assertEqual(len(status["live_execution_attempts"]), 1)
            cleanup_worktree(repo, workspace)

    def test_start_refuses_without_a_prepared_worktree(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            refused = run_cli(
                "start", "TASK-001", "--workspace", str(workspace), "--actor", "worker", expect=2
            )
            self.assertIn("CONTRACTED", refused["error"])
            self.assertEqual(_rows(workspace), [])

    def test_resume_judges_effects_against_the_original_baseline_not_the_tree(self) -> None:
        """Worker writes, host dies: the effect is still attributable on resume."""
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            started, worktree, _ = _start(temp, workspace)
            (worktree / "docs").mkdir(parents=True, exist_ok=True)
            (worktree / "docs" / "result.txt").write_text("ok\n", encoding="utf-8")
            # "Resume": reopen state, load the persisted baseline, compare.
            db = StateDB(workspace / "runtime" / "state.sqlite")
            try:
                attempt = db.live_execution_attempt("TASK-001")
            finally:
                db.close()
            assert attempt is not None
            baseline = load_baseline_artifact(Path(attempt["baseline_path"]), attempt=attempt)
            self.assertNotIn("docs/result.txt", baseline)
            self.assertEqual(effected_paths(worktree, baseline), ["docs/result.txt"])
            cleanup_worktree(repo, workspace)

    def test_a_result_for_the_live_attempt_is_recorded_and_settles_it(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            started, worktree, contract = _start(temp, workspace)
            (worktree / "docs").mkdir(parents=True, exist_ok=True)
            (worktree / "docs" / "result.txt").write_text("ok\n", encoding="utf-8")
            recorded = run_cli(
                "record-attempt",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--receipt",
                str(_receipt(temp, contract)),
            )
            self.assertEqual(recorded["attempt_id"], started["attempt_id"])
            self.assertEqual(recorded["attempt"], 1)
            row = _rows(workspace)[0]
            self.assertEqual(row["state"], "TERMINAL")
            self.assertEqual(row["terminal_status"], "SUBMITTED")
            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(verification["execution_attempt_id"], started["attempt_id"])
            self.assertEqual(_rows(workspace)[0]["terminal_status"], "PASSED_LOCAL")
            cleanup_worktree(repo, workspace)

    def test_legacy_executing_task_with_no_attempt_fails_closed(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            _, worktree, contract = _start(temp, workspace)
            conn = sqlite3.connect(workspace / "runtime" / "state.sqlite")
            conn.execute("DELETE FROM execution_attempts")
            conn.commit()
            conn.close()
            refused = run_cli(
                "record-attempt",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--receipt",
                str(_receipt(temp, contract)),
                expect=2,
            )
            self.assertEqual(refused["error_code"], "RUNTIME_RECONCILIATION_REQUIRED")
            status = run_cli("status", "--workspace", str(workspace))
            task = next(item for item in status["tasks"] if item["id"] == "TASK-001")
            self.assertEqual(task["runtime_state"], "EXECUTING")
            self.assertIsNone(task["execution_attempt"])
            cleanup_worktree(repo, workspace)

    def test_a_fenced_attempt_cannot_contribute_a_result(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            _, _, contract = _start(temp, workspace)
            conn = sqlite3.connect(workspace / "runtime" / "state.sqlite")
            conn.execute("UPDATE execution_attempts SET fence_status='fenced'")
            conn.commit()
            conn.close()
            refused = run_cli(
                "record-attempt",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--receipt",
                str(_receipt(temp, contract)),
                expect=2,
            )
            self.assertEqual(refused["error_code"], "STALE_ATTEMPT_RESULT")
            cleanup_worktree(repo, workspace)

    def test_a_result_under_a_released_lease_is_refused(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            _, _, contract = _start(temp, workspace)
            run_cli(
                "release-lease",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--reason",
                "operator",
                "--actor",
                "operator",
            )
            refused = run_cli(
                "record-attempt",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--receipt",
                str(_receipt(temp, contract)),
                expect=2,
            )
            self.assertEqual(refused["error_code"], "STALE_LEASE_RESULT")
            cleanup_worktree(repo, workspace)

    def test_a_result_that_does_not_bind_the_attempt_contract_is_refused(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            _, _, contract = _start(temp, workspace)
            conn = sqlite3.connect(workspace / "runtime" / "state.sqlite")
            conn.execute("UPDATE execution_attempts SET base_sha='0000000000'")
            conn.commit()
            conn.close()
            refused = run_cli(
                "record-attempt",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--receipt",
                str(_receipt(temp, contract)),
                expect=2,
            )
            self.assertEqual(refused["error_code"], "STALE_ATTEMPT_RESULT")
            cleanup_worktree(repo, workspace)

    def test_a_corrupted_or_rebound_baseline_fails_closed(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            started, _, _ = _start(temp, workspace)
            db = StateDB(workspace / "runtime" / "state.sqlite")
            try:
                attempt = db.live_execution_attempt("TASK-001")
            finally:
                db.close()
            assert attempt is not None
            artifact = Path(attempt["baseline_path"])
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            payload["baseline"] = {"docs/result.txt": "file:deadbeef"}
            artifact.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ControllerError) as caught:
                load_baseline_artifact(artifact, attempt=attempt)
            self.assertEqual(caught.exception.error_code, "EXECUTION_BASELINE_MISSING")
            artifact.unlink()
            with self.assertRaises(ControllerError) as caught:
                load_baseline_artifact(artifact, attempt=attempt)
            self.assertEqual(caught.exception.error_code, "EXECUTION_BASELINE_MISSING")
            # A baseline for a different base revision is refused too.
            with self.assertRaises(ControllerError):
                load_baseline_artifact(
                    baseline_artifact_path(workspace, "TASK-001", started["attempt_id"]),
                    attempt={**attempt, "base_sha": "other"},
                )
            cleanup_worktree(repo, workspace)

    def test_failure_settles_the_attempt_and_a_retry_mints_a_successor(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            first, _, _ = _start(temp, workspace)
            run_cli(
                "fail",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--reason",
                "provider died",
                "--actor",
                "worker",
            )
            rows = _rows(workspace)
            self.assertEqual(rows[0]["state"], "TERMINAL")
            self.assertEqual(rows[0]["terminal_status"], "FAILED")
            # A retry re-claims, re-prepares and starts again: a NEW attempt, number 2.
            second, _, _ = _start(temp, workspace)
            self.assertNotEqual(second["attempt_id"], first["attempt_id"])
            self.assertEqual(second["attempt_number"], 2)
            self.assertEqual(len(_rows(workspace)), 2)
            cleanup_worktree(repo, workspace)

    def test_bind_dispatch_records_provider_correlation_on_the_live_attempt(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            started, _, _ = _start(temp, workspace)
            bound = run_cli(
                "bind-dispatch",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--provider-execution-id",
                "dispatch-42",
                "--provider-ref",
                "stub-provider",
            )
            self.assertEqual(bound["attempt_id"], started["attempt_id"])
            self.assertEqual(bound["state"], "RUNNING")
            self.assertEqual(bound["provider_execution_id"], "dispatch-42")
            run_cli(
                "fail",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--reason",
                "x",
                "--actor",
                "worker",
            )
            refused = run_cli(
                "bind-dispatch",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--provider-execution-id",
                "dispatch-43",
                expect=2,
            )
            self.assertEqual(refused["error_code"], "STALE_ATTEMPT_RESULT")
            cleanup_worktree(repo, workspace)

    def test_relocking_an_in_flight_definition_abandons_its_attempt(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            blueprint, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            _start(temp, workspace)
            import yaml

            path = blueprint / "TASK_CARDS.yaml"
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            doc["tasks"][0]["objective"] = "edited mid-flight"
            path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
            run_cli("relock", "--workspace", str(workspace), "--actor", "operator")
            row = _rows(workspace)[0]
            self.assertEqual(row["state"], "ABANDONED")
            self.assertEqual(row["reason"], "definition_relocked")
            cleanup_worktree(repo, workspace)


if __name__ == "__main__":
    unittest.main()
