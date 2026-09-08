"""Tool caches are never manifest inputs, and every recomputation agrees.

A `mypy` / `pytest` / `ruff` run whose cwd sits inside a template leaves a
gitignored cache directory behind. The core generator once inventoried it,
which committed digests of local cache state that churned on every run. The
generator and the three validators that recompute digests must skip the same
names, or a cache on disk becomes a permanent inventory mismatch.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generate_manifest = _load("core_generate_manifest", ROOT / "scripts/generate_manifest.py")
validate_pair = _load("core_validate_pair", ROOT / "scripts/validate_pair.py")
validate_controller = _load(
    "core_validate_controller",
    ROOT / "program-execution-controller-template/scripts/validate_controller.py",
)
validate_blueprint = _load(
    "core_validate_blueprint",
    ROOT / "program-execution-blueprint-template/scripts/validate_blueprint.py",
)


class ManifestInputTests(unittest.TestCase):
    def test_tool_caches_are_not_manifest_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "scripts").mkdir()
            (root / "scripts" / "real.py").write_text("x = 1\n", encoding="utf-8")
            for cache in (".mypy_cache/3.12", ".pytest_cache/v", ".ruff_cache/0.1", "__pycache__"):
                (root / "scripts" / cache).mkdir(parents=True)
                (root / "scripts" / cache / "cache.db").write_bytes(b"\x00")
            (root / "MANIFEST.yaml").write_text("files: []\n", encoding="utf-8")
            found = generate_manifest.manifest_inputs(root)
            inputs = [p.relative_to(root).as_posix() for p in found]
        self.assertEqual(inputs, ["scripts/real.py"])

    def test_validators_skip_the_same_names_as_the_generator(self) -> None:
        expected = generate_manifest.TOOL_CACHE_DIRS
        self.assertIn(".mypy_cache", expected)
        for module in (validate_pair, validate_controller, validate_blueprint):
            self.assertEqual(module.TOOL_CACHE_DIRS, expected, module.__name__)

    def test_committed_manifests_carry_no_cache_entries(self) -> None:
        for manifest in (
            ROOT / "MANIFEST.yaml",
            ROOT / "program-execution-controller-template/MANIFEST.yaml",
            ROOT / "program-execution-blueprint-template/MANIFEST.yaml",
        ):
            text = manifest.read_text(encoding="utf-8")
            for name in generate_manifest.TOOL_CACHE_DIRS:
                self.assertNotIn(f"/{name}/", text, f"{manifest.name} inventories {name}")


if __name__ == "__main__":
    unittest.main()
