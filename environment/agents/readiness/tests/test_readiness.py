from __future__ import annotations

import unittest

from environment.agents.readiness import compose


class ReadinessTests(unittest.TestCase):
    def test_execution_ready(self):
        dims = {
            k: True
            for k in [
                "IDENTITY_READY",
                "PROGRAM_EXECUTION_READY",
                "AUTONOMY_READY",
                "DEPLOYMENT_READY",
                "RESULT_INGRESS_READY",
                "DATA_CAPTURE_READY",
            ]
        }
        self.assertEqual(compose.execution_ready(dims)["status"], "EXECUTION_READY")

    def test_missing_blocks(self):
        dims = {
            k: True
            for k in [
                "IDENTITY_READY",
                "PROGRAM_EXECUTION_READY",
                "AUTONOMY_READY",
                "DEPLOYMENT_READY",
                "RESULT_INGRESS_READY",
            ]
        }
        dims["DATA_CAPTURE_READY"] = False
        self.assertEqual(compose.execution_ready(dims)["status"], "NOT_READY")

    def test_completion_join(self):
        bad = compose.completion_evidence_ok(
            return_receipt=None,
            acceptance_receipt={"status": "ACCEPTED"},
            ingress_receipt={"outcome": "CAPTURED"},
        )
        self.assertFalse(bad["allowed"])
        ok = compose.completion_evidence_ok(
            return_receipt={"status": "RETURNED"},
            acceptance_receipt={"status": "ACCEPTED"},
            ingress_receipt={"outcome": "NO_REUSABLE_DATA"},
        )
        self.assertTrue(ok["allowed"])


if __name__ == "__main__":
    unittest.main()
