"""Gate D — official Blueprint v2 validation through the adapter (contract §13)."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from compiler.blueprint_validate import validate, validate_or_repair
from compiler.intent import parse_intent
from compiler.repo_truth import RepoTruth
from compiler.resolver import resolve
from compiler.synthesizer import synthesize


def _synthesize(tmp_path: Path) -> Path:
    truth = RepoTruth(
        root=tmp_path,
        remote="https://github.com/Quantum-L9/Cursor-Governance.git",
        revision="0123456789abcdef0123456789abcdef01234567",
        owner="Igor Beylin",
        test_command="pytest -q",
        package_manager=None,
        runtime_version="3.12",
        dpk=None,
        constraints_files=[],
        adr_files=[],
        validation_commands=["pytest -q"],
        rollback_defs=[],
        source_priority={},
    )
    resolution = resolve(
        parse_intent(
            {
                "schema": "program-execution.intent.v1",
                "objective": "Make repository X achieve Y and keep going until verified.",
            }
        ),
        truth=truth,
    )
    output = tmp_path / "blueprint"
    synthesize(resolution, output)
    return output


def test_representative_program_passes_official_validator_as_template(tmp_path: Path) -> None:
    root = _synthesize(tmp_path)
    result = validate(root, mode="template")
    assert result.ok, "\n".join(result.errors)


def test_synthesizer_never_accepts_its_own_program(tmp_path: Path) -> None:
    """Acceptance is `accept_blueprint`'s decision against bound evidence.

    The synthesizer used to stamp `definition_status: accepted` itself, so an
    instantiated validation passed on a tree nobody had accepted and that
    carried no ACCEPTANCE_RECEIPT.
    """
    root = _synthesize(tmp_path)
    program = yaml.safe_load((root / "PROGRAM.yaml").read_text(encoding="utf-8"))
    assert program["program"]["definition_status"] == "draft"
    assert not (root / "ACCEPTANCE_RECEIPT.yaml").exists()
    assert not validate(root, mode="instantiated").ok, "a draft is not executable"

    scripts = Path(__file__).resolve().parents[2] / "scripts"
    collect = _load_script("cp_f5_collect_evidence", scripts / "collect_evidence.py")
    accept = _load_script("cp_f5_accept_blueprint", scripts / "accept_blueprint.py")
    collect.collect_evidence(
        root,
        evidence_id="EVID-001",
        revision="0123456789abcdef0123456789abcdef01234567",
        digest=None,
        notes="test",
        producer="test",
        expires_at=None,
    )
    accepted = accept.accept_blueprint(root, actor="test", evidence_ids=["EVID-001"])
    assert accepted["status"] == "ACCEPTED"
    result = validate(root, mode="instantiated")
    assert result.ok, "\n".join(result.errors)


def _load_script(name: str, path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_negative_program_fails_for_expected_reason(tmp_path: Path) -> None:
    root = _synthesize(tmp_path)
    (root / "TASK_CARDS.yaml").unlink()
    result = validate(root, mode="template")
    assert not result.ok
    assert any("missing required file" in e and "TASK_CARDS" in e for e in result.errors)


def test_malformed_synthesis_bounded_repair_or_explicit_blocker(tmp_path: Path) -> None:
    root = _synthesize(tmp_path)
    # Drift the manifest: deterministic non-authority issue -> bounded repair.
    manifest = root / "MANIFEST.yaml"
    text = manifest.read_text(encoding="utf-8")
    manifest.write_text(text.replace("sha256:", "sha256: deadbeef", 1), encoding="utf-8")
    result = validate_or_repair(root, mode="template", repair_attempts=1)
    assert result.ok, "manifest drift should be repaired within the bounded budget"
    # A defect repair cannot fix (placeholder injection) -> explicit blocker.
    program = root / "PROGRAM.yaml"
    program.write_text(
        program.read_text(encoding="utf-8").replace(
            "definition_status: draft", "definition_status: REPLACE_WITH_STATUS", 1
        ),
        encoding="utf-8",
    )
    result = validate_or_repair(root, mode="template", repair_attempts=1)
    assert not result.ok
    joined = "\n".join(result.errors)
    assert ("schema violation" in joined) or ("unresolved placeholder" in joined)


def test_validator_is_the_official_one(tmp_path: Path) -> None:
    from compiler.blueprint_validate import VALIDATOR

    assert VALIDATOR.name == "validate_blueprint.py"
    assert "program-execution-blueprint-template" in str(VALIDATOR)
