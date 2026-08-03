from __future__ import annotations

import unittest
from pathlib import Path


class CursorBackgroundDescriptorTests(unittest.TestCase):
    def test_descriptor_declares_conditional_cancellation(self) -> None:
        import yaml

        value = yaml.safe_load((Path(__file__).resolve().parents[1] / "ADAPTER.yaml").read_text())
        self.assertEqual(value["capabilities"]["cancellation"], "conditional")


if __name__ == "__main__":
    unittest.main()
