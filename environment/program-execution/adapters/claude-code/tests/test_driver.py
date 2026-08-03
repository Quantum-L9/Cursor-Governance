from __future__ import annotations

import unittest
from pathlib import Path


class ClaudeDriverSourceTests(unittest.TestCase):
    def test_dangerous_permission_flag_absent(self) -> None:
        text = (Path(__file__).resolve().parents[1] / "driver.py").read_text()
        self.assertNotIn("dangerously-skip-permissions", text)
        self.assertIn("--output-format", text)


if __name__ == "__main__":
    unittest.main()
