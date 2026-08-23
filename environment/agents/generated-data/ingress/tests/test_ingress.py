from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

INGRESS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INGRESS))
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

import ingest  # noqa: E402
import security_gate  # noqa: E402


class IngressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["L9_RUNTIME_ROOT"] = self.tmp.name

    def tearDown(self) -> None:
        self.tmp.cleanup()
        os.environ.pop("L9_RUNTIME_ROOT", None)

    def test_secret_quarantine(self):
        acc = {"status": "ACCEPTED", "receipt_digest": "acc1"}
        packet = {"notes": "api_key=SUPERSECRET123", "units": [1]}
        self.assertFalse(security_gate.preflight(packet)["safe"])
        out = ingest.ingest_accepted_result(
            accepted_result={}, generated_data_packet=packet, acceptance_receipt=acc
        )
        self.assertEqual(out["outcome"], "QUARANTINED")
        # quarantine meta must not echo secret
        qdir = Path(self.tmp.name) / "generated-data" / "quarantine"
        text = "".join(p.read_text() for p in qdir.glob("*.json"))
        self.assertNotIn("SUPERSECRET123", text)

    def test_safe_capture_and_idempotent(self):
        acc = {"status": "ACCEPTED", "receipt_digest": "acc2"}
        # Accepted ingress now hands the packet to the orchestration processor
        # and the packet validator, so this uses the repository's canonical
        # valid packet rather than a stub the new pipeline would reject.
        packet = json.loads(
            (
                Path(__file__).resolve().parents[1].parent
                / "tests/fixtures/valid-recon-packet.json"
            ).read_text(encoding="utf-8")
        )
        a = ingest.ingest_accepted_result(
            accepted_result={}, generated_data_packet=packet, acceptance_receipt=acc
        )
        b = ingest.ingest_accepted_result(
            accepted_result={}, generated_data_packet=packet, acceptance_receipt=acc
        )
        self.assertEqual(a["outcome"], "CAPTURED")
        self.assertEqual(a["receipt_digest"], b["receipt_digest"])

    def test_unprocessable_packet_fails_closed_with_a_receipt(self):
        """Ingress is a boundary: an unusable packet is FAILED, not an exception."""
        acc = {"status": "ACCEPTED", "receipt_digest": "acc4"}
        packet = {"units": [{"class": "repository_fact"}], "notes": "no identity"}
        out = ingest.ingest_accepted_result(
            accepted_result={}, generated_data_packet=packet, acceptance_receipt=acc
        )
        self.assertEqual(out["outcome"], "FAILED")
        self.assertEqual(out["processing_status"], "FAILED")
        self.assertIsNone(out["processor_job_id"])
        self.assertIn("not processable", out["reason"])

    def test_no_reusable(self):
        acc = {"status": "ACCEPTED", "receipt_digest": "acc3"}
        out = ingest.ingest_accepted_result(
            accepted_result={}, generated_data_packet=None, acceptance_receipt=acc
        )
        self.assertEqual(out["outcome"], "NO_REUSABLE_DATA")


if __name__ == "__main__":
    unittest.main()
