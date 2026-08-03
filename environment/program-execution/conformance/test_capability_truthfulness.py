from __future__ import annotations

import datetime as dt
import unittest

from adapters.common.models import CapabilityReceipt

from conformance.helpers import PROGRAM_DIGEST


class CapabilityTruthfulnessTests(unittest.TestCase):
    def test_expired_capability_is_not_fresh(self) -> None:
        receipt = CapabilityReceipt.create(
            adapter_id="test-adapter",
            adapter_version="1.0.0",
            status="PASS",
            capabilities=["inspect"],
            program_lock_digest=PROGRAM_DIGEST,
            ttl_seconds=1,
        )
        future = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=2)
        self.assertFalse(receipt.is_fresh(future))

    def test_blocked_capability_is_not_fresh(self) -> None:
        receipt = CapabilityReceipt.create(
            adapter_id="test-adapter",
            adapter_version="1.0.0",
            status="BLOCKED",
            capabilities=[],
            program_lock_digest=PROGRAM_DIGEST,
        )
        self.assertFalse(receipt.is_fresh())


if __name__ == "__main__":
    unittest.main()
