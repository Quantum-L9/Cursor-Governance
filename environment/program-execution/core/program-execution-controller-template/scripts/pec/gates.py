"""Controller-derived convergence gate evaluation (PEC-P1-005).

facts -> Controller -> verdict. The caller supplies evidence references; this
module derives PASS / FAIL / UNKNOWN / NOT_APPLICABLE_WITH_REASON from the gate's
frozen definition and the typed evidence the runtime holds. Nothing here reads
a result the caller proposed. A gate type the evaluator does not understand is
UNKNOWN, never PASS.

Deterministic: the same definition, evidence set, lock and clock always yield
the same verdict and the same reason codes.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .common import ControllerError, parse_time

GATE_EVALUATOR_VERSION = "pec.gate-evaluator.v1"

#: Gate classes the Blueprint schema admits. Anything else is an unknown type.
SUPPORTED_GATE_CLASSES = frozenset(
    {
        "authority",
        "contract",
        "execution",
        "validation",
        "migration",
        "release",
        "operations",
        "security",
        "phase0",
    }
)
#: Gate classes that close over executed work. Their PASS needs the
#: Controller's own verification of an in-scope task, never catalog evidence.
EXECUTION_GATE_CLASSES = frozenset({"execution", "validation"})
CONTROLLER_VERIFICATION_METHOD = "independent_controller_verification"

# Reason codes (observability contract, remediation §22).
GATE_EVIDENCE_MISSING = "GATE_EVIDENCE_MISSING"
GATE_EVIDENCE_STALE = "GATE_EVIDENCE_STALE"
GATE_EVIDENCE_CONTRADICTS = "GATE_EVIDENCE_CONTRADICTS"
GATE_EVIDENCE_OUT_OF_SCOPE = "GATE_EVIDENCE_OUT_OF_SCOPE"
GATE_VERIFICATION_REQUIRED = "GATE_VERIFICATION_REQUIRED"
GATE_UNKNOWN_TYPE = "GATE_UNKNOWN_TYPE"
GATE_DEFINITION_INACTIVE = "GATE_DEFINITION_INACTIVE"
GATE_WAIVED = "GATE_WAIVED"
GATE_EXPECTATION_MISMATCH = "GATE_EXPECTATION_MISMATCH"

#: Operator-readable explanation per reason code, used in refusals.
REASON_TEXT = {
    GATE_EVIDENCE_MISSING: "PASS requires its declared evidence; evidence is missing",
    GATE_EVIDENCE_STALE: "evidence is expired, invalidated, planned or no longer current",
    GATE_EVIDENCE_CONTRADICTS: "explicit negative evidence for a task in the gate's scope",
    GATE_EVIDENCE_OUT_OF_SCOPE: (
        "PASS requires evidence supporting a task in the gate's scope; none does"
    ),
    GATE_VERIFICATION_REQUIRED: (
        "PASS requires Controller verification evidence for a task in its scope; "
        "planning or catalog evidence cannot close an execution gate"
    ),
    GATE_UNKNOWN_TYPE: "the gate class has no deterministic evaluator; UNKNOWN, never PASS",
    GATE_DEFINITION_INACTIVE: "the gate definition is superseded or retired",
    GATE_WAIVED: "an allowed, active, in-scope waiver applies",
}


@dataclass
class GateVerdict:
    result: str
    reason_codes: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    evidence_used: list[str] = field(default_factory=list)
    evaluator: str = GATE_EVALUATOR_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "result": self.result,
            "reason_codes": sorted(set(self.reason_codes)),
            "unresolved": sorted(set(self.unresolved)),
            "evidence_used": sorted(set(self.evidence_used)),
            "evaluator": self.evaluator,
        }


def _evidence_state(db: Any, evidence_id: str, now: dt.datetime) -> tuple[str, dict[str, Any]]:
    """`(state, item)` where state is missing / invalid / negative / valid."""
    item = db.evidence(evidence_id)
    if item is None:
        return "missing", {}
    status = str(item.get("status") or "")
    if status in {"invalidated", "expired", "UNKNOWN", "planned"}:
        return "invalid", item
    expires_at = item.get("expires_at")
    if expires_at and parse_time(str(expires_at)) <= now:
        return "invalid", item
    if str(item.get("result") or "") in {"FAIL", "BLOCKED", "UNKNOWN"}:
        return "negative", item
    return "valid", item


def _verification_is_current(db: Any, item: dict[str, Any], program_digest: str | None) -> bool:
    """A Controller verification counts only while it describes the current state.

    The receipt it points at must exist, still carry the digest the evidence
    recorded, and have been produced under the current Program Lock.
    """
    source = Path(str(item.get("source") or ""))
    receipt: dict[str, Any] | None = None
    lookup = getattr(db, "receipt_by_artifact", None)
    if callable(lookup):
        record = lookup(str(source))
        if record is not None:
            receipt = dict(record["payload"])
    if receipt is None:
        # No canonical record: the file alone is not evidence (R8).
        return False
    if str(receipt.get("receipt_digest") or "") != str(item.get("digest") or ""):
        return False
    if program_digest and str(receipt.get("program_digest") or "") != str(program_digest):
        return False
    return True


def _waiver_verdict(db: Any, gate: dict[str, Any], waiver_id: str, now: dt.datetime) -> GateVerdict:
    definition = gate.get("definition") or {}
    if not definition.get("waiver_allowed"):
        raise ControllerError(
            f"gate {gate['id']} does not allow waivers", error_code="GATE_WAIVER_NOT_ALLOWED"
        )
    waiver = db.waiver(waiver_id)
    if (
        waiver is None
        or waiver.get("status") != "active"
        or gate["id"] not in (waiver.get("scope") or [])
    ):
        raise ControllerError(
            "waiver is missing, inactive, or out of scope", error_code="GATE_WAIVER_INVALID"
        )
    if parse_time(str(waiver["expires_at"])) <= now:
        raise ControllerError("waiver is expired", error_code="GATE_WAIVER_INVALID")
    for evidence_id in waiver.get("evidence_ids") or []:
        state, _ = _evidence_state(db, str(evidence_id), now)
        if state != "valid":
            raise ControllerError("waiver evidence is invalid", error_code="GATE_WAIVER_INVALID")
    return GateVerdict(
        result="NOT_APPLICABLE_WITH_REASON",
        reason_codes=[GATE_WAIVED],
        evidence_used=[str(item) for item in waiver.get("evidence_ids") or []],
    )


def derive_gate_result(
    db: Any,
    gate: dict[str, Any],
    evidence_ids: list[str],
    *,
    waiver_id: str | None = None,
    now: dt.datetime | None = None,
) -> GateVerdict:
    """Derive the gate's verdict from its definition and the runtime's evidence.

    Order of evaluation is fixed so the verdict is reproducible:

    1. waiver -> NOT_APPLICABLE_WITH_REASON (or a refused input);
    2. unknown class / inactive definition -> UNKNOWN;
    3. any supplied evidence missing or stale -> UNKNOWN;
    4. any supplied evidence that is a negative result FOR an in-scope task
       -> FAIL (explicit negative evidence, where the gate defines failure);
    5. declared required evidence absent -> UNKNOWN;
    6. no supplied evidence supports the gate's scope -> UNKNOWN;
    7. execution/validation class without a current Controller verification
       PASS for an in-scope task -> UNKNOWN;
    8. otherwise PASS.
    """
    now = now or dt.datetime.now(dt.UTC)
    if waiver_id is not None:
        return _waiver_verdict(db, gate, waiver_id, now)
    definition = gate.get("definition") or {}
    gate_class = str(definition.get("class") or "")
    if gate_class not in SUPPORTED_GATE_CLASSES:
        return GateVerdict(
            result="UNKNOWN",
            reason_codes=[GATE_UNKNOWN_TYPE],
            unresolved=[f"class:{gate_class or 'undeclared'}"],
        )
    status = str(definition.get("definition_status") or "active")
    if status not in {"active", "draft"}:
        return GateVerdict(
            result="UNKNOWN",
            reason_codes=[GATE_DEFINITION_INACTIVE],
            unresolved=[f"definition_status:{status}"],
        )
    scope_tasks = {str(item) for item in (definition.get("scope") or {}).get("task_ids") or []}
    program_digest = db.get_meta("program_digest")
    supplied = list(dict.fromkeys(str(item) for item in evidence_ids))
    verdict = GateVerdict(result="PASS", evidence_used=supplied)

    valid_items: dict[str, dict[str, Any]] = {}
    for evidence_id in supplied:
        state, item = _evidence_state(db, evidence_id, now)
        if state == "missing":
            verdict.reason_codes.append(GATE_EVIDENCE_MISSING)
            verdict.unresolved.append(f"missing:{evidence_id}")
        elif state == "invalid":
            verdict.reason_codes.append(GATE_EVIDENCE_STALE)
            verdict.unresolved.append(f"invalid:{evidence_id}")
        elif state == "negative":
            supports = {str(x) for x in item.get("supports") or []}
            if not scope_tasks or supports & scope_tasks:
                verdict.reason_codes.append(GATE_EVIDENCE_CONTRADICTS)
                verdict.unresolved.append(f"negative:{evidence_id}")
            else:
                verdict.reason_codes.append(GATE_EVIDENCE_OUT_OF_SCOPE)
                verdict.unresolved.append(f"negative_out_of_scope:{evidence_id}")
        else:
            valid_items[evidence_id] = item
    if GATE_EVIDENCE_CONTRADICTS in verdict.reason_codes:
        verdict.result = "FAIL"
        return verdict
    if GATE_EVIDENCE_MISSING in verdict.reason_codes or GATE_EVIDENCE_STALE in verdict.reason_codes:
        verdict.result = "UNKNOWN"
        return verdict

    required = [str(item) for item in definition.get("required_evidence_ids") or []]
    missing_required = sorted(set(required) - set(valid_items))
    if missing_required:
        verdict.result = "UNKNOWN"
        verdict.reason_codes.append(GATE_EVIDENCE_MISSING)
        verdict.unresolved.extend(f"required:{item}" for item in missing_required)
        return verdict

    if not valid_items:
        verdict.result = "UNKNOWN"
        verdict.reason_codes.append(GATE_EVIDENCE_MISSING)
        verdict.unresolved.append("no_evidence")
        return verdict

    if scope_tasks:
        in_scope = {
            evidence_id
            for evidence_id, item in valid_items.items()
            if {str(x) for x in item.get("supports") or []} & scope_tasks
        }
        if not in_scope:
            verdict.result = "UNKNOWN"
            verdict.reason_codes.append(GATE_EVIDENCE_OUT_OF_SCOPE)
            verdict.unresolved.append("scope:" + ",".join(sorted(scope_tasks)))
            return verdict
        if gate_class in EXECUTION_GATE_CLASSES:
            # An execution or validation gate closes over work that ran. Only
            # the Controller's own, still-current verification of an in-scope
            # task can close it; catalog evidence cannot.
            verifications = [
                evidence_id
                for evidence_id in in_scope
                if str(valid_items[evidence_id].get("method") or "")
                == CONTROLLER_VERIFICATION_METHOD
                and str(valid_items[evidence_id].get("result") or "") == "PASS"
            ]
            if not verifications:
                verdict.result = "UNKNOWN"
                verdict.reason_codes.append(GATE_VERIFICATION_REQUIRED)
                verdict.unresolved.append("controller_verification")
                return verdict
            current = [
                evidence_id
                for evidence_id in verifications
                if _verification_is_current(db, valid_items[evidence_id], program_digest)
            ]
            if not current:
                verdict.result = "UNKNOWN"
                verdict.reason_codes.append(GATE_EVIDENCE_STALE)
                verdict.unresolved.extend(f"verification_stale:{item}" for item in verifications)
                return verdict
    return verdict
