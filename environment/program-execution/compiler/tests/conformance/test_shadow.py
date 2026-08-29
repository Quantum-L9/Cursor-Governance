"""W1.4 + AT-009/AT-010/AT-012 — shadow compile has no campaign side effect."""

from __future__ import annotations

import json
from pathlib import Path

from compiler.tests.conformance.shadow_runner import compile_fixture, fixture_ids


def test_fixture_corpus_is_01_through_14() -> None:
    ids = fixture_ids()
    assert len(ids) == 14
    assert ids[0].startswith("01_")
    assert ids[-1].startswith("14_")


def test_shadow_compile_does_not_touch_l9_programs_or_worktree(
    tmp_path: Path, monkeypatch
) -> None:
    root = Path(__file__).resolve().parents[5]
    programs = Path.home() / ".l9" / "programs"
    before_programs = (
        sorted(p.name for p in programs.iterdir()) if programs.is_dir() else []
    )
    fixture = Path(__file__).resolve().parent / "fixtures" / "01_one_sentence_intent"
    report = compile_fixture(fixture, repo_root=root)
    after_programs = (
        sorted(p.name for p in programs.iterdir()) if programs.is_dir() else []
    )
    assert before_programs == after_programs
    assert report.side_effects == []
    assert "classify" in report.stages


def test_malformed_intent_fails_before_side_effects(tmp_path: Path) -> None:
    import yaml

    bad = tmp_path / "bad.yaml"
    bad.write_text(
        yaml.safe_dump({"schema": "program-execution.intent.v1", "tasks": ["nope"]}),
        encoding="utf-8",
    )
    # Avoid a circular import name: load from the live script.
    import importlib.util
    import sys

    pe = Path(__file__).resolve().parents[3]
    if str(pe) not in sys.path:
        sys.path.insert(0, str(pe))
    path = pe / "scripts" / "campaign_input.py"
    spec = importlib.util.spec_from_file_location("pec_at012_campaign_input", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    found = module.classify(bad)
    assert found.kind is module.CampaignInputKind.PROGRAM_INTENT_V1
    try:
        module.compile_intent_ingress(bad)
        raised = False
    except module.CampaignInputRejected:
        raised = True
    assert raised


def test_comparator_is_semantic_not_wording_exact() -> None:
    from compiler.tests.conformance.expectation import SemanticExpectation
    from compiler.tests.conformance.shadow_runner import compare

    expect = SemanticExpectation(
        fixture_id="semantic",
        objective_contains=("harden the existing",),
        prohibitions=("DO NOT",),
    )
    compiled = {
        "objective": "Harden the existing compiler ingress.",
        "signals": ["DO NOT"],
        "dispositions": [{"disposition": "HARDEN_WIRE_EXISTING"}],
        "authority_actions": ["inspect"],
        "source_refs": ["SRC-0001"],
    }
    report = compare(expect, compiled, stages=["compare"], kind="brief", route="brief")
    assert report.metrics["fixture_pass_count"] == 1
    assert json.dumps(report.to_dict())
