"""Projection parity fails closed on every drift between a binding, its target and its contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
PACK = "skills/l9-global-architect"
GovRepo = Any  # the conftest fixture's type; fixtures are reached only through pytest

BINDING_FILE = "generated/governance/projections/L9.GAR.PROJECTION.SKILL_BOOTLOADER.001.yaml"
SKILL = f"{PACK}/SKILL.md"
STATE_MACHINE = f"{PACK}/runtime/STATE_MACHINE.yaml"


def _problems(result: subprocess.CompletedProcess[str]) -> list[str]:
    report = json.loads(result.stdout)
    return [p for b in report.get("bindings", {}).values() for p in b["problems"]]


def test_committed_binding_is_current_in_this_tree() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO / "tools/authority/validate_projection_parity.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_fresh_binding_is_current(generated_repo: GovRepo) -> None:
    result = generated_repo.run("validate_projection_parity.py")
    assert result.returncode == 0, result.stdout


def test_one_target_byte_is_drift(generated_repo: GovRepo) -> None:
    generated_repo.edit(SKILL, lambda s: s + " ")
    result = generated_repo.run("validate_projection_parity.py")
    assert result.returncode == 1
    assert any("projected_content_sha256" in p for p in _problems(result))


def test_removed_anchor_is_drift_and_blocks_generation(generated_repo: GovRepo) -> None:
    generated_repo.edit(
        SKILL, lambda s: s.replace("Bind the exact target identity", "Bind the target", 1)
    )
    result = generated_repo.run("validate_projection_parity.py")
    assert result.returncode == 1
    assert any("anchor for WF-TARGET-001" in p for p in _problems(result))
    generated_repo.commit("anchor gone")
    regenerated = generated_repo.generate()
    assert regenerated.returncode == 1
    assert "REGISTRY-009" in regenerated.stdout


def test_contract_change_is_drift(generated_repo: GovRepo) -> None:
    generated_repo.edit(
        STATE_MACHINE,
        lambda s: s.replace(
            "title: GAR Principal Architect Engineer Workflow",
            "title: GAR Principal Architect Engineer Workflow v2",
            1,
        ),
    )
    result = generated_repo.run("validate_projection_parity.py")
    assert result.returncode == 1
    assert any("PROJECTION-001 pinned digest" in p for p in _problems(result))


def test_clause_absent_from_contract_is_drift(generated_repo: GovRepo) -> None:
    generated_repo.edit(
        BINDING_FILE,
        lambda s: s.replace("  - WF-BLOCK-001\n", "  - WF-BLOCK-001\n  - WF-NOPE-001\n", 1),
    )
    result = generated_repo.run("validate_projection_parity.py")
    assert result.returncode == 1
    assert any("PROJECTION-005 clause WF-NOPE-001" in p for p in _problems(result))


def test_target_claiming_ownership_is_drift(generated_repo: GovRepo) -> None:
    generated_repo.edit(
        BINDING_FILE,
        lambda s: s.replace(
            "target_may_redefine_semantics: false", "target_may_redefine_semantics: true", 1
        ),
    )
    result = generated_repo.run("validate_projection_parity.py")
    assert result.returncode == 1
    problems = _problems(result)
    assert any("PROJECTION-002" in p for p in problems)
    assert any(p.startswith("SCHEMA CONST") for p in problems)


def test_relaxed_drift_policy_is_drift(generated_repo: GovRepo) -> None:
    generated_repo.edit(
        BINDING_FILE, lambda s: s.replace("drift_policy: fail_closed", "drift_policy: warn", 1)
    )
    result = generated_repo.run("validate_projection_parity.py")
    assert result.returncode == 1
    assert any("PROJECTION-004" in p for p in _problems(result))


def test_missing_binding_instance_is_drift(generated_repo: GovRepo) -> None:
    (generated_repo.root / BINDING_FILE).unlink()
    result = generated_repo.run("validate_projection_parity.py")
    assert result.returncode == 1
    assert "declared projection target has no binding instance" in result.stdout


def test_absent_registry_is_blocked(gov_repo: GovRepo) -> None:
    result = gov_repo.run("validate_projection_parity.py")
    assert result.returncode == 3
    assert json.loads(result.stdout)["status"] == "BLOCKED"
