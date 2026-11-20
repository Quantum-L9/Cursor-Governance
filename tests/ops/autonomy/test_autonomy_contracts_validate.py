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


# -- Program Execution: an optional, one-way consumer of root autonomy ------

PE_CONSUMER = "program-execution-autonomy-consumer"


def _consumer_entry() -> dict:
    import yaml

    manifest = yaml.safe_load(
        (REPO / "environment/contracts/autonomy/MANIFEST.yaml").read_text(encoding="utf-8")
    )
    return next(item for item in manifest["artifacts"] if item["artifact_id"] == PE_CONSUMER)


def test_program_execution_is_registered_but_never_required() -> None:
    mod = _load()
    assert _consumer_entry()["invocation"] == "explicit_operator_only"
    # Root autonomy must stay valid without Program Execution.
    assert PE_CONSUMER not in mod.REQUIRED_ARTIFACT_IDS


def test_the_consumer_entry_agrees_with_the_surface_profile() -> None:
    mod = _load()
    assert mod._program_execution_consumer_errors(REPO, _consumer_entry()) == []


def test_a_consumer_that_disagrees_with_the_profile_fails() -> None:
    mod = _load()
    for key, value, needle in (
        ("stage", "manual", "disagrees with the surface profile"),
        ("invocation", "ambient", "invocation must be explicit_operator_only"),
        ("provider_id", "someone-else", "provider_id must be root-autonomy-control-plane"),
        ("effect_hook", "missing/hook.py", "missing effect_hook path"),
    ):
        errors = mod._program_execution_consumer_errors(REPO, {**_consumer_entry(), key: value})
        assert any(needle in error for error in errors), (key, errors)


def test_root_autonomy_and_the_gate_still_do_not_reach_program_execution() -> None:
    """The dependency runs one way: Program Execution consumes, nothing consumes it."""
    offenders = []
    for root in (REPO / "autonomy", REPO / "ops" / "autonomy"):
        for path in root.rglob("*.py"):
            if "tests" in path.parts:
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith(("import ", "from ")) and (
                    "program_execution" in stripped or "peer_execution" in stripped
                ):
                    offenders.append(f"{path.relative_to(REPO)}: {stripped}")
    assert offenders == []
    wrapper = REPO / "environment/agents/adapters/claude-code/hooks/local_execution_gate_wrap.py"
    assert "program-execution" not in wrapper.read_text(encoding="utf-8")
