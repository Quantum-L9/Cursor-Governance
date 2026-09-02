"""Gate D+ — Mission Program Binding production (ADR-0026).

Validate, then identify, then bind, then write outside the Blueprint. Each of
these tests removes one way that ordering could silently break.
"""

from __future__ import annotations

import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from compiler.blueprint_validate import validate
from compiler.intent import parse_intent
from compiler.mission_admission import admit
from compiler.mission_binding import (
    FORBIDDEN_IN_BLUEPRINT_FILENAME,
    MissionBindingError,
    produce_binding,
)
from compiler.repo_truth import RepoTruth
from compiler.resolver import resolve
from compiler.synthesizer import MISSION_CONTEXT_FILENAME, synthesize

PE_ROOT = Path(__file__).resolve().parents[2]
MISSION_ROOT = PE_ROOT / "mission"
FIXTURE = MISSION_ROOT / "tests" / "fixtures" / "valid_mission.yaml"

# APPEND, never insert(0): a module file outranks a namespace directory
# regardless of order (see compiler.mission_admission).
if str(MISSION_ROOT) not in sys.path:
    sys.path.append(str(MISSION_ROOT))

from mission import load_mission, parse_mission  # noqa: E402

BOUND_AT = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)


def _mission(**overrides: object):
    document = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    document.update(overrides)
    return parse_mission(document)


def _truth(root: Path) -> RepoTruth:
    return RepoTruth(
        root=root,
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
        source_priority={"test_command": "prose"},
    )


def _blueprint(tmp_path: Path, mission=None) -> Path:
    intent = parse_intent(
        {"schema": "program-execution.intent.v1", "objective": "Make repo X achieve Y."}
    )
    admission = admit(mission, intent) if mission is not None else None
    resolution = resolve(intent, truth=_truth(tmp_path), admission=admission)
    return synthesize(resolution, tmp_path / "blueprint")


def _bind(mission, root: Path, output_path: Path, **overrides):
    kwargs = {
        "program_id": "PROG-GATEWAY-P1",
        "binding_id": "MPB-GATEWAY-P1",
        "bound_at": BOUND_AT,
        "output_path": output_path,
    }
    kwargs.update(overrides)
    return produce_binding(mission, root, **kwargs)


def test_official_validation_precedes_binding(tmp_path: Path) -> None:
    """An invalid Blueprint has no admissible identity, so nothing is written."""
    mission = load_mission(FIXTURE)
    root = _blueprint(tmp_path, mission)
    (root / "RUNBOOK.md").unlink()
    assert not validate(root, mode="instantiated").ok

    output = tmp_path / "MISSION_BINDING.yaml"
    with pytest.raises(MissionBindingError) as excinfo:
        _bind(mission, root, output)
    assert "validation" in str(excinfo.value)
    assert not output.exists(), "a failed binding must leave no artifact"


def test_stale_blueprint_state_blocks_binding(tmp_path: Path) -> None:
    """A tree edited after the manifest was written is not the Blueprint it claims."""
    mission = load_mission(FIXTURE)
    root = _blueprint(tmp_path, mission)
    (root / "README.md").write_text("edited after the manifest\n", encoding="utf-8")

    output = tmp_path / "MISSION_BINDING.yaml"
    with pytest.raises(MissionBindingError) as excinfo:
        _bind(mission, root, output)
    assert "manifest" in str(excinfo.value).lower()
    assert not output.exists()


def test_binding_pins_exact_mission_and_blueprint_identity(tmp_path: Path) -> None:
    mission = load_mission(FIXTURE)
    root = _blueprint(tmp_path, mission)
    output = tmp_path / "MISSION_BINDING.yaml"

    binding = _bind(mission, root, output)

    # Mission identity comes from the parsed Mission, never from this caller.
    assert binding.mission_id == mission.mission_id
    assert binding.mission_revision == mission.mission_revision
    assert binding.mission_digest == mission.mission_digest

    # Blueprint identity is exactly the canonical manifest-byte digest.
    expected = hashlib.sha256((root / "MANIFEST.yaml").read_bytes()).hexdigest()
    assert binding.blueprint_digest == expected

    document = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert document["schema"] == "l9.program-execution.mission-program-binding.v1"
    assert document["blueprint_digest"] == expected
    assert document["mission_digest"] == mission.mission_digest


def test_binding_output_inside_the_blueprint_is_rejected(tmp_path: Path) -> None:
    """The circular shape ADR-0026 names, refused explicitly."""
    mission = load_mission(FIXTURE)
    root = _blueprint(tmp_path, mission)

    for inside in (
        root / FORBIDDEN_IN_BLUEPRINT_FILENAME,
        root / "schemas" / FORBIDDEN_IN_BLUEPRINT_FILENAME,
    ):
        with pytest.raises(MissionBindingError) as excinfo:
            _bind(mission, root, inside)
        assert "outside the Blueprint digest domain" in str(excinfo.value)
        assert not inside.exists()

    # A symlink into the Blueprint is the same circularity.
    link_parent = tmp_path / "link"
    link_parent.symlink_to(root, target_is_directory=True)
    with pytest.raises(MissionBindingError):
        _bind(mission, root, link_parent / FORBIDDEN_IN_BLUEPRINT_FILENAME)


def test_no_binding_document_enters_the_blueprint_digest_domain(tmp_path: Path) -> None:
    mission = load_mission(FIXTURE)
    root = _blueprint(tmp_path, mission)
    output = tmp_path / "MISSION_BINDING.yaml"
    binding = _bind(mission, root, output)

    assert output.parent == tmp_path
    assert list(root.rglob(FORBIDDEN_IN_BLUEPRINT_FILENAME)) == []

    manifest = yaml.safe_load((root / "MANIFEST.yaml").read_text(encoding="utf-8"))
    covered = {entry["path"] for entry in manifest["files"]}
    assert FORBIDDEN_IN_BLUEPRINT_FILENAME not in covered
    assert MISSION_CONTEXT_FILENAME in covered, "the non-circular projection is covered"

    # Identity is unchanged by the act of binding: the Blueprint does not move.
    assert (
        binding.blueprint_digest
        == hashlib.sha256((root / "MANIFEST.yaml").read_bytes()).hexdigest()
    )


def test_mission_supersession_never_rewrites_an_existing_binding(tmp_path: Path) -> None:
    mission = load_mission(FIXTURE)
    root = _blueprint(tmp_path, mission)
    output = tmp_path / "MISSION_BINDING.yaml"
    first = _bind(mission, root, output)

    superseding = _mission(mission_revision=2)
    assert superseding.mission_digest != mission.mission_digest

    with pytest.raises(MissionBindingError) as excinfo:
        _bind(superseding, root, output, binding_id="MPB-GATEWAY-P1-R2")
    assert "immutable" in str(excinfo.value)

    still = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert still["mission_revision"] == first.mission_revision == 1
    assert still["mission_digest"] == mission.mission_digest

    # A new Program gets a new binding, at its own path.
    second = _bind(
        superseding,
        root,
        tmp_path / "MISSION_BINDING_R2.yaml",
        binding_id="MPB-GATEWAY-P2",
        program_id="PROG-GATEWAY-P2",
    )
    assert second.mission_revision == 2
    assert second.blueprint_digest == first.blueprint_digest


def test_caller_cannot_supply_mission_identity_or_skip_parsing(tmp_path: Path) -> None:
    mission = load_mission(FIXTURE)
    root = _blueprint(tmp_path, mission)
    output = tmp_path / "MISSION_BINDING.yaml"

    raw = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    raw["mission_digest"] = "f" * 64
    with pytest.raises(MissionBindingError):
        _bind(raw, root, output)
    assert not output.exists()

    with pytest.raises(MissionBindingError):
        _bind(mission, tmp_path / "not-a-blueprint", output)
    assert not output.exists()


def test_binding_is_impossible_for_an_unvalidatable_root(tmp_path: Path) -> None:
    """No Blueprint, no identity, no binding — and no partially written file."""
    mission = load_mission(FIXTURE)
    empty = tmp_path / "empty"
    empty.mkdir()
    output = tmp_path / "MISSION_BINDING.yaml"

    with pytest.raises(MissionBindingError):
        _bind(mission, empty, output)
    assert not output.exists()
