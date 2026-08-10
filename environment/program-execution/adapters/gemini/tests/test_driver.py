from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from adapters.common.models import ProbeContext
from scripts.provider_loader import instantiate, repository_root

PROGRAM_DIGEST = "sha256:" + "1" * 64


class GeminiReviewAdapterTests(unittest.TestCase):
    def test_probe_is_blocked_without_transport(self) -> None:
        with tempfile.TemporaryDirectory() as runtime:
            adapter = instantiate("gemini-review", runtime)
            receipt = adapter.probe(
                ProbeContext(
                    repository_root=str(repository_root()),
                    runtime_root=runtime,
                    program_lock_digest=PROGRAM_DIGEST,
                )
            )
            self.assertEqual(receipt.status, "BLOCKED")
            self.assertEqual(list(receipt.capabilities), [])

    def test_reviewer_maps_to_verifier_kind(self) -> None:
        descriptor = yaml.safe_load(
            (Path(__file__).resolve().parents[1] / "ADAPTER.yaml").read_text()
        )
        self.assertEqual(descriptor["adapter_kind"], "verifier")


if __name__ == "__main__":
    unittest.main()
