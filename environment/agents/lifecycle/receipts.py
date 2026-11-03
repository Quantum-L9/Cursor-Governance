from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from environment.agents.lifecycle.schemas import (
    ASSIGNMENT_SCHEMA,
    DISPATCH_SCHEMA,
    HOST_ADMISSION_SCHEMA,
    HOST_CORRELATION_SCHEMA,
    HOST_RAW_STOP_SCHEMA,
    PR_ASSIGNMENT_SCHEMA,
    RETURN_SCHEMA,
)
from environment.agents.results.receipts import safe_receipt_id
from environment.agents.runtime_paths import (
    agent_runtime_root,
    assignment_root,
    subagent_receipt_root,
)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
        + b"\n"
    )


def _digest(body: Any) -> str:
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path: Path, body: dict[str, Any]) -> dict[str, Any]:
    identity = {key: value for key, value in body.items() if key != "observed_at"}
    digest = _digest(identity)
    if path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("receipt_digest") != digest:
            raise RuntimeError(f"receipt collision at {path}: existing body differs")
        return existing
    stored = {**body, "receipt_digest": digest}
    encoded = (
        json.dumps(stored, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    )
    _atomic_write(path, encoded)
    return stored


def _assignment_file(assignment_id: str) -> str:
    return f"{safe_receipt_id(assignment_id, label='assignment_id')}.json"


def _subagent_file(subagent_id: str) -> str:
    return f"{safe_receipt_id(subagent_id, label='subagent_id')}.json"


def assignment_path(assignment_id: str) -> Path:
    return assignment_root() / _assignment_file(assignment_id)


def dispatch_path(assignment_id: str) -> Path:
    return subagent_receipt_root() / "dispatch" / _assignment_file(assignment_id)


def return_path(assignment_id: str) -> Path:
    return subagent_receipt_root() / "return" / _assignment_file(assignment_id)


def raw_result_path(assignment_id: str) -> Path:
    return agent_runtime_root() / "results" / "raw" / _assignment_file(assignment_id)


def host_correlation_path(subagent_id: str) -> Path:
    return subagent_receipt_root() / "host-correlation" / _subagent_file(subagent_id)


HOST_ADMISSION_RESERVE_TTL = timedelta(minutes=2)
# A start with no stop and no return is a live lane only inside this window.
# Older starts are abandoned slots: subagentStop never wrote a receipt, and
# leaving them in flight fills max_mutation_lanes forever.
HOST_ADMISSION_RUN_TTL = timedelta(hours=6)


def host_admission_path(tool_use_id: str) -> Path:
    name = f"{safe_receipt_id(tool_use_id, label='tool_use_id')}.json"
    return subagent_receipt_root() / "host-admission" / name


@contextmanager
def host_admission_lock() -> Iterator[None]:
    """Serialize cap check + admission write across concurrent preToolUse hooks."""
    path = subagent_receipt_root() / "host-admission.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def host_stop_path(subagent_id: str) -> Path:
    return subagent_receipt_root() / "host-stop" / _subagent_file(subagent_id)


def write_host_correlation(fields: dict[str, Any]) -> dict[str, Any]:
    subagent_id = str(fields.get("subagent_id") or "").strip()
    assignment_id = str(fields.get("assignment_id") or "").strip()
    if not subagent_id or not assignment_id:
        raise ValueError("host correlation requires subagent_id and assignment_id")
    body = {
        "schema": HOST_CORRELATION_SCHEMA,
        "observed_at": _now(),
        "status": "CORRELATED",
        **fields,
    }
    return write_json(host_correlation_path(subagent_id), body)


def load_host_correlation(subagent_id: str) -> dict[str, Any] | None:
    path = host_correlation_path(subagent_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def write_host_admission(fields: dict[str, Any]) -> dict[str, Any]:
    tool_use_id = str(fields.get("tool_use_id") or "").strip()
    assignment_id = str(fields.get("assignment_id") or "").strip()
    if not tool_use_id or not assignment_id:
        raise ValueError("host admission requires tool_use_id and assignment_id")
    body = {
        "schema": HOST_ADMISSION_SCHEMA,
        "observed_at": _now(),
        "status": "ADMITTED",
        "path": "host-native",
        **fields,
        "tool_use_id": tool_use_id,
        "assignment_id": assignment_id,
    }
    return write_json(host_admission_path(tool_use_id), body)


def load_host_admission(tool_use_id: str) -> dict[str, Any] | None:
    path = host_admission_path(tool_use_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _parse_observed_at(raw: Any) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


HostCorrelationIndex = dict[str, list[dict[str, Any]]]


def _load_host_correlation_index() -> HostCorrelationIndex:
    """Map tool_use_id / tool_call_id → every correlation body carrying it.

    One directory scan. The relation is many-to-one: several correlation
    receipts may share an identifier, so every match is retained. Consumers
    aggregate over the list exactly as the pre-index scan aggregated over the
    directory (any match → started; any stopped match → stopped), which keeps
    the answer independent of the order ``glob()`` yields files.
    """
    index: HostCorrelationIndex = {}
    corr_root = subagent_receipt_root() / "host-correlation"
    if not corr_root.is_dir():
        return index
    for path in corr_root.glob("*.json"):
        try:
            corr = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(corr, dict):
            continue
        seen: set[str] = set()
        for key in (corr.get("tool_use_id"), corr.get("tool_call_id")):
            text = str(key or "").strip()
            if text and text not in seen:
                seen.add(text)
                index.setdefault(text, []).append(corr)
    return index


def _host_admission_has_start(
    body: dict[str, Any], *, index: HostCorrelationIndex | None = None
) -> bool:
    tool_use_id = str(body.get("tool_use_id") or "")
    if not tool_use_id:
        return False
    table = index if index is not None else _load_host_correlation_index()
    return tool_use_id in table


def _host_admission_activity_at(
    body: dict[str, Any], *, index: HostCorrelationIndex | None = None
) -> datetime | None:
    """Latest stamp on the admission or any correlation that shares its id."""
    stamps = [_parse_observed_at(body.get("observed_at"))]
    tool_use_id = str(body.get("tool_use_id") or "")
    table = index if index is not None else _load_host_correlation_index()
    for corr in table.get(tool_use_id, ()):
        stamps.append(_parse_observed_at(corr.get("observed_at")))
    parsed = [stamp for stamp in stamps if stamp is not None]
    return max(parsed) if parsed else None


def _host_admission_expired(
    body: dict[str, Any],
    *,
    now: datetime | None = None,
    index: HostCorrelationIndex | None = None,
) -> bool:
    if _host_admission_has_stop(body, index=index):
        return False
    activity = _host_admission_activity_at(body, index=index)
    if activity is None:
        return False
    clock = now or datetime.now(UTC)
    age = clock - activity
    if _host_admission_has_start(body, index=index):
        return age > HOST_ADMISSION_RUN_TTL
    return age > HOST_ADMISSION_RESERVE_TTL


def _host_admission_has_stop(
    body: dict[str, Any], *, index: HostCorrelationIndex | None = None
) -> bool:
    """True when ANY correlation sharing the admission's id has a host-stop receipt."""
    tool_use_id = str(body.get("tool_use_id") or "")
    if not tool_use_id:
        return False
    table = index if index is not None else _load_host_correlation_index()
    for corr in table.get(tool_use_id, ()):
        subagent_id = str(corr.get("subagent_id") or "").strip()
        if not subagent_id:
            continue
        try:
            stopped = host_stop_path(subagent_id).is_file()
        except ValueError:
            continue
        if stopped:
            return True
    return False


def terminate_abandoned_host_agents(*, now: datetime | None = None) -> dict[str, int]:
    """Write the stop the launcher owes every start that subagentStop never closed.

    The Task admission path calls this before it counts the mutation cap.
    A correlation younger than ``HOST_ADMISSION_RUN_TTL`` is left alone.
    """
    clock = now or datetime.now(UTC)
    root = subagent_receipt_root() / "host-correlation"
    stopped = 0
    kept_live = 0
    if root.is_dir():
        for path in root.glob("*.json"):
            try:
                body = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(body, dict):
                continue
            subagent_id = str(body.get("subagent_id") or "").strip()
            if not subagent_id:
                continue
            try:
                if host_stop_path(subagent_id).is_file():
                    continue
            except ValueError:
                continue
            activity = _parse_observed_at(body.get("observed_at"))
            if activity is not None and clock - activity <= HOST_ADMISSION_RUN_TTL:
                kept_live += 1
                continue
            try:
                write_host_stop(
                    subagent_id,
                    {
                        "status": "abandoned",
                        "reason": "launcher reaped: subagentStop did not arrive",
                        "assignment_id": body.get("assignment_id"),
                        "tool_use_id": body.get("tool_use_id"),
                    },
                )
            except (OSError, RuntimeError, ValueError):
                continue
            for key in ("tool_use_id", "tool_call_id"):
                tool_id = str(body.get(key) or "").strip()
                if not tool_id:
                    continue
                try:
                    host_admission_path(tool_id).unlink(missing_ok=True)
                except ValueError:
                    continue
            stopped += 1
    return {"stopped": stopped, "kept_live": kept_live}


def list_in_flight_host_admissions() -> list[dict[str, Any]]:
    """Host-native admissions that have not returned or stopped.

    The Task launch path calls this while holding the admission lock, so a
    launch terminates abandoned children before it counts the mutation cap.
    """
    terminate_abandoned_host_agents()
    root = subagent_receipt_root() / "host-admission"
    if not root.is_dir():
        return []
    index = _load_host_correlation_index()
    open_ones: list[dict[str, Any]] = []
    # #region agent log
    _dbg_files = 0
    _dbg_returned = 0
    _dbg_bad_id = 0
    _dbg_stopped = 0
    _dbg_expired = 0
    # #endregion
    for path in root.glob("*.json"):
        # #region agent log
        _dbg_files += 1
        # #endregion
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(body, dict):
            continue
        assignment_id = str(body.get("assignment_id") or "").strip()
        if assignment_id:
            try:
                returned = return_path(assignment_id).is_file()
            except ValueError:
                # #region agent log
                _dbg_bad_id += 1
                # #endregion
                continue
            if returned:
                # #region agent log
                _dbg_returned += 1
                # #endregion
                continue
        if _host_admission_has_stop(body, index=index):
            # #region agent log
            _dbg_stopped += 1
            # #endregion
            continue
        if _host_admission_expired(body, index=index):
            # #region agent log
            _dbg_expired += 1
            # #endregion
            path.unlink(missing_ok=True)
            continue
        open_ones.append(body)
    # #region agent log
    try:
        import time as _agent_time

        _now = datetime.now(UTC)
        _mut = [b for b in open_ones if b.get("mutation")]
        _started = 0
        _old = 0
        _types: dict[str, int] = {}
        _oldest = ""
        _samples: list[dict[str, Any]] = []
        _ranked = sorted(_mut, key=lambda b: str(b.get("observed_at") or ""))
        for _b in _ranked:
            _kind = str(_b.get("subagent_type") or "?")
            _types[_kind] = _types.get(_kind, 0) + 1
            _has_start = _host_admission_has_start(_b, index=index)
            if _has_start:
                _started += 1
            _obs = str(_b.get("observed_at") or "")
            if not _oldest or (_obs and _obs < _oldest):
                _oldest = _obs
            _parsed = _parse_observed_at(_b.get("observed_at"))
            if _parsed is not None and _now - _parsed > HOST_ADMISSION_RUN_TTL:
                _old += 1
            if len(_samples) < 3:
                _tid = str(_b.get("tool_use_id") or "")
                _corr_times = [str(c.get("observed_at") or "") for c in index.get(_tid, ())]
                _aid = str(_b.get("assignment_id") or "")
                _ret = False
                try:
                    _ret = bool(_aid) and return_path(_aid).is_file()
                except ValueError:
                    _ret = False
                _samples.append(
                    {
                        "observed_at": _obs,
                        "subagent_type": _kind,
                        "has_start": _has_start,
                        "has_stop": _host_admission_has_stop(_b, index=index),
                        "return_exists": _ret,
                        "newest_correlation_at": max(_corr_times) if _corr_times else "",
                        "correlation_count": len(_corr_times),
                    }
                )
        _payload = {
            "sessionId": "982472",
            "runId": "post-fix",
            "hypothesisId": "A",
            "location": "receipts.py:list_in_flight_host_admissions",
            "message": "in-flight cap inventory",
            "data": {
                "files": _dbg_files,
                "skipped_returned": _dbg_returned,
                "skipped_bad_id": _dbg_bad_id,
                "skipped_stopped": _dbg_stopped,
                "expired_unlinked": _dbg_expired,
                "kept": len(open_ones),
                "kept_mutating": len(_mut),
                "mutating_with_start": _started,
                "mutating_older_than_6h": _old,
                "oldest_mutating_observed_at": _oldest,
                "mutating_types": _types,
                "oldest_mutating_samples": _samples,
            },
            "timestamp": int(_agent_time.time() * 1000),
        }
        with open(
            "/Users/ib-mac/Cursor-Governance/.cursor/debug-982472.log",
            "a",
            encoding="utf-8",
        ) as _agent_fh:
            _agent_fh.write(json.dumps(_payload, default=str) + "\n")
    except Exception:
        pass
    # #endregion
    return open_ones


def write_host_stop(subagent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = {
        "schema": HOST_RAW_STOP_SCHEMA,
        "observed_at": _now(),
        "status": str(payload.get("status") or "UNKNOWN"),
        "subagent_id": subagent_id,
        "payload": payload,
    }
    return write_json(host_stop_path(subagent_id), body)


def write_raw_result(assignment_id: str, result: Any) -> dict[str, Any]:
    """Persist raw subagent output before any validation or distillation.

    The raw evidence object is immutable for an assignment. A repeated stop with
    identical bytes is idempotent; the same assignment with different output is
    a collision and is refused rather than silently replacing evidence.
    """

    envelope = {
        "schema": "l9.subagent-raw-result.v1",
        "assignment_id": assignment_id,
        "captured_at": _now(),
        "result": result,
    }
    # captured_at is not part of the immutable payload identity.
    identity = {
        "schema": envelope["schema"],
        "assignment_id": assignment_id,
        "result": result,
    }
    result_digest = _digest(identity)
    envelope["result_digest"] = result_digest
    path = raw_result_path(assignment_id)
    if path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("result_digest") != result_digest:
            raise RuntimeError(
                f"raw result collision for assignment {assignment_id}: existing evidence differs"
            )
        return {
            "path": str(path),
            "result_digest": result_digest,
            "idempotent": True,
            "result": existing.get("result"),
        }
    _atomic_write(
        path,
        json.dumps(envelope, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n",
    )
    return {
        "path": str(path),
        "result_digest": result_digest,
        "idempotent": False,
        "result": result,
    }


def load_raw_result(assignment_id: str) -> dict[str, Any] | None:
    path = raw_result_path(assignment_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def write_assignment(fields: dict[str, Any]) -> dict[str, Any]:
    body = {"schema": ASSIGNMENT_SCHEMA, "observed_at": _now(), "status": "ASSIGNED", **fields}
    return write_json(assignment_path(fields["assignment_id"]), body)


def write_dispatch(fields: dict[str, Any]) -> dict[str, Any]:
    body = {"schema": DISPATCH_SCHEMA, "observed_at": _now(), "status": "DISPATCHED", **fields}
    return write_json(dispatch_path(fields["assignment_id"]), body)


def write_return(fields: dict[str, Any]) -> dict[str, Any]:
    body = {"schema": RETURN_SCHEMA, "observed_at": _now(), "status": "RETURNED", **fields}
    return write_json(return_path(fields["assignment_id"]), body)


def write_pr_remediation_assignment(fields: dict[str, Any]) -> dict[str, Any]:
    aid = fields["assignment_id"]
    body = {
        "schema": PR_ASSIGNMENT_SCHEMA,
        "observed_at": _now(),
        "status": "ASSIGNED",
        "role": "l9-pr-remediation",
        "max_cycles": fields.get("max_cycles", 3),
        "never_merge": True,
        "never_force_push": True,
        **fields,
    }
    path = assignment_root() / "pr-remediation" / _assignment_file(aid)
    return write_json(path, body)


def load_assignment(assignment_id: str) -> dict[str, Any] | None:
    path = assignment_path(assignment_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def load_dispatch(assignment_id: str) -> dict[str, Any] | None:
    path = dispatch_path(assignment_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def load_return(assignment_id: str) -> dict[str, Any] | None:
    path = return_path(assignment_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
