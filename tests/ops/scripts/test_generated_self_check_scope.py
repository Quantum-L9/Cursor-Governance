"""PR self-check must not dirty unrelated generated snapshots."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SYNC = ROOT / "ops" / "scripts" / "sync_generated_artifacts.py"
WORKFLOW = ROOT / ".github" / "workflows" / "governance-self-check.yml"
PE_MANIFEST = "environment/program-execution/MANIFEST.json"
SKILL_REGISTRY = "ops/generated/skill-registry.json"


def _sync_module():
    spec = importlib.util.spec_from_file_location("sync_generated_artifacts", SYNC)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_non_pe_python_does_not_run_pe_or_skills() -> None:
    module = _sync_module()
    changed = {"ops/scripts/foo.py"}
    assert module.should_run(changed, ("environment/program-execution/",)) is False
    assert module.should_run(changed, ("skills/", "ops/generated/skill-registry.json")) is False


def test_pe_source_still_requires_manifest_prefix() -> None:
    module = _sync_module()
    changed = {"environment/program-execution/scripts/run_campaign.py"}
    assert module.should_run(changed, ("environment/program-execution/",)) is True


def test_non_pe_sync_does_not_write_pe_manifest_or_skill_registry(
    monkeypatch,
) -> None:
    module = _sync_module()
    calls: list[str] = []
    monkeypatch.setattr(module, "sync_pe_adapters", lambda root, wrote: calls.append("pe"))
    monkeypatch.setattr(module, "sync_skill_registry", lambda root, wrote: calls.append("skills"))
    result = module.sync(ROOT, changed_paths={"ops/scripts/foo.py"}, pe_manifest=False)
    assert "pe" not in calls
    assert "skills" not in calls
    assert PE_MANIFEST not in result["wrote"]
    assert SKILL_REGISTRY not in result["wrote"]


def test_pe_source_with_pe_manifest_reaches_manifest(monkeypatch) -> None:
    module = _sync_module()
    calls: list[str] = []
    monkeypatch.setattr(module, "sync_pe_adapters", lambda root, wrote: calls.append("pe"))
    monkeypatch.setattr(module, "sync_pe_core", lambda root, wrote: None)
    monkeypatch.setattr(module, "sync_pe_templates", lambda root, wrote: None)
    module.sync(
        ROOT,
        changed_paths={"environment/program-execution/scripts/run_campaign.py"},
        pe_manifest=True,
    )
    assert "pe" in calls


def test_workflow_splits_pr_from_main_snapshot() -> None:
    body = WORKFLOW.read_text(encoding="utf-8")
    assert "--changed-file" in body
    assert 'EVENT_NAME" = "pull_request"' in body or "$EVENT_NAME" in body
    assert "--force --pe-manifest --check" in body
    assert "environment/program-execution/" in body
    assert PE_MANIFEST in body
