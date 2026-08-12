from __future__ import annotations
import os, sys, tempfile, unittest
from pathlib import Path
from environment.agents.lifecycle import compose_start, compose_stop
from environment.agents.readiness import compose as readiness
from environment.agents.results import gateway
INGRESS = Path(__file__).resolve().parents[1] / "generated-data" / "ingress"
sys.path.insert(0, str(INGRESS))
import ingest  # noqa: E402

class ClosedLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["L9_RUNTIME_ROOT"] = self.tmp.name
        os.environ["HOME"] = self.tmp.name
    def tearDown(self) -> None:
        self.tmp.cleanup()
        os.environ.pop("L9_RUNTIME_ROOT", None)
    def test_happy_path_chain(self):
        start = compose_start.compose_subagent_start({
            "assignment": {"assignment_id": "loop-1", "campaign_id": "c1", "action_id": "a1", "subagent_role": "l9-recon", "parent_agent_id": "cursor", "workspace": self.tmp.name, "surface": "cursor-ide", "base_sha": "deadbeef"},
            "lease": {"lease_id": "lease-1", "status": "ACTIVE"},
            "deployment_receipt": {"status": "DEPLOYMENT_READY"},
        })
        self.assertEqual(start["permission"], "allow")
        ret = compose_stop.compose_subagent_stop({"assignment_id": "loop-1", "output": {"ok": True}})
        self.assertEqual(ret["status"], "RETURNED")
        acc = gateway.accept(return_receipt=ret["return_receipt"], surface_result={"schema": "l9.cursor-subagent.result.v1", "status": "completed", "assignment_id": "loop-1", "lease_id": "lease-1", "base_sha": "deadbeef", "result_id": "loop-r1", "agent_id": "cursor"})
        self.assertEqual(acc["status"], "ACCEPTED")
        ing = ingest.ingest_accepted_result(accepted_result={}, generated_data_packet={"units": [{"class": "repository_fact"}]}, acceptance_receipt=acc)
        self.assertEqual(ing["outcome"], "CAPTURED")
        self.assertTrue(readiness.completion_evidence_ok(return_receipt=ret["return_receipt"], acceptance_receipt=acc, ingress_receipt=ing)["allowed"])
    def test_failure_matrix_terminals(self):
        self.assertFalse(readiness.completion_evidence_ok(return_receipt={"status": "RETURNED"}, acceptance_receipt=None, ingress_receipt={"outcome": "CAPTURED"})["allowed"])
        ing = ingest.ingest_accepted_result(accepted_result={}, generated_data_packet={"token": "password=hunter2"}, acceptance_receipt={"status": "ACCEPTED", "receipt_digest": "acc-sec"})
        self.assertEqual(ing["outcome"], "QUARANTINED")

if __name__ == "__main__":
    unittest.main()
