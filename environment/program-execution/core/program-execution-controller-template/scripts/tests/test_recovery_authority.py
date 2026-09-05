"""PEC-P0-001: only Controller recovery may take execution authority away.

`fresh-workspace` is a presentation over `recover_execution`: every affected
attempt is fenced and its evidence preserved BEFORE any worktree or branch is
destroyed, the lease is released, the task lands on STALE (never ELIGIBLE --
readiness is recomputed by the next claim), and a stale worker's late result is
identity-refused afterwards.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from helpers import (
    CONTROLLER_ROOT,
    SCRIPTS,
    bootstrap_repo,
    cleanup_worktree,
    register_contract,
    run_cli,
    write_json,
)

sys.path.insert(0, str(SCRIPTS))
from pec import controller as pec_controller  # noqa: E402
from pec.common import ControllerError  # noqa: E402


def _rows(workspace: Path, table: str) -> list[dict[str, Any]]:
    conn = sqlite3.connect(workspace / "runtime" / "state.sqlite")
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]  # nosec B608 - test
    finally:
        conn.close()


def _task_state(workspace: Path, task_id: str = "TASK-001") -> str:
    status = run_cli("status", "--workspace", str(workspace))
    return str(next(t for t in status["tasks"] if t["id"] == task_id)["runtime_state"])


def _start(temp: Path, workspace: Path, task_id: str = "TASK-001") -> tuple[dict, Path, dict]:
    run_cli("claim", task_id, "--workspace", str(workspace), "--holder", "worker")
    prepared = run_cli("prepare", task_id, "--workspace", str(workspace))
    rendered = run_cli("render-contract", task_id, "--workspace", str(workspace))
    started = run_cli("start", task_id, "--workspace", str(workspace), "--actor", "worker")
    contract = json.loads(Path(rendered["contract"]).read_text(encoding="utf-8"))
    return started, Path(prepared["worktree"]), contract


def _receipt(temp: Path, contract: dict[str, Any]) -> Path:
    return write_json(
        temp / "late-attempt.json",
        {
            "schema": "program-execution-controller.attempt-receipt.v2",
            "task_id": "TASK-001",
            "contract_digest": contract["contract_digest"],
            "program_digest": contract["program_digest"],
            "base_sha": contract["base_sha"],
            "candidate_sha": None,
            "changed_files": ["docs/result.txt"],
            "validation_results": [
                {"command": c, "status": "PASS", "exit_code": 0, "evidence": "late"}
                for c in contract["validation_commands"]
            ],
            "produced_evidence": [],
            "residual_unknowns": [],
            "claimed_status": "completed",
        },
    )


def _ledger_types(workspace: Path) -> list[str]:
    lines = (workspace / "ledger" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line)["type"] for line in lines if line.strip()]


class FreshWorkspaceAuthorityTests(unittest.TestCase):
    def test_fresh_workspace_is_not_a_direct_front_door(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            env = {
                k: v
                for k, v in os.environ.items()
                if k not in {"L9_ALLOW_PEC_DIRECT", "L9_CAMPAIGN_TUNNEL"}
            }
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "pec.py"),
                    "fresh-workspace",
                    "--workspace",
                    str(workspace),
                    "--repository",
                    str(repo),
                ],
                cwd=CONTROLLER_ROOT,
                text=True,
                capture_output=True,
                check=False,
                env=env,
                timeout=45,
            )
            self.assertEqual(completed.returncode, 2, completed.stdout)
            self.assertIn("not a live campaign front door", completed.stdout)

    def test_reset_fences_preserves_releases_and_lands_stale_not_eligible(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            started, worktree, contract = _start(temp, workspace)
            (worktree / "docs").mkdir(parents=True, exist_ok=True)
            (worktree / "docs" / "result.txt").write_text("half-written\n", encoding="utf-8")

            report = run_cli(
                "fresh-workspace",
                "--workspace",
                str(workspace),
                "--repository",
                str(repo),
                "--reason",
                "operator reset",
            )
            item = report["recovery"]["items"][0]
            self.assertEqual(item["status"], "RECOVERED")
            self.assertEqual(item["attempt_fenced"], started["attempt_id"])
            self.assertEqual(item["lease_released"], started["lease_id"])
            self.assertEqual(item["runtime_state"], "STALE")
            self.assertEqual(item["fence_proof"], "identity_fence_only")
            # Evidence preserved BEFORE destruction.
            artifact = Path(item["artifact"])
            metadata = json.loads((artifact / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["execution_attempt"]["attempt_id"], started["attempt_id"])
            self.assertEqual(metadata["baseline"]["digest"], started["baseline_digest"])
            self.assertEqual(metadata["lease"]["lease_id"], started["lease_id"])
            self.assertIn("docs/result.txt", (artifact / "untracked.txt").read_text())
            self.assertEqual(
                (artifact / "untracked" / "docs" / "result.txt").read_text(), "half-written\n"
            )
            # Destroyed only afterwards.
            self.assertFalse(worktree.exists())
            attempt = _rows(workspace, "execution_attempts")[0]
            self.assertEqual(attempt["state"], "FENCED")
            self.assertEqual(attempt["fence_status"], "fenced")
            self.assertEqual([r for r in _rows(workspace, "leases") if r["active"]], [])
            self.assertEqual(_task_state(workspace), "STALE")
            self.assertIn("EXECUTION_RECOVERED", _ledger_types(workspace))

            # A stale worker's late result is identity-refused.
            refused = run_cli(
                "record-attempt",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--receipt",
                str(_receipt(temp, contract)),
                expect=2,
            )
            # Refused on identity (fenced attempt / released lease) or, earlier
            # still, on the task no longer being EXECUTING at all.
            self.assertTrue(
                refused.get("error_code")
                in {"RUNTIME_RECONCILIATION_REQUIRED", "STALE_ATTEMPT_RESULT", "STALE_LEASE_RESULT"}
                or "STALE" in refused["error"],
                refused,
            )
            # And ELIGIBLE is reached only through readiness, at the next claim.
            successor, _, _ = _start(temp, workspace)
            self.assertNotEqual(successor["attempt_id"], started["attempt_id"])
            self.assertEqual(successor["attempt_number"], 2)
            self.assertEqual(_rows(workspace, "execution_attempts")[0]["state"], "FENCED")
            cleanup_worktree(repo, workspace)

    def test_late_result_after_successor_lease_is_refused_for_the_old_attempt(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            _, _, old_contract = _start(temp, workspace)
            run_cli(
                "recover-execution",
                "--workspace",
                str(workspace),
                "--actor",
                "operator",
                "--reason",
                "host lost",
            )
            successor, worktree, new_contract = _start(temp, workspace)
            # The old worker's receipt binds the old contract digest only if
            # the contract was re-rendered; either way the attempt/lease binding
            # decides, and the successor attempt is the only live one.
            refused = run_cli(
                "record-attempt",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--receipt",
                str(_receipt(temp, {**old_contract, "base_sha": "0" * 40})),
                expect=2,
            )
            self.assertIn("mismatch", refused["error"].lower())
            cleanup_worktree(repo, workspace)

    def test_repeated_recovery_is_idempotent(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            _start(temp, workspace)
            first = run_cli(
                "fresh-workspace", "--workspace", str(workspace), "--repository", str(repo)
            )
            second = run_cli(
                "fresh-workspace", "--workspace", str(workspace), "--repository", str(repo)
            )
            self.assertEqual(first["recovery"]["items"][0]["status"], "RECOVERED")
            self.assertEqual(second["recovery"]["items"], [])
            self.assertEqual(_ledger_types(workspace).count("EXECUTION_RECOVERED"), 1)
            self.assertEqual(
                len([r for r in _rows(workspace, "evidence") if "RECOVERY" in r["id"]]), 1
            )

    def test_lease_without_worktree_is_still_fenced_and_released(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            report = run_cli(
                "recover-execution",
                "--workspace",
                str(workspace),
                "--actor",
                "operator",
                "--reason",
                "lease only",
            )
            item = report["items"][0]
            self.assertEqual(item["status"], "RECOVERED")
            self.assertIsNotNone(item["lease_released"])
            self.assertIsNone(item["attempt_fenced"])
            self.assertEqual(_task_state(workspace), "STALE")

    def test_unregistered_worktree_without_lease_is_swept_by_mechanics(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            orphan = workspace / "worktrees" / "TASK-001"
            orphan.mkdir(parents=True)
            (orphan / "leftover.txt").write_text("x\n", encoding="utf-8")
            report = run_cli(
                "fresh-workspace", "--workspace", str(workspace), "--repository", str(repo)
            )
            self.assertFalse(orphan.exists())
            item = report["recovery"]["items"][0]
            self.assertEqual(item["status"], "RECOVERED")
            self.assertIn("leftover.txt", (Path(item["artifact"]) / "untracked.txt").read_text())

    def test_recovery_fails_closed_when_evidence_cannot_be_preserved(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            started, worktree, _ = _start(temp, workspace)
            original = pec_controller.run_git

            def broken(repo_path: Path, *args: str, check: bool = True) -> Any:
                if args and args[0] == "diff":
                    raise RuntimeError("worktree unreadable")
                return original(repo_path, *args, check=check)

            pec_controller.run_git = broken  # type: ignore[assignment]
            try:
                with self.assertRaises(RuntimeError):
                    pec_controller.recover_execution(
                        workspace, "operator", reason="test", repository=repo
                    )
            finally:
                pec_controller.run_git = original  # type: ignore[assignment]
            self.assertTrue(worktree.is_dir(), "worktree destroyed without evidence")
            self.assertEqual(_rows(workspace, "execution_attempts")[0]["state"], "DISPATCHING")
            self.assertEqual(_task_state(workspace), "EXECUTING")
            cleanup_worktree(repo, workspace)

    def test_provider_terminated_flag_is_recorded_as_fence_proof(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            _start(temp, workspace)
            report = run_cli(
                "recover-execution",
                "--workspace",
                str(workspace),
                "--actor",
                "operator",
                "--reason",
                "cancelled",
                "--provider-terminated",
                "--keep-worktrees",
            )
            item = report["items"][0]
            self.assertEqual(item["fence_proof"], "provider_terminated_confirmed")
            self.assertTrue((workspace / "worktrees" / "TASK-001").is_dir())
            cleanup_worktree(repo, workspace)

    def test_workspace_reset_module_holds_no_state_authority(self) -> None:
        with self.assertRaises(ControllerError):
            raise ControllerError("sentinel")  # keeps the import used
        from pec import workspace_reset

        self.assertFalse(hasattr(workspace_reset, "_release_open_leases"))
        self.assertNotIn(
            "release_leases", workspace_reset.fresh_execution_workspace.__code__.co_varnames
        )


if __name__ == "__main__":
    unittest.main()
