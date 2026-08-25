from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from environment.agents.lifecycle import compose_start, compose_stop, receipts


class LifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["L9_RUNTIME_ROOT"] = self.tmp.name

    def tearDown(self) -> None:
        self.tmp.cleanup()
        os.environ.pop("L9_RUNTIME_ROOT", None)

    def _assignment(self, **extra):
        base = {
            "assignment_id": "asg-1",
            "campaign_id": "camp-1",
            "action_id": "act-1",
            "subagent_role": "l9-pr-remediation",
            "parent_agent_id": "cursor",
            "workspace": self.tmp.name,
            "surface": "cursor-ide",
            "base_sha": "abc123",
        }
        base.update(extra)
        return base

    def test_start_pass(self):
        out = compose_start.compose_subagent_start(
            {
                "assignment": self._assignment(),
                "lease": {"lease_id": "lease-1", "status": "ACTIVE"},
                "deployment_receipt": {"status": "DEPLOYMENT_READY"},
            }
        )
        self.assertEqual(out["permission"], "allow")
        self.assertIsNotNone(receipts.load_dispatch("asg-1"))

    def test_start_wrong_assignment(self):
        out = compose_start.compose_subagent_start(
            {"lease": {"lease_id": "x"}, "deployment_receipt": {"status": "READY"}}
        )
        self.assertEqual(out["permission"], "deny")

    def test_start_stale_deployment(self):
        out = compose_start.compose_subagent_start(
            {
                "assignment": self._assignment(),
                "lease": {"lease_id": "lease-1", "status": "ACTIVE"},
                "deployment_receipt": {"status": "BLOCKED"},
            }
        )
        self.assertEqual(out["permission"], "deny")

    def test_start_stale_lease(self):
        out = compose_start.compose_subagent_start(
            {
                "assignment": self._assignment(),
                "lease": {"lease_id": "lease-1", "status": "EXPIRED"},
                "deployment_receipt": {"status": "DEPLOYMENT_READY"},
            }
        )
        self.assertEqual(out["permission"], "deny")

    def test_stop_correlated(self):
        compose_start.compose_subagent_start(
            {
                "assignment": self._assignment(),
                "lease": {"lease_id": "lease-1", "status": "ACTIVE"},
                "deployment_receipt": {"status": "DEPLOYMENT_READY"},
            }
        )
        out = compose_stop.compose_subagent_stop({"assignment_id": "asg-1", "output": "ok"})
        self.assertEqual(out["status"], "RETURNED")
        again = compose_stop.compose_subagent_stop({"assignment_id": "asg-1", "output": "ok"})
        self.assertTrue(again.get("idempotent"))

    def test_orphan_stop(self):
        out = compose_stop.compose_subagent_stop({"assignment_id": "missing", "output": "x"})
        self.assertEqual(out["status"], "QUARANTINED")

    def test_host_stop_without_correlation_is_quarantined_with_evidence(self):
        out = compose_stop.compose_subagent_stop(
            {"subagent_id": "sub-orphan", "status": "FAILED", "error": "boom"}
        )
        self.assertEqual(out["status"], "QUARANTINED")
        stop_path = receipts.host_stop_path("sub-orphan")
        self.assertTrue(stop_path.is_file())

    def test_pr_assignment(self):
        body = receipts.write_pr_remediation_assignment(
            {
                "assignment_id": "pr-1",
                "pr_number": 104,
                "branch": "feat/x",
                "max_cycles": 3,
            }
        )
        self.assertEqual(body["schema"], "l9.pr-remediation-assignment.v1")
        self.assertTrue(
            (
                Path(self.tmp.name) / "agents" / "assignments" / "pr-remediation" / "pr-1.json"
            ).is_file()
        )


if __name__ == "__main__":
    unittest.main()
