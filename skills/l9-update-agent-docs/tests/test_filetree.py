from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
SCRIPTS = PACK / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


df = load("doc_filetree", SCRIPTS / "doc_filetree.py")
gm = load("generate_module_readmes", SCRIPTS / "generate_module_readmes.py")


def test_write_filetree_lists_modules_and_skips_wip(tmp_path: Path):
    (tmp_path / "pkg" / "sub").mkdir(parents=True)
    (tmp_path / "pkg" / "mod.py").write_text("def top():\n    return 1\n", encoding="utf-8")
    (tmp_path / "pkg" / "sub" / "inner.py").write_text("class Inner:\n    pass\n", encoding="utf-8")
    (tmp_path / "WIP" / "scratch").mkdir(parents=True)
    (tmp_path / "WIP" / "scratch" / "x.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    inventory, written, admission = df.write_filetree(tmp_path)
    assert written is True
    assert admission == "create"
    text = (tmp_path / "filetree.md").read_text(encoding="utf-8")
    assert df.validate_filetree(text) == []
    paths = [row.path for row in inventory.modules]
    assert paths == ["pkg", "pkg/sub"]
    assert {row.kind for row in inventory.modules if row.path == "pkg/sub"} == {"submodule"}
    assert "WIP" not in text
    parsed = df.parse_inventory(text)
    assert [row.path for row in parsed.modules] == paths
    assert "README.md" in parsed.root_files


def test_filetree_lists_corpus_and_index_kinds(tmp_path: Path):
    (tmp_path / "protocols").mkdir()
    (tmp_path / "protocols" / "a.md").write_text("# A\n", encoding="utf-8")
    (tmp_path / "protocols" / "b.md").write_text("# B\n", encoding="utf-8")
    (tmp_path / "pkg" / "a").mkdir(parents=True)
    (tmp_path / "pkg" / "b").mkdir()
    (tmp_path / "pkg" / "a" / "a.py").write_text("def a():\n    return 1\n", encoding="utf-8")
    (tmp_path / "pkg" / "b" / "b.py").write_text("def b():\n    return 1\n", encoding="utf-8")
    inventory, written, admission = df.write_filetree(tmp_path)
    assert written is True
    assert admission == "create"
    kinds = {row.path: row.kind for row in inventory.modules}
    assert kinds["protocols"] == "corpus"
    assert kinds["pkg"] == "index"
    assert kinds["pkg/a"] == "submodule"
    text = (tmp_path / "filetree.md").read_text(encoding="utf-8")
    parsed = df.parse_inventory(text)
    assert {row.path: row.kind for row in parsed.modules}["protocols"] == "corpus"


def test_discover_modules_reads_filetree_not_a_second_walk(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("def top():\n    return 1\n", encoding="utf-8")
    df.write_filetree(tmp_path)
    (tmp_path / "ghost").mkdir()
    (tmp_path / "ghost" / "late.py").write_text("def late():\n    return 1\n", encoding="utf-8")
    found = gm.discover_module_paths(tmp_path, {"defaults": {}, "subsystems": {}})
    assert found == ["pkg"]


def test_missing_readme_diagnosis_uses_filetree_inventory(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("def top():\n    return 1\n", encoding="utf-8")
    inventory, _written, _admission = df.write_filetree(tmp_path)
    assert any(row.path == "pkg" and row.readme == "missing" for row in inventory.modules)
    written = gm.write_missing_module_readmes(tmp_path, inventory=inventory)
    assert written == ["pkg/README.md"]
    refreshed, _written, _admission = df.write_filetree(tmp_path)
    assert any(row.path == "pkg" and row.readme == "present" for row in refreshed.modules)


def test_filetree_refreshes_owned_stale_and_preserves_unowned(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("def top():\n    return 1\n", encoding="utf-8")
    _inventory, written, admission = df.write_filetree(tmp_path)
    assert written is True
    assert admission == "create"
    owned = (tmp_path / "filetree.md").read_text(encoding="utf-8")
    (tmp_path / "pkg" / "later.py").write_text("def later():\n    return 1\n", encoding="utf-8")
    _inventory, refreshed, refresh_admission = df.write_filetree(tmp_path)
    assert refreshed is True
    assert refresh_admission == "refresh"
    assert "later.py" in (tmp_path / "filetree.md").read_text(encoding="utf-8")
    (tmp_path / "filetree.md").write_text("# Hand filetree\n\nDo not smash.\n", encoding="utf-8")
    _inventory, wrote_again, preserve_admission = df.write_filetree(tmp_path)
    assert wrote_again is False
    assert preserve_admission == "preserve"
    leftover = "# Hand filetree\n\nDo not smash.\n"
    assert (tmp_path / "filetree.md").read_text(encoding="utf-8") == leftover
    assert owned != "# Hand filetree\n\nDo not smash.\n"
