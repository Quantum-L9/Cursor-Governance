from __future__ import annotations

import tempfile
import unittest

from adapters.common.models import LifecycleReceipt
from adapters.common.receipts import ReceiptChain

from conformance.helpers import PROGRAM_DIGEST


class ReceiptIntegrityTests(unittest.TestCase):
    def test_hash_chain_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            chain = ReceiptChain(directory)
            first = LifecycleReceipt.create(
                adapter_id="test-adapter",
                adapter_version="1.0.0",
                phase="probe",
                program_lock_digest=PROGRAM_DIGEST,
                status="PASS",
            )
            chain.append(first)
            second = LifecycleReceipt.create(
                adapter_id="test-adapter",
                adapter_version="1.0.0",
                phase="cleanup",
                program_lock_digest=PROGRAM_DIGEST,
                status="PASS",
                previous_receipt_digest=first.receipt_digest,
            )
            chain.append(second)
            self.assertEqual(chain.verify(), [])

    def test_wrong_previous_digest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            chain = ReceiptChain(directory)
            receipt = LifecycleReceipt.create(
                adapter_id="test-adapter",
                adapter_version="1.0.0",
                phase="probe",
                program_lock_digest=PROGRAM_DIGEST,
                status="PASS",
                previous_receipt_digest="sha256:" + "f" * 64,
            )
            with self.assertRaises(ValueError):
                chain.append(receipt)


if __name__ == "__main__":
    unittest.main()
