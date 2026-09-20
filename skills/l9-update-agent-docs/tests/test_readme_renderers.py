"""Rendering quality: a README shrinks as its evidence thins.

The old template always emitted Purpose, Components, Functions, Exports
and Dependencies, filling each with `_No ..._` when it had nothing. These
tests pin the opposite contract: a section with no positive content is
not rendered at all.
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
rr = load("readme_renderers", SCRIPTS / "readme_renderers.py")
rq = load("readme_quality", SCRIPTS / "readme_quality.py")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def target(path: str, kind: str = "module", **kwargs) -> rm.ReadmeTarget:
    return rm.ReadmeTarget(path=path, kind=kind, title=path.rsplit("/", 1)[-1], **kwargs)


def render(tmp_path: Path, path: str, kind: str = "module", **kwargs) -> str:
    model = ev.compile_readme_model(tmp_path, target(path, kind, **kwargs))
    return rr.render_readme(model)


# --- T-R-001: empty sections disappear ---


def test_empty_sections_are_not_rendered(tmp_path: Path):
    write(tmp_path / "bare" / "mod.py", "_private = 1\n")
    text = render(tmp_path, "bare")
    for absent in (
        "_No public classes in this path._",
        "_No public module-level functions._",
        "_No `__all__` exports._",
        "_No imports parsed._",
        "## Purpose",
        "## Dependencies",
    ):
        assert absent not in text, absent
    assert "**Path:** `bare`" in text
    assert rr.marker_for("module") in text


def test_readme_shrinks_as_evidence_thins(tmp_path: Path):
    write(tmp_path / "rich" / "mod.py", '"""Rich."""\n\nimport yaml\n\nclass Thing:\n    pass\n')
    write(tmp_path / "bare" / "mod.py", "_hidden = 1\n")
    assert len(render(tmp_path, "rich")) > len(render(tmp_path, "bare"))


def test_no_generated_readme_carries_a_forbidden_filler_phrase(tmp_path: Path):
    write(tmp_path / "bare" / "mod.py", "_private = 1\n")
    write(tmp_path / "corpus" / "a.md", "# A\n")
    write(tmp_path / "corpus" / "b.md", "# B\n")
    write(tmp_path / "idx" / "one" / "a.py", "a = 1\n")
    write(tmp_path / "idx" / "two" / "b.py", "b = 1\n")
    rendered = [
        render(tmp_path, "bare"),
        render(tmp_path, "corpus", "corpus"),
        render(tmp_path, "idx", "index"),
    ]
    for text in rendered:
        lowered = text.lower()
        for phrase in rq.FORBIDDEN_PURPOSE_PHRASES:
            assert phrase not in lowered, phrase


# --- T-R-002: modules are grouped, never flattened ---


def test_subsystem_groups_symbols_by_module(tmp_path: Path):
    write(tmp_path / "pair" / "a.py", "def main():\n    return 1\n")
    write(tmp_path / "pair" / "b.py", "def main():\n    return 2\n")
    text = render(tmp_path, "pair", "subsystem")
    assert "### `a.py`" in text
    assert "### `b.py`" in text
    assert text.index("### `a.py`") < text.index("### `b.py`")
    assert "## Public interface" not in text


# --- T-R-003: dependency output is curated ---


def test_standard_library_is_not_rendered(tmp_path: Path):
    write(
        tmp_path / "dep" / "mod.py",
        "import json\nimport pathlib\nimport yaml\nfrom doc_policy import thing\n",
    )
    model = ev.compile_readme_model(
        tmp_path, target("dep"), internal_names=frozenset({"doc_policy"})
    )
    text = rr.render_readme(model)
    assert "**Internal:** `doc_policy`" in text
    assert "**External:** `yaml`" in text
    assert "`json`" not in text
    assert "`pathlib`" not in text


def test_dependency_section_absent_when_only_stdlib_is_imported(tmp_path: Path):
    write(tmp_path / "dep" / "mod.py", "import json\nimport pathlib\n")
    assert "## Dependencies" not in render(tmp_path, "dep")


# --- T-R-004: structural identity cannot be overridden ---


def test_rendered_path_always_equals_the_target_path(tmp_path: Path):
    write(tmp_path / "real" / "mod.py", "x = 1\n")
    spoofed = rm.ReadmeTarget(path="real", kind="module", title="Something Else")
    text = rr.render_readme(ev.compile_readme_model(tmp_path, spoofed))
    assert "**Path:** `real`" in text
    assert "# Something Else" in text


# --- T-R-005: a skill README points at its authority ---


def test_skill_readme_links_its_contract(tmp_path: Path):
    write(
        tmp_path / "skills" / "demo" / "SKILL.md",
        "---\nname: demo\ndescription: do the thing\n---\n\n# Demo\n",
    )
    write(tmp_path / "skills" / "demo" / "scripts" / "a.py", "a = 1\n")
    text = render(tmp_path, "skills/demo", "skill")
    assert "SKILL.md" in text
    assert "## Authority" in text
    assert "do the thing" in text
    assert "[`scripts/`](scripts/)" in text
    assert "AST" not in text


# --- marker ---


def test_marker_records_the_target_kind(tmp_path: Path):
    write(tmp_path / "corpus" / "a.md", "# A\n")
    write(tmp_path / "corpus" / "b.md", "# B\n")
    text = render(tmp_path, "corpus", "corpus")
    assert rr.marker_kind(text) == "corpus"
    assert rr.owns_marker(text)


def test_legacy_markers_are_not_claimed_by_the_current_owner_check():
    assert not rr.owns_marker("<!-- l9-module-readme: generated-from-ast -->")
    assert not rr.owns_marker("# Handwritten\n")


# --- quality validator ---


def test_validator_flags_a_purpose_leak(tmp_path: Path):
    write(tmp_path / "pair" / "a.py", '"""Only a."""\n')
    write(tmp_path / "pair" / "b.py", '"""Only b."""\n')
    model = ev.compile_readme_model(tmp_path, target("pair", "subsystem"))
    leaked = rm.ReadmeModel(
        target=model.target,
        purpose="Only a.",
        modules=model.modules,
    )
    findings = rq.validate_readme_model(tmp_path, leaked, rr.render_readme(leaked))
    assert any(finding.rule_id == "readme.multi_module.purpose_leak" for finding in findings)


def test_validator_flags_a_purpose_with_no_evidence_reference(tmp_path: Path):
    """INV-RD-004 mechanically: a claim must name where it came from."""
    model = rm.ReadmeModel(target=target("x"), purpose="Something nobody can source.")
    findings = rq.validate_readme_model(tmp_path, model, rr.render_readme(model))
    assert any(finding.rule_id == "readme.purpose.unsourced" for finding in findings)


def test_a_compiled_purpose_always_carries_its_evidence(tmp_path: Path):
    write(tmp_path / "solo" / "only.py", '"""Solo does one thing."""\n')
    model = ev.compile_readme_model(tmp_path, target("solo"))
    assert model.purpose == "Solo does one thing."
    assert any(ref.kind == "module_docstring" for ref in model.evidence)
    findings = rq.validate_readme_model(
        tmp_path, model, rr.render_readme(model), authorized={"solo"}
    )
    assert not any(finding.rule_id == "readme.purpose.unsourced" for finding in findings)


def test_validator_flags_generic_purpose(tmp_path: Path):
    model = rm.ReadmeModel(
        target=target("x"),
        purpose="AST-extracted module documentation.",
    )
    findings = rq.validate_readme_model(tmp_path, model, rr.render_readme(model))
    assert any(finding.rule_id == "readme.generic_purpose" for finding in findings)


def test_validator_flags_an_unauthorized_target(tmp_path: Path):
    model = rm.ReadmeModel(target=target("ghost"))
    findings = rq.validate_readme_model(
        tmp_path, model, rr.render_readme(model), authorized={"real"}
    )
    assert any(finding.rule_id == "readme.target.unauthorized" for finding in findings)


def test_validator_flags_a_broken_relative_reference(tmp_path: Path):
    (tmp_path / "idx").mkdir()
    model = rm.ReadmeModel(target=target("idx", "index"), children=("missing",))
    findings = rq.validate_readme_model(tmp_path, model, rr.render_readme(model))
    assert any(finding.rule_id == "readme.reference.missing" for finding in findings)


def test_validator_accepts_a_clean_compiled_model(tmp_path: Path):
    write(tmp_path / "solo" / "only.py", '"""Solo."""\n\nimport yaml\n')
    model = ev.compile_readme_model(tmp_path, target("solo"))
    findings = rq.validate_readme_model(
        tmp_path, model, rr.render_readme(model), authorized={"solo"}
    )
    assert [finding for finding in findings if finding.severity == "ERROR"] == []


def test_retirement_refuses_an_unowned_file():
    assert rq.retirement_findings("a/README.md", "# Handwritten\n")
    assert not rq.retirement_findings("a/README.md", rr.marker_for("module"))
