"""GAR product architecture decision validator: schema v3 acceptance and rejection."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PACK = REPO / "skills" / "l9-global-architect"
VALIDATOR = PACK / "scripts" / "validate_product_architecture_decision.py"
FIXTURE = PACK / "fixtures" / "greenfield-decision.json"


def _run(decision: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(decision)],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def test_greenfield_fixture_is_accepted() -> None:
    decision = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert decision["schema"] == "l9.gar.product-architecture-decision/v3"
    proc = _run(FIXTURE)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "GAR_PRODUCT_ARCHITECTURE_DECISION: PASS" in proc.stdout


def _deprecated_disposition(decision: dict) -> None:
    decision["architecture"]["owner_dispositions"][0]["disposition"] = "HARVEST_THEN_DECIDE"


def _intervention_mismatch(decision: dict) -> None:
    decision["architecture"]["intervention_class"] = "NO_ACTION"


def _signal_unbound(decision: dict) -> None:
    decision["reasoning"]["signal_prediction_propagation_ref"] = None


def _accepted_with_unknowns(decision: dict) -> None:
    decision["architecture"]["material_unknowns"] = ["unresolved"]


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        pytest.param(_deprecated_disposition, "GAR_DECISION_INVALID", id="harvest-then-decide"),
        pytest.param(_intervention_mismatch, "GAR_DECISION_INTERVENTION_FIDELITY", id="fidelity"),
        pytest.param(_signal_unbound, "GAR_DECISION_SIGNAL_UNBOUND", id="signal-unbound"),
        pytest.param(_accepted_with_unknowns, "GAR_DECISION_UNRESOLVED", id="unknowns"),
    ],
)
def test_invalid_decisions_are_rejected(tmp_path: Path, mutate, code: str) -> None:
    decision = json.loads(FIXTURE.read_text(encoding="utf-8"))
    mutate(decision)
    path = tmp_path / "decision.json"
    path.write_text(json.dumps(decision), encoding="utf-8")
    proc = _run(path)
    assert proc.returncode == 1, proc.stdout
    assert "GAR_PRODUCT_ARCHITECTURE_DECISION: FAIL" in proc.stdout
    assert code in proc.stdout
