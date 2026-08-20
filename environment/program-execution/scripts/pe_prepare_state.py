#!/usr/bin/env python3
"""What preparation produced, from which inputs, and why it ran again.

`pe_timing.StageCache` can already reuse a stage's recorded result while its
inputs are unchanged, but PE-FAST-001 wired exactly one stage into it. Extending
that to the rest of preparation needs two things the bare cache does not provide.

The first is a filesystem check. A preparation stage is not a pure function: it
compiles a blueprint, clones a checkout, places a campaign source. Reusing its
recorded result is only sound while the files it wrote are still there, so a
cache entry alone is never sufficient evidence for a skip. Answering "is this
stage still done?" with a cache lookup, and being wrong, is worse than never
caching at all -- it produces a campaign that reports itself prepared and then
fails downstream with a missing path.

The second is a reason. When preparation is slow, the operator's question is
"why did it do that again?", and a cache that silently recomputes cannot answer.
Every decision here carries the reason it was made, and every reason is recorded
in `PREPARE_STATE.json` next to the campaign it describes.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from pe_timing import write_json_atomic  # noqa: E402 - sibling, after the sys.path guard

PREPARE_STATE_SCHEMA = "program-execution.prepare-state.v1"
LOCAL_ACCEPTANCE_SCHEMA = "program-execution.local-acceptance.v1"
LOCAL_ACCEPTED = "LOCAL_ACCEPTED"

# The three transitions that must never read a local acceptance as authority.
# They leave the machine, so they re-derive acceptance strictly.
NOT_SUFFICIENT_FOR = ("publish", "merge", "deploy")

# Reasons a stage ran. `REUSED` is the only one that skips work; the rest are
# the vocabulary of "why did preparation do that again?".
REUSED = "reused"
NO_RECORD = "no_prior_record"
INPUT_CHANGED = "input_changed"
OUTPUT_MISSING = "output_missing"
CACHE_DISABLED = "cache_disabled"


def record_local_acceptance(
    path: Path,
    *,
    campaign_id: str,
    revision: str,
    compile_key: str,
    launchability: dict[str, Any],
) -> Path:
    """Write the provenance for an acceptance granted by local evidence alone.

    In FAST local mode a campaign is accepted on exactly two facts: it compiled,
    and it is launchable. Those are enough to start work on this machine and are
    deliberately not enough to leave it, so the record names the facts and the
    fingerprint they were established at rather than asserting a bare verdict.

    The record is scoped `local_only`. It exists so that an acceptance nobody
    typed is still auditable -- not so that publish can skip its own checks.
    """
    return write_json_atomic(
        path,
        {
            "schema": LOCAL_ACCEPTANCE_SCHEMA,
            "status": LOCAL_ACCEPTED,
            "campaign_id": campaign_id,
            "authority": "local_only",
            "not_sufficient_for": list(NOT_SUFFICIENT_FOR),
            "revision": revision,
            "basis": {
                "compile": {"status": "PASS", "key": compile_key},
                "launchability": {
                    "status": "PASS" if launchability.get("launchable") else "FAIL",
                    "task_count": launchability.get("task_count"),
                    "inferred": bool(launchability.get("inferred")),
                },
            },
        },
    )


@dataclass(frozen=True)
class Decision:
    """Whether a stage may be skipped, and the reason either way."""

    reuse: bool
    reason: str
    detail: str = ""
    value: Any = None

    def as_detail(self) -> dict[str, Any]:
        """The shape recorded on a timer entry and in the durable state file."""
        out: dict[str, Any] = {"reused": self.reuse, "reason": self.reason}
        if self.detail:
            out["detail"] = self.detail
        return out


@dataclass
class StageRun:
    """The live handle a stage body uses to see and set its own result."""

    decision: Decision
    value: Any = None

    @property
    def reused(self) -> bool:
        """True when the stage's work is already done and may be skipped."""
        return self.decision.reuse


@dataclass
class PrepareState:
    """The durable answer to "what is already prepared, and from what?".

    Written next to the campaign as `PREPARE_STATE.json`. It is a record, not a
    lock: losing it costs a rebuild, never correctness.
    """

    path: Path
    campaign_id: str = ""
    stages: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path, *, campaign_id: str = "") -> PrepareState:
        target = Path(path)
        try:
            doc = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls(path=target, campaign_id=campaign_id)
        if doc.get("schema") != PREPARE_STATE_SCHEMA:
            return cls(path=target, campaign_id=campaign_id)
        stages = doc.get("stages")
        return cls(
            path=target,
            campaign_id=str(doc.get("campaign_id") or campaign_id),
            stages=dict(stages) if isinstance(stages, dict) else {},
        )

    def record(
        self,
        stage: str,
        *,
        key: str,
        decision: Decision,
        outputs: list[str] | None = None,
        seconds: float | None = None,
    ) -> None:
        entry: dict[str, Any] = {"key": key, **decision.as_detail()}
        if outputs is not None:
            entry["outputs"] = list(outputs)
        if seconds is not None:
            entry["duration_s"] = round(float(seconds), 3)
        self.stages[stage] = entry
        self.save()

    def report(self) -> dict[str, Any]:
        return {
            "schema": PREPARE_STATE_SCHEMA,
            "campaign_id": self.campaign_id,
            "stages": dict(self.stages),
        }

    def save(self) -> Path:
        return write_json_atomic(self.path, self.report())


class PrepareCache:
    """Decide whether a preparation stage may be skipped, and say why.

    Wraps `pe_timing.StageCache` with the on-disk verification that a
    side-effecting stage requires, and records every decision in `PrepareState`.
    """

    def __init__(self, cache: Any, state: PrepareState) -> None:
        self.cache = cache
        self.state = state

    def decide(self, stage: str, key: str, *, outputs: list[Path] | None = None) -> Decision:
        """May `stage` be skipped, given `key` and the outputs it should have left?

        `key` is a content fingerprint of the stage's inputs, so a changed input
        is a changed key and cannot produce a hit. `outputs` are the paths the
        stage is responsible for having created; every one must still exist.
        """
        if not getattr(self.cache, "enabled", False):
            return Decision(False, CACHE_DISABLED)
        cached = self.cache.get(stage, key)
        if cached is None:
            # StageCache.get returns None both for "never ran" and for "ran with
            # a different key". Distinguish them, because "input_changed" is an
            # actionable answer and "no_prior_record" is not the same news.
            prior = self.state.stages.get(stage)
            if prior and prior.get("key") and prior.get("key") != key:
                return Decision(False, INPUT_CHANGED, detail=f"key {prior['key'][:12]}→{key[:12]}")
            return Decision(False, NO_RECORD)
        for path in outputs or []:
            if not Path(path).exists():
                return Decision(False, OUTPUT_MISSING, detail=str(path))
        return Decision(True, REUSED, value=cached)

    def store(self, stage: str, key: str, value: Any) -> None:
        self.cache.put(stage, key, value)

    @contextmanager
    def stage(
        self,
        timer: Any,
        name: str,
        key: str,
        *,
        outputs: list[Path] | None = None,
        verify: Callable[[Any], bool] | None = None,
    ) -> Iterator[StageRun]:
        """Time `name`, decide whether its body may be skipped, and record why.

        The body checks `run.reused` and, when it does the work, assigns the
        result to `run.value` so it can be reused next time. `verify` covers the
        stages whose outputs are only known from the cached value itself: it is
        given that value and returns False to downgrade the hit to a miss.
        """
        decision = self.decide(name, key, outputs=outputs)
        if decision.reuse and verify is not None and not verify(decision.value):
            decision = Decision(False, OUTPUT_MISSING, detail="cached output failed verification")
        run = StageRun(decision=decision, value=decision.value if decision.reuse else None)
        with timer.stage(name) as entry:
            entry["cached"] = decision.reuse
            detail = dict(entry.get("detail") or {})
            detail.update(decision.as_detail())
            entry["detail"] = detail
            yield run
        self.commit(
            name,
            key,
            decision,
            outputs=outputs,
            value=run.value,
            seconds=entry.get("duration_s"),
        )

    def commit(
        self,
        stage: str,
        key: str,
        decision: Decision,
        *,
        outputs: list[Path] | None = None,
        value: Any = None,
        seconds: float | None = None,
    ) -> None:
        """Persist a completed stage: cache its result and record the decision."""
        if not decision.reuse and value is not None:
            self.store(stage, key, value)
        self.state.record(
            stage,
            key=key,
            decision=decision,
            outputs=[str(path) for path in (outputs or [])],
            seconds=seconds,
        )
