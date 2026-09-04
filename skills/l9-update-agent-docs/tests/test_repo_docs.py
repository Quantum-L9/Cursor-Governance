from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
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


dp = load("doc_policy", SCRIPTS / "doc_policy.py")
dc = load("doc_change", SCRIPTS / "doc_change.py")
do = load("doc_obligations", SCRIPTS / "doc_obligations.py")
rd = load("repo_docs", SCRIPTS / "repo_docs.py")


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
            "https://github.com/Quantum-L9/Test-Repo.git",
        ],
        check=True,
    )


def commit(root: Path, message: str = "change") -> str:
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", message], check=True)
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def stack(root: Path, architecture: bool = True) -> None:
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


def module_pipeline(root: Path, *, complete: bool = True) -> None:
    write(root / "scripts/generate_subsystem_readmes.py", "# generator\n")
    write(
        root / "config/subsystems/readme_config.yaml",
        "version: 1\n"
        "subsystems:\n"
        "  skills:\n"
        "    path: skills\n"
        "    title: Skills\n"
        "    tier: control_plane\n"
        "    description: Skills.\n",
    )
    if complete:
        write(root / "workflows/dags/readme_pipeline_dag.py", "# dag\n")


def evidence(eid: str, path: str) -> dict:
    return {
        "id": eid,
        "epistemic": "CONFIRMED",
        "source": "repo",
        "locator": {"kind": "path_lines", "value": f"{path}:1-20"},
        "claim": "durable behavior changed",
        "secret_redacted": False,
    }


def concept(cid: str, destination: str, evidence_id: str) -> dict:
    return {
        "id": cid,
        "name": cid,
        "problem": "documentation must track durable repository behavior",
        "description": "qualified documentation obligation",
        "semantic_contract": (
            "Keep the documentation index aligned with executable repository behavior."
        ),
        "disposition": "PORT",
        "beneficiary_destination": destination,
        "evidence_ids": [evidence_id],
        "risks": ["stale documentation"],
        "acceptance_tests": [
            {
                "given": "repository change",
                "when": "docs refresh",
                "then": "receipt closes",
                "must_not": "invent semantics",
            }
        ],
        "beneficiary_fit": {
            "comparison": "DONOR_STRONGER",
            "existing_owner": destination,
            "merge_decision": "refresh existing index",
            "compatibility_risk": "low",
        },
        "nugget": True,
        "rank_score": 80,
    }


def bound_harvest(root: Path, base: str) -> dict:
    changed, error = dc.changed_files_since(root, base)
    assert error is None
    policy = dp.load_policy()
    impact = dc.impact_analysis(policy, changed or [])
    required = dc.semantic_harvest_required(policy, impact, root)
    digest, _paths = do.semantic_source_digest(root, policy, impact, required)
    assert digest
    request = rd.build_harvest_request("Quantum-L9/Test-Repo", required, digest)
    ev_arch = evidence("e-arch", ".github/workflows/ci.yml")
    ev_inv = evidence("e-inv", ".github/workflows/ci.yml")
    return {
        "schema_version": "1.1.0",
        "request": request,
        "source_identity": {
            "repo_docs": {
                "repository": "Quantum-L9/Test-Repo",
                "semantic_source_digest": digest,
                "required_surfaces": required,
            }
        },
        "inventory": [],
        "system": {
            "identity": "repo-docs",
            "workflows": [],
            "control_flow": [],
            "ownership_boundaries": [],
            "dependencies": [],
            "must_not_own": [],
        },
        "surfaces": [],
        "drift": [],
        "evidence": [ev_arch, ev_inv],
        "concepts": [
            concept("arch-contract", "docs:architecture", "e-arch"),
            concept("inv-contract", "docs:invariants", "e-inv"),
        ],
        "safety": [],
        "unknowns": [],
        "highest_leverage_nugget": "arch-contract",
        "status": "PASS",
    }


def test_policy_and_receipt_contracts_are_deeply_executable(tmp_path: Path):
    assert dp.validate_policy(dp.load_policy()) == []
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    module_pipeline(root)
    write(root / "skills/demo/x.py", "def x():\n    return 1\n")
    base = commit(root, "base")
    write(root / "skills/demo/x.py", "def x():\n    return 2\n")
    commit(root)
    receipt = rd.audit_repository(root, changed_since=base)
    broken = copy.deepcopy(receipt["obligations"][0])
    del broken["target"]["path"]
    assert dp.schema_errors(broken, dp.OBLIGATION_SCHEMA)
    broken_receipt = copy.deepcopy(receipt)
    broken_receipt["obligations"][0]["owner"] = {}
    assert rd.validate_receipt_shape(broken_receipt)


def test_workflow_change_compiles_target_resolved_semantic_obligations(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    base = commit(root, "base")
    write(root / ".github/workflows/ci.yml", "name: CI\n")
    commit(root)
    receipt = rd.audit_repository(
        root,
        changed_since=base,
        source_head_sha="source-head",
        tested_revision_sha="tested-revision",
    )
    obligations = {row["surface"]: row for row in receipt["obligations"]}
    assert receipt["final_status"] == "PARTIAL"
    assert receipt["revision"]["source_head_sha"] == "source-head"
    assert receipt["revision"]["tested_revision_sha"] == "tested-revision"
    assert obligations["architecture"]["target"]["path"] == "ARCHITECTURE.md"
    assert obligations["invariants"]["target"]["path"] == "INVARIANTS.md"
    assert obligations["architecture"]["lifecycle"]["status"] == "AWAITING_QUALIFICATION"
    assert rd.exit_code_for_receipt(receipt) == 3


def test_bound_harvest_normalizes_into_same_obligations_and_closes(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    base = commit(root, "base")
    write(root / ".github/workflows/ci.yml", "name: CI\n")
    write(root / "ARCHITECTURE.md", "# Architecture\n\nRepo docs compiler added.\n")
    write(root / "INVARIANTS.md", "# Invariants\n\nRepo docs receipt is evidence.\n")
    commit(root, "implementation and docs")
    write(
        root / "WIP/9-3-26/repo-docs/harvest.json",
        json.dumps(bound_harvest(root, base), indent=2),
    )
    commit(root, "harvest evidence")
    receipt = rd.audit_repository(root, changed_since=base)
    semantic = [
        row for row in receipt["obligations"] if row["surface"] in {"architecture", "invariants"}
    ]
    assert receipt["semantic_harvest"]["status"] == "PASS"
    assert receipt["semantic_harvest"]["discovered"] is True
    assert receipt["final_status"] == "PASS"
    assert receipt["summary"]["open"] == 0
    assert semantic and all(row["lifecycle"]["status"] == "CLOSED" for row in semantic)
    assert all(row["qualification"]["status"] == "QUALIFIED" for row in semantic)
    assert rd.validate_receipt_shape(receipt) == []


def test_module_change_resolves_exact_generator_target_and_lifecycle(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    module_pipeline(root)
    write(root / "skills/demo/x.py", "def x():\n    return 1\n")
    base = commit(root, "base")
    write(root / "skills/demo/x.py", "def x():\n    return 2\n")
    commit(root, "code")
    red = rd.audit_repository(root, changed_since=base)
    module = next(row for row in red["obligations"] if row["surface"] == "module_readmes")
    assert red["final_status"] == "PARTIAL"
    assert module["target"]["path"] == "skills/README.md"
    assert module["owner"]["id"] == "readme-pipeline-v1"
    assert module["required_action"]["type"] == "REGENERATE"
    write(
        root / "skills/README.md",
        "# Skills\n\n## Purpose\n\nDocs.\n\n## Components\n\nGenerated.\n",
    )
    commit(root, "generated README")
    green = rd.audit_repository(root, changed_since=base)
    module = next(row for row in green["obligations"] if row["surface"] == "module_readmes")
    assert module["lifecycle"]["status"] == "CLOSED"
    assert green["final_status"] == "PASS"


def test_policy_capability_controls_are_executable(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    policy = dp.load_policy()
    capability = dc.probe_module_readme_capability(root, policy, ["skills/x.py"])
    assert capability["status"] == "NotApplicable"
    write(root / "scripts/generate_subsystem_readmes.py", "")
    partial = dc.probe_module_readme_capability(root, policy, ["skills/x.py"])
    assert partial["status"] == "BLOCKED"


def test_optional_llms_projection_is_terminal_not_applicable(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    base = commit(root, "base")
    write(root / "ARCHITECTURE.md", "# Architecture\n\nChanged.\n")
    commit(root)
    receipt = rd.audit_repository(root, changed_since=base)
    llms = next(row for row in receipt["obligations"] if row["surface"] == "llms_txt")
    assert llms["lifecycle"] == {
        "status": "NOT_APPLICABLE",
        "reason": "surface has no applicable target for this change",
        "terminal": True,
    }
    assert receipt["final_status"] == "PASS"


def test_dirty_managed_region_fails_closed(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    marker = "<!-- BEGIN L9 FORMATTER OWNERSHIP -->\nowned\n<!-- END L9 FORMATTER OWNERSHIP -->"
    write(root / "README.md", (root / "README.md").read_text() + marker + "\n")
    commit(root)
    write(root / "README.md", (root / "README.md").read_text().replace("owned", "changed"))
    receipt = rd.audit_repository(root)
    assert receipt["final_status"] == "FAIL"
    assert any(item["code"] == "managed_regions" for item in receipt["structural_failures"])
