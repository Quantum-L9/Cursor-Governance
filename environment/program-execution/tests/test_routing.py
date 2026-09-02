from __future__ import annotations

import time
import unittest
from pathlib import Path

from adapters.common.errors import AdapterFailure
from peer_execution.imports import pe_script
from peer_execution.models import CapabilityReceipt

_router = pe_script("router")
route_contract = _router.route_contract

LOCK = "sha256:" + "a" * 64
GITHUB_VERIFY = {
    "action_class": "verification",
    "requested_actions": ["verify"],
    "target_kind": "github_repository",
    "program_lock_digest": LOCK,
}


class RoutingTests(unittest.TestCase):
    def test_active_generic_shell_routes_verification(self) -> None:
        root = Path(__file__).resolve().parents[1]
        result = route_contract(
            {
                "action_class": "verification",
                "requested_actions": ["verify"],
                "target_kind": "git_repository",
            },
            subsystem_root=root,
            capability_receipts={},
        )
        self.assertEqual(result["adapter_id"], "ci-generic-shell")

    def test_dormant_chatgpt_is_not_selected(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with self.assertRaises(AdapterFailure):
            route_contract(
                {
                    "action_class": "read_only_architecture_or_artifact_work",
                    "requested_actions": ["artifact_production"],
                    "target_kind": "document_artifact",
                },
                subsystem_root=root,
                capability_receipts={},
            )


class ConditionalReceiptTests(unittest.TestCase):
    """`status: PASS` in a file is not a fresh capability receipt."""

    def _receipt(self, **overrides) -> dict:
        fields = {
            "adapter_id": "ci-github-actions",
            "adapter_version": "1.0.0",
            "status": "PASS",
            "capabilities": ["workflow_dispatch", "verify"],
            "program_lock_digest": LOCK,
        }
        fields.update(overrides)
        return CapabilityReceipt.create(**fields).to_dict()

    def test_a_bare_pass_marker_does_not_route(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with self.assertRaises(AdapterFailure) as ctx:
            route_contract(
                GITHUB_VERIFY,
                subsystem_root=root,
                capability_receipts={"ci-github-actions": {"status": "PASS"}},
            )
        rejections = ctx.exception.evidence[0]["routing_rejections"]
        self.assertIn("capability_receipt_malformed", rejections["ci-github-actions"])

    def test_expired_tampered_and_foreign_lock_receipts_are_rejected(self) -> None:
        expired = self._receipt(ttl_seconds=1)
        time.sleep(1.2)
        tampered = self._receipt()
        tampered["capabilities"] = ["verify", "merge"]  # digest no longer matches
        foreign = self._receipt(program_lock_digest="sha256:" + "b" * 64)
        self.assertEqual(
            _router._capability_receipt_rejections(expired, LOCK),
            ["capability_receipt_expired"],
        )
        self.assertEqual(
            _router._capability_receipt_rejections(tampered, LOCK),
            ["capability_receipt_malformed"],
        )
        self.assertEqual(
            _router._capability_receipt_rejections(foreign, LOCK),
            ["capability_receipt_program_lock_mismatch"],
        )
        self.assertEqual(_router._capability_receipt_rejections(self._receipt(), LOCK), [])

    def test_a_fresh_verified_receipt_routes(self) -> None:
        root = Path(__file__).resolve().parents[1]
        result = route_contract(
            GITHUB_VERIFY,
            subsystem_root=root,
            capability_receipts={"ci-github-actions": self._receipt()},
        )
        self.assertEqual(result["adapter_id"], "ci-github-actions")


if __name__ == "__main__":
    unittest.main()
