from __future__ import annotations

import unittest
from pathlib import Path


class NoDirectGraphitiWriterTests(unittest.TestCase):
    def test_graphiti_integration_is_read_only(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = (root / "integrations/graphiti/context_reader.py").read_text(encoding="utf-8")
        for forbidden in ("add_memory", "write_memory", "cmd_write"):
            self.assertNotIn(forbidden, source)
        self.assertIn("search", source)


if __name__ == "__main__":
    unittest.main()
