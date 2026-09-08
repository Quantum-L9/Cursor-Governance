#!/usr/bin/env python3
"""Map a MemoryCandidate on stdin to a canonical memory write (stage C10).

The candidate's statement is admitted through the memory control plane
(``ops/memory``) as an ``insight`` with a stable idempotency key; memory
decides admission, dedup and quarantine, and its receipt is the verdict.
Nothing here calls a provider. The namespace is a *request* derived from the
candidate's recorded repository (registry match) or the drain workspace; a
recorded repository that matches no registry slug fails closed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

SOURCE = "generated-data"


def _namespace_from_candidate_source(source: Mapping[str, Any]) -> str | None:
    """Prefer the candidate's recorded repository over the drain process cwd."""
    recorded = str(source.get("repository") or "").strip()
    if not recorded:
        return None
    from ops.memory.namespace_context import aliases_for, load_registry

    registry = load_registry()
    repos = registry.get("repos") or {}
    if recorded in repos:
        return recorded
    needle = recorded.lower()
    for slug in repos:
        names = aliases_for(registry, str(slug))
        if any(name.lower() == needle for name in names):
            return str(slug)
        for name in names:
            basename = name.rsplit("/", 1)[-1]
            if basename and basename.lower() == needle:
                return str(slug)
        if needle == str(slug).lower():
            return str(slug)
    return None


def _candidate_from_stdin(raw: bytes) -> dict[str, Any]:
    parsed = json.loads(raw.decode("utf-8") if raw else "{}")
    if not isinstance(parsed, Mapping):
        raise ValueError("stdin must be a MemoryCandidate object")
    if str(parsed.get("kind") or "") != "MemoryCandidate":
        raise ValueError("stdin kind must be MemoryCandidate")
    return dict(parsed)


def _memory_client(session_id: str | None) -> Any:
    from ops.memory.control_plane_client import MemoryControlPlaneClient
    from ops.memory.runtime_binding import resolve_runtime_binding

    return MemoryControlPlaneClient(resolve_runtime_binding(), session_id=session_id)


def resolve_namespace(candidate: Mapping[str, Any], *, workspace: Path) -> str:
    """The namespace request for this candidate; raises when it cannot be honest."""
    from ops.memory.namespace_context import (
        forbidden_namespaces,
        load_registry,
        resolve_namespace_context,
    )

    source = candidate.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("candidate.source is required")
    recorded_repo = str(source.get("repository") or "").strip()
    explicit = _namespace_from_candidate_source(source)
    if recorded_repo and not explicit:
        raise RuntimeError(
            f"write blocked: no namespace match for candidate.source.repository={recorded_repo}"
        )
    context = resolve_namespace_context(workspace, explicit=explicit)
    namespace = context.write_namespace_hint
    if not namespace:
        raise RuntimeError(
            "write blocked: " + ("; ".join(context.warnings) or "namespace unresolved")
        )
    if namespace in forbidden_namespaces(load_registry()):
        raise RuntimeError(f"write blocked: namespace {namespace!r} is forbidden for writes")
    return namespace


def ingest_candidate(
    candidate: Mapping[str, Any],
    *,
    dry_run: bool = False,
    client: Any = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    knowledge = candidate.get("knowledge")
    source = candidate.get("source")
    if not isinstance(knowledge, Mapping) or not isinstance(source, Mapping):
        raise ValueError("candidate.knowledge and candidate.source are required")
    statement = str(knowledge.get("statement") or "").strip()
    if not statement:
        raise ValueError("candidate.knowledge.statement is required")
    candidate_id = str(candidate.get("candidate_id") or "")
    if not candidate_id:
        raise ValueError("candidate.candidate_id is required")
    workspace_path = Path(workspace or os.getcwd()).expanduser().resolve()
    namespace = resolve_namespace(candidate, workspace=workspace_path)
    tags = tuple(
        str(tag)
        for tag in ("sgd", knowledge.get("primary_class"), source.get("campaign_id"))
        if tag
    )
    if dry_run:
        return {
            "status": "accepted",
            "dry_run": True,
            "candidate_id": candidate_id,
            "memory_id": candidate_id,
            "write_receipt_id": candidate_id,
            "group_id": namespace,
        }
    client = client or _memory_client(str(source.get("packet_id") or "") or None)
    if not client.binding.ok:
        raise RuntimeError("memory runtime unbound: " + "; ".join(client.binding.reasons))
    outcome = client.write(
        statement,
        workspace=str(workspace_path),
        namespace=namespace,
        memory_class="insight",
        tags=tags,
        idempotency_key=f"sgd:{candidate_id}",
        source=SOURCE,
        source_id=candidate_id,
    )
    receipt = outcome.receipt
    if receipt is None:
        raise RuntimeError(f"write not admitted: {outcome.status.value}: {outcome.error or ''}")
    status = "accepted" if receipt.status == "admitted" else receipt.status
    if receipt.status == "duplicate":
        status = "deduplicated"
    return {
        "status": status,
        "candidate_id": candidate_id,
        "memory_id": receipt.record_id or candidate_id,
        "write_receipt_id": receipt.receipt_id,
        "group_id": namespace,
        "result": {
            "status": receipt.status,
            "record_id": receipt.record_id,
            "admission_reasons": list(receipt.admission_reasons),
            "warnings": list(receipt.warnings),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workspace", default=None)
    args = parser.parse_args(argv)
    try:
        candidate = _candidate_from_stdin(sys.stdin.buffer.read())
        result = ingest_candidate(candidate, dry_run=args.dry_run, workspace=args.workspace)
    except Exception as exc:
        json.dump({"status": "rejected", "error": str(exc)}, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
        return 1
    json.dump(result, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if str(result.get("status")) in {"accepted", "deduplicated"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
