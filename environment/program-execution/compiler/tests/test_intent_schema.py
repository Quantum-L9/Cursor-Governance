"""Gate A — program-execution.intent.v1 contract tests (contract §4, §18)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from compiler.intent import parse_intent, parse_intent_file

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_minimal_valid_input_is_genuinely_minimal() -> None:
    """Happy path + sparse input: only objective (and target) are supplied."""
    intent = parse_intent(
        {"schema": "program-execution.intent.v1", "objective": "Make repo X achieve Y."}
    )
    assert intent.objective == "Make repo X achieve Y."
    assert intent.targets == ()
    assert intent.policy_profile is None


def test_minimal_fixture_validates() -> None:
    intent = parse_intent_file(FIXTURES / "minimal-intent.yaml")
    assert intent.targets == ("Quantum-L9/Cursor-Governance",)
    assert intent.policy_profile == "quantum-l9.safe-autonomy.v1"


def test_implementation_prescribing_input_is_rejected() -> None:
    """User fields describe outcome/authority, not implementation."""
    with pytest.raises(ValueError, match="violates program-execution.intent.v1"):
        parse_intent_file(FIXTURES / "implementation-prescribing-intent.yaml")


@pytest.mark.parametrize(
    "extra",
    [
        {"tasks": ["write code"]},
        {"files": ["src/main.py"]},
        {"execution_waves": ["w0"]},
        {"worker_prompts": ["do it"]},
        {"test_commands": ["pytest"]},
    ],
)
def test_each_implementation_prescription_is_rejected(extra: dict) -> None:
    raw: dict = {"schema": "program-execution.intent.v1", "objective": "goal", **extra}
    with pytest.raises(ValueError, match="violates program-execution.intent.v1"):
        parse_intent(raw)


def test_schema_requires_objective() -> None:
    with pytest.raises(ValueError, match="violates program-execution.intent.v1"):
        parse_intent({"schema": "program-execution.intent.v1"})


def test_constraints_narrowing_shape_is_accepted() -> None:
    intent = parse_intent(
        {
            "schema": "program-execution.intent.v1",
            "objective": "goal",
            "constraints": {"permission_ceiling": {"merge": False}},
        }
    )
    assert intent.constraints == {"permission_ceiling": {"merge": False}}


def test_fixture_yaml_round_trips_schema_name() -> None:
    data = yaml.safe_load((FIXTURES / "minimal-intent.yaml").read_text(encoding="utf-8"))
    assert data["schema"] == "program-execution.intent.v1"
