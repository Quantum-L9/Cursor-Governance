from __future__ import annotations

import unittest
from pathlib import Path


class GraphitiContextReaderTests(unittest.TestCase):
    def test_source_contains_search_only(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "context_reader.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"search"', source)
        for forbidden in ("add_memory", "cmd_write", "write_memory"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
