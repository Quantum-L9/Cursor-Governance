"""Canonical Replan semantic revision projection (program-execution.replan.v1).

One canonical semantic revision — the Replan contract plus revision schema plus
the activated Replan Revision identity — is projected to every registered
execution peer through the existing peer-runtime-bindings topology.

Rules enforced here (see core/shared/REPLAN_CONTRACT.yaml):

- canonical source only; peer-local semantic overrides are prohibited,
- unsupported peers fail closed explicitly,
- partial semantic revision activation is prohibited: the projection is not
  ACTIVE unless every applicable peer is accounted for under the same
  semantic revision digest.

Projection accounting is durable runtime state and lives outside git
(workspace ``runtime/projection/``).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .bindings import load_peer_bindings
from .digests import digest_object, verify_embedded_digest

SEMANTIC_REVISION_SCHEMA = "program-execution.replan.semantic-revision.v1"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_semantic_revision(
    contract_path: Path,
    revision_schema_path: Path,
    *,
    replan_revision_id: str,
    plan_revision: str,
    activated_at: str,
    actor: str,
) -> dict[str, Any]:
    """Build the digest-bound canonical semantic revision identity."""
    contract_path = Path(contract_path).resolve()
    revision_schema_path = Path(revision_schema_path).resolve()
    payload: dict[str, Any] = {
        "schema": SEMANTIC_REVISION_SCHEMA,
        "contract_path": str(contract_path),
        "contract_digest": _sha256_file(contract_path),
        "revision_schema_path": str(revision_schema_path),
        "revision_schema_digest": _sha256_file(revision_schema_path),
        "replan_revision_id": replan_revision_id,
        "plan_revision": plan_revision,
        "activated_at": activated_at,
        "created_by": actor,
    }
    payload["semantic_revision_digest"] = digest_object(payload)
    return payload


def applicable_peers(bindings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Peers that participate in shared semantic revision accounting.

    A peer entry participates when it declares execution bindings. Peers with
    no bindings are represented as explicitly unsupported and fail closed.
    """
    result: dict[str, dict[str, Any]] = {}
    for peer_id, spec in (bindings.get("peers") or {}).items():
        if not isinstance(spec, dict):
            continue
        execution = spec.get("execution") or {}
        binding_list = execution.get("bindings") or []
        supported = bool(binding_list) and isinstance(binding_list, list)
        result[str(peer_id)] = {
            "agent_ref": str(spec.get("agent_ref", peer_id)),
            "bindings": list(binding_list) if supported else [],
            "capability": "supported" if supported else "unsupported",
            "fail_closed": not supported,
        }
    return result


def project_to_peers(
    repository_root: str | Path,
    workspace: str | Path,
    *,
    semantic_revision: dict[str, Any],
    actor: str,
) -> dict[str, Any]:
    """Project one semantic revision to every registered peer.

    Writes digest-bound accounting under ``<workspace>/runtime/projection/``.
    Returns the projection status: ACTIVE only when every applicable peer is
    accounted for under the same semantic revision digest.
    """
    repository_root = Path(repository_root).resolve()
    workspace = Path(workspace).resolve()
    bindings = load_peer_bindings(repository_root)
    peers = applicable_peers(bindings)
    if not peers:
        raise ValueError("no registered execution peers to project to")
    revision_digest = semantic_revision["semantic_revision_digest"]
    records = []
    for peer_id in sorted(peers):
        spec = peers[peer_id]
        record = {
            "peer_id": peer_id,
            "agent_ref": spec["agent_ref"],
            "surfaces": [binding.get("surface") for binding in spec["bindings"]],
            "provider_refs": [binding.get("provider_ref") for binding in spec["bindings"]],
            "semantic_revision_digest": revision_digest,
            "capability": spec["capability"],
            "fail_closed": spec["fail_closed"],
        }
        record["record_digest"] = digest_object(record)
        records.append(record)
    unaccounted = [record["peer_id"] for record in records if record["capability"] != "supported"]
    status = "BLOCKED" if unaccounted else "ACTIVE"
    target = workspace / "runtime/projection"
    target.mkdir(parents=True, exist_ok=True)
    semantic_revision_file = target / "replan-semantic-revision.json"
    _write_atomic(semantic_revision_file, _canonical_json(semantic_revision) + "\n")
    accounting = {
        "schema": "program-execution.replan.peer-accounting.v1",
        "semantic_revision_digest": revision_digest,
        "status": status,
        "projected_by": actor,
        "records": records,
    }
    accounting["accounting_digest"] = digest_object(accounting)
    accounting_file = target / "peer-accounting.json"
    _write_atomic(accounting_file, _canonical_json(accounting) + "\n")
    return accounting


def verify_projection(repository_root: str | Path, workspace: str | Path) -> dict[str, Any]:
    """Re-validate stored projection accounting against the current registry.

    Partial activation detection: a stored ACTIVE accounting becomes BLOCKED if
    the registry no longer accounts for every peer under the same digest.
    """
    import json as _json

    repository_root = Path(repository_root).resolve()
    workspace = Path(workspace).resolve()
    bindings = load_peer_bindings(repository_root)
    peers = applicable_peers(bindings)
    accounting_path = workspace / "runtime/projection/peer-accounting.json"
    if not accounting_path.is_file():
        return {"status": "BLOCKED", "reason": "no projection accounting recorded"}
    accounting = _json.loads(accounting_path.read_text(encoding="utf-8"))
    if not isinstance(accounting, dict) or not verify_embedded_digest(
        accounting, "accounting_digest"
    ):
        return {"status": "BLOCKED", "reason": "projection accounting digest does not verify"}
    revision_digest = accounting.get("semantic_revision_digest")
    recorded = {record["peer_id"]: record for record in accounting.get("records") or []}
    errors = []
    for peer_id in sorted(peers):
        record = recorded.get(peer_id)
        if record is None:
            errors.append(f"missing peer accounting: {peer_id}")
            continue
        if record["semantic_revision_digest"] != revision_digest:
            errors.append(f"peer digest mismatch: {peer_id}")
        if record["capability"] == "unsupported":
            errors.append(f"unsupported peer must fail closed: {peer_id}")
    if errors:
        return {"status": "BLOCKED", "reason": "; ".join(sorted(errors))}
    # A recorded status is the only evidence of activation; absence is BLOCKED.
    return {"status": str(accounting.get("status") or "BLOCKED"), "reason": ""}


def _write_atomic(path: Path, text: str) -> None:
    """Durable runtime state: a reader sees the old file or the new one, never a blend."""
    import os
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    handle, staged = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staged, path)
    finally:
        if os.path.exists(staged):
            os.unlink(staged)


def _canonical_json(value: Any) -> str:
    import json as _json

    return _json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
