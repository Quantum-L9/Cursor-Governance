from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import digest_object, load_yaml, sha256_file, utc_now, write_json


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


def write_program_lock(root: Path, target: Path) -> dict[str, Any]:
    lock = normalize_blueprint(root)
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
