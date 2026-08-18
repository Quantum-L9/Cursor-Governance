#!/usr/bin/env python3
"""Append-only execution trace for the PE campaign front door (PE-TRACE-001).

Every public campaign invocation writes `<workspace>/telemetry/events.jsonl`,
one JSON object per line, so a crashed run still leaves the events it already
emitted on disk. `harvest_trace` reads only that file and answers where the
time went, what repeated, and what failed.

Telemetry is additive: it is never a gate. A failure to initialise or append
warns on stderr and lets the campaign continue. The one exception is the
explicit trace-harvest command, where the caller asked for telemetry itself.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EVENT_SCHEMA = "pe.execution-trace.v1"
SUMMARY_SCHEMA = "pe.execution-trace-summary.v1"
TELEMETRY_DIRNAME = "telemetry"
EVENTS_FILENAME = "events.jsonl"
SUMMARY_JSON_FILENAME = "run-summary.json"
SUMMARY_MD_FILENAME = "run-summary.md"

# Bounded diagnostic tail; telemetry stores evidence, not transcripts.
MAX_ERROR_MESSAGE = 2000

STATUS_STARTED = "STARTED"
STATUS_PASSED = "PASSED"
STATUS_FAILED = "FAILED"
STATUS_INFO = "INFO"

# Contract §21. Fixed mapping, no subjective allocation.
#
# Categories absent from this table (campaign, task, task_prepare, execute,
# publish, close) are counted and timed but deliberately land in no bucket:
# they wrap other traced operations, and bucketing a container double-counts
# its children. Sibling spans inside one bucket can still overlap where the
# contract maps a container and its child to the same bucket (arm contains
# reconcile), so wall_clock_ms, not the bucket sum, is the authority on
# elapsed time.
CATEGORY_BUCKETS: dict[str, str] = {
    "input": "preparation",
    "compile": "preparation",
    "blueprint": "preparation",
    "planning": "preparation",
    "research": "preparation",
    "preflight": "preparation",
    "evidence": "preparation",
    "acceptance": "preparation",
    "bootstrap": "preparation",
    "arm": "preparation",
    "reconcile": "preparation",
    "worker": "implementation",
    "filesystem_write": "implementation",
    "commit": "implementation",
    "validation": "validation",
    "verification": "verification",
    "gate": "verification",
    "retry": "recovery",
    "recovery": "recovery",
    "cleanup": "recovery",
    "workspace": "recovery",
}

# Categories that describe a workspace reset or recovery action, counted
# separately in the summary because they are a suspected time sink.
RECOVERY_CATEGORIES = frozenset({"retry", "recovery", "cleanup", "workspace"})


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_run_id() -> str:
    return f"RUN-{uuid.uuid4().hex[:16]}"


# PE artifacts are stamped when they are emitted (created_at, snapshot_at,
# accepted_at, produced_at), so two byte-identical recompilations of the same
# campaign never hash alike. Normalising the stamp is what lets §16 answer
# "this ran twice over inputs that did not change".
_TIMESTAMP_RE = re.compile(
    rb"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"
)


def normalize(data: bytes) -> bytes:
    """Blank out emission timestamps so identical work hashes identically."""
    return _TIMESTAMP_RE.sub(b"<timestamp>", data)


def fingerprint(*parts: Any) -> str:
    """Deterministic SHA-256 over the given input parts.

    Accepts paths (hashed by content when readable, else by name), bytes, and
    anything JSON-serialisable. Used only for the repeatable preparation
    operations named in the contract; this is not a dependency graph.

    Emission timestamps are normalised out of every part, so a repeat over
    unchanged inputs is visible even though the artifacts were re-stamped.
    """
    digest = hashlib.sha256()
    for part in parts:
        if isinstance(part, Path):
            digest.update(str(part).encode("utf-8"))
            try:
                digest.update(normalize(part.read_bytes()))
            except OSError:
                digest.update(b"<unreadable>")
        elif isinstance(part, bytes):
            digest.update(normalize(part))
        else:
            digest.update(
                normalize(
                    json.dumps(part, sort_keys=True, default=str, ensure_ascii=False).encode(
                        "utf-8"
                    )
                )
            )
        digest.update(b"\0")
    return digest.hexdigest()


def _bounded(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:MAX_ERROR_MESSAGE]


class ExecutionTrace:
    """Append-only JSONL writer with a late-bound workspace.

    The campaign runner classifies its input before it knows which workspace
    the campaign owns, so events emitted before `bind()` are buffered in memory
    and flushed once the destination is known. An unbound trace that is never
    bound simply drops its buffer -- telemetry never blocks execution.
    """

    def __init__(
        self,
        workspace: Path | None = None,
        campaign_id: str = "",
        run_id: str | None = None,
        *,
        strict: bool = False,
        clock: Any = None,
    ) -> None:
        self.campaign_id = campaign_id or ""
        self.run_id = run_id or new_run_id()
        self.strict = strict
        self._clock = clock or time.monotonic
        self._buffer: list[dict[str, Any]] = []
        self._reported_exc: int | None = None
        self._path: Path | None = None
        self._disabled = False
        if workspace is not None:
            self.bind(workspace, campaign_id=campaign_id)

    # -- destination ----------------------------------------------------

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def bound(self) -> bool:
        return self._path is not None

    def bind(self, workspace: Path, *, campaign_id: str = "") -> None:
        """Point the trace at `<workspace>/telemetry/events.jsonl` and flush."""
        if campaign_id:
            self.campaign_id = campaign_id
        try:
            telemetry = Path(workspace) / TELEMETRY_DIRNAME
            telemetry.mkdir(parents=True, exist_ok=True)
            self._path = telemetry / EVENTS_FILENAME
        except OSError as exc:
            self._warn(f"cannot open telemetry directory under {workspace}: {exc}")
            return
        buffered, self._buffer = self._buffer, []
        for record in buffered:
            if not record.get("campaign_id"):
                record["campaign_id"] = self.campaign_id
            self._append(record)

    def relocate(self, events_path: Path) -> None:
        """Move the trace file and keep appending at the new location.

        The pec workspace is recycled mid-run: it is quarantined when a
        previous campaign left it occupied, and `pec bootstrap` refuses to
        build into a directory that is not empty. Rather than lose the
        preparation events already on disk, the trace steps aside and steps
        back in, so one run stays one continuous file.

        An existing file at the destination is preserved and appended to,
        which is what keeps campaign-wide aggregates across runs intact.
        """
        target = Path(events_path)
        current = self._path
        if current is not None and current.resolve() == target.resolve():
            return
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if current is not None and current.is_file():
                if target.exists():
                    with open(target, "a", encoding="utf-8") as handle:
                        handle.write(current.read_text(encoding="utf-8"))
                    current.unlink()
                else:
                    shutil.move(str(current), str(target))
            self._path = target
            self._disabled = False
        except OSError as exc:
            self._warn(f"cannot relocate telemetry to {target}: {exc}")
            return
        if current is not None:
            # Leave no empty telemetry/ behind: pec bootstrap refuses to
            # build into a workspace that still holds a directory.
            try:
                current.parent.rmdir()
            except OSError:
                pass

    def rehome(self, workspace: Path) -> None:
        """Relocate to `<workspace>/telemetry/events.jsonl`."""
        self.relocate(Path(workspace) / TELEMETRY_DIRNAME / EVENTS_FILENAME)

    @contextmanager
    def stepped_aside(self, staging: Path) -> Iterator[None]:
        """Hold the trace outside a workspace that is about to be rebuilt.

        `pec bootstrap` refuses a non-empty workspace, so the telemetry
        directory cannot be sitting in it while bootstrap runs.
        """
        home = self._path
        if home is None:
            yield
            return
        self.relocate(Path(staging) / EVENTS_FILENAME)
        try:
            yield
        finally:
            self.relocate(home)
            try:
                Path(staging).rmdir()
            except OSError:
                pass

    # -- emission -------------------------------------------------------

    def event(
        self,
        event_type: str,
        category: str,
        operation: str,
        *,
        status: str = STATUS_INFO,
        task_id: str | None = None,
        attempt_number: int | None = None,
        input_fingerprint: str | None = None,
        cache_status: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        duration_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "schema": EVENT_SCHEMA,
            "event_id": f"EVT-{uuid.uuid4().hex[:16]}",
            "campaign_id": self.campaign_id,
            "run_id": self.run_id,
            "event_type": event_type,
            "category": category,
            "operation": operation,
            "status": status,
            "timestamp": utc_now(),
            "duration_ms": duration_ms,
            "task_id": task_id,
            "attempt_number": attempt_number,
            "input_fingerprint": input_fingerprint,
            "cache_status": cache_status,
            "error_code": error_code,
            "error_message": _bounded(error_message),
            "metadata": metadata or {},
        }
        self._emit(record)
        return record

    @contextmanager
    def span(
        self,
        category: str,
        operation: str,
        *,
        task_id: str | None = None,
        attempt_number: int | None = None,
        input_fingerprint: str | None = None,
        cache_status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Emit STARTED on entry and PASSED/FAILED on exit, then re-raise.

        The yielded dict is a mutable metadata carrier: mutate it inside the
        block to attach facts (exit codes, counts) to the terminal event.
        Setting `error_code` on the carrier marks the span FAILED without
        raising, for operations that report failure by return value (a
        non-zero exit code, a non-empty error list) rather than by
        exception.
        """
        carrier: dict[str, Any] = dict(metadata or {})
        self.event(
            "OPERATION_STARTED",
            category,
            operation,
            status=STATUS_STARTED,
            task_id=task_id,
            attempt_number=attempt_number,
            input_fingerprint=input_fingerprint,
            cache_status=cache_status,
            metadata=dict(carrier),
        )
        started = self._clock()
        try:
            yield carrier
        except BaseException as exc:
            # The same exception unwinds through every enclosing span. Each
            # span records that it failed, but only the innermost one is the
            # failure: the rest are marked propagated so the summary counts
            # one root cause instead of one per nesting level.
            propagated = self._reported_exc == id(exc)
            self._reported_exc = id(exc)
            carrier["propagated"] = propagated
            self.event(
                "OPERATION_FAILED",
                category,
                operation,
                status=STATUS_FAILED,
                task_id=task_id,
                attempt_number=attempt_number,
                input_fingerprint=input_fingerprint,
                cache_status=carrier.pop("cache_status", cache_status),
                error_code=str(
                    carrier.pop("error_code", None)
                    or getattr(exc, "error_code", None)
                    or type(exc).__name__
                ),
                error_message=str(carrier.pop("error_message", None) or exc),
                duration_ms=self._elapsed_ms(started),
                metadata=carrier,
            )
            raise
        duration_ms = self._elapsed_ms(started)
        failed = carrier.pop("error_code", None)
        error_message = carrier.pop("error_message", None)
        self.event(
            "OPERATION_FAILED" if failed else "OPERATION_FINISHED",
            category,
            operation,
            status=STATUS_FAILED if failed else STATUS_PASSED,
            task_id=task_id,
            attempt_number=attempt_number,
            input_fingerprint=input_fingerprint,
            cache_status=carrier.pop("cache_status", cache_status),
            error_code=str(failed) if failed else None,
            error_message=error_message,
            duration_ms=duration_ms,
            metadata=carrier,
        )

    def _elapsed_ms(self, started: float) -> int:
        return max(0, int(round((self._clock() - started) * 1000)))

    # -- io -------------------------------------------------------------

    def _emit(self, record: dict[str, Any]) -> None:
        if self._path is None:
            self._buffer.append(record)
            return
        self._append(record)

    def _append(self, record: dict[str, Any]) -> None:
        if self._disabled or self._path is None:
            return
        try:
            line = json.dumps(record, sort_keys=True, default=str, ensure_ascii=False)
            with open(self._path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            self._warn(f"telemetry append failed ({exc}); tracing disabled for this run")
            self._disabled = True

    def _warn(self, message: str) -> None:
        if self.strict:
            raise RuntimeError(message)
        print(f"pe-trace: {message}", file=sys.stderr, flush=True)


# -- harvester ----------------------------------------------------------


def read_events(workspace: Path) -> list[dict[str, Any]]:
    """Read every well-formed event line. A torn final line is skipped."""
    path = Path(workspace) / TELEMETRY_DIRNAME / EVENTS_FILENAME
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            events.append(record)
    return events


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _terminal(event: dict[str, Any]) -> bool:
    return event.get("status") in {STATUS_PASSED, STATUS_FAILED}


def harvest_trace(workspace: Path) -> dict[str, Any]:
    """Summarise `telemetry/events.jsonl`. Reads nothing else."""
    events = read_events(workspace)
    summary: dict[str, Any] = {
        "schema": SUMMARY_SCHEMA,
        "campaign_id": "",
        "run_ids": [],
        "wall_clock_ms": 0,
        "task_counts": {"completed": 0, "attempted": 0},
        "operation_counts": {},
        "failure_counts": {},
        "retry_counts": {},
        "repeated_operations": [],
        "timing": {
            "preparation_ms": 0,
            "implementation_ms": 0,
            "validation_ms": 0,
            "verification_ms": 0,
            "recovery_ms": 0,
            "time_to_first_write_ms": None,
        },
        "top_time_consumers": [],
        "per_task": {},
        "workspace_recovery_counts": {},
        "event_count": len(events),
    }
    if not events:
        return summary

    run_ids: list[str] = []
    timestamps: list[datetime] = []
    by_fingerprint: dict[tuple[str, str], list[dict[str, Any]]] = {}
    by_operation: dict[str, dict[str, Any]] = {}
    per_task: dict[str, dict[str, Any]] = {}
    campaign_run_started: datetime | None = None
    first_write_at: datetime | None = None

    for event in events:
        campaign_id = str(event.get("campaign_id") or "")
        if campaign_id and not summary["campaign_id"]:
            summary["campaign_id"] = campaign_id
        run_id = str(event.get("run_id") or "")
        if run_id and run_id not in run_ids:
            run_ids.append(run_id)
        moment = _parse_ts(event.get("timestamp"))
        if moment is not None:
            timestamps.append(moment)

        event_type = str(event.get("event_type") or "")
        operation = str(event.get("operation") or "")
        category = str(event.get("category") or "")
        status = str(event.get("status") or "")
        task_id = event.get("task_id")
        duration = event.get("duration_ms")
        duration_ms = int(duration) if isinstance(duration, (int, float)) else 0

        if event_type == "OPERATION_STARTED" and operation == "campaign_run":
            if campaign_run_started is None and moment is not None:
                campaign_run_started = moment
        if event_type == "TASK_FIRST_WRITE" and moment is not None and first_write_at is None:
            first_write_at = moment

        if _terminal(event):
            summary["operation_counts"][operation] = (
                summary["operation_counts"].get(operation, 0) + 1
            )
            bucket = CATEGORY_BUCKETS.get(category)
            if bucket:
                summary["timing"][f"{bucket}_ms"] += duration_ms
            entry = by_operation.setdefault(
                operation, {"operation": operation, "executions": 0, "total_duration_ms": 0}
            )
            entry["executions"] += 1
            entry["total_duration_ms"] += duration_ms
            if category in RECOVERY_CATEGORIES:
                summary["workspace_recovery_counts"][operation] = (
                    summary["workspace_recovery_counts"].get(operation, 0) + 1
                )
            fp = event.get("input_fingerprint")
            if isinstance(fp, str) and fp:
                by_fingerprint.setdefault((operation, fp), []).append(event)

        propagated = bool((event.get("metadata") or {}).get("propagated"))
        if status == STATUS_FAILED and not propagated:
            code = str(event.get("error_code") or "UNKNOWN_ERROR")
            failure = summary["failure_counts"].setdefault(
                code, {"count": 0, "total_duration_ms": 0, "tasks": []}
            )
            failure["count"] += 1
            failure["total_duration_ms"] += duration_ms
            if isinstance(task_id, str) and task_id and task_id not in failure["tasks"]:
                failure["tasks"].append(task_id)

        if isinstance(task_id, str) and task_id:
            task = per_task.setdefault(
                task_id,
                {
                    "attempts": 0,
                    "eligible_at": None,
                    "first_write_at": None,
                    "completed": False,
                    "validation_executions": 0,
                    "verification_executions": 0,
                    "failures": 0,
                    "eligible_to_first_write_ms": None,
                    "implementation_ms": 0,
                    "validation_ms": 0,
                    "verification_ms": 0,
                    "total_ms": 0,
                },
            )
            attempt = event.get("attempt_number")
            if isinstance(attempt, int):
                task["attempts"] = max(task["attempts"], attempt)
            if event_type == "TASK_ELIGIBLE" and task["eligible_at"] is None:
                task["eligible_at"] = event.get("timestamp")
            if event_type == "TASK_FIRST_WRITE" and task["first_write_at"] is None:
                task["first_write_at"] = event.get("timestamp")
            if event_type == "TASK_COMPLETED":
                task["completed"] = True
            if _terminal(event):
                task["total_ms"] += duration_ms
                bucket = CATEGORY_BUCKETS.get(category)
                if bucket in {"implementation", "validation", "verification"}:
                    task[f"{bucket}_ms"] += duration_ms
                if category == "validation":
                    task["validation_executions"] += 1
                if category in {"verification", "gate"}:
                    task["verification_executions"] += 1
            if status == STATUS_FAILED and not propagated:
                task["failures"] += 1

    summary["run_ids"] = run_ids
    if timestamps:
        summary["wall_clock_ms"] = int(
            round((max(timestamps) - min(timestamps)).total_seconds() * 1000)
        )
    if campaign_run_started is not None and first_write_at is not None:
        summary["timing"]["time_to_first_write_ms"] = int(
            round((first_write_at - campaign_run_started).total_seconds() * 1000)
        )

    for task_id, task in per_task.items():
        eligible = _parse_ts(task["eligible_at"])
        wrote = _parse_ts(task["first_write_at"])
        if eligible is not None and wrote is not None:
            task["eligible_to_first_write_ms"] = int(
                round((wrote - eligible).total_seconds() * 1000)
            )
        if task["attempts"] > 1:
            summary["retry_counts"][task_id] = task["attempts"] - 1
    summary["per_task"] = per_task
    summary["task_counts"] = {
        "completed": sum(1 for task in per_task.values() if task["completed"]),
        "attempted": len(per_task),
    }

    repeated: list[dict[str, Any]] = []
    for (operation, fp), group in by_fingerprint.items():
        if len(group) < 2:
            continue
        durations = [
            int(item["duration_ms"]) if isinstance(item.get("duration_ms"), (int, float)) else 0
            for item in group
        ]
        repeated.append(
            {
                "operation": operation,
                "input_fingerprint": fp,
                "executions": len(group),
                "extra_executions": len(group) - 1,
                "total_duration_ms": sum(durations),
                # v1 is deliberately conservative: every execution after the
                # first is reported as extra. It is "repeated with the same
                # input", not a claim that the repeat was avoidable.
                "extra_duration_ms": sum(durations[1:]),
            }
        )
    repeated.sort(key=lambda item: (-item["extra_duration_ms"], item["operation"]))
    summary["repeated_operations"] = repeated

    consumers = sorted(
        by_operation.values(), key=lambda item: (-item["total_duration_ms"], item["operation"])
    )
    summary["top_time_consumers"] = consumers[:10]
    return summary


# -- rendering ----------------------------------------------------------


def _ms(value: Any) -> str:
    if value is None:
        return "n/a"
    total = int(value)
    seconds, millis = divmod(total, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {seconds:02d}s"
    if minutes:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}.{millis:03d}s"


def render_summary_markdown(summary: dict[str, Any]) -> str:
    """Render run-summary.md purely from the JSON summary."""
    timing = summary.get("timing") or {}
    counts = summary.get("task_counts") or {}
    lines = [
        "# PE execution trace",
        "",
        f"- **Campaign**: {summary.get('campaign_id') or 'unknown'}",
        f"- **Runs**: {', '.join(summary.get('run_ids') or []) or 'none'}",
        f"- **Wall clock**: {_ms(summary.get('wall_clock_ms'))}",
        f"- **Events**: {summary.get('event_count', 0)}",
        "",
        "## Task progress",
        "",
        f"- completed: {counts.get('completed', 0)}",
        f"- attempted: {counts.get('attempted', 0)}",
        "",
        "## Time distribution",
        "",
        "| Bucket | Duration |",
        "| --- | ---: |",
    ]
    for bucket in ("preparation", "implementation", "validation", "verification", "recovery"):
        lines.append(f"| {bucket} | {_ms(timing.get(f'{bucket}_ms', 0))} |")
    lines += [
        "",
        "## Time to first code",
        "",
        f"- campaign start to first write: {_ms(timing.get('time_to_first_write_ms'))}",
        "",
        "## Top 10 operations by duration",
        "",
        "| Operation | Executions | Total |",
        "| --- | ---: | ---: |",
    ]
    for item in summary.get("top_time_consumers") or []:
        lines.append(
            f"| {item['operation']} | {item['executions']} | {_ms(item['total_duration_ms'])} |"
        )
    lines += [
        "",
        "## Repeated operations with same inputs",
        "",
    ]
    repeated = summary.get("repeated_operations") or []
    if not repeated:
        lines.append("None observed.")
    else:
        lines += [
            "| Operation | Fingerprint | Executions | Extra | Extra time |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
        for item in repeated:
            lines.append(
                f"| {item['operation']} | `{item['input_fingerprint'][:12]}` | "
                f"{item['executions']} | {item['extra_executions']} | "
                f"{_ms(item['extra_duration_ms'])} |"
            )
    lines += ["", "## Failure counts", ""]
    failures = summary.get("failure_counts") or {}
    if not failures:
        lines.append("None recorded.")
    else:
        lines += ["| Error code | Count | Tasks |", "| --- | ---: | --- |"]
        for code, item in sorted(failures.items()):
            lines.append(f"| {code} | {item['count']} | {', '.join(item['tasks']) or '-'} |")
    lines += ["", "## Retry counts", ""]
    retries = summary.get("retry_counts") or {}
    if not retries:
        lines.append("None recorded.")
    else:
        lines += ["| Task | Retries |", "| --- | ---: |"]
        for task_id, count in sorted(retries.items()):
            lines.append(f"| {task_id} | {count} |")
    lines += [
        "",
        "## Per-task timings",
        "",
        "| Task | Eligible to first write | Implementation | Validation | Verification | "
        "Attempts | Total |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for task_id, task in sorted((summary.get("per_task") or {}).items()):
        lines.append(
            f"| {task_id} | {_ms(task.get('eligible_to_first_write_ms'))} | "
            f"{_ms(task.get('implementation_ms', 0))} | {_ms(task.get('validation_ms', 0))} | "
            f"{_ms(task.get('verification_ms', 0))} | {task.get('attempts', 0)} | "
            f"{_ms(task.get('total_ms', 0))} |"
        )
    lines += ["", "## Workspace / recovery counts", ""]
    recovery = summary.get("workspace_recovery_counts") or {}
    if not recovery:
        lines.append("None recorded.")
    else:
        lines += ["| Operation | Count |", "| --- | ---: |"]
        for operation, count in sorted(recovery.items()):
            lines.append(f"| {operation} | {count} |")
    return "\n".join(lines) + "\n"


def write_summary(workspace: Path, summary: dict[str, Any]) -> dict[str, Path]:
    telemetry = Path(workspace) / TELEMETRY_DIRNAME
    telemetry.mkdir(parents=True, exist_ok=True)
    json_path = telemetry / SUMMARY_JSON_FILENAME
    md_path = telemetry / SUMMARY_MD_FILENAME
    json_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_summary_markdown(summary), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def harvest_and_write(workspace: Path) -> dict[str, Any]:
    summary = harvest_trace(workspace)
    write_summary(workspace, summary)
    return summary


def render_terminal_summary(summary: dict[str, Any]) -> str:
    timing = summary.get("timing") or {}
    counts = summary.get("task_counts") or {}
    lines = [
        f"campaign: {summary.get('campaign_id') or 'unknown'}",
        f"runs:     {len(summary.get('run_ids') or [])}",
        f"wall:     {_ms(summary.get('wall_clock_ms'))}",
        f"tasks:    {counts.get('completed', 0)} completed / "
        f"{counts.get('attempted', 0)} attempted",
        f"first-write: {_ms(timing.get('time_to_first_write_ms'))}",
        "time: "
        + "  ".join(
            f"{bucket}={_ms(timing.get(f'{bucket}_ms', 0))}"
            for bucket in (
                "preparation",
                "implementation",
                "validation",
                "verification",
                "recovery",
            )
        ),
    ]
    repeated = summary.get("repeated_operations") or []
    lines.append(f"repeated-same-input: {len(repeated)} operation(s)")
    for item in repeated[:5]:
        lines.append(
            f"  {item['operation']}: {item['executions']}x "
            f"(+{_ms(item['extra_duration_ms'])} after the first)"
        )
    failures = summary.get("failure_counts") or {}
    lines.append(f"failures: {sum(item['count'] for item in failures.values())}")
    for code, item in sorted(failures.items()):
        lines.append(f"  {code}: {item['count']}")
    lines.append("slowest:")
    for item in (summary.get("top_time_consumers") or [])[:5]:
        lines.append(
            f"  {item['operation']}: {_ms(item['total_duration_ms'])} ({item['executions']}x)"
        )
    return "\n".join(lines)
