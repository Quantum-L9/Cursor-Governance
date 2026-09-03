from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

PACK = Path(__file__).resolve().parents[1]
SCRIPTS = PACK / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


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
    subprocess.run(["git", "-C", str(root), "config", "user.email", "tests@example.com"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Tests"], check=True)


def commit_all(root: Path, message: str = "base") -> str:
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", message], check=True)
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def honest_stack(root: Path, *, invariants: bool = True, architecture: bool = False) -> None:
    write(root / "README.md", "# Repo\n\n## Purpose\n\nIndex.\n\n## Key Files\n\nCANONICAL_LAW.md AGENTS.md\n")
    write(root / "CLAUDE.md", "# Load\n\n## Authority chain\n\nCANONICAL_LAW.md > AGENTS.md\n")
    write(root / "AGENTS.md", "# Agents\n")
    write(root / "CANONICAL_LAW.md", "# Law\n")
    if invariants:
        write(root / "INVARIANTS.md", "# Invariants\n")
    if architecture:
        write(root / "ARCHITECTURE.md", "# Architecture\n")


def evidence(eid: str = "e1", epistemic: str = "CONFIRMED") -> dict:
    return {
        "id": eid,
        "epistemic": epistemic,
        "source": "repo",
        "locator": {"kind": "path_lines", "value": ".github/workflows/ci.yml:1-10"},
        "claim": "workflow enforces durable behavior",
        "secret_redacted": False,
    }


def concept(cid: str, surface: str, *, eid: str = "e1", disposition: str = "PORT", comparison: str = "DONOR_STRONGER") -> dict:
    return {
        "id": cid,
        "name": f"{surface} semantic",
        "problem": "durable behavior must remain documented",
        "semantic_contract": f"Keep {surface} aligned with executable semantics.",
        "disposition": disposition,
        "beneficiary_destination": f"docs:{surface}",
        "evidence_ids": [eid],
        "risks": ["stale docs"],
        "acceptance_tests": [{"given": "change", "when": "docs refresh", "then": "aligned", "must_not": "invent"}],
        "beneficiary_fit": {
            "comparison": comparison,
            "existing_owner": surface,
            "merge_decision": "preserve stronger semantics",
            "compatibility_risk": "low",
        },
        "nugget": True,
        "rank_score": 55,
    }


def harvest(*concepts: dict, evidence_rows: list[dict] | None = None, status: str = "PASS") -> dict:
    return {
        "schema_version": "1.1.0",
        "status": status,
        "evidence": evidence_rows or [],
        "concepts": list(concepts),
    }


def test_policy_schema_is_runtime_authority_and_semantic_ssot_is_unique():
    policy = rd.load_policy()
    assert rd.validate_policy(policy) == []
    broken = yaml.safe_load(yaml.safe_dump(policy))
    del broken["surfaces"]["agents"]["requirement"]
    assert any("requirement" in error for error in rd.validate_policy(broken))
    duplicate = yaml.safe_load(yaml.safe_dump(policy))
    duplicate["surfaces"]["claude"]["authority_class"] = "operating_ssot"
    assert any("exactly one operating_ssot" in error for error in rd.validate_policy(duplicate))


def test_root_containment_and_surface_actions(tmp_path: Path):
    policy = rd.load_policy()
    assert rd.resolve_under_root(tmp_path, "llms.txt") == tmp_path / "llms.txt"
    assert rd.resolve_under_root(tmp_path, "../llms.txt") is None
    assert rd.surface_action(policy["surfaces"]["claude"], exists=False) == "CREATE"
    assert rd.surface_action(policy["surfaces"]["readme_root"], exists=False) == "SKIP"
    assert rd.surface_action(policy["surfaces"]["llms_txt"], exists=False, enabled=True) == "CREATE"


def test_missing_pointer_files_are_partial_not_pass(tmp_path: Path):
    result = vp.validate_root(tmp_path)
    assert result["status"] == "PARTIAL"
    assert {row["status"] for row in result["files"]} == {"Unknown"}


def test_managed_region_dirty_worktree_is_compared_to_head(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir(); init_git(root); honest_stack(root)
    write(root / "README.md", "# Repo\n\n## Purpose\n\nIndex.\n\n## Key Files\n\nCANONICAL_LAW.md AGENTS.md\n<!-- BEGIN L9 FORMATTER OWNERSHIP -->\nowned\n<!-- END L9 FORMATTER OWNERSHIP -->\n")
    commit_all(root)
    write(root / "README.md", (root / "README.md").read_text().replace("owned", "changed"))
    changed, base, error = rd.automatic_changed_scope(root)
    assert error is None and base == "HEAD" and changed == ["README.md"]
    status, findings = rd.validate_managed_regions(root, base, changed, rd.load_policy())
    assert status == "FAIL"
    assert "managed block changed" in findings[0]


def test_impact_is_machine_routed_and_harvest_is_selective(tmp_path: Path):
    policy = rd.load_policy()
    root = tmp_path / "repo"; root.mkdir(); honest_stack(root)
    impact = rd.impact_analysis(policy, [".github/workflows/ci.yml", "src/api/routes.py", "src/core.py"])
    assert {"architecture", "invariants", "api_reference", "module_readmes"}.issubset(set(impact["impacted_surfaces"]))
    assert rd.semantic_harvest_required(policy, impact, root) == ["invariants"]
    docs_only = rd.impact_analysis(policy, ["README.md"])
    assert rd.semantic_harvest_required(policy, docs_only, root) == []


def test_missing_harvest_emits_exact_targeted_request(tmp_path: Path):
    root = tmp_path / "repo"; root.mkdir(); init_git(root); honest_stack(root)
    base = commit_all(root)
    write(root / ".github/workflows/ci.yml", "name: CI\n"); commit_all(root, "workflow")
    receipt = rd.audit_repository(root, changed_since=base)
    semantic = receipt["semantic_harvest"]
    assert semantic["status"] == "PARTIAL"
    assert semantic["required_surfaces"] == ["invariants"]
    assert semantic["request"]["harvest_target"] == "repo-docs:invariants"
    assert receipt["freshness"]["stale_surfaces"] == ["invariants"]
    assert rd.exit_code_for_receipt(receipt) == 3


def test_confirmed_qualified_harvest_closes_semantic_obligation(tmp_path: Path):
    root = tmp_path / "repo"; root.mkdir(); init_git(root); honest_stack(root)
    base = commit_all(root)
    write(root / ".github/workflows/ci.yml", "name: CI\n")
    write(root / "INVARIANTS.md", "# Invariants\n\n- CI contract refreshed.\n")
    write(root / "harvest.json", json.dumps(harvest(concept("i1", "invariants"), evidence_rows=[evidence()])))
    commit_all(root, "workflow and docs")
    receipt = rd.audit_repository(root, changed_since=base, harvest_path="harvest.json")
    semantic = receipt["semantic_harvest"]
    assert semantic["status"] == "PASS"
    assert semantic["resolved_surfaces"] == ["invariants"]
    assert semantic["obligations"][0]["action"] == "ADD_OR_REFRESH"
    assert receipt["freshness"]["status"] == "PASS"
    assert receipt["final_status"] == "PASS"
    assert rd.exit_code_for_receipt(receipt) == 0
    assert "harvest.json" in receipt["evidence_sources"]
    assert ".github/workflows/ci.yml:1-10" in receipt["evidence_sources"]


def test_inference_cannot_close_and_stronger_beneficiary_is_preserved(tmp_path: Path):
    schema = Path("/tmp/l9-intelligence-harvest/contracts/harvest-ir.schema.json")
    inferred = rd.compile_obligations(
        harvest(concept("i1", "invariants"), evidence_rows=[evidence(epistemic="INFERENCE")]),
        ["invariants"], {"invariants": "docs:invariants"}, schema,
    )
    assert inferred["status"] == "PARTIAL" and inferred["resolved_surfaces"] == []
    stronger = concept("i2", "invariants", disposition="MERGE_WITH_EXISTING", comparison="BENEFICIARY_STRONGER")
    preserved = rd.compile_obligations(
        harvest(stronger, evidence_rows=[evidence()]),
        ["invariants"], {"invariants": "docs:invariants"}, schema,
    )
    assert preserved["status"] == "PASS"
    assert preserved["obligations"][0]["action"] == "PRESERVE"


def test_freshness_flags_stale_and_closes_when_doc_changes(tmp_path: Path):
    root = tmp_path / "repo"; root.mkdir(); honest_stack(root)
    policy = rd.load_policy()
    stale = rd.freshness_analysis(root, policy, rd.impact_analysis(policy, [".github/workflows/ci.yml"]), False)
    assert stale["stale_surfaces"] == ["invariants"]
    current = rd.freshness_analysis(root, policy, rd.impact_analysis(policy, [".github/workflows/ci.yml", "INVARIANTS.md"]), False)
    assert current["status"] == "PASS" and current["stale_surfaces"] == []


def test_optional_not_applicable_does_not_yellow_healthy_repo(tmp_path: Path):
    root = tmp_path / "repo"; root.mkdir(); init_git(root); honest_stack(root); commit_all(root)
    receipt = rd.audit_repository(root)
    assert receipt["llms_txt"]["status"] == "NotApplicable"
    assert receipt["final_status"] == "PASS"


def test_llms_is_small_machine_projection_and_run_mutation(tmp_path: Path):
    root = tmp_path / "repo"; root.mkdir(); init_git(root); honest_stack(root)
    write(root / "mkdocs.yml", "site_name: demo\n"); commit_all(root)
    receipt = rd.audit_repository(root, llms_base_url_value="https://docs.example.com", write_llms=True)
    text = (root / "llms.txt").read_text()
    assert text.startswith("# repo\n") and "Projection only; not authority." in text
    assert rd.validate_llms_txt(text) == []
    assert receipt["changes"]["run_mutations"] == ["llms.txt"]


def test_module_readme_capability_is_truthful_about_polyglot(tmp_path: Path):
    root = tmp_path / "repo"; root.mkdir(); policy = rd.load_policy()
    assert rd.probe_module_readme_capability(root, policy)["status"] == "NotApplicable"
    write(root / "scripts/generate_subsystem_readmes.py", "")
    assert rd.probe_module_readme_capability(root, policy)["status"] == "BLOCKED"
    write(root / "config/subsystems/readme_config.yaml", "version: 1\n")
    write(root / "workflows/dags/readme_pipeline_dag.py", "")
    assert rd.probe_module_readme_capability(root, policy, ["src/x.py"])["status"] == "AVAILABLE"
    ts = rd.probe_module_readme_capability(root, policy, ["src/x.ts"])
    assert ts["status"] == "PARTIAL" and ts["unsupported_impacted_extensions"] == [".ts"]


def test_receipt_schema_is_executable_authority(tmp_path: Path):
    root = tmp_path / "repo"; root.mkdir(); init_git(root); honest_stack(root); commit_all(root)
    receipt = rd.audit_repository(root)
    assert rd.validate_receipt_shape(receipt) == []
    broken = dict(receipt); broken.pop("freshness")
    assert rd.validate_receipt_shape(broken)


def test_partial_exit_semantics_distinguish_actionable_from_passive():
    passive = {"final_status": "PARTIAL", "semantic_harvest": {"unresolved_surfaces": []}, "freshness": {"stale_surfaces": [], "missing_surfaces": []}}
    active = {"final_status": "PARTIAL", "semantic_harvest": {"unresolved_surfaces": ["invariants"]}, "freshness": {"stale_surfaces": [], "missing_surfaces": []}}
    assert rd.exit_code_for_receipt(passive) == 0
    assert rd.exit_code_for_receipt(passive, fail_on_partial=True) == 3
    assert rd.exit_code_for_receipt(active) == 3
