from __future__ import annotations

import tempfile
import unittest

from adapters.common.models import ProbeContext
from scripts.provider_loader import instantiate, repository_root

PROGRAM_DIGEST = "sha256:" + "1" * 64


class ManusCloudAdapterTests(unittest.TestCase):
    def test_probe_is_blocked_without_transport(self) -> None:
        with tempfile.TemporaryDirectory() as runtime:
            adapter = instantiate("manus-cloud", runtime)
            receipt = adapter.probe(
                ProbeContext(
                    repository_root=str(repository_root()),
                    runtime_root=runtime,
                    program_lock_digest=PROGRAM_DIGEST,
                )
            )
            self.assertEqual(receipt.status, "BLOCKED")
            self.assertEqual(list(receipt.capabilities), [])


if __name__ == "__main__":
    unittest.main()
