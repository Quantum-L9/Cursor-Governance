#!/usr/bin/env python3
"""Stage timing, honest progress, and fingerprint-keyed reuse of preparation.

Three small things that were missing and made the system feel slow in ways
nobody could point at:

- nothing measured how long each stage took, so regressions were invisible;
- "preparation checklist 100%" was reported as if the campaign were done,
  when zero tasks had executed;
- every restart recomputed preparation stages whose inputs had not changed.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

TIMINGS_SCHEMA = "program-execution.stage-timings.v1"
PROGRESS_SCHEMA = "program-execution.progress.v1"
CACHE_SCHEMA = "program-execution.stage-cache.v1"

EXECUTION_STATES = {
    "LEASED",
    "PREPARED",
    "CONTRACTED",
    "EXECUTING",
    "SUBMITTED",
    "VERIFYING",
    "PASSED_LOCAL",
    "COMPLETED",
}
VERIFIED_STATES = {"PASSED_LOCAL", "COMPLETED"}


def format_duration(seconds: float) -> str:
    total = int(round(seconds))
    return f"{total // 60:02d}m {total % 60:02d}s"


class StageTimer:
    """Record how long each named stage took, and persist it for comparison."""

    def __init__(self, workspace: Path | None = None) -> None:
        self.workspace = Path(workspace) if workspace is not None else None
        self.stages: list[dict[str, Any]] = []
        self._started = time.monotonic()

    @contextmanager
    def stage(self, name: str, **detail: Any) -> Iterator[dict[str, Any]]:
        entry: dict[str, Any] = {"stage": name, "detail": dict(detail)}
        started = time.monotonic()
        try:
            yield entry
        finally:
            entry["duration_s"] = round(time.monotonic() - started, 3)
            entry.setdefault("cached", False)
            self.stages.append(entry)
            self.flush()

    def record(self, name: str, duration_s: float, **detail: Any) -> None:
        self.stages.append(
            {
                "stage": name,
                "duration_s": round(duration_s, 3),
                "cached": bool(detail.pop("cached", False)),
                "detail": detail,
            }
        )
        self.flush()

    def total_s(self) -> float:
        return time.monotonic() - self._started

    def by_phase(self, phases: dict[str, tuple[str, ...]]) -> dict[str, float]:
        totals = {phase: 0.0 for phase in phases}
        for entry in self.stages:
            for phase, names in phases.items():
                if entry["stage"] in names:
                    totals[phase] += float(entry.get("duration_s") or 0.0)
        return {phase: round(value, 3) for phase, value in totals.items()}

    def report(self) -> dict[str, Any]:
        return {
            "schema": TIMINGS_SCHEMA,
            "total_s": round(self.total_s(), 3),
            "stages": list(self.stages),
        }

    def flush(self) -> Path | None:
        if self.workspace is None:
            return None
        path = self.workspace / "runtime" / "TIMINGS.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.report(), indent=2, sort_keys=True) + "\n", "utf-8")
        return path

    def format(self) -> str:
        lines = ["timing:"]
        for entry in self.stages:
            mark = " (cached)" if entry.get("cached") else ""
            lines.append(f"  {entry['stage']:<24} {format_duration(entry['duration_s'])}{mark}")
        lines.append(f"  {'TOTAL':<24} {format_duration(self.total_s())}")
        return "\n".join(lines)


def fingerprint(*parts: Any) -> str:
    """Content fingerprint of stage inputs; file paths hash by content."""
    digest = hashlib.sha256()
    for part in parts:
        if isinstance(part, Path):
            digest.update(b"path:")
            digest.update(str(part).encode("utf-8"))
            if part.is_file():
                digest.update(part.read_bytes())
            elif part.is_dir():
                for item in sorted(part.rglob("*")):
                    if item.is_file():
                        digest.update(item.relative_to(part).as_posix().encode("utf-8"))
                        digest.update(item.read_bytes())
        else:
            digest.update(json.dumps(part, sort_keys=True, default=str).encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()


class StageCache:
    """Reuse a preparation stage's result while its inputs are unchanged.

    Restarting execution is not a reason to re-parse a source, recompile a
    blueprint, or re-run network-backed stack research — and a flaky research
    API must not send admission back to zero.
    """

    def __init__(self, root: Path, *, enabled: bool = True) -> None:
        self.root = Path(root)
        self.enabled = enabled

    def _path(self, stage: str) -> Path:
        return self.root / "cache" / f"{stage}.json"

    def get(self, stage: str, key: str) -> Any | None:
        if not self.enabled:
            return None
        path = self._path(stage)
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if payload.get("schema") != CACHE_SCHEMA or payload.get("key") != key:
            return None
        return payload.get("value")

    def put(self, stage: str, key: str, value: Any) -> None:
        if not self.enabled:
            return
        path = self._path(stage)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema": CACHE_SCHEMA, "stage": stage, "key": key, "value": value}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def invalidate(self, stage: str) -> None:
        self._path(stage).unlink(missing_ok=True)


def progress(
    tasks: list[dict[str, Any]],
    *,
    campaign_id: str,
    preparation: str,
    gates_total: int = 0,
    gates_passed: int = 0,
    published: str = "NOT STARTED",
    timings: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Separate the dimensions that were previously collapsed into one number."""
    states = [str(task.get("runtime_state") or "") for task in tasks]
    total = len(states)
    executed = sum(1 for state in states if state in EXECUTION_STATES)
    verified = sum(1 for state in states if state in VERIFIED_STATES)
    current = next(
        (
            {"task_id": str(task.get("id")), "state": str(task.get("runtime_state"))}
            for task in tasks
            if str(task.get("runtime_state") or "") in EXECUTION_STATES - {"COMPLETED"}
        ),
        None,
    )
    return {
        "schema": PROGRESS_SCHEMA,
        "campaign_id": campaign_id,
        "preparation": preparation,
        "execution": {"done": executed, "total": total},
        "verification": {"done": verified, "total": total},
        "exit_gates": {"done": gates_passed, "total": gates_total},
        "publish": published,
        "current": current,
        "elapsed": timings or {},
    }


def format_progress(report: dict[str, Any]) -> str:
    execution = report["execution"]
    verification = report["verification"]
    gates = report["exit_gates"]
    lines = [
        f"Campaign: {report['campaign_id']}",
        "",
        f"Preparation:  {report['preparation']}",
        f"Execution:    {execution['done']} / {execution['total']} tasks",
        f"Verification: {verification['done']} / {verification['total']}",
        f"Exit gates:   {gates['done']} / {gates['total']}",
        f"Publish:      {report['publish']}",
    ]
    current = report.get("current")
    if current:
        lines += ["", "Current:", f"  {current['task_id']}", f"  state: {current['state']}"]
    elapsed = report.get("elapsed") or {}
    if elapsed:
        lines.append("")
        for name, seconds in elapsed.items():
            lines.append(f"Elapsed {name}: {format_duration(float(seconds))}")
    return "\n".join(lines)
