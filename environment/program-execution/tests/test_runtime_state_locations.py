from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from adapters.common.runtime_store import RuntimeStore


class RuntimeStateLocationTests(unittest.TestCase):
    def test_runtime_store_uses_supplied_external_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RuntimeStore(directory)
            path = store.save("dispatch-001", {"adapter_id": "test"})
            self.assertTrue(path.is_relative_to(Path(directory).resolve()))

    def test_path_escape_is_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RuntimeStore(directory)
            with self.assertRaisesRegex(ValueError, "unsafe runtime identifier"):
                store.save("../../escape", {"adapter_id": "test"})


if __name__ == "__main__":
    unittest.main()
