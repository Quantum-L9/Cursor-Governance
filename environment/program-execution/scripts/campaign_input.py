#!/usr/bin/env python3
"""What did the operator actually hand the campaign front door?

`run_campaign.py` used to answer that question implicitly, by trying
`load_activate_seed()` on everything and falling through to the brief compiler
when the shape did not match. A fully specified `campaign-source.v2` matched
neither: its `campaign_id` lives under `metadata`, not at the top level, so the
activate-seed heuristic rejected it and the brief compiler was handed YAML it
could not read. The front door refused a legitimate campaign input.

The failure mode that followed is the reason this module exists: a rejection
with no route and no remedy invites someone to import the runner's private
`default_*` stage functions and drive the pipeline by hand. So classification
happens once, up front, and produces exactly two outcomes — a route, or a
rejection that says why, how to fix it, and that nothing ran.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is a hard dependency of the gate
    yaml = None  # type: ignore[assignment]

CAMPAIGN_SOURCE_SCHEMA = "l9.program-execution.campaign-source.v2"
PROGRAM_INTENT_SCHEMA = "program-execution.intent.v1"
ARCHITECTURE_INTENT_SCHEMA = "l9.program-execution.architecture-intent.v1"
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.S)

REJECTION_CODE = "PE_CAMPAIGN_INPUT_REJECTED"
BYPASS_DIAGNOSTIC = "PUBLIC_CAMPAIGN_FRONT_DOOR_REJECTED"

BYPASS_FORBIDDEN = (
    "Do not import and invoke `default_*` runner functions to bypass this "
    "failure. Fix the input or the front-door router."
)


class CampaignInputKind(Enum):
    BRIEF = "brief"
    PLAN = "plan"
    ACTIVATE = "activate"
    CAMPAIGN_SOURCE_V2 = "campaign-source.v2"
    ARCHITECTURE_INTENT_V1 = "architecture-intent.v1"
    PROGRAM_INTENT_V1 = "program-execution.intent.v1"
    UNKNOWN = "unknown"


SUPPORTED_KINDS = (
    CampaignInputKind.CAMPAIGN_SOURCE_V2,
    CampaignInputKind.ARCHITECTURE_INTENT_V1,
    CampaignInputKind.ACTIVATE,
    CampaignInputKind.PLAN,
    CampaignInputKind.BRIEF,
)

ROUTES = {
    CampaignInputKind.CAMPAIGN_SOURCE_V2: "campaign_source -> blueprint -> PEC",
    CampaignInputKind.ARCHITECTURE_INTENT_V1: (
        "architecture -> campaign_source -> blueprint -> PEC"
    ),
    CampaignInputKind.ACTIVATE: "activate -> campaign_source -> blueprint -> PEC",
    CampaignInputKind.PLAN: "plan -> activate -> campaign_source -> blueprint -> PEC",
    CampaignInputKind.BRIEF: "brief -> activate -> campaign_source -> blueprint -> PEC",
    CampaignInputKind.PROGRAM_INTENT_V1: (
        "intent -> compiler -> blueprint (compile ingress; not campaign execute)"
    ),
}


@dataclass(frozen=True)
class Classification:
    kind: CampaignInputKind
    path: Path
    schema: str = ""
    document: dict[str, Any] | None = field(default=None, repr=False)

    @property
    def supported(self) -> bool:
        return self.kind in SUPPORTED_KINDS

    @property
    def route(self) -> str:
        return ROUTES.get(self.kind, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "schema": self.schema,
            "path": str(self.path),
            "supported": self.supported,
            "route": self.route,
        }


class CampaignInputRejected(Exception):
    """A terminal, self-explaining refusal. Nothing has executed when it raises.

    The message is written to be pasted to an operator verbatim, because that
    is what an agent is expected to do with it instead of finding a way around.
    """

    exit_code = 2

    def __init__(
        self,
        *,
        detected: CampaignInputKind,
        reason: str,
        fix: str,
        path: Path,
        schema: str = "",
    ) -> None:
        self.detected = detected
        self.reason = reason.strip()
        self.fix = fix.strip()
        self.path = path
        self.schema = schema
        super().__init__(self.render())

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": REJECTION_CODE,
            "detected_input_kind": self.detected.value,
            "schema": self.schema,
            "path": str(self.path),
            "reason": self.reason,
            "supported_input_kinds": [kind.value for kind in SUPPORTED_KINDS],
            "nothing_executed": True,
            "workspace_created": False,
            "tasks_started": 0,
            "manual_stage_bypass_permitted": False,
            "fix": self.fix,
        }

    def render(self) -> str:
        supported = "\n".join(f"  - {kind.value}" for kind in SUPPORTED_KINDS)
        return (
            f"{REJECTION_CODE}\n\n"
            f"input:\n"
            f"  kind: {self.detected.value}\n"
            f"  schema: {self.schema or '(none)'}\n"
            f"  path: {self.path}\n\n"
            f"reason:\n  {self.reason}\n\n"
            f"supported:\n{supported}\n\n"
            "nothing_executed: true\n"
            "workspace_created: false\n"
            "tasks_started: 0\n\n"
            f"fix:\n  {self.fix}\n\n"
            f"{BYPASS_DIAGNOSTIC}\n"
            "manual_stage_bypass_permitted: false\n"
            f"{BYPASS_FORBIDDEN}\n"
        )


def _load_document(path: Path) -> dict[str, Any] | None:
    """Parse YAML/JSON, or return None when the file is not a mapping document."""
    if yaml is None:
        raise RuntimeError("PyYAML required to classify campaign input")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return raw if isinstance(raw, dict) else None


def _is_activate_seed(doc: dict[str, Any]) -> bool:
    return bool(
        str(doc.get("campaign_id") or "").strip()
        and str(doc.get("title") or "").strip()
        and str(doc.get("objective") or "").strip()
        and isinstance(doc.get("tasks"), list)
        and doc.get("tasks")
    )


def _parse_frontmatter(text: str) -> dict[str, Any] | None:
    match = FRONTMATTER_RE.match(text)
    if match is None or yaml is None:
        return None
    try:
        raw = yaml.safe_load(match.group(1))
    except Exception:
        return None
    return raw if isinstance(raw, dict) else None


def _is_plan_intent(doc: dict[str, Any] | None) -> bool:
    if not isinstance(doc, dict) or _is_activate_seed(doc):
        return False
    schema = str(doc.get("schema") or "").strip()
    if schema in {ARCHITECTURE_INTENT_SCHEMA, PROGRAM_INTENT_SCHEMA}:
        return False
    if schema == CAMPAIGN_SOURCE_SCHEMA or schema.endswith("campaign-source.v2"):
        return False
    todos = doc.get("todos")
    if not isinstance(todos, list) or not todos:
        return False
    if str(doc.get("mode") or "").strip() == "plan" and (
        str(doc.get("title") or "").strip() or str(doc.get("objective") or "").strip()
    ):
        return True
    if str(doc.get("name") or "").strip() and str(doc.get("overview") or "").strip():
        return True
    if str(doc.get("title") or "").strip() and str(doc.get("objective") or "").strip():
        return True
    return False


def classify(path: Path, *, forced_kind: CampaignInputKind | None = None) -> Classification:
    """Classify by content and schema, never by file extension alone.

    A `.yaml` suffix says nothing about which of three YAML dialects this is,
    and the campaign source dialect is the one that was being misrouted.

    `forced_kind` is how `make campaign-architecture` says "read this as
    architecture intent". The operator already made that choice by picking the
    target, so an unchanged assistant transcript needs no frontmatter edit and
    the router needs no content-sniffing heuristic to guess at it. Ordinary
    `make campaign` never forces, so generic memo traffic keeps going to the
    brief compiler untouched.
    """
    path = Path(path)
    if not path.is_file():
        raise CampaignInputRejected(
            detected=CampaignInputKind.UNKNOWN,
            reason=f"no such campaign input file: {path}",
            fix="Pass INTENT=<path> pointing at an existing campaign source, "
            "activate YAML, or brief memo.",
            path=path,
        )
    text = path.read_text(encoding="utf-8")
    doc = _load_document(path)
    frontmatter_doc = _parse_frontmatter(text) or {}
    declared = str(frontmatter_doc.get("schema") or "").strip()
    if forced_kind is CampaignInputKind.ARCHITECTURE_INTENT_V1 or (
        declared == ARCHITECTURE_INTENT_SCHEMA
    ):
        return Classification(
            kind=CampaignInputKind.ARCHITECTURE_INTENT_V1,
            path=path,
            schema=declared or ARCHITECTURE_INTENT_SCHEMA,
            document=frontmatter_doc or None,
        )
    if doc is None:
        frontmatter = frontmatter_doc or None
        if _is_plan_intent(frontmatter):
            return Classification(kind=CampaignInputKind.PLAN, path=path, document=frontmatter)
        if path.suffix.lower() in {".md", ".markdown", ".txt"}:
            return Classification(kind=CampaignInputKind.BRIEF, path=path)
        return Classification(kind=CampaignInputKind.UNKNOWN, path=path)
    schema = str(doc.get("schema") or "").strip()
    if schema == ARCHITECTURE_INTENT_SCHEMA:
        return Classification(
            kind=CampaignInputKind.ARCHITECTURE_INTENT_V1, path=path, schema=schema, document=doc
        )
    if schema == CAMPAIGN_SOURCE_SCHEMA or schema.endswith("campaign-source.v2"):
        return Classification(
            kind=CampaignInputKind.CAMPAIGN_SOURCE_V2, path=path, schema=schema, document=doc
        )
    if schema == PROGRAM_INTENT_SCHEMA:
        return Classification(
            kind=CampaignInputKind.PROGRAM_INTENT_V1, path=path, schema=schema, document=doc
        )
    if _is_activate_seed(doc):
        return Classification(
            kind=CampaignInputKind.ACTIVATE, path=path, schema=schema, document=doc
        )
    if _is_plan_intent(doc):
        return Classification(kind=CampaignInputKind.PLAN, path=path, schema=schema, document=doc)
    if path.suffix.lower() in {".md", ".markdown", ".txt"}:
        frontmatter = _parse_frontmatter(text)
        if _is_plan_intent(frontmatter):
            return Classification(
                kind=CampaignInputKind.PLAN, path=path, schema=schema, document=frontmatter
            )
        return Classification(kind=CampaignInputKind.BRIEF, path=path, schema=schema, document=doc)
    return Classification(kind=CampaignInputKind.UNKNOWN, path=path, schema=schema, document=doc)


def _compile_module() -> Any:
    """Load the campaign-source compiler, which owns source preflight.

    Imported lazily so `classify()` stays a pure routing decision with no
    jsonschema/Blueprint dependency — a caller that only wants the route pays
    nothing for the preflight machinery.
    """
    import importlib.util

    path = Path(__file__).resolve().parent / "compile_campaign_source.py"
    spec = importlib.util.spec_from_file_location("pe_compile_campaign_source", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise CampaignInputRejected(
            detected=CampaignInputKind.CAMPAIGN_SOURCE_V2,
            reason=f"cannot load the campaign-source compiler at {path}",
            fix="Restore environment/program-execution/scripts/compile_campaign_source.py.",
            path=path,
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _preflight_program_intent(classification: Classification) -> list[str]:
    """Feed program-execution.intent.v1 through the strict compiler parser.

    This is compile ingress, not campaign execution. intent.py stays strict.
    Nothing is written under ~/.l9/programs.
    """
    document = classification.document
    if not isinstance(document, dict):
        raise CampaignInputRejected(
            detected=classification.kind,
            schema=classification.schema,
            path=classification.path,
            reason="program-execution.intent.v1 document is not a mapping.",
            fix="Supply a YAML/JSON object with schema and objective.",
        )
    pe_root = Path(__file__).resolve().parents[1]
    # APPEND, never insert(0): `scripts` is a top-level name Program Execution
    # SHARES with the repository root, so a prepend hands PE's `scripts/` that
    # name process-wide. See peer_execution.imports.pe_script.
    if str(pe_root) not in sys.path:
        sys.path.append(str(pe_root))
    from compiler.intent import parse_intent

    try:
        intent = parse_intent(document)
    except ValueError as exc:
        raise CampaignInputRejected(
            detected=classification.kind,
            schema=classification.schema,
            path=classification.path,
            reason=str(exc),
            fix="Fix the intent against program-execution.intent.v1. Nothing was executed.",
        ) from exc
    return [f"intent_objective={intent.objective}"]


def compile_intent_ingress(path: Path) -> dict[str, Any]:
    """Classify and compile-check a program-execution.intent.v1 file.

    Used by the shadow harness and ``--check-input``. Does not execute a campaign.
    """
    found = classify(path)
    if found.kind is not CampaignInputKind.PROGRAM_INTENT_V1:
        return {
            "kind": found.kind.value,
            "route": found.route,
            "supported": found.supported,
            "compile_ok": False,
            "reason": "not program-execution.intent.v1",
        }
    warnings = _preflight_program_intent(found)
    return {
        "kind": found.kind.value,
        "route": ROUTES[CampaignInputKind.PROGRAM_INTENT_V1],
        "supported": True,
        "compile_ok": True,
        "warnings": warnings,
        "nothing_executed": True,
    }


def preflight(classification: Classification) -> list[str]:
    """Prove a direct campaign source is executable, not merely well-named.

    Classification answers "which route"; it does not answer "will this run".
    A source with `TASK-001A`, a local_write task that names no writable path,
    or a composed validation command used to classify as SUPPORTED and fail
    after isolation, compile and bootstrap. Those are deterministic source
    defects, so they are decided here, where nothing has been created yet.

    Read-only. Returns compile warnings for supported non-direct kinds (none)
    and for a clean direct source. Raises the terminal refusal otherwise.
    """
    if classification.kind is CampaignInputKind.PROGRAM_INTENT_V1:
        return _preflight_program_intent(classification)
    if classification.kind is not CampaignInputKind.CAMPAIGN_SOURCE_V2:
        return []
    document = classification.document
    if not isinstance(document, dict):  # pragma: no cover - classify guarantees this
        return []
    module = _compile_module()
    try:
        return list(module.preflight_campaign_source_document(document))
    except Exception as exc:  # noqa: BLE001 - re-raised as the terminal refusal
        if isinstance(exc, CampaignInputRejected):
            raise
        raise CampaignInputRejected(
            detected=classification.kind,
            schema=classification.schema,
            reason=str(exc),
            fix="Fix the campaign source at the identified task/gate/field. Nothing was "
            "executed and no workspace was created.",
            path=classification.path,
        ) from exc


def reject(classification: Classification) -> CampaignInputRejected:
    """Build the terminal refusal for an unsupported classification."""
    if classification.kind is CampaignInputKind.PROGRAM_INTENT_V1:
        return CampaignInputRejected(
            detected=classification.kind,
            schema=classification.schema,
            path=classification.path,
            reason=(
                "The live campaign runner does not execute program-execution.intent.v1. "
                "Compile ingress is live: classify + compiler.intent.parse_intent "
                "(intent -> compiler -> blueprint). Conversion is not the only path."
            ),
            fix=(
                "Compile through the Program Execution compiler (shadow / "
                "--check-input). Campaign execution still uses campaign-source.v2 "
                "after compile:\n"
                '    make -C "$HOME/.cursor-governance" campaign '
                "INTENT=/path/to/CAMPAIGN_SOURCE.yaml"
            ),
        )
    return CampaignInputRejected(
        detected=classification.kind,
        schema=classification.schema,
        path=classification.path,
        reason=(
            "The file parsed, but matched no supported campaign input shape: it "
            f"declares schema {classification.schema or '(none)'} and is not an "
            "activate seed (campaign_id, title, objective, tasks)."
        ),
        fix=(
            "Supply a campaign-source.v2 "
            f"(schema: {CAMPAIGN_SOURCE_SCHEMA}), an activate seed, or a brief memo."
        ),
    )


def seed_view(source: dict[str, Any]) -> dict[str, Any]:
    """Present a campaign-source.v2 through the small seed surface stages read.

    Stack proof, the resume path, and admission read a handful of activate-seed
    keys. This is a *view*, not a conversion: the canonical source still goes to
    `compile_source` untouched, so no task, dependency, validation, gate, or
    authority datum is flattened on the way in.
    """
    metadata = source.get("metadata") or {}
    program = source.get("program") or {}
    target = dict(source.get("target") or {})
    # `targets[]` owns execution target identity for a direct campaign source.
    # Resolving the runner's repository from `program.target_repository_id` /
    # `metadata.intended_host` instead let the runner bind one repository while
    # the compiler built the Blueprint against another.
    target["repository_id"] = _compile_module().resolve_campaign_target_repository(source)
    return {
        "campaign_id": str(metadata.get("campaign_id") or program.get("id") or "").strip(),
        "title": str(metadata.get("title") or program.get("name") or "").strip(),
        "objective": str(program.get("objective") or "").strip(),
        "problem_statement": str(program.get("problem_statement") or "").strip(),
        "tasks": list(source.get("tasks") or []),
        "gates": list(source.get("gates") or []),
        "target": target,
        "stack_tools": list(source.get("stack_tools") or []),
        "plan_status": str(source.get("plan_status") or "").strip(),
    }


def main(argv: list[str] | None = None) -> int:
    """`--check-input`: classify and print the route. Executes no campaign stage."""
    import argparse

    parser = argparse.ArgumentParser(description="classify a PE campaign input")
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--as",
        dest="forced",
        choices=[CampaignInputKind.ARCHITECTURE_INTENT_V1.value],
        default=None,
        help="interpret the input as this kind (the campaign-architecture route)",
    )
    args = parser.parse_args(argv)
    forced = CampaignInputKind(args.forced) if args.forced else None
    try:
        found = classify(args.path, forced_kind=forced)
    except CampaignInputRejected as exc:
        print(json.dumps(exc.to_dict(), indent=2) if args.json else exc.render())
        return exc.exit_code
    compile_ingress = found.kind is CampaignInputKind.PROGRAM_INTENT_V1
    if not found.supported and not compile_ingress:
        exc = reject(found)
        print(json.dumps(exc.to_dict(), indent=2) if args.json else exc.render())
        return exc.exit_code
    try:
        warnings = preflight(found)
    except CampaignInputRejected as exc:
        print(json.dumps(exc.to_dict(), indent=2) if args.json else exc.render())
        return exc.exit_code
    if args.json:
        payload = found.to_dict()
        payload["preflight"] = {"passed": True, "warnings": warnings}
        print(json.dumps(payload, indent=2))
    else:
        print(f"SUPPORTED\nkind: {found.kind.value}\nroute: {found.route}")
        for warning in warnings:
            print(f"warning: {warning}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
