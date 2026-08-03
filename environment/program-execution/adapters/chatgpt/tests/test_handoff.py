from __future__ import annotations

import unittest
from pathlib import Path

import yaml


class ChatGPTHandoffTests(unittest.TestCase):
    def test_adapter_is_dormant(self) -> None:
        value = yaml.safe_load((Path(__file__).resolve().parents[1] / "ADAPTER.yaml").read_text())
        self.assertEqual(value["status"]["default"], "dormant")


if __name__ == "__main__":
    unittest.main()
