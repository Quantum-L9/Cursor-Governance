#!/usr/bin/env python3
"""Compile a campaign-source.v2 seed into a Blueprint v2 pair."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

# Sibling import safety: this module is also loaded via importlib (tests) with
# PYTHONPATH pointing at the PE root, so the scripts/ dir may not be on sys.path.
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))


def _load_prohibition_entry() -> Any:
    """Load the shared prohibition classifier from the compiler package.

    scripts/ reaches compiler/ by path rather than by package import, the same
    direction campaign_input.py already uses, because the repository root also
    carries a `scripts` package that shadows this one.
    """
    module_path = Path(__file__).resolve().parents[1] / "compiler" / "prohibition_kind.py"
    spec = importlib.util.spec_from_file_location("pes_prohibition_kind", module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - packaging error
        raise RuntimeError(f"cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("pes_prohibition_kind", module)
    spec.loader.exec_module(module)
    return module.entry


prohibition_entry = _load_prohibition_entry()


from blueprint_ops import (  # noqa: E402
    dump_yaml,
    load_yaml,
    patch_phase0_operator_name,
    scan_placeholders,
    write_manifest,
)
from blueprint_ops import (  # noqa: E402
    validate_blueprint as validate_blueprint_artifact,
)

_PE_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
# APPEND, never insert(0): `scripts` is a top-level name Program Execution
# SHARES with the repository root, so a prepend hands PE's `scripts/` that name
# process-wide -- and this file runs inside every `make campaign` through
# campaign_input._compile_module(). See peer_execution.imports.pe_script.
if str(_PE_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.append(str(_PE_ROOT_FOR_IMPORT))

from peer_execution.validation_command import validation_command_error  # noqa: E402

PE_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PE_ROOT / "core/shared/schemas/campaign-source.schema.json"
PROVENANCE_SCHEMA_PATH = PE_ROOT / "compiler/schemas/architecture-resolution.schema.json"
INTENT_PROVENANCE_SCHEMA = "l9.program-execution.intent-provenance.v1"
BLUEPRINT_TEMPLATE = PE_ROOT / "core/program-execution-blueprint-template"
ADAPTER_REMAP = {"git_repo_adapter": "git"}
LIKELIHOOD = {"possible": "medium", "likely": "high", "unlikely": "low"}
SEVERITY = {"critical": "critical", "material": "high", "low": "low"}
EVIDENCE_TYPE = {
    "repository_inspection": "inspection",
    "architecture_decision_records": "inspection",
    "test_result": "test_result",
    "conformance_result": "test_result",
}
CONTRACT_KEYS = ("pair", "blueprint", "controller_minimum")
AUTH_REQUIRED = ("id", "responsibility", "owner")
DECISION_REQUIRED = ("id", "question", "status")
TASK_STATUSES_ADMITTED = {"ready", "blocked", "cancelled", "superseded"}
# Actions the sealed Program Execution runner cannot perform. A source may
# still declare them -- historical sources declare push and pull_request --
# but the effective Task Card ceiling narrows every one to false. A ceiling
# that advertises authority no downstream surface can exercise is inherited
# as fact by the Controller contract, the root-Autonomy grant, and the worker.
PE_FORBIDDEN_ACTIONS = (
    "push",
    "pull_request",
    "merge",
    "publish_or_release",
    "deploy_or_migrate",
    "destructive_change",
    "external_message",
)
KERNEL_PROFILES = ("BUILD", "CHANGE", "AUDIT")
DEFAULT_KERNEL_PROFILE = "BUILD"
# Task-local ordering aliases. `dependency_edges` is the only executable DAG
# authority for campaign-source.v2; these are refused, never merged into it.
TASK_DEPENDENCY_ALIASES = ("dependencies", "dependency_ids")
# Read only to detect contradiction with targets[]. Never a target authority.
TARGET_REPOSITORY_ALIASES = (
    ("program.target_repository_id", ("program", "target_repository_id")),
    ("metadata.intended_host", ("metadata", "intended_host")),
    ("target.repository_id", ("target", "repository_id")),
)


class CompileError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def validate_campaign_source(data: dict[str, Any]) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(data),
        key=lambda item: list(item.path),
    )
    return [
        f"{'.'.join(str(part) for part in err.path) or '<root>'}: {err.message}" for err in errors
    ]


def validate_intent_provenance(src: dict[str, Any]) -> list[str]:
    """Re-derive the architecture mapping rather than trusting the record of it.

    Without this, the architecture route is bypassable by hand: compile a valid
    architecture campaign, delete one mapped requirement from the emitted YAML,
    and hand the edited file straight to this compiler. The Blueprint would
    still validate — schema validity says nothing about intent fidelity — and
    the deleted obligation would be gone with a PASS coverage record still
    attached, claiming otherwise.

    So every count and every reference is recomputed here. Sources with no
    `intent_provenance` are untouched: legacy and hand-authored campaign sources
    are not architecture-intent sources and are not required to become one.
    """
    provenance = src.get("intent_provenance")
    if provenance is None:
        return []
    if not isinstance(provenance, dict):
        raise CompileError("intent_provenance must be a mapping")
    schema = str(provenance.get("schema") or "")
    if schema != INTENT_PROVENANCE_SCHEMA:
        raise CompileError(f"intent_provenance.schema {schema!r} is not {INTENT_PROVENANCE_SCHEMA}")
    errors = sorted(
        Draft202012Validator(
            json.loads(PROVENANCE_SCHEMA_PATH.read_text(encoding="utf-8"))
        ).iter_errors(provenance),
        key=lambda item: list(item.path),
    )
    if errors:
        detail = "; ".join(
            f"{'.'.join(str(part) for part in err.path) or '<root>'}: {err.message}"
            for err in errors[:5]
        )
        raise CompileError(f"intent_provenance schema: {detail}")

    units = provenance.get("source_units") or []
    unit_ids = {str(unit.get("id")) for unit in units}
    if len(unit_ids) != len(units):
        raise CompileError("intent_provenance.source_units contains duplicate unit ids")
    items = provenance.get("semantic_items") or []
    item_ids = {str(item.get("id")) for item in items}
    if len(item_ids) != len(items):
        raise CompileError("intent_provenance.semantic_items contains duplicate ids")

    known = _campaign_construct_ids(src)
    material_items = 0
    mapped_material = 0
    for item in items:
        refs = [str(ref) for ref in item.get("source_refs") or []]
        if not refs:
            raise CompileError(f"semantic item {item.get('id')!r} has no source provenance")
        missing = sorted(set(refs) - unit_ids)
        if missing:
            raise CompileError(
                f"semantic item {item.get('id')!r} cites unknown source units: {missing}"
            )
        if str(item.get("materiality") or "material") != "material":
            continue
        material_items += 1
        mappings = item.get("campaign_mappings") or []
        if mappings:
            mapped_material += 1
        for mapping in mappings:
            _require_mapping_target(item, mapping, known)

    coverage = provenance.get("coverage") or {}
    recorded_status = str(coverage.get("status") or "")
    if recorded_status != "PASS":
        raise CompileError(
            f"intent_provenance.coverage.status is {recorded_status!r}; a campaign source "
            "compiled from architecture intent must carry PASS coverage"
        )
    if int(coverage.get("total_units") or 0) != len(units):
        raise CompileError(
            "intent_provenance.coverage.total_units does not match the source unit ledger"
        )
    material_units = [unit for unit in units if unit.get("signals")]
    if int(coverage.get("material_units") or 0) != len(material_units):
        raise CompileError(
            "intent_provenance.coverage.material_units does not match the unit ledger"
        )
    ungoverned = [
        str(unit.get("id"))
        for unit in material_units
        if str(unit.get("disposition") or "") in {"", "mapped_context"}
    ]
    if ungoverned:
        raise CompileError(
            "source units carrying normative signals have no governed disposition: "
            + ", ".join(sorted(ungoverned)[:12])
        )
    if int(coverage.get("unmapped_material_units") or 0) != 0:
        raise CompileError("intent_provenance.coverage records unmapped material source units")
    recorded_material = coverage.get("material_semantic_items")
    if recorded_material is not None and int(recorded_material) != material_items:
        raise CompileError(
            "intent_provenance.coverage.material_semantic_items does not match the item ledger "
            f"(recorded {recorded_material}, present {material_items})"
        )
    recorded_mapped = coverage.get("mapped_material_semantic_items")
    if recorded_mapped is not None and int(recorded_mapped) > mapped_material:
        raise CompileError(
            "intent_provenance.coverage claims more mapped material items than the source "
            f"carries (recorded {recorded_mapped}, present {mapped_material})"
        )
    chunks_expected = int(coverage.get("chunks_expected") or 1)
    chunks_extracted = int(coverage.get("chunks_extracted") or 1)
    if chunks_extracted < chunks_expected:
        raise CompileError(
            f"intent_provenance records {chunks_extracted} of {chunks_expected} source chunks "
            "extracted; no chunk may be omitted"
        )
    return _verify_architecture_source(provenance)


ARCHITECTURE_SOURCE_UNVERIFIABLE = "architecture_source_unverifiable"


def _architecture_intent_module() -> Any:
    """`compiler.architecture_intent`, by the route campaign_input already uses."""
    from compiler.architecture_intent import digest, normalize_source

    return normalize_source, digest


def _verify_architecture_source(provenance: dict[str, Any]) -> list[str]:
    """Re-derive `intent_provenance.source.sha256` from the document it names.

    The declared digest is a *claim* about a file outside the campaign source.
    When that file is readable it is normalized and digested exactly as the
    architecture route did, and a different result is drift: the campaign
    source was compiled from a document that no longer says what it said.
    When the file is not readable the claim cannot be checked, and that is
    recorded as a warning rather than silently accepted.
    """
    origin = provenance.get("source") or {}
    declared = str(origin.get("sha256") or "").strip().lower()
    declared_path = str(origin.get("path") or "").strip()
    if not declared_path:
        return [
            f"{ARCHITECTURE_SOURCE_UNVERIFIABLE}: intent_provenance.source names no path; "
            f"declared sha256 {declared[:12]} was not re-derived"
        ]
    candidate = Path(declared_path).expanduser()
    try:
        raw = candidate.read_text(encoding="utf-8")
    except OSError as exc:
        return [
            f"{ARCHITECTURE_SOURCE_UNVERIFIABLE}: {declared_path} is not readable "
            f"({type(exc).__name__}); declared sha256 {declared[:12]} was not re-derived"
        ]
    except UnicodeDecodeError as exc:
        raise CompileError(
            f"architecture source drifted: {declared_path} is no longer UTF-8 text ({exc}); "
            f"intent_provenance.source.sha256 records {declared[:12]}. Recompile through "
            "the architecture route instead of editing the compiled campaign source"
        ) from exc
    normalize_source, digest = _architecture_intent_module()
    actual = digest(normalize_source(raw))
    if actual != declared:
        raise CompileError(
            f"architecture source drifted: {declared_path} now digests {actual[:12]}, "
            f"intent_provenance.source.sha256 records {declared[:12]}. Recompile through "
            "the architecture route instead of editing the compiled campaign source"
        )
    return []


_MAPPING_LOOKUP = {
    "task": "tasks",
    "task_action": "tasks",
    "task_acceptance": "tasks",
    "task_validation": "tasks",
    "task_negative_case": "tasks",
    "task_path": "tasks",
    "prohibited_path": "prohibited_paths",
    "decision": "decisions",
    "risk": "risks",
    "unknown": "unknowns",
    "evidence_requirement": "evidence_requirements",
    "gate": "gates",
    "wave": "waves",
}


def _campaign_construct_ids(src: dict[str, Any]) -> dict[str, set[str]]:
    known: dict[str, set[str]] = {}
    for key in (
        "tasks",
        "gates",
        "waves",
        "decisions",
        "risks",
        "unknowns",
        "prohibited_paths",
        "evidence_requirements",
    ):
        known[key] = {
            str(entry.get("id"))
            for entry in (src.get(key) or [])
            if isinstance(entry, dict) and entry.get("id")
        }
    return known


def _require_mapping_target(
    item: dict[str, Any], mapping: dict[str, Any], known: dict[str, set[str]]
) -> None:
    kind = str(mapping.get("kind") or "")
    bucket = _MAPPING_LOOKUP.get(kind)
    if bucket is None:
        return
    identifier = str(mapping.get("task_id") or mapping.get("id") or "")
    if not identifier:
        raise CompileError(
            f"semantic item {item.get('id')!r} maps to {kind} without naming which one"
        )
    if identifier not in known.get(bucket, set()):
        raise CompileError(
            f"semantic item {item.get('id')!r} maps to {kind} {identifier!r}, which the campaign "
            f"source does not contain; the mapped obligation was removed"
        )


def _load_instantiate() -> Any:
    path = BLUEPRINT_TEMPLATE / "scripts/instantiate.py"
    spec = importlib.util.spec_from_file_location("pe_bp_instantiate", path)
    if spec is None or spec.loader is None:
        raise CompileError(f"cannot load instantiate.py: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_instantiated(target: Path, src: dict[str, Any], stamp: str) -> None:
    if (target / "PROGRAM.yaml").is_file():
        return
    if target.exists() and any(target.iterdir()):
        raise CompileError(f"target is not an empty Blueprint tree: {target}")
    prog = src["program"]
    module = _load_instantiate()
    module.render_tree(
        target,
        {
            "PROGRAM_NAME": str(prog["name"]),
            "PROGRAM_ID": str(prog["id"]),
            "PROGRAM_VERSION": str(prog.get("version") or "1.0.0"),
            "PROGRAM_OWNER": str(prog["owner"]),
            "DATE": stamp,
        },
    )


def _program_contracts(prog: dict[str, Any]) -> dict[str, str]:
    raw = dict(prog.get("contracts") or {})
    return {
        "blueprint": "program-execution-blueprint.v2",
        "controller_minimum": "program-execution-controller.v2",
        "pair": "program-execution-system.v2",
        **{key: raw[key] for key in CONTRACT_KEYS if key in raw},
    }


def _remap_adapter(value: str) -> str:
    return ADAPTER_REMAP.get(value, value)


def _first_authority_id(src: dict[str, Any]) -> str:
    authorities = [item for item in (src.get("authorities") or []) if isinstance(item, dict)]
    for item in authorities:
        if str(item.get("id") or "").strip():
            return str(item["id"])
    raise CompileError(
        "campaign source declares no authorities; decisions, observability signals and "
        "rollback need an owning authority the source defines"
    )


def _known_authority_ids(src: dict[str, Any]) -> set[str]:
    return {
        str(item.get("id"))
        for item in (src.get("authorities") or [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }


def _decision_authority(item: dict[str, Any], src: dict[str, Any]) -> str:
    authority = str(item.get("authority_id") or "").strip()
    if not authority:
        raise CompileError(f"decision {item.get('id')!r} names no authority_id")
    if authority not in _known_authority_ids(src):
        raise CompileError(
            f"decision {item.get('id')!r} names authority {authority!r}, which the source "
            "does not define"
        )
    return authority


def _task_owner_authority(item: dict[str, Any], first_authority: str) -> str:
    basis = [str(value) for value in (item.get("authority_basis_ids") or []) if str(value)]
    return basis[0] if basis else first_authority


def _decision_rationale(item: dict[str, Any]) -> str:
    selected = str(item.get("selected_option_id") or "").strip()
    authority = str(item.get("authority_id") or "").strip()
    if selected and authority:
        return f"Selected {selected} per {authority}."
    if selected:
        return f"Selected {selected}."
    return "Decision recorded from the campaign source; no option selected yet."


def _source_revision(source: Path) -> str:
    """Exact identity of the source this Blueprint was compiled from.

    Always the digest of the bytes actually compiled. The architecture route's
    declared document digest used to be recorded here instead, so the
    traceability register named a file the compiler never read — and the same
    edited campaign source, handed in twice, recorded the same "revision". The
    declared digest rides beside it as `architecture_source_sha256`.
    """
    return "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()


def _require_auth(item: dict[str, Any]) -> None:
    missing = [key for key in AUTH_REQUIRED if not item.get(key)]
    if missing:
        raise CompileError(f"authority missing required keys: {missing}")


def _semantic_precheck(src: dict[str, Any]) -> list[str]:
    """Fail loudly on source shapes that have no valid compiled representation.

    Run before any artifact is written. Returns compile warnings.
    """
    warnings: list[str] = []
    # One repository identity, resolved before anything reads a target.
    resolve_campaign_target_repository(src)
    for decision in src.get("decisions") or []:
        if not decision.get("options"):
            raise CompileError(
                f"decision {decision['id']!r} has no options array; every decision requires "
                "source-side options (id + description) because the Blueprint Decision "
                "Register mandates non-empty options — fix the source, never synthesize "
                "options in the compiled artifact"
            )
        missing = [key for key in DECISION_REQUIRED if not decision.get(key)]
        if missing:
            raise CompileError(
                f"decision {decision.get('id')!r} is missing required keys {missing}; "
                "the Decision Register admits no decision without them -- fix the source"
            )
        admitted = blueprint_decision_statuses()
        if decision["status"] not in admitted:
            raise CompileError(
                f"decision {decision['id']!r}: status {decision['status']!r} is not one of "
                f"{sorted(admitted)}"
            )
        _decision_authority(decision, src)
    _require_unique_task_ids(src)
    for task in src.get("tasks") or []:
        status = task.get("definition_status")
        if status not in TASK_STATUSES_ADMITTED:
            raise CompileError(
                f"task {task['id']!r}: definition_status {status!r} is not admitted by the "
                f"instantiated Blueprint validator ({sorted(TASK_STATUSES_ADMITTED)}); "
                "fix the source"
            )
        for alias in TASK_DEPENDENCY_ALIASES:
            if task.get(alias):
                raise CompileError(
                    f"task {task['id']!r} declares task-local {alias!r}. Top-level "
                    "`dependency_edges` is the sole executable DAG authority for "
                    "campaign-source.v2, and a second ordering representation cannot be "
                    "reconciled with it -- readiness would follow one while the executable "
                    "graph followed the other. Express the edge as a top-level "
                    f"dependency_edges entry naming the predecessor and {task['id']!r}"
                )
        _require_consistent_execution_authority(task)
        _task_kernel_profile(task)
        for entry in task.get("validation") or []:
            if (
                isinstance(entry, dict)
                and not str(
                    entry.get("command_or_inspection") or entry.get("command") or ""
                ).strip()
            ):
                warnings.append(
                    f"task {task['id']!r} validation {entry.get('id')!r} declares no command or "
                    "inspection; it cannot reach the Rendered Contract and pec verify will have "
                    "nothing to run"
                )
    return warnings


def _require_unique_task_ids(src: dict[str, Any]) -> None:
    """Two tasks with one id have no compiled representation.

    Lowering keys tasks by id, so the second definition silently overwrote the
    first and the dependency graph, task cards and readiness all described a
    program with one task fewer than the operator wrote. Compared
    case-insensitively: the Blueprint grammar is upper-case, and `task-001`
    beside `TASK-001` is a collision the runner's edit detection cannot tell
    apart either.
    """
    seen: dict[str, str] = {}
    for task in src.get("tasks") or []:
        task_id = str((task or {}).get("id") or "")
        key = task_id.casefold()
        if key in seen:
            collision = (
                f"duplicate task id {task_id!r}"
                if seen[key] == task_id
                else (
                    f"task id {task_id!r} collides with {seen[key]!r} "
                    "(ids compare case-insensitively)"
                )
            )
            raise CompileError(
                f"{collision}; every task must carry a unique id — the later definition "
                "would silently replace the earlier one. Renumber the task in the source"
            )
        seen[key] = task_id


def _admission_evidence(src: dict[str, Any]) -> list[dict[str, Any]]:
    """Return source evidence, or a planned EVID-001 when the seed omitted it.

    Activate seeds historically emit no ``evidence_requirements``. Falling
    back to the first gate id for ``SRC-001.evidence_id`` fails template
    validation (``GATE-*`` is not an evidence id), so pec cannot bootstrap
    even with ``--admission-draft``.
    """
    evidence = [item for item in (src.get("evidence_requirements") or []) if isinstance(item, dict)]
    if evidence:
        return evidence
    host = str(
        (src.get("metadata") or {}).get("intended_host") or resolve_campaign_target_repository(src)
    )
    return [
        {
            "id": "EVID-001",
            "claim": "campaign_source_and_target_origin_main_are_bound",
            "source_type": "repository_inspection",
            "source_location": host,
            "collection_method": "read_only_inspection",
            "freshness": "collect_at_admission",
            "producer": "controller",
            "supports": ["DELTA-001"],
            "contradicts": [],
        }
    ]


VALIDATION_METHODS = frozenset(
    {"command", "inspection", "command_and_inspection", "external_adapter"}
)
# Methods whose `command_or_inspection` is shell. `inspection` is prose and is
# never handed to the shell-command grammar.
_EXECUTABLE_VALIDATION_METHODS = frozenset(
    {"command", "command_and_inspection", "external_adapter"}
)


def _normalized_validation_method(raw: dict[str, Any], task_id: str) -> str:
    """The one method decision, made before preflight or lowering reads the entry.

    Preflight used to read ``method`` verbatim and skip anything not already an
    executable method, while lowering coerced every unrecognized value to
    ``command``. An entry that omitted ``method`` therefore skipped the shell
    grammar during preflight and was executed as shell afterwards -- the two
    stages disagreed about the same entry. The decision is made once, here.

    An omitted method is the legacy executable representation, whether the text
    arrived in the explicit ``command`` field or in ``command_or_inspection``,
    so it normalizes to ``command`` and is grammar-checked as one. A method that
    is declared and unrecognized is a source defect: coercing it to ``command``
    would run text the author never claimed was shell.
    """
    declared = str(raw.get("method") or "").strip()
    if not declared:
        return "command"
    if declared not in VALIDATION_METHODS:
        raise CompileError(
            f"task {task_id!r} validation {raw.get('id')!r} declares method {declared!r}, which "
            f"is not one of {sorted(VALIDATION_METHODS)}. An unknown method is never coerced to "
            "'command' -- name the method the entry actually uses"
        )
    return declared


def normalize_task_validation(item: dict[str, Any], suffix: str) -> list[dict[str, Any]]:
    """The task's validation ledger, normalized once for preflight and lowering.

    Both stages read the entries this returns, so neither can reach a different
    conclusion about a method or its text. The acceptance statement remains the
    fallback for a task that declared no validation at all.
    """
    task_id = str(item.get("id") or "")
    entries: list[dict[str, Any]] = []
    for position, raw in enumerate(item.get("validation") or [], start=1):
        if not isinstance(raw, dict):
            continue
        command = str(raw.get("command_or_inspection") or raw.get("command") or "").strip()
        if not command:
            continue
        entries.append(
            {
                "id": str(raw.get("id") or "").strip() or f"VAL-{suffix}-{position:02d}",
                "method": _normalized_validation_method(raw, task_id),
                "command_or_inspection": command,
                "environment": str(raw.get("environment") or "").strip() or "local",
                "expected_result": "PASS",
            }
        )
    acceptance = item.get("acceptance") or []
    if not entries and acceptance:
        entries.append(
            {
                "id": f"VAL-{suffix}",
                "method": "inspection",
                "command_or_inspection": str(acceptance[0]["statement"]).strip(),
                "environment": ("planning" if item.get("id") == "TASK-001" else "local"),
                "expected_result": "PASS",
            }
        )
    return entries


def _task_validations(item: dict[str, Any], suffix: str) -> list[dict[str, Any]]:
    """Lower exactly the normalized ledger preflight already inspected."""
    return normalize_task_validation(item, suffix)


def _task_kernel_profile(item: dict[str, Any]) -> str:
    """The kernel profile this task executes under, decided once.

    The campaign source admits BUILD / CHANGE / AUDIT, but the Task Card schema
    carried no such field, so the value was dropped at lowering and every task
    reached the Rendered Contract as BUILD -- an authored CHANGE or AUDIT
    silently became something else. Defaulting happens here and nowhere
    downstream, so the value that survives is the value that was authored.
    """
    raw = str(item.get("kernel_profile") or "").strip()
    if not raw:
        return DEFAULT_KERNEL_PROFILE
    if raw not in KERNEL_PROFILES:
        raise CompileError(
            f"task {str(item.get('id'))!r} declares kernel_profile {raw!r}; admitted profiles "
            f"are {list(KERNEL_PROFILES)}"
        )
    return raw


# The Blueprint template schemas are the ID law. Reading the patterns from them
# keeps preflight and the instantiated validator from drifting into two
# competing grammars — the drift that let TASK-001A reach template validation.
TASK_ID_SCHEMA = BLUEPRINT_TEMPLATE / "schemas/task-cards.schema.json"
GATE_ID_SCHEMA = BLUEPRINT_TEMPLATE / "schemas/convergence-gates.schema.json"


def _schema_id_pattern(path: Path, collection: str) -> str:
    """The canonical `id` pattern the instantiated Blueprint validator enforces."""
    schema = json.loads(path.read_text(encoding="utf-8"))
    node = schema.get("properties", {}).get(collection, {})
    pattern = node.get("items", {}).get("properties", {}).get("id", {}).get("pattern")
    if not pattern:
        raise CompileError(
            f"{path.name} declares no {collection}[].id pattern; the Blueprint ID grammar "
            "cannot be sourced and preflight would be guessing"
        )
    return str(pattern)


def blueprint_task_id_pattern() -> str:
    return _schema_id_pattern(TASK_ID_SCHEMA, "tasks")


def blueprint_gate_id_pattern() -> str:
    return _schema_id_pattern(GATE_ID_SCHEMA, "gates")


DECISION_SCHEMA = BLUEPRINT_TEMPLATE / "schemas/decision-register.schema.json"


def blueprint_decision_statuses() -> frozenset[str]:
    """The `decisions[*].status` values the instantiated Decision Register admits."""
    schema = json.loads(DECISION_SCHEMA.read_text(encoding="utf-8"))
    node = schema.get("properties", {}).get("decisions", {})
    enum = node.get("items", {}).get("properties", {}).get("status", {}).get("enum")
    if not isinstance(enum, list) or not enum:
        raise CompileError(
            f"{DECISION_SCHEMA.name} declares no decisions[].status enum; the admitted "
            "decision statuses cannot be sourced and preflight would be guessing"
        )
    return frozenset(str(value) for value in enum)


def effective_authorization_ceiling(item: dict[str, Any]) -> dict[str, Any]:
    """The one authority ceiling a compiled Task Card may carry.

    Downstream authority is an intersection, never a union: the Controller
    Source Contract, the root-Autonomy grant, and the runner each narrow this
    and none of them may add to it. So the narrowing happens once, here, and
    every consumer reads the same effective answer.

    Two narrowings apply. `program_control` writes no repository content and so
    commits none of it, which removes both `local_write` and `commit` whatever
    the source declared. Every action the sealed runner cannot perform is set
    false -- a historical source declaring `push: true` still compiles, it
    simply stops advertising authority that no downstream surface can exercise.
    """
    declared = item.get("authorization_ceiling")
    ceiling = dict(declared) if isinstance(declared, dict) else {}
    if str(item.get("execution_kind") or "").strip() == "program_control":
        ceiling["local_write"] = False
        ceiling["commit"] = False
    for action in PE_FORBIDDEN_ACTIONS:
        ceiling[action] = False
    return ceiling


def _is_mutating_task(item: dict[str, Any]) -> bool:
    """Does this task's effective ceiling permit writing repository content?"""
    return bool(effective_authorization_ceiling(item).get("local_write"))


def _require_consistent_execution_authority(item: dict[str, Any]) -> None:
    """Refuse a repo_local ceiling the runner has no terminal state for.

    Program Execution's terminal effect is a verified local commit. A task
    allowed to mutate the worktree but forbidden to commit has no supported end
    state -- there is no terminal dirty-worktree mode -- so its verified work
    could never be carried anywhere. A task allowed to commit but forbidden to
    write can only commit work it did not author, because the commit boundary
    stages the mutations the task itself produced. Neither shape is executable,
    so neither compiles.
    """
    if str(item.get("execution_kind") or "").strip() != "repo_local":
        return
    ceiling = effective_authorization_ceiling(item)
    local_write = bool(ceiling.get("local_write"))
    commit = bool(ceiling.get("commit"))
    task_id = str(item.get("id") or "")
    if local_write and not commit:
        raise CompileError(
            f"task {task_id!r} permits local_write with commit false. Program Execution has no "
            "terminal dirty-worktree mode, so the verified work would be stranded uncommitted "
            "and the task could never complete. Declare commit true, or make the task "
            "inspection-only by declaring local_write false"
        )
    if commit and not local_write:
        raise CompileError(
            f"task {task_id!r} permits commit with local_write false. The commit boundary stages "
            "the task's own verified mutations, so commit cannot float free of local write. "
            "Declare local_write true, or make the task inspection-only by declaring commit false"
        )


def _alias_value(src: dict[str, Any], path: tuple[str, ...]) -> str:
    node: Any = src
    for key in path:
        if not isinstance(node, dict):
            return ""
        node = node.get(key)
    return str(node or "").strip()


def resolve_campaign_target_repository(src: dict[str, Any]) -> str:
    """The one repository identity a direct campaign source binds execution to.

    `targets[]` is the canonical declaration. The compiler already built the
    Blueprint from it while the runner's seed view resolved its repository from
    `program.target_repository_id` / `metadata.intended_host`, so a source whose
    fields disagreed compiled against one repository and executed against
    another. The aliases are read here only to detect that contradiction; none
    of them is an independent authority.

    The current runner executes one repository per campaign, so zero and
    multiple distinct ids are both refused -- taking the first would invent a
    primary target the source never declared.
    """
    found: list[str] = []
    for entry in src.get("targets") or []:
        if not isinstance(entry, dict):
            continue
        value = str(entry.get("repository_id") or "").strip()
        if value and value not in found:
            found.append(value)
    if not found:
        raise CompileError(
            "campaign source declares no targets[].repository_id; the execution target "
            "repository is never inferred from metadata. Declare the target repository in "
            "targets[]"
        )
    if len(found) > 1:
        raise CompileError(
            f"campaign source declares multiple distinct targets[].repository_id ({found!r}); "
            "the Program Execution runner executes one repository per campaign. Split the "
            "campaign so each one names a single execution repository"
        )
    canonical = found[0]
    for name, path in TARGET_REPOSITORY_ALIASES:
        value = _alias_value(src, path)
        if value and value != canonical:
            raise CompileError(
                f"campaign source binds two different repositories: targets[].repository_id is "
                f"{canonical!r} but {name} is {value!r}. One repository identity owns execution "
                "and targets[] is that authority -- correct the alias or remove it"
            )
    return canonical


def _declared_writable_locations(item: dict[str, Any]) -> list[str]:
    """Writable scope the source actually declared. Never inferred from prose."""
    found: list[str] = []
    for output in item.get("outputs") or []:
        if isinstance(output, dict):
            text = str(output.get("location") or "").strip()
            if text and not text.startswith("receipts/"):
                found.append(text)
    for path in item.get("paths") or []:
        text = str(path or "").strip()
        if text and not text.startswith("receipts/"):
            found.append(text)
    return found


def preflight_campaign_source_document(src: dict[str, Any]) -> list[str]:
    """Deterministic source defects, found before anything is created.

    Pure and read-only: no worktree, no PEC state, no mutation authority, no
    provider execution, no remote call, and the source document is never
    modified. Returns compile warnings; raises CompileError on a defect that
    has no valid compiled representation.

    This is the single authority `campaign-check-input` and `run_campaign`
    both call, so a source cannot pass the check and then fail the run.
    """
    errors = validate_campaign_source(src)
    if errors:
        raise CompileError(
            "campaign source failed schema validation:\n  - " + "\n  - ".join(errors)
        )
    warnings = _semantic_precheck(src)

    task_pattern = re.compile(blueprint_task_id_pattern())
    gate_pattern = re.compile(blueprint_gate_id_pattern())

    for task in src.get("tasks") or []:
        task_id = str(task.get("id") or "")
        if not task_pattern.match(task_id):
            raise CompileError(
                f"task id {task_id!r} does not match the Blueprint task grammar "
                f"{task_pattern.pattern!r}; the instantiated Blueprint validator would "
                "refuse it after isolation and compile. Renumber the task in the source "
                "— ids are never rewritten for you"
            )
        if _is_mutating_task(task) and not _declared_writable_locations(task):
            raise CompileError(
                f"task {task_id!r} permits local_write but declares no outputs[].location "
                "or paths[]; refuse to fabricate writable scope. Declare the exact "
                "repository paths the worker may modify"
            )
        # The exact ledger the Task Card will carry, so preflight cannot skip a
        # command that lowering will execute.
        for entry in normalize_task_validation(task, task_id.split("-")[-1]):
            if entry["method"] not in _EXECUTABLE_VALIDATION_METHODS:
                # Inspection text is prose for a human or the controller to read.
                # It is not shell and must never reach the shell parser.
                continue
            command = entry["command_or_inspection"]
            reason = validation_command_error(command)
            if reason is not None:
                raise CompileError(
                    f"task {task_id!r} validation {entry['id']!r} declares command "
                    f"{command!r}, which the peer permission ceiling refuses: {reason}. "
                    "Declare one shell operation per validation entry"
                )

    for gate in src.get("gates") or []:
        gate_id = str(gate.get("id") or "")
        if not gate_pattern.match(gate_id):
            raise CompileError(
                f"gate id {gate_id!r} does not match the Blueprint gate grammar "
                f"{gate_pattern.pattern!r}; the instantiated Blueprint validator would "
                "refuse it after isolation and compile. Renumber the gate in the source"
            )

    return warnings


def _task_output_locations(item: dict[str, Any]) -> list[str]:
    """Every declared writable path for pec draft-contract.

    `receipts/` is a controller internal, never a worker output. The
    inspection fallback applies only when the task declared no paths.
    """
    locations: list[str] = []

    def add(raw: object) -> None:
        text = str(raw or "").strip()
        if text and not text.startswith("receipts/") and text not in locations:
            locations.append(text)

    for output in item.get("outputs") or []:
        if isinstance(output, dict):
            add(output.get("location"))
    for path in item.get("paths") or []:
        add(path)
    if not locations:
        if _is_mutating_task(item):
            # Fabricating a path here would hand the provider write authority
            # over a file the source never named, and bury the source defect
            # under a plausible-looking receipt. `preflight_campaign_source_document`
            # catches this before isolation; raising here keeps a direct
            # compile_source() call from emitting an empty outputs[] and failing
            # later as an opaque template-schema violation.
            raise CompileError(
                f"task {item['id']!r} permits local_write but declares no "
                "outputs[].location or paths[]; refuse to fabricate writable scope. "
                "Declare the exact repository paths the worker may modify"
            )
        # An inspection/program-control task writes no repository content, so a
        # receipt location is a truthful description of what it produces.
        locations.append(f"docs/program-execution/{item['id']}.md")
    return locations


def _task_output_location(item: dict[str, Any]) -> str:
    """First declared writable path. Contracts use _task_output_locations."""
    return _task_output_locations(item)[0]


def _phase0_gate(
    prog: dict[str, Any], tasks: list[dict[str, Any]], waves: list[dict[str, Any]]
) -> dict[str, Any]:
    """Build the phase-0 completeness gate from compiled program data.

    The template's own GATE-000 references template-only scaffolding (W0 /
    TASK-001 / EVID-002) and must never be re-read from the instantiated tree.
    """
    wave_ids = [wave["id"] for wave in waves if wave.get("id") == "W0"]
    task_ids = [task["id"] for task in tasks if task.get("wave_id") == "W0"]
    return {
        "id": "GATE-000",
        "name": "phase0_user_config_complete",
        "definition_status": "active",
        "owner": prog["owner"],
        "class": "phase0",
        "blocking_class": "true_blocking",
        "scope": {"wave_ids": wave_ids, "task_ids": task_ids},
        "method": {
            "type": "inspection",
            "steps": [
                "Inspect PHASE0_USER_CONFIG.yaml completeness, blocking inventory, "
                "alignment, and operator_ack."
            ],
        },
        "pass_condition": (
            "When program_deploying is false, Phase 0 may remain draft with "
            "phase0_complete false. When program_deploying is true, phase0_complete "
            "is true, stop_conditions_reviewed is true, alignment.uv_lock_check and "
            "toolchain_pin_lockstep are pass or not_applicable, make_pr_gate_required "
            "is true, autonomous_merge is false, and advisory CI is inventoried or waived."
        ),
        "fail_condition": (
            "program_deploying true with incomplete Phase 0, uncleared environmental "
            "stops, or lock/pin misalignment."
        ),
        "blocking": True,
        "required_evidence_ids": [],
        "waiver_allowed": False,
    }


def _bind_stack_proof(src: dict[str, Any], stack_proof: Path | None) -> dict[str, Any]:
    if stack_proof is None:
        raise CompileError("stack-proof receipt is required before compile")
    proof_mod = importlib.util.spec_from_file_location(
        "context7_stack_proof", _SCRIPT_DIR / "context7_stack_proof.py"
    )
    if proof_mod is None or proof_mod.loader is None:
        raise CompileError("cannot load context7_stack_proof")
    module = importlib.util.module_from_spec(proof_mod)
    proof_mod.loader.exec_module(module)
    receipt = module.load_receipt(stack_proof)
    inferred = module.infer_tools(
        {
            "campaign_id": src["metadata"]["campaign_id"],
            "objective": src.get("program", {}).get("objective") or src.get("objective") or "",
            "problem_statement": src.get("program", {}).get("problem_statement") or "",
            "tasks": src.get("tasks") or [],
        }
    )
    errors = module.validate_receipt(receipt, inferred)
    seed_like = {
        "campaign_id": src["metadata"]["campaign_id"],
        "objective": str(src.get("program", {}).get("objective") or src.get("objective") or ""),
        "problem_statement": str(
            src.get("program", {}).get("problem_statement") or src.get("problem_statement") or ""
        ),
        "tasks": src.get("tasks") or [],
    }
    errors.extend(module.seed_contradicts(seed_like, receipt))
    if errors:
        raise CompileError("stack-proof bind failed: " + "; ".join(errors))
    return receipt


def normalize_definition_status(src: dict[str, Any]) -> list[str]:
    """Canonicalize legacy ordering-blocked tasks as `ready` (ADR-0023).

    `definition_status: blocked` combined with dependencies is legacy ordering
    misuse: dependency/wave edges are the ordering authority, and the
    controller has no `blocked → ready` definition transition. Such tasks
    compile as `ready` with their dependencies preserved, and the runtime
    reports the wait as waiting, never as a blocker.

    `blocked` with no dependency to wait on is a runtime dead-end — no
    controller path will ever make the task claimable — so compilation fails
    instead of emitting a permanently unclaimable Task Card.
    """
    notes: list[str] = []
    inbound: dict[str, list[str]] = {}
    for edge in src.get("dependency_edges") or []:
        if isinstance(edge, dict) and edge.get("from") and edge.get("to"):
            inbound.setdefault(str(edge["to"]), []).append(str(edge["from"]))
    for task in src.get("tasks") or []:
        if task.get("definition_status") != "blocked":
            continue
        # Only inbound `dependency_edges`. Task-local `dependencies` /
        # `dependency_ids` aliases are refused in `_semantic_precheck`, so a
        # second ordering representation can never reach this decision.
        dependencies = inbound.get(str(task.get("id"))) or []
        if not dependencies:
            raise CompileError(
                f"task {task['id']!r}: definition_status 'blocked' with no dependencies would "
                "compile into a permanently unclaimable Task Card (the controller has no "
                "blocked → ready definition transition). A complete task definition is "
                "'ready' (ADR-0023); express sequencing through dependencies/waves, and "
                "express real runtime blockers through blocking_unknown_ids, "
                "required_decision_ids, input_evidence_ids, or blocking gates"
            )
        task["definition_status"] = "ready"
        notes.append(
            f"task {task['id']!r}: legacy ordering misuse canonicalized — definition_status "
            f"'blocked' compiled as 'ready'; ordering is enforced by dependencies "
            f"{list(dependencies)!r} (ADR-0023)"
        )
    return notes


def _architecture_lineage(src: dict[str, Any], *, verification: str = "verified") -> dict[str, Any]:
    """Project clause-level architecture lineage into the existing traceability source.

    The `sources` items are already `additionalProperties: true`, so lineage
    rides in the artifact the Blueprint already has rather than in a second,
    competing traceability file. `architecture_source_sha256` is the declared
    document digest, kept apart from `revision` (the compiled bytes), and
    `architecture_source_verification` says whether that claim was re-derived.
    """
    provenance = src.get("intent_provenance")
    if not isinstance(provenance, dict):
        return {}
    items = provenance.get("semantic_items") or []
    return {
        "architecture_source_sha256": str((provenance.get("source") or {}).get("sha256") or ""),
        "architecture_source_verification": verification,
        "architecture_intent": {
            "schema": str(provenance.get("schema") or ""),
            "source_sha256": str((provenance.get("source") or {}).get("sha256") or ""),
            "source_path": str((provenance.get("source") or {}).get("path") or ""),
            "extractor": provenance.get("extractor") or {},
            "coverage": provenance.get("coverage") or {},
            "source_unit_ids": [
                str(unit.get("id")) for unit in provenance.get("source_units") or []
            ],
            "clauses": [
                {
                    "semantic_id": str(item.get("id")),
                    "kind": str(item.get("kind") or ""),
                    "source_refs": [str(ref) for ref in item.get("source_refs") or []],
                    "campaign_mappings": [
                        str(mapping.get("task_id") or mapping.get("id") or mapping.get("kind"))
                        for mapping in item.get("campaign_mappings") or []
                    ],
                }
                for item in items
                if str(item.get("materiality") or "material") == "material"
            ],
        },
    }


def compile_source(
    source: Path,
    target: Path,
    *,
    stamp: str | None = None,
    stack_proof: Path | None = None,
) -> dict[str, Any]:
    """Compile `source` into `target`, which only ever holds a validated tree.

    Every artifact is written into a staging directory beside `target`, the
    placeholder scan and template validation run there, and only a tree that
    passed is swapped into place. A compile that fails validation used to leave
    its partial output at `target`; the campaign runner quarantined it, the CLI
    left it for the next reader to mistake for a blueprint.
    """
    source = source.resolve()
    target = target.resolve()
    staging = target.with_name(f".{target.name}.compiling-{os.getpid()}")
    if staging.exists():
        shutil.rmtree(staging)
    if target.is_dir():
        # Recompiling in place keeps the files a compile does not regenerate
        # (acceptance receipts, collected evidence); stage from a copy.
        shutil.copytree(target, staging, symlinks=True)
    try:
        result = _compile_into(source, staging, stamp=stamp, stack_proof=stack_proof)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    previous = target.with_name(f".{target.name}.previous-{os.getpid()}")
    if previous.exists():
        shutil.rmtree(previous)
    if target.exists():
        target.rename(previous)
    try:
        staging.rename(target)
    except BaseException:
        if previous.exists() and not target.exists():
            previous.rename(target)
        raise
    shutil.rmtree(previous, ignore_errors=True)
    result["target"] = str(target)
    return result


def _compile_into(
    source: Path,
    target: Path,
    *,
    stamp: str | None,
    stack_proof: Path | None,
) -> dict[str, Any]:
    src = load_yaml(source)
    if not isinstance(src, dict):
        raise CompileError("campaign source must be an object")
    schema_errors = validate_campaign_source(src)
    if schema_errors:
        raise CompileError("campaign source schema: " + "; ".join(schema_errors))
    campaign_id = src["metadata"]["campaign_id"]
    # No preregistration. A campaign compiles because it is valid, not because
    # its id was listed somewhere first; identity collisions are answered from
    # real state at id allocation, which is a different question from admission.
    provenance_warnings = validate_intent_provenance(src)
    # Source defects are decided before the stack-proof receipt is bound, so an
    # unexecutable source is refused with nothing bound and nothing created.
    warnings = _semantic_precheck(src)
    stack_receipt = _bind_stack_proof(src, stack_proof)
    warnings.extend(provenance_warnings)
    warnings.extend(normalize_definition_status(src))
    now = stamp or utc_now()
    ensure_instantiated(target, src, now)
    prog = src["program"]
    patch_phase0_operator_name(target, str(prog["owner"]))
    tasks = list(src.get("tasks") or [])
    gates = list(src.get("gates") or [])
    waves = list(src.get("waves") or [])
    workstreams = list(src.get("workstreams") or [])
    task_by_id = {item["id"]: item for item in tasks}
    compiled_from = source.as_posix()
    repo_rel = ""
    try:
        repo_rel = source.relative_to(PE_ROOT.parents[1]).as_posix()
    except ValueError:
        repo_rel = source.name

    dump_yaml(
        target / "PROGRAM.yaml",
        {
            "schema": "program-execution-blueprint.program.v2",
            "schema_version": "2.0.0",
            "program": {
                "id": prog["id"],
                "name": prog["name"],
                "version": prog.get("version") or "1.0.0",
                "owner": prog["owner"],
                "definition_status": "draft",
                "snapshot_at": now,
                "objective": str(prog["objective"]).strip(),
                "problem_statement": str(prog["problem_statement"]).strip(),
                "target_state": str(prog["target_state"]).strip(),
                "scope": prog["scope"],
                "contracts": _program_contracts(prog),
                "authority_order": prog["authority_order"],
                "operating_rules": prog["operating_rules"],
                "terminal_verdicts": prog["terminal_verdicts"],
            },
        },
    )

    compiled_targets = []
    for item in src.get("targets") or []:
        mapped = dict(item)
        # Source-only metadata: the Blueprint target schema has
        # additionalProperties: false and no default_branch field.
        mapped.pop("default_branch", None)
        adapter = str(mapped.get("adapter") or "git")
        mapped["adapter"] = _remap_adapter(adapter)
        compiled_targets.append(mapped)
    dump_yaml(
        target / "EXECUTION_TARGETS.yaml",
        {
            "schema": "program-execution-blueprint.execution-targets.v2",
            "schema_version": "2.0.0",
            "targets": compiled_targets,
        },
    )

    # Ids are read from the source, never minted: a fabricated GATE-001 failed
    # late as an "unresolved reference" the operator never wrote, and a
    # fabricated AUTH-005 shipped silently.
    if not compiled_targets:
        raise CompileError("campaign source declares no execution targets")
    if not gates:
        raise CompileError(
            "campaign source declares no gates; every authority, workstream and cutover "
            "step must reference a gate the source defines"
        )
    first_target = compiled_targets[0]["id"]
    first_gate = gates[0]["id"]
    first_authority = _first_authority_id(src)
    responsibilities = []
    for auth in src.get("authorities") or []:
        _require_auth(auth)
        responsibilities.append(
            {
                "id": auth["id"],
                "responsibility": auth["responsibility"],
                "owner_target_id": first_target,
                "source_of_truth": str(auth["owner"]),
                "consumers": ["controller", "workers", "verifiers"],
                "allowed_roles": ["authority"],
                "prohibited_owner_target_ids": [],
                "enforcement": ["schema", "tests", "controller_import"],
                "validation_gate_ids": list(auth.get("validation_gate_ids") or [first_gate]),
                "definition_status": "active",
            }
        )
    dump_yaml(
        target / "AUTHORITY_REGISTRY.yaml",
        {
            "schema": "program-execution-blueprint.authority-registry.v2",
            "schema_version": "2.0.0",
            "policy": {
                "one_owner_per_responsibility": True,
                "projection_does_not_transfer_authority": True,
                "unresolved_conflict_result": "BLOCKED",
            },
            "responsibilities": responsibilities,
        },
    )

    dump_yaml(
        target / "DECISION_REGISTER.yaml",
        {
            "schema": "program-execution-blueprint.decision-register.v2",
            "schema_version": "2.0.0",
            "policy": "No blocked decision may be silently defaulted.",
            "decisions": [
                {
                    "id": item["id"],
                    "question": item["question"],
                    "status": item["status"],
                    "owner": item.get("authority_id") or prog["owner"],
                    "options": [
                        {
                            "id": option["id"],
                            "description": option["description"],
                            "benefits": [option["description"]],
                            "risks": ["Rejected alternative would violate accepted ADRs."],
                        }
                        for option in item.get("options") or []
                    ],
                    "selected_option": item.get("selected_option_id"),
                    "rationale": _decision_rationale(item),
                    "evidence_ids": list(item.get("required_evidence_ids") or []),
                    "blocks": list(item.get("blocking_task_ids") or []),
                    "required_by": _decision_authority(item, src),
                    "supersedes": None,
                }
                for item in src.get("decisions") or []
            ],
        },
    )

    dump_yaml(
        target / "UNKNOWN_REGISTER.yaml",
        {
            "schema": "program-execution-blueprint.unknown-register.v2",
            "schema_version": "2.0.0",
            "policy": "Unknowns remain explicit and block only named work.",
            "unknowns": [
                {
                    "id": item["id"],
                    "topic": str(item["statement"]).strip(),
                    "owner": item["owner"],
                    "blocks": list(item.get("blocking_task_ids") or []),
                    "safe_state": (
                        "Do not execute named dependent tasks until evidence-bound resolution."
                    ),
                    "resolution_requirements": [str(item["resolution_method"]).strip()],
                    "resolution_evidence_ids": list(item.get("resolution_evidence_ids") or []),
                    "status": item["status"],
                    "resolved_at": None,
                }
                for item in src.get("unknowns") or []
            ],
        },
    )

    dump_yaml(
        target / "RISK_REGISTER.yaml",
        {
            "schema": "program-execution-blueprint.risk-register.v2",
            "schema_version": "2.0.0",
            "risks": [
                {
                    "id": item["id"],
                    "risk": item["statement"],
                    "severity": SEVERITY.get(item.get("impact"), "high"),
                    "likelihood": LIKELIHOOD.get(
                        item.get("likelihood"),
                        item.get("likelihood") or "UNKNOWN",
                    ),
                    "owner": item["owner"],
                    "trigger": item["statement"],
                    "preventive_controls": list(item.get("mitigations") or ["inspect"]),
                    "contingency": [
                        "halt_named_subgraph",
                        "preserve_previous_valid_plan",
                    ],
                    "related_tasks": [task["id"] for task in tasks],
                    "related_gates": [gate["id"] for gate in gates],
                    "acceptance_decision_id": None,
                    "status": "open",
                }
                for item in src.get("risks") or []
            ],
        },
    )

    dump_yaml(
        target / "WAIVER_REGISTER.yaml",
        {
            "schema": "program-execution-blueprint.waiver-register.v2",
            "schema_version": "2.0.0",
            "policy": {
                "implicit_waivers_forbidden": True,
                "expired_waiver_non_passing": True,
            },
            "waivers": list(src.get("waivers") or []),
        },
    )

    evidence = _admission_evidence(src)
    dump_yaml(
        target / "EVIDENCE_CATALOG.yaml",
        {
            "schema": "program-execution-blueprint.evidence-catalog.v2",
            "schema_version": "2.0.0",
            "evidence": [
                {
                    "id": item["id"],
                    "type": EVIDENCE_TYPE.get(item.get("source_type"), "other"),
                    "source": item.get("source_location") or item.get("claim"),
                    "revision": "UNKNOWN",
                    "digest": None,
                    "method": item.get("collection_method") or "inspection",
                    "environment": "planning",
                    "producer": str(item.get("producer") or "controller"),
                    "produced_at": now,
                    "expires_at": None,
                    "result": "INFORMATIONAL",
                    "status": "planned",
                    "supports": list(item.get("supports") or []),
                    "contradicts": list(item.get("contradicts") or []),
                    "notes": item.get("claim"),
                }
                for item in evidence
            ],
        },
    )

    dump_yaml(
        target / "DO_NOT_BUILD.yaml",
        {
            "schema": "program-execution-blueprint.do-not-build.v2",
            "schema_version": "2.0.0",
            "prohibited_primary_paths": [
                # W8/S1: a prohibition is either a path the Controller can match
                # or a law it cannot. Writing a law into path_or_pattern did not
                # enforce it - it made do_not_build PASS having matched nothing.
                prohibition_entry(
                    identifier=item["id"],
                    statement=item["statement"],
                    reason=item["rationale"],
                    detection="review_and_conformance",
                    exception_authority="NONE",
                )
                for item in src.get("prohibited_paths") or []
            ],
            "allowed_experiments": [
                {
                    "id": "EXP-001",
                    "scope": f"Isolated $HOME/.l9/programs/{campaign_id} only",
                    "constraints": [
                        "must_not_become_production_authority",
                        "must_be_disposable",
                        "must_be_labeled_experimental",
                    ],
                    "expiry": now,
                }
            ],
        },
    )

    dump_yaml(
        target / "CURRENT_STATE_DELTA.yaml",
        {
            "schema": "program-execution-blueprint.current-state-delta.v2",
            "schema_version": "2.0.0",
            "snapshot_at": now,
            "freshness_policy": {
                "maximum_age": "admission_window",
                "stale_result": "BLOCKED",
            },
            "sources": [
                {
                    "source_id": f"SRC-{index:03d}",
                    "evidence_id": item["id"],
                    "revision": "UNKNOWN",
                    "freshness": "collect_at_admission",
                }
                for index, item in enumerate(evidence[:5], start=1)
            ],
            "deltas": [
                {
                    "id": "DELTA-001",
                    "target_id": first_target,
                    "expected_state": "Native Blueprint compiled",
                    "observed_state": "Campaign source registered",
                    "classification": "UNKNOWN",
                    "impact": "Admission remains blocking",
                    "required_action": "Collect planned evidence",
                    "evidence_ids": [item["id"] for item in evidence[:5]],
                }
            ],
            "next_blocking_action": "Collect admission evidence.",
        },
    )

    ws_exit: dict[str, list[str]] = {}
    for wave in waves:
        for task_id in wave.get("task_ids") or []:
            workstream = task_by_id.get(task_id, {}).get("workstream_id")
            if workstream:
                ws_exit.setdefault(workstream, [])
                for gate_id in wave.get("exit_gate_ids") or []:
                    if gate_id not in ws_exit[workstream]:
                        ws_exit[workstream].append(gate_id)
    dump_yaml(
        target / "WORKSTREAMS.yaml",
        {
            "schema": "program-execution-blueprint.workstreams.v2",
            "schema_version": "2.0.0",
            "workstreams": [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "objective": str(item["objective"]).strip(),
                    "owner": item["owner"],
                    "target_ids": [first_target],
                    "scope": {
                        "include": [str(item["objective"]).strip()],
                        "exclude": ["remote mutation", "merge", "deploy"],
                    },
                    "inputs": ["CAMPAIGN_SOURCE.yaml"],
                    "outputs": ["task receipts", "gate evidence"],
                    "entry_gate_ids": [] if item["id"] == workstreams[0]["id"] else [first_gate],
                    "exit_gate_ids": ws_exit.get(item["id"]) or [first_gate],
                    "rollback_boundary": (
                        "Discard unaccepted generated artifacts; no remote mutation."
                    ),
                    "definition_status": "active",
                }
                for item in workstreams
            ],
        },
    )

    edges = []
    for index, edge in enumerate(src.get("dependency_edges") or [], start=1):
        predecessor = task_by_id.get(edge["from"], {})
        edges.append(
            {
                "id": f"EDGE-{index:03d}",
                "from": edge["from"],
                "to": edge["to"],
                "relation": "requires",
                "blocking": True,
                "proof_gate_ids": predecessor.get("completion_gate_ids") or [],
            }
        )
    wave_groups = [
        list(wave.get("task_ids") or []) for wave in waves if len(wave.get("task_ids") or []) > 1
    ]
    dump_yaml(
        target / "DEPENDENCY_GRAPH.yaml",
        {
            "schema": "program-execution-blueprint.dependency-graph.v2",
            "schema_version": "2.0.0",
            "direction": "predecessor_to_successor",
            "nodes": [
                {
                    "id": item["id"],
                    "entity_type": "task",
                    "owner": _task_owner_authority(item, first_authority),
                }
                for item in tasks
            ],
            "edges": edges,
            "critical_path": [item["id"] for item in tasks],
            "parallelizable_groups": wave_groups,
            "hard_rule": ("No successor may bypass a predecessor by reproducing its output."),
        },
    )

    compiled_waves = []
    for index, wave in enumerate(waves):
        ws_ids = sorted(
            {
                task_by_id[task_id]["workstream_id"]
                for task_id in wave.get("task_ids") or []
                if task_id in task_by_id
            }
        )
        compiled_waves.append(
            {
                "id": wave["id"],
                "name": wave["name"],
                "sequence": index,
                "depends_on": list(wave.get("predecessor_wave_ids") or []),
                "workstream_ids": ws_ids,
                "task_ids": list(wave.get("task_ids") or []),
                "entry_gate_ids": [],
                "exit_gate_ids": list(wave.get("exit_gate_ids") or []),
                "rollback_boundary": ("Restore worktree to Program Lock base; preserve receipts."),
                "definition_status": "active",
            }
        )
    dump_yaml(
        target / "EXECUTION_WAVES.yaml",
        {
            "schema": "program-execution-blueprint.execution-waves.v2",
            "schema_version": "2.0.0",
            "promotion_rule": (
                "A wave starts only when prior waves and blocking entry gates pass."
            ),
            "waves": compiled_waves,
        },
    )

    compiled_tasks = []
    for item in tasks:
        ceiling = effective_authorization_ceiling(item)
        suffix = item["id"].split("-")[-1]
        output_locations = _task_output_locations(item)
        compiled_tasks.append(
            {
                "id": item["id"],
                "title": item["title"],
                "definition_status": item["definition_status"],
                "workstream_id": item["workstream_id"],
                "wave_id": item["wave_id"],
                "target_id": item["target_id"],
                "execution_kind": item["execution_kind"],
                "kernel_profile": _task_kernel_profile(item),
                "objective": str(item["objective"]).strip(),
                "authority_basis_ids": item["authority_basis_ids"],
                "required_decision_ids": item.get("required_decision_ids") or [],
                "blocking_unknown_ids": item.get("blocking_unknown_ids") or [],
                "input_evidence_ids": item.get("input_evidence_ids") or [],
                "actions": item["actions"],
                "outputs": [
                    {
                        "id": (
                            f"OUT-{suffix}"
                            if len(output_locations) == 1
                            else f"OUT-{suffix}-{position:02d}"
                        ),
                        "type": "receipt",
                        "location": location,
                        "required": True,
                    }
                    for position, location in enumerate(output_locations, start=1)
                ],
                "acceptance": item["acceptance"],
                "validation": _task_validations(item, suffix),
                "negative_cases": item["negative_cases"],
                "rollback": item["rollback"],
                "risk": item["risk"],
                "authorization_ceiling": ceiling,
                "completion_gate_ids": item["completion_gate_ids"],
            }
        )
    dump_yaml(
        target / "TASK_CARDS.yaml",
        {
            "schema": "program-execution-blueprint.task-cards.v2",
            "schema_version": "2.0.0",
            "tasks": compiled_tasks,
        },
    )

    class_map = {"entry": "authority", "completion": "validation"}
    compiled_gates = [_phase0_gate(prog, tasks, waves)]
    for item in gates:
        wave_ids = [wave["id"] for wave in waves if item["id"] in (wave.get("exit_gate_ids") or [])]
        compiled_gates.append(
            {
                "id": item["id"],
                "name": item["name"],
                "definition_status": "active",
                "owner": item.get("owner_authority_id") or prog["owner"],
                "class": class_map.get(item.get("gate_type"), "validation"),
                "scope": {
                    "wave_ids": wave_ids,
                    "task_ids": list(item.get("task_ids") or []),
                },
                "method": {
                    "type": "inspection",
                    "steps": list(item.get("pass_criteria") or ["Inspect required evidence."]),
                },
                "pass_condition": "; ".join(item.get("pass_criteria") or ["PASS"]),
                "fail_condition": str(item.get("failure_effect") or "BLOCKED"),
                "blocking": bool(item.get("blocking", True)),
                "required_evidence_ids": list(item.get("required_evidence_ids") or []),
                "waiver_allowed": False,
            }
        )
    dump_yaml(
        target / "CONVERGENCE_GATES.yaml",
        {
            "schema": "program-execution-blueprint.convergence-gates.v2",
            "schema_version": "2.0.0",
            "result_values": [
                "PASS",
                "FAIL",
                "BLOCKED",
                "UNKNOWN",
                "NOT_APPLICABLE_WITH_REASON",
            ],
            "unknown_is_non_passing": True,
            "gates": compiled_gates,
        },
    )

    obs = src.get("observability") or {}
    fields = list(obs.get("program_progress_fields") or obs.keys() or ["progress"])
    dump_yaml(
        target / "OBSERVABILITY_PLAN.yaml",
        {
            "schema": "program-execution-blueprint.observability-plan.v2",
            "schema_version": "2.0.0",
            "signals": [
                {
                    "id": f"OBS-{index:03d}",
                    "name": name,
                    "owner": first_authority,
                    "source_target_id": first_target,
                    "collection_method": "controller_projection",
                    "expected_range": "defined",
                    "alert_condition": "missing_or_stale",
                    "retention": "program_lifetime",
                    "related_gate_ids": [first_gate],
                    "status": "planned",
                }
                for index, name in enumerate(fields[:8], start=1)
            ],
            "incident_routing": [
                {
                    "condition": "blocking_signal_breach",
                    "owner": prog["owner"],
                    "action": "pause_affected_wave_and_preserve_evidence",
                }
            ],
        },
    )

    cut = src.get("cutover_and_rollback") or {}
    dump_yaml(
        target / "CUTOVER_AND_ROLLBACK.yaml",
        {
            "schema": "program-execution-blueprint.cutover-and-rollback.v2",
            "schema_version": "2.0.0",
            "cutover": {
                "required_gate_ids": [item["id"] for item in gates[-2:]] or [first_gate],
                "approval_action": "publish_or_release",
                "steps": list(cut.get("preconditions") or ["accepted_blueprint"]),
                "abort_conditions": ["blocking_gate_failure", "parity_failure"],
                "observation_window": "until_handoff",
            },
            "rollback": {
                "trigger_conditions": [
                    "blocking_gate_failure",
                    "authority_containment_failure",
                ],
                "steps": list(cut.get("rollback_rules") or ["preserve_failed_replan_evidence"]),
                "data_reconciliation": "append_only_receipts_never_rewritten",
                "validation": ["prior_evidence_unchanged"],
                "owner": first_authority,
            },
        },
    )

    dump_yaml(
        target / "SOURCE_TRACEABILITY.yaml",
        {
            "schema": "program-execution-blueprint.source-traceability.v2",
            "schema_version": "2.0.0",
            "authority_classes": [
                "governing",
                "supporting",
                "contradicting",
                "example",
                "historical",
                "inferred",
            ],
            "sources": [
                {
                    "id": "SRC-001",
                    "source": repo_rel or source.name,
                    "revision": _source_revision(source),
                    "authority_class": "governing",
                    "evidence_id": evidence[0]["id"],
                    "claims": [
                        "Campaign source is the immutable operator intent.",
                        "Stack-proof receipt bound before compile.",
                    ],
                    "stack_proof": {
                        "path": str(stack_proof),
                        "status": stack_receipt.get("status"),
                        "tools": [
                            item.get("name")
                            for item in (stack_receipt.get("tools") or [])
                            if isinstance(item, dict)
                        ],
                        "constraints": [
                            constraint
                            for item in (stack_receipt.get("tools") or [])
                            if isinstance(item, dict)
                            for constraint in (item.get("constraints") or [])
                        ],
                    },
                    "target_ids": [first_target],
                    "workstream_ids": [item["id"] for item in workstreams],
                    "task_ids": [item["id"] for item in tasks],
                    "gate_ids": [item["id"] for item in gates],
                    "status": "active",
                    **_architecture_lineage(
                        src,
                        verification=(
                            "unverifiable"
                            if any(
                                warning.startswith(ARCHITECTURE_SOURCE_UNVERIFIABLE)
                                for warning in provenance_warnings
                            )
                            else "verified"
                        ),
                    ),
                }
            ],
        },
    )

    (target / "EXECUTIVE_DECISION.md").write_text(
        "\n".join(
            [
                f"# Executive Decision: {prog['name']}",
                "",
                "## Decision",
                "",
                str(prog["objective"]).strip(),
                "",
                "## Problem being resolved",
                "",
                str(prog["problem_statement"]).strip(),
                "",
                "## Target state",
                "",
                str(prog["target_state"]).strip(),
                "",
                "## Authority assignment",
                "",
                "Reference `AUTHORITY_REGISTRY.yaml`.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_manifest(target, repo_rel or compiled_from)
    placeholder_errors = scan_placeholders(target)
    if placeholder_errors:
        raise CompileError(
            "unresolved placeholders in compiled blueprint: " + "; ".join(placeholder_errors[:5])
        )
    validation_errors = validate_blueprint_artifact(target, "template")
    if validation_errors:
        raise CompileError(
            "compiled blueprint failed template validation: " + "; ".join(validation_errors[:5])
        )
    return {
        "campaign_id": campaign_id,
        "target": str(target),
        "compiled_from": repo_rel or compiled_from,
        "task_count": len(compiled_tasks),
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="compile_campaign_source")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--stack-proof", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        result = compile_source(
            args.source,
            args.target,
            stack_proof=args.stack_proof,
        )
    except CompileError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
