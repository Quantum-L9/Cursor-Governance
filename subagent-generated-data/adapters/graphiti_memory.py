from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GraphitiAdapterError(RuntimeError):
    """Raised when governed memory delivery cannot be completed safely."""


@dataclass(frozen=True)
class MemoryCandidate:
    schema_version: str
    kind: str
    candidate_id: str
    source: Mapping[str, Any]
    knowledge: Mapping[str, Any]
    governance: Mapping[str, Any]
    provenance: Mapping[str, Any]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "candidate_id": self.candidate_id,
            "source": dict(self.source),
            "knowledge": dict(self.knowledge),
            "governance": dict(self.governance),
            "provenance": dict(self.provenance),
            "generated_at": self.generated_at,
        }


@dataclass(frozen=True)
class MemoryDeliveryResult:
    candidate_id: str
    status: str
    transport: str
    destination_reference: str
    receipt_hash: str
    response: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "status": self.status,
            "transport": self.transport,
            "destination_reference": self.destination_reference,
            "receipt_hash": self.receipt_hash,
            "response": dict(self.response),
        }


class MemoryTransport(Protocol):
    def deliver(
        self,
        candidate: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Deliver one governed memory candidate."""


class FileOutboxTransport:
    """Durably enqueue candidates for later Graphiti ingestion."""

    def __init__(self, outbox_dir: str | Path) -> None:
        self.outbox_dir = Path(outbox_dir)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)

    def deliver(
        self,
        candidate: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        candidate_id = str(candidate["candidate_id"])
        target = self.outbox_dir / f"{candidate_id}.json"
        payload = canonical_json(candidate)
        payload_hash = hashlib.sha256(payload).hexdigest()
        if target.exists():
            existing = target.read_bytes()
            existing_hash = hashlib.sha256(existing).hexdigest()
            if existing_hash != payload_hash:
                raise GraphitiAdapterError(
                    f"Candidate ID collision with different payload: {candidate_id}"
                )
            return {
                "status": "already_enqueued",
                "path": str(target),
                "payload_hash": payload_hash,
            }
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=self.outbox_dir,
            prefix=f".{candidate_id}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            temporary = Path(handle.name)
        temporary.replace(target)
        return {
            "status": "enqueued",
            "path": str(target),
            "payload_hash": payload_hash,
        }


class HttpJsonTransport:
    """Submit governed candidates to an HTTP JSON endpoint."""

    def __init__(
        self,
        endpoint: str,
        *,
        bearer_token: str | None = None,
        timeout_seconds: int = 20,
    ) -> None:
        if not endpoint.startswith(("http://", "https://")):
            raise ValueError("Graphiti HTTP endpoint must use http:// or https://")
        self.endpoint = endpoint
        self.bearer_token = bearer_token
        self.timeout_seconds = timeout_seconds

    def deliver(
        self,
        candidate: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "l9-subagent-generated-data/1.0",
        }
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        request = Request(
            self.endpoint,
            data=canonical_json(candidate),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                body = response.read()
                status_code = response.status
        except HTTPError as exc:
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )
            raise GraphitiAdapterError(
                f"Graphiti endpoint rejected candidate: HTTP {exc.code}: {body}"
            ) from exc
        except URLError as exc:
            raise GraphitiAdapterError(f"Graphiti endpoint unavailable: {exc}") from exc
        if not 200 <= status_code < 300:
            raise GraphitiAdapterError(f"Unexpected Graphiti status: {status_code}")
        if not body:
            return {
                "status": "accepted",
                "http_status": status_code,
            }
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {
                "raw_response": body.decode(
                    "utf-8",
                    errors="replace",
                )
            }
        if not isinstance(parsed, Mapping):
            parsed = {"response": parsed}
        return {
            "status": "accepted",
            "http_status": status_code,
            **dict(parsed),
        }


class CommandTransport:
    """Invoke an explicit Graphiti ingestion command with JSON on stdin."""

    def __init__(
        self,
        command: list[str],
        *,
        timeout_seconds: int = 30,
    ) -> None:
        if not command:
            raise ValueError("Graphiti command transport requires a command")
        self.command = command
        self.timeout_seconds = timeout_seconds

    def deliver(
        self,
        candidate: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        completed = subprocess.run(
            self.command,
            input=canonical_json(candidate),
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        stdout = completed.stdout.decode(
            "utf-8",
            errors="replace",
        )
        stderr = completed.stderr.decode(
            "utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            raise GraphitiAdapterError(
                f"Graphiti command rejected candidate: exit={completed.returncode}; stderr={stderr}"
            )
        if not stdout.strip():
            response: Mapping[str, Any] = {"status": "accepted"}
        else:
            try:
                parsed = json.loads(stdout)
            except json.JSONDecodeError:
                parsed = {
                    "status": "accepted",
                    "stdout": stdout,
                }
            if not isinstance(parsed, Mapping):
                response = {
                    "status": "accepted",
                    "response": parsed,
                }
            else:
                response = parsed
        return {
            **dict(response),
            "stderr": stderr,
            "exit_code": completed.returncode,
        }


class GraphitiMemoryAdapter:
    """Compile approved memory-route units into governed candidates."""

    def __init__(self, transport: MemoryTransport) -> None:
        self.transport = transport

    def compile_candidate(
        self,
        *,
        harvested_unit: Mapping[str, Any],
        routing_decision: Mapping[str, Any],
        promotion_result: Mapping[str, Any],
        packet: Mapping[str, Any],
    ) -> MemoryCandidate:
        self._require_memory_promotion(
            harvested_unit=harvested_unit,
            routing_decision=routing_decision,
            promotion_result=promotion_result,
        )
        original = harvested_unit["original_unit"]
        identity = packet["identity"]
        provenance = packet["provenance"]
        unit_id = str(harvested_unit["unit_id"])
        route_decision_id = str(routing_decision["decision_id"])
        candidate_seed = {
            "unit_id": unit_id,
            "packet_id": packet["packet_id"],
            "route_decision_id": route_decision_id,
            "promotion_id": promotion_result["promotion_id"],
            "statement_hash": harvested_unit["statement_hash"],
        }
        candidate_hash = hashlib.sha256(canonical_json(candidate_seed)).hexdigest()
        generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return MemoryCandidate(
            schema_version="1.0.0",
            kind="MemoryCandidate",
            candidate_id=f"memcand-{candidate_hash[:24]}",
            source={
                "campaign_id": identity["campaign_id"],
                "graph_id": identity["graph_id"],
                "action_id": identity["action_id"],
                "agent_id": identity["agent_id"],
                "role": identity["role"],
                "lease_id": identity["lease_id"],
                "repository": identity["repository"],
                "repository_class": identity["repository_class"],
                "base_sha": identity["base_sha"],
                "packet_id": packet["packet_id"],
                "primary_artifact_id": packet["primary_result"]["artifact_id"],
            },
            knowledge={
                "unit_id": unit_id,
                "statement": original["statement"],
                "primary_class": original["primary_class"],
                "epistemic_status": original["epistemic_status"],
                "scope": original["scope"],
                "confidence": original["confidence"],
                "freshness": original["freshness"],
                "expected_reuse": original["expected_reuse"],
                "invalidation_conditions": original["invalidation_conditions"],
            },
            governance={
                "authority_class": "advisory",
                "route": "memory",
                "routing_decision_id": route_decision_id,
                "promotion_id": promotion_result["promotion_id"],
                "promotion_decision": promotion_result["decision"],
                "risk_class": promotion_result["risk_class"],
                "visibility": original.get(
                    "visibility",
                    "repository_local",
                ),
                "may_override_repository_state": False,
                "may_override_canonical_authority": False,
            },
            provenance={
                **dict(provenance),
                "source_evidence": original["source_evidence"],
                "statement_hash": harvested_unit["statement_hash"],
                "packet_hash": packet.get("packet_hash"),
            },
            generated_at=generated_at,
        )

    def deliver(
        self,
        candidate: MemoryCandidate,
    ) -> MemoryDeliveryResult:
        payload = candidate.to_dict()
        response = self.transport.deliver(payload)
        response_status = str(response.get("status", "unknown"))
        accepted_statuses = {
            "accepted",
            "enqueued",
            "already_enqueued",
            "merged",
            "contested",
            "quarantined",
        }
        if response_status not in accepted_statuses:
            raise GraphitiAdapterError(
                f"Graphiti transport returned unsupported status: {response_status!r}"
            )
        destination_reference = str(
            response.get(
                "memory_id",
                response.get(
                    "path",
                    response.get(
                        "candidate_id",
                        candidate.candidate_id,
                    ),
                ),
            )
        )
        receipt_payload = {
            "candidate_id": candidate.candidate_id,
            "status": response_status,
            "destination_reference": destination_reference,
            "response": dict(response),
        }
        receipt_hash = hashlib.sha256(canonical_json(receipt_payload)).hexdigest()
        return MemoryDeliveryResult(
            candidate_id=candidate.candidate_id,
            status=response_status,
            transport=type(self.transport).__name__,
            destination_reference=destination_reference,
            receipt_hash=receipt_hash,
            response=dict(response),
        )

    @staticmethod
    def _require_memory_promotion(
        *,
        harvested_unit: Mapping[str, Any],
        routing_decision: Mapping[str, Any],
        promotion_result: Mapping[str, Any],
    ) -> None:
        unit_id = str(harvested_unit.get("unit_id"))
        if routing_decision.get("unit_id") != unit_id:
            raise GraphitiAdapterError("Routing decision unit does not match harvested unit")
        if promotion_result.get("unit_id") != unit_id:
            raise GraphitiAdapterError("Promotion result unit does not match harvested unit")
        if routing_decision.get("route") != "memory":
            raise GraphitiAdapterError("Graphiti adapter only accepts memory route decisions")
        if routing_decision.get("status") != "eligible":
            raise GraphitiAdapterError("Graphiti adapter requires an eligible route decision")
        if promotion_result.get("decision") != "promote":
            raise GraphitiAdapterError("Graphiti adapter requires a promote decision")


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def select_transport(args: argparse.Namespace) -> MemoryTransport:
    if args.endpoint:
        return HttpJsonTransport(
            args.endpoint,
            bearer_token=(args.token or os.environ.get("L9_GRAPHITI_MEMORY_TOKEN")),
            timeout_seconds=args.timeout,
        )
    if args.command:
        return CommandTransport(
            args.command,
            timeout_seconds=args.timeout,
        )
    return FileOutboxTransport(args.outbox)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Compile and deliver one approved generated-data memory candidate.")
    )
    parser.add_argument("--packet", required=True)
    parser.add_argument("--harvested-unit", required=True)
    parser.add_argument("--routing-decision", required=True)
    parser.add_argument("--promotion-result", required=True)
    parser.add_argument(
        "--outbox",
        default=("subagent-generated-data/.runtime/memory-outbox"),
    )
    parser.add_argument("--endpoint")
    parser.add_argument("--token")
    parser.add_argument(
        "--command",
        nargs="+",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
    )
    parser.add_argument(
        "--compile-only",
        action="store_true",
    )
    args = parser.parse_args()
    adapter = GraphitiMemoryAdapter(select_transport(args))
    candidate = adapter.compile_candidate(
        harvested_unit=load_json(args.harvested_unit),
        routing_decision=load_json(args.routing_decision),
        promotion_result=load_json(args.promotion_result),
        packet=load_json(args.packet),
    )
    if args.compile_only:
        print(
            json.dumps(
                candidate.to_dict(),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    result = adapter.deliver(candidate)
    print(
        json.dumps(
            result.to_dict(),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
