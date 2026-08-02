from __future__ import annotations

import datetime as dt
import json
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, register_contract, run_cli, write_json


class ApprovalTest(unittest.TestCase):
    def test_t4_requires_exact_evidence_bound_approval(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp, risk_tier="T4")
            register_contract(temp, workspace, risk_tier="T4")
            blocked = run_cli(
                "claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker", expect=2
            )
            self.assertIn("required_approval_missing_or_invalid", blocked["error"])
            lock = json.loads((workspace / "runtime" / "program-lock.json").read_text())
            db = sqlite3.connect(workspace / "runtime" / "state.sqlite")
            base_sha = db.execute(
                "SELECT head_sha FROM repositories WHERE repository_id='repo-a'"
            ).fetchone()[0]
            db.close()
            now = dt.datetime.now(dt.UTC).replace(microsecond=0)
            approval = {
                "schema": "program-execution-controller.approval.v2",
                "approval_id": "APPROVAL-001",
                "action": "execute_task",
                "task_id": "TASK-001",
                "target_id": "TARGET-001",
                "repository_id": "repo-a",
                "program_digest": lock["lock_digest"],
                "base_sha": base_sha,
                "candidate_sha": None,
                "permits": ["inspect", "local_write"],
                "forbids": ["push", "merge", "deploy_or_migrate"],
                "prerequisite_evidence_ids": ["EVID-PLAN"],
                "approved_by": "operator",
                "issued_at": now.isoformat(),
                "expires_at": (now + dt.timedelta(hours=1)).isoformat(),
            }
            path = write_json(temp / "approval.json", approval)
            run_cli("add-approval", "--workspace", str(workspace), "--file", str(path))
            lease = run_cli(
                "claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker"
            )
            self.assertEqual(lease["task_id"], "TASK-001")


if __name__ == "__main__":
    unittest.main()
