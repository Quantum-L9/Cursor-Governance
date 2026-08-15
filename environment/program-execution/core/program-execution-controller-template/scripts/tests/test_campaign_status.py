from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, register_contract, run_cli


class CampaignStatusTest(unittest.TestCase):
    def test_accepted_bootstrap_activates_runtime_status(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            boot_status = json.loads((workspace / "runtime" / "campaign-status.json").read_text())
            self.assertEqual(boot_status["runtime_status"], "active")
            self.assertEqual(boot_status["source_status"], "operator_intake")
            self.assertEqual(
                boot_status["schema"], "program-execution-controller.campaign-status.v1"
            )
            status = run_cli("status", "--workspace", str(workspace))
            self.assertEqual(status["campaign_status"]["runtime_status"], "active")
            ledger = (workspace / "ledger" / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn("CAMPAIGN_ACTIVATED", ledger)

    def test_claim_reactivates_if_receipt_missing(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            receipt = workspace / "runtime" / "campaign-status.json"
            receipt.unlink()
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker-a")
            restored = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(restored["runtime_status"], "active")
            self.assertEqual(restored["actor"], "worker-a")


if __name__ == "__main__":
    unittest.main()
