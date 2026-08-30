#!/usr/bin/env python3
"""Map a MemoryCandidate on stdin to Graphiti add_memory."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _candidate_from_stdin(raw: bytes) -> dict[str, Any]:
    parsed = json.loads(raw.decode("utf-8") if raw else "{}")
    if not isinstance(parsed, Mapping):
        raise ValueError("stdin must be a MemoryCandidate object")
    if str(parsed.get("kind") or "") != "MemoryCandidate":
        raise ValueError("stdin kind must be MemoryCandidate")
    return dict(parsed)


def ingest_candidate(candidate: Mapping[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    from ops.graphiti.episode_contract import FORBIDDEN_GROUPS, EpisodeContract
    from ops.graphiti.graphiti_memory_client import (
        call_tool,
        load_env,
        resolve_group_id,
        target_repo,
    )
    from ops.graphiti.hydration.identity import envelope_body, resolve_write_identity

    knowledge = candidate.get("knowledge")
    source = candidate.get("source")
    if not isinstance(knowledge, Mapping) or not isinstance(source, Mapping):
        raise ValueError("candidate.knowledge and candidate.source are required")
    statement = str(knowledge.get("statement") or "").strip()
    if not statement:
        raise ValueError("candidate.knowledge.statement is required")
    load_env()
    identity = resolve_write_identity(
        explicit_agent_id=str(source.get("agent_id") or "") or None,
        surface="cursor",
    )
    body = envelope_body(
        json.dumps(
            {
                "statement": statement,
                "candidate_id": candidate.get("candidate_id"),
                "unit_id": knowledge.get("unit_id"),
                "primary_class": knowledge.get("primary_class"),
                "campaign_id": source.get("campaign_id"),
                "action_id": source.get("action_id"),
                "packet_id": source.get("packet_id"),
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        agent_id=identity["agent_id"],
        user_id=identity["user_id"],
        kind="insight",
    )
    resolved = resolve_group_id(target_repo(argparse.Namespace(workspace=None)))
    group_id = resolved.get("group_id")
    if resolved.get("readonly") or not group_id or group_id in FORBIDDEN_GROUPS:
        raise RuntimeError(f"write blocked: {resolved.get('error') or resolved.get('warning')}")
    now = datetime.now(UTC)
    contract = EpisodeContract(
        name=f"sgd-{candidate.get('candidate_id')}",
        episode_body=body,
        source="json",
        source_description=f"sgd-memory-candidate agent={identity['agent_id']}",
        reference_time=now,
        group_id=group_id,
        kind="insight",
        agent_id=identity["agent_id"],
        user_id=identity["user_id"],
    )
    payload = contract.to_mcp_payload()
    if dry_run:
        return {
            "status": "accepted",
            "dry_run": True,
            "candidate_id": candidate.get("candidate_id"),
            "memory_id": str(candidate.get("candidate_id")),
            "write_receipt_id": str(candidate.get("candidate_id")),
            "group_id": group_id,
        }
    result = call_tool("add_memory", payload)
    memory_id = ""
    if isinstance(result, Mapping):
        memory_id = str(result.get("memory_id") or result.get("uuid") or result.get("id") or "")
    return {
        "status": "accepted",
        "candidate_id": candidate.get("candidate_id"),
        "memory_id": memory_id or str(candidate.get("candidate_id")),
        "write_receipt_id": memory_id or str(candidate.get("candidate_id")),
        "group_id": group_id,
        "result": result if isinstance(result, Mapping) else {"raw": result},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        candidate = _candidate_from_stdin(sys.stdin.buffer.read())
        result = ingest_candidate(candidate, dry_run=args.dry_run)
    except Exception as exc:
        json.dump({"status": "rejected", "error": str(exc)}, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
        return 1
    json.dump(result, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if str(result.get("status")) in {"accepted", "deduplicated"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
