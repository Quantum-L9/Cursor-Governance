from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import (
    READINESS_SESSION,
    bootstrap_repo,
    establish_phase_lock,
    establish_runtime_readiness,
    register_contract,
    run_cli,
    session_workspace,
    surface,
)

REPO = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO / "ops" / "scripts"))
from write_runtime_readiness_receipt import main as write_receipt  # noqa: E402


class PreflightTests(unittest.TestCase):
    """Preflight must name the exact next legal operation.

    ``bootstrap_repo`` establishes the READY session receipt; the phase lock is
    established separately so each test can withhold it and assert the specific
    blocker rather than a generic failure.
    """

    def tearDown(self) -> None:
        for key in ("CURSOR_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
            os.environ.pop(key, None)

    def _preflight(self, workspace: Path, receipt_workspace: Path, *task: str) -> dict:
        return run_cli(
            "preflight",
            "--workspace",
            str(workspace),
            *task,
            "--receipt-workspace",
            str(receipt_workspace),
        )

    def test_missing_receipt_does_not_mutate(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            # The fixture repo is not the session workspace, so no receipt is
            # keyed to it — the missing-receipt path this test is about.
            result = self._preflight(workspace, repo, "--task-id", "TASK-001")
            self.assertFalse(result["ready"])
            tokens = [row["token"] for row in result["blockers"]]
            self.assertIn("runtime_receipt_missing", tokens)
            self.assertEqual(result["next_action"]["command"], "python3")
            self.assertIn("write_runtime_readiness_receipt.py", result["next_action"]["args"][0])

    def test_not_ready_receipt_refuses_mutation(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            write_receipt(
                [
                    "--surface",
                    surface(),
                    "--workspace",
                    str(repo),
                    "--governance",
                    str(REPO),
                    "--governance-revision",
                    "aaa111",
                    "--runtime-script-revision",
                    "bbb222",
                    "--session-id",
                    READINESS_SESSION,
                ]
            )
            result = self._preflight(workspace, repo)
            self.assertFalse(result["ready"])
            self.assertIn("runtime_receipt_not_ready", [row["token"] for row in result["blockers"]])
            self.assertEqual(result["blockers"][0]["error_code"], "REVISION_MISMATCH")

    def test_degraded_receipt_refuses_mutation(self) -> None:
        """DEGRADED is not READY: a half-provisioned runtime may not mutate."""
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            write_receipt(
                [
                    "--surface",
                    surface(),
                    "--workspace",
                    str(repo),
                    "--governance",
                    str(REPO),
                    "--governance-revision",
                    "a" * 40,
                    "--runtime-script-revision",
                    "a" * 40,
                    "--session-id",
                    READINESS_SESSION,
                    "--degraded-count",
                    "2",
                ]
            )
            result = self._preflight(workspace, repo)
            self.assertFalse(result["ready"])
            self.assertIn("runtime_receipt_not_ready", [row["token"] for row in result["blockers"]])

    def test_phase_lock_missing_names_acquire(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            result = self._preflight(workspace, session_workspace(temp), "--task-id", "TASK-001")
            self.assertFalse(result["ready"])
            tokens = [row["token"].split(":", 1)[0] for row in result["blockers"]]
            self.assertIn("phase_lock_missing", tokens)
            self.assertFalse(result["lock"]["verified"])
            self.assertEqual(result["next_action"]["command"], "python3")
            self.assertIn("memory_lock.py", result["next_action"]["args"][0])
            self.assertIn("acquire", result["next_action"]["args"])
            self.assertIn(READINESS_SESSION, result["next_action"]["args"])

    def test_ungranted_lock_is_not_a_lock(self) -> None:
        """A local lock artifact without a Graphiti grant is an unbacked claim."""
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            establish_phase_lock(granted=False)
            result = self._preflight(workspace, session_workspace(temp))
            tokens = [row["token"].split(":", 1)[0] for row in result["blockers"]]
            self.assertIn("phase_lock_not_granted", tokens)

    def test_graphiti_grant_absent_is_blocked(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            establish_phase_lock(graphiti_satisfied=False)
            result = self._preflight(workspace, session_workspace(temp))
            tokens = [row["token"] for row in result["blockers"]]
            self.assertIn("graphiti_phase_lock_unsatisfied", tokens)

    def test_lock_held_by_other_session_is_blocked(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            establish_phase_lock(session_id="a-different-session")
            result = self._preflight(workspace, session_workspace(temp))
            tokens = [row["token"].split(":", 1)[0] for row in result["blockers"]]
            self.assertIn("phase_lock_session_mismatch", tokens)

    def test_source_contract_incomplete_names_draft(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            establish_phase_lock()
            result = self._preflight(workspace, session_workspace(temp), "--task-id", "TASK-001")
            self.assertFalse(result["ready"])
            tokens = [row["token"] for row in result["blockers"]]
            self.assertIn("source_contract_incomplete", tokens)
            self.assertTrue(result["lock"]["verified"])
            self.assertEqual(result["next_action"]["command"], "pec")
            self.assertEqual(result["next_action"]["args"][0], "draft-contract")

    def test_after_register_names_claim(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            establish_phase_lock()
            register_contract(temp, workspace)
            result = self._preflight(workspace, session_workspace(temp), "--task-id", "TASK-001")
            tokens = [row["token"] for row in result["blockers"]]
            self.assertIn("lease_missing", tokens)
            self.assertEqual(result["next_action"]["args"][0], "claim")

    def test_lock_identity_mismatch(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            establish_phase_lock()
            os.environ["CLAUDE_PROJECT_DIR"] = str(temp / "a")
            os.environ["CURSOR_PROJECT_DIR"] = str(temp / "b")
            result = self._preflight(workspace, session_workspace(temp))
            tokens = [row["token"] for row in result["blockers"]]
            self.assertIn("lock_identity_mismatch", tokens)
            self.assertEqual(result["blockers"][0]["error_code"], "LOCK_IDENTITY_MISMATCH")

    def test_dirty_repo_named(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            establish_phase_lock()
            (repo / "dirty.txt").write_text("x\n", encoding="utf-8")
            run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")
            result = self._preflight(workspace, session_workspace(temp))
            tokens = [row["token"] for row in result["blockers"]]
            self.assertIn("repository_dirty", tokens)


class RuntimeAdmissionTests(unittest.TestCase):
    """Mutating commands are refused without a READY receipt; reads still work."""

    def test_mutating_command_refused_without_receipt(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            # Point admission at a workspace no receipt was ever written for.
            os.environ["L9_PE_RECEIPT_WORKSPACE"] = str(temp / "unprovisioned")
            try:
                refusal = run_cli(
                    "claim",
                    "TASK-001",
                    "--workspace",
                    str(workspace),
                    "--holder",
                    "worker",
                    expect=3,
                )
            finally:
                os.environ["L9_PE_RECEIPT_WORKSPACE"] = str(session_workspace(temp))
            self.assertEqual(refusal["status"], "BLOCKED")
            self.assertEqual(refusal["error_code"], "RUNTIME_RECEIPT_MISSING")
            self.assertIn("write_runtime_readiness_receipt.py", refusal["next_action"]["args"][0])
            _ = repo

    def test_degraded_runtime_refuses_mutation_but_allows_diagnosis(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            establish_runtime_readiness(temp, degraded_count=3)
            refusal = run_cli(
                "claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker", expect=3
            )
            self.assertEqual(refusal["overall_status"], "DEGRADED")
            self.assertEqual(refusal["command"], "claim")
            # The diagnostic path must stay open, or the refusal is unclearable.
            self.assertIn("tasks", run_cli("status", "--workspace", str(workspace)))
            self.assertIn("blockers", self._preflight_ok(workspace, temp))

    def test_writing_commands_are_not_classified_read_only(self) -> None:
        """Exemption is by observed write behavior, not by how diagnostic it sounds.

        ``export-handoff`` writes runtime/campaign-status.json and
        ``draft-contract`` writes a draft plus opens the runtime, so neither may
        be exempt; the four genuine read-only diagnostics must stay reachable.
        """
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from pec.admission import READ_ONLY_COMMANDS, is_mutating

        for command in ("export-handoff", "draft-contract", "claim", "record-attempt", "close"):
            self.assertTrue(is_mutating(command), command)
            self.assertNotIn(command, READ_ONLY_COMMANDS)
        for command in ("status", "next", "preflight", "validate"):
            self.assertFalse(is_mutating(command), command)

    def _preflight_ok(self, workspace: Path, temp: Path) -> dict:
        return run_cli(
            "preflight",
            "--workspace",
            str(workspace),
            "--receipt-workspace",
            str(session_workspace(temp)),
        )


if __name__ == "__main__":
    unittest.main()
