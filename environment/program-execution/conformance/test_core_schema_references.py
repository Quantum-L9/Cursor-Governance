from __future__ import annotations

import unittest
from pathlib import Path


class CoreSchemaReferenceTests(unittest.TestCase):
    def test_adapter_schemas_do_not_duplicate_core_names(self) -> None:
        root = Path(__file__).resolve().parents[1]
        core = root / "core/program-execution-controller-template/schemas"
        adapter = root / "conformance/schemas"
        core_names = {path.name for path in core.glob("*.json")}
        adapter_names = {path.name for path in adapter.glob("*.json")}
        self.assertEqual(core_names & adapter_names, set())


if __name__ == "__main__":
    unittest.main()
