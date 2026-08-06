from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


class RepositoryAlignmentTests(unittest.TestCase):
    def _load(self):
        root = Path(__file__).resolve().parents[1]
        path = root / "scripts/apply_repository_alignment.py"
        spec = importlib.util.spec_from_file_location("alignment_module", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("alignment module could not be loaded")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_alignment_is_narrow_and_idempotent(self) -> None:
        module = self._load()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [
                "CANONICAL_LAW.md",
                "AGENTS.md",
                "README.md",
                "Makefile",
                "environment/agents/docs/WORK_CLAIM_PROTOCOL.md",
            ]
            for relative in paths:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"original:{relative}\n", encoding="utf-8")
            first = module.apply(root)
            second = module.apply(root)
            self.assertEqual(sorted(first), sorted(paths))
            self.assertEqual(second, [])
            for relative in paths:
                text = (root / relative).read_text(encoding="utf-8")
                self.assertTrue(text.startswith(f"original:{relative}\n"))
                self.assertEqual(text.count("PROGRAM_EXECUTION_ADAPTER_LAYER_V1"), 1)


if __name__ == "__main__":
    unittest.main()
