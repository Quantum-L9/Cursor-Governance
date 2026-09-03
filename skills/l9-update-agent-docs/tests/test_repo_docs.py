from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

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


rd = load("repo_docs", SCRIPTS / "repo_docs.py")
vp = load("validate_pointer_headings", SCRIPTS / "validate_pointer_headings.py")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    for key, value in (("user.email", "tests@example.com"), ("user.name", "Tests")):
        subprocess.run(["git", "-C", str(root), "config", key, value], check=True)


def commit(root: Path, message: str = "change") -> str:
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", message], check=True)
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()


def stack(root: Path, architecture: bool = False) -> None:
    write(
        root / "README.md",
        "# Repo\n\n## Purpose\n\nIndex.\n\n## Key Files\n\nCANONICAL_LAW.md AGENTS.md\n",
    )
    write(
        root / "CLAUDE.md",
        "# Load\n\n## Authority chain\n\nCANONICAL_LAW.md > AGENTS.md\n",
    )
    write(root / "AGENTS.md", "# Agents\n")
    write(root / "CANONICAL_LAW.md", "# Law\n")
    write(root / "INVARIANTS.md", "# Invariants\n")
    if architecture:
        write(root / "ARCHITECTURE.md", "# Architecture\n")


def ev(epistemic: str = "CONFIRMED") -> dict:
    return {
        "id": "e1",
        "epistemic": epistemic,
        "source": "repo",
        "locator": {"kind": "path_lines", "value": ".github/workflows/ci.yml:1-10"},
        "claim": "workflow enforces durable behavior",
        "secret_redacted": False,
    }


def nugget(disposition: str = "PORT", comparison: str = "DONOR_STRONGER") -> dict:
    return {
        "id": "i1",
        "name": "invariant semantic",
        "problem": "durable behavior must remain documented",
        "semantic_contract": "Keep invariants aligned with executable semantics.",
        "disposition": disposition,
        "beneficiary_destination": "docs:invariants",
        "evidence_ids": ["e1"],
        "risks": ["stale docs"],
        "acceptance_tests": [
            {"given": "change", "when": "refresh", "then": "aligned", "must_not": "invent"}
        ],
        "beneficiary_fit": {
            "comparison": comparison,
            "existing_owner": "invariants",
            "merge_decision": "preserve stronger semantics",
            "compatibility_risk": "low",
        },
        "nugget": True,
        "rank_score": 55,
    }


def harvest(*concepts: dict, evidence: list[dict] | None = None) -> dict:
    return {
        "schema_version": "1.1.0",
        "request": {
            "request_id": "repo-docs-test",
            "donor": "repo",
            "beneficiary": "repo",
            "harvest_target": "repo-docs:invariants",
        },
        "source_identity": {},
        "inventory": [],
        "system": {
            "identity": "repo",
            "workflows": [],
            "control_flow": [],
            "ownership_boundaries": [],
            "dependencies": [],
            "must_not_own": [],
        },
        "surfaces": [],
        "drift": [],
        "evidence": evidence or [],
        "concepts": list(concepts),
        "safety": [],
        "unknowns": [],
        "highest_leverage_nugget": concepts[0]["id"] if concepts else None,
        "status": "PASS",
    }


def test_contracts_are_executable_and_single_ssot():
    policy = rd.load_policy()
    assert rd.validate_policy(policy) == []
    broken = yaml.safe_load(yaml.safe_dump(policy))
    del broken["surfaces"]["agents"]["requirement"]
    assert rd.validate_policy(broken)
    duplicate = yaml.safe_load(yaml.safe_dump(policy))
    duplicate["surfaces"]["claude"]["authority_class"] = "operating_ssot"
    assert any("exactly one operating_ssot" in e for e in rd.validate_policy(duplicate))


def test_dirty_managed_region_fails_and_missing_pointer_is_partial(tmp_path: Path):
    assert vp.validate_root(tmp_path)["status"] == "PARTIAL"
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    marker = "<!-- BEGIN L9 FORMATTER OWNERSHIP -->\nowned\n<!-- END L9 FORMATTER OWNERSHIP -->"
    write(root / "README.md", (root / "README.md").read_text() + marker + "\n")
    commit(root)
    write(root / "README.md", (root / "README.md").read_text().replace("owned", "changed"))
    changed, base, error = rd.automatic_changed_scope(root)
    assert error is None and base == "HEAD"
    status, findings = rd.validate_managed_regions(root, base, changed, rd.load_policy())
    assert status == "FAIL" and "managed block changed" in findings[0]


def test_impact_freshness_and_targeted_harvest_request(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    base = commit(root)
    write(root / ".github/workflows/ci.yml", "name: CI\n")
    commit(root)
    receipt = rd.audit_repository(root, changed_since=base)
    assert receipt["semantic_harvest"]["required_surfaces"] == ["invariants"]
    assert receipt["semantic_harvest"]["request"]["harvest_target"] == "repo-docs:invariants"
    assert receipt["freshness"]["stale_surfaces"] == ["invariants"]
    assert rd.exit_code_for_receipt(receipt) == 3


def test_canonical_harvest_closes_only_confirmed_semantics(tmp_path: Path):
    schema = PACK.parent / "l9-intelligence-harvest" / "contracts" / "harvest-ir.schema.json"
    inferred = rd.compile_obligations(
        harvest(nugget(), evidence=[ev("INFERENCE")]),
        ["invariants"],
        {"invariants": "docs:invariants"},
        schema,
    )
    assert inferred["status"] == "PARTIAL"
    stronger = nugget("MERGE_WITH_EXISTING", "BENEFICIARY_STRONGER")
    preserved = rd.compile_obligations(
        harvest(stronger, evidence=[ev()]),
        ["invariants"],
        {"invariants": "docs:invariants"},
        schema,
    )
    assert preserved["status"] == "PASS"
    assert preserved["obligations"][0]["action"] == "PRESERVE"


def test_red_to_green_lifecycle_and_observed_evidence(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    base = commit(root)
    write(root / ".github/workflows/ci.yml", "name: CI\n")
    write(root / "INVARIANTS.md", "# Invariants\n\n- CI contract refreshed.\n")
    write(root / "harvest.json", json.dumps(harvest(nugget(), evidence=[ev()])))
    commit(root)
    receipt = rd.audit_repository(root, changed_since=base, harvest_path="harvest.json")
    assert receipt["semantic_harvest"]["status"] == "PASS"
    assert receipt["freshness"]["status"] == "PASS"
    assert receipt["final_status"] == "PASS" and rd.exit_code_for_receipt(receipt) == 0
    assert "harvest.json" in receipt["evidence_sources"]
    assert ".github/workflows/ci.yml:1-10" in receipt["evidence_sources"]
    assert rd.validate_receipt_shape(receipt) == []


def test_optional_llms_and_polyglot_capability_are_truthful(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    commit(root)
    assert rd.audit_repository(root)["final_status"] == "PASS"
    policy = rd.load_policy()
    write(root / "scripts/generate_subsystem_readmes.py", "")
    write(root / "config/subsystems/readme_config.yaml", "version: 1\n")
    write(root / "workflows/dags/readme_pipeline_dag.py", "")
    assert rd.probe_module_readme_capability(root, policy, ["src/x.py"])["status"] == "AVAILABLE"
    ts = rd.probe_module_readme_capability(root, policy, ["src/x.ts"])
    assert ts["status"] == "PARTIAL" and ts["unsupported_impacted_extensions"] == [".ts"]
    write(root / "mkdocs.yml", "site_name: demo\n")
    receipt = rd.audit_repository(
        root,
        llms_base_url_value="https://docs.example.com",
        write_llms=True,
    )
    assert receipt["changes"]["run_mutations"] == ["llms.txt"]
    assert rd.validate_llms_txt((root / "llms.txt").read_text()) == []
