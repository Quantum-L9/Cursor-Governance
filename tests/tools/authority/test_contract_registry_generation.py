"""The contract registry is deterministic, provenance-bound, and refuses every gate violation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[3]
PACK = "skills/l9-global-architect"
GovRepo = Any  # the conftest fixture's type; fixtures are reached only through pytest

REGISTRY = "generated/governance/CONTRACT_REGISTRY.yaml"
BINDING_FILE = "generated/governance/projections/L9.GAR.PROJECTION.SKILL_BOOTLOADER.001.yaml"
EPISTEMIC = f"{PACK}/contracts/EPISTEMIC_DISCIPLINE.yaml"


def _status(result: subprocess.CompletedProcess[str]) -> str:
    return str(json.loads(result.stdout)["status"])


# Literal paths on purpose: the PR test selector (ops/scripts/select_pr_pytest_paths.py) picks a
# test file when it names a changed path, so a change to any generation input selects the live
# checks here. The test below fails when this list and the registry's own record diverge.
WATCHED_INPUTS = (
    "contracts/schemas/canonical.schema.contract_projection_binding.v1.yaml",
    "contracts/schemas/canonical.schema.contract_registry.v1.yaml",
    "contracts/schemas/canonical.schema.evidence_contract.v1.yaml",
    "contracts/schemas/canonical.schema.governance_contract.v1.yaml",
    "contracts/schemas/canonical.schema.invariant_contract.v1.yaml",
    "contracts/schemas/canonical.schema.policy_contract.v1.yaml",
    "contracts/schemas/canonical.schema.workflow_contract.v1.yaml",
    "skills/l9-global-architect/SKILL.md",
    "skills/l9-global-architect/bindings/GOVERNANCE_GENERATION.yaml",
    "skills/l9-global-architect/contracts/ARCHITECTURAL_INTEGRITY.yaml",
    "skills/l9-global-architect/contracts/CONVERGENCE.yaml",
    "skills/l9-global-architect/contracts/EPISTEMIC_DISCIPLINE.yaml",
    "skills/l9-global-architect/contracts/L9_ARCHITECTURE_PROFILE.yaml",
    "skills/l9-global-architect/contracts/OBJECTIVE_DERIVATION.yaml",
    "skills/l9-global-architect/contracts/OUTCOME_OWNERSHIP.yaml",
    "skills/l9-global-architect/integrations/REASONING_FOURSOME_BINDING.yaml",
    "skills/l9-global-architect/runtime/MANIFEST.yaml",
    "skills/l9-global-architect/runtime/STATE_MACHINE.yaml",
)


def test_watched_inputs_are_the_registry_generation_inputs() -> None:
    import yaml

    registry = yaml.safe_load((REPO / REGISTRY).read_text(encoding="utf-8"))
    assert list(WATCHED_INPUTS) == registry["generation_inputs"]


def test_committed_registry_is_current_in_this_tree() -> None:
    """The live registry regenerates byte-for-byte; needs no git history (depth-1 CI)."""
    result = subprocess.run(
        [sys.executable, str(REPO / "tools/authority/generate_contract_registry.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_generation_is_deterministic(gov_repo: GovRepo) -> None:
    first = gov_repo.generate()
    assert first.returncode == 0, first.stdout
    registry = (gov_repo.root / REGISTRY).read_bytes()
    binding = (gov_repo.root / BINDING_FILE).read_bytes()
    second = gov_repo.generate()
    assert second.returncode == 0, second.stdout
    assert (gov_repo.root / REGISTRY).read_bytes() == registry
    assert (gov_repo.root / BINDING_FILE).read_bytes() == binding


def test_registry_carries_real_digests_and_head_provenance(generated_repo: GovRepo) -> None:
    import yaml

    registry = yaml.safe_load((generated_repo.root / REGISTRY).read_text(encoding="utf-8"))
    head_parent = subprocess.run(
        ["git", "-C", str(generated_repo.root), "rev-parse", "HEAD~1"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert registry["metadata"]["source_commit_sha"] == head_parent
    ids = sorted(c["contract_id"] for c in registry["contracts"])
    assert ids == [
        "L9.GAR.ARCHITECTURAL_INTEGRITY.001",
        "L9.GAR.CONVERGENCE.001",
        "L9.GAR.EPISTEMIC_DISCIPLINE.001",
        "L9.GAR.OUTCOME_OWNERSHIP.001",
        "L9.GAR.WORKFLOW.001",
    ]
    digests = [c["digest"] for c in registry["contracts"]]
    assert all(
        d.startswith("sha256:") and len(d) == 71 and d != "sha256:" + "0" * 64 for d in digests
    )
    assert len(set(digests)) == 5
    assert registry["graph"]["unresolved_refs"] == []
    assert registry["coverage"]["projection_drift_count"] == 0


def test_check_and_provenance_are_current_after_commit(generated_repo: GovRepo) -> None:
    assert generated_repo.run("generate_contract_registry.py", "--check").returncode == 0
    result = generated_repo.run("generate_contract_registry.py", "--check-provenance")
    assert result.returncode == 0, result.stdout


def test_uncommitted_inputs_block_generation(gov_repo: GovRepo) -> None:
    gov_repo.edit(
        EPISTEMIC,
        lambda s: s.replace(
            "title: GAR Epistemic Discipline", "title: GAR Epistemic Discipline!", 1
        ),
    )
    result = gov_repo.generate()
    assert result.returncode == 3
    assert "not committed" in result.stdout


def test_contract_byte_change_is_drift(generated_repo: GovRepo) -> None:
    generated_repo.edit(
        EPISTEMIC,
        lambda s: s.replace(
            "title: GAR Epistemic Discipline", "title: GAR Epistemic Discipline!", 1
        ),
    )
    result = generated_repo.run("generate_contract_registry.py", "--check")
    assert result.returncode == 1
    assert REGISTRY in result.stdout


def test_hand_edited_registry_is_drift(generated_repo: GovRepo) -> None:
    generated_repo.edit(
        REGISTRY, lambda s: s.replace("owner: l9-global-architect", "owner: someone-else", 1)
    )
    result = generated_repo.run("generate_contract_registry.py", "--check")
    assert result.returncode == 1


def test_stray_binding_file_is_drift(generated_repo: GovRepo) -> None:
    stray = (
        generated_repo.root / "generated/governance/projections/L9.GAR.PROJECTION.STRAY.001.yaml"
    )
    stray.write_text((generated_repo.root / BINDING_FILE).read_text(encoding="utf-8"))
    result = generated_repo.run("generate_contract_registry.py", "--check")
    assert result.returncode == 1
    assert "not produced by any declared projection target" in result.stdout


def test_provenance_detects_input_rewritten_after_generation(generated_repo: GovRepo) -> None:
    generated_repo.edit(f"{PACK}/runtime/MANIFEST.yaml", lambda s: s + "# trailing\n")
    generated_repo.commit("unregenerated input change")
    result = generated_repo.run("generate_contract_registry.py", "--check-provenance")
    assert result.returncode == 1
    assert "MANIFEST.yaml differs" in result.stdout


def test_dependency_cycle_is_refused(gov_repo: GovRepo) -> None:
    gov_repo.edit(
        EPISTEMIC,
        lambda s: s.replace(
            "dependencies:\n  requires_contracts: []",
            "dependencies:\n  requires_contracts:\n    - L9.GAR.CONVERGENCE.001",
            1,
        ),
    )
    gov_repo.commit("cycle")
    result = gov_repo.generate()
    assert result.returncode == 1
    assert "REGISTRY-005" in result.stdout


CONVERGENCE = f"{PACK}/contracts/CONVERGENCE.yaml"


def _lifecycle(text: str, field: str, value: str) -> str:
    """Set one lifecycle field (``supersedes: []`` or ``deprecated_by: null``)."""
    if field == "supersedes":
        old, new = "  supersedes: []\n", f"  supersedes:\n    - {value}\n"
    else:
        old, new = "  deprecated_by: null\n", f"  deprecated_by: {value}\n"
    assert old in text, field
    return text.replace(old, new, 1)


def test_reciprocal_supersession_is_not_a_cycle(gov_repo: GovRepo) -> None:
    """B supersedes A and A deprecated_by B are one edge seen from both ends."""
    gov_repo.edit(
        CONVERGENCE, lambda s: _lifecycle(s, "supersedes", "L9.GAR.EPISTEMIC_DISCIPLINE.001")
    )
    gov_repo.edit(EPISTEMIC, lambda s: _lifecycle(s, "deprecated_by", "L9.GAR.CONVERGENCE.001"))
    gov_repo.commit("reciprocal lifecycle")
    result = gov_repo.generate()
    assert result.returncode == 0, result.stdout


def test_supersession_cycle_is_refused(gov_repo: GovRepo) -> None:
    gov_repo.edit(
        CONVERGENCE, lambda s: _lifecycle(s, "supersedes", "L9.GAR.EPISTEMIC_DISCIPLINE.001")
    )
    gov_repo.edit(EPISTEMIC, lambda s: _lifecycle(s, "supersedes", "L9.GAR.CONVERGENCE.001"))
    gov_repo.commit("supersession cycle")
    result = gov_repo.generate()
    assert result.returncode == 1
    assert "GOV-CONTRACT-009" in result.stdout


def test_unresolved_reference_is_refused(gov_repo: GovRepo) -> None:
    gov_repo.edit(
        EPISTEMIC,
        lambda s: s.replace(
            "dependencies:\n  requires_contracts: []",
            "dependencies:\n  requires_contracts:\n    - L9.GAR.NOWHERE.001",
            1,
        ),
    )
    gov_repo.commit("dangling")
    result = gov_repo.generate()
    assert result.returncode == 1
    assert "REGISTRY-004" in result.stdout and "L9.GAR.NOWHERE.001" in result.stdout


def test_schema_invalid_source_is_refused(gov_repo: GovRepo) -> None:
    gov_repo.edit(EPISTEMIC, lambda s: s.replace("tier: constitutional", "tier: supreme", 1))
    gov_repo.commit("bad tier")
    result = gov_repo.generate()
    assert result.returncode == 1
    assert "does not validate" in result.stdout


@pytest.mark.parametrize(
    "tool", ["validate_canonical_contract.py", "validate_projection_parity.py"]
)
def test_missing_tooling_is_capability_block(gov_repo: GovRepo, tool: str) -> None:
    (gov_repo.root / "tools/authority" / tool).unlink()
    gov_repo.commit("no tool")
    result = subprocess.run(
        [
            sys.executable,
            str(gov_repo.root / "tools/authority/generate_contract_registry.py"),
            "--root",
            str(gov_repo.root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "CAPABILITY_BLOCK" in result.stdout or "No such file" in result.stderr


def test_absent_provenance_commit_is_blocked_not_passed(generated_repo: GovRepo) -> None:
    generated_repo.edit(
        REGISTRY,
        lambda s: s.replace(s.split("source_commit_sha: ", 1)[1].split("\n", 1)[0], "f" * 40, 1),
    )
    result = generated_repo.run("generate_contract_registry.py", "--check-provenance")
    assert result.returncode == 3
    assert _status(result) == "BLOCKED"


def test_registry_output_path_is_under_generated(gov_repo: GovRepo) -> None:
    assert not (gov_repo.root / REGISTRY).exists()
    assert gov_repo.generate().returncode == 0
    assert (gov_repo.root / REGISTRY).is_file()
    assert Path(REGISTRY).parts[:2] == ("generated", "governance")
