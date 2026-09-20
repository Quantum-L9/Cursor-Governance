"""Evidence compilation: what a fact may and may not be made to say.

AST facts establish which symbols a file exposes. They do not establish
what a directory is for. These tests pin that line, because crossing it
is what made a compiler directory describe itself as an IR normalizer.
"""

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


ev = load("readme_evidence", SCRIPTS / "readme_evidence.py")
rm = load("readme_model", SCRIPTS / "readme_model.py")
gm = load("generate_module_readmes", SCRIPTS / "generate_module_readmes.py")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def target(path: str, kind: str = "module", **kwargs) -> rm.ReadmeTarget:
    return rm.ReadmeTarget(path=path, kind=kind, title=path.rsplit("/", 1)[-1], **kwargs)


# --- T-M-001: a single module may speak for its directory ---


def test_single_module_purpose_comes_from_its_docstring(tmp_path: Path):
    write(tmp_path / "solo" / "only.py", '"""Normalize the widget stream."""\n\nx = 1\n')
    model = ev.compile_readme_model(tmp_path, target("solo"))
    assert model.purpose == "Normalize the widget stream."


# --- T-M-002: several modules may not ---


def test_multi_module_directory_never_borrows_a_child_purpose(tmp_path: Path):
    write(tmp_path / "scripts" / "harvest.py", '"""Normalize Harvest IR into packets."""\n')
    write(tmp_path / "scripts" / "repo_docs.py", '"""Repository documentation compiler."""\n')
    model = ev.compile_readme_model(tmp_path, target("scripts", "subsystem"))
    assert model.purpose is None
    # The per-module purposes survive; only the directory-level claim is refused.
    assert {module.purpose for module in model.modules} == {
        "Normalize Harvest IR into packets.",
        "Repository documentation compiler.",
    }


def test_configured_purpose_outranks_every_derived_source(tmp_path: Path):
    write(tmp_path / "scripts" / "a.py", '"""A."""\n')
    write(tmp_path / "scripts" / "b.py", '"""B."""\n')
    model = ev.compile_readme_model(
        tmp_path,
        target("scripts", "subsystem", configured_purpose="Compile repository documentation."),
    )
    assert model.purpose == "Compile repository documentation."


# --- T-M-003: a skill's own contract is its purpose ---


def test_skill_purpose_comes_from_the_contract_frontmatter(tmp_path: Path):
    write(
        tmp_path / "skills" / "demo" / "SKILL.md",
        "---\nname: demo\ndescription: compile repository changes into obligations\n---\n\n"
        "# Demo\n\n## Purpose\n\nA longer prose purpose.\n",
    )
    model = ev.compile_readme_model(tmp_path, target("skills/demo", "skill"))
    assert model.purpose == "compile repository changes into obligations"
    assert model.authority_links == ("SKILL.md",)


def test_skill_purpose_falls_back_to_the_purpose_section(tmp_path: Path):
    write(
        tmp_path / "skills" / "demo" / "SKILL.md",
        "# Demo\n\n## Purpose\n\nCompile the thing deterministically.\n\nMore prose.\n",
    )
    model = ev.compile_readme_model(tmp_path, target("skills/demo", "skill"))
    assert model.purpose == "Compile the thing deterministically."


def test_skill_responsibilities_come_from_a_named_section(tmp_path: Path):
    write(
        tmp_path / "skills" / "demo" / "SKILL.md",
        "# Demo\n\n## Ownership boundaries\n\n- owns the inventory\n- owns the receipt\n",
    )
    model = ev.compile_readme_model(tmp_path, target("skills/demo", "skill"))
    assert model.responsibilities == ("owns the inventory", "owns the receipt")


# --- T-M-004: no evidence, no claim ---


def test_unsupported_purpose_is_absent_not_invented(tmp_path: Path):
    write(tmp_path / "quiet" / "mod.py", "x = 1\n")
    model = ev.compile_readme_model(tmp_path, target("quiet"))
    assert model.purpose is None
    assert model.description is None


def test_corpus_purpose_is_absent_without_configuration(tmp_path: Path):
    write(tmp_path / "protocols" / "a.md", "# A\n")
    write(tmp_path / "protocols" / "b.md", "# B\n")
    model = ev.compile_readme_model(tmp_path, target("protocols", "corpus"))
    assert model.purpose is None
    assert model.contents == ("a.md", "b.md")
    assert model.file_types == (("Markdown", 2),)


# --- module identity survives compilation ---


def test_module_identity_is_preserved_per_file(tmp_path: Path):
    write(tmp_path / "pair" / "a.py", "def main():\n    return 1\n")
    write(tmp_path / "pair" / "b.py", "def main():\n    return 2\n")
    model = ev.compile_readme_model(tmp_path, target("pair", "subsystem"))
    assert [module.file for module in model.modules] == ["a.py", "b.py"]
    assert all(len(module.functions) == 1 for module in model.modules)
    assert {module.functions[0].name for module in model.modules} == {"main"}


# --- T-R-003 evidence half: dependency classification ---


def test_dependencies_split_internal_external_and_stdlib():
    deps = ev.classify_dependencies(
        ["json", "pathlib", "yaml", "doc_policy", "jsonschema.validators"],
        frozenset({"doc_policy"}),
    )
    assert deps.internal == ("doc_policy",)
    assert deps.external == ("jsonschema", "yaml")
    assert deps.stdlib == ("json", "pathlib")


def test_relative_imports_are_not_dependencies(tmp_path: Path):
    write(tmp_path / "pkg" / "mod.py", "from . import sibling\nfrom .deep import thing\n")
    model = ev.compile_readme_model(tmp_path, target("pkg"))
    assert model.dependencies.internal == ()
    assert model.dependencies.external == ()


def test_a_wrapped_docstring_summary_is_not_cut_at_the_newline(tmp_path: Path):
    """A one-sentence summary wrapped over two source lines is one sentence."""
    write(
        tmp_path / "pkg" / "mod.py",
        "def is_migration(rel):\n"
        '    """Migration modules are invoked by the framework via file path;\n'
        '    their top-level defs are never referenced by name."""\n'
        "    return True\n",
    )
    model = ev.compile_readme_model(tmp_path, target("pkg"))
    summary = model.modules[0].functions[0].summary
    assert summary.endswith("by name.")
    assert not summary.rstrip().endswith(";")


# --- generated prose must not read as broken output ---


def test_routing_clause_removal_leaves_no_dangling_punctuation(tmp_path: Path):
    """`… asks for AWS —` reads as truncation, not as a finished sentence."""
    write(
        tmp_path / "skills" / "demo" / "SKILL.md",
        "---\ndescription: bind credentials at will; AWS is the one seed — "
        "use when an agent needs a token\n---\n\n# Demo\n",
    )
    model = ev.compile_readme_model(tmp_path, target("skills/demo", "skill"))
    assert model.purpose == "bind credentials at will; AWS is the one seed"
    assert not model.purpose.endswith(("—", "-", ";", ",", ":", "…"))


def test_a_short_description_is_never_ellipsized(tmp_path: Path):
    write(
        tmp_path / "skills" / "demo" / "SKILL.md",
        "---\ndescription: portable saas dashboard ui operator — use when running a dashboard\n"
        "---\n\n# Demo\n",
    )
    model = ev.compile_readme_model(tmp_path, target("skills/demo", "skill"))
    assert model.purpose == "portable saas dashboard ui operator"


def test_one_long_sentence_is_kept_whole_rather_than_ellipsized(tmp_path: Path):
    sentence = "deep-audit pull requests against " + "architecture and invariants " * 11
    write(
        tmp_path / "skills" / "demo" / "SKILL.md",
        f"---\ndescription: {sentence.strip()}. use when auditing\n---\n\n# Demo\n",
    )
    model = ev.compile_readme_model(tmp_path, target("skills/demo", "skill"))
    assert 320 < len(model.purpose) <= 480
    assert not model.purpose.endswith("…")


def test_a_sentence_boundary_is_preferred_over_a_hard_cut(tmp_path: Path):
    first = "Compile the thing deterministically."
    description = first + " " + "And then a great deal more prose besides. " * 12
    write(
        tmp_path / "skills" / "demo" / "SKILL.md",
        "---\nname: demo\n---\n\n# Demo\n\n## Purpose\n\n" + description + "\n",
    )
    model = ev.compile_readme_model(tmp_path, target("skills/demo", "skill"))
    assert model.purpose.endswith(".")
    assert not model.purpose.endswith("…")


def test_repository_module_names_are_conservative(tmp_path: Path):
    write(tmp_path / "ops" / "helper.py", "x = 1\n")
    names = ev.repository_module_names(tmp_path, ["ops"])
    assert "ops" in names
    assert "helper" in names
    assert "requests" not in names
