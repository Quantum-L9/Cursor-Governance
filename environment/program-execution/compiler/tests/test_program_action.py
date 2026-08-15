"""Program action resolution: create | extend | supersede (contract §14)."""

from __future__ import annotations

from compiler.program_action import decide

EXISTING = [
    {
        "id": "pe-existing",
        "objective": "Evolve the compiler so a minimal goal compiles into a validated Blueprint.",
        "targets": [{"repository_id": "Quantum-L9/Cursor-Governance"}],
        "governing_authority": {"policy_profile": "quantum-l9.safe-autonomy.v1"},
    }
]


def _resolution(
    objective: str, targets: list[str] | None = None, profile: str | None = None
) -> dict:
    return {
        "intent": {"normalized_objective": objective},
        "targets": [{"repository_id": t} for t in (targets or ["Quantum-L9/Cursor-Governance"])],
        "governing_authority": {"policy_profile": profile or "quantum-l9.safe-autonomy.v1"},
    }


def test_create_when_nothing_governs() -> None:
    action = decide([], _resolution("Make repo X achieve Y."))
    assert action["mode"] == "create"
    assert action["parent_program_ref"] is None


def test_extend_when_within_accepted_scope() -> None:
    action = decide(
        EXISTING,
        _resolution(
            "Evolve the compiler so a minimal goal compiles into a validated Blueprint with tests."
        ),
    )
    assert action["mode"] == "extend"
    assert action["parent_program_ref"] == "pe-existing"


def test_supersede_on_material_objective_change() -> None:
    action = decide(
        EXISTING,
        _resolution(
            "Evolve the compiler into a validated Blueprint generator with a "
            "totally different architecture."
        ),
    )
    assert action["mode"] == "supersede"


def test_supersede_on_target_change() -> None:
    action = decide(
        EXISTING,
        _resolution(
            "Evolve the compiler so a minimal goal compiles into a validated Blueprint.",
            targets=["Quantum-L9/other-repo"],
        ),
    )
    assert action["mode"] == "supersede"


def test_supersede_on_profile_change() -> None:
    action = decide(
        EXISTING,
        _resolution(
            "Evolve the compiler so a minimal goal compiles into a validated Blueprint.",
            profile="quantum-l9.strict-autonomy.v1",
        ),
    )
    assert action["mode"] == "supersede"


def test_no_silent_mutation_of_locked_program() -> None:
    """A locked program is never mutated: it is replaced with an explicit parent ref."""
    action = decide(
        EXISTING,
        _resolution(
            "Evolve the compiler into a validated Blueprint generator with a "
            "totally different architecture."
        ),
    )
    assert action["mode"] == "supersede"
    assert action["parent_program_ref"] == "pe-existing"
