"""Consumer-surface conformance for the root-document compiler upgrades."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
SCRIPTS = PACK / "scripts"
sys.path.insert(0, str(SCRIPTS))

from consumer_snapshot import build_consumer_snapshot  # noqa: E402
from doc_llm import render_llm_txt, validate_llm_txt  # noqa: E402
from doc_policy import load_policy  # noqa: E402
from doc_surface_analysis import (  # noqa: E402
    ANALYZERS,
    _snapshot_required_analyzer,
    assess_surface_obligations,
)
from repo_docs import audit_repository, revision_identity  # noqa: E402
from root_contracts import (  # noqa: E402
    architecture_delta,
    assess_architecture_index,
    assess_root_agent_contract,
)
from surface_analyzers.pyproject import analyze as analyze_pyproject  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    for key, value in (("user.email", "tests@example.com"), ("user.name", "Tests")):
        subprocess.run(["git", "-C", str(root), "config", key, value], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "remote",
            "add",
            "origin",
            "https://github.com/example/consumer.git",
        ],
        check=True,
    )
    write(root / "CANONICAL_LAW.md", "# Law\n")
    write(
        root / "README.md",
        "# Consumer\n\n## Purpose\n\nConsumer.\n\n## Key Files\n\nCANONICAL_LAW.md AGENTS.md\n",
    )
    write(root / "AGENTS.md", "# Agents\n")
    write(root / "CLAUDE.md", "# Load\n\n## Authority chain\n\nCANONICAL_LAW.md > AGENTS.md\n")
    write(root / "ARCHITECTURE.md", "# Architecture\n")
    write(root / "INVARIANTS.md", "# Invariants\n")


def commit(root: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", message], check=True)
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def snapshot(root: Path, changed: list[str] | None = None) -> dict:
    revision = revision_identity(
        root,
        base_ref=None,
        source_head_sha="source",
        tested_revision_sha="tested",
        dirty_scope=False,
    )
    return build_consumer_snapshot(root, load_policy(), revision, changed_files=changed or [])


def test_snapshot_is_stable_when_only_audit_scope_changes(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    assert snapshot(root, ["README.md"])["digest"] == snapshot(root, ["AGENTS.md"])["digest"]


def test_llm_manifest_carries_snapshot_and_document_digests(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    policy = load_policy()
    current = snapshot(root)
    rendered = render_llm_txt(root, policy, None, current)
    assert "L9_DOC_MANIFEST" in rendered
    assert current["digest"] in rendered
    assert validate_llm_txt(rendered, root=root, snapshot=current) == []
    stale = json.loads(json.dumps(current))
    stale["documents"]["AGENTS.md"]["digest"] = "0" * 64
    assert any("stale" in item for item in validate_llm_txt(rendered, root=root, snapshot=stale))


def test_api_projection_mutation_creates_llm_obligation(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    base = commit(root, "base")
    audit_repository(root, changed_since=base)
    projections = commit(root, "projections")
    write(
        root / "openapi.yaml",
        "openapi: 3.1.0\npaths:\n  /health:\n    get:\n      responses:\n"
        "        '200': {description: healthy}\n",
    )
    commit(root, "api")
    receipt = audit_repository(root, changed_since=projections)
    surfaces = {row["surface"] for row in receipt["obligations"]}
    assert "api_reference" in surfaces
    assert "llm_txt" in surfaces
    assert "llm.txt" in receipt["changes"]["run_mutations"]
    assert "filetree.md" in receipt["consumer_snapshot"]["documents"]


def test_ci_locked_uv_workflow_requires_a_lockfile(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    write(
        root / "pyproject.toml",
        "[project]\nrequires-python = '>=3.12'\n\n[tool.uv]\npackage = false\n",
    )
    write(
        root / ".github/workflows/test.yml",
        "name: test\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n"
        "      - run: uv sync --locked\n",
    )
    ids = {row["rule_id"] for row in analyze_pyproject(root, root / "pyproject.toml")["findings"]}
    assert "python.uv.lock_presence" in ids


def test_project_script_and_testpath_must_resolve(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    write(
        root / "pyproject.toml",
        "[project]\nrequires-python = '>=3.12'\n\n[project.scripts]\n"
        "consumer = 'missing.cli:main'\n\n"
        "[tool.pytest.ini_options]\ntestpaths = ['missing-tests']\n",
    )
    ids = {row["rule_id"] for row in analyze_pyproject(root, root / "pyproject.toml")["findings"]}
    assert {"python.project_script.module_resolution", "python.pytest.testpath_missing"} <= ids


def test_root_agent_contract_rejects_missing_links_and_commands(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    (root / "CANONICAL_LAW.md").unlink()
    write(
        root / "AGENTS.md",
        "# Agents\n\n[missing](CANONICAL_LAW.md)\n\n<!-- L9_AGENT_CONTRACT\n"
        "commands: [make missing]\nfiles: [docs/nope.md]\n"
        "environment: [bad_name]\nauthorities: [NOPE.md]\n-->\n",
    )
    findings = assess_root_agent_contract(root, root / "AGENTS.md", snapshot(root))["findings"]
    assert {
        "root.reference.missing",
        "agents.contract.command_missing",
        "agents.contract.file_missing",
        "agents.contract.environment_name",
        "agents.contract.authority_missing",
    } <= {row["rule_id"] for row in findings}


def test_architecture_contract_checks_components_and_emits_delta(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    write(
        root / "ARCHITECTURE.md",
        "# Architecture\n\n<!-- L9_ARCHITECTURE_COMPONENTS\n"
        "components: [missing/service.py]\n-->\n",
    )
    write(root / "pyproject.toml", "[project]\nname = 'consumer'\nrequires-python = '>=3.12'\n")
    current = snapshot(root, ["pyproject.toml"])
    findings = assess_architecture_index(root, root / "ARCHITECTURE.md", current)["findings"]
    assert "architecture.component_missing" in {row["rule_id"] for row in findings}
    assert architecture_delta(current) == [
        {
            "action": "unknown",
            "kind": "unclassified_contract_change",
            "path": "pyproject.toml",
            "evidence_id": "pyproject.toml",
        }
    ]


def test_project_script_snapshot_records_a_numeric_source_line(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    write(
        root / "pyproject.toml",
        "[project]\nname = 'consumer'\nrequires-python = '>=3.12'\n\n"
        "[project.scripts]\nconsumer = 'consumer.cli:main'\n",
    )
    write(root / "consumer" / "cli.py", "def main():\n    return 0\n")
    fact = next(item for item in snapshot(root)["facts"] if item["kind"] == "project_script")
    assert fact["line"] == 6
    assert fact["resolution"] == "consumer/cli.py"


def test_project_script_snapshot_records_a_quoted_key_source_line(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    write(
        root / "pyproject.toml",
        "[project]\nname = 'consumer'\nrequires-python = '>=3.12'\n\n"
        "[project.scripts]\n\"consumer-cli\" = 'consumer.cli:main'\n",
    )
    write(root / "consumer" / "cli.py", "def main():\n    return 0\n")
    fact = next(item for item in snapshot(root)["facts"] if item["kind"] == "project_script")
    assert fact["line"] == 6
    assert fact["resolution"] == "consumer/cli.py"


def test_root_contract_registry_uses_explicit_snapshot_sentinel(tmp_path: Path) -> None:
    assert ANALYZERS["architecture-index-contract-v1"] is _snapshot_required_analyzer
    assert ANALYZERS["root-agent-contract-v1"] is _snapshot_required_analyzer
    result = _snapshot_required_analyzer(tmp_path, tmp_path / "AGENTS.md")
    assert result["status"] == "BLOCKED"
    assert "consumer snapshot evidence" in result["blockers"][0]


def test_root_contract_rejects_escaped_reference_before_authority_filter(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    write(root / "README.md", "# Consumer\n\n[escape](../outside.md)\n")
    findings = assess_root_agent_contract(root, root / "README.md", snapshot(root))["findings"]
    assert "root.reference.escaped_root" in {row["rule_id"] for row in findings}


def test_architecture_component_must_remain_under_repository_root(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    outside = tmp_path / "outside.py"
    outside.write_text("# external\n", encoding="utf-8")
    write(
        root / "ARCHITECTURE.md",
        "# Architecture\n\n<!-- L9_ARCHITECTURE_COMPONENTS\ncomponents: [../outside.py]\n-->\n",
    )
    findings = assess_architecture_index(root, root / "ARCHITECTURE.md", snapshot(root))["findings"]
    assert "architecture.component_missing" in {row["rule_id"] for row in findings}


def test_snapshot_aware_root_assessment_blocks_when_evidence_is_absent(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    policy = load_policy()
    obligation = {
        "surface": "architecture",
        "target": {"path": "ARCHITECTURE.md", "present": True},
        "evidence": [],
        "blockers": [],
        "required_action": {},
        "lifecycle": {},
        "validation": {"required": [], "results": []},
    }
    result = assess_surface_obligations(root, policy, [obligation], snapshot=None)[0]
    assert result["assessment"]["status"] == "BLOCKED"
    assert result["lifecycle"]["status"] == "BLOCKED"
