"""Tests for first-class autonomy contracts MANIFEST validator."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "ops/scripts/validate_autonomy_contracts.py"


def _load():
    spec = importlib.util.spec_from_file_location("validate_autonomy_contracts", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_autonomy_contracts_validate_pass_on_repo() -> None:
    mod = _load()
    errors = mod.validate(REPO)
    assert errors == [], errors


def test_autonomy_contracts_cli_main_zero(monkeypatch) -> None:
    mod = _load()
    monkeypatch.setattr("sys.argv", ["validate_autonomy_contracts.py"])
    assert mod.main() == 0


def test_pycache_only_legacy_autonomy_path_is_forbidden(tmp_path: Path) -> None:
    leftover = tmp_path / "environment/agents/adapters/claude-code/autonomy/__pycache__"
    leftover.mkdir(parents=True)
    (leftover / "cli.cpython-312.pyc").write_bytes(b"\0")
    mod = _load()
    errors = mod._provider_autonomy_residue_errors(tmp_path)
    assert any("provider-owned autonomy runtime forbidden" in e for e in errors)
    assert any("legacy Claude-owned autonomy runtime path still exists" in e for e in errors)
