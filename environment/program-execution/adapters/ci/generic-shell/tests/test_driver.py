from __future__ import annotations

import unittest
from pathlib import Path


class GenericShellSourceTests(unittest.TestCase):
    def test_no_shell_true(self) -> None:
        text = (Path(__file__).resolve().parents[1] / "driver.py").read_text()
        self.assertNotIn("shell=True", text)


if __name__ == "__main__":
    unittest.main()
