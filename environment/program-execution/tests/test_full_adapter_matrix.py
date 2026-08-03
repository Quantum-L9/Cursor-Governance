from __future__ import annotations

import unittest
from pathlib import Path

import yaml


class FullAdapterMatrixTests(unittest.TestCase):
    def test_all_expected_adapter_ids_are_registered(self) -> None:
        root = Path(__file__).resolve().parents[1]
        value = yaml.safe_load(
            (root / "registry/EXECUTION_ADAPTER_REGISTRY.yaml").read_text(encoding="utf-8")
        )
        actual = {item["adapter_id"] for item in value["adapters"]}
        expected = {
            "cursor-foreground",
            "cursor-background",
            "claude-code-direct",
            "claude-code-bounded-autonomy",
            "chatgpt-manual-handoff",
            "ci-generic-shell",
            "ci-github-actions",
            "github-remote-actions",
            "github-checks",
            "github-deployments",
            "target-deployment-factory",
        }
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
