from __future__ import annotations

import unittest
from pathlib import Path


class NoCoreSchemaDuplicationTests(unittest.TestCase):
    def test_no_duplicate_schema_basenames(self) -> None:
        root = Path(__file__).resolve().parents[1]
        core = root / "core/program-execution-controller-template/schemas"
        adapter = root / "conformance/schemas"
        self.assertFalse(
            {path.name for path in core.glob("*.json")}
            & {path.name for path in adapter.glob("*.json")}
        )


if __name__ == "__main__":
    unittest.main()
