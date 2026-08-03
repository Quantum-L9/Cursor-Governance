from __future__ import annotations

import unittest
from pathlib import Path


class BoundedAdapterSourceTests(unittest.TestCase):
    def test_state_root_is_isolated(self) -> None:
        text = (Path(__file__).resolve().parents[1] / "provider.py").read_text()
        self.assertIn(".l9/autonomy/claude-code", text)
        self.assertNotIn("runtime.sqlite3", text)


if __name__ == "__main__":
    unittest.main()
