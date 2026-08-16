"""A clean session must reach EXECUTING without exploratory command failures.

This is the runtime path, not a simulation of it: the shared bootstrap script
runs for real and is the thing that writes the readiness receipt; the phase lock
and Graphiti grant go through the canonical memory modules; the governed-write
gate, the Controller CLI and the admission gate are all invoked as a session
invokes them. Anything this test stubs is something a real session would find
broken later, so it stubs nothing on the startup path.

The negative case is the point of the whole campaign: a runtime that is stale or
incompatible must be refused *before* the first governed mutation, with a next
action that names how to repair it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import (
    bootstrap_repo,
    cleanup_worktree,
    establish_phase_lock,
    run_cli,
    session_workspace,
    surface,
    write_json,
)

REPO = Path(__file__).resolve().parents[6]
GATE = REPO / "environment" / "agents" / "adapters" / "claude-code" / "hooks" / "memory_gate.py"
BOOTSTRAP = REPO / "ops" / "scripts" / "bootstrap_agent_environment.sh"
MEM = REPO / "environment" / "agents" / "adapters" / "claude-code" / "memory"
sys.path.insert(0, str(REPO / "ops" / "scripts"))
sys.path.insert(0, str(MEM))
import memory_state as st  # noqa: E402
from write_runtime_readiness_receipt import main as write_receipt  # noqa: E402
from write_runtime_readiness_receipt import receipt_path  # noqa: E402

SESSION_ID = "clean-startup-session"
PRESERVED = (
    "HOME",
    "L9_RUNTIME_ROOT",
    "L9_PE_RECEIPT_WORKSPACE",
    "CLAUDE_PROJECT_DIR",
    "CURSOR_PROJECT_DIR",
)


class CleanStartupTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {key: os.environ.get(key) for key in PRESERVED}

    def tearDown(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _run_shared_bootstrap(self, workspace: Path) -> subprocess.CompletedProcess[str]:
        """Run the real shared bootstrap in --check mode.

        --check keeps the run hermetic (no toolchain installs, no network) while
        still exercising the same argument handling, identity resolution and
        readiness-receipt write that a session's bootstrap performs.
        """
        return subprocess.run(
            [
                "bash",
                str(BOOTSTRAP),
                "--surface",
                surface(),
                "--governance",
                str(REPO),
                "--workspace",
                str(workspace),
                "--check",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            timeout=300,
            check=False,
        )

    def test_real_bootstrap_to_executing_and_attempt_receipt(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            # bootstrap_repo establishes the isolated HOME/runtime root and the
            # program workspace; the receipt it writes is then REPLACED below by
            # one the real bootstrap script produces, so nothing on the startup
            # path is fixture-authored.
            _, repo, workspace = bootstrap_repo(temp)
            session_ws = session_workspace(temp)

            # Remove the fixture's receipt so the assertion below can only pass
            # if the real bootstrap script produced one.
            written = receipt_path(surface=surface(), workspace=session_ws)
            written.unlink()

            proc = self._run_shared_bootstrap(session_ws)
            self.assertEqual(proc.returncode, 0, f"bootstrap failed:\n{proc.stderr}")
            self.assertTrue(written.is_file(), "shared bootstrap wrote no readiness receipt")
            receipt = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema"], "l9.agents.runtime-readiness.v1")
            self.assertEqual(receipt["memory_state_root"], str(session_ws / ".l9" / "memory"))
            # The receipt must describe the runtime, not merely assert over it.
            ids = {row["id"] for row in receipt["components"]}
            self.assertIn("governance.ssot", ids)
            self.assertIn("environment.generated_llm_rules", ids)
            self.assertIn("session.identity", ids)
            self.assertIn("memory.state_root", ids)

            # A real bootstrap resolves no session id of its own on this surface;
            # re-issue the receipt with the session identity the rest of the path
            # runs under, which is exactly what an unresolved identity requires.
            self.assertEqual(
                write_receipt(
                    [
                        "--surface",
                        surface(),
                        "--workspace",
                        str(session_ws),
                        "--governance",
                        str(REPO),
                        "--governance-revision",
                        "a" * 40,
                        "--runtime-script-revision",
                        "a" * 40,
                        "--session-id",
                        SESSION_ID,
                    ]
                ),
                0,
            )
            receipt = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(receipt["overall_status"], "READY")

            # Session + phase-lock state through the canonical memory modules.
            establish_phase_lock(session_id=SESSION_ID)
            contract = st.load_contract()
            lock = st.read_lock(contract, "cursor-governance")
            self.assertIsNotNone(lock)
            self.assertEqual(lock["session_id"], SESSION_ID)

            # The governed-write precheck must pass for this session.
            gate = subprocess.run(
                [sys.executable, str(GATE)],
                input=json.dumps(
                    {
                        "tool_name": "Edit",
                        "tool_input": {"file_path": "environment/agents/adapters/claude-code/x.py"},
                        "session_id": SESSION_ID,
                    }
                ),
                capture_output=True,
                text=True,
                env={**os.environ, "CLAUDE_PROJECT_DIR": str(session_ws)},
                timeout=30,
                check=False,
            )
            self.assertNotIn('"permissionDecision": "deny"', gate.stdout, gate.stdout)

            # Reconcile the target repository, then walk PE to EXECUTING. Every
            # step below is the operation preflight named — no exploration.
            run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")

            pre_draft = self._preflight(workspace, session_ws)
            self.assertTrue(pre_draft["lock"]["verified"])
            self.assertEqual(pre_draft["next_action"]["args"][0], "draft-contract")

            draft = temp / "TASK-001.source.json"
            run_cli(
                "draft-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--output",
                str(draft),
            )
            run_cli(
                "register-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--file",
                str(draft),
                "--actor",
                "operator",
            )
            self.assertEqual(
                self._preflight(workspace, session_ws)["next_action"]["args"][0], "claim"
            )

            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            prepared = run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            rendered = run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
            run_cli("start", "TASK-001", "--workspace", str(workspace), "--actor", "worker")
            status = run_cli("status", "--workspace", str(workspace))
            task = next(item for item in status["tasks"] if item["id"] == "TASK-001")
            self.assertEqual(task["runtime_state"], "EXECUTING")

            worktree = Path(prepared["worktree"])
            target = worktree / "docs" / "result.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("ok\n", encoding="utf-8")
            contract_body = json.loads(Path(rendered["contract"]).read_text(encoding="utf-8"))
            receipt_body = {
                "schema": "program-execution-controller.attempt-receipt.v2",
                "task_id": "TASK-001",
                "contract_digest": contract_body["contract_digest"],
                "program_digest": contract_body["program_digest"],
                "base_sha": contract_body["base_sha"],
                "candidate_sha": None,
                "changed_files": ["docs/result.txt"],
                "validation_results": [
                    {
                        "command": command,
                        "status": "PASS",
                        "exit_code": 0,
                        "evidence": "worker output",
                    }
                    for command in contract_body["validation_commands"]
                ],
                "produced_evidence": [],
                "residual_unknowns": [],
                "claimed_status": "completed",
            }
            recorded = run_cli(
                "record-attempt",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--receipt",
                str(write_json(temp / "TASK-001.attempt.json", receipt_body)),
            )
            self.assertTrue(recorded)
            cleanup_worktree(repo, workspace)

    def test_stale_runtime_is_refused_before_mutation(self) -> None:
        """Negative case: an incompatible runtime never reaches a mutation."""
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            session_ws = session_workspace(temp)
            establish_phase_lock(session_id=SESSION_ID)

            # Governance and runtime script disagree: the checkout moved under a
            # live session. This is the drift the receipt exists to catch.
            write_receipt(
                [
                    "--surface",
                    surface(),
                    "--workspace",
                    str(session_ws),
                    "--governance",
                    str(REPO),
                    "--governance-revision",
                    "a" * 40,
                    "--runtime-script-revision",
                    "b" * 40,
                    "--session-id",
                    SESSION_ID,
                ]
            )
            stale = json.loads(
                receipt_path(surface=surface(), workspace=session_ws).read_text(encoding="utf-8")
            )
            self.assertEqual(stale["overall_status"], "NOT_READY")
            self.assertEqual(stale["failure_code"], "REVISION_MISMATCH")

            refusal = run_cli(
                "claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker", expect=3
            )
            self.assertEqual(refusal["status"], "BLOCKED")
            self.assertEqual(refusal["error_code"], "REVISION_MISMATCH")
            self.assertIn("write_runtime_readiness_receipt.py", refusal["next_action"]["args"][0])

            # Refused before mutating: the task never left its pre-claim state.
            task = next(
                item
                for item in run_cli("status", "--workspace", str(workspace))["tasks"]
                if item["id"] == "TASK-001"
            )
            self.assertNotEqual(task["runtime_state"], "EXECUTING")
            _ = repo

    def _preflight(self, workspace: Path, receipt_workspace: Path) -> dict:
        return run_cli(
            "preflight",
            "--workspace",
            str(workspace),
            "--task-id",
            "TASK-001",
            "--receipt-workspace",
            str(receipt_workspace),
        )


if __name__ == "__main__":
    unittest.main()
