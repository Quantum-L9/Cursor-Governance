from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Mapping
from typing import Any

from .digests import digest_object, normalize_digest


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
        "task_id": str(contract.get("task_id") or contract.get("id")),
        "contract_digest": bare(
            str(contract.get("contract_digest") or contract.get("rendered_contract_digest"))
        ),
        "program_digest": bare(
            str(contract.get("program_digest") or contract.get("program_lock_digest"))
        ),
        "base_sha": str(contract.get("base_sha") or "0" * 40),
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
    verdict = "PASSED_LOCAL" if all(value == "PASS" for value in gates.values()) else "FAILED"
    body = {
        "schema": "program-execution-controller.verification-receipt.v2",
        "verification_id": "VERIFY-" + uuid.uuid4().hex,
        "task_id": str(contract.get("task_id") or contract.get("id")),
        "contract_digest": bare(
            str(contract.get("contract_digest") or contract.get("rendered_contract_digest"))
        ),
        "program_digest": bare(
            str(contract.get("program_digest") or contract.get("program_lock_digest"))
        ),
        "base_sha": str(contract.get("base_sha") or "0" * 40),
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
