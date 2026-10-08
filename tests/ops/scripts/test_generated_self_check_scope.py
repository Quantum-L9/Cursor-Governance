"""PR self-check must not dirty unrelated generated snapshots."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SYNC = ROOT / "ops" / "scripts" / "sync_generated_artifacts.py"
WORKFLOW = ROOT / ".github" / "workflows" / "governance-self-check.yml"
SKILL_REGISTRY = "ops/generated/skill-registry.json"


def _sync_module():
    spec = importlib.util.spec_from_file_location("sync_generated_artifacts", SYNC)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unrelated_python_does_not_run_skills() -> None:
    module = _sync_module()
    changed = {"ops/scripts/foo.py"}
    assert module.should_run(changed, ("skills/", "ops/generated/skill-registry.json")) is False


def test_unrelated_sync_does_not_write_skill_registry(monkeypatch) -> None:
    module = _sync_module()
    calls: list[str] = []
    monkeypatch.setattr(module, "sync_skill_registry", lambda root, wrote: calls.append("skills"))
    result = module.sync(ROOT, changed_paths={"ops/scripts/foo.py"})
    assert "skills" not in calls
    assert SKILL_REGISTRY not in result["wrote"]


def test_generic_sync_has_no_program_execution_surface() -> None:
    """Program Execution is an eviction target; the generic helper owns none of it."""
    module = _sync_module()
    assert not hasattr(module, "sync_pe_adapters")
    assert not hasattr(module, "sync_pe_core")
    assert not hasattr(module, "sync_pe_templates")
    assert not any("program-execution" in prefix for prefix in module.GENERATED_PATH_PREFIXES)
    assert "pe_manifest" not in module.sync.__code__.co_varnames
    options = {opt for action in module.build_parser()._actions for opt in action.option_strings}
    assert "--pe-manifest" not in options


def test_workflow_splits_pr_from_main_snapshot() -> None:
    body = WORKFLOW.read_text(encoding="utf-8")
    assert "--changed-file" in body
    assert 'EVENT_NAME" = "pull_request"' in body or "$EVENT_NAME" in body
    assert "--force --check" in body
    assert "--pe-manifest" not in body
    assert "environment/program-execution/MANIFEST.json" not in body


def test_no_workflow_passes_the_removed_pe_manifest_flag() -> None:
    """argparse rejects unknown flags, so any caller left behind fails on main."""
    callers = [
        path.relative_to(ROOT).as_posix()
        for path in sorted((ROOT / ".github" / "workflows").glob("*.yml"))
        if any(
            "sync_generated_artifacts.py" in line and "--pe-manifest" in line
            for line in path.read_text(encoding="utf-8").splitlines()
        )
    ]
    assert callers == [], callers
