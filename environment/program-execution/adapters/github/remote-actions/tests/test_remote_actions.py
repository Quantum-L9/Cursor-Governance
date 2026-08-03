from __future__ import annotations

import unittest
from pathlib import Path


class RemoteActionSourceTests(unittest.TestCase):
    def test_merge_is_not_implemented(self) -> None:
        root = Path(__file__).resolve().parents[1]
        text = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
        self.assertNotIn("pr merge", text)
        self.assertNotIn("enable_auto_merge", text)
        self.assertIn("require_exact_approval", text)


if __name__ == "__main__":
    unittest.main()
