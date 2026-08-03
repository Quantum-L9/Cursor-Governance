from __future__ import annotations

import unittest
from pathlib import Path


class CursorForegroundDescriptorTests(unittest.TestCase):
    def test_descriptor_exists(self) -> None:
        self.assertTrue((Path(__file__).resolve().parents[1] / "ADAPTER.yaml").is_file())


if __name__ == "__main__":
    unittest.main()
