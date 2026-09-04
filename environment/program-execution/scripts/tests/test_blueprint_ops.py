"""A Blueprint inventories only the regular files it owns.

`rglob` reports a symlink whose target is a file as a file, so a link inside
the blueprint to a path outside it was digested into MANIFEST.yaml as if it
were blueprint content, and a broken link silently vanished from the
inventory. Both are now refused where the inventory is taken.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PE_ROOT / "scripts/blueprint_ops.py"


def _load():
    spec = importlib.util.spec_from_file_location("blueprint_ops_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BlueprintInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ops = _load()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.blueprint = self.root / "blueprint"
        self.blueprint.mkdir()
        (self.blueprint / "PROGRAM.yaml").write_text("program: {id: demo}\n", encoding="utf-8")

    def test_a_clean_tree_is_inventoried_with_every_file(self) -> None:
        (self.blueprint / "nested").mkdir()
        (self.blueprint / "nested" / "TASK-001.md").write_text("# task\n", encoding="utf-8")
        self.ops.write_manifest(self.blueprint, "test")
        manifest = yaml.safe_load((self.blueprint / "MANIFEST.yaml").read_text(encoding="utf-8"))
        self.assertEqual(
            sorted(item["path"] for item in manifest["files"]),
            ["PROGRAM.yaml", "nested/TASK-001.md"],
        )

    def test_a_symlink_to_a_file_outside_the_blueprint_is_refused(self) -> None:
        outside = self.root / "secret.yaml"
        outside.write_text("outside: true\n", encoding="utf-8")
        (self.blueprint / "leak.yaml").symlink_to(outside)
        with self.assertRaises(self.ops.BlueprintTreeError) as ctx:
            self.ops.write_manifest(self.blueprint, "test")
        self.assertIn("leak.yaml", str(ctx.exception))
        self.assertFalse((self.blueprint / "MANIFEST.yaml").exists())

    def test_a_broken_symlink_does_not_vanish_silently(self) -> None:
        (self.blueprint / "gone.md").symlink_to(self.root / "does-not-exist.md")
        with self.assertRaises(self.ops.BlueprintTreeError) as ctx:
            self.ops.write_manifest(self.blueprint, "test")
        self.assertIn("gone.md", str(ctx.exception))

    def test_a_symlinked_directory_is_refused(self) -> None:
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "x.md").write_text("x\n", encoding="utf-8")
        (self.blueprint / "tasks").symlink_to(elsewhere)
        with self.assertRaises(self.ops.BlueprintTreeError):
            self.ops.write_manifest(self.blueprint, "test")

    def test_placeholder_scan_refuses_symlinks_too(self) -> None:
        outside = self.root / "outside.md"
        outside.write_text("clean\n", encoding="utf-8")
        (self.blueprint / "link.md").symlink_to(outside)
        with self.assertRaises(self.ops.BlueprintTreeError):
            self.ops.scan_placeholders(self.blueprint)

    def test_the_compiler_refuses_a_symlink_that_rides_in_a_recompile(self) -> None:
        """`compile_source` stages from a copy with `symlinks=True`; the manifest step
        must still refuse rather than digest the link's target."""
        self.assertIn("symlinks=True", (PE_ROOT / "scripts/compile_campaign_source.py").read_text())
        (self.blueprint / "link.yaml").symlink_to(self.root / "nowhere.yaml")
        with self.assertRaises(self.ops.BlueprintTreeError):
            self.ops.tree_files(self.blueprint)


if __name__ == "__main__":
    unittest.main()
