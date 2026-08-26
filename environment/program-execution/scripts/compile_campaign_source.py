#!/usr/bin/env python3
"""Compile a campaign-source.v2 seed into a Blueprint v2 pair."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
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
if str(_PE_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(_PE_ROOT_FOR_IMPORT))

from peer_execution.validation_command import validation_command_error  # noqa: E402

PE_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PE_ROOT / "core/shared/schemas/campaign-source.schema.json"
ALLOWLIST_PATH = PE_ROOT / "campaigns/COMPILE_ALLOWLIST.yaml"
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
TASK_STATUSES_ADMITTED = {"ready", "blocked", "cancelled", "superseded"}


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


def load_allowlist(path: Path | None = None) -> set[str]:
    raw = load_yaml(path or ALLOWLIST_PATH)
    ids = raw.get("campaign_ids") if isinstance(raw, dict) else None
    if not isinstance(ids, list) or not ids:
        raise CompileError("COMPILE_ALLOWLIST.yaml has no campaign_ids")
    return {str(item) for item in ids}


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


def _require_auth(item: dict[str, Any]) -> None:
    missing = [key for key in AUTH_REQUIRED if not item.get(key)]
    if missing:
        raise CompileError(f"authority missing required keys: {missing}")


def _semantic_precheck(src: dict[str, Any]) -> list[str]:
    """Fail loudly on source shapes that have no valid compiled representation.

    Run before any artifact is written. Returns compile warnings.
    """
    warnings: list[str] = []
    for decision in src.get("decisions") or []:
        if not decision.get("options"):
            raise CompileError(
                f"decision {decision['id']!r} has no options array; every decision requires "
                "source-side options (id + description) because the Blueprint Decision "
                "Register mandates non-empty options — fix the source, never synthesize "
                "options in the compiled artifact"
            )
    for task in src.get("tasks") or []:
        status = task.get("definition_status")
        if status not in TASK_STATUSES_ADMITTED:
            raise CompileError(
                f"task {task['id']!r}: definition_status {status!r} is not admitted by the "
                f"instantiated Blueprint validator ({sorted(TASK_STATUSES_ADMITTED)}); "
                "fix the source"
            )
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
    host = str((src.get("metadata") or {}).get("intended_host") or "UNKNOWN")
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


def _task_validations(item: dict[str, Any], suffix: str) -> list[dict[str, Any]]:
    """Carry the seed's validation entries into the Task Card unchanged.

    Flattening every entry to ``method: inspection`` dropped the seed's shell
    commands, so the Blueprint carried no ``required_validation_commands``, the
    Rendered Contract carried none, and pec verify returned INCOMPLETE for every
    task with nothing to run. The Task Cards schema admits ``command``, so pass
    the declared command through and keep the acceptance statement only as the
    fallback for a task that declared no validation.
    """
    entries: list[dict[str, Any]] = []
    for position, raw in enumerate(item.get("validation") or [], start=1):
        if not isinstance(raw, dict):
            continue
        command = str(raw.get("command_or_inspection") or raw.get("command") or "").strip()
        if not command:
            continue
        method = str(raw.get("method") or "").strip()
        if method not in VALIDATION_METHODS:
            method = "command"
        entries.append(
            {
                "id": str(raw.get("id") or "").strip() or f"VAL-{suffix}-{position:02d}",
                "method": method,
                "command_or_inspection": command,
                "environment": str(raw.get("environment") or "").strip() or "local",
                "expected_result": "PASS",
            }
        )
    if not entries:
        entries.append(
            {
                "id": f"VAL-{suffix}",
                "method": "inspection",
                "command_or_inspection": str(item["acceptance"][0]["statement"]).strip(),
                "environment": ("planning" if item["id"] == "TASK-001" else "local"),
                "expected_result": "PASS",
            }
        )
    return entries


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


def _is_mutating_task(item: dict[str, Any]) -> bool:
    """Does this task's effective ceiling permit writing repository content?

    `program_control` has its local_write removed at compile time regardless of
    what the source declared, so the effective ceiling — not the declared one —
    decides.
    """
    if str(item.get("execution_kind") or "").strip() == "program_control":
        return False
    ceiling = item.get("authorization_ceiling") or {}
    return bool(ceiling.get("local_write")) if isinstance(ceiling, dict) else False


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
        for entry in task.get("validation") or []:
            if not isinstance(entry, dict):
                continue
            method = str(entry.get("method") or "").strip()
            if method not in _EXECUTABLE_VALIDATION_METHODS:
                # Inspection text is prose for a human or the controller to read.
                # It is not shell and must never reach the shell parser.
                continue
            command = str(entry.get("command_or_inspection") or entry.get("command") or "").strip()
            if not command:
                continue
            reason = validation_command_error(command)
            if reason is not None:
                raise CompileError(
                    f"task {task_id!r} validation {entry.get('id')!r} declares command "
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
        dependencies = (
            task.get("dependency_ids")
            or task.get("dependencies")
            or inbound.get(str(task.get("id")))
            or []
        )
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


def compile_source(
    source: Path,
    target: Path,
    *,
    stamp: str | None = None,
    allowlist_path: Path | None = None,
    stack_proof: Path | None = None,
) -> dict[str, Any]:
    source = source.resolve()
    target = target.resolve()
    src = load_yaml(source)
    if not isinstance(src, dict):
        raise CompileError("campaign source must be an object")
    schema_errors = validate_campaign_source(src)
    if schema_errors:
        raise CompileError("campaign source schema: " + "; ".join(schema_errors))
    campaign_id = src["metadata"]["campaign_id"]
    allowed = load_allowlist(allowlist_path)
    if campaign_id not in allowed:
        raise CompileError(f"campaign {campaign_id} is not in COMPILE_ALLOWLIST.yaml")
    stack_receipt = _bind_stack_proof(src, stack_proof)
    warnings = _semantic_precheck(src)
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

    first_target = compiled_targets[0]["id"] if compiled_targets else "TARGET-001"
    first_gate = gates[0]["id"] if gates else "GATE-001"
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
                    "rationale": (
                        f"Selected {item.get('selected_option_id')} per {item.get('authority_id')}."
                    ),
                    "evidence_ids": list(item.get("required_evidence_ids") or []),
                    "blocks": list(item.get("blocking_task_ids") or []),
                    "required_by": item.get("authority_id") or "AUTH-005",
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
                {
                    "id": item["id"],
                    "path_or_pattern": item["statement"],
                    "reason": item["rationale"],
                    "detection": "review_and_conformance",
                    "exception_authority": "NONE",
                }
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
                    "owner": (item.get("authority_basis_ids") or ["AUTH-001"])[0],
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
        ceiling = dict(item.get("authorization_ceiling") or {})
        if item.get("execution_kind") == "program_control":
            ceiling["local_write"] = False
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
                    "owner": "AUTH-002",
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
                "owner": "AUTH-001",
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
                    "revision": src.get("integrity", {}).get("digest_algorithm", "sha256"),
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
    parser.add_argument("--allowlist", type=Path, default=None)
    parser.add_argument("--stack-proof", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        result = compile_source(
            args.source,
            args.target,
            allowlist_path=args.allowlist,
            stack_proof=args.stack_proof,
        )
    except CompileError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
