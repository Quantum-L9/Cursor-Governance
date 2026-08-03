from __future__ import annotations

import unittest
from pathlib import Path

import yaml


class RegistryAlignmentTests(unittest.TestCase):
    def test_registry_descriptors_and_providers_exist(self) -> None:
        root = Path(__file__).resolve().parents[1]
        registry = yaml.safe_load(
            (root / "registry/EXECUTION_ADAPTER_REGISTRY.yaml").read_text(encoding="utf-8")
        )
        for entry in registry["adapters"]:
            self.assertTrue((root / entry["descriptor"]).is_file())
            self.assertTrue((root / entry["provider_module"]).is_file())


if __name__ == "__main__":
    unittest.main()
