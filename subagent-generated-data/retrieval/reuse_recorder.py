from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION = ROOT / "subagent-generated-data" / "orchestration"
import sys

sys.path.insert(0, str(ORCHESTRATION))
from state_store import (
    PipelineStateStore,
    deterministic_id,
)

VALID_OUTCOMES = {
    "accelerated_execution",
    "prevented_error",
    "improved_validation",
    "improved_context",
    "reduced_discovery",
    "improved_scope_control",
    "improved_contract",
    "no_observable_value",
    "caused_confusion",
    "stale",
    "incorrect",
}


@dataclass(frozen=True)
class ReuseDispatchResult:
    event_id: str
    local_recorded: bool
    remote_dispatched: bool
    remote_response: Mapping[str, Any] | None
    invalidation_candidate: Mapping[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "local_recorded": self.local_recorded,
            "remote_dispatched": self.remote_dispatched,
            "remote_response": (
                dict(self.remote_response) if self.remote_response is not None else None
            ),
            "invalidation_candidate": (
                dict(self.invalidation_candidate)
                if self.invalidation_candidate is not None
                else None
            ),
        }


class ReuseRecorder:
    def __init__(
        self,
        store: PipelineStateStore,
        *,
        command: Sequence[str] | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.store = store
        self.command = tuple(command or ())
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(
        cls,
        store: PipelineStateStore,
    ) -> ReuseRecorder:
        raw = os.environ.get(
            "L9_SGD_GRAPHITI_REUSE_COMMAND",
            "",
        ).strip()
        return cls(
            store,
            command=shlex.split(raw) if raw else (),
        )

    def record_selection(
        self,
        *,
        record_id: str,
        campaign_id: str,
        action_id: str,
        agent_id: str,
        context_pack_id: str,
        payload: Mapping[str, Any],
    ) -> ReuseDispatchResult:
        return self._record(
            stage="selected",
            record_id=record_id,
            campaign_id=campaign_id,
            action_id=action_id,
            agent_id=agent_id,
            context_pack_id=context_pack_id,
            outcome=None,
            payload=payload,
            dispatch_remote=False,
        )

    def record_injection(
        self,
        *,
        record_id: str,
        campaign_id: str,
        action_id: str,
        agent_id: str,
        context_pack_id: str,
        payload: Mapping[str, Any],
    ) -> ReuseDispatchResult:
        return self._record(
            stage="injected",
            record_id=record_id,
            campaign_id=campaign_id,
            action_id=action_id,
            agent_id=agent_id,
            context_pack_id=context_pack_id,
            outcome=None,
            payload=payload,
            dispatch_remote=False,
        )

    def finalize_outcome(
        self,
        *,
        record_id: str,
        campaign_id: str,
        action_id: str,
        agent_id: str,
        context_pack_id: str,
        outcome: str,
        correction_required: bool,
        validity_confirmed: bool,
        evidence: Mapping[str, Any],
    ) -> ReuseDispatchResult:
        if outcome not in VALID_OUTCOMES:
            raise ValueError(f"Unsupported reuse outcome: {outcome}")
        payload = {
            "schema_version": "1.0.0",
            "kind": "MemoryReuseEvent",
            "record_id": record_id,
            "consumer": {
                "campaign_id": campaign_id,
                "action_id": action_id,
                "agent_id": agent_id,
            },
            "use": {
                "context_pack_id": context_pack_id,
                "injection_method": "agent_contract_context",
            },
            "outcome": outcome,
            "evidence": dict(evidence),
            "correction_required": correction_required,
            "validity_confirmed": validity_confirmed,
        }
        return self._record(
            stage="finalized",
            record_id=record_id,
            campaign_id=campaign_id,
            action_id=action_id,
            agent_id=agent_id,
            context_pack_id=context_pack_id,
            outcome=outcome,
            payload=payload,
            dispatch_remote=True,
        )

    def _record(
        self,
        *,
        stage: str,
        record_id: str,
        campaign_id: str,
        action_id: str,
        agent_id: str,
        context_pack_id: str,
        outcome: str | None,
        payload: Mapping[str, Any],
        dispatch_remote: bool,
    ) -> ReuseDispatchResult:
        event_id = deterministic_id(
            "reuse",
            {
                "record_id": record_id,
                "campaign_id": campaign_id,
                "action_id": action_id,
                "agent_id": agent_id,
                "context_pack_id": context_pack_id,
                "stage": stage,
                "outcome": outcome,
            },
        )
        _, created = self.store.record_reuse_event(
            event_id=event_id,
            record_id=record_id,
            campaign_id=campaign_id,
            action_id=action_id,
            agent_id=agent_id,
            context_pack_id=context_pack_id,
            stage=stage,
            outcome=outcome,
            payload=payload,
        )
        response: Mapping[str, Any] | None = None
        remote_dispatched = False
        if dispatch_remote and self.command:
            response = self._dispatch(payload)
            remote_dispatched = True
        invalidation_candidate = None
        if stage == "finalized" and outcome in {
            "stale",
            "incorrect",
        }:
            invalidation_candidate = {
                "schema_version": "1.0.0",
                "kind": "SourceInvalidationRequest",
                "event_type": "failed_reuse_reported",
                "record_ids": [record_id],
                "reason": outcome,
                "requires_policy_approval": True,
                "source_reuse_event_id": event_id,
            }
        return ReuseDispatchResult(
            event_id=event_id,
            local_recorded=created,
            remote_dispatched=remote_dispatched,
            remote_response=response,
            invalidation_candidate=invalidation_candidate,
        )

    def _dispatch(
        self,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        completed = subprocess.run(
            list(self.command),
            input=json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ),
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"Reuse command failed: {completed.stderr.strip()}")
        response = json.loads(completed.stdout or "{}")
        if not isinstance(response, Mapping):
            raise RuntimeError("Reuse response must be an object")
        return response


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a finalized memory-reuse outcome.")
    parser.add_argument("--database", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--command", nargs="+")
    args = parser.parse_args()
    payload = json.loads(Path(args.event).read_text(encoding="utf-8"))
    recorder = ReuseRecorder(
        PipelineStateStore(args.database),
        command=args.command,
    )
    result = recorder.finalize_outcome(
        record_id=str(payload["record_id"]),
        campaign_id=str(payload["campaign_id"]),
        action_id=str(payload["action_id"]),
        agent_id=str(payload["agent_id"]),
        context_pack_id=str(payload["context_pack_id"]),
        outcome=str(payload["outcome"]),
        correction_required=bool(payload.get("correction_required", False)),
        validity_confirmed=bool(payload.get("validity_confirmed", True)),
        evidence=dict(payload.get("evidence", {})),
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
