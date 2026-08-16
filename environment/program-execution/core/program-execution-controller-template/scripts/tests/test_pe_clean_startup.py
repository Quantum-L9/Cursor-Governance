from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, cleanup_worktree, run_cli, write_json

REPO = Path(__file__).resolve().parents[6]
GATE = REPO / "environment" / "agents" / "adapters" / "claude-code" / "hooks" / "memory_gate.py"
MEM = REPO / "environment" / "agents" / "adapters" / "claude-code" / "memory"
sys.path.insert(0, str(REPO / "ops" / "scripts"))
sys.path.insert(0, str(MEM))
import memory_state as st  # noqa: E402
from write_runtime_readiness_receipt import main as write_receipt  # noqa: E402


class CleanStartupTests(unittest.TestCase):
    def setUp(self) -> None:
        self._home = os.environ.get("HOME")
        self._runtime = os.environ.get("L9_RUNTIME_ROOT")
        self._claude = os.environ.get("CLAUDE_PROJECT_DIR")
        self._cursor = os.environ.get("CURSOR_PROJECT_DIR")

    def tearDown(self) -> None:
        for key, value in (
            ("HOME", self._home),
            ("L9_RUNTIME_ROOT", self._runtime),
            ("CLAUDE_PROJECT_DIR", self._claude),
            ("CURSOR_PROJECT_DIR", self._cursor),
        ):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_clean_temp_reaches_executing_and_attempt_receipt(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            home = temp / "home"
            home.mkdir()
            os.environ["HOME"] = str(home)
            os.environ["L9_RUNTIME_ROOT"] = str(temp / "l9")
            agent_ws = temp / "agent-ws"
            agent_ws.mkdir()
            os.environ["CLAUDE_PROJECT_DIR"] = str(agent_ws)
            os.environ["CURSOR_PROJECT_DIR"] = str(agent_ws)
            session_id = "clean-startup-session"
            blueprint, repo, workspace = bootstrap_repo(temp)
            sha = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            self.assertEqual(
                write_receipt(
                    [
                        "--surface",
                        "cursor",
                        "--workspace",
                        str(repo),
                        "--governance-revision",
                        sha,
                        "--runtime-script-revision",
                        sha,
                        "--bound-sha",
                        sha,
                        "--session-id",
                        session_id,
                    ]
                ),
                0,
            )
            contract = st.load_contract()
            st.write_receipt(contract, session_id, {"namespaces": ["cursor-governance"]})
            st.write_lock(contract, "cursor-governance", session_id, "sig")
            lock_path = st.lock_path(contract, "cursor-governance")
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            lock["transport"] = "cursor-graphiti-phase-lock"
            lock["granted"] = True
            lock_path.write_text(json.dumps(lock) + "\n", encoding="utf-8")
            gate = subprocess.run(
                [sys.executable, str(GATE)],
                input=json.dumps(
                    {
                        "tool_name": "Edit",
                        "tool_input": {"file_path": "environment/agents/adapters/claude-code/x.py"},
                        "session_id": session_id,
                    }
                ),
                capture_output=True,
                text=True,
                env={**os.environ, "CLAUDE_PROJECT_DIR": str(agent_ws)},
                timeout=15,
                check=False,
            )
            self.assertNotIn('"permissionDecision": "deny"', gate.stdout, gate.stdout)

            pre_draft = run_cli(
                "preflight",
                "--workspace",
                str(workspace),
                "--task-id",
                "TASK-001",
                "--receipt-workspace",
                str(repo),
            )
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
            pre_claim = run_cli(
                "preflight",
                "--workspace",
                str(workspace),
                "--task-id",
                "TASK-001",
                "--receipt-workspace",
                str(repo),
            )
            self.assertEqual(pre_claim["next_action"]["args"][0], "claim")

            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            prepared = run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            rendered = run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
            run_cli(
                "start",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--actor",
                "worker",
            )
            status = run_cli("status", "--workspace", str(workspace))
            task = next(item for item in status["tasks"] if item["id"] == "TASK-001")
            self.assertEqual(task["runtime_state"], "EXECUTING")

            worktree = Path(prepared["worktree"])
            target = worktree / "docs" / "result.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("ok\n", encoding="utf-8")
            contract_body = json.loads(Path(rendered["contract"]).read_text(encoding="utf-8"))
            receipt = {
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
            receipt_path = write_json(temp / "TASK-001.attempt.json", receipt)
            recorded = run_cli(
                "record-attempt",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--receipt",
                str(receipt_path),
            )
            self.assertTrue(recorded)
            self.assertEqual(receipt["schema"], "program-execution-controller.attempt-receipt.v2")
            cleanup_worktree(repo, workspace)
            _ = blueprint
            _ = prepared


if __name__ == "__main__":
    unittest.main()
