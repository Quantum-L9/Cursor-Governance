from __future__ import annotations

import unittest
from pathlib import Path

from adapters.common.errors import AdapterFailure
from scripts.router import route_contract


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


if __name__ == "__main__":
    unittest.main()
