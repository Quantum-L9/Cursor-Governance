from __future__ import annotations

import json
import os
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from helpers import (
    SCRIPTS,
    bootstrap_repo,
    cleanup_worktree,
    make_blueprint,
    make_repo,
    prepare_attempt,
    register_contract,
    run_cli,
    source_contract,
    write_json,
)


def _inspection_blueprint(root: Path) -> Path:
    bp = make_blueprint(root)
    cards = yaml.safe_load((bp / "TASK_CARDS.yaml").read_text(encoding="utf-8"))
    for task in cards.get("tasks") or []:
        for item in task.get("validation") or []:
            item["method"] = "inspection"
    (bp / "TASK_CARDS.yaml").write_text(yaml.safe_dump(cards, sort_keys=False), encoding="utf-8")
    return bp


class PipelineAssemblyFillTest(unittest.TestCase):
    def test_inspection_only_verify_passed_local(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            bp = _inspection_blueprint(temp / "blueprint")
            repo = make_repo(temp / "repo")
            workspace = temp / "runtime"
            run_cli("bootstrap", "--workspace", str(workspace), "--blueprint", str(bp))
            run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")
            drafted = run_cli(
                "draft-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--output",
                str(temp / "TASK-001.source.json"),
            )
            self.assertTrue(Path(drafted["path"]).is_file())
            source = json.loads(Path(drafted["path"]).read_text(encoding="utf-8"))
            self.assertEqual(source["validation_commands"], [])
            run_cli(
                "register-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--file",
                str(temp / "TASK-001.source.json"),
                "--actor",
                "operator",
            )
            prepare_attempt(temp, workspace, output="docs/result.txt")
            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(verification["verdict"], "PASSED_LOCAL", verification.get("gates"))
            self.assertEqual(verification["gates"]["validation"], "PASS")
            cleanup_worktree(repo, workspace)

    def test_inspection_only_missing_output_fails(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            bp = _inspection_blueprint(temp / "blueprint")
            repo = make_repo(temp / "repo")
            workspace = temp / "runtime"
            run_cli("bootstrap", "--workspace", str(workspace), "--blueprint", str(bp))
            run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")
            contract = source_contract("TASK-001", "docs/result.txt")
            contract["validation_commands"] = []
            write_json(temp / "TASK-001.source.json", contract)
            run_cli(
                "register-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--file",
                str(temp / "TASK-001.source.json"),
                "--actor",
                "operator",
            )
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            prepared = run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            rendered = run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
            run_cli("start", "TASK-001", "--workspace", str(workspace), "--actor", "worker")
            contract_body = json.loads(Path(rendered["contract"]).read_text(encoding="utf-8"))
            receipt = {
                "schema": "program-execution-controller.attempt-receipt.v2",
                "task_id": "TASK-001",
                "contract_digest": contract_body["contract_digest"],
                "program_digest": contract_body["program_digest"],
                "base_sha": contract_body["base_sha"],
                "candidate_sha": None,
                "changed_files": [],
                "validation_results": [],
                "produced_evidence": [],
                "residual_unknowns": [],
                "claimed_status": "completed",
            }
            receipt_path = write_json(temp / "TASK-001.attempt.json", receipt)
            run_cli(
                "record-attempt",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--receipt",
                str(receipt_path),
            )
            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(verification["verdict"], "FAILED")
            self.assertEqual(verification["gates"]["validation"], "FAIL")
            Path(prepared["worktree"]).mkdir(parents=True, exist_ok=True)
            cleanup_worktree(repo, workspace)

    def test_claim_ttl_minutes(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            lease = run_cli(
                "claim",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--holder",
                "worker",
                "--ttl-minutes",
                "15",
            )
            issued = datetime.fromisoformat(lease["issued_at"].replace("Z", "+00:00"))
            expires = datetime.fromisoformat(lease["expires_at"].replace("Z", "+00:00"))
            self.assertEqual(expires - issued, timedelta(minutes=15))
            cleanup_worktree(repo, workspace)

    def test_status_names_current_after_claim(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            status = run_cli("status", "--workspace", str(workspace))
            nxt = run_cli("next", "--workspace", str(workspace))
            self.assertEqual(status["current"]["task_id"], "TASK-001")
            self.assertEqual(status["current"]["runtime_state"], "LEASED")
            self.assertEqual(nxt["current"]["task_id"], "TASK-001")
            self.assertEqual(nxt["ready"], [])
            cleanup_worktree(repo, workspace)

    def test_successor_claimable_after_complete_and_gate(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            bp = make_blueprint(temp / "blueprint", two_tasks=True)
            repo = make_repo(temp / "repo")
            workspace = temp / "runtime"
            run_cli("bootstrap", "--workspace", str(workspace), "--blueprint", str(bp))
            run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")
            register_contract(temp, workspace, task_id="TASK-001", output="docs/result.txt")
            register_contract(temp, workspace, task_id="TASK-002", output="docs/second.txt")
            prepare_attempt(temp, workspace, output="docs/result.txt")
            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(verification["verdict"], "PASSED_LOCAL")
            evidence_id = verification["evidence_id"]
            run_cli(
                "evaluate-gate",
                "GATE-001",
                "PASS",
                "--workspace",
                str(workspace),
                "--evidence-id",
                evidence_id,
                "--method",
                "independent verification",
                "--actor",
                "controller",
            )
            run_cli(
                "complete",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--actor",
                "operator",
                "--evidence-id",
                evidence_id,
            )
            nxt = run_cli("next", "--workspace", str(workspace))
            ready_ids = [item["id"] for item in nxt["ready"]]
            self.assertIn("TASK-002", ready_ids)
            lease = run_cli(
                "claim", "TASK-002", "--workspace", str(workspace), "--holder", "worker"
            )
            self.assertEqual(lease["task_id"], "TASK-002")
            cleanup_worktree(repo, workspace)
            cleanup_worktree(repo, workspace, task_id="TASK-002")

    def test_bootstrap_refuses_hash_program_id(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            bp = make_blueprint(temp / "blueprint")
            program = (bp / "PROGRAM.yaml").read_text(encoding="utf-8")
            (bp / "PROGRAM.yaml").write_text(
                program.replace("id: test-program", "id: pe-deadbeef01"),
                encoding="utf-8",
            )
            result = run_cli(
                "bootstrap",
                "--workspace",
                str(temp / "runtime"),
                "--blueprint",
                str(bp),
                expect=2,
            )
            self.assertIn("hash id", result["error"])

    def test_start_refuses_operator_memo_cwd(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            memo = temp / "PE- Memory.md"
            memo.write_text("operator memo\n", encoding="utf-8")
            launch = {
                "schema": "l9.program-execution.launch-pointer.v1",
                "load_operator_brief": False,
                "operator_brief": str(memo),
            }
            (workspace / "runtime").mkdir(parents=True, exist_ok=True)
            (workspace / "runtime" / "LAUNCH.json").write_text(json.dumps(launch), encoding="utf-8")
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
            import subprocess
            import sys

            pec_env = os.environ.copy()
            pec_env.setdefault("L9_ALLOW_PEC_DIRECT", "1")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "pec.py"),
                    "start",
                    "TASK-001",
                    "--workspace",
                    str(workspace),
                    "--actor",
                    "worker",
                ],
                cwd=str(memo.parent),
                text=True,
                capture_output=True,
                check=False,
                timeout=45,
                env=pec_env,
            )
            self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
            self.assertIn("operator memo", completed.stdout)
            cleanup_worktree(repo, workspace)


if __name__ == "__main__":
    unittest.main()
