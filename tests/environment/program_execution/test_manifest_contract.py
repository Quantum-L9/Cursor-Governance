"""Contract tests for the Program Execution adapter-layer manifest.

The manifest is advisory (see TODO.md): nothing in the PR gate or CI enforces
it. That makes these tests the only thing standing between the generator and
the validator, so they assert the two agree about what the manifest describes
rather than merely that each runs.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "environment" / "program-execution" / "scripts"


def _load(name: str):
    path = SCRIPTS / f"{name}.py"
    if not path.is_file():
        raise AssertionError(f"missing manifest script: {path}")
    spec = importlib.util.spec_from_file_location(f"pe_manifest_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


generate_manifest = _load("generate_manifest")
validate_manifest = _load("validate_manifest")


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A miniature Program Execution root covering every exclusion rule."""
    root = tmp_path / "program-execution"
    (root / "adapters").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "core" / "nested").mkdir(parents=True)

    (root / "README.md").write_text("readme\n", encoding="utf-8")
    (root / "adapters" / "adapter.yaml").write_text("a: 1\n", encoding="utf-8")
    (root / "scripts" / "run.py").write_text("print('run')\n", encoding="utf-8")
    # core/ carries its own MANIFEST.yaml and is out of this manifest's surface.
    (root / "core" / "nested" / "owned.py").write_text("x = 1\n", encoding="utf-8")
    return root


def _write(root: Path) -> dict:
    value = generate_manifest.generate(root)
    (root / "MANIFEST.json").write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return value


def test_generation_is_deterministic(tree: Path) -> None:
    """Two runs over an unchanged tree produce byte-identical output."""
    first = json.dumps(generate_manifest.generate(tree), indent=2, sort_keys=True)
    second = json.dumps(generate_manifest.generate(tree), indent=2, sort_keys=True)
    assert first == second


def test_generate_then_validate_round_trips(tree: Path) -> None:
    _write(tree)
    assert validate_manifest.validate(tree) == []


def test_core_is_excluded_from_both_sides(tree: Path) -> None:
    value = _write(tree)
    paths = {item["path"] for item in value["files"]}
    assert not any(path.startswith("core/") for path in paths)
    assert paths == {"README.md", "adapters/adapter.yaml", "scripts/run.py"}
    # The validator must agree, or core/ would read as a permanent "missing".
    assert validate_manifest.validate(tree) == []


@pytest.mark.parametrize("cache", [".pytest_cache", ".ruff_cache", ".mypy_cache"])
def test_tool_cache_does_not_break_validation(tree: Path, cache: str) -> None:
    """A stray tool cache must not read as an inventory mismatch.

    ``environment/program-execution/peer_execution/pytest.ini`` makes that tree a
    pytest rootdir, so running the suite there drops a ``.pytest_cache/`` inside
    the manifest surface. The generator has always skipped these names; the
    validator used to skip only ``__pycache__`` and reported the difference as a
    failure no regeneration could clear.
    """
    _write(tree)
    cache_dir = tree / "adapters" / cache
    cache_dir.mkdir()
    (cache_dir / "CACHEDIR.TAG").write_text("Signature: 8a477f597d28d172\n", encoding="utf-8")

    assert validate_manifest.validate(tree) == []
    # And regenerating must not adopt the cache either.
    assert {item["path"] for item in generate_manifest.generate(tree)["files"]} == {
        "README.md",
        "adapters/adapter.yaml",
        "scripts/run.py",
    }


def test_pycache_and_bytecode_stay_excluded(tree: Path) -> None:
    _write(tree)
    pycache = tree / "scripts" / "__pycache__"
    pycache.mkdir()
    (pycache / "run.cpython-312.pyc").write_bytes(b"\x00")
    (tree / "scripts" / "stray.pyc").write_bytes(b"\x00")
    assert validate_manifest.validate(tree) == []


def test_digest_mismatch_is_reported(tree: Path) -> None:
    """The validator still catches what it exists to catch."""
    _write(tree)
    (tree / "scripts" / "run.py").write_text("print('tampered')\n", encoding="utf-8")
    errors = validate_manifest.validate(tree)
    assert errors == ["manifest digest mismatch: scripts/run.py"]


def test_untracked_new_file_is_reported(tree: Path) -> None:
    _write(tree)
    (tree / "adapters" / "extra.yaml").write_text("b: 2\n", encoding="utf-8")
    errors = validate_manifest.validate(tree)
    assert len(errors) == 1
    assert "adapters/extra.yaml" in errors[0]
