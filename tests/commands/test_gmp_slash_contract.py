"""Slash command contract for /gmp — last steps Shell executor then Build."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GMP_CMD = ROOT / "commands" / "gmp.md"


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


def test_gmp_command_targets_the_caller_clone() -> None:
    text = GMP_CMD.read_text(encoding="utf-8")
    assert 'GOV_EXEC="${GOV}/workflows/gmp_executor.py"' in text
    assert 'GOV="${HOME}/.cursor-governance"' in text
    assert 'WORK="$(git rev-parse --show-toplevel)" || exit 1' in text
    assert 'PR_REMEDIATE=0 make -C "$GOV" pr WS="$WORK"' in text
    assert '--workspace "$WORK" authorize-release' in text
    assert '"$GOV_PY" workflows/gmp_executor.py' not in text
    assert "$(pwd)/.venv/bin/python" not in text
    invocations = [line for line in text.splitlines() if line.startswith('"$GOV_PY" "$GOV_EXEC"')]
    assert len(invocations) == 4, invocations
    blocks = text.split('"$GOV_PY" "$GOV_EXEC"')[1:]
    for block in blocks:
        assert '--workspace "$WORK"' in block.split("```", 1)[0], block[:200]


def test_gmp_command_carries_run_contract() -> None:
    text = GMP_CMD.read_text(encoding="utf-8")
    assert "## Run contract" in text
    assert "snapshot_digest" in text
    assert "PR_REMEDIATE=0 make pr" in text
    assert "l9 pr" in text
    assert "<episode names>" not in text
    assert "l9-gmp-protocol" not in text


def test_gmp_skill_is_retired() -> None:
    assert not (ROOT / "skills" / "l9-gmp-protocol").exists()


def test_gmp_executor_does_not_import_pe_autonomy_contracts() -> None:
    source = (ROOT / "workflows" / "gmp_executor.py").read_text(encoding="utf-8")
    assert "environment.contracts.autonomy" not in source
    assert "environment/contracts/autonomy" not in source
