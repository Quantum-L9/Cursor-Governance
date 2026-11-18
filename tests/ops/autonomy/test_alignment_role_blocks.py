"""Privacy and Meta Planner stay blocked after the producer receipt exists."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import operator_alignment  # noqa: E402


def test_coding_agent_stays_blocked_when_strategy_is_readable(tmp_path: Path) -> None:
    root = tmp_path / "dot-github"
    strategy = root / "strategy"
    strategy.mkdir(parents=True)
    (strategy / "OPERATOR_DOCTRINE.yaml").write_text("sealed\n", encoding="utf-8")
    result = operator_alignment.coding_agent_confidentiality(root, claimed="PASS")
    assert result == operator_alignment.BLOCKED_PRIVACY


def test_meta_planner_stays_blocked() -> None:
    assert operator_alignment.meta_planner_status() == operator_alignment.BLOCKED_NO_CONSUMER
