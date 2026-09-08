"""Legacy provider-record reconciliation (campaign stage C10).

Before the realignment, session memory was written straight to the provider,
so the provider holds records the canonical store never saw. This module
classifies an **export** of such records (produced outside this boundary —
Cursor-Governance never reads the provider itself) and admits what memory
should own through the canonical control plane:

    A  canonical_known          digest already present canonically -> nothing to do
    B  provider_only_continuation  a PICKUP the canonical store lacks -> admit as a
                                continuation capsule (governed candidate)
    C  provider_only_durable    a lesson/insight/decision the store lacks -> admit
                                through the generic canonical write
    D  malformed                unparseable or empty -> reported, never admitted
    E  duplicate_in_export      same digest already classified in this run
    F  forbidden_namespace      the export names a namespace Cursor may never write
    G  refused_by_memory        memory rejected or quarantined the admission

Everything admitted here carries the producer ``Cursor-Governance/legacy-
reconciliation`` and the tag ``legacy_unverified``: it crossed canonical
admission, but its provenance is the provider's, not a session's. Dry run is
the default; ``--apply`` commits. Nothing here writes a provider.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ops.memory.control_plane_client import MemoryControlPlaneClient, OutcomeStatus
from ops.memory.namespace_context import forbidden_namespaces, load_registry
from ops.memory.session_contracts import PRODUCER, ContinuationCapsuleV2

CLASS_CANONICAL_KNOWN = "A_canonical_known"
CLASS_CONTINUATION = "B_provider_only_continuation"
CLASS_DURABLE = "C_provider_only_durable"
CLASS_MALFORMED = "D_malformed"
CLASS_DUPLICATE = "E_duplicate_in_export"
CLASS_FORBIDDEN = "F_forbidden_namespace"
CLASS_REFUSED = "G_refused_by_memory"

RECONCILIATION_PRODUCER = f"{PRODUCER}/legacy-reconciliation"
RECONCILIATION_VERSION = "legacy-reconciliation/1.0.0"
LEGACY_TAG = "legacy_unverified"
EXPORT_SCHEMA = "cursor.legacy-provider-export/v1"

_DURABLE_CLASSES = {"lesson": "insight", "insight": "insight", "decision": "decision"}
_NOT_ADMITTED = frozenset(
    {
        OutcomeStatus.CANONICAL_UNAVAILABLE,
        OutcomeStatus.TIMEOUT,
        OutcomeStatus.BINDING_FAILED,
        OutcomeStatus.INVALID_RECEIPT,
    }
)


@dataclass(frozen=True)
class LegacyRecord:
    record_id: str
    text: str
    kind: str | None = None
    created_at: str | None = None

    @property
    def digest(self) -> str:
        normalized = re.sub(r"\s+", " ", self.text).strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


@dataclass
class Classified:
    record: LegacyRecord
    klass: str
    reason: str
    objective: str = ""
    next_action: str = ""
    memory_class: str | None = None
    admission: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record.record_id,
            "digest": self.record.digest,
            "class": self.klass,
            "reason": self.reason,
            "memory_class": self.memory_class,
            "admission": self.admission,
        }


# ---------------------------------------------------------------------------
# Export parsing
# ---------------------------------------------------------------------------


def load_export(path: Path) -> tuple[str, list[LegacyRecord]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != EXPORT_SCHEMA:
        raise ValueError(f"export must carry schema {EXPORT_SCHEMA!r}")
    namespace = str(data.get("namespace") or "").strip()
    if not namespace:
        raise ValueError("export must name its namespace")
    records: list[LegacyRecord] = []
    for item in data.get("records") or []:
        if not isinstance(item, dict):
            records.append(LegacyRecord(record_id="", text=""))
            continue
        records.append(
            LegacyRecord(
                record_id=str(item.get("id") or item.get("uuid") or ""),
                text=str(item.get("text") or item.get("fact") or item.get("content") or ""),
                kind=(str(item["kind"]) if item.get("kind") else None),
                created_at=(str(item["created_at"]) if item.get("created_at") else None),
            )
        )
    return namespace, records


def _parse_pickup(text: str) -> tuple[str, str]:
    """``PICKUP|objective=…|next=…`` lines or a PICKUP JSON body -> (objective, next)."""
    objective = ""
    next_action = ""
    start = text.find("{")
    if start >= 0:
        try:
            data = json.loads(text[start:])
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            objective = str(data.get("active_objective") or "")[:500]
            nested = (data.get("next_action_contract") or {}).get("next_action")
            next_action = str(data.get("next_action") or nested or "")[:1000]
    for part in re.split(r"[|\n]", text):
        low = part.strip().lower()
        if low.startswith("objective=") and not objective:
            objective = part.strip().split("=", 1)[1].strip()[:500]
        elif low.startswith(("next=", "next_action=")) and not next_action:
            next_action = part.strip().split("=", 1)[1].strip()[:1000]
    return objective, next_action


def _is_pickup(record: LegacyRecord) -> bool:
    upper = record.text.upper()
    return (
        (record.kind or "").lower() in {"pickup_context", "pickup"}
        or "PICKUP|" in upper
        or '"TYPE": "PICKUP"' in upper
        or "ACTIVE_OBJECTIVE" in upper
    )


# ---------------------------------------------------------------------------
# Classification (pure)
# ---------------------------------------------------------------------------


def classify(
    records: Iterable[LegacyRecord],
    *,
    namespace: str,
    canonical_digests: Iterable[str] = (),
    forbidden: Iterable[str] = (),
) -> list[Classified]:
    known = set(canonical_digests)
    banned = set(forbidden)
    seen: set[str] = set()
    out: list[Classified] = []
    for record in records:
        if namespace in banned:
            out.append(Classified(record, CLASS_FORBIDDEN, f"namespace {namespace!r} is forbidden"))
            continue
        if not record.record_id or not record.text.strip():
            out.append(Classified(record, CLASS_MALFORMED, "empty id or text"))
            continue
        digest = record.digest
        if digest in known:
            out.append(Classified(record, CLASS_CANONICAL_KNOWN, "digest present canonically"))
            continue
        if digest in seen:
            out.append(Classified(record, CLASS_DUPLICATE, "same digest earlier in export"))
            continue
        seen.add(digest)
        if _is_pickup(record):
            objective, next_action = _parse_pickup(record.text)
            if not objective and not next_action:
                out.append(Classified(record, CLASS_MALFORMED, "PICKUP without objective/next"))
                continue
            out.append(
                Classified(
                    record,
                    CLASS_CONTINUATION,
                    "provider-only continuation",
                    objective=objective or "Continue work",
                    next_action=next_action or "Proceed from user request",
                )
            )
            continue
        kind = (record.kind or "insight").lower()
        memory_class = _DURABLE_CLASSES.get(kind)
        if memory_class is None:
            out.append(Classified(record, CLASS_MALFORMED, f"unsupported kind {kind!r}"))
            continue
        out.append(
            Classified(record, CLASS_DURABLE, "provider-only durable", memory_class=memory_class)
        )
    return out


def summary(classified: Sequence[Classified]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in classified:
        counts[item.klass] = counts.get(item.klass, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Admission (through the control plane only)
# ---------------------------------------------------------------------------


def _capsule(item: Classified, namespace: str) -> ContinuationCapsuleV2:
    record = item.record
    return ContinuationCapsuleV2(
        session_id=f"legacy-{record.record_id}"[:120],
        repository_identity=namespace,
        objective=item.objective,
        next_action=item.next_action,
        repository_state_digest="unknown",
        producer_version=RECONCILIATION_VERSION,
        unfinished_work=(f"{LEGACY_TAG}: provider record {record.record_id}",),
        created_at=record.created_at or datetime.now(UTC).isoformat(),
        producer=RECONCILIATION_PRODUCER,
    )


def apply(
    classified: Sequence[Classified],
    *,
    client: MemoryControlPlaneClient,
    workspace: str,
    namespace: str,
    agent_id: str = "legacy-reconciliation",
    dry_run: bool = True,
) -> list[Classified]:
    """Admit B and C records; every other class is left untouched."""
    for item in classified:
        if item.klass == CLASS_CONTINUATION:
            candidate = _capsule(item, namespace).to_governed_candidate(
                namespace=namespace, source_sha="0" * 40, agent_id=agent_id
            )
            if dry_run:
                item.admission = {"dry_run": True, "candidate_id": candidate["candidate_id"]}
                continue
            outcome = client.ingest_candidate(candidate, workspace=workspace)
        elif item.klass == CLASS_DURABLE:
            if dry_run:
                item.admission = {"dry_run": True, "idempotency_key": _key(item)}
                continue
            outcome = client.write(
                item.record.text.strip(),
                workspace=workspace,
                namespace=namespace,
                memory_class=item.memory_class or "insight",
                tags=(LEGACY_TAG, "migrated"),
                idempotency_key=_key(item),
                source="legacy-reconciliation",
                source_id=item.record.record_id,
            )
        else:
            continue
        receipt = outcome.receipt
        item.admission = {
            "status": outcome.status.value,
            "receipt_status": getattr(receipt, "status", None),
            "record_id": getattr(receipt, "record_id", None),
            "error": outcome.error,
        }
        if outcome.status in _NOT_ADMITTED:
            raise RuntimeError(f"memory unavailable during reconciliation: {outcome.status.value}")
        if not outcome.ok:
            item.klass = CLASS_REFUSED
            item.reason = f"memory {outcome.status.value.lower()}"
    return list(classified)


def _key(item: Classified) -> str:
    return f"legacy:{item.record.digest}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def canonical_digests_from_search(
    client: MemoryControlPlaneClient, *, workspace: str, namespace: str
) -> set[str]:
    """Digests of what the canonical store already holds for this namespace."""
    digests: set[str] = set()
    for tags in ((), ("session_continuation",)):
        outcome = client.search(
            "*",
            workspace=workspace,
            write_namespace_hint=namespace,
            read_namespace_hints=(namespace,),
            tags=tags,
            limit=200,
        )
        receipt = outcome.receipt
        if receipt is None:
            continue
        for hit in receipt.hits:
            digests.add(LegacyRecord(record_id="x", text=hit.record.content).digest)
    return digests


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--export", required=True, help="provider export JSON (schema above)")
    parser.add_argument("--workspace", default=os.getcwd())
    parser.add_argument("--apply", action="store_true", help="commit admissions (default: dry run)")
    parser.add_argument("--agent-id", default="legacy-reconciliation")
    parser.add_argument("--no-canonical-lookup", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    from ops.memory.runtime_binding import resolve_runtime_binding

    namespace, records = load_export(Path(args.export))
    forbidden = forbidden_namespaces(load_registry())
    client = MemoryControlPlaneClient(resolve_runtime_binding(), session_id="legacy-reconciliation")
    known: set[str] = set()
    if not args.no_canonical_lookup and client.binding.ok:
        known = canonical_digests_from_search(client, workspace=args.workspace, namespace=namespace)
    classified = classify(
        records, namespace=namespace, canonical_digests=known, forbidden=forbidden
    )
    if args.apply and not client.binding.ok:
        sys.stderr.write("memory runtime unbound: " + "; ".join(client.binding.reasons) + "\n")
        return 1
    apply(
        classified,
        client=client,
        workspace=args.workspace,
        namespace=namespace,
        agent_id=args.agent_id,
        dry_run=not args.apply,
    )
    counts = summary(classified)
    mode = "apply" if args.apply else "dry_run"
    report: dict[str, Any] = {
        "schema": "cursor.legacy-reconciliation-report/v1",
        "authority": "none",
        "namespace": namespace,
        "mode": mode,
        "canonical_digests_known": len(known),
        "summary": counts,
        "records": [item.as_dict() for item in classified],
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(f"legacy reconciliation [{mode}] namespace={namespace}\n")
        for klass, count in sorted(counts.items()):
            sys.stdout.write(f"  {klass:<32} {count}\n")
    return 0


__all__ = [
    "CLASS_CANONICAL_KNOWN",
    "CLASS_CONTINUATION",
    "CLASS_DUPLICATE",
    "CLASS_DURABLE",
    "CLASS_FORBIDDEN",
    "CLASS_MALFORMED",
    "CLASS_REFUSED",
    "EXPORT_SCHEMA",
    "LEGACY_TAG",
    "Classified",
    "LegacyRecord",
    "apply",
    "classify",
    "load_export",
    "main",
    "summary",
]


if __name__ == "__main__":
    raise SystemExit(main())
