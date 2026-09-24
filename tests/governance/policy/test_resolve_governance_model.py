from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "ops" / "scripts" / "resolve_governance_model.py"


def _load():
    spec = importlib.util.spec_from_file_location("resolve_governance_model", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = _load()


def _seed(tmp_path: Path, *, binding: bool = True, external: bool = False) -> Path:
    root = tmp_path / "repo"
    (root / "governance" / "policy" / "contracts").mkdir(parents=True)
    for name in (
        "resolved-governance-model.v1.schema.json",
        "governance-resolve-receipt.v1.schema.json",
    ):
        shutil.copy(
            ROOT / "governance/policy/contracts" / name,
            root / "governance/policy/contracts" / name,
        )
    if binding:
        (root / "ops" / "x").mkdir(parents=True)
        (root / "ops" / "x" / "binding.json").write_text("{}\n", encoding="utf-8")
        (root / "tests").mkdir()
        (root / "tests/test_x.py").write_text(
            "def test_x():\n    assert True\n", encoding="utf-8"
        )
    inv = {
        "id": "L9-REPO-001",
        "title": "X",
        "statement": "X must remain true.",
        "applicability": "always",
        "relationships": [],
        "bindings": [
            {
                "path": "ops/x/binding.json",
                "kind": "configuration",
                "required": True,
                "symbol": None,
            }
        ],
        "verifiers": [
            {
                "path": "tests/test_x.py",
                "kind": "manual_external" if external else "test",
                "required": True,
                "invocation_id": "x",
            }
        ],
        "projection": {"invariants": True, "agents": True, "providers": []},
        "source_change_ids": ["GOV-2026-0001"],
        "invariant_digest": "sha256:" + "d" * 64,
    }
    policy_digest = "sha256:" + "b" * 64
    org = {
        "schema": "l9.org-invariants.compiled.v1",
        "organization": "Quantum-L9",
        "policy_digest": policy_digest,
        "source_transaction_digest": "sha256:" + "c" * 64,
        "status": "active",
        "invariants": [],
        "retired_ids": [],
    }
    repo = {
        "schema": "l9.repo-invariants.v1",
        "repository": "Quantum-L9/Cursor-Governance",
        "policy_digest": policy_digest,
        "source_transaction_digest": "sha256:" + "c" * 64,
        "status": "active",
        "invariants": [inv],
        "retired_ids": [],
    }
    (root / "governance").mkdir(exist_ok=True)
    (root / "ORG_INVARIANTS.yaml").write_text(
        yaml.safe_dump(org, sort_keys=False), encoding="utf-8"
    )
    (root / "governance/REPO_INVARIANTS.yaml").write_text(
        yaml.safe_dump(repo, sort_keys=False), encoding="utf-8"
    )
    return root


def test_structural_resolve_is_implemented_and_passes(tmp_path: Path) -> None:
    root = _seed(tmp_path)
    model, receipt = mod.resolve(root, source_revision="abcdef0")
    assert receipt["status"] == "PASS"
    assert model["invariants"][0]["implementation"]["status"] == "IMPLEMENTED"
    assert model["facts"]


def test_admitted_pass_is_verified(tmp_path: Path) -> None:
    root = _seed(tmp_path)
    model, receipt = mod.resolve(
        root, source_revision="abcdef0", evidence={"verifier_results": {"x": "PASS"}}
    )
    assert receipt["status"] == "PASS"
    assert model["invariants"][0]["implementation"]["status"] == "VERIFIED"


def test_missing_required_binding_blocks_projected_invariant(tmp_path: Path) -> None:
    root = _seed(tmp_path, binding=False)
    model, receipt = mod.resolve(root, source_revision="abcdef0")
    assert receipt["status"] == "BLOCKED"
    assert receipt["blocked_ids"] == ["L9-REPO-001"]
    assert model["invariants"][0]["implementation"]["status"] == "MISSING"


def test_external_verifier_without_evidence_is_unknown(tmp_path: Path) -> None:
    root = _seed(tmp_path, external=True)
    model, receipt = mod.resolve(root, source_revision="abcdef0")
    assert receipt["status"] == "BLOCKED"
    assert model["invariants"][0]["implementation"]["status"] == "UNKNOWN"


def test_admitted_failure_is_conflict(tmp_path: Path) -> None:
    root = _seed(tmp_path)
    model, receipt = mod.resolve(
        root, source_revision="abcdef0", evidence={"verifier_results": {"x": "FAIL"}}
    )
    assert receipt["status"] == "BLOCKED"
    assert model["invariants"][0]["implementation"]["status"] == "CONFLICT"


def test_deterministic_model_digest(tmp_path: Path) -> None:
    root = _seed(tmp_path)
    first, _ = mod.resolve(root, source_revision="abcdef0")
    second, _ = mod.resolve(root, source_revision="abcdef0")
    assert first == second
    assert first["model_digest"] == second["model_digest"]
