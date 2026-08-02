from __future__ import annotations

import unittest

from autonomy.adapters.protocol import AdapterConfig


class AdapterBypassTests(unittest.TestCase):
    def test_direct_tool_access_is_visible_in_config(self) -> None:
        config = AdapterConfig.from_dict(
            {
                "adapter_id": "unsafe",
                "adapter_type": "cursor",
                "protocol_version": "1.0.0",
                "executable": "cursor",
                "tool_mediation_mode": "optional",
                "direct_tool_access": True,
                "autonomous_merge": True,
                "supports_background_agents": False,
                "supports_agent_identity": False,
                "supports_lease_propagation": False,
                "supports_heartbeat": False,
                "supports_typed_artifacts": False,
                "supports_independent_review": False,
                "supports_human_gate": False,
                "metadata": {},
            }
        )
        self.assertTrue(config.direct_tool_access)
        self.assertTrue(config.autonomous_merge)
        self.assertEqual(config.tool_mediation_mode, "optional")


if __name__ == "__main__":
    unittest.main()
