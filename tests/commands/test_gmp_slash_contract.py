"""Slash command contract for /gmp — last steps Shell executor then Build."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GMP_CMD = ROOT / "commands" / "gmp.md"
SKILL = ROOT / "skills" / "l9-gmp-protocol" / "SKILL.md"


def test_gmp_command_has_no_ynp_chain_or_stale_executor_path() -> None:
    text = GMP_CMD.read_text(encoding="utf-8")
    assert "auto_chain: ynp" not in text
    assert "dag_executor" not in text
    assert "workflows-synced" not in text
    exec_idx = text.index("EXECUTION (MANDATORY)")
    execution = text[exec_idx:]
    assert "do not ask" in execution.lower()
    assert "gmp_executor.py" in execution
    assert "--mode start" in execution
    assert "Build" in execution
    assert "--mode finalize" in execution


def test_gmp_skill_has_no_stale_executor_path() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert "workflows-synced" not in text
    assert "dag_executor" not in text
    assert "auto_chain: ynp" not in text
    assert "workflows/gmp_executor.py" in text


def test_gmp_executor_does_not_import_pe_autonomy_contracts() -> None:
    source = (ROOT / "workflows" / "gmp_executor.py").read_text(encoding="utf-8")
    assert "environment.contracts.autonomy" not in source
    assert "environment/contracts/autonomy" not in source
