from __future__ import annotations

import unittest
from pathlib import Path

from adapters.common.imports import load_module


class ClaudeBoundedBridgeTests(unittest.TestCase):
    def test_campaign_disables_autonomous_merge(self) -> None:
        root = Path(__file__).resolve().parents[1]
        module = load_module(
            root / "campaign_mapper.py",
            "pes_test_claude_campaign_mapper",
        )
        value = module.map_campaign(
            {
                "task_id": "TASK-1",
                "objective": "Build",
                "base_sha": "1" * 40,
                "requested_actions": ["local_write"],
                "program_digest": "sha256:" + "2" * 64,
                "contract_digest": "sha256:" + "3" * 64,
            },
            "dispatch-12345678",
        )
        self.assertFalse(value["autonomous_merge"])
        self.assertEqual(value["authority_profile"], "program_deploy_max_autonomy")


if __name__ == "__main__":
    unittest.main()
