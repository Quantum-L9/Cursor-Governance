"""Every extracted field has a downstream consumer.

The ledger is the gate for the signal-utilization law. A field counts as
utilized only when a renderer, a root-doc compiler, the llm.txt compiler,
or the receipt writer reads it. Validator-only reads do not count.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import sys
from dataclasses import fields
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
SCRIPTS = PACK / "scripts"
sys.path.insert(0, str(SCRIPTS))

CONSUMERS = (
    SCRIPTS / "readme_renderers.py",
    SCRIPTS / "doc_root.py",
    SCRIPTS / "doc_llm.py",
    SCRIPTS / "generate_module_readmes.py",
    SCRIPTS / "repo_docs.py",
)
MODEL_TYPES = (
    "ModuleDoc",
    "InterfaceDoc",
    "SourceFact",
    "DependencyDoc",
    "ReadmeModel",
    "ReadmeTarget",
    "EvidenceRef",
    "ExtractionIssue",
    "RelationshipDoc",
)
UNWIRED: frozenset[str] = frozenset()


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


def _consumer_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in CONSUMERS)


def _consumed(field_name: str, text: str) -> bool:
    attr = re.compile(rf"\.{re.escape(field_name)}\b")
    key = re.compile(rf"\[\s*['\"]{re.escape(field_name)}['\"]\s*\]")
    return bool(attr.search(text) or key.search(text))


def _analyzer_keys() -> set[str]:
    keys: set[str] = set()
    for path in (SCRIPTS / "surface_analyzers").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or node.name not in {
                "analyze",
                "_assessment",
            }:
                continue
            for child in ast.walk(node):
                if not isinstance(child, ast.Return) or not isinstance(child.value, ast.Dict):
                    continue
                for key in child.value.keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        keys.add(key.value)
    return keys


def test_every_extracted_field_has_a_consumer():
    model = load("readme_model", SCRIPTS / "readme_model.py")
    evidence = load("readme_evidence", SCRIPTS / "readme_evidence.py")
    text = _consumer_text()
    missing: list[str] = []
    for type_name in MODEL_TYPES:
        for field in fields(getattr(model, type_name)):
            token = f"{type_name}.{field.name}"
            if token in UNWIRED:
                continue
            if not _consumed(field.name, text):
                missing.append(token)
    for slot in evidence.SkillContract.__slots__:
        token = f"SkillContract.{slot}"
        if token in UNWIRED:
            continue
        if not _consumed(slot, text):
            missing.append(token)
    for key in sorted(_analyzer_keys()):
        token = f"analyzer.{key}"
        if token in UNWIRED:
            continue
        if not _consumed(key, text):
            missing.append(token)
    assert missing == []
    assert UNWIRED == frozenset()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_typescript_dependencies_and_signature(tmp_path: Path):
    ev = load("readme_evidence", SCRIPTS / "readme_evidence.py")
    rm = load("readme_model", SCRIPTS / "readme_model.py")
    rr = load("readme_renderers", SCRIPTS / "readme_renderers.py")
    write(
        tmp_path / "src" / "index.ts",
        'import OpenAI from "openai/resources";\n'
        'import { z } from "zod";\n'
        'import { format } from "./format";\n'
        "export function rank(value: string, limit?: number) { return value }\n",
    )
    write(
        tmp_path / "src" / "format.ts",
        "export function format(value: string) { return value }\n",
    )
    model = ev.compile_readme_model(
        tmp_path, rm.ReadmeTarget(path="src", kind="module", title="src")
    )
    rendered = rr.render_readme(model)
    assert "openai" in model.dependencies.external
    assert "zod" in model.dependencies.external
    assert "src/format" in model.dependencies.internal
    assert "`rank(value: string, limit?: number)`" in rendered
    assert "**External:**" in rendered
    assert "**Internal:**" in rendered


def test_skill_readme_renders_version_and_authority_links(tmp_path: Path):
    ev = load("readme_evidence", SCRIPTS / "readme_evidence.py")
    rm = load("readme_model", SCRIPTS / "readme_model.py")
    rr = load("readme_renderers", SCRIPTS / "readme_renderers.py")
    write(
        tmp_path / "skills" / "demo" / "SKILL.md",
        "---\nmetadata:\n  version: 4.4.0\n---\n# Demo\n\n"
        "Compile the docs. use when the user asks.\n\n"
        "## Ownership boundaries\n\n- owns the receipt\n",
    )
    model = ev.compile_readme_model(
        tmp_path, rm.ReadmeTarget(path="skills/demo", kind="skill", title="demo")
    )
    rendered = rr.render_readme(model)
    assert model.version == "4.4.0"
    assert "**Version:** `4.4.0`" in rendered
    assert "[`SKILL.md`](SKILL.md)" in rendered


def test_agents_lists_command_names_and_compiled_purposes(tmp_path: Path):
    doc_root = load("doc_root", SCRIPTS / "doc_root.py")
    rm = load("readme_model", SCRIPTS / "readme_model.py")
    write(tmp_path / "package.json", '{"scripts":{"build":"tsc","secret":"TOKEN=hidden"}}\n')
    write(
        tmp_path / "pyproject.toml",
        '[project]\nname="demo"\n\n[project.scripts]\ndemo = "demo:main"\n',
    )
    policy = {"external_bindings": {"org_profile": {"url": "https://example.test"}}}
    model = rm.ReadmeModel(
        target=rm.ReadmeTarget(path="src", kind="module", title="src"),
        purpose="Rank incoming requests.",
    )
    rendered = doc_root.render_agents(tmp_path, policy, (model,))
    assert "`build`" in rendered
    assert "`demo`" in rendered
    assert "TOKEN" not in rendered
    assert "tsc" not in rendered
    assert "[`src/README.md`](src/README.md): Rank incoming requests." in rendered


def test_invariants_lists_workflow_name_and_jobs(tmp_path: Path):
    doc_root = load("doc_root", SCRIPTS / "doc_root.py")
    write(
        tmp_path / ".github" / "workflows" / "ci.yml",
        "name: CI\njobs:\n  lint:\n    runs-on: ubuntu-latest\n"
        "  test:\n    runs-on: ubuntu-latest\n",
    )
    rendered = doc_root.render_invariants(tmp_path, {"external_bindings": {}})
    assert "workflow `CI`" in rendered
    assert "`lint`" in rendered
    assert "`test`" in rendered


def test_llm_manifest_lists_compiled_readmes():
    doc_llm = load("doc_llm", SCRIPTS / "doc_llm.py")
    rm = load("readme_model", SCRIPTS / "readme_model.py")
    model = rm.ReadmeModel(
        target=rm.ReadmeTarget(path="src", kind="module", title="src"),
        purpose="Rank incoming requests.",
    )
    snapshot = {
        "publication_markers": [],
        "digest": "abc",
        "documents": {"src/README.md": {"digest": "deadbeef"}},
    }
    entries = doc_llm._readme_manifest_entries(snapshot, (model,), None)
    assert entries == [
        {
            "id": "readme:src:README.md",
            "path": "src/README.md",
            "href": "src/README.md",
            "role": "compiled module documentation",
            "owner": "l9-update-agent-docs",
            "authority_class": "projection",
            "sha256": "deadbeef",
            "availability": "repository_local",
            "purpose": "Rank incoming requests.",
        }
    ]


def test_receipt_records_evidence_and_warnings():
    gm = load("generate_module_readmes", SCRIPTS / "generate_module_readmes.py")
    rm = load("readme_model", SCRIPTS / "readme_model.py")
    model = rm.ReadmeModel(
        target=rm.ReadmeTarget(path="src", kind="module", title="src"),
        evidence=(rm.EvidenceRef(source="src/index.ts", kind="source_facts", detail="1 file"),),
    )
    finding = rm.QualityFinding(
        rule_id="readme.empty_section",
        severity="WARN",
        message="a rendered section has no positive content",
        source="src/README.md",
    )
    row = gm._quality_entry(model, (finding,))
    assert row["evidence"] == [
        {"source": "src/index.ts", "kind": "source_facts", "detail": "1 file"}
    ]
    assert row["warnings"] == [
        {
            "rule_id": "readme.empty_section",
            "message": "a rendered section has no positive content",
        }
    ]
