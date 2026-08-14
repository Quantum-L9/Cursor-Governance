from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Mapping
from typing import Any

from .digests import digest_object, normalize_digest


def _required_string(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _contract_field(contract: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = contract.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise ValueError(f"contract is missing required field: {' or '.join(keys)}")


def bare(value: str) -> str:
    return normalize_digest(value).split(":", 1)[1]


def attempt_receipt(
    contract: Mapping[str, Any],
    *,
    candidate_sha: str | None,
    changed_files: list[str],
    validation_results: list[dict[str, Any]],
    produced_evidence: list[dict[str, Any]],
    residual_unknowns: list[str] | None = None,
    claimed_status: str = "completed",
) -> dict[str, Any]:
    return {
        "schema": "program-execution-controller.attempt-receipt.v2",
        "task_id": _contract_field(contract, "task_id", "id"),
        "contract_digest": bare(
            _contract_field(contract, "contract_digest", "rendered_contract_digest")
        ),
        "program_digest": bare(_contract_field(contract, "program_digest", "program_lock_digest")),
        "base_sha": _required_string("base_sha", contract.get("base_sha")),
        "candidate_sha": candidate_sha,
        "changed_files": sorted(set(changed_files)),
        "validation_results": validation_results,
        "produced_evidence": produced_evidence,
        "residual_unknowns": residual_unknowns or [],
        "claimed_status": claimed_status,
    }


def verification_receipt(
    contract: Mapping[str, Any],
    *,
    candidate_sha: str | None,
    declared_changed_files: list[str],
    observed_changed_files: list[str],
    validations: list[dict[str, Any]],
    gates: dict[str, str],
) -> dict[str, Any]:
    if gates and all(value == "PASS" for value in gates.values()):
        verdict = "PASSED_LOCAL"
    elif "STALE" in gates.values():
        verdict = "STALE"
    else:
        verdict = "FAILED"
    body = {
        "schema": "program-execution-controller.verification-receipt.v2",
        "verification_id": "VERIFY-" + uuid.uuid4().hex,
        "task_id": _contract_field(contract, "task_id", "id"),
        "contract_digest": bare(
            _contract_field(contract, "contract_digest", "rendered_contract_digest")
        ),
        "program_digest": bare(_contract_field(contract, "program_digest", "program_lock_digest")),
        "base_sha": _required_string("base_sha", contract.get("base_sha")),
        "candidate_sha": candidate_sha,
        "declared_changed_files": sorted(set(declared_changed_files)),
        "observed_changed_files": sorted(set(observed_changed_files)),
        "validations": validations,
        "gates": gates,
        "verdict": verdict,
        "evidence_id": "EVIDENCE-" + uuid.uuid4().hex,
        "verified_at": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
    }
    body["receipt_digest"] = digest_object(body).split(":", 1)[1]
    return body
