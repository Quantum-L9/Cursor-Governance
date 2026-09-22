from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
SCRIPTS = PACK / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name: str, path: Path):
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gm = load("generate_module_readmes", SCRIPTS / "generate_module_readmes.py")
rr = load("readme_renderers", SCRIPTS / "readme_renderers.py")


def test_discover_modules_and_submodules(tmp_path: Path):
    (tmp_path / "pkg" / "sub").mkdir(parents=True)
    (tmp_path / "pkg" / "mod.py").write_text("def top():\n    return 1\n", encoding="utf-8")
    (tmp_path / "pkg" / "sub" / "inner.py").write_text("class Inner:\n    pass\n", encoding="utf-8")
    (tmp_path / "docs" / "notes").mkdir(parents=True)
    (tmp_path / "docs" / "notes" / "x.py").write_text("x = 1\n", encoding="utf-8")
    found = gm.discover_module_paths(tmp_path, {"defaults": {}, "subsystems": {}})
    assert found == ["pkg", "pkg/sub"]


def test_write_missing_creates_module_and_submodule_readmes(tmp_path: Path):
    (tmp_path / "pkg" / "sub").mkdir(parents=True)
    (tmp_path / "pkg" / "mod.py").write_text(
        '"""Top module."""\n\ndef top():\n    return 1\n', encoding="utf-8"
    )
    (tmp_path / "pkg" / "sub" / "inner.py").write_text("class Inner:\n    pass\n", encoding="utf-8")
    written = gm.write_missing_module_readmes(tmp_path)
    assert "pkg/README.md" in written
    assert "pkg/sub/README.md" in written
    parent = (tmp_path / "pkg" / "README.md").read_text(encoding="utf-8")
    child = (tmp_path / "pkg" / "sub" / "README.md").read_text(encoding="utf-8")
    assert rr.marker_for("module") in parent
    assert gm.classify_readme(tmp_path / "pkg" / "README.md") == "generated"
    assert "Top module." in parent
    assert "def top" in parent
    assert "`Inner`" in child
    # Second run over an unchanged tree is a no-op: the corpus converges.
    assert gm.write_missing_module_readmes(tmp_path) == []


def test_never_writes_root_readme(tmp_path: Path):
    (tmp_path / "ok.py").write_text("class Rootish:\n    pass\n", encoding="utf-8")
    written = gm.write_missing_module_readmes(tmp_path)
    assert "README.md" not in written
    assert not (tmp_path / "README.md").exists()


def test_skips_handwritten_readme(tmp_path: Path):
    pkg = tmp_path / "kept"
    pkg.mkdir()
    (pkg / "ok.py").write_text("class Keep:\n    pass\n", encoding="utf-8")
    (pkg / "README.md").write_text("---\nauto_generated: false\n---\n# Hand\n", encoding="utf-8")
    assert gm.write_missing_module_readmes(tmp_path) == []
    assert (pkg / "README.md").read_text(encoding="utf-8").startswith("---")


def test_regenerate_preserves_unowned_readme_without_marker(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "ok.py").write_text("class Keep:\n    pass\n", encoding="utf-8")
    (pkg / "README.md").write_text("# Human notes\n", encoding="utf-8")
    assert gm.write_missing_module_readmes(tmp_path, regenerate=True) == []
    assert (pkg / "README.md").read_text(encoding="utf-8") == "# Human notes\n"


LEGACY_GENERATED = (
    "# Pkg\n\n"
    "**Path:** `pkg` | **Tier:** operations\n\n"
    "## Purpose\n\nOld generator output.\n\n"
    "## Components\n\n_No public classes in this path._\n\n"
    "## Functions\n\n_No public module-level functions._\n\n"
    "## Exports\n\n_No `__all__` exports._\n\n"
    "## Dependencies\n\n_No imports parsed._\n"
)


def test_classify_readme_distinguishes_marker_legacy_and_handwritten(tmp_path: Path):
    marked = tmp_path / "marked.md"
    marked.write_text(f"# X\n\n{gm.GENERATED_MARKER}\n", encoding="utf-8")
    legacy = tmp_path / "legacy.md"
    legacy.write_text(LEGACY_GENERATED, encoding="utf-8")
    opted_out = tmp_path / "opted_out.md"
    opted_out.write_text("---\nauto_generated: false\n---\n" + LEGACY_GENERATED, encoding="utf-8")
    prose = tmp_path / "prose.md"
    prose.write_text("# Human notes\n\n## Purpose\n\nMine.\n", encoding="utf-8")
    assert gm.classify_readme(tmp_path / "absent.md") == "missing"
    assert gm.classify_readme(marked) == "generated"
    assert gm.classify_readme(legacy) == "legacy_generated"
    assert gm.classify_readme(opted_out) == "handwritten"
    assert gm.classify_readme(prose) == "handwritten"
    assert gm.is_generated(legacy) and gm.is_legacy_generated(legacy)
    assert not gm.is_handwritten(legacy)
    assert gm.is_handwritten(opted_out) and gm.is_handwritten(prose)


def test_legacy_generated_readme_migrates_to_the_current_marker(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "ok.py").write_text('"""Pkg."""\n\nclass Keep:\n    pass\n', encoding="utf-8")
    (pkg / "README.md").write_text(LEGACY_GENERATED, encoding="utf-8")
    # Reconciliation refreshes a stale generator-owned README unconditionally.
    # A corpus that only converges behind a flag never converges.
    assert gm.write_missing_module_readmes(tmp_path) == ["pkg/README.md"]
    text = (pkg / "README.md").read_text(encoding="utf-8")
    assert rr.marker_for("module") in text
    assert gm.GENERATED_MARKER not in text
    assert "`Keep`" in text
    assert gm.classify_readme(pkg / "README.md") == "generated"
    assert gm.write_missing_module_readmes(tmp_path) == []


def test_regenerate_keeps_legacy_opt_out_handwritten(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "ok.py").write_text("class Keep:\n    pass\n", encoding="utf-8")
    body = "---\nauto_generated: false\n---\n" + LEGACY_GENERATED
    (pkg / "README.md").write_text(body, encoding="utf-8")
    assert gm.write_missing_module_readmes(tmp_path, regenerate=True) == []
    assert (pkg / "README.md").read_text(encoding="utf-8") == body


def test_cli_refreshes_legacy_corpus_and_gaps_reports_it(tmp_path: Path, capsys):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "ok.py").write_text("class Keep:\n    pass\n", encoding="utf-8")
    (pkg / "README.md").write_text(LEGACY_GENERATED, encoding="utf-8")
    assert gm.main(["--root", str(tmp_path), "--gaps"]) == 0
    assert "refresh\tpkg" in capsys.readouterr().out
    assert gm.main(["--root", str(tmp_path)]) == 0
    assert rr.marker_for("module") in (pkg / "README.md").read_text(encoding="utf-8")
    assert gm.main(["--root", str(tmp_path), "--gaps"]) == 0
    assert "gaps\tnone" in capsys.readouterr().out


def test_cli_dry_run_reports_the_plan_and_writes_nothing(tmp_path: Path, capsys):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "ok.py").write_text("class Keep:\n    pass\n", encoding="utf-8")
    assert gm.main(["--root", str(tmp_path), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "create=1" in out
    assert not (tmp_path / "pkg" / "README.md").exists()


def test_extract_facts_ignores_ancestor_dot_l9(tmp_path: Path):
    root = tmp_path / ".l9" / "wt"
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "mod.py").write_text("class Visible:\n    pass\n", encoding="utf-8")
    facts = gm.extract_subsystem_facts(root, "pkg")
    assert [cls.name for cls in facts.classes] == ["Visible"]
    assert facts.files == ["pkg/mod.py"]


def test_corpus_and_index_folders_get_type_index_readmes(tmp_path: Path):
    (tmp_path / "protocols").mkdir()
    (tmp_path / "protocols" / "alpha.md").write_text("# A\n", encoding="utf-8")
    (tmp_path / "protocols" / "beta.md").write_text("# B\n", encoding="utf-8")
    (tmp_path / "prompts").mkdir()
    (tmp_path / "lib" / "schemas").mkdir(parents=True)
    (tmp_path / "lib" / "schemas" / "one.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "lib" / "schemas" / "two.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "pkg" / "a").mkdir(parents=True)
    (tmp_path / "pkg" / "b").mkdir()
    (tmp_path / "pkg" / "a" / "a.py").write_text("def a():\n    return 1\n", encoding="utf-8")
    (tmp_path / "pkg" / "b" / "b.py").write_text("def b():\n    return 1\n", encoding="utf-8")
    (tmp_path / "deep" / "nested" / "schemas").mkdir(parents=True)
    (tmp_path / "deep" / "nested" / "schemas" / "only.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "skills" / "demo" / "references").mkdir(parents=True)
    (tmp_path / "skills" / "demo" / "SKILL.md").write_text("# Demo\n", encoding="utf-8")
    (tmp_path / "skills" / "demo" / "references" / "note.md").write_text("# N\n", encoding="utf-8")
    (tmp_path / "skills" / "demo" / "references" / "other.md").write_text("# O\n", encoding="utf-8")
    (tmp_path / "WIP" / "profiles").mkdir(parents=True)
    (tmp_path / "WIP" / "profiles" / "x.md").write_text("# X\n", encoding="utf-8")
    (tmp_path / "foundation" / "security").mkdir(parents=True)
    written = set(gm.write_missing_module_readmes(tmp_path))
    assert "protocols/README.md" in written
    assert "lib/schemas/README.md" in written
    assert "pkg/README.md" in written
    assert "pkg/a/README.md" in written
    proto = (tmp_path / "protocols" / "README.md").read_text(encoding="utf-8")
    assert rr.marker_for("corpus") in proto
    assert "Markdown" in proto
    assert "alpha.md" in proto
    index = (tmp_path / "pkg" / "README.md").read_text(encoding="utf-8")
    assert rr.marker_for("index") in index
    assert "**Kind:** index" in index
    # An empty directory earns no README: a generated page whose only claim
    # is that the directory is reserved and has no files costs a read and
    # returns nothing.
    assert "prompts/README.md" not in written
    assert not (tmp_path / "prompts" / "README.md").exists()
    assert "deep/nested/schemas/README.md" not in written
    assert "skills/demo/references/README.md" not in written
    assert "WIP/profiles/README.md" not in written
    assert "foundation/README.md" not in written
    assert "foundation/security/README.md" not in written


def test_changed_filter_limits_writes(tmp_path: Path):
    (tmp_path / "alpha").mkdir()
    (tmp_path / "beta").mkdir()
    (tmp_path / "alpha" / "a.py").write_text("def a():\n    return 1\n", encoding="utf-8")
    (tmp_path / "beta" / "b.py").write_text("def b():\n    return 1\n", encoding="utf-8")
    written = gm.write_missing_module_readmes(tmp_path, changed=["beta/b.py"])
    assert written == ["beta/README.md"]
    assert not (tmp_path / "alpha" / "README.md").exists()


def test_compat_wrapper_re_exports_exactly_the_generator_api():
    wrapper = load(
        "generate_subsystem_readmes", PACK.parents[1] / "scripts" / "generate_subsystem_readmes.py"
    )
    assert list(wrapper.__all__) == list(gm.__all__)
    for name in gm.__all__:
        assert getattr(wrapper, name) is getattr(gm, name), name
