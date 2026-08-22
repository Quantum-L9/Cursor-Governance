"""The core manifest generator must not rewrite a manifest into another shape.

Three manifests under `environment/program-execution/core/` are hashed by three
different validators and do not agree on shape: `core/MANIFEST.yaml` names its
artifact with `artifact:` and records `bytes:` per file, while both distributable
templates use `template:` and carry `path`+`sha256` only.

The generator used to emit one fixed shape for all of them, so running it against
the controller template turned `template:` into `artifact:` and added a `bytes:`
key to every entry — a manifest its own validator then rejected. These tests pin
that the shape is read from the target rather than decided by the generator.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
CORE = REPO / "environment" / "program-execution" / "core"
GENERATOR = CORE / "scripts" / "generate_manifest.py"

TEMPLATES = (
    "program-execution-blueprint-template",
    "program-execution-controller-template",
)


def _load_generator():
    spec = importlib.util.spec_from_file_location("pe_core_generate_manifest", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


generate_manifest = _load_generator()


def _manifest(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture
def template_tree(tmp_path: Path) -> Path:
    """A miniature template carrying a `template:`-shaped manifest."""
    root = tmp_path / "demo-template"
    (root / "scripts").mkdir(parents=True)
    (root / "README.md").write_text("readme\n", encoding="utf-8")
    (root / "scripts" / "run.py").write_text("x = 1\n", encoding="utf-8")
    (root / "MANIFEST.yaml").write_text(
        yaml.safe_dump(
            {
                "schema": "program-execution-demo.manifest.v2",
                "schema_version": "2.0.0",
                "template": "program-execution-demo",
                "files": [{"path": "README.md", "sha256": "stale"}],
                "integrity": {"algorithm": "sha256", "self_excluded": True},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return root


class TestShapePreservation:
    def test_template_manifest_keeps_its_template_key(self, template_tree: Path) -> None:
        generate_manifest.generate(template_tree)

        doc = _manifest(template_tree / "MANIFEST.yaml")
        assert "template" in doc, "the generator replaced `template:` with another key"
        assert "artifact" not in doc
        assert doc["template"] == "program-execution-demo"

    def test_template_manifest_gains_no_bytes_key(self, template_tree: Path) -> None:
        generate_manifest.generate(template_tree)

        entries = _manifest(template_tree / "MANIFEST.yaml")["files"]
        assert entries, "manifest lost its file list"
        for entry in entries:
            assert set(entry) == {"path", "sha256"}, f"entry shape changed: {entry}"

    def test_digests_are_actually_refreshed(self, template_tree: Path) -> None:
        generate_manifest.generate(template_tree)

        entries = {
            e["path"]: e["sha256"] for e in _manifest(template_tree / "MANIFEST.yaml")["files"]
        }
        assert entries["README.md"] != "stale"
        assert "scripts/run.py" in entries, "a new file was not picked up"

    def test_top_level_key_order_survives(self, template_tree: Path) -> None:
        before = list(_manifest(template_tree / "MANIFEST.yaml"))

        generate_manifest.generate(template_tree)

        assert list(_manifest(template_tree / "MANIFEST.yaml")) == before

    def test_a_manifest_recording_bytes_keeps_recording_them(self, tmp_path: Path) -> None:
        root = tmp_path / "sys"
        root.mkdir()
        (root / "a.md").write_text("hello\n", encoding="utf-8")
        (root / "MANIFEST.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema": "s.v2",
                    "schema_version": "2.0.0",
                    "artifact": "sys-v2",
                    "files": [{"path": "a.md", "sha256": "stale", "bytes": 0}],
                    "integrity": {"algorithm": "sha256", "self_excluded": True},
                    "summary": {"file_count": 1, "total_bytes": 0},
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        generate_manifest.generate(root)

        doc = _manifest(root / "MANIFEST.yaml")
        assert set(doc["files"][0]) == {"path", "sha256", "bytes"}
        assert doc["files"][0]["bytes"] == 6
        assert doc["summary"] == {"file_count": 1, "total_bytes": 6}

    def test_creating_a_new_manifest_still_requires_identity(self, tmp_path: Path) -> None:
        root = tmp_path / "fresh"
        root.mkdir()
        (root / "a.md").write_text("x\n", encoding="utf-8")

        with pytest.raises(SystemExit):
            generate_manifest.generate(root)

        generate_manifest.generate(root, "schema.v2", "artifact-v2")
        assert _manifest(root / "MANIFEST.yaml")["artifact"] == "artifact-v2"


class TestDeterminism:
    def test_regeneration_is_byte_identical(self, template_tree: Path) -> None:
        generate_manifest.generate(template_tree)
        once = (template_tree / "MANIFEST.yaml").read_bytes()

        generate_manifest.generate(template_tree)

        assert (template_tree / "MANIFEST.yaml").read_bytes() == once

    def test_the_manifest_never_describes_itself(self, template_tree: Path) -> None:
        generate_manifest.generate(template_tree)

        paths = {e["path"] for e in _manifest(template_tree / "MANIFEST.yaml")["files"]}
        assert "MANIFEST.yaml" not in paths

    def test_compiled_python_debris_is_excluded(self, template_tree: Path) -> None:
        cache = template_tree / "scripts" / "__pycache__"
        cache.mkdir()
        (cache / "run.cpython-312.pyc").write_bytes(b"\x00")

        generate_manifest.generate(template_tree)

        paths = {e["path"] for e in _manifest(template_tree / "MANIFEST.yaml")["files"]}
        assert not any("__pycache__" in p or p.endswith(".pyc") for p in paths)


class TestRepositoryManifestsAreCurrent:
    """The checked-in manifests must already satisfy their own generator."""

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_template_manifest_is_regenerable_without_change(self, template: str) -> None:
        target = CORE / template / "MANIFEST.yaml"
        before = target.read_bytes()
        try:
            generate_manifest.generate(CORE / template)
            assert target.read_bytes() == before, (
                f"{template}/MANIFEST.yaml is stale — run "
                "`python3 ops/scripts/sync_generated_artifacts.py --force`"
            )
        finally:
            target.write_bytes(before)
