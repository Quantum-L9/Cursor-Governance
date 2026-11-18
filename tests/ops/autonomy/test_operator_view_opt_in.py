"""Opt-in operator view. Activation defaults stay false."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import operator_alignment  # noqa: E402

from ops.autonomy.projection_mode import ProjectionMode  # noqa: E402


def _activation_block(name: str) -> str:
    text = (REPO / "governance" / name / "MODE.yaml").read_text(encoding="utf-8")
    return text.split("activation:", 1)[1].split("\n\n", 1)[0]


def test_planner_and_cto_defaults_stay_off() -> None:
    planner = _activation_block("planner-mode")
    cto = _activation_block("cto-mode")
    assert "default: false" in planner
    assert "default: off" in cto
    assert "always_enabled: false" in planner
    assert "always_enabled: false" in cto


def test_opt_in_cites_only_the_admitted_receipt(tmp_path: Path) -> None:
    receipt = tmp_path / "receipt"
    receipt.write_bytes(next(iter(operator_alignment.ADMITTED_PRODUCER_RECEIPTS)))
    mode = ProjectionMode.__new__(ProjectionMode)
    assert mode.cite_operator_view(receipt) == operator_alignment.ADMITTED
    other = tmp_path / "other"
    other.write_bytes(b"not-the-receipt")
    assert mode.cite_operator_view(other) == operator_alignment.FORGED_VIEW
