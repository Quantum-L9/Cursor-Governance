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
    # Two skill packs, so `skills` is an index the inventory authorizes on
    # its own. The config entry below decorates that target; it must never
    # be what creates it.
    write(root / "skills/other/y.py", "def y():\n    return 1\n")
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


def test_audit_fills_missing_readmes_outside_the_change_set(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    module_pipeline(root)
    write(root / "skills/demo/x.py", "def x():\n    return 1\n")
    write(root / "environment/agents/lifecycle/mod.py", "def ready():\n    return True\n")
    base = commit(root, "base with two modules and no readmes")
    write(root / "skills/demo/x.py", "def x():\n    return 2\n")
    commit(root, "touch only one module")
    receipt = rd.audit_repository(root, changed_since=base)
    assert (root / "skills/demo/README.md").is_file()
    assert (root / "environment/agents/lifecycle/README.md").is_file()
    assert "environment/agents/lifecycle/README.md" in receipt["changes"]["run_mutations"]
    assert receipt["final_status"] == "PASS"


def test_receipt_carries_the_readme_reconciliation_histogram(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    module_pipeline(root)
    write(root / "skills/demo/x.py", "def x():\n    return 1\n")
    base = commit(root, "base")
    write(root / "skills/demo/x.py", "def x():\n    return 2\n")
    commit(root, "code")
    receipt = rd.audit_repository(root, changed_since=base)
    planned = receipt["capabilities"]["module_readmes"]["planned"]
    assert set(planned) == {
        "create",
        "refresh",
        "unchanged",
        "preserve",
        "retire",
        "conflict",
    }
    assert planned["create"] >= 1
    assert planned["conflict"] == 0
    quality = receipt["capabilities"]["module_readmes"]["quality"]
    assert quality
    assert {row["completeness"] for row in quality} <= {
        "complete",
        "partial",
        "minimal-by-design",
    }
    # The histogram is diagnostics on the capability, not a second ledger.
    assert receipt["final_status"] == "PASS"

    # A second audit over the settled tree plans no mutation at all.
    again = rd.audit_repository(root, changed_since=base)
    settled = again["capabilities"]["module_readmes"]["planned"]
    assert settled["create"] == 0
    assert settled["refresh"] == 0
    assert settled["retire"] == 0
    assert settled["conflict"] == 0


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
    receipt = rd.audit_repository(root, changed_since=base)
    modules = [row for row in receipt["obligations"] if row["surface"] == "module_readmes"]
    paths = {row["target"]["path"] for row in modules}
    assert (root / "skills/README.md").is_file()
    assert (root / "skills/demo/README.md").is_file()
    assert "skills/README.md" in paths
    assert "skills/demo/README.md" in paths
    assert all(row["owner"]["id"] == "l9-update-agent-docs" for row in modules)
    assert all(row["lifecycle"]["status"] == "CLOSED" for row in modules)
    assert (root / "filetree.md").is_file()
    assert receipt["filetree"]["path"] == "filetree.md"
    assert receipt["filetree"]["status"] == "PASS"
    assert "filetree.md" in receipt["changes"]["run_mutations"]
    filetree = next(row for row in receipt["obligations"] if row["surface"] == "filetree")
    assert filetree["lifecycle"]["status"] == "CLOSED"
    assert receipt["final_status"] == "PASS"


def test_policy_capability_controls_are_executable(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    policy = dp.load_policy()
    capability = dc.probe_module_readme_capability(root, policy, ["skills/x.py"])
    assert capability["status"] == "AVAILABLE"
    assert capability["owner"] == "l9-update-agent-docs"
    assert capability["present"]["generator"] is True
    xml = dc.probe_module_readme_capability(root, policy, ["skills/x.xml"])
    assert xml["status"] == "AVAILABLE"
    assert xml["unsupported_impacted_extensions"] == []


def test_default_llm_projection_is_created_and_closed(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    base = commit(root, "base")
    write(root / "ARCHITECTURE.md", "# Architecture\n\nChanged.\n")
    commit(root)
    receipt = rd.audit_repository(root, changed_since=base)
    llm = next(row for row in receipt["obligations"] if row["surface"] == "llm_txt")
    assert (root / "llm.txt").is_file()
    assert (root / "filetree.md").is_file()
    assert receipt["filetree"]["written"] is True
    assert receipt["llm_txt"]["enabled"] is True
    assert receipt["llm_txt"]["written"] is True
    assert receipt["llm_txt"]["admission"] == "create"
    assert "<!-- l9-llm-txt: generated-projection -->" in (root / "llm.txt").read_text(
        encoding="utf-8"
    )
    assert llm["target"]["path"] == "llm.txt"
    assert llm["lifecycle"]["status"] == "CLOSED"
    assert receipt["final_status"] == "PASS"


def test_adapter_can_disable_llm_projection(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    write(
        root / ".claude/adapters/test-repo-update-agent-docs.md",
        "<!-- L9_DOCS\nllm_txt: disabled\n-->\n",
    )
    base = commit(root, "base")
    write(root / "ARCHITECTURE.md", "# Architecture\n\nChanged.\n")
    commit(root)
    receipt = rd.audit_repository(root, changed_since=base)
    llm = next(row for row in receipt["obligations"] if row["surface"] == "llm_txt")
    assert receipt["llm_txt"]["enabled"] is False
    assert llm["lifecycle"] == {
        "status": "NOT_APPLICABLE",
        "reason": "surface has no applicable target for this change",
        "terminal": True,
    }
    assert not (root / "llm.txt").exists()


def test_legacy_llms_txt_is_renamed_when_llm_txt_is_missing(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    handwritten = "# Quantum-L9 Test\n\n## Authority\n\n- [Law](CANONICAL_LAW.md)\n"
    write(root / "llms.txt", handwritten)
    base = commit(root, "base")
    write(root / "ARCHITECTURE.md", "# Architecture\n\nChanged.\n")
    commit(root)
    receipt = rd.audit_repository(root, changed_since=base)
    assert (root / "llm.txt").read_text(encoding="utf-8") == handwritten
    assert not (root / "llms.txt").exists()
    assert receipt["llm_txt"]["admission"] == "preserve"
    assert receipt["llm_txt"]["written"] is False
    assert "retired:llms.txt" in receipt["changes"]["run_mutations"]


def test_retirement_oserror_becomes_blocked_receipt(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    write(root / "llms.txt", "# leftover\n")
    base = commit(root, "base")
    write(root / "ARCHITECTURE.md", "# Architecture\n\nChanged.\n")
    commit(root)

    def refuse(root: Path, *, rename_missing: bool = True) -> list[str]:
        raise OSError("read-only filesystem")

    monkeypatch.setattr(rd, "retire_legacy_llms_txt", refuse)
    receipt = rd.audit_repository(root, changed_since=base)
    assert receipt["final_status"] == "BLOCKED"
    assert receipt["llm_txt"]["status"] == "BLOCKED"
    assert receipt["llm_txt"]["admission"] == "skipped"
    assert any("read-only filesystem" in item for item in receipt["llm_txt"]["findings"])
    assert any(
        item["code"] == "llm_txt" and item["severity"] == "BLOCKED"
        for item in receipt["structural_failures"]
    )
    llm = next(row for row in receipt["obligations"] if row["surface"] == "llm_txt")
    assert llm["lifecycle"]["status"] == "BLOCKED"
    assert (root / "llms.txt").is_file()
    assert rd.validate_receipt_shape(receipt) == []


def test_disabled_projection_retirement_oserror_is_blocked(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    write(root / "llm.txt", "# Keep this\n")
    write(root / "llms.txt", "# leftover\n")
    write(
        root / ".claude/adapters/test-repo-update-agent-docs.md",
        "<!-- L9_DOCS\nllm_txt: disabled\n-->\n",
    )
    base = commit(root, "base")
    write(root / "ARCHITECTURE.md", "# Architecture\n\nChanged.\n")
    commit(root)

    def refuse(root: Path, *, rename_missing: bool = True) -> list[str]:
        assert rename_missing is False
        raise PermissionError("locked")

    monkeypatch.setattr(rd, "retire_legacy_llms_txt", refuse)
    receipt = rd.audit_repository(root, changed_since=base)
    assert receipt["final_status"] == "BLOCKED"
    assert receipt["llm_txt"]["enabled"] is False
    assert receipt["llm_txt"]["status"] == "BLOCKED"
    assert rd.validate_receipt_shape(receipt) == []


def test_filetree_oserror_becomes_blocked_receipt(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    base = commit(root, "base")
    write(root / "ARCHITECTURE.md", "# Architecture\n\nChanged.\n")
    commit(root)

    def refuse(root: Path, *, write: bool = True):
        raise OSError("disk full")

    monkeypatch.setattr(rd, "build_filetree_state", refuse)
    receipt = rd.audit_repository(root, changed_since=base)
    assert receipt["final_status"] == "BLOCKED"
    assert receipt["filetree"]["status"] == "BLOCKED"
    assert receipt["filetree"]["written"] is False
    assert any(item["code"] == "filetree" for item in receipt["structural_failures"])
    assert rd.validate_receipt_shape(receipt) == []


def test_legacy_llms_txt_is_deleted_when_llm_txt_exists(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    handwritten = "# Keep this\n\n- [Law](CANONICAL_LAW.md)\n"
    write(root / "llm.txt", handwritten)
    write(root / "llms.txt", "# leftover name\n")
    base = commit(root, "base")
    write(root / "ARCHITECTURE.md", "# Architecture\n\nChanged.\n")
    commit(root)
    receipt = rd.audit_repository(root, changed_since=base)
    assert (root / "llm.txt").read_text(encoding="utf-8") == handwritten
    assert not (root / "llms.txt").exists()
    assert receipt["llm_txt"]["admission"] == "preserve"
    assert "retired:llms.txt" in receipt["changes"]["run_mutations"]


def test_write_llm_does_not_overwrite_unowned_llm_txt(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    handwritten = "# Keep this\n\n- [Law](CANONICAL_LAW.md)\n"
    write(root / "llm.txt", handwritten)
    base = commit(root, "base")
    write(root / "ARCHITECTURE.md", "# Architecture\n\nChanged.\n")
    commit(root)
    receipt = rd.audit_repository(root, changed_since=base, write_llm=True)
    assert (root / "llm.txt").read_text(encoding="utf-8") == handwritten
    assert receipt["llm_txt"]["admission"] == "preserve"
    assert receipt["llm_txt"]["written"] is False


def test_preserved_unowned_targets_are_terminal_obligations(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    write(root / "llm.txt", "# Keep this\n\n- [Law](CANONICAL_LAW.md)\n")
    write(root / "filetree.md", "# My own tree\n")
    base = commit(root, "base")
    write(root / "ARCHITECTURE.md", "# Architecture\n\nChanged.\n")
    commit(root)
    receipt = rd.audit_repository(root, changed_since=base, write_llm=True)
    assert (root / "llm.txt").read_text(encoding="utf-8").startswith("# Keep this")
    assert (root / "filetree.md").read_text(encoding="utf-8") == "# My own tree\n"
    assert receipt["llm_txt"]["admission"] == "preserve"
    assert receipt["filetree"]["admission"] == "preserve"
    rows = {row["surface"]: row for row in receipt["obligations"]}
    for surface in ("llm_txt", "filetree"):
        assert rows[surface]["lifecycle"]["status"] == "PRESERVED"
        assert rows[surface]["lifecycle"]["terminal"] is True
        assert rows[surface]["required_action"]["type"] == "PRESERVE"
        assert any(
            row["locator"]["value"] == "admission:preserve" and row["supports"] == "preservation"
            for row in rows[surface]["evidence"]
        )
    assert receipt["summary"]["open"] == 0
    assert receipt["final_status"] == "PASS"
    assert rd.validate_receipt_shape(receipt) == []


def test_current_owned_targets_close_without_a_rewrite(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    base = commit(root, "base")
    write(root / "ARCHITECTURE.md", "# Architecture\n\nChanged.\n")
    commit(root)
    first = rd.audit_repository(root, changed_since=base)
    assert first["llm_txt"]["admission"] == "create"
    assert first["filetree"]["written"] is True
    commit(root, "projections")
    write(root / "ARCHITECTURE.md", "# Architecture\n\nChanged again.\n")
    commit(root)
    receipt = rd.audit_repository(root, changed_since=base)
    # The v3 LLM manifest carries every indexed source digest, so an
    # architecture byte change requires a projection refresh.
    assert receipt["llm_txt"]["admission"] == "refresh"
    assert receipt["llm_txt"]["written"] is True
    assert receipt["filetree"]["admission"] == "unchanged"
    assert receipt["filetree"]["written"] is False
    assert "llm.txt" in receipt["changes"]["run_mutations"]
    rows = {row["surface"]: row for row in receipt["obligations"]}
    for surface in ("llm_txt", "filetree"):
        assert rows[surface]["lifecycle"]["status"] == "CLOSED"
        freshness = next(
            row
            for row in rows[surface]["validation"]["results"]
            if row["name"] == "target_freshness"
        )
        assert freshness["status"] == "PASS"
        assert freshness["evidence_ids"]
        assert all(
            any(row["id"] == ev_id for row in rows[surface]["evidence"])
            for ev_id in freshness["evidence_ids"]
        )
    assert receipt["final_status"] == "PASS"
    assert rd.validate_receipt_shape(receipt) == []


def test_skipped_admission_keeps_refresh_obligation_open(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    base = commit(root, "base")
    write(root / "ARCHITECTURE.md", "# Architecture\n\nChanged.\n")
    commit(root)
    receipt = rd.audit_repository(root, changed_since=base, write_filetree=False)
    assert receipt["filetree"]["admission"] == "skipped"
    assert not (root / "filetree.md").exists()
    filetree = next(row for row in receipt["obligations"] if row["surface"] == "filetree")
    assert filetree["lifecycle"]["status"] == "OPEN"
    freshness = next(
        row for row in filetree["validation"]["results"] if row["name"] == "target_freshness"
    )
    assert freshness["status"] == "UNKNOWN"
    assert receipt["final_status"] == "PARTIAL"


def test_declared_root_python_fences_are_syntax_checked_without_execution(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    write(
        root / "README.md",
        (root / "README.md").read_text(encoding="utf-8")
        + "\n```python\nraise RuntimeError('must not execute')\n```\n",
    )
    fence = dp.python_fence_validate_root(root)
    assert fence["status"] == "PASS"
    assert fence["findings"] == []


def test_invalid_root_python_fence_is_bounded_to_declared_pointer_documents(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    write(root / "notes.md", "```python\ndef broken(:\n```\n")
    assert dp.python_fence_validate_root(root)["status"] == "PASS"
    write(
        root / "README.md",
        (root / "README.md").read_text(encoding="utf-8") + "\n```python\ndef broken(:\n```\n",
    )
    fence = dp.python_fence_validate_root(root)
    assert fence["status"] == "FAIL"
    assert fence["findings"]
    assert fence["findings"][0].startswith("README.md:")
    assert "invalid Python fence" in fence["findings"][0]


def test_root_python_fence_scanner_accepts_markdown_indentation_and_delimiters(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    for fence in (
        "   ```python\ndef broken(:\n   ```\n",
        "````python\ndef broken(:\n````\n",
        "~~~python\ndef broken(:\n~~~\n",
    ):
        write(root / "README.md", "# Repo\n\n" + fence)
        checked = dp.python_fence_validate_root(root)
        assert checked["status"] == "FAIL"
        assert next(row for row in checked["files"] if row["path"] == "README.md") == {
            "path": "README.md",
            "fence_count": 1,
        }


def test_root_python_fence_scanner_requires_the_opening_delimiter_length(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    write(
        root / "README.md",
        "# Repo\n\n````python\nx = 1\n```\ny = 2\n````\n",
    )
    assert dp.python_fence_validate_root(root)["status"] == "FAIL"
    write(root / "README.md", "# Repo\n\n````python\nx = 1\n`````\n")
    assert dp.python_fence_validate_root(root)["status"] == "PASS"


def test_invalid_root_python_fence_is_a_receipt_structural_failure(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    base = commit(root, "base")
    write(
        root / "README.md",
        (root / "README.md").read_text(encoding="utf-8") + "\n```python\ndef broken(:\n```\n",
    )
    commit(root, "invalid root fence")
    receipt = rd.audit_repository(root, changed_since=base)
    assert receipt["final_status"] == "FAIL"
    assert any(item["code"] == "python_fence_validation" for item in receipt["structural_failures"])
    validator = next(
        item for item in receipt["validators_executed"] if item["name"] == "root_python_fences"
    )
    assert validator["status"] == "FAIL"


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


def test_receipt_outside_root_reports_the_rejection_and_still_emits(
    tmp_path: Path, monkeypatch, capsys
):
    """`--receipt` outside the audited root must refuse loudly, not silently.

    Refusing to write there is correct. Returning 2 with no stdout and no
    stderr is not: the audit has already run and may already have mutated the
    tree, so the caller is left with an exit code and nothing to read.
    """
    root = tmp_path / "repo"
    root.mkdir()
    init(root)
    stack(root)
    commit(root, "base")
    outside = tmp_path / "outside" / "receipt.json"
    monkeypatch.setattr(
        sys, "argv", ["repo_docs.py", "--root", str(root), "--receipt", str(outside)]
    )
    code = rd.main()
    captured = capsys.readouterr()
    assert code == 2
    assert not outside.exists()
    assert str(outside) in captured.err
    assert json.loads(captured.out)["schema"] == rd.RECEIPT_ID
