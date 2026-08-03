from __future__ import annotations

import tempfile
import unittest

from adapters.common.base import BaseExecutionAdapter
from adapters.common.models import ProbeContext

from conformance.helpers import PROGRAM_DIGEST, valid_contract


class UnsupportedAdapter(BaseExecutionAdapter):
    adapter_id = "unsupported-test-adapter"


class CancellationTests(unittest.TestCase):
    def test_unsupported_cancellation_is_truthful(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            adapter = UnsupportedAdapter(directory)
            adapter.probe(
                ProbeContext(
                    repository_root=directory,
                    runtime_root=directory,
                    program_lock_digest=PROGRAM_DIGEST,
                )
            )
            prepared = adapter.prepare(valid_contract())
            adapter.dispatch({"dispatch_id": prepared.dispatch_id})
            receipt = adapter.cancel(str(prepared.dispatch_id))
            self.assertEqual(receipt.status, "UNSUPPORTED")


if __name__ == "__main__":
    unittest.main()
