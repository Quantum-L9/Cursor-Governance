from __future__ import annotations

import os
import tempfile
import unittest

from environment.agents.results import gateway


class GatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["L9_RUNTIME_ROOT"] = self.tmp.name

    def tearDown(self) -> None:
        self.tmp.cleanup()
        os.environ.pop("L9_RUNTIME_ROOT", None)

    def test_reject_without_return(self):
        out = gateway.accept(return_receipt=None, surface_result={"status": "completed"})
        self.assertEqual(out["status"], "REJECTED")

    def test_accept_idempotent(self):
        ret = {
            "assignment_id": "a1",
            "status": "RETURNED",
            "lease_id": "L1",
            "base_sha": "sha",
            "parent_agent_id": "cursor",
            "surface": "cursor-ide",
        }
        surface = {
            "schema": "l9.cursor-subagent.result.v1",
            "status": "completed",
            "assignment_id": "a1",
            "lease_id": "L1",
            "base_sha": "sha",
            "result_id": "r1",
            "agent_id": "cursor",
        }
        a = gateway.accept(return_receipt=ret, surface_result=surface)
        b = gateway.accept(return_receipt=ret, surface_result=surface)
        self.assertEqual(a["status"], "ACCEPTED")
        self.assertEqual(a["receipt_digest"], b["receipt_digest"])

    def test_wrong_lease(self):
        ret = {
            "assignment_id": "a1",
            "status": "RETURNED",
            "lease_id": "L1",
            "base_sha": "sha",
            "parent_agent_id": "cursor",
            "surface": "cursor-ide",
        }
        surface = {
            "schema": "l9.cursor-subagent.result.v1",
            "status": "completed",
            "assignment_id": "a1",
            "lease_id": "L2",
            "base_sha": "sha",
            "result_id": "r2",
            "agent_id": "cursor",
        }
        out = gateway.accept(return_receipt=ret, surface_result=surface)
        self.assertEqual(out["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
