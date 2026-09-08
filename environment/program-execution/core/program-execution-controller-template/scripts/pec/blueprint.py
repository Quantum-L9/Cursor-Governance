from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .common import (
    digest_object,
    load_yaml,
    sha256_file,
    utc_now,
    verification_mechanisms_from_card,
    write_json,
)

LOCK_SCHEMA = Path(__file__).resolve().parents[2] / "schemas" / "program-lock.schema.json"


class BlueprintError(RuntimeError):
    def __init__(self, message: str, *, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


def _load(root: Path, name: str) -> Any:
    path = root / name
    if not path.is_file():
        raise BlueprintError(f"missing blueprint file: {name}")
    try:
        return load_yaml(path)
    except Exception as exc:
        raise BlueprintError(f"failed to parse {name}: {exc}") from exc


def normalize_blueprint(root: Path) -> dict[str, Any]:
    root = root.resolve()
    index = _load(root, "EXECUTION_INDEX.yaml")
    if index.get("blueprint_contract") != "program-execution-blueprint.v2":
        raise BlueprintError(
            "unsupported Blueprint contract; expected program-execution-blueprint.v2"
        )
    required = list(index.get("required_sources") or [])
    if not required:
        raise BlueprintError("EXECUTION_INDEX.yaml has no required_sources")
    data = {name: _load(root, name) for name in required}
    source_digests = {"EXECUTION_INDEX.yaml": sha256_file(root / "EXECUTION_INDEX.yaml")}
    source_digests.update({name: sha256_file(root / name) for name in required})

    program = data["PROGRAM.yaml"].get("program") or {}
    contracts = program.get("contracts") or {}
    if contracts.get("blueprint") != "program-execution-blueprint.v2":
        raise BlueprintError("PROGRAM.yaml Blueprint contract mismatch")
    if contracts.get("pair") != "program-execution-system.v2":
        raise BlueprintError("PROGRAM.yaml pair contract mismatch")

    targets = data["EXECUTION_TARGETS.yaml"].get("targets") or []
    target_map = {item["id"]: item for item in targets}
    graph = data["DEPENDENCY_GRAPH.yaml"]
    inbound: dict[str, list[str]] = {}
    for edge in graph.get("edges") or []:
        if edge.get("blocking", True):
            inbound.setdefault(edge["to"], []).append(edge["from"])

    tasks: list[dict[str, Any]] = []
    for raw in data["TASK_CARDS.yaml"].get("tasks") or []:
        target = target_map.get(raw["target_id"])
        if target is None:
            raise BlueprintError(f"task {raw['id']} references unknown target {raw['target_id']}")
        execution_kind = raw["execution_kind"]
        repository_id = target.get("repository_id") if execution_kind == "repo_local" else None
        verification_mechanisms = verification_mechanisms_from_card(raw)
        required_commands = [
            item["command_or_inspection"]
            for item in verification_mechanisms
            if item.get("method") in {"command", "command_and_inspection"}
        ]
        tasks.append(
            {
                "id": raw["id"],
                "title": raw["title"],
                "definition_status": raw["definition_status"],
                "wave_id": raw["wave_id"],
                "workstream_id": raw["workstream_id"],
                "target_id": raw["target_id"],
                "repository_id": repository_id,
                "execution_kind": execution_kind,
                "objective": raw["objective"],
                "dependencies": sorted(set(inbound.get(raw["id"], []))),
                "required_decisions": list(raw.get("required_decision_ids") or []),
                "blocking_unknowns": list(raw.get("blocking_unknown_ids") or []),
                "required_evidence": list(raw.get("input_evidence_ids") or []),
                "completion_gates": list(raw.get("completion_gate_ids") or []),
                "authorization_ceiling": dict(raw.get("authorization_ceiling") or {}),
                "required_acceptance": [item["id"] for item in raw.get("acceptance") or []],
                "verification_mechanisms": verification_mechanisms,
                "required_validation_commands": required_commands,
                "risk_tier": (raw.get("risk") or {}).get("tier", "T2"),
                "source": raw,
            }
        )

    body = {
        "schema": "program-execution-controller.program-lock.v2",
        "created_at": utc_now(),
        "blueprint_root": str(root),
        "blueprint_contract": "program-execution-blueprint.v2",
        "program": program,
        "source_digests": source_digests,
        "targets": targets,
        "authority": data["AUTHORITY_REGISTRY.yaml"],
        "decisions": data["DECISION_REGISTER.yaml"].get("decisions") or [],
        "unknowns": data["UNKNOWN_REGISTER.yaml"].get("unknowns") or [],
        "risks": data["RISK_REGISTER.yaml"].get("risks") or [],
        "waivers": data["WAIVER_REGISTER.yaml"].get("waivers") or [],
        "evidence": data["EVIDENCE_CATALOG.yaml"].get("evidence") or [],
        "do_not_build": data["DO_NOT_BUILD.yaml"],
        "current_state": data["CURRENT_STATE_DELTA.yaml"],
        "workstreams": data["WORKSTREAMS.yaml"].get("workstreams") or [],
        "dependency_graph": graph,
        "waves": data["EXECUTION_WAVES.yaml"].get("waves") or [],
        "tasks": tasks,
        "gates": data["CONVERGENCE_GATES.yaml"].get("gates") or [],
        "observability": data["OBSERVABILITY_PLAN.yaml"],
        "cutover_and_rollback": data["CUTOVER_AND_ROLLBACK.yaml"],
        "traceability": data["SOURCE_TRACEABILITY.yaml"],
    }
    body["lock_digest"] = digest_object(body)
    return body


class RelockRefused(BlueprintError):
    """A relock the Controller discovered it cannot admit. Nothing was written."""


#: Keys the compiler stamps with the compile time, per section: `snapshot_at`
#: in PROGRAM.yaml and CURRENT_STATE_DELTA.yaml, `produced_at` in
#: EVIDENCE_CATALOG.yaml, `expiry` in DO_NOT_BUILD.yaml. Every recompile moves
#: them; they carry no program intent. Masked ONLY in the section the compiler
#: writes them to: a waiver's `expires_at` or a risk's `expiry` is program
#: semantics (an expired waiver stops satisfying a gate), and a mask applied to
#: every section let an edit there ride a task-scoped relock.
_COMPILE_STAMP_KEYS: dict[str, frozenset[str]] = {
    "program": frozenset({"snapshot_at"}),
    "current_state": frozenset({"snapshot_at"}),
    "evidence": frozenset({"produced_at", "expires_at"}),
    "do_not_build": frozenset({"expiry", "expires_at"}),
}

#: Keys admission writes AFTER the lock froze the file, per section:
#: `accept_blueprint` flips `program.definition_status`; `collect_evidence`
#: binds each evidence entry's environment/notes/producer/revision/status/digest;
#: the traceability register's `sources[*].revision` is the digest of the
#: authored source, which a task-card edit changes by definition. A relock
#: compares program-wide sections with these masked, because a live campaign's
#: compiled files always differ from the lock in exactly these fields.
_ADMISSION_OWNED_KEYS: dict[str, frozenset[str]] = {
    "program": frozenset({"definition_status"}),
    "evidence": frozenset({"environment", "notes", "producer", "revision", "status", "digest"}),
    "traceability": frozenset({"revision"}),
}


def _semantic_view(section: str, value: Any) -> Any:
    """`value` with compile stamps and admission-owned keys removed, recursively."""
    masked = _COMPILE_STAMP_KEYS.get(section, frozenset()) | _ADMISSION_OWNED_KEYS.get(
        section, frozenset()
    )
    if not masked:
        return value

    def _strip(node: Any) -> Any:
        if isinstance(node, dict):
            return {key: _strip(item) for key, item in node.items() if key not in masked}
        if isinstance(node, list):
            return [_strip(item) for item in node]
        return node

    return _strip(value)


#: Lock sections that mirror one Blueprint file each. A relock names TASKS; if
#: any of these sections would change too, the edit was program-wide.
_PROGRAM_WIDE_SECTIONS = (
    "program",
    "targets",
    "authority",
    "decisions",
    "unknowns",
    "risks",
    "waivers",
    "evidence",
    "do_not_build",
    "current_state",
    "workstreams",
    "dependency_graph",
    "waves",
    "gates",
    "observability",
    "cutover_and_rollback",
    "traceability",
)

#: Sections whose change means the lock describes a different Program or a
#: different target repository, not merely a wider edit to this one.
_IDENTITY_SECTIONS = ("targets",)

LOCK_SCHEMA_ID = "program-execution-controller.program-lock.v2"


def lock_integrity_errors(lock: Any) -> list[str]:
    """Why this lock body cannot be trusted as evidence of anything.

    Structural integrity is the precondition of every semantic question: a lock
    whose digest does not cover its body, or whose schema is not the one this
    Controller speaks, has no frozen semantics to compare against.
    """
    if not isinstance(lock, dict):
        return ["program lock is not an object"]
    errors: list[str] = []
    if lock.get("schema") != LOCK_SCHEMA_ID:
        errors.append("program lock schema mismatch")
    body = dict(lock)
    claimed = body.pop("lock_digest", None)
    if digest_object(body) != claimed:
        errors.append("program lock digest mismatch")
    if not errors:
        errors.extend(validate_program_lock_schema(lock))
    return errors


def semantic_delta(lock: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Everything that differs, semantically, between a lock and a Blueprint.

    This is the one owner of "what changed". Callers never say what changed;
    they may only say what they are prepared to admit, and this answer decides
    whether that is enough. File digests are reported but never decide: a live
    campaign's compiled files legitimately move in the admission-owned fields
    the masks above remove.
    """
    program_wide = sorted(
        name
        for name in _PROGRAM_WIDE_SECTIONS
        if _semantic_view(name, lock.get(name)) != _semantic_view(name, current.get(name))
    )
    recorded_tasks = {str(task["id"]): task for task in lock.get("tasks") or []}
    live_tasks = {str(task["id"]): task for task in current.get("tasks") or []}
    recorded_sources = dict(lock.get("source_digests") or {})
    current_sources = dict(current.get("source_digests") or {})
    locked_program_id = str((lock.get("program") or {}).get("id") or "")
    current_program_id = str((current.get("program") or {}).get("id") or "")
    delta = {
        "program_wide": program_wide,
        "identity": sorted(name for name in _IDENTITY_SECTIONS if name in program_wide),
        "program_id_changed": locked_program_id != current_program_id,
        "tasks_changed": sorted(
            task_id
            for task_id in recorded_tasks
            if task_id in live_tasks
            and task_definition_digest(recorded_tasks[task_id])
            != task_definition_digest(live_tasks[task_id])
        ),
        "tasks_added": sorted(set(live_tasks) - set(recorded_tasks)),
        "tasks_removed": sorted(set(recorded_tasks) - set(live_tasks)),
        "sources_added": sorted(set(current_sources) - set(recorded_sources)),
        "sources_removed": sorted(set(recorded_sources) - set(current_sources)),
        "source_digests_moved": sorted(
            name
            for name, digest in recorded_sources.items()
            if name in current_sources and current_sources[name] != digest
        ),
        "blueprint_contract_changed": lock.get("blueprint_contract")
        != current.get("blueprint_contract"),
    }
    delta["wider_than_tasks"] = bool(
        delta["program_wide"]
        or delta["tasks_added"]
        or delta["tasks_removed"]
        or delta["sources_added"]
        or delta["sources_removed"]
        or delta["blueprint_contract_changed"]
    )
    delta["exact"] = not delta["wider_than_tasks"] and not delta["tasks_changed"]
    return delta


#: Resume decision states (PEC remediation R2). Only EXACT_MATCH proceeds
#: directly; TASK_SCOPED_DRIFT enters the canonical relock; everything else
#: stops.
RESUME_EXACT_MATCH = "EXACT_MATCH"
RESUME_TASK_SCOPED_DRIFT = "TASK_SCOPED_DRIFT"
RESUME_WIDER_PROGRAM_DRIFT = "WIDER_PROGRAM_DRIFT"
RESUME_SCHEMA_INCOMPATIBLE = "SCHEMA_INCOMPATIBLE"
RESUME_TARGET_MISMATCH = "TARGET_MISMATCH"
RESUME_LOCK_INVALID = "LOCK_INVALID"
RESUME_SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


def classify_lock_drift(lock_path: Path) -> dict[str, Any]:
    """Compare the active Program Lock against the Blueprint on disk, semantically.

    Returns `{"decision": <RESUME_*>, "reasons": [...], "delta": {...}}`.
    The decision is what a resume is allowed to do, in the canonical order:
    integrity first (an untrusted lock answers nothing), then availability and
    contract compatibility of the current source, then identity, then width.
    """
    if not lock_path.is_file():
        return {"decision": RESUME_LOCK_INVALID, "reasons": ["program lock missing"], "delta": None}
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {
            "decision": RESUME_LOCK_INVALID,
            "reasons": [f"program lock parse failure: {exc}"],
            "delta": None,
        }
    if isinstance(lock, dict) and lock.get("schema") != LOCK_SCHEMA_ID:
        return {
            "decision": RESUME_SCHEMA_INCOMPATIBLE,
            "reasons": [f"program lock schema {lock.get('schema')!r} is not {LOCK_SCHEMA_ID}"],
            "delta": None,
        }
    integrity = lock_integrity_errors(lock)
    if integrity:
        return {"decision": RESUME_LOCK_INVALID, "reasons": integrity, "delta": None}
    root = Path(str(lock.get("blueprint_root") or ""))
    if not str(lock.get("blueprint_root") or "") or not root.is_dir():
        return {
            "decision": RESUME_SOURCE_UNAVAILABLE,
            "reasons": [f"blueprint root unavailable: {root}"],
            "delta": None,
        }
    try:
        current = normalize_blueprint(root)
    except BlueprintError as exc:
        text = str(exc)
        decision = RESUME_SCHEMA_INCOMPATIBLE if "contract" in text else RESUME_SOURCE_UNAVAILABLE
        return {"decision": decision, "reasons": [text], "delta": None}
    delta = semantic_delta(lock, current)
    if delta["blueprint_contract_changed"]:
        return {
            "decision": RESUME_SCHEMA_INCOMPATIBLE,
            "reasons": ["Blueprint contract changed since the lock was written"],
            "delta": delta,
        }
    if delta["program_id_changed"] or delta["identity"]:
        reasons = []
        if delta["program_id_changed"]:
            reasons.append("program id changed")
        reasons.extend(f"identity section changed: {name}" for name in delta["identity"])
        return {"decision": RESUME_TARGET_MISMATCH, "reasons": reasons, "delta": delta}
    if delta["wider_than_tasks"]:
        reasons = [f"program-wide section changed: {name}" for name in delta["program_wide"]]
        reasons.extend(f"task added: {task_id}" for task_id in delta["tasks_added"])
        reasons.extend(f"task removed: {task_id}" for task_id in delta["tasks_removed"])
        reasons.extend(f"source added: {name}" for name in delta["sources_added"])
        reasons.extend(f"source removed: {name}" for name in delta["sources_removed"])
        return {"decision": RESUME_WIDER_PROGRAM_DRIFT, "reasons": reasons, "delta": delta}
    if delta["tasks_changed"]:
        return {
            "decision": RESUME_TASK_SCOPED_DRIFT,
            "reasons": [
                f"task definition changed: {task_id}" for task_id in delta["tasks_changed"]
            ],
            "delta": delta,
        }
    return {"decision": RESUME_EXACT_MATCH, "reasons": [], "delta": delta}


def relock_tasks(lock_path: Path, task_ids: Iterable[str]) -> dict[str, Any]:
    """Adopt edited task definitions the caller is prepared to admit, or refuse.

    `COMPATIBILITY.yaml` calls a source-digest change `runtime_stale_until_relock`
    but nothing implemented the relock, so the only way past an edited task card
    was a fresh workspace -- discarding the completed history of every other task
    to adopt one new definition.

    This is that relock, at task granularity, with the Controller discovering
    what changed. `task_ids` is a requested MAXIMUM scope, never a statement of
    what changed: the full semantic delta between the lock and the Blueprint is
    computed first, and the relock succeeds only when every difference is a
    definition inside that scope. A wider difference -- another task, a gate,
    the authority registry, the task set, the source set -- is refused with
    `RELOCK_SCOPE_INSUFFICIENT` / `PROGRAM_LOCK_GLOBAL_DRIFT` and the lock is
    left byte-for-byte as it was. Source digests are refreshed only after the
    whole delta has been admitted, so the lock never attests a file whose
    semantics it does not carry.
    """
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RelockRefused(
            f"relock refused: program lock unreadable: {exc}", error_code="LOCK_INVALID"
        ) from exc
    integrity = lock_integrity_errors(lock)
    if integrity:
        raise RelockRefused(
            "relock refused: the current lock fails integrity: " + "; ".join(integrity),
            error_code="LOCK_INVALID",
        )
    root = Path(lock.get("blueprint_root") or "")
    current = normalize_blueprint(root)
    live = {str(task["id"]): task for task in current.get("tasks") or []}

    wanted = sorted(dict.fromkeys(str(task_id) for task_id in task_ids))
    missing = [task_id for task_id in wanted if task_id not in live]
    if missing:
        raise RelockRefused(
            f"cannot relock tasks absent from the Blueprint: {sorted(missing)}",
            error_code="RELOCK_SCOPE_INSUFFICIENT",
        )

    delta = semantic_delta(lock, current)
    if delta["blueprint_contract_changed"]:
        raise RelockRefused(
            "scoped relock refused: Blueprint contract changed",
            error_code="SCHEMA_INCOMPATIBLE",
        )
    if delta["tasks_added"] or delta["tasks_removed"]:
        raise RelockRefused(
            "scoped relock refused: task membership changed "
            f"(added={delta['tasks_added']}, removed={delta['tasks_removed']})",
            error_code="PROGRAM_LOCK_GLOBAL_DRIFT",
        )
    if delta["sources_added"] or delta["sources_removed"]:
        raise RelockRefused(
            "scoped relock refused: Blueprint source membership changed "
            f"(added={delta['sources_added']}, removed={delta['sources_removed']})",
            error_code="PROGRAM_LOCK_GLOBAL_DRIFT",
        )
    if delta["program_wide"]:
        # Program-wide sources are compiled artifacts, and admission annotates
        # them after the lock froze them; `_semantic_view` masks exactly those
        # fields, so what remains here is a real program-wide edit. Refreshing
        # CONVERGENCE_GATES.yaml's digest while the lock still carried the old
        # gates would make the lock attest a file it does not reflect.
        raise RelockRefused(
            "relock adopts task definitions only; program-wide sections changed: "
            + ", ".join(delta["program_wide"])
            + " -- revert those edits or bootstrap a fresh workspace",
            error_code="PROGRAM_LOCK_GLOBAL_DRIFT",
        )
    outside_scope = sorted(set(delta["tasks_changed"]) - set(wanted))
    if outside_scope:
        raise RelockRefused(
            "scoped relock refused: task definitions changed outside the requested scope: "
            + ", ".join(outside_scope)
            + f" (requested scope: {wanted or 'none'})",
            error_code="RELOCK_SCOPE_INSUFFICIENT",
        )

    previous_digest = str(lock.get("lock_digest") or "")
    changed = [task_id for task_id in wanted if task_id in delta["tasks_changed"]]
    recorded_tasks = {str(task["id"]): task for task in lock.get("tasks") or []}
    definitions: dict[str, dict[str, str]] = {}
    tasks: list[dict[str, Any]] = []
    for task in lock.get("tasks") or []:
        task_id = str(task["id"])
        if task_id not in changed:
            tasks.append(task)
            continue
        definitions[task_id] = {
            "from": task_definition_digest(recorded_tasks[task_id]),
            "to": task_definition_digest(live[task_id]),
        }
        tasks.append(live[task_id])

    current_sources = dict(current.get("source_digests") or {})
    if not changed and not delta["source_digests_moved"]:
        return {
            "status": "CURRENT",
            "relocked": [],
            "previous_lock_digest": previous_digest,
            "lock_digest": previous_digest,
            "definitions": {},
            "tasks": {},
            "delta": delta,
        }
    body = dict(lock)
    body.pop("lock_digest", None)
    body["tasks"] = tasks
    # The file digests move with the definitions, or the very next verification
    # reports the same staleness this call just resolved. The guards above are
    # what keep that refresh honest: every semantic difference is now inside
    # the admitted scope, so every digest refreshed here covers semantics the
    # new body actually carries.
    body["source_digests"] = current_sources
    body["lock_digest"] = digest_object(body)
    schema_errors = validate_program_lock_schema(body)
    if schema_errors:
        raise RelockRefused(
            "relocked program lock schema failed: " + "; ".join(schema_errors),
            error_code="LOCK_INVALID",
        )
    write_json(lock_path, body)  # temp file + atomic replace
    return {
        "status": "RELOCKED",
        "relocked": sorted(definitions),
        "previous_lock_digest": previous_digest,
        "lock_digest": body["lock_digest"],
        "definitions": definitions,
        "tasks": {task_id: live[task_id] for task_id in definitions},
        "delta": delta,
    }


def validate_program_lock_schema(lock: dict[str, Any]) -> list[str]:
    # Imported here, not at module scope: jsonschema costs ~0.19s to import and
    # every `pec.py` CLI invocation paid it whether or not it validated anything.
    # The conformance suite spawns that CLI ~14 times per campaign test, so the
    # import alone was minutes of the suite's wall clock.
    from jsonschema import Draft202012Validator  # noqa: PLC0415 - deferred: see above

    schema = json.loads(LOCK_SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(lock),
        key=lambda item: list(item.path),
    )
    return [
        f"{'.'.join(str(part) for part in err.path) or '<root>'}: {err.message}" for err in errors
    ]


def build_program_lock(root: Path) -> dict[str, Any]:
    """Normalize and schema-check a Blueprint into a lock body, writing nothing."""
    lock = normalize_blueprint(root)
    schema_errors = validate_program_lock_schema(lock)
    if schema_errors:
        raise BlueprintError("program lock schema failed: " + "; ".join(schema_errors))
    return lock


def write_program_lock(root: Path, target: Path) -> dict[str, Any]:
    lock = build_program_lock(root)
    write_json(target, lock)
    return lock


def verify_program_lock(lock_path: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not lock_path.is_file():
        return False, ["program lock missing"]
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, [f"program lock parse failure: {exc}"]
    if lock.get("schema") != "program-execution-controller.program-lock.v2":
        errors.append("program lock schema mismatch")
    errors.extend(validate_program_lock_schema(lock))
    claimed = lock.get("lock_digest")
    body = dict(lock)
    body.pop("lock_digest", None)
    if digest_object(body) != claimed:
        errors.append("program lock digest mismatch")
    blueprint_root = Path(lock.get("blueprint_root") or "")
    for name, digest in (lock.get("source_digests") or {}).items():
        path = blueprint_root / name
        if not path.is_file():
            errors.append(f"Blueprint source missing: {name}")
        elif sha256_file(path) != digest:
            errors.append(f"Blueprint source changed: {name}")
    return not errors, errors


# The one blueprint source whose changes can be attributed to individual tasks.
# Every other file describes the program as a whole -- authority, gates, evidence,
# waves -- so a change to it is not scopable and keeps the global verdict.
TASK_SOURCE = "TASK_CARDS.yaml"


def task_definition_digest(task: dict[str, Any]) -> str:
    """A fingerprint of one task's definition, independent of the other tasks.

    The lock already carries each task's authored card under `source`, so this
    needs no new lock field: the digest is derived from what was frozen.
    """
    return digest_object(task)


def stale_task_ids(lock_path: Path) -> set[str] | None:
    """Which tasks' own definitions have moved since the lock was written.

    `verify_program_lock` answers at file granularity, which conflates two
    different things: a lock that cannot be trusted at all, and a task card file
    in which one task was edited. The first must block the program; the second
    should only affect the task that was edited, because every other task's
    definition -- and the history recorded against it -- is exactly what it was.

    Returns the set of task ids whose definition changed, or None when the
    change cannot be attributed to particular tasks and the whole lock must be
    treated as stale. None is the conservative answer and is what callers get
    for a corrupt lock, a missing file, or an edit to any program-wide source.
    """
    if not lock_path.is_file():
        return None
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    # Structural integrity is not scopable: if the lock does not describe itself
    # correctly, nothing derived from it is evidence of anything.
    body = dict(lock)
    claimed = body.pop("lock_digest", None)
    if digest_object(body) != claimed:
        return None
    if lock.get("schema") != "program-execution-controller.program-lock.v2":
        return None

    root = Path(lock.get("blueprint_root") or "")
    changed: list[str] = []
    for name, digest in (lock.get("source_digests") or {}).items():
        path = root / name
        if not path.is_file() or sha256_file(path) != digest:
            changed.append(name)
    if not changed:
        return set()
    if any(name != TASK_SOURCE for name in changed):
        return None

    try:
        current = normalize_blueprint(root)
    except BlueprintError:
        return None
    recorded = {str(task["id"]): task_definition_digest(task) for task in lock.get("tasks") or []}
    live = {str(task["id"]): task_definition_digest(task) for task in current.get("tasks") or []}
    # A task that was added or removed changes the shape of the program, not just
    # one definition, so decline to scope rather than guessing.
    if set(recorded) != set(live):
        return None
    return {task_id for task_id, digest in recorded.items() if live[task_id] != digest}
