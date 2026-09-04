"""The source-integrity receipt attests two independent reads, or says it cannot.

`write_receipt` used to copy `digest` into `pack_recorded_digest` and assert
`digest_matches_pack: true` unconditionally, so the receipt agreed with
itself and attested nothing about the file it described.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

PE_ROOT = Path(__file__).resolve().parents[2]
ACTIVATE_DIR = PE_ROOT.parents[1] / "skills/l9-pe-campaign-activate/scripts"


def _load_activation():
    if str(ACTIVATE_DIR) not in sys.path:
        sys.path.insert(0, str(ACTIVATE_DIR))
    spec = importlib.util.spec_from_file_location(
        "compile_activation_receipt_under_test", ACTIVATE_DIR / "compile_activation_files.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class WriteReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.act = _load_activation()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.source = self.root / "CAMPAIGN_SOURCE.yaml"
        self.source.write_text("schema: demo\nmetadata: {campaign_id: demo}\n", encoding="utf-8")

    def test_digest_and_bytes_are_measured_from_the_placed_file(self) -> None:
        receipt = self.act.write_receipt(self.source, "demo", stamp="2026-01-01T00:00:00Z")
        data = self.source.read_bytes()
        self.assertEqual(receipt["digest"], hashlib.sha256(data).hexdigest())
        self.assertEqual(receipt["bytes"], len(data))
        on_disk = json.loads(
            self.source.with_name("source-integrity-receipt.json").read_text(encoding="utf-8")
        )
        self.assertEqual(on_disk["digest"], receipt["digest"])

    def test_without_a_compiler_serialization_the_pack_fields_are_unknown_not_true(self):
        receipt = self.act.write_receipt(self.source, "demo", stamp="2026-01-01T00:00:00Z")
        self.assertIsNone(receipt["pack_recorded_digest"])
        self.assertIsNone(receipt["pack_recorded_bytes"])
        self.assertIsNone(receipt["digest_matches_pack"])

    def test_a_matching_serialization_is_recorded_as_a_match(self) -> None:
        expected = self.source.read_bytes()
        receipt = self.act.write_receipt(
            self.source, "demo", stamp="2026-01-01T00:00:00Z", expected_bytes=expected
        )
        self.assertTrue(receipt["digest_matches_pack"])
        self.assertEqual(receipt["pack_recorded_digest"], hashlib.sha256(expected).hexdigest())
        self.assertEqual(receipt["pack_recorded_bytes"], len(expected))

    def test_a_drifted_file_is_refused_not_recorded_as_matching(self) -> None:
        with self.assertRaises(self.act.CompileError) as ctx:
            self.act.write_receipt(
                self.source,
                "demo",
                stamp="2026-01-01T00:00:00Z",
                expected_bytes=b"schema: something-else\n",
            )
        self.assertIn("drifted", str(ctx.exception))
        self.assertFalse(self.source.with_name("source-integrity-receipt.json").exists())

    def test_the_operator_input_is_bound_into_the_receipt(self) -> None:
        intent = self.root / "intent.yaml"
        intent.write_text("campaign_id: demo\n", encoding="utf-8")
        receipt = self.act.write_receipt(
            self.source, "demo", stamp="2026-01-01T00:00:00Z", operator_input=intent
        )
        self.assertEqual(
            receipt["operator_input"],
            {
                "path": str(intent),
                "sha256": hashlib.sha256(intent.read_bytes()).hexdigest(),
                "bytes": intent.stat().st_size,
            },
        )


class CompileActivationReceiptTests(unittest.TestCase):
    """End to end: the compiler hands its own serialization and the operator input in."""

    def test_compile_activation_binds_input_and_output_honestly(self) -> None:
        sys.path.insert(0, str(ACTIVATE_DIR))
        import test_compile_activation_files as fixtures  # noqa: PLC0415

        act = _load_activation()
        with tempfile.TemporaryDirectory() as raw:
            root = fixtures._repo(Path(raw))
            act.compile_activation(root / "intent.yaml", root, stamp="2026-08-15T00:00:00Z")
            campaign = root / "environment/program-execution/campaigns/demo-activate-v1"
            source = campaign / "CAMPAIGN_SOURCE.yaml"
            receipt = json.loads(
                (campaign / "source-integrity-receipt.json").read_text(encoding="utf-8")
            )
            placed = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertEqual(receipt["digest"], placed)
            self.assertEqual(receipt["pack_recorded_digest"], placed)
            self.assertEqual(receipt["pack_recorded_bytes"], source.stat().st_size)
            self.assertTrue(receipt["digest_matches_pack"])
            intent = root / "intent.yaml"
            self.assertEqual(
                receipt["operator_input"]["sha256"],
                hashlib.sha256(intent.read_bytes()).hexdigest(),
            )
            self.assertEqual(receipt["operator_input"]["bytes"], intent.stat().st_size)


if __name__ == "__main__":
    unittest.main()
