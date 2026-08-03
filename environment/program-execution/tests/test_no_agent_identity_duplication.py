from __future__ import annotations

import unittest
from pathlib import Path


class NoAgentIdentityDuplicationTests(unittest.TestCase):
    def test_no_agent_registry_inside_subsystem(self) -> None:
        root = Path(__file__).resolve().parents[1]
        matches = list(root.rglob("agent_registry.yaml"))
        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
