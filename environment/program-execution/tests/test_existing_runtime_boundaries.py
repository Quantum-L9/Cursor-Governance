from __future__ import annotations

import unittest
from pathlib import Path


class ExistingRuntimeBoundaryTests(unittest.TestCase):
    def test_bounded_adapter_reuses_existing_runtime(self) -> None:
        root = Path(__file__).resolve().parents[1]
        bridge = root / "integrations/claude-code-bounded-autonomy/bridge.py"
        text = bridge.read_text(encoding="utf-8")
        self.assertIn("environment/claude-code/autonomy/cli.py", text)
        self.assertNotIn("class Scheduler", text)

    def test_root_autonomy_bridge_does_not_define_leases(self) -> None:
        root = Path(__file__).resolve().parents[1]
        bridge = root / "integrations/autonomy-control-plane/bridge.py"
        text = bridge.read_text(encoding="utf-8")
        self.assertNotIn("class LeaseManager", text)
        self.assertIn("autonomy/adapters/orchestrator.py", text)


if __name__ == "__main__":
    unittest.main()
