from __future__ import annotations

import unittest
from pathlib import Path

from adapters.common.imports import load_module


class AutonomyControlPlaneBridgeTests(unittest.TestCase):
    def test_identifiers_are_deterministic(self) -> None:
        root = Path(__file__).resolve().parents[1]
        module = load_module(
            root / "contract_mapper.py",
            "pes_test_autonomy_contract_mapper",
        )
        first = module.deterministic_ids("Program A", "TASK-1", 2, "cursor-foreground")
        second = module.deterministic_ids("Program A", "TASK-1", 2, "cursor-foreground")
        self.assertEqual(first, second)
        self.assertEqual(first["action_id"], "task-1")

    def test_bridge_only_reuses_existing_files(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "bridge.py").read_text(encoding="utf-8")
        self.assertIn("autonomy/adapters/orchestrator.py", source)
        self.assertNotIn("class LeaseManager", source)


if __name__ == "__main__":
    unittest.main()
