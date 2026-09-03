from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

PACK = Path(__file__).resolve().parents[1]
SCRIPTS = PACK / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rd = load_module("repo_docs", SCRIPTS / "repo_docs.py")
vp = load_module("validate_pointer_headings", SCRIPTS / "validate_pointer_headings.py")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init_git(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "tests@example.com"],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Tests"], check=True)


def commit_all(root: Path, message: str = "base") -> str:
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", message], check=True)
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def honest_pointer_stack(root: Path) -> None:
    write(
        root / "README.md",
        "# Repo\n\n## Purpose\n\nIndex.\n\n## Key Files\n\nCANONICAL_LAW.md AGENTS.md\n",
    )
    write(root / "CLAUDE.md", "# Load\n\n## Authority chain\n\nCANONICAL_LAW.md > AGENTS.md\n")
    write(root / "AGENTS.md", "# Agents\n")
    write(root / "CANONICAL_LAW.md", "# Law\n")


def test_policy_is_typed_and_rejects_duplicate_operating_ssot():
    policy = rd.load_policy()
    assert rd.validate_policy(policy) == []
    clone = yaml.safe_load(yaml.safe_dump(policy))
    clone["surfaces"]["claude"]["authority_class"] = "operating_ssot"
    errors = rd.validate_policy(clone)
    assert any("exactly one operating_ssot" in error for error in errors)


def test_adapter_precedence_explicit_then_repo_then_domain(tmp_path: Path):
    root = tmp_path / "my-repo"
    root.mkdir()
    write(root / ".claude/adapters/my-repo-update-agent-docs.md", "repo")
    write(root / ".claude/adapters/plasticos-update-agent-docs.md", "domain")
    write(root / "addons/__manifest__.py", "{}")
    write(root / "custom.md", "explicit")

    rel, state = rd.resolve_adapter(root, "custom.md")
    assert (rel, state) == ("custom.md", "EXPLICIT")
    rel, state = rd.resolve_adapter(root)
    assert (rel, state) == (".claude/adapters/my-repo-update-agent-docs.md", "DISCOVERED")
    (root / ".claude/adapters/my-repo-update-agent-docs.md").unlink()
    rel, state = rd.resolve_adapter(root)
    assert (rel, state) == (".claude/adapters/plasticos-update-agent-docs.md", "DISCOVERED")


def test_create_vs_refresh_contract():
    policy = rd.load_policy()
    assert rd.surface_action(policy["surfaces"]["claude"], exists=False) == "CREATE"
    assert rd.surface_action(policy["surfaces"]["claude"], exists=True) == "REFRESH"
    assert rd.surface_action(policy["surfaces"]["readme_root"], exists=False) == "SKIP"
    assert rd.surface_action(policy["surfaces"]["canonical_law"], exists=True) == "EXTERNAL"
    assert rd.surface_action(policy["surfaces"]["llms_txt"], exists=False, enabled=True) == "CREATE"


def test_managed_blocks_must_be_byte_stable():
    policy = rd.load_policy()
    before = (
        "# A\n<!-- BEGIN L9 FORMATTER OWNERSHIP -->\nowned\n"
        "<!-- END L9 FORMATTER OWNERSHIP -->\nTail\n"
    )
    after_ok = before.replace("Tail", "Tail changed")
    assert rd.managed_block_mutations(before, after_ok, policy) == []
    after_bad = before.replace("owned", "rewritten")
    assert rd.managed_block_mutations(before, after_bad, policy) == [
        "managed block changed: l9_formatter_ownership"
    ]


def test_root_containment_refuses_escape(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    assert rd.resolve_under_root(root, "llms.txt") == root / "llms.txt"
    assert rd.resolve_under_root(root, "../llms.txt") is None
    assert rd.resolve_under_root(root, "/tmp/llms.txt") is None


def test_missing_pointer_files_are_partial_not_pass(tmp_path: Path):
    result = vp.validate_root(tmp_path)
    assert result["status"] == "PARTIAL"
    assert {row["status"] for row in result["files"]} == {"Unknown"}


def test_llms_projection_is_small_absolute_and_not_authority(tmp_path: Path):
    root = tmp_path / "demo"
    root.mkdir()
    honest_pointer_stack(root)
    write(root / "ARCHITECTURE.md", "# Architecture\n")
    write(root / "INVARIANTS.md", "# Invariants\n")
    write(root / "API_REFERENCE.md", "# API\n")
    policy = rd.load_policy()
    rendered = rd.render_llms_txt(root, policy, "https://docs.example.com/")
    assert rendered.startswith("# demo\n")
    assert "## Documentation" in rendered
    assert "https://docs.example.com/README.md" in rendered
    assert "projection, not authority" in rendered
    assert rd.validate_llms_txt(rendered) == []
    target = rd.write_llms_txt(root, rendered)
    assert target == root / "llms.txt"


def test_impact_analysis_routes_only_affected_surfaces():
    policy = rd.load_policy()
    impact = rd.impact_analysis(
        policy,
        [
            ".github/workflows/ci.yml",
            "src/api/routes.py",
            "src/core/engine.py",
            "AGENTS.md",
        ],
    )
    impacted = set(impact["impacted_surfaces"])
    assert {"architecture", "invariants"}.issubset(impacted)
    assert "api_reference" in impacted
    assert "module_readmes" in impacted
    assert {"agents", "claude"}.issubset(impacted)
    assert "llms_txt" in impacted


def test_module_readme_capability_is_available_blocked_or_not_applicable(tmp_path: Path):
    policy = rd.load_policy()
    root = tmp_path / "repo"
    root.mkdir()
    assert rd.probe_module_readme_capability(root, policy)["status"] == "NotApplicable"
    write(root / "scripts/generate_subsystem_readmes.py", "")
    assert rd.probe_module_readme_capability(root, policy)["status"] == "BLOCKED"
    write(root / "config/subsystems/readme_config.yaml", "version: 1\n")
    write(root / "workflows/dags/readme_pipeline_dag.py", "")
    result = rd.probe_module_readme_capability(root, policy)
    assert result["status"] == "AVAILABLE"
    assert result["polyglot_extension_owner"] == "scripts/generate_subsystem_readmes.py"


def test_changed_since_and_managed_region_regression(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init_git(root)
    honest_pointer_stack(root)
    write(
        root / "ARCHITECTURE.md",
        "# Architecture\n<!-- BEGIN L9 FORMATTER OWNERSHIP -->\nowned\n"
        "<!-- END L9 FORMATTER OWNERSHIP -->\n",
    )
    base = commit_all(root)
    write(
        root / "ARCHITECTURE.md",
        "# Architecture\n<!-- BEGIN L9 FORMATTER OWNERSHIP -->\nchanged\n"
        "<!-- END L9 FORMATTER OWNERSHIP -->\n",
    )
    commit_all(root, "change")
    changed, error = rd.changed_files_since(root, base)
    assert error is None
    assert changed == ["ARCHITECTURE.md"]
    errors = rd.validate_managed_regions(root, base, changed or [], rd.load_policy())
    assert errors == ["ARCHITECTURE.md: managed block changed: l9_formatter_ownership"]


def test_receipt_contains_sha_surfaces_owners_changes_evidence_and_validators(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init_git(root)
    honest_pointer_stack(root)
    sha = commit_all(root)
    receipt = rd.audit_repository(root)
    assert receipt["target"]["sha"] == sha
    assert receipt["surfaces"]
    assert all("owner" in surface for surface in receipt["surfaces"])
    assert set(receipt["changes"]) == {"changed_files", "skipped_files", "unknown_files"}
    assert receipt["evidence_sources"]
    assert receipt["validators_executed"]
    assert rd.validate_receipt_shape(receipt) == []
    out = root / "repo-docs-receipt.json"
    out.write_text(json.dumps(receipt), encoding="utf-8")
    assert json.loads(out.read_text(encoding="utf-8"))["schema"] == "l9.repo-docs.receipt.v1"


def test_adapter_can_enable_llms_without_site_marker(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    adapter = root / ".claude/adapters/repo-update-agent-docs.md"
    write(
        adapter,
        "# adapter\n\n<!-- L9_DOCS\nllms_txt: enabled\n"
        "llms_base_url: https://docs.example.com\n-->\n",
    )
    directives = rd.adapter_directives(root, ".claude/adapters/repo-update-agent-docs.md")
    enabled, reason = rd.llms_enabled(root, rd.load_policy(), directives)
    base, source = rd.llms_base_url(directives, None)
    assert (enabled, reason) == (True, "adapter")
    assert (base, source) == ("https://docs.example.com/", "adapter")
