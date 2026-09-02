"""Shadow compiler: compile, do not execute a campaign, compare, score.

Never writes ~/.l9/programs or mutates the operator worktree.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from compiler.architecture_intent import (
    normalize_source,
    normative_signals,
    segment,
)
from compiler.intent import parse_intent
from compiler.repo_truth import classify_dispositions, discover

from .expectation import SemanticExpectation

PE_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
# APPEND, never insert(0): Program Execution needs its own PE-exclusive
# packages here, but `scripts` is a top-level name it SHARES with the
# repository root. Prepending would hand PE's `scripts/` that name for the
# whole process. See peer_execution.imports.pe_script.
if str(PE_ROOT) not in sys.path:
    sys.path.append(str(PE_ROOT))


def _campaign_input():
    path = PE_ROOT / "scripts" / "campaign_input.py"
    spec = importlib.util.spec_from_file_location("pec_shadow_campaign_input", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@dataclass
class ShadowReport:
    fixture_id: str
    route: str
    kind: str
    stages: list[str]
    losses: list[str]
    side_effects: list[str]
    metrics: dict[str, int | float]
    compiled: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "route": self.route,
            "kind": self.kind,
            "stages": self.stages,
            "losses": self.losses,
            "side_effects": self.side_effects,
            "metrics": self.metrics,
            "compiled": self.compiled,
        }


def fixture_ids() -> list[str]:
    return sorted(p.name for p in FIXTURES.iterdir() if p.is_dir() and not p.name.startswith("."))


def compile_fixture(fixture_dir: Path, *, repo_root: Path) -> ShadowReport:
    source = _source_path(fixture_dir)
    expect = SemanticExpectation.load(fixture_dir / "expect.yaml")
    text = source.read_text(encoding="utf-8")
    ci = _campaign_input()
    found = ci.classify(source)
    stages = ["classify"]
    compiled: dict[str, Any] = {
        "kind": found.kind.value,
        "route": found.route,
        "objective": text,
        "signals": list(normative_signals(normalize_source(text))),
        "units": [u.id for u in segment(normalize_source(text))],
        "dispositions": [],
        "authority_actions": ["inspect"],
        "source_refs": [u.id for u in segment(normalize_source(text))],
    }
    if found.kind is ci.CampaignInputKind.PROGRAM_INTENT_V1:
        stages.append("intent_parse")
        ingress = ci.compile_intent_ingress(source)
        compiled["ingress"] = ingress
        stages.append("intent_ingress")
        if ingress.get("compile_ok"):
            intent = parse_intent(json.loads(json.dumps(found.document)))
            compiled["objective"] = intent.objective
            truth = discover(repo_root)
            compiled["dispositions"] = [
                row.to_dict() for row in classify_dispositions([intent.objective], truth)
            ]
            stages.append("disposition")
    else:
        compiled["dispositions"] = [
            row.to_dict() for row in classify_dispositions([text.strip()], discover(repo_root))
        ]
        stages.append("disposition")
        compiled["objective"] = text
    return compare(expect, compiled, stages=stages, kind=found.kind.value, route=found.route)


def compare(
    expect: SemanticExpectation,
    compiled: dict[str, Any],
    *,
    stages: list[str],
    kind: str,
    route: str,
) -> ShadowReport:
    haystack = json.dumps(compiled, ensure_ascii=False).lower()
    losses: list[str] = []
    material_intent_loss = 0
    prohibition_loss = 0
    acceptance_loss = 0
    unknown_loss = 0
    false_create = 0
    grounding_error = 0
    authority_widening = 0
    traced = 0
    required = 0

    for needle in expect.objective_contains + expect.preserve:
        required += 1
        if needle.lower() in haystack:
            traced += 1
        else:
            material_intent_loss += 1
            losses.append(f"missing:{needle}")
    for prohibition in expect.prohibitions:
        required += 1
        signals = {str(s).upper() for s in compiled.get("signals") or []}
        if prohibition.upper() in signals or prohibition.lower() in haystack:
            traced += 1
        else:
            prohibition_loss += 1
            losses.append(f"prohibition_loss:{prohibition}")
    dispositions = [str(row.get("disposition")) for row in compiled.get("dispositions") or []]
    for wanted in expect.expected_dispositions:
        if wanted not in dispositions:
            if wanted == "KEEP" and "CREATE" in dispositions:
                false_create += 1
                losses.append("false_create_where_canonical_exists")
            elif wanted == "UNKNOWN" and dispositions and "UNKNOWN" not in dispositions:
                unknown_loss += 1
                losses.append("unknown_loss")
            else:
                grounding_error += 1
                losses.append(f"disposition_miss:{wanted}")
        else:
            traced += 1
            required += 1
    if expect.authority_must_not_expand:
        extra = set(compiled.get("authority_actions") or []) - {"inspect", "local_write"}
        if extra:
            authority_widening += 1
            losses.append(f"authority_widening:{sorted(extra)}")
    if expect.source_traceability_required:
        required += 1
        if compiled.get("source_refs"):
            traced += 1
        else:
            losses.append("missing_source_provenance")
            grounding_error += 1

    metrics = {
        "material_intent_loss_count": material_intent_loss,
        "prohibition_loss_count": prohibition_loss,
        "acceptance_loss_count": acceptance_loss,
        "unknown_loss_count": unknown_loss,
        "false_create_count": false_create,
        "grounding_error_count": grounding_error,
        "authority_widening_count": authority_widening,
        "source_traceability_percent": (100.0 * traced / required) if required else 100.0,
        "fixture_pass_count": 0 if losses else 1,
        "fixture_fail_count": 1 if losses else 0,
    }
    return ShadowReport(
        fixture_id=expect.fixture_id,
        route=route,
        kind=kind,
        stages=stages,
        losses=losses,
        side_effects=[],
        metrics=metrics,
        compiled=compiled,
    )


def _source_path(fixture_dir: Path) -> Path:
    for name in ("source.yaml", "source.md", "source.json"):
        candidate = fixture_dir / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"no source in {fixture_dir}")
