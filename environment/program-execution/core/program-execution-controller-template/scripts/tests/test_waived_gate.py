from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from helpers import (
    cleanup_worktree,
    make_blueprint,
    make_repo,
    prepare_attempt,
    register_contract,
    run_cli,
)


class WaivedGateTest(unittest.TestCase):
    def test_explicit_active_evidence_backed_waiver_satisfies_not_applicable_gate(self):
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            bp = make_blueprint(temp / "blueprint")
            waivers = yaml.safe_load((bp / "WAIVER_REGISTER.yaml").read_text())
            waivers["waivers"] = [
                {
                    "id": "WAIVER-001",
                    "scope": ["GATE-001"],
                    "owner": "operator",
                    "reason": "fixture exception",
                    "compensating_controls": ["independent verification"],
                    "evidence_ids": ["EVID-PLAN"],
                    "issued_at": "2026-08-01T13:00:00-04:00",
                    "expires_at": "2027-08-01T13:00:00-04:00",
                    "status": "active",
                }
            ]
            (bp / "WAIVER_REGISTER.yaml").write_text(yaml.safe_dump(waivers, sort_keys=False))
            gates = yaml.safe_load((bp / "CONVERGENCE_GATES.yaml").read_text())
            gates["gates"][0]["waiver_allowed"] = True
            (bp / "CONVERGENCE_GATES.yaml").write_text(yaml.safe_dump(gates, sort_keys=False))
            repo = make_repo(temp / "repo")
            workspace = temp / "runtime"
            run_cli("bootstrap", "--workspace", str(workspace), "--blueprint", str(bp))
            run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")
            register_contract(temp, workspace)
            prepare_attempt(temp, workspace)
            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            evidence = verification["evidence_id"]
            run_cli(
                "evaluate-gate",
                "GATE-001",
                "NOT_APPLICABLE_WITH_REASON",
                "--workspace",
                str(workspace),
                "--evidence-id",
                evidence,
                "--method",
                "explicit fixture waiver",
                "--actor",
                "controller",
                "--waiver-id",
                "WAIVER-001",
            )
            result = run_cli(
                "complete",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--actor",
                "operator",
                "--evidence-id",
                evidence,
            )
            self.assertEqual(result["status"], "COMPLETED")
            cleanup_worktree(repo, workspace)


if __name__ == "__main__":
    unittest.main()
