from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from adapters.common.models import ProbeContext
from peer_execution.imports import pe_script

_provider_loader = pe_script("provider_loader")
instantiate = _provider_loader.instantiate
repository_root = _provider_loader.repository_root

PROGRAM_DIGEST = "sha256:" + "1" * 64


class CodexCloudAdapterTests(unittest.TestCase):
    def test_probe_is_blocked_without_transport(self) -> None:
        with tempfile.TemporaryDirectory() as runtime:
            adapter = instantiate("codex-cloud", runtime)
            receipt = adapter.probe(
                ProbeContext(
                    repository_root=str(repository_root()),
                    runtime_root=runtime,
                    program_lock_digest=PROGRAM_DIGEST,
                )
            )
            self.assertEqual(receipt.status, "BLOCKED")
            self.assertEqual(list(receipt.capabilities), [])

    def test_driver_declares_no_forbidden_operations(self) -> None:
        text = (Path(__file__).resolve().parents[1] / "provider.py").read_text()
        self.assertNotIn("merge_pull_request(", text)
        self.assertNotIn("git push --force", text)


if __name__ == "__main__":
    unittest.main()
