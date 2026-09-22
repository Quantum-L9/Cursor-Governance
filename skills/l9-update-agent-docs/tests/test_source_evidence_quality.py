"""Regression coverage for upstream source evidence and README quality gates."""

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
df = load("doc_filetree", SCRIPTS / "doc_filetree.py")
sf = load("source_facts", SCRIPTS / "source_facts.py")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def target(path: str, kind: str = "module") -> rm.ReadmeTarget:
    return rm.ReadmeTarget(path=path, kind=kind, title=path.rsplit("/", 1)[-1])


def test_polyglot_source_facts_render_relationships_and_coverage(tmp_path: Path):
    path = tmp_path / "service"
    write(path / "__init__.py", '"""Repository-native service package purpose."""\n')
    write(path / "api.ts", "import client from './client';\nexport function serve() {}\n")
    write(
        path / "deploy.sh",
        "#!/usr/bin/env bash\nsource ./shared.sh\nDEPLOY_ENV=${DEPLOY_ENV}\ndeploy() {}\n",
    )
    write(path / "main.tf", 'variable "region" {}\nmodule "network" { source = "./network" }\n')
    write(path / "config.xml", "<configuration><endpoint /></configuration>\n")
    write(path / "Dockerfile", 'FROM python:3.12\nCMD ["python", "-m", "service"]\n')

    model = ev.compile_readme_model(tmp_path, target("service", "subsystem"))
    rendered = rr.render_readme(model)

    assert {fact.language for fact in model.source_facts} == {
        "python",
        "typescript",
        "shell",
        "terraform",
        "xml",
        "dockerfile",
    }
    assert model.completeness == "complete"
    assert model.purpose == "Repository-native service package purpose."
    assert {relationship.kind for relationship in model.relationships} >= {
        "base_image",
        "configures",
        "imports",
        "uses_module",
    }
    assert "## Integrates with" in rendered
    assert "## Source coverage" in rendered
    assert "**Status:** complete; **Files:** 6/6 extracted" in rendered
    assert not [
        finding
        for finding in rq.validate_readme_model(tmp_path, model, rendered)
        if finding.severity == "ERROR"
    ]


def test_parse_failure_stays_visible_as_partial_evidence(tmp_path: Path):
    write(tmp_path / "broken" / "bad.py", "def missing(:\n")
    model = ev.compile_readme_model(tmp_path, target("broken"))
    rendered = rr.render_readme(model)

    assert model.completeness == "partial"
    assert model.extraction_issues
    assert "**Status:** partial; **Files:** 0/1 extracted" in rendered
    findings = rq.validate_readme_model(tmp_path, model, rendered)
    assert any(finding.rule_id == "readme.source.extraction_issue" for finding in findings)


def test_long_interfaces_and_file_indexes_are_complete_and_linked(tmp_path: Path):
    functions = "\n".join(f"def function_{index}():\n    return {index}\n" for index in range(10))
    write(tmp_path / "api" / "service.py", functions)
    model = ev.compile_readme_model(tmp_path, target("api"))
    rendered = rr.render_readme(model)
    assert "[Complete interface index](#complete-interface-index)" in rendered
    assert "## Complete interface index" in rendered
    assert "`def function_7()`" in rendered
    assert "`def function_8()`" not in rendered
    assert "_+2 public symbol(s) omitted from this index._" in rendered

    for index in range(41):
        write(tmp_path / "corpus" / f"item-{index}.md", f"# Item {index}\n")
    corpus = ev.compile_readme_model(tmp_path, target("corpus", "corpus"))
    corpus_rendered = rr.render_readme(corpus)
    assert "[Complete file index](#complete-file-index)" in corpus_rendered
    assert "## Complete file index" in corpus_rendered
    assert "`item-40.md`" in corpus_rendered


def test_xml_dtds_are_rejected_as_visible_extraction_issues(tmp_path: Path):
    write(
        tmp_path / "xml" / "config.xml",
        "<!DOCTYPE config [<!ENTITY value 'unsafe'>]>\n<config>&value;</config>\n",
    )
    model = ev.compile_readme_model(tmp_path, target("xml"))
    assert model.completeness == "partial"
    assert any("DTD and entity declarations" in issue.detail for issue in model.extraction_issues)


def test_source_evidence_registry_is_cached_per_process():
    sf.load_source_evidence_registry.cache_clear()
    first = sf.load_source_evidence_registry()
    second = sf.load_source_evidence_registry()
    assert first is second
    assert sf.load_source_evidence_registry.cache_info().hits == 1


def test_manifest_purpose_and_link_errors_are_evidence_backed(tmp_path: Path):
    write(tmp_path / "package" / "main.js", "export const ready = true;\n")
    write(
        tmp_path / "package" / "package.json",
        '{"name": "package", "description": "The target-local manifest describes this package."}\n',
    )
    model = ev.compile_readme_model(tmp_path, target("package"))
    assert model.purpose == "The target-local manifest describes this package."
    assert any(ref.kind == "manifest_description" for ref in model.evidence)

    rendered = (
        rr.render_readme(model) + "\n## Extra\n\n[bad](../../escape.md)\n[missing](#absent)\n"
    )
    findings = rq.validate_readme_model(tmp_path, model, rendered)
    assert {finding.rule_id for finding in findings} >= {
        "readme.reference.escaped_root",
        "readme.reference.anchor_missing",
    }


def test_filetree_classification_uses_the_same_polyglot_registry(tmp_path: Path):
    write(tmp_path / "frontend" / "app.tsx", "export const App = () => null;\n")
    inventory = df.walk_inventory(tmp_path)
    row = next(item for item in inventory.modules if item.path == "frontend")
    assert row.kind == "module"
    assert row.sources == 1
