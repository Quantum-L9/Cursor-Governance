from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "ops/scripts/compile_governance_policy.py"


def _load():
    spec = importlib.util.spec_from_file_location("policy_compiler", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = _load()


def _seed(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    contracts = root / "governance/policy/contracts"
    contracts.mkdir(parents=True)
    (root / "governance/policy/changes").mkdir()
    names = (
        "policy-change.v1.schema.json",
        "repo-invariants.schema.json",
        "org-invariants.compiled.v1.schema.json",
        "policy-compile-receipt.v1.schema.json",
    )
    for name in names:
        shutil.copy(ROOT / "governance/policy/contracts" / name, contracts / name)
    return root


def _base(root: Path) -> str:
    return mod.PolicyCompiler(root).compile()["receipt"]["policy_digest"]


def _tx(change: str, invariant: str, base: str, **overrides: Any) -> dict[str, Any]:
    tx = {
        "schema": "l9.policy-change.v1",
        "change_id": change,
        "change_set_id": None,
        "scope": "repository",
        "operation": "add",
        "invariant_id": invariant,
        "supersedes": [],
        "preconditions": {
            "base_policy_digest": base,
            "target_invariant_digest": None,
            "superseded_invariant_digests": {},
        },
        "depends_on": [],
        "authority": {"kind": "explicit_user_authorization", "refs": []},
        "requirement": {
            "title": invariant,
            "statement": "Must remain true.",
            "applicability": "always",
        },
        "relationships": [],
        "bindings": [],
        "verifiers": [],
        "projection": {"invariants": True, "agents": True, "providers": []},
        "provenance": {"migration": None},
    }
    tx.update(overrides)
    return tx


def _write(root: Path, name: str, value: dict[str, Any]) -> None:
    path = root / "governance/policy/changes" / name
    path.write_text(yaml.safe_dump(value, sort_keys=False))


def test_deterministic(tmp_path: Path) -> None:
    root = _seed(tmp_path)
    _write(root, "a.yaml", _tx("GOV-2026-0001", "L9-REPO-001", _base(root)))
    first = mod.PolicyCompiler(root).compile()
    second = mod.PolicyCompiler(root).compile()
    assert first["repo_bytes"] == second["repo_bytes"]
    assert first["receipt"]["policy_digest"] == second["receipt"]["policy_digest"]


def test_duplicate_change_blocks(tmp_path: Path) -> None:
    root = _seed(tmp_path)
    base = _base(root)
    _write(root, "a.yaml", _tx("GOV-2026-0001", "L9-REPO-001", base))
    _write(root, "b.yaml", _tx("GOV-2026-0001", "L9-REPO-002", base))
    with pytest.raises(mod.PolicyError, match="duplicate change_id"):
        mod.PolicyCompiler(root).compile()


def test_cycle_and_stale_base_block(tmp_path: Path) -> None:
    root = _seed(tmp_path)
    base = _base(root)
    a = _tx("GOV-2026-0001", "L9-REPO-001", base, depends_on=["GOV-2026-0002"])
    b = _tx("GOV-2026-0002", "L9-REPO-002", base, depends_on=["GOV-2026-0001"])
    _write(root, "a.yaml", a)
    _write(root, "b.yaml", b)
    with pytest.raises(mod.PolicyError, match="dependency cycle"):
        mod.PolicyCompiler(root).compile()
    a["depends_on"] = []
    a["preconditions"]["base_policy_digest"] = "sha256:" + "f" * 64
    _write(root, "a.yaml", a)
    with pytest.raises(mod.PolicyError, match="stale base_policy_digest"):
        mod.PolicyCompiler(root).compile()


def test_retired_id_reuse_and_repo_over_org_block(tmp_path: Path) -> None:
    root = _seed(tmp_path)
    base = _base(root)
    first = _tx("GOV-2026-0001", "L9-REPO-001", base)
    _write(root, "a.yaml", first)
    one = mod.PolicyCompiler(root).compile()
    inv = one["repository"]["invariants"][0]
    retire = _tx(
        "GOV-2026-0002",
        "L9-REPO-001",
        one["receipt"]["policy_digest"],
        operation="retire",
        depends_on=["GOV-2026-0001"],
    )
    retire["preconditions"]["target_invariant_digest"] = inv["invariant_digest"]
    _write(root, "b.yaml", retire)
    two = mod.PolicyCompiler(root).compile()
    reuse = _tx(
        "GOV-2026-0003",
        "L9-REPO-001",
        two["receipt"]["policy_digest"],
        depends_on=["GOV-2026-0002"],
    )
    _write(root, "c.yaml", reuse)
    with pytest.raises(mod.PolicyError, match="already used or retired"):
        mod.PolicyCompiler(root).compile()


def test_path_traversal_and_manual_drift_block(tmp_path: Path) -> None:
    root = _seed(tmp_path)
    tx = _tx("GOV-2026-0001", "L9-REPO-001", _base(root))
    tx["bindings"] = [
        {"path": "../escape", "kind": "configuration", "required": True, "symbol": None}
    ]
    _write(root, "a.yaml", tx)
    with pytest.raises(mod.PolicyError, match="unsafe binding path"):
        mod.PolicyCompiler(root).compile()
    tx["bindings"] = []
    _write(root, "a.yaml", tx)
    assert mod.main(["compile", "--root", str(root)]) == 0
    (root / "governance/REPO_INVARIANTS.yaml").write_text("tampered\n")
    assert mod.main(["check", "--root", str(root)]) == 1
