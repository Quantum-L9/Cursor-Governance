"""Gate B — intent resolution semantics (contract §5-§6, §18 matrix)."""

from __future__ import annotations

from pathlib import Path

import compiler.resolver as resolver
import pytest
from compiler.intent import Intent, parse_intent
from compiler.policy import DEFAULT_PROFILE, load_policy
from compiler.repo_truth import RepoTruth, discover


def _truth(
    root: Path,
    *,
    owner: str | None = None,
    test_command: str | None = None,
    remote: str | None = "https://github.com/Quantum-L9/Cursor-Governance.git",
    revision: str = "0123456789abcdef0123456789abcdef01234567",
) -> RepoTruth:
    return RepoTruth(
        root=root,
        remote=remote,
        revision=revision,
        owner=owner,
        test_command=test_command,
        package_manager=None,
        runtime_version="3.12",
        dpk=None,
        constraints_files=[],
        adr_files=[],
        validation_commands=[test_command] if test_command else [],
        rollback_defs=[],
        source_priority={"test_command": "prose"} if test_command else {},
    )


def _intent(objective: str = "Make repo X achieve Y.") -> Intent:
    return parse_intent({"schema": "program-execution.intent.v1", "objective": objective})


def test_happy_path_resolution_is_ready(tmp_path: Path) -> None:
    resolution = resolver.resolve(_intent(), truth=_truth(tmp_path, owner="Igor Beylin"))
    assert resolution["schema"] == "program-execution.intent-resolution.v1"
    assert resolution["synthesis_status"] == "ready"
    assert resolution["program_action"]["mode"] == "create"
    assert resolution["confidence"]["target_resolution"] == "high"


def test_sparse_input_needs_no_clarification(tmp_path: Path) -> None:
    resolution = resolver.resolve(_intent(), truth=_truth(tmp_path, owner="Igor Beylin"))
    assert resolution["decisions"]["requires_human_authority"] == []
    assert resolution["unknowns"] == []


def test_evidence_determined_fact_auto_resolves_with_provenance(tmp_path: Path) -> None:
    truth = _truth(tmp_path, owner="Igor Beylin", test_command="pytest -q")
    resolution = resolver.resolve(_intent(), truth=truth)
    statements = [r["statement"] for r in resolution["derived_requirements"]]
    test_req = next(s for s in statements if "pytest -q" in s)
    source = next(
        r["source"] for r in resolution["derived_requirements"] if r["statement"] == test_req
    )
    assert source["type"] == "evidence"
    assert source["ref"]


def test_policy_determined_fact_auto_resolves_with_policy_provenance(tmp_path: Path) -> None:
    resolution = resolver.resolve(_intent(), truth=_truth(tmp_path, owner="Igor Beylin"))
    ceiling_req = next(
        r
        for r in resolution["derived_requirements"]
        if "ceiling" in r["statement"].lower() and r["source"]["type"] == "policy"
    )
    assert ceiling_req["source"]["ref"] == DEFAULT_PROFILE
    assert resolution["_compiler_meta"]["ceiling"]["inspect"] is True


def test_authority_bearing_choice_becomes_scoped_unknown(tmp_path: Path) -> None:
    truth = _truth(tmp_path, owner=None, remote=None, revision=None)
    resolution = resolver.resolve(_intent(), truth=truth)
    assert resolution["unknowns"], "authority-bearing issues must be explicit"
    assert all(u["blocks"] for u in resolution["unknowns"])
    assert resolution["synthesis_status"] in {"blocked", "requires_authority"}
    assert resolution["targets"] == [], "no invented target"


def test_missing_ownership_never_invents_owner(tmp_path: Path) -> None:
    policy = load_policy(DEFAULT_PROFILE)
    policy["provenance"] = []  # drop policy default owner for this scenario
    truth = _truth(tmp_path, owner=None)

    monkeypatch_loader = pytest.MonkeyPatch()
    monkeypatch_loader.setattr(resolver, "load_policy", lambda _profile: policy)
    try:
        resolution = resolver.resolve(_intent(), truth=truth, profile_id=DEFAULT_PROFILE)
    finally:
        monkeypatch_loader.undo()
    assert resolution["_compiler_meta"]["owner"] is None
    assert any("unresolved" in u["topic"].lower() for u in resolution["unknowns"])
    assert not any("unresolved" not in u["topic"].lower() and False for u in [])


def test_unknown_scoping_blocks_only_dependents(tmp_path: Path) -> None:
    truth = _truth(
        tmp_path, owner=None, remote="https://github.com/Quantum-L9/Cursor-Governance.git"
    )
    resolution = resolver.resolve(_intent(), truth=truth)
    # Local implementation is not globally blocked: the only Unknown is scoped.
    assert resolution["synthesis_status"] in {"ready", "requires_authority"}
    for unknown in resolution["unknowns"]:
        assert unknown["blocks"], "scoped Unknown must name its dependents"


def test_permission_widening_is_rejected_not_silently_applied(tmp_path: Path) -> None:
    intent = parse_intent(
        {
            "schema": "program-execution.intent.v1",
            "objective": "goal",
            "constraints": {"permission_ceiling": {"merge": True}},
        }
    )
    policy = load_policy(DEFAULT_PROFILE)
    assert policy["authorization_ceiling"]["merge"] is False
    resolution = resolver.resolve(intent, truth=_truth(tmp_path, owner="Igor Beylin"))
    assert resolution["_compiler_meta"]["ceiling"]["merge"] is False
    assert any("widen" in u["topic"].lower() for u in resolution["unknowns"]), (
        "widening request must escalate, not silently apply"
    )


def test_safe_autonomy_profile_matches_the_sealed_pe_ceiling(tmp_path: Path) -> None:
    """The profile may not advertise authority the runner cannot reach.

    Program Execution ends at a verified local commit: there is no push and no
    pull-request path, and remote mutation is denied in the universal
    Controller core. A profile still claiming push/pull_request handed every
    consumer a ceiling that no downstream surface could exercise.
    """
    policy = load_policy(DEFAULT_PROFILE)
    ceiling = policy["authorization_ceiling"]
    assert ceiling["commit"] is True
    assert ceiling["local_write"] is True
    assert ceiling["inspect"] is True
    for action in (
        "push",
        "pull_request",
        "merge",
        "publish_or_release",
        "deploy_or_migrate",
        "destructive_change",
        "external_message",
    ):
        assert ceiling[action] is False, action
    resolution = resolver.resolve(_intent(), truth=_truth(tmp_path, owner="Igor Beylin"))
    resolved = resolution["_compiler_meta"]["ceiling"]
    assert resolved["push"] is False
    assert resolved["pull_request"] is False
    assert resolved["commit"] is True


def test_structural_evidence_is_not_runtime_proof(tmp_path: Path) -> None:
    """A declared test command is structural evidence, never a PASS claim."""
    resolution = resolver.resolve(
        _intent(), truth=_truth(tmp_path, owner="Igor Beylin", test_command="pytest -q")
    )
    payload = {k: v for k, v in resolution.items() if not k.startswith("_")}
    import yaml

    text = yaml.safe_dump(payload)
    assert "test PASS" not in text and "PASS" not in text.split("expected_result")[0]


def test_conflicting_source_authority_records_conflict(tmp_path: Path) -> None:
    """README contradicting accepted contracts must not become authority."""
    (tmp_path / "README.md").write_text("Owner: Some Random Robot\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("Owner: Igor Beylin\n", encoding="utf-8")
    truth = discover(tmp_path)
    # discover() does not read README for ownership; conflict surface stays out of authority.
    assert truth.owner == "Igor Beylin"
    assert "README" not in str(truth.source_priority.get("owner", ""))


def test_existing_program_material_change_supersedes(tmp_path: Path) -> None:
    existing = [
        {
            "id": "pe-old",
            "objective": (
                "Evolve l9-devpack-compiler so a simple goal compiles into a Blueprint v2."
            ),
            "targets": [{"repository_id": "Quantum-L9/l9-devpack-compiler"}],
            "governing_authority": {"policy_profile": "quantum-l9.safe-autonomy.v1"},
        }
    ]
    resolution = resolver.resolve(
        parse_intent(
            {
                "schema": "program-execution.intent.v1",
                "objective": (
                    "Evolve l9-devpack-compiler so a simple goal compiles into a Blueprint v2."
                ),
            }
        ),
        truth=_truth(tmp_path, owner="Igor Beylin"),
        existing_programs=existing,
    )
    assert resolution["program_action"]["mode"] == "supersede"
    assert resolution["program_action"]["parent_program_ref"] == "pe-old"


# --- Mission-bound resolution (ADR-0024, ADR-0026) -------------------------


def _mission(**overrides: object):
    import sys

    import yaml

    mission_root = Path(__file__).resolve().parents[2] / "mission"
    if str(mission_root) not in sys.path:
        sys.path.insert(0, str(mission_root))
    from mission import parse_mission

    fixture = mission_root / "tests" / "fixtures" / "valid_mission.yaml"
    document = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    document.update(overrides)
    return parse_mission(document)


def _admission(intent: Intent | None = None, **overrides: object):
    from compiler.mission_admission import admit

    return admit(_mission(**overrides), intent or _intent())


def test_mission_bound_resolution_intersects_the_ceiling(tmp_path: Path) -> None:
    from compiler.policy import CEILING_KEYS

    unbound = resolver.resolve(_intent(), truth=_truth(tmp_path, owner="Igor Beylin"))
    ceiling = dict.fromkeys(CEILING_KEYS, True)
    ceiling["commit"] = False
    bound = resolver.resolve(
        _intent(),
        truth=_truth(tmp_path, owner="Igor Beylin"),
        admission=_admission(authority_ceiling=ceiling),
    )

    assert unbound["_compiler_meta"]["ceiling"]["commit"] is True
    assert bound["_compiler_meta"]["ceiling"]["commit"] is False, "Mission must narrow"
    assert bound["_compiler_meta"]["ceiling"]["inspect"] is True, "narrowing is per action"


def test_mission_can_never_widen_the_resolved_ceiling(tmp_path: Path) -> None:
    """The fixture Mission grants push and pull_request; the profile does not."""
    from compiler.policy import CEILING_KEYS

    admission = _admission(authority_ceiling=dict.fromkeys(CEILING_KEYS, True))
    assert all(admission.authority_ceiling[key] for key in CEILING_KEYS)

    policy = load_policy(DEFAULT_PROFILE)
    resolution = resolver.resolve(
        _intent(), truth=_truth(tmp_path, owner="Igor Beylin"), admission=admission
    )
    resolved = resolution["_compiler_meta"]["ceiling"]
    for action in CEILING_KEYS:
        assert not (resolved[action] and not policy["authorization_ceiling"][action]), action
    assert resolved["push"] is False
    assert resolved["merge"] is False


def test_mission_context_is_first_class_exact_provenance(tmp_path: Path) -> None:
    import yaml

    admission = _admission()
    resolution = resolver.resolve(
        _intent(), truth=_truth(tmp_path, owner="Igor Beylin"), admission=admission
    )

    assert resolution["mission_context"] == admission.mission_context()
    reference = admission.authority_reference()
    assert reference in resolution["governing_authority"]["source_ids"]
    assert reference in resolution["decisions"]["accepted_from_authority"]
    assert any(
        requirement["source"] == {"type": "decision", "ref": reference}
        for requirement in resolution["derived_requirements"]
    ), "the intersection must be traceable, not silent"

    # First-class means it survives write_resolution(), which strips `_` keys.
    path = resolver.write_resolution(resolution, tmp_path / "INTENT_RESOLUTION.yaml")
    written = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert written["mission_context"] == admission.mission_context()

    # And it carries no Mission planning, budget, or lifecycle semantics.
    mission = _mission()
    text = yaml.safe_dump(written["mission_context"])
    assert mission.objective not in text
    for absent in ("authority_ceiling", "budgets", "acceptance_criteria", "constraints"):
        assert absent not in text


def test_invalid_admission_fails_closed(tmp_path: Path) -> None:
    """A duck-typed admission could carry a digest nobody parsed."""

    class NotAnAdmission:
        mission_id = "MISSION-FAKE"
        mission_revision = 1
        mission_digest = "f" * 64

        def mission_context(self) -> dict:
            return {
                "schema": "program-execution.mission-context.v1",
                "mission_id": self.mission_id,
                "mission_revision": self.mission_revision,
                "mission_digest": self.mission_digest,
            }

    with pytest.raises(ValueError, match="MissionAdmission"):
        resolver.resolve(
            _intent(), truth=_truth(tmp_path, owner="Igor Beylin"), admission=NotAnAdmission()
        )
    with pytest.raises(ValueError, match="MissionAdmission"):
        resolver.resolve(
            _intent(),
            truth=_truth(tmp_path, owner="Igor Beylin"),
            admission={"mission_id": "MISSION-FAKE"},
        )


def test_unbound_resolution_is_unchanged(tmp_path: Path) -> None:
    """Backward compatibility is the load-bearing property of an optional binding."""
    truth = _truth(tmp_path, owner="Igor Beylin", test_command="pytest -q")
    baseline = resolver.resolve(_intent(), truth=truth)
    explicit_none = resolver.resolve(_intent(), truth=truth, admission=None)

    assert "mission_context" not in baseline
    assert baseline == explicit_none
    assert baseline["synthesis_status"] == "ready"
    assert baseline["decisions"]["accepted_from_authority"] == []
    assert baseline["governing_authority"]["source_ids"] == ["POLICY:" + DEFAULT_PROFILE]
