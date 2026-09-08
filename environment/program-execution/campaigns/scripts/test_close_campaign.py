from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from close_campaign import (  # noqa: E402
    ClosureReceiptError,
    archive_completed,
    close_campaign,
    next_campaign,
    validate_closure_receipt,
)


def _receipt(campaign_id: str = "alpha", verdict: str = "CONVERGED", **over: Any) -> dict:
    body = {
        "schema": "program-execution-controller.closure-receipt.v1",
        "closure_id": "CLOSURE-0123456789abcdef",
        "producer": "Program Execution Controller",
        "controller_id": "controller-test",
        "campaign_id": campaign_id,
        "program_id": campaign_id,
        "program_digest": "f" * 64,
        "runtime_workspace": "/tmp/ws",
        "verdict": verdict,
        "recommendation": verdict,
        "facts": {},
        "blockers_checked": ["tasks"],
        "evidence": {},
        "closed_by": "operator",
        "closed_at": "2026-09-06T00:00:00+00:00",
        **over,
    }
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    body["receipt_digest"] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return body


class _Root(unittest.TestCase):
    def _root(self, temp: Path) -> Path:
        root = temp / "campaigns"
        root.mkdir()
        (root / "CAMPAIGN_EXECUTION_POLICY.yaml").write_text(
            "campaigns:\n  - id: alpha\n    execute_order: 1\n  - id: beta\n    execute_order: 2\n",
            encoding="utf-8",
        )
        return root


class CloseCampaignTest(_Root):
    def test_close_then_next_skips_complete(self) -> None:
        with TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            self.assertEqual(next_campaign(root)["id"], "alpha")
            closed = close_campaign(root, "alpha", _receipt(), "AUTH-001")
            self.assertEqual(closed["lifecycle"], "complete")
            self.assertEqual(closed["verdict"], "CONVERGED")
            self.assertEqual(closed["evidence"]["closure_id"], "CLOSURE-0123456789abcdef")
            self.assertTrue((root / "alpha" / "handoff" / "CLOSEOUT.yaml").is_file())
            self.assertEqual(next_campaign(root)["id"], "beta")

    def test_archive_moves_to_completed_and_next_skips(self) -> None:
        with TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            (root / "alpha").mkdir()
            (root / "alpha" / "CAMPAIGN_SOURCE.yaml").write_text("schema: x\n", encoding="utf-8")
            receipt_path = Path(raw) / "closure.json"
            receipt_path.write_text(json.dumps(_receipt()), encoding="utf-8")
            close_campaign(root, "alpha", receipt_path, "AUTH-001")
            archived = archive_completed(root, "alpha")
            self.assertEqual(archived, root / "COMPLETED" / "alpha")
            self.assertFalse((root / "alpha").exists())
            self.assertTrue((archived / "CAMPAIGN_SOURCE.yaml").is_file())
            self.assertEqual(next_campaign(root)["id"], "beta")


class ClosureReceiptAuthorityTests(_Root):
    """PEC-P1-002: the closer projects a Controller closure; it never decides."""

    def _refused(self, root: Path, receipt: Any, **kwargs: Any) -> str:
        with self.assertRaises(SystemExit) as caught:
            close_campaign(root, "alpha", receipt, "AUTH-001", **kwargs)
        self.assertFalse((root / "CAMPAIGN_STATUS.yaml").exists(), "a refused close wrote")
        return str(caught.exception)

    def test_a_free_form_verdict_is_not_accepted(self) -> None:
        with TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            text = self._refused(root, {"verdict": "CONVERGED"})
            self.assertIn("missing fields", text)

    def test_missing_receipt_file_is_refused(self) -> None:
        with TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            self.assertIn("not found", self._refused(root, Path(raw) / "absent.json"))

    def test_tampered_receipt_is_refused(self) -> None:
        with TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            receipt = _receipt(verdict="NOT_CONVERGED")
            receipt["verdict"] = "CONVERGED"  # digest no longer covers the body
            self.assertIn("digest mismatch", self._refused(root, receipt))

    def test_receipt_for_a_different_program_is_refused(self) -> None:
        with TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            self.assertIn("for campaign", self._refused(root, _receipt(campaign_id="beta")))

    def test_receipt_from_a_different_producer_is_refused(self) -> None:
        with TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            self.assertIn("producer", self._refused(root, _receipt(producer="make-campaign")))

    def test_non_terminal_receipt_verdict_is_refused(self) -> None:
        with TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            self.assertIn("not terminal", self._refused(root, _receipt(verdict="INCONCLUSIVE")))

    def test_expected_verdict_must_match_the_controller(self) -> None:
        with TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            text = self._refused(
                root, _receipt(verdict="NOT_CONVERGED"), expected_verdict="CONVERGED"
            )
            self.assertIn("expected CONVERGED", text)

    def test_extra_evidence_cannot_override_receipt_bindings(self) -> None:
        with TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            closed = close_campaign(
                root,
                "alpha",
                _receipt(),
                "AUTH-001",
                extra_evidence={"closure_id": "forged", "handoff_id": "H-1"},
            )
            self.assertEqual(closed["evidence"]["closure_id"], "CLOSURE-0123456789abcdef")
            self.assertEqual(closed["evidence"]["handoff_id"], "H-1")

    def test_validate_reports_the_schema(self) -> None:
        with self.assertRaises(ClosureReceiptError):
            validate_closure_receipt(_receipt(schema="other"), "alpha")


if __name__ == "__main__":
    unittest.main()
