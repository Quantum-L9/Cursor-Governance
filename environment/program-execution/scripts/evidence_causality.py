"""Evidence inputs must be admission evidence or the output of an earlier task.

A catalog id is not satisfied by a new ``EVID-RUNTIME-*`` row. The task that
lists it as an input waits until that exact id is ``available``. This module
is the check that runs before a campaign arms a task, and the list of catalog
rows a passing task is allowed to mark available.
"""

from __future__ import annotations

import re
from typing import Any

_TASK_ID = re.compile(r"TASK-\d+")
_COLLECT_AT_TASK = re.compile(r"collect_at_task[_-](\d+)", re.IGNORECASE)
_COLLECT_AT_NAMED = re.compile(r"collect_at_(TASK-\d+)", re.IGNORECASE)


def _text(value: object) -> str:
    return str(value or "").strip()


def _is_admission(freshness: str) -> bool:
    text = freshness.strip().lower()
    if not text:
        return False
    if text in {"locked"} or text.startswith("bound_at_") or text.startswith("collect_before_"):
        return True
    return text.startswith("collect_at_admission")


def _named_task(freshness: str) -> str | None:
    match = _COLLECT_AT_TASK.fullmatch(freshness.strip())
    if match:
        return f"TASK-{int(match.group(1)):03d}"
    match = _COLLECT_AT_NAMED.fullmatch(freshness.strip())
    if match:
        return match.group(1).upper()
    return None


def _explicit_producer(item: dict[str, Any]) -> str | None:
    producer = _text(item.get("producer"))
    if _TASK_ID.fullmatch(producer):
        return producer
    return None


def _input_ids(task: dict[str, Any]) -> list[str]:
    raw = task.get("input_evidence_ids")
    if raw is None:
        raw = task.get("required_evidence") or []
    return [_text(item) for item in raw if _text(item)]


def _gate_ids(task: dict[str, Any]) -> list[str]:
    raw = task.get("completion_gate_ids")
    if raw is None:
        raw = task.get("completion_gates") or []
    return [_text(item) for item in raw if _text(item)]


def _gate_owners(tasks: list[dict[str, Any]]) -> dict[str, set[str]]:
    owners: dict[str, set[str]] = {}
    for task in tasks:
        task_id = _text(task.get("id"))
        if not task_id:
            continue
        for gate_id in _gate_ids(task):
            owners.setdefault(gate_id, set()).add(task_id)
    return owners


def producing_task_ids(item: dict[str, Any], tasks: list[dict[str, Any]]) -> set[str]:
    """Tasks whose pass records this catalog id as available.

    Admission evidence is collected before any task. A freshness that names a
    task means that task, even when the same task also lists the id as an
    input — that overlap is the circular case. ``collect_after_*`` evidence is
    produced by the owner of a supported gate who does not itself consume the id.
    """
    freshness = _text(item.get("freshness"))
    if _is_admission(freshness):
        return set()
    named = _named_task(freshness)
    if named:
        return {named}
    producer = _explicit_producer(item)
    if producer:
        return {producer}
    if not freshness.startswith("collect_after_") and not freshness.startswith("collect_at_"):
        return set()
    evidence_id = _text(item.get("id"))
    consumers = {_text(task.get("id")) for task in tasks if evidence_id in _input_ids(task)}
    owners = _gate_owners(tasks)
    produced: set[str] = set()
    for support in item.get("supports") or []:
        support_id = _text(support)
        if not support_id:
            continue
        if support_id.startswith("TASK-") and support_id not in consumers:
            produced.add(support_id)
        for owner in owners.get(support_id, ()):
            if owner not in consumers:
                produced.add(owner)
    return produced


def task_wave_rank(waves: list[Any] | None) -> dict[str, int]:
    items = [wave for wave in waves or [] if isinstance(wave, dict)]
    if items and all("sequence" in wave for wave in items):
        rank: dict[str, int] = {}
        for wave in items:
            try:
                sequence = int(wave["sequence"])
            except (TypeError, ValueError):
                sequence = 0
            for task_id in wave.get("task_ids") or []:
                rank[_text(task_id)] = sequence
        return rank
    return _rank_by_predecessor(items)


def _rank_by_predecessor(waves: list[dict[str, Any]]) -> dict[str, int]:
    by_id = {_text(wave.get("id")): wave for wave in waves if _text(wave.get("id"))}
    memo: dict[str, int] = {}

    def depth(wave_id: str, stack: frozenset[str]) -> int:
        if wave_id in memo:
            return memo[wave_id]
        if wave_id in stack:
            memo[wave_id] = 0
            return 0
        wave = by_id.get(wave_id) or {}
        preds = [
            _text(pred)
            for pred in (wave.get("predecessor_wave_ids") or wave.get("depends_on") or [])
            if _text(pred)
        ]
        if not preds:
            memo[wave_id] = 0
            return 0
        value = 1 + max(depth(pred, stack | {wave_id}) for pred in preds)
        memo[wave_id] = value
        return value

    rank: dict[str, int] = {}
    for index, wave in enumerate(waves):
        wave_id = _text(wave.get("id"))
        sequence = depth(wave_id, frozenset()) if wave_id in by_id else index
        for task_id in wave.get("task_ids") or []:
            rank[_text(task_id)] = sequence
    return rank


def _earlier_tasks(
    task_id: str, inbound: dict[str, set[str]], wave_rank: dict[str, int]
) -> set[str]:
    seen: set[str] = set()
    stack = list(inbound.get(task_id, ()))
    while stack:
        current = stack.pop()
        if not current or current in seen or current == task_id:
            continue
        seen.add(current)
        stack.extend(inbound.get(current, ()))
    mine = wave_rank.get(task_id)
    if mine is not None:
        for other, rank in wave_rank.items():
            if other != task_id and rank < mine:
                seen.add(other)
    return seen


def evidence_input_errors(
    tasks: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    wave_rank: dict[str, int] | None = None,
) -> list[str]:
    """Refusals for catalog inputs no earlier task can record available.

    Evidence with no freshness and no task producer is left alone so a
    blueprint compiled before this check still validates. Admission freshness
    is collected before tasks, not by a task.
    """
    by_id = {_text(item.get("id")): item for item in evidence if _text(item.get("id"))}
    if not any(_text(item.get("freshness")) or _explicit_producer(item) for item in by_id.values()):
        return []
    inbound: dict[str, set[str]] = {}
    for edge in edges:
        source = _text(edge.get("from"))
        dest = _text(edge.get("to"))
        if source and dest:
            inbound.setdefault(dest, set()).add(source)
    rank = wave_rank or {}
    errors: list[str] = []
    for task in tasks:
        task_id = _text(task.get("id"))
        if not task_id:
            continue
        earlier = _earlier_tasks(task_id, inbound, rank)
        for evidence_id in _input_ids(task):
            item = by_id.get(evidence_id)
            if item is None:
                continue
            freshness = _text(item.get("freshness"))
            if not freshness and not _explicit_producer(item):
                continue
            if _is_admission(freshness):
                continue
            producers = producing_task_ids(item, tasks)
            if task_id in producers:
                schedule = freshness or _text(item.get("producer"))
                errors.append(
                    f"task {task_id} lists {evidence_id} as input evidence, but "
                    f"{evidence_id} is collected at {task_id} ({schedule}); "
                    "a task cannot consume its own output"
                )
                continue
            if not producers or producers.isdisjoint(earlier):
                named = ", ".join(sorted(producers)) if producers else "no task"
                detail = f", freshness {freshness}" if freshness else ""
                errors.append(
                    f"task {task_id} lists {evidence_id} as input evidence, but no earlier "
                    f"task can record {evidence_id} available (collected by {named}{detail})"
                )
    return errors


def errors_for_campaign_source(document: dict[str, Any]) -> list[str]:
    return evidence_input_errors(
        list(document.get("tasks") or []),
        list(document.get("evidence_requirements") or []),
        list(document.get("dependency_edges") or []),
        wave_rank=task_wave_rank(list(document.get("waves") or [])),
    )


def catalog_updates_for_passed_task(
    items: list[dict[str, Any]],
    task_id: str,
    tasks: list[dict[str, Any]],
    *,
    revision: str,
    source: str,
    produced_at: str,
    digest: str | None,
) -> list[dict[str, Any]]:
    """Catalog rows this pass makes available. Runtime evidence ids are not catalog ids."""
    updates: list[dict[str, Any]] = []
    for item in items:
        evidence_id = _text(item.get("id"))
        if not evidence_id or evidence_id.startswith("EVID-RUNTIME-"):
            continue
        if task_id not in producing_task_ids(item, tasks):
            continue
        updated = dict(item)
        updated["status"] = "available"
        updated["result"] = "PASS"
        if revision:
            updated["revision"] = revision
        updated["source"] = source
        updated["produced_at"] = produced_at
        if digest:
            updated["digest"] = digest
        updates.append(updated)
    return updates
