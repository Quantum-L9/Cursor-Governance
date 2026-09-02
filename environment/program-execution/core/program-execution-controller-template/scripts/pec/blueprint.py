from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .common import digest_object, load_yaml, sha256_file, utc_now, write_json

LOCK_SCHEMA = Path(__file__).resolve().parents[2] / "schemas" / "program-lock.schema.json"


class BlueprintError(RuntimeError):
    pass


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
        required_commands = [
            item["command_or_inspection"]
            for item in raw.get("validation") or []
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


def relock_tasks(lock_path: Path, task_ids: Iterable[str]) -> dict[str, Any]:
    """Refresh the frozen definition of specific tasks, leaving the rest alone.

    `COMPATIBILITY.yaml` calls a source-digest change `runtime_stale_until_relock`
    but nothing implemented the relock, so the only way past an edited task card
    was a fresh workspace -- discarding the completed history of every other task
    to adopt one new definition.

    This is that relock, at task granularity. Definitions named in `task_ids` are
    replaced with what the blueprint says now and the file digests are refreshed;
    every other task's entry is preserved byte-for-byte, so the lock continues to
    attest exactly what it attested before for the work already done.
    """
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    root = Path(lock.get("blueprint_root") or "")
    current = normalize_blueprint(root)
    live = {str(task["id"]): task for task in current.get("tasks") or []}

    wanted = [str(task_id) for task_id in task_ids]
    missing = [task_id for task_id in wanted if task_id not in live]
    if missing:
        raise BlueprintError(f"cannot relock tasks absent from the Blueprint: {sorted(missing)}")

    previous_digest = str(lock.get("lock_digest") or "")
    definitions: dict[str, dict[str, str]] = {}
    tasks: list[dict[str, Any]] = []
    for task in lock.get("tasks") or []:
        task_id = str(task["id"])
        if task_id not in wanted:
            tasks.append(task)
            continue
        definitions[task_id] = {
            "from": task_definition_digest(task),
            "to": task_definition_digest(live[task_id]),
        }
        tasks.append(live[task_id])

    # Admission annotates compiled files after the lock freezes them, so the
    # file digests legitimately move on a live campaign; refreshing them is
    # what keeps the next verification from reporting the staleness this call
    # resolved. What must NOT ride along under a task-scoped relock is a change
    # to a program-wide section: refreshing CONVERGENCE_GATES.yaml's digest
    # while the lock still carries the old gates would make the lock attest a
    # file it does not reflect.
    changed_sections = sorted(
        name
        for name in _PROGRAM_WIDE_SECTIONS
        if _semantic_view(name, lock.get(name)) != _semantic_view(name, current.get(name))
    )
    if changed_sections:
        raise BlueprintError(
            "relock adopts task definitions only; program-wide sections changed: "
            + ", ".join(changed_sections)
            + " -- revert those edits or bootstrap a fresh workspace"
        )
    body = dict(lock)
    body.pop("lock_digest", None)
    body["tasks"] = tasks
    body["source_digests"] = current.get("source_digests") or {}
    body["lock_digest"] = digest_object(body)
    schema_errors = validate_program_lock_schema(body)
    if schema_errors:
        raise BlueprintError("relocked program lock schema failed: " + "; ".join(schema_errors))
    write_json(lock_path, body)
    return {
        "relocked": sorted(definitions),
        "previous_lock_digest": previous_digest,
        "lock_digest": body["lock_digest"],
        "definitions": definitions,
        "tasks": {task_id: live[task_id] for task_id in definitions},
    }


#: Keys the compiler stamps with the compile time (`snapshot_at` in PROGRAM.yaml
#: and CURRENT_STATE.yaml, `produced_at` in EVIDENCE_CATALOG.yaml, `expiry` in
#: DO_NOT_BUILD.yaml). Every recompile moves them; they carry no program intent.
_COMPILE_STAMP_KEYS = frozenset({"snapshot_at", "produced_at", "expiry", "expires_at"})

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
    masked = _COMPILE_STAMP_KEYS | _ADMISSION_OWNED_KEYS.get(section, frozenset())

    def _strip(node: Any) -> Any:
        if isinstance(node, dict):
            return {key: _strip(item) for key, item in node.items() if key not in masked}
        if isinstance(node, list):
            return [_strip(item) for item in node]
        return node

    return _strip(value)


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
    except Exception:
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
