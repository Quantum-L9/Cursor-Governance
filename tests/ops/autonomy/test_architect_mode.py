"""Architect mode: opt-in binding of the architecture and strategic-planning domain projections."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import architect_mode  # noqa: E402
import cto_mode  # noqa: E402

SID = "session-a"
# The union of the required domains of l9.domain-consumer-binding/gar@1 and
# l9.domain-consumer-binding/strategic-planner@1 (Quantum-L9/.github v3.36.0, ADR-033).
GAR_REQUIRED = [
    "architecture",
    "governance",
    "evidence-provenance",
    "contracts-conformance",
    "capabilities-dependencies",
]
PLANNER_ADDED = ["strategic-value", "signals"]
SELECTED = [f"l9.projection/{n}@1" for n in GAR_REQUIRED + PLANNER_ADDED]


@pytest.fixture(autouse=True)
def _no_ambient_session(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in architect_mode.SESSION_ENVS:
        monkeypatch.delenv(name, raising=False)


def _verify(status: str):
    def verify(_binding: Path, _root: Path | None) -> dict:
        return {
            "status": status,
            "reason": "ADMITTED" if status == architect_mode.ADMITTED else "X",
        }

    return verify


def test_contract_is_opt_in_and_selects_the_canonical_union() -> None:
    doc = architect_mode.load_contract()
    assert doc["activation"]["default"] is False
    assert doc["activation"]["always_enabled"] is False
    assert doc["activation"]["repository_presence_alone_activates"] is False
    projections = doc["selection"]["projections"]
    assert [p["ref"] for p in projections] == SELECTED
    assert all(p["required"] is True for p in projections)
    refs = {p["ref"] for p in projections}
    assert "l9.projection/cursor-governance-operating-plane@2" not in refs
    assert "l9.projection/identity-attribution@1" not in refs


@pytest.mark.parametrize("ref", SELECTED)
def test_each_binding_pins_its_committed_bundle_and_records_admission(ref: str) -> None:
    entry = next(
        p for p in architect_mode.load_contract()["selection"]["projections"] if p["ref"] == ref
    )
    binding = yaml.safe_load((REPO / entry["binding"]).read_text())
    pins = binding["input"]["authority"]
    lock = json.loads((REPO / binding["input"]["bundle"]["path"] / "bundle.lock.json").read_text())
    assert lock["projection_profile"] == {
        "ref": ref,
        "digest": pins["projection_profile_digest"],
    }
    assert lock["composition_profile"] == {
        "ref": pins["composition_profile_ref"],
        "digest": pins["composition_profile_digest"],
    }
    assert [c["source_class"] for c in lock["components"]] == pins["expected_source_classes"]
    decided = {
        (d["candidate_ref"], d["candidate_digest"]) for d in binding["admission"]["decisions"]
    }
    assert decided == {
        (ref, pins["projection_profile_digest"]),
        (pins["composition_profile_ref"], pins["composition_profile_digest"]),
    }
    assert binding["load_condition"]["repository_presence_alone_loads"] is False


def test_bundles_are_registered_with_the_producer() -> None:
    sys.path.insert(0, str(REPO / "tools" / "authority"))
    import produce_projection_bundle as producer

    for ref in SELECTED:
        name = ref.split("/")[1].split("@")[0]
        assert producer.BUNDLES[ref] == {
            "composition_profile": f"l9.compose/{name}@1",
            "output": Path(f"generated/governance/domain_{name.replace('-', '_')}"),
        }


def test_off_by_default(tmp_path: Path) -> None:
    report = architect_mode.evaluate(
        tmp_path, verify=_verify(architect_mode.ADMITTED), session_id=SID
    )
    assert report["mode"] == "OFF"


def test_active_loads_every_composed_view(tmp_path: Path) -> None:
    architect_mode.request(tmp_path, session_id=SID)
    report = architect_mode.evaluate(
        tmp_path, verify=_verify(architect_mode.ADMITTED), session_id=SID
    )
    assert report["mode"] == "ACTIVE"
    assert [item["ref"] for item in report["load"]] == SELECTED
    assert all(Path(item["composed_view"]).is_file() for item in report["load"])


def test_one_unadmitted_domain_blocks_the_mode(tmp_path: Path) -> None:
    architect_mode.request(tmp_path, session_id=SID)

    def verify(binding: Path, root: Path | None) -> dict:
        status = "STALE" if binding.name == "signals.yaml" else architect_mode.ADMITTED
        return {"status": status, "reason": status}

    report = architect_mode.evaluate(tmp_path, verify=verify, session_id=SID)
    assert report["mode"] == "BLOCKED"
    assert [b["ref"] for b in report["blockers"]] == ["l9.projection/signals@1"]
    assert report["load"] == []


def test_modes_keep_separate_state(tmp_path: Path) -> None:
    architect_mode.request(tmp_path, session_id=SID)
    assert (tmp_path / ".l9/architect-mode/session.json").is_file()
    cto = cto_mode.evaluate(tmp_path, verify=_verify(cto_mode.ADMITTED), session_id=SID)
    assert cto["mode"] == "OFF"
    assert architect_mode.release(tmp_path) is True
    assert not (tmp_path / ".l9/cto-mode").exists()


def test_cli_without_authority_checkout_blocks_admission(tmp_path: Path) -> None:
    script = REPO / "ops/autonomy/architect_mode.py"
    on = subprocess.run(
        [sys.executable, str(script), "on", "--workspace", str(tmp_path), "--session-id", SID],
        capture_output=True,
        text=True,
        check=False,
    )
    report = json.loads(on.stdout)
    # Admission is resolved against an authority checkout; without one nothing is loaded.
    assert on.returncode == 3, on.stdout + on.stderr
    assert report["mode"] == "BLOCKED"
    assert {p["reason"] for p in report["projections"]} == {"AUTHORITY_ROOT_REQUIRED"}
    assert report["load"] == []
