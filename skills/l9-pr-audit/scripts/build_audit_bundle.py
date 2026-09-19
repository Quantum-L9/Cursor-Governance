#!/usr/bin/env python3
"""Validate canonical l9-pr-audit JSON and build a revision-bound remediation ZIP.

Structural truth lives in schemas/audit-output.schema.json. This script owns only
cross-field semantic invariants and deterministic projections.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import zipfile
from collections import defaultdict, deque
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as exc:  # pragma: no cover - fail closed in unsupported runtimes
    raise SystemExit(
        "jsonschema>=4 is required to validate the canonical audit contract; "
        "do not bypass schema validation"
    ) from exc

SCHEMA_VERSION = "l9.pr-audit.v2.0"
HANDOFF_VERSION = "l9.pr-audit.remediation-handoff.v2.0"
MANIFEST_VERSION = "l9.pr-audit.bundle-manifest.v2.0"
BUILDER_VERSION = "2.0.0"
SHA_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")
EXECUTION_EVIDENCE = {"TEST", "CI", "RUNTIME", "MEASUREMENT"}
READY_STATES = {"READY", "READY_WITH_NON_BLOCKING_NOTES"}
ANTI_BYPASS_KINDS = {
    "TEST_REMOVAL_OR_DISABLEMENT",
    "SKIP_IGNORE_GROWTH",
    "GATE_WEAKENING",
    "EXCLUSION_SUPPRESSION_GROWTH",
    "GENERATED_OR_OWNER_BYPASS",
    "UNEXPLAINED_DEPENDENCY_MOVEMENT",
}
MUTATION_OWNER = "CODEBASE"
AUDIT_DOMAINS = {
    "INTENT_SCOPE",
    "COMMUNICATION_CONTRACTS",
    "ROUTING_INTEGRATION",
    "OWNERSHIP_AUTHORITY",
    "STRUCTURE_SOURCE_OF_TRUTH",
    "SCHEMA_CONFIGURATION",
    "SECURITY",
    "RELIABILITY_OBSERVABILITY",
    "TESTING_VALIDATION",
    "LEVERAGE_SIMPLICITY",
    "CROSS_PR",
    "CHANGE_DISCIPLINE",
}
CHANGE_LEDGER_SCHEMA = "l9.pr-audit.change-ledger.v1.4"
CHANGE_LEDGER_GENERATOR_VERSION = "1.4.0"
CHANGE_LEDGER_SET_SCHEMA = "l9.pr-audit.change-ledger-set.v1.0"

# High-confidence packaging tripwire, not a substitute for repository secret scanning.
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"sk_live_[A-Za-z0-9]{16,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(
        r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|secret)\s*[:=]\s*"
        r"['\"]?[A-Za-z0-9+/_.-]{12,}"
    ),
]


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("audit JSON root must be an object")
    return data


def schema_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "schemas"


def schema_path() -> Path:
    return schema_dir() / "audit-output.schema.json"


def handoff_schema_path() -> Path:
    return schema_dir() / "remediation-handoff.schema.json"


def manifest_schema_path() -> Path:
    return schema_dir() / "bundle-manifest.schema.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_strings(child)


def contains_secret_material(value: Any) -> str | None:
    for text in iter_strings(value):
        # Redaction markers protect only the replaced token, not the entire string.
        # Continue scanning surrounding text so "REDACTED ... api_key=<live>" cannot bypass the tripwire.
        scrubbed = re.sub(r"(?i)\bREDACTED\b", "<redacted>", text)
        for pattern in SECRET_PATTERNS:
            if pattern.search(scrubbed):
                return pattern.pattern
    return None


def validate_against_schema(data: dict[str, Any], path: Path, label: str) -> list[str]:
    schema = load_json(path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors: list[str] = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        errors.append(f"{label} schema {location}: {error.message}")
    return errors


def schema_errors(audit: dict[str, Any]) -> list[str]:
    return validate_against_schema(audit, schema_path(), "audit")


def is_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA_RE.fullmatch(value))


def safe_repo_path(value: str) -> bool:
    if not value or value.startswith(("/", "~")) or "\\" in value:
        return False
    path = PurePosixPath(value)
    return ".." not in path.parts and not value.startswith("./")


def evidence_map(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["evidence_id"]: item for item in audit["shared_evidence_index"]}


def finding_map(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["finding_id"]: item for item in audit["findings"]}


def surface_map(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["finding_id"]: item for item in audit["remediation_surface_index"]}


def graph_map(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["finding_id"]: item for item in audit["finding_dependency_graph"]}


def pr_map(audit: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {item["pr_number"]: item for item in audit["pr_bindings"]}


def authority_map(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["authority_id"]: item for item in audit["authority_resolution"]["sources"]}


def confirmed_evidence(eids: Iterable[str], emap: dict[str, dict[str, Any]]) -> bool:
    return any(emap.get(eid, {}).get("epistemic_state") == "CONFIRMED" for eid in eids)


def evidence_discriminates(
    eids: Iterable[str],
    emap: dict[str, dict[str, Any]],
    property_name: str,
    *,
    confirmed_only: bool = True,
) -> bool:
    for eid in eids:
        item = emap.get(eid, {})
        if confirmed_only and item.get("epistemic_state") != "CONFIRMED":
            continue
        if property_name in item.get("properties_discriminated", []):
            return True
    return False


def builder_path() -> Path:
    return Path(__file__).resolve()


def load_change_ledger_paths(paths: Iterable[Path]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for path in paths:
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"change ledger root must be object: {path}")
        pr = data.get("pr_number")
        if not isinstance(pr, int) or pr < 1:
            raise ValueError(f"change ledger pr_number invalid: {path}")
        if pr in out:
            raise ValueError(f"duplicate change ledger for PR {pr}")
        canonical = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")
        out[pr] = {"ledger": data, "sha256": sha256_bytes(canonical)}
    return out


def change_ledger_set(change_ledgers: dict[int, dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": CHANGE_LEDGER_SET_SCHEMA,
        "ledgers": [
            {"pr_number": pr, "source_sha256": item["sha256"], "ledger": item["ledger"]}
            for pr, item in sorted(change_ledgers.items())
        ],
    }


def load_change_ledger_set(data: dict[str, Any]) -> dict[int, dict[str, Any]]:
    if data.get("schema_version") != CHANGE_LEDGER_SET_SCHEMA:
        raise ValueError("change-ledger set schema_version mismatch")
    out: dict[int, dict[str, Any]] = {}
    for item in data.get("ledgers", []):
        if not isinstance(item, dict):
            raise ValueError("change-ledger set entry must be object")
        pr = item.get("pr_number")
        ledger = item.get("ledger")
        digest = item.get("source_sha256")
        if (
            not isinstance(pr, int)
            or pr < 1
            or not isinstance(ledger, dict)
            or not isinstance(digest, str)
        ):
            raise ValueError("invalid change-ledger set entry")
        if pr in out:
            raise ValueError(f"duplicate change ledger for PR {pr}")
        canonical = (json.dumps(ledger, indent=2, sort_keys=True) + "\n").encode("utf-8")
        out[pr] = {"ledger": ledger, "sha256": digest, "canonical_sha256": sha256_bytes(canonical)}
    return out


def red_team_semantic_errors(
    audit: dict[str, Any],
    emap: dict[str, dict[str, Any]],
    fmap: dict[str, dict[str, Any]],
    amap: dict[str, dict[str, Any]],
    change_ledgers: dict[int, dict[str, Any]] | None,
) -> list[str]:
    errors: list[str] = []
    symbols = audit["changed_symbol_ledger"]
    claims = audit["claim_validation_matrix"]
    falsifications = audit["falsification_ledger"]
    symbol_map = {item["symbol_id"]: item for item in symbols}
    claim_map = {item["claim_id"]: item for item in claims}
    fals_map = {item["falsification_id"]: item for item in falsifications}
    if len(symbol_map) != len(symbols):
        errors.append("changed_symbol_ledger contains duplicate symbol_id values")
    if len(claim_map) != len(claims):
        errors.append("claim_validation_matrix contains duplicate claim_id values")
    if len(fals_map) != len(falsifications):
        errors.append("falsification_ledger contains duplicate falsification_id values")

    bindings = audit["deterministic_census_binding"]["ledger_bindings"]
    binding_map = {item["pr_number"]: item for item in bindings}
    if len(binding_map) != len(bindings):
        errors.append("deterministic_census_binding contains duplicate PR bindings")
    expected_prs = {item["pr_number"] for item in audit["pr_bindings"]}
    if set(binding_map) != expected_prs:
        errors.append("deterministic_census_binding must cover every audited PR exactly once")
    for num, binding in binding_map.items():
        if (
            num in pr_map(audit)
            and binding["head_sha"].lower() != pr_map(audit)[num]["head_sha"].lower()
        ):
            errors.append(
                f"PR {num} deterministic census binding head_sha does not match canonical PR head"
            )

    valid_objectives = {
        item["objective_id"]
        for item in audit["intent_contract"]["objectives"]
        if item["status"] == "ACTIVE"
    }
    for symbol in symbols:
        for eid in symbol["evidence_ids"]:
            if eid not in emap:
                errors.append(
                    f"changed symbol {symbol['symbol_id']} references unknown evidence {eid}"
                )
        for cid in symbol["claim_ids"]:
            if cid not in claim_map:
                errors.append(
                    f"changed symbol {symbol['symbol_id']} references unknown claim {cid}"
                )
        for fid in symbol["finding_ids"]:
            if fid not in fmap:
                errors.append(
                    f"changed symbol {symbol['symbol_id']} references unknown finding {fid}"
                )
        unknown_obj = set(symbol["objective_ids"]) - valid_objectives
        if unknown_obj:
            errors.append(
                f"changed symbol {symbol['symbol_id']} references unknown/inactive objectives {sorted(unknown_obj)}"
            )
        if symbol["scope_disposition"] == "SCOPE_EXTENSION" and not symbol["finding_ids"]:
            errors.append(
                f"changed symbol {symbol['symbol_id']} SCOPE_EXTENSION requires finding_ids"
            )
        if symbol["source"] == "MACHINE" and symbol["detection_method"] == "AUDITOR_SEMANTIC":
            errors.append(
                f"changed symbol {symbol['symbol_id']} MACHINE source cannot use AUDITOR_SEMANTIC detection"
            )

    for claim in claims:
        for aid in claim["authority_ids"]:
            if aid not in amap:
                errors.append(f"claim {claim['claim_id']} references unknown authority {aid}")
        for eid in claim["evidence_ids"] + claim["validation_evidence_ids"]:
            if eid not in emap:
                errors.append(f"claim {claim['claim_id']} references unknown evidence {eid}")
        for fid in claim["finding_ids"]:
            if fid not in fmap:
                errors.append(f"claim {claim['claim_id']} references unknown finding {fid}")
        for falid in claim["falsification_ids"]:
            if falid not in fals_map:
                errors.append(f"claim {claim['claim_id']} references unknown falsification {falid}")
            elif fals_map[falid]["claim_id"] != claim["claim_id"]:
                errors.append(
                    f"claim {claim['claim_id']} references falsification {falid} owned by another claim"
                )
        if claim["materiality"] == "MATERIAL":
            if not evidence_discriminates(
                claim["evidence_ids"], emap, f"claim:{claim['claim_id']}"
            ):
                errors.append(f"material claim {claim['claim_id']} lacks claim-specific evidence")
            if not claim["falsification_ids"]:
                errors.append(
                    f"material claim {claim['claim_id']} requires at least one falsification probe"
                )
            results = [
                fals_map[fid]["result"] for fid in claim["falsification_ids"] if fid in fals_map
            ]
            if claim["status"] == "SUPPORTED" and (
                not results or any(result != "SURVIVED" for result in results)
            ):
                errors.append(
                    f"material SUPPORTED claim {claim['claim_id']} requires all applicable falsification probes to SURVIVE"
                )
            if claim["status"] == "REFUTED" and "FALSIFIED" not in results:
                errors.append(
                    f"material REFUTED claim {claim['claim_id']} requires a FALSIFIED probe"
                )
            if (
                claim["status"] == "UNKNOWN"
                and "FALSIFIED" not in results
                and "INCONCLUSIVE" not in results
            ):
                errors.append(
                    f"material UNKNOWN claim {claim['claim_id']} requires an INCONCLUSIVE probe"
                )
            if claim["status"] == "NOT_APPLICABLE" and any(
                result != "NOT_APPLICABLE" for result in results
            ):
                errors.append(
                    f"material NOT_APPLICABLE claim {claim['claim_id']} requires NOT_APPLICABLE probes"
                )
        if claim["status"] == "SUPPORTED":
            if not confirmed_evidence(claim["evidence_ids"], emap):
                errors.append(f"SUPPORTED claim {claim['claim_id']} requires CONFIRMED evidence")
            for prop in claim["validation_properties"]:
                if not evidence_discriminates(claim["validation_evidence_ids"], emap, prop):
                    errors.append(
                        f"SUPPORTED claim {claim['claim_id']} lacks validation evidence discriminating {prop}"
                    )
            if claim["materiality"] == "MATERIAL":
                survived = [
                    fals_map[fid]
                    for fid in claim["falsification_ids"]
                    if fid in fals_map and fals_map[fid]["result"] == "SURVIVED"
                ]
                if not survived:
                    errors.append(
                        f"material SUPPORTED claim {claim['claim_id']} requires a SURVIVED falsification probe"
                    )
        if (
            claim["status"] == "REFUTED"
            and not claim["finding_ids"]
            and claim["claim_kind"] not in {"AUDIT_DOMAIN", "READINESS", "CONVERGENCE"}
        ):
            errors.append(f"REFUTED claim {claim['claim_id']} requires finding_ids")

    for fal in falsifications:
        claim = claim_map.get(fal["claim_id"])
        if claim is None:
            errors.append(
                f"falsification {fal['falsification_id']} references unknown claim {fal['claim_id']}"
            )
            continue
        for eid in fal["evidence_ids"]:
            if eid not in emap:
                errors.append(
                    f"falsification {fal['falsification_id']} references unknown evidence {eid}"
                )
        for fid in fal["finding_ids"]:
            if fid not in fmap:
                errors.append(
                    f"falsification {fal['falsification_id']} references unknown finding {fid}"
                )
        if fal["result"] in {"SURVIVED", "FALSIFIED"}:
            prop = f"falsification:{fal['claim_id']}"
            if not evidence_discriminates(fal["evidence_ids"], emap, prop):
                errors.append(
                    f"falsification {fal['falsification_id']} lacks claim-specific discriminating evidence {prop}"
                )
        if fal["result"] == "FALSIFIED" and claim["status"] == "SUPPORTED":
            errors.append(
                f"claim {claim['claim_id']} cannot be SUPPORTED after falsification {fal['falsification_id']} FALSIFIED"
            )
        if (
            fal["result"] == "INCONCLUSIVE"
            and claim["materiality"] == "MATERIAL"
            and claim["status"] == "SUPPORTED"
        ):
            errors.append(
                f"material claim {claim['claim_id']} cannot be SUPPORTED with INCONCLUSIVE falsification"
            )
        if fal["judgment_required"] and fal["execution_kind"] not in {"LLM_JUDGMENT", "HYBRID"}:
            errors.append(
                f"falsification {fal['falsification_id']} judgment_required requires LLM_JUDGMENT or HYBRID"
            )
        if fal["execution_kind"] in {"LLM_JUDGMENT", "HYBRID"} and not fal["judgment_required"]:
            errors.append(
                f"falsification {fal['falsification_id']} {fal['execution_kind']} requires judgment_required=true"
            )
        if fal["execution_kind"] in {"STATIC", "COMMAND", "CHECK"} and fal["judgment_required"]:
            errors.append(
                f"falsification {fal['falsification_id']} deterministic execution kind cannot require LLM judgment"
            )
        if fal["judgment_required"] and not fal["judgment_rationale"]:
            errors.append(
                f"falsification {fal['falsification_id']} judgment_required requires judgment_rationale"
            )

    # Canonical claim outcomes mirror existing audit truth instead of creating another verdict store.
    objective_status = {
        item["objective_id"]: item["status"]
        for item in audit["change_discipline"]["objective_closure"]
    }
    domain_status = {
        item["domain"]: item["status"] for item in audit["audit_coverage"]["domain_assessments"]
    }
    pr_verdicts = {item["pr_number"]: item["merge_readiness"] for item in audit["per_pr_verdicts"]}
    for claim in claims:
        kind = claim["claim_kind"]
        if kind == "OBJECTIVE" and claim["subject"] in objective_status:
            expected = {
                "SATISFIED": "SUPPORTED",
                "UNPROVEN": "UNKNOWN",
                "NOT_IMPLEMENTED": "REFUTED",
                "CONFLICTED": "REFUTED",
            }[objective_status[claim["subject"]]]
            if claim["status"] != expected:
                errors.append(
                    f"objective claim {claim['claim_id']} status {claim['status']} must mirror {expected}"
                )
        elif kind == "AUDIT_DOMAIN" and claim["subject"] in domain_status:
            expected = {
                "PASS": "SUPPORTED",
                "FAIL": "REFUTED",
                "NOT_APPLICABLE": "NOT_APPLICABLE",
                "UNKNOWN": "UNKNOWN",
            }[domain_status[claim["subject"]]]
            if claim["status"] != expected:
                errors.append(
                    f"domain claim {claim['claim_id']} status {claim['status']} must mirror {expected}"
                )
        elif kind == "READINESS" and len(claim["pr_numbers"]) == 1:
            num = claim["pr_numbers"][0]
            if num in pr_verdicts:
                expected = (
                    "SUPPORTED"
                    if pr_verdicts[num] in READY_STATES
                    else "REFUTED"
                    if pr_verdicts[num] == "NOT_READY"
                    else "UNKNOWN"
                )
                if claim["status"] != expected:
                    errors.append(
                        f"readiness claim {claim['claim_id']} status {claim['status']} must mirror {expected}"
                    )
        elif kind == "CONVERGENCE":
            state = audit["executive_verdict"]["convergence_status"]
            expected = (
                "SUPPORTED"
                if state == "CONVERGED"
                else "REFUTED"
                if state == "NOT_CONVERGED"
                else "UNKNOWN"
            )
            if claim["status"] != expected:
                errors.append(
                    f"convergence claim {claim['claim_id']} status {claim['status']} must mirror {expected}"
                )

    # Every machine symbol has a matching CHANGED_SYMBOL claim and every changed-symbol claim references its machine symbol through the seed assertion.
    symbol_claims = [c for c in claims if c["claim_kind"] == "CHANGED_SYMBOL"]
    for symbol in symbols:
        linked = [c for c in symbol_claims if c["claim_id"] in symbol["claim_ids"]]
        if not linked:
            errors.append(f"changed symbol {symbol['symbol_id']} lacks CHANGED_SYMBOL claim")
            continue
        expected = (
            "REFUTED"
            if symbol["finding_ids"]
            else "UNKNOWN"
            if symbol["scope_disposition"] == "UNKNOWN"
            else "NOT_APPLICABLE"
            if symbol["scope_disposition"] == "NOT_APPLICABLE"
            else "SUPPORTED"
        )
        for claim in linked:
            if claim["status"] != expected:
                errors.append(
                    f"changed-symbol claim {claim['claim_id']} status {claim['status']} must mirror {expected}"
                )

    machine_symbol_ids = {item["symbol_id"] for item in symbols if item["source"] == "MACHINE"}
    symbol_obligation_subjects = {
        item["subject"]
        for item in audit["audit_obligation_ledger"]
        if item["kind"] == "CHANGED_SYMBOL"
    }
    if symbol_obligation_subjects != machine_symbol_ids:
        errors.append(
            f"CHANGED_SYMBOL obligations must exactly match machine changed symbols: missing={sorted(machine_symbol_ids - symbol_obligation_subjects)}, extra={sorted(symbol_obligation_subjects - machine_symbol_ids)}"
        )

    if change_ledgers is not None:
        pr_numbers = {p["pr_number"] for p in audit["pr_bindings"]}
        if set(change_ledgers) != pr_numbers:
            errors.append(
                f"change-ledger PR set must exactly match audited PRs: expected={sorted(pr_numbers)} actual={sorted(change_ledgers)}"
            )
        bindings = {
            item["pr_number"]: item
            for item in audit["deterministic_census_binding"]["ledger_bindings"]
        }
        if set(bindings) != pr_numbers:
            errors.append(
                "deterministic_census_binding ledger_bindings must exactly cover audited PRs"
            )
        expected_machine_symbols: dict[str, dict[str, Any]] = {}
        expected_claim_seeds: dict[str, dict[str, Any]] = {}
        expected_fal_seeds: dict[str, dict[str, Any]] = {}
        for pr, wrapper in change_ledgers.items():
            ledger = wrapper["ledger"]
            digest = wrapper["sha256"]
            if (
                ledger.get("schema_version") != CHANGE_LEDGER_SCHEMA
                or ledger.get("generator_version") != CHANGE_LEDGER_GENERATOR_VERSION
            ):
                errors.append(f"PR {pr} change ledger version mismatch")
                continue
            if ledger.get("repository") != audit["repository_binding"]["repository"]:
                errors.append(f"PR {pr} change ledger repository mismatch")
            if (
                pr in pr_map(audit)
                and ledger.get("head_sha", "").lower() != pr_map(audit)[pr]["head_sha"].lower()
            ):
                errors.append(f"PR {pr} change ledger head_sha mismatch")
            binding = bindings.get(pr)
            if binding:
                if binding["head_sha"].lower() != ledger.get("head_sha", "").lower():
                    errors.append(f"PR {pr} deterministic census binding head_sha mismatch")
                if binding["ledger_sha256"] != digest:
                    errors.append(f"PR {pr} deterministic census binding ledger_sha256 mismatch")
            for item in ledger.get("changed_symbols", []):
                expected_machine_symbols[item["symbol_id"]] = item
            for item in ledger.get("claim_seeds", []):
                expected_claim_seeds[item["claim_id"]] = item
            for item in ledger.get("falsification_seeds", []):
                expected_fal_seeds[item["falsification_id"]] = item
        actual_machine = {
            item["symbol_id"]: item for item in symbols if item["source"] == "MACHINE"
        }
        if set(actual_machine) != set(expected_machine_symbols):
            errors.append(
                f"machine changed-symbol ledger must exactly match deterministic census: missing={sorted(set(expected_machine_symbols) - set(actual_machine))}, extra={sorted(set(actual_machine) - set(expected_machine_symbols))}"
            )
        for sid, expected in expected_machine_symbols.items():
            actual = actual_machine.get(sid)
            if not actual:
                continue
            for key in (
                "pr_number",
                "path",
                "symbol_name",
                "symbol_kind",
                "change_type",
                "detection_method",
                "detection_confidence",
            ):
                if actual.get(key) != expected.get(key):
                    errors.append(
                        f"machine changed symbol {sid} field {key} differs from deterministic census"
                    )
        actual_machine_claims = {
            item["claim_id"]: item for item in claims if item["source"] == "MACHINE_SEEDED"
        }
        if not set(expected_claim_seeds).issubset(actual_machine_claims):
            errors.append(
                f"claim matrix omitted deterministic claim seeds: {sorted(set(expected_claim_seeds) - set(actual_machine_claims))}"
            )
        for cid, expected in expected_claim_seeds.items():
            actual = actual_machine_claims.get(cid)
            if not actual:
                continue
            for key in ("claim_kind", "subject", "assertion", "materiality", "source"):
                if actual.get(key) != expected.get(key):
                    errors.append(
                        f"machine claim {cid} field {key} differs from deterministic census"
                    )
        actual_machine_fals = {
            item["falsification_id"]: item
            for item in falsifications
            if item["source"] == "MACHINE_SEEDED"
        }
        if not set(expected_fal_seeds).issubset(actual_machine_fals):
            errors.append(
                f"falsification ledger omitted deterministic seeds: {sorted(set(expected_fal_seeds) - set(actual_machine_fals))}"
            )
        for fid, expected in expected_fal_seeds.items():
            actual = actual_machine_fals.get(fid)
            if not actual:
                continue
            for key in ("claim_id", "source", "attack_class", "hypothesis"):
                if actual.get(key) != expected.get(key):
                    errors.append(
                        f"machine falsification {fid} field {key} differs from deterministic census"
                    )
    return errors


def deterministic_closure_errors(
    audit: dict[str, Any],
    emap: dict[str, dict[str, Any]],
    fmap: dict[str, dict[str, Any]],
    change_ledgers: dict[int, dict[str, Any]] | None,
) -> list[str]:
    errors: list[str] = []
    rows = audit["deterministic_closure_ledger"]
    row_map = {r["closure_id"]: r for r in rows}
    if len(row_map) != len(rows):
        errors.append("deterministic_closure_ledger contains duplicate closure_id values")

    machine_seeds: dict[str, dict[str, Any]] = {}
    if change_ledgers is not None:
        for pr, wrapper in change_ledgers.items():
            ledger = wrapper.get("ledger", wrapper)
            for seed in ledger.get("closure_seeds", []):
                machine_seeds[seed["closure_id"]] = seed
        machine_rows = {r["closure_id"]: r for r in rows if r["source"] == "MACHINE_SEEDED"}
        if set(machine_rows) != set(machine_seeds):
            missing = sorted(set(machine_seeds) - set(machine_rows))
            extra = sorted(set(machine_rows) - set(machine_seeds))
            if missing:
                errors.append(f"deterministic_closure_ledger missing machine seeds {missing}")
            if extra:
                errors.append(
                    f"deterministic_closure_ledger contains unbound machine seeds {extra}"
                )
        for cid, seed in machine_seeds.items():
            row = machine_rows.get(cid)
            if not row:
                continue
            for key in ("pr_number", "closure_kind", "subject", "seed_hash"):
                if row.get(key) != seed.get(key):
                    errors.append(f"closure {cid} rewrites machine-owned {key}")

    finding_ids = set(fmap)
    for row in rows:
        cid = row["closure_id"]
        for eid in row["evidence_ids"]:
            if eid not in emap:
                errors.append(f"closure {cid} references unknown evidence {eid}")
        for fid in row["finding_ids"]:
            if fid not in finding_ids:
                errors.append(f"closure {cid} references unknown finding {fid}")
        if row["status"] == "FINDING" and not row["finding_ids"]:
            errors.append(f"closure {cid} FINDING requires finding_ids")
        if (
            row["status"] == "UNKNOWN"
            and audit["executive_verdict"]["convergence_status"] == "CONVERGED"
        ):
            errors.append(f"CONVERGED cannot retain UNKNOWN deterministic closure {cid}")
        d = row["details"]
        kind = row["closure_kind"]
        if kind == "PUBLIC_CONTRACT":
            disp = d.get("disposition")
            if disp not in {
                "PRESERVED",
                "MIGRATION_AUTHORIZED",
                "BREAKING_FINDING",
                "NOT_APPLICABLE",
                "UNKNOWN",
            }:
                errors.append(f"closure {cid} PUBLIC_CONTRACT invalid disposition")
            if disp == "BREAKING_FINDING" and not row["finding_ids"]:
                errors.append(f"closure {cid} BREAKING_FINDING requires finding")
            preservation_ids = {x["obligation_id"] for x in audit["preservation_obligations"]}
            claimed = set(d.get("preservation_obligation_ids") or [])
            if disp in {"PRESERVED", "MIGRATION_AUTHORIZED", "BREAKING_FINDING"} and not claimed:
                errors.append(
                    f"closure {cid} public-contract delta requires preservation_obligation_ids"
                )
            if claimed - preservation_ids:
                errors.append(
                    f"closure {cid} references unknown preservation obligations {sorted(claimed - preservation_ids)}"
                )
        elif kind == "SSOT_UNIQUENESS":
            disp = d.get("disposition")
            allowed = {
                "UNIQUE",
                "CANDIDATES_ENUMERATED",
                "SAME_AUTHORITY",
                "DISTINCT_SEMANTIC",
                "COMPETING_AUTHORITY",
                "UNKNOWN",
            }
            if disp not in allowed:
                errors.append(f"closure {cid} SSOT_UNIQUENESS invalid disposition")
            if disp == "COMPETING_AUTHORITY" and not row["finding_ids"]:
                errors.append(f"closure {cid} competing authority requires finding")
            seed = machine_seeds.get(cid, {}).get("payload", {})
            if seed.get("coverage_only"):
                if not seed.get("repository_files_complete") and disp != "UNKNOWN":
                    errors.append(
                        f"closure {cid} SSOT coverage cannot close from incomplete repository corpus"
                    )
                expected = (
                    "UNIQUE" if seed.get("candidate_count", 0) == 0 else "CANDIDATES_ENUMERATED"
                )
                if seed.get("repository_files_complete") and disp not in {expected, "UNKNOWN"}:
                    errors.append(
                        f"closure {cid} SSOT coverage disposition must be {expected} or UNKNOWN"
                    )
            elif (
                row["source"] == "MACHINE_SEEDED"
                and not seed.get("repository_files_complete", False)
                and disp in {"SAME_AUTHORITY", "DISTINCT_SEMANTIC"}
            ):
                errors.append(
                    f"closure {cid} cannot prove SSOT candidate disposition from incomplete repository corpus"
                )
        elif kind == "BYPASS_PATH":
            disp = d.get("disposition")
            if disp not in {
                "COVERAGE_COMPLETE",
                "REQUIRED_BOUNDARY_PRESENT",
                "ALLOWED_DIRECT_PATH",
                "BYPASS_FINDING",
                "UNKNOWN",
            }:
                errors.append(f"closure {cid} BYPASS_PATH invalid disposition")
            if disp == "BYPASS_FINDING" and not row["finding_ids"]:
                errors.append(f"closure {cid} bypass finding requires finding")
            seed = machine_seeds.get(cid, {}).get("payload", {})
            if seed.get("coverage_only"):
                if not seed.get("repository_files_complete") and disp != "UNKNOWN":
                    errors.append(
                        f"closure {cid} bypass coverage cannot close from incomplete repository corpus"
                    )
                if seed.get("repository_files_complete") and disp not in {
                    "COVERAGE_COMPLETE",
                    "UNKNOWN",
                }:
                    errors.append(
                        f"closure {cid} bypass coverage requires COVERAGE_COMPLETE or UNKNOWN"
                    )
            elif (
                disp == "REQUIRED_BOUNDARY_PRESENT"
                and seed
                and not seed.get("required_token_present")
            ):
                errors.append(
                    f"closure {cid} cannot claim required boundary present when machine census did not observe it"
                )
        elif kind == "SUPERSESSION_LIVENESS":
            cls = d.get("classification")
            if cls not in {"LIVE", "DEAD", "DOC_ONLY", "TEST_ONLY", "GENERATED", "UNKNOWN"}:
                errors.append(f"closure {cid} SUPERSESSION_LIVENESS invalid classification")
            if cls == "LIVE" and not row["finding_ids"]:
                errors.append(f"closure {cid} LIVE supersession reference requires finding")
        elif kind == "FAILURE_EDGE":
            if d.get("disposition") not in {
                "TESTED",
                "STRUCTURALLY_PROVEN",
                "NOT_APPLICABLE",
                "UNKNOWN",
            }:
                errors.append(f"closure {cid} FAILURE_EDGE invalid disposition")
        elif kind == "CONFIG_PRECEDENCE":
            disp = d.get("disposition")
            if disp not in {"SINGLE_WINNER", "CONFLICT", "NONE", "UNKNOWN"}:
                errors.append(f"closure {cid} CONFIG_PRECEDENCE invalid disposition")
            seed = machine_seeds.get(cid, {}).get("payload", {})
            paths = {x.get("path") for x in seed.get("sources", []) if isinstance(x, dict)}
            if disp == "SINGLE_WINNER":
                winner = d.get("winner_path")
                if not seed.get("repository_files_complete"):
                    errors.append(
                        f"closure {cid} SINGLE_WINNER requires complete repository corpus"
                    )
                if winner not in paths:
                    errors.append(
                        f"closure {cid} SINGLE_WINNER winner_path must be a discovered source"
                    )
                src = next((x for x in seed.get("sources", []) if x.get("path") == winner), {})
                if src.get("authority_kind") in {None, "UNKNOWN"}:
                    errors.append(f"closure {cid} SINGLE_WINNER requires known winner authority")
            if disp == "CONFLICT" and not row["finding_ids"]:
                errors.append(f"closure {cid} config conflict requires finding")
        elif kind == "DEPENDENCY_CAUSALITY":
            disp = d.get("disposition")
            if disp not in {"JUSTIFIED", "UNJUSTIFIED", "TRANSITIVE", "LOCK_ONLY", "UNKNOWN"}:
                errors.append(f"closure {cid} DEPENDENCY_CAUSALITY invalid disposition")
            if disp == "JUSTIFIED" and not d.get("objective_ids") and not row["finding_ids"]:
                errors.append(
                    f"closure {cid} justified dependency movement requires objective_ids or finding linkage"
                )
            if disp == "UNJUSTIFIED" and not row["finding_ids"]:
                errors.append(f"closure {cid} unjustified dependency movement requires finding")
        elif kind == "DEPENDENCY_PAIRING":
            disp = d.get("disposition")
            if disp not in {"CONSISTENT", "MISMATCH", "NOT_APPLICABLE", "UNKNOWN"}:
                errors.append(f"closure {cid} DEPENDENCY_PAIRING invalid disposition")
            if disp == "MISMATCH" and not row["finding_ids"]:
                errors.append(f"closure {cid} manifest/lock mismatch requires finding")
        elif kind == "DIFF_HUNK":
            disp = d.get("disposition")
            if disp not in {
                "REQUIRED",
                "DIRECTLY_COUPLED",
                "VALIDATION_REQUIRED",
                "GENERATED",
                "FORMATTING_ONLY",
                "FINDING",
                "UNKNOWN",
            }:
                errors.append(f"closure {cid} DIFF_HUNK invalid disposition")
            if disp == "FINDING" and not row["finding_ids"]:
                errors.append(f"closure {cid} hunk FINDING requires finding_ids")
            if disp in {"REQUIRED", "DIRECTLY_COUPLED", "VALIDATION_REQUIRED"} and not d.get(
                "objective_ids"
            ):
                errors.append(f"closure {cid} substantive hunk requires objective_ids")
        elif kind == "CI_CAUSALITY":
            cause = d.get("causality")
            if cause not in {"PR_CAUSED", "PRE_EXISTING", "ENVIRONMENT", "PIPELINE", "UNKNOWN"}:
                errors.append(f"closure {cid} CI_CAUSALITY invalid causality")
            if cause == "PR_CAUSED" and not row["finding_ids"]:
                errors.append(f"closure {cid} PR_CAUSED CI failure requires finding")
            if cause == "PRE_EXISTING" and not evidence_discriminates(
                row["evidence_ids"], emap, "ci_baseline"
            ):
                errors.append(
                    f"closure {cid} PRE_EXISTING CI attribution requires ci_baseline evidence"
                )
        elif kind == "GENERATED_PROVENANCE":
            disp = d.get("disposition")
            if disp not in {"MATCHED", "MISMATCHED", "UNKNOWN", "NOT_APPLICABLE"}:
                errors.append(f"closure {cid} GENERATED_PROVENANCE invalid disposition")
            seed = machine_seeds.get(cid, {}).get("payload", {})
            if disp == "MATCHED":
                if (
                    not seed.get("generator_path")
                    or not seed.get("source_inputs")
                    or not seed.get("generation_command")
                ):
                    errors.append(
                        f"closure {cid} MATCHED generated provenance requires generator/source/command"
                    )
                if not seed.get("generated_head_sha") or seed.get("generated_head_sha") != seed.get(
                    "regenerated_sha"
                ):
                    errors.append(
                        f"closure {cid} MATCHED generated provenance requires equal generated/regenerated hashes"
                    )
            if disp == "MISMATCHED" and not row["finding_ids"]:
                errors.append(f"closure {cid} generated mismatch requires finding")
        elif kind == "PRODUCER_CONSUMER":
            disp = d.get("disposition")
            allowed = {
                "COVERAGE_COMPLETE",
                "UNCHANGED_COMPATIBLE",
                "UPDATED",
                "MIGRATION_REQUIRED",
                "NOT_APPLICABLE",
                "UNKNOWN",
            }
            if disp not in allowed:
                errors.append(f"closure {cid} PRODUCER_CONSUMER invalid disposition")
            seed = machine_seeds.get(cid, {}).get("payload", {})
            if seed.get("coverage_only"):
                if not seed.get("repository_files_complete") and disp != "UNKNOWN":
                    errors.append(
                        f"closure {cid} producer/consumer coverage cannot close from incomplete corpus"
                    )
                if seed.get("repository_files_complete") and disp not in {
                    "COVERAGE_COMPLETE",
                    "UNKNOWN",
                }:
                    errors.append(
                        f"closure {cid} producer/consumer coverage requires COVERAGE_COMPLETE or UNKNOWN"
                    )
            else:
                if (
                    disp == "MIGRATION_REQUIRED"
                    and not row["finding_ids"]
                    and not d.get("preservation_obligation_ids")
                ):
                    errors.append(
                        f"closure {cid} MIGRATION_REQUIRED requires finding or preservation obligation"
                    )
                preservation_ids = {x["obligation_id"] for x in audit["preservation_obligations"]}
                claimed = set(d.get("preservation_obligation_ids") or [])
                if claimed - preservation_ids:
                    errors.append(
                        f"closure {cid} references unknown preservation obligations {sorted(claimed - preservation_ids)}"
                    )
        elif kind == "MUTATION_EXECUTION":
            result = d.get("result")
            allowed = {
                "KILLED",
                "SURVIVED",
                "BASELINE_FAILED",
                "EXECUTION_ERROR",
                "NOT_EXECUTED",
                "NOT_APPLICABLE",
            }
            if result not in allowed:
                errors.append(f"closure {cid} MUTATION_EXECUTION invalid result")
            if result == "KILLED":
                if (
                    d.get("baseline_exit_code") != 0
                    or not isinstance(d.get("mutant_exit_code"), int)
                    or d.get("mutant_exit_code") == 0
                ):
                    errors.append(f"closure {cid} KILLED requires baseline pass and mutant failure")
                if row["status"] != "PASS":
                    errors.append(f"closure {cid} KILLED must have PASS status")
            elif result == "SURVIVED":
                if d.get("baseline_exit_code") != 0 or d.get("mutant_exit_code") != 0:
                    errors.append(f"closure {cid} SURVIVED requires baseline and mutant pass")
                if row["status"] != "FINDING" or not row["finding_ids"]:
                    errors.append(f"closure {cid} SURVIVED requires FINDING status and finding")
            elif result in {"BASELINE_FAILED", "EXECUTION_ERROR", "NOT_EXECUTED"}:
                if row["status"] != "UNKNOWN":
                    errors.append(f"closure {cid} {result} must remain UNKNOWN")
                if not d.get("reason"):
                    errors.append(f"closure {cid} {result} requires reason")
            elif result == "NOT_APPLICABLE" and row["status"] != "NOT_APPLICABLE":
                errors.append(f"closure {cid} NOT_APPLICABLE result requires NOT_APPLICABLE status")
            if d.get("original_repository_unchanged") is False:
                errors.append(f"closure {cid} mutation execution altered audited repository")
        elif kind == "REVIEW_THREAD_SEMANTIC":
            disp = d.get("disposition")
            allowed = {
                "FIXED_BY_FINDING",
                "DISPROVEN_WITH_EVIDENCE",
                "ACCEPTED_NONBLOCKER",
                "DUPLICATE",
                "OUT_OF_SCOPE",
                "UNKNOWN",
            }
            if disp not in allowed:
                errors.append(f"closure {cid} REVIEW_THREAD_SEMANTIC invalid disposition")
            if disp == "FIXED_BY_FINDING" and not row["finding_ids"]:
                errors.append(f"closure {cid} FIXED_BY_FINDING requires finding")
            if disp == "DISPROVEN_WITH_EVIDENCE" and not evidence_discriminates(
                row["evidence_ids"], emap, "review_thread_disposition"
            ):
                errors.append(
                    f"closure {cid} disproven thread requires review_thread_disposition evidence"
                )
            if disp == "ACCEPTED_NONBLOCKER" and not evidence_discriminates(
                row["evidence_ids"], emap, "review_thread_acceptance"
            ):
                errors.append(
                    f"closure {cid} accepted nonblocker requires review_thread_acceptance authority evidence"
                )
            if disp == "DUPLICATE" and not d.get("duplicate_of"):
                errors.append(f"closure {cid} DUPLICATE requires duplicate_of")
            if disp == "OUT_OF_SCOPE" and not evidence_discriminates(
                row["evidence_ids"], emap, "review_thread_scope"
            ):
                errors.append(f"closure {cid} OUT_OF_SCOPE requires review_thread_scope evidence")
        elif kind == "ORPHAN_ARTIFACT":
            disp = d.get("disposition")
            allowed = {"REACHABLE", "REGISTERED", "CONTRACT_AUTHORIZED", "ORPHAN", "UNKNOWN"}
            if disp not in allowed:
                errors.append(f"closure {cid} ORPHAN_ARTIFACT invalid disposition")
            seed = machine_seeds.get(cid, {}).get("payload", {})
            if disp == "REACHABLE":
                if (
                    not seed.get("repository_files_complete")
                    or int(seed.get("consumer_count", 0)) < 1
                ):
                    errors.append(
                        f"closure {cid} REACHABLE requires complete corpus and discovered consumer"
                    )
            if disp == "REGISTERED" and not evidence_discriminates(
                row["evidence_ids"], emap, "artifact_registration"
            ):
                errors.append(f"closure {cid} REGISTERED requires artifact_registration evidence")
            if disp == "CONTRACT_AUTHORIZED" and not evidence_discriminates(
                row["evidence_ids"], emap, "future_contract_authority"
            ):
                errors.append(
                    f"closure {cid} CONTRACT_AUTHORIZED requires future_contract_authority evidence"
                )
            if disp == "ORPHAN" and (row["status"] != "FINDING" or not row["finding_ids"]):
                errors.append(f"closure {cid} ORPHAN requires finding")
        elif kind == "ARCHITECTURE_ECONOMY":
            basis = d.get("justification_basis")
            allowed = {
                "REQUIREMENT_NECESSITATES_BOUNDARY",
                "VERIFIED_PATTERN_EXTENSION",
                "EXISTING_OWNER_CANNOT_ABSORB",
                "UNJUSTIFIED",
                "UNKNOWN",
            }
            if basis not in allowed:
                errors.append(f"closure {cid} ARCHITECTURE_ECONOMY invalid justification_basis")
            if basis == "UNJUSTIFIED" and not row["finding_ids"]:
                errors.append(f"closure {cid} unjustified architecture requires finding")
            if (
                basis in allowed - {"UNJUSTIFIED", "UNKNOWN"}
                and not d.get("objective_ids")
                and not d.get("authority_ids")
            ):
                errors.append(
                    f"closure {cid} justified architecture requires objective_ids or authority_ids"
                )

    # Cross-link deterministic candidates back to the pre-existing canonical change-discipline stores.
    machine_failure_edges = {
        seed["subject"] for seed in machine_seeds.values() if seed["closure_kind"] == "FAILURE_EDGE"
    }
    failure_rows = {
        item["failure_path_id"] for item in audit["change_discipline"]["failure_path_coverage"]
    }
    if machine_failure_edges != failure_rows:
        errors.append(
            f"failure_path_coverage must exactly cover machine failure edges: missing={sorted(machine_failure_edges - failure_rows)}, extra={sorted(failure_rows - machine_failure_edges)}"
        )

    supersession_rows = {
        item["supersession_id"]: item for item in audit["change_discipline"]["supersession_closure"]
    }
    live_by_sup: dict[str, list[str]] = defaultdict(list)
    unknown_by_sup: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row["closure_kind"] != "SUPERSESSION_LIVENESS":
            continue
        seed = machine_seeds.get(row["closure_id"], {}).get("payload", {})
        sid = seed.get("supersession_id")
        cls = row["details"].get("classification")
        if sid and cls == "LIVE":
            live_by_sup[sid].append(row["subject"])
        if sid and cls == "UNKNOWN":
            unknown_by_sup[sid].append(row["subject"])
    for sid, discipline_row in supersession_rows.items():
        if discipline_row["status"] == "CLOSED" and (
            live_by_sup.get(sid) or unknown_by_sup.get(sid)
        ):
            errors.append(
                f"supersession {sid} cannot be CLOSED with LIVE/UNKNOWN liveness references"
            )
        if discipline_row["status"] == "RESIDUAL" and not live_by_sup.get(sid):
            errors.append(
                f"supersession {sid} RESIDUAL requires at least one LIVE liveness reference"
            )

    economy_rows = {
        item["candidate_id"]: item for item in audit["change_discipline"]["architectural_economy"]
    }
    economy_closures = {
        row["subject"]: row
        for row in rows
        if row["closure_kind"] == "ARCHITECTURE_ECONOMY" and row["source"] == "MACHINE_SEEDED"
    }
    if set(economy_closures) != set(economy_rows):
        errors.append(
            f"architecture-economy closure must exactly cover canonical candidates: missing={sorted(set(economy_rows) - set(economy_closures))}, extra={sorted(set(economy_closures) - set(economy_rows))}"
        )
    for candidate_id, discipline_row in economy_rows.items():
        closure = economy_closures.get(candidate_id)
        if not closure:
            continue
        basis = closure["details"].get("justification_basis")
        if discipline_row["disposition"] == "JUSTIFIED" and basis not in {
            "REQUIREMENT_NECESSITATES_BOUNDARY",
            "VERIFIED_PATTERN_EXTENSION",
            "EXISTING_OWNER_CANNOT_ABSORB",
        }:
            errors.append(
                f"architecture candidate {candidate_id} JUSTIFIED requires a concrete deterministic justification basis"
            )
        if discipline_row["disposition"] == "UNJUSTIFIED" and basis != "UNJUSTIFIED":
            errors.append(
                f"architecture candidate {candidate_id} UNJUSTIFIED must use UNJUSTIFIED closure basis"
            )
        if discipline_row["disposition"] == "UNKNOWN" and basis != "UNKNOWN":
            errors.append(
                f"architecture candidate {candidate_id} UNKNOWN must use UNKNOWN closure basis"
            )

    # A required check observed failing in the bound deterministic census cannot coexist with READY.
    if audit["executive_verdict"]["readiness_status"] in {"READY", "CONDITIONALLY_READY"}:
        for row in rows:
            if row["closure_kind"] != "CI_CAUSALITY" or row["source"] != "MACHINE_SEEDED":
                continue
            seed = machine_seeds.get(row["closure_id"], {}).get("payload", {})
            if seed.get("required") and str(seed.get("conclusion", "")).lower() in {
                "failure",
                "failed",
                "error",
                "cancelled",
                "timed_out",
            }:
                errors.append(
                    f"READY cannot coexist with current required failed check {seed.get('name')}"
                )

    # v2.0 closure cross-rules.
    review_seed_ids = {
        seed["subject"]
        for seed in machine_seeds.values()
        if seed["closure_kind"] == "REVIEW_THREAD_SEMANTIC"
    }
    review_rows = {
        row["subject"]
        for row in rows
        if row["closure_kind"] == "REVIEW_THREAD_SEMANTIC" and row["source"] == "MACHINE_SEEDED"
    }
    if review_rows != review_seed_ids:
        errors.append(
            f"review-thread semantic closure must exactly cover machine threads: missing={sorted(review_seed_ids - review_rows)}, extra={sorted(review_rows - review_seed_ids)}"
        )
    # Strong test discrimination cannot coexist with a survived or unresolved executable mutation candidate.
    mutation_by_path = defaultdict(list)
    for row in rows:
        if row["closure_kind"] == "MUTATION_EXECUTION":
            seed = machine_seeds.get(row["closure_id"], {}).get("payload", {})
            mutation_by_path[seed.get("path")].append(row)
    for td in audit["change_discipline"]["test_discrimination"]:
        if td["status"] != "DISCRIMINATING":
            continue
        related = (
            mutation_by_path.get(td.get("surface")) or mutation_by_path.get(td.get("path")) or []
        )
        if related and any(r["details"].get("result") != "KILLED" for r in related):
            errors.append(
                f"test discrimination {td.get('test_discrimination_id')} cannot be DISCRIMINATING while mutation candidates are not all KILLED"
            )
    # Complete producer/consumer coverage is required for each machine public-contract delta when repository corpus is complete.
    pc_coverage = [
        r
        for r in rows
        if r["closure_kind"] == "PRODUCER_CONSUMER"
        and machine_seeds.get(r["closure_id"], {}).get("payload", {}).get("coverage_only")
    ]
    for row in pc_coverage:
        seed = machine_seeds.get(row["closure_id"], {}).get("payload", {})
        if (
            seed.get("repository_files_complete")
            and row["details"].get("disposition") != "COVERAGE_COMPLETE"
        ):
            errors.append(
                f"producer/consumer coverage {row['closure_id']} must close COVERAGE_COMPLETE on complete corpus"
            )
    # Orphan candidates cannot converge as UNKNOWN.
    if audit["executive_verdict"]["convergence_status"] == "CONVERGED":
        for row in rows:
            if (
                row["closure_kind"]
                in {
                    "REVIEW_THREAD_SEMANTIC",
                    "ORPHAN_ARTIFACT",
                    "MUTATION_EXECUTION",
                    "PRODUCER_CONSUMER",
                }
                and row["status"] == "UNKNOWN"
            ):
                errors.append(
                    f"CONVERGED cannot retain unresolved v2.0 closure {row['closure_id']}"
                )

    post = audit["post_judgment_closure"]
    # Root-cause dominance: same semantic owner + overlapping implementation surface creates a mandatory pair.
    surfaces = {
        x["finding_id"]: set(x["implementation_surfaces"])
        for x in audit["remediation_surface_index"]
    }
    findings = audit["findings"]
    required_pairs = set()
    for i, a in enumerate(findings):
        for b in findings[i + 1 :]:
            if a["ownership"]["semantic_owner"] == b["ownership"][
                "semantic_owner"
            ] and surfaces.get(a["finding_id"], set()) & surfaces.get(b["finding_id"], set()):
                required_pairs.add(tuple(sorted((a["finding_id"], b["finding_id"]))))
    pair_rows = {
        tuple(sorted((x["finding_a"], x["finding_b"]))): x for x in post["root_cause_dominance"]
    }
    if set(pair_rows) != required_pairs:
        errors.append(
            f"root_cause_dominance must exactly cover machine candidate pairs {sorted(required_pairs)}"
        )
    for pair, row in pair_rows.items():
        if (
            row["disposition"] == "UNKNOWN"
            and audit["executive_verdict"]["convergence_status"] == "CONVERGED"
        ):
            errors.append(f"CONVERGED cannot retain UNKNOWN root-cause dominance {pair}")
        for eid in row["evidence_ids"]:
            if eid not in emap:
                errors.append(f"root-cause pair {pair} references unknown evidence {eid}")

    # Severity floors/ceilings. Blocking findings default floor High; Critical requires confirmed, blocking, high-impact class.
    rank = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
    high_impact = {
        "SECURITY",
        "CORRECTNESS",
        "CONTRACT",
        "INVARIANT",
        "RELIABILITY",
        "PRESERVATION",
        "CROSS_PR",
        "SOURCE_OF_TRUTH",
    }
    sev_rows = {x["finding_id"]: x for x in post["severity_consistency"]}
    if set(sev_rows) != set(fmap):
        errors.append("severity_consistency must cover every finding exactly once")
    for fid, f in fmap.items():
        row = sev_rows.get(fid)
        if not row:
            continue
        floor = "High" if f["merge_blocking"] else "Low"
        ceiling = (
            "Critical"
            if f["merge_blocking"]
            and f["confidence"] == "Confirmed"
            and f["finding_class"] in high_impact
            else "High"
        )
        if (
            row["machine_floor"] != floor
            or row["machine_ceiling"] != ceiling
            or row["actual_severity"] != f["severity"]
        ):
            errors.append(f"severity row {fid} does not match deterministic bounds/actual severity")
        consistent = rank[floor] <= rank[f["severity"]] <= rank[ceiling]
        if row["status"] == "CONSISTENT" and not consistent:
            errors.append(
                f"finding {fid} severity outside deterministic bounds requires authority override"
            )
        if row["status"] == "OVERRIDDEN_WITH_AUTHORITY" and not evidence_discriminates(
            row["evidence_ids"], emap, "severity_override"
        ):
            errors.append(f"finding {fid} severity override lacks severity_override evidence")
        if (
            row["status"] == "UNKNOWN"
            and audit["executive_verdict"]["convergence_status"] == "CONVERGED"
        ):
            errors.append(f"CONVERGED cannot retain UNKNOWN severity consistency for {fid}")

    # Every executed validation is either claim-closing or explicitly justified non-closing evidence.
    exec_ids = {eid for eid, e in emap.items() if e["evidence_type"] in EXECUTION_EVIDENCE}
    cov = {x["evidence_id"]: x for x in post["validation_run_coverage"]}
    if set(cov) != exec_ids:
        errors.append(
            "validation_run_coverage must exactly cover every TEST/CI/RUNTIME/MEASUREMENT evidence record"
        )
    claims = {x["claim_id"]: x for x in audit["claim_validation_matrix"]}
    for eid, row in cov.items():
        if row["disposition"] == "CLAIM_CLOSING":
            if not row["claim_ids"]:
                errors.append(f"validation evidence {eid} CLAIM_CLOSING requires claim_ids")
            for cid in row["claim_ids"]:
                if cid not in claims or eid not in claims[cid]["validation_evidence_ids"]:
                    errors.append(f"validation evidence {eid} does not actually close claim {cid}")
        elif row["disposition"] == "JUSTIFIED_NON_CLOSING" and not row["rationale"].strip():
            errors.append(f"validation evidence {eid} non-closing disposition requires rationale")
        elif (
            row["disposition"] == "UNKNOWN"
            and audit["executive_verdict"]["convergence_status"] == "CONVERGED"
        ):
            errors.append(f"CONVERGED cannot retain UNKNOWN validation coverage for {eid}")
    return errors


def validate_semantics(
    audit: dict[str, Any], change_ledgers: dict[int, dict[str, Any]] | None = None
) -> list[str]:
    """Validate cross-field invariants that JSON Schema cannot express cleanly."""
    errors: list[str] = []
    if audit.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
        return errors

    repo = audit["repository_binding"]
    repo_name = repo["repository"]
    baseline = repo["audited_default_branch_sha"].lower()

    # Identity uniqueness.
    pnums = [p["pr_number"] for p in audit["pr_bindings"]]
    if len(pnums) != len(set(pnums)):
        errors.append("pr_bindings contains duplicate pr_number values")
    emap = evidence_map(audit)
    if len(emap) != len(audit["shared_evidence_index"]):
        errors.append("shared_evidence_index contains duplicate evidence_id values")
    fmap = finding_map(audit)
    if len(fmap) != len(audit["findings"]):
        errors.append("findings contains duplicate finding_id values")
    smap = surface_map(audit)
    if len(smap) != len(audit["remediation_surface_index"]):
        errors.append("remediation_surface_index contains duplicate finding_id values")
    gmap = graph_map(audit)
    if len(gmap) != len(audit["finding_dependency_graph"]):
        errors.append("finding_dependency_graph contains duplicate finding_id values")
    amap = authority_map(audit)
    if len(amap) != len(audit["authority_resolution"]["sources"]):
        errors.append("authority_resolution.sources contains duplicate authority_id values")

    errors.extend(red_team_semantic_errors(audit, emap, fmap, amap, change_ledgers))
    errors.extend(deterministic_closure_errors(audit, emap, fmap, change_ledgers))

    pr_by_num = pr_map(audit)
    heads = {num: item["head_sha"].lower() for num, item in pr_by_num.items()}

    # Evidence integrity, execution revision identity, and secret-safe repository binding.
    for eid, item in emap.items():
        if item["repository"] != repo_name:
            errors.append(
                f"evidence {eid} repository {item['repository']!r} != canonical {repo_name!r}"
            )
        if item["evidence_type"] in EXECUTION_EVIDENCE:
            source = item.get("source_head_sha")
            tested = item.get("tested_revision_sha")
            result = item.get("validation_result")
            if source is None or tested is None or result is None:
                errors.append(
                    f"execution evidence {eid} requires source_head_sha, tested_revision_sha, validation_result"
                )
                continue
            if source != "UNKNOWN" and (
                not is_sha(source) or source.lower() not in set(heads.values())
            ):
                errors.append(
                    f"execution evidence {eid}.source_head_sha must equal an audited PR source head or UNKNOWN"
                )
            if tested != "UNKNOWN" and not is_sha(tested):
                errors.append(
                    f"execution evidence {eid}.tested_revision_sha must be SHA or UNKNOWN"
                )
            if result in {"PASS", "FAIL"} and not is_sha(tested):
                errors.append(
                    f"execution evidence {eid} cannot claim {result} without exact tested_revision_sha"
                )
        elif any(
            key in item for key in ("source_head_sha", "tested_revision_sha", "validation_result")
        ):
            # Permitted structurally, but avoid ambiguous execution semantics on non-execution evidence.
            if item.get("validation_result") in {"PASS", "FAIL"}:
                errors.append(
                    f"non-execution evidence {eid} must not carry PASS/FAIL validation_result"
                )

    # Intent/change-discipline integrity and complete deterministic disposition.
    intent = audit["intent_contract"]
    source_ids = {item["source_id"] for item in intent["sources"]}
    if len(source_ids) != len(intent["sources"]):
        errors.append("intent_contract.sources contains duplicate source_id values")
    objective_ids = {item["objective_id"] for item in intent["objectives"]}
    if len(objective_ids) != len(intent["objectives"]):
        errors.append("intent_contract.objectives contains duplicate objective_id values")
    active_objectives = {
        item["objective_id"] for item in intent["objectives"] if item["status"] == "ACTIVE"
    }
    for src in intent["sources"]:
        for eid in src["evidence_ids"]:
            if eid not in emap:
                errors.append(f"intent source {src['source_id']} references missing evidence {eid}")
    for obj in intent["objectives"]:
        for sid in obj["source_ids"]:
            if sid not in source_ids:
                errors.append(
                    f"objective {obj['objective_id']} references unknown intent source {sid}"
                )
    original = intent["original_pr_prompt"]
    if original["availability"] in {"PROVIDED", "RECOVERED"}:
        if not original.get("source_id") or original["source_id"] not in source_ids:
            errors.append("available original PR prompt requires a valid source_id")
        for eid in original["evidence_ids"]:
            if eid not in emap:
                errors.append(f"original PR prompt references missing evidence {eid}")
    elif original.get("source_id") is not None:
        errors.append("unavailable original PR prompt must not claim source_id")

    for num, pr in pr_by_num.items():
        seen_paths: set[str] = set()
        for item in pr["changed_files"]:
            path = item["path"]
            if path in seen_paths:
                errors.append(f"PR {num} changed_files contains duplicate path {path}")
            seen_paths.add(path)
            if not safe_repo_path(path):
                errors.append(f"PR {num} changed file path is unsafe: {path}")

    discipline = audit["change_discipline"]
    closure = {item["objective_id"]: item for item in discipline["objective_closure"]}
    if set(closure) != active_objectives:
        errors.append(
            f"objective_closure must cover exactly active objectives; expected={sorted(active_objectives)} observed={sorted(closure)}"
        )
    for item in discipline["objective_closure"]:
        for eid in item["implementation_evidence_ids"] + item["validation_evidence_ids"]:
            if eid not in emap:
                errors.append(
                    f"objective closure {item['objective_id']} references missing evidence {eid}"
                )
        for fid in item["finding_ids"]:
            if fid not in fmap:
                errors.append(
                    f"objective closure {item['objective_id']} references unknown finding {fid}"
                )

    scope_by_pr: dict[int, set[str]] = defaultdict(set)
    for item in discipline["scope_fidelity"]["changed_surfaces"]:
        num = item["pr_number"]
        if num not in pr_by_num:
            errors.append(f"scope_fidelity references unknown PR {num}")
            continue
        if item["path"] in scope_by_pr[num]:
            errors.append(f"scope_fidelity duplicates PR {num} path {item['path']}")
        scope_by_pr[num].add(item["path"])
        for oid in item["objective_ids"]:
            if oid not in objective_ids:
                errors.append(f"scope surface {item['path']} references unknown objective {oid}")
        for eid in item["evidence_ids"]:
            if eid not in emap:
                errors.append(f"scope surface {item['path']} references missing evidence {eid}")
        for fid in item["finding_ids"]:
            if fid not in fmap:
                errors.append(f"scope surface {item['path']} references unknown finding {fid}")
        if item["disposition"] == "SCOPE_EXTENSION" and not item["finding_ids"]:
            errors.append(f"scope extension {item['path']} requires finding_ids")
    for num, pr in pr_by_num.items():
        expected = {item["path"] for item in pr["changed_files"]}
        observed = scope_by_pr.get(num, set())
        if observed != expected:
            errors.append(
                f"PR {num} scope_fidelity must disposition every changed file exactly once; missing={sorted(expected - observed)} extra={sorted(observed - expected)}"
            )

    complexity_by_pr = {item["pr_number"]: item for item in discipline["complexity_delta"]}
    if set(complexity_by_pr) != set(pr_by_num):
        errors.append("complexity_delta must contain exactly one record per bound PR")
    for num, item in complexity_by_pr.items():
        if num not in pr_by_num:
            continue
        files = pr_by_num[num]["changed_files"]
        expected_added = sum(1 for f in files if f["status"] == "added")
        expected_deleted = sum(1 for f in files if f["status"] == "deleted")
        expected_modified = len(files) - expected_added - expected_deleted
        if (item["files_added"], item["files_deleted"], item["files_modified"]) != (
            expected_added,
            expected_deleted,
            expected_modified,
        ):
            errors.append(
                f"PR {num} complexity_delta file counts do not match changed_files inventory"
            )
        for eid in item["evidence_ids"]:
            if eid not in emap:
                errors.append(f"PR {num} complexity_delta references missing evidence {eid}")

    for section, id_key, bad_state in (
        ("architectural_economy", "candidate_id", "UNJUSTIFIED"),
        ("supersession_closure", "supersession_id", "RESIDUAL"),
        ("failure_path_coverage", "failure_path_id", None),
        ("test_discrimination", "test_obligation_id", None),
    ):
        seen: set[str] = set()
        for item in discipline[section]:
            ident = item[id_key]
            if ident in seen:
                errors.append(f"{section} contains duplicate {id_key} {ident}")
            seen.add(ident)
            if item["pr_number"] not in pr_by_num:
                errors.append(f"{section} {ident} references unknown PR {item['pr_number']}")
            for eid in item["evidence_ids"]:
                if eid not in emap:
                    errors.append(f"{section} {ident} references missing evidence {eid}")
            for fid in item["finding_ids"]:
                if fid not in fmap:
                    errors.append(f"{section} {ident} references unknown finding {fid}")
            for oid in item.get("objective_ids", []):
                if oid not in objective_ids:
                    errors.append(f"{section} {ident} references unknown objective {oid}")
            if (
                bad_state is not None
                and item.get("disposition", item.get("status")) == bad_state
                and not item["finding_ids"]
            ):
                errors.append(f"{section} {ident} state {bad_state} requires finding_ids")
            if section == "architectural_economy" and item["disposition"] == "JUSTIFIED":
                if not item["objective_ids"]:
                    errors.append(f"architectural economy {ident} JUSTIFIED requires objective_ids")
                if not item["existing_owner_considered"]:
                    errors.append(
                        f"architectural economy {ident} JUSTIFIED requires existing_owner_considered=true"
                    )
            if (
                section == "supersession_closure"
                and item["status"] == "RESIDUAL"
                and not item["finding_ids"]
            ):
                errors.append(f"supersession {ident} RESIDUAL requires finding_ids")
            if (
                section == "test_discrimination"
                and item["status"] in {"WEAK", "ABSENT"}
                and not item["finding_ids"]
            ):
                errors.append(f"test discrimination {ident} {item['status']} requires finding_ids")

    seen_controls: set[str] = set()
    known_control_boundaries = {
        item["boundary_id"]: item for item in audit["boundary_map"]["boundaries"]
    }
    for item in discipline["control_adequacy"]:
        ident = item["control_id"]
        if ident in seen_controls:
            errors.append(f"control_adequacy contains duplicate control_id {ident}")
        seen_controls.add(ident)
        if item["pr_number"] not in pr_by_num:
            errors.append(f"control_adequacy {ident} references unknown PR {item['pr_number']}")
        for eid in item["evidence_ids"]:
            if eid not in emap:
                errors.append(f"control_adequacy {ident} references missing evidence {eid}")
        for fid in item["finding_ids"]:
            if fid not in fmap:
                errors.append(f"control_adequacy {ident} references unknown finding {fid}")
        for boundary_id in item["boundary_ids"]:
            if boundary_id not in known_control_boundaries:
                errors.append(f"control_adequacy {ident} references unknown boundary {boundary_id}")
        if item["status"] == "UNDERBUILT" and not item["finding_ids"]:
            errors.append(f"control_adequacy {ident} UNDERBUILT requires finding_ids")
    control_covered_boundaries = {
        bid for item in discipline["control_adequacy"] for bid in item["boundary_ids"]
    }
    required_control_boundaries = {
        bid
        for bid, boundary in known_control_boundaries.items()
        if boundary["kind"] in {"SECURITY", "POLICY_ENFORCEMENT", "VALIDATION", "SOURCE_OF_TRUTH"}
    }
    missing_control_boundaries = required_control_boundaries - control_covered_boundaries
    if missing_control_boundaries:
        errors.append(
            f"control_adequacy must cover every material control boundary: {sorted(missing_control_boundaries)}"
        )

    obligations = audit["audit_obligation_ledger"]
    ob_ids = [item["obligation_id"] for item in obligations]
    if len(ob_ids) != len(set(ob_ids)):
        errors.append("audit_obligation_ledger contains duplicate obligation_id values")
    obs_by_kind_pr: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for item in obligations:
        if item["pr_number"] not in pr_by_num:
            errors.append(
                f"obligation {item['obligation_id']} references unknown PR {item['pr_number']}"
            )
        for eid in item["evidence_ids"]:
            if eid not in emap:
                errors.append(
                    f"obligation {item['obligation_id']} references missing evidence {eid}"
                )
        for fid in item["finding_ids"]:
            if fid not in fmap:
                errors.append(
                    f"obligation {item['obligation_id']} references unknown finding {fid}"
                )
        if item["status"] == "FINDING" and not item["finding_ids"]:
            errors.append(f"obligation {item['obligation_id']} FINDING requires finding_ids")
        obs_by_kind_pr[(item["kind"], item["pr_number"])].append(item)

    # Objective obligations are per affected PR; at minimum every active objective must be represented once.
    objective_subjects = {item["subject"] for item in obligations if item["kind"] == "OBJECTIVE"}
    missing_objective_obligations = active_objectives - objective_subjects
    if missing_objective_obligations:
        errors.append(
            f"audit obligation ledger missing OBJECTIVE obligations: {sorted(missing_objective_obligations)}"
        )
    for num, pr in pr_by_num.items():
        changed_subjects = {item["subject"] for item in obs_by_kind_pr[("CHANGED_SURFACE", num)]}
        expected_changed = {item["path"] for item in pr["changed_files"]}
        if changed_subjects != expected_changed:
            errors.append(
                f"PR {num} CHANGED_SURFACE obligations must exactly match changed_files; missing={sorted(expected_changed - changed_subjects)} extra={sorted(changed_subjects - expected_changed)}"
            )
        review = pr["review_thread_coverage"]
        if isinstance(review["unresolved_discovered"], int):
            observed_threads = len(obs_by_kind_pr[("REVIEW_THREAD", num)])
            if observed_threads != review["unresolved_discovered"]:
                errors.append(
                    f"PR {num} REVIEW_THREAD obligation count {observed_threads} != unresolved_discovered {review['unresolved_discovered']}"
                )

    for item in discipline["architectural_economy"]:
        if not any(
            o["kind"] == "ARCHITECTURAL_GROWTH"
            and o["pr_number"] == item["pr_number"]
            and o["subject"] == item["candidate_id"]
            for o in obligations
        ):
            errors.append(
                f"architectural candidate {item['candidate_id']} lacks ARCHITECTURAL_GROWTH obligation"
            )
    for item in discipline["supersession_closure"]:
        if not any(
            o["kind"] == "SUPERSESSION"
            and o["pr_number"] == item["pr_number"]
            and o["subject"] == item["supersession_id"]
            for o in obligations
        ):
            errors.append(f"supersession {item['supersession_id']} lacks SUPERSESSION obligation")
    for item in discipline["failure_path_coverage"]:
        if not any(
            o["kind"] == "FAILURE_PATH"
            and o["pr_number"] == item["pr_number"]
            and o["subject"] == item["failure_path_id"]
            for o in obligations
        ):
            errors.append(f"failure path {item['failure_path_id']} lacks FAILURE_PATH obligation")
    for item in discipline["test_discrimination"]:
        if not any(
            o["kind"] == "TEST_DISCRIMINATION"
            and o["pr_number"] == item["pr_number"]
            and o["subject"] == item["test_obligation_id"]
            for o in obligations
        ):
            errors.append(
                f"test obligation {item['test_obligation_id']} lacks TEST_DISCRIMINATION obligation"
            )
    for item in discipline["control_adequacy"]:
        if not any(
            o["kind"] == "CONTROL_ADEQUACY"
            and o["pr_number"] == item["pr_number"]
            and o["subject"] == item["control_id"]
            for o in obligations
        ):
            errors.append(
                f"control adequacy {item['control_id']} lacks CONTROL_ADEQUACY obligation"
            )

    failed_by_pr: dict[int, set[str]] = defaultdict(set)
    for item in audit["failed_check_evidence"]:
        failed_by_pr[item["pr_number"]].add(item["check"])
    for num, checks in failed_by_pr.items():
        observed = {item["subject"] for item in obs_by_kind_pr[("CI_FAILURE", num)]}
        if not checks.issubset(observed):
            errors.append(
                f"PR {num} audit obligation ledger missing CI_FAILURE obligations: {sorted(checks - observed)}"
            )

    change_domain = next(
        (
            item
            for item in audit["audit_coverage"]["domain_assessments"]
            if item["domain"] == "CHANGE_DISCIPLINE"
        ),
        None,
    )
    if change_domain is None or change_domain["status"] in {"NOT_APPLICABLE", "UNKNOWN"}:
        errors.append("CHANGE_DISCIPLINE must be explicitly assessed before audit convergence")

    # Inspection inventory: make the actual inspected universe explicit.
    coverage = audit["audit_coverage"]
    artifact_records = coverage["artifact_inventory"]
    artifact_ids = [item["artifact_id"] for item in artifact_records]
    if len(artifact_ids) != len(set(artifact_ids)):
        errors.append("audit_coverage.artifact_inventory contains duplicate artifact_id values")
    changed_inventory: dict[tuple[int, str], int] = defaultdict(int)
    inventory_paths: set[str] = set()
    for item in artifact_records:
        path = item["path"]
        inventory_paths.add(path)
        if not safe_repo_path(path):
            errors.append(f"artifact inventory path is unsafe: {path}")
        for eid in item["evidence_ids"]:
            if eid not in emap:
                errors.append(
                    f"artifact inventory {item['artifact_id']} references missing evidence {eid}"
                )
        if item["revision"] != "UNKNOWN":
            allowed_revisions = {baseline, *heads.values()}
            if item["revision"].lower() not in allowed_revisions:
                errors.append(
                    f"artifact inventory {item['artifact_id']} revision is outside audited baseline/PR heads"
                )
        for num in item["pr_numbers"]:
            if num not in pr_by_num:
                errors.append(
                    f"artifact inventory {item['artifact_id']} references unknown PR {num}"
                )
            if "CHANGED" in item["roles"]:
                changed_inventory[(num, path)] += 1
                if item["revision"] != "UNKNOWN" and item["revision"].lower() != heads.get(num):
                    errors.append(
                        f"artifact inventory changed surface {path} for PR {num} must bind the PR head revision"
                    )
    for num, pr in pr_by_num.items():
        for changed in pr["changed_files"]:
            key = (num, changed["path"])
            if changed_inventory.get(key) != 1:
                errors.append(
                    f"PR {num} changed file {changed['path']} must appear exactly once as CHANGED in artifact_inventory"
                )
    for surface in audit["remediation_surface_index"]:
        for path in (
            surface["authoritative_surfaces"]
            + surface["implementation_surfaces"]
            + surface["coupled_surfaces"]
        ):
            if safe_repo_path(path) and path not in inventory_paths:
                errors.append(
                    f"remediation surface {path} is not represented in artifact_inventory"
                )
    if coverage["status"] == "COMPLETE":
        unknown_inventory = [
            item["artifact_id"] for item in artifact_records if item["revision"] == "UNKNOWN"
        ]
        if unknown_inventory:
            errors.append(
                f"COMPLETE audit coverage cannot contain UNKNOWN artifact revisions: {sorted(unknown_inventory)}"
            )

    # PR readiness inputs must themselves be evidence-backed.
    for num, pr in pr_by_num.items():
        required = pr["required_check_resolution"]
        review = pr["review_thread_coverage"]
        for label, claim in (
            ("required_check_resolution", required),
            ("review_thread_coverage", review),
        ):
            for eid in claim["evidence_ids"]:
                if eid not in emap:
                    errors.append(f"PR {num} {label} references missing evidence {eid}")
            if claim["status"] in {"RESOLVED", "NONE", "COMPLETE"}:
                if not claim["evidence_ids"] or not confirmed_evidence(claim["evidence_ids"], emap):
                    errors.append(
                        f"PR {num} {label} status {claim['status']} requires CONFIRMED evidence"
                    )
        if required["status"] in {"RESOLVED", "NONE"} and not evidence_discriminates(
            required["evidence_ids"], emap, "required_check_identity"
        ):
            errors.append(
                f"PR {num} resolved required-check identity lacks discriminating evidence"
            )
        if review["status"] == "COMPLETE" and not evidence_discriminates(
            review["evidence_ids"], emap, "review_thread_coverage"
        ):
            errors.append(f"PR {num} COMPLETE review coverage lacks discriminating evidence")
        if required["status"] == "NONE" and required.get("checks", []):
            errors.append(f"PR {num} required_check_resolution NONE requires empty checks")
        if required["status"] == "RESOLVED" and not required.get("checks"):
            errors.append(
                f"PR {num} required_check_resolution RESOLVED requires at least one check"
            )
        if review["status"] == "COMPLETE":
            counts = (
                review["unresolved_discovered"],
                review["classified"],
                review["unresolved_remaining"],
            )
            if not all(isinstance(value, int) for value in counts):
                errors.append(f"PR {num} COMPLETE review coverage requires integer counts")
            elif review["unresolved_discovered"] != review["classified"]:
                errors.append(
                    f"PR {num} COMPLETE review coverage requires discovered == classified"
                )

    # Authority resolution and traceability.
    for source in audit["authority_resolution"]["sources"]:
        for eid in source["evidence_ids"]:
            if eid not in emap:
                errors.append(
                    f"authority {source['authority_id']} references missing evidence {eid}"
                )
        if source["kind"] != "USER" and not source["evidence_ids"]:
            errors.append(f"authority {source['authority_id']} requires evidence_ids")
    for conflict in audit["authority_resolution"]["conflicts"]:
        for aid in conflict["authority_ids"]:
            if aid not in amap:
                errors.append(f"authority conflict references unknown authority_id {aid}")
    if audit["authority_resolution"]["status"] == "RESOLVED":
        unresolved_conflicts = [
            conflict["description"]
            for conflict in audit["authority_resolution"]["conflicts"]
            if conflict["status"] in {"UNKNOWN", "BLOCKING"}
        ]
        if unresolved_conflicts:
            errors.append("authority_resolution RESOLVED cannot retain UNKNOWN/BLOCKING conflicts")

    # Audit coverage has one canonical closed-world domain assessment store.
    coverage = audit["audit_coverage"]
    assessments = {item["domain"]: item for item in coverage["domain_assessments"]}
    if len(assessments) != len(coverage["domain_assessments"]):
        errors.append("audit_coverage.domain_assessments contains duplicate domains")
    if set(assessments) != AUDIT_DOMAINS:
        errors.append(
            f"domain_assessments must cover every audit domain exactly once; "
            f"missing={sorted(AUDIT_DOMAINS - set(assessments))} extra={sorted(set(assessments) - AUDIT_DOMAINS)}"
        )
    for domain, item in assessments.items():
        for eid in item["evidence_ids"]:
            if eid not in emap:
                errors.append(f"domain assessment {domain} references missing evidence {eid}")
        for fid in item["finding_ids"]:
            if fid not in fmap:
                errors.append(f"domain assessment {domain} references unknown finding {fid}")
        if item["status"] in {"PASS", "FAIL"}:
            if not item["evidence_ids"] or not confirmed_evidence(item["evidence_ids"], emap):
                errors.append(
                    f"domain assessment {domain} {item['status']} requires CONFIRMED evidence_ids"
                )
            if not evidence_discriminates(item["evidence_ids"], emap, f"audit_domain:{domain}"):
                errors.append(
                    f"domain assessment {domain} {item['status']} lacks audit_domain:{domain} discriminating evidence"
                )
        if item["status"] == "FAIL" and not item["finding_ids"]:
            errors.append(f"domain assessment {domain} FAIL requires finding_ids")
        if item["status"] == "NOT_APPLICABLE" and item["finding_ids"]:
            errors.append(f"domain assessment {domain} NOT_APPLICABLE must not reference findings")
    if coverage["status"] == "COMPLETE":
        unknown_domains = sorted(
            domain for domain, item in assessments.items() if item["status"] == "UNKNOWN"
        )
        if unknown_domains:
            errors.append(
                f"audit_coverage COMPLETE cannot contain UNKNOWN domain assessments: {unknown_domains}"
            )
        blocking_exclusions = [
            item["surface"]
            for item in coverage["excluded_or_inaccessible"]
            if item["impact"] != "NON_BLOCKING"
        ]
        if blocking_exclusions:
            errors.append(
                f"audit_coverage COMPLETE cannot contain blocking exclusions: {sorted(blocking_exclusions)}"
            )

    # Project architecture-policy adapters are explicit and scope-bound.
    adapter_resolution = audit["architecture_policy_adapters"]
    adapters = {item["adapter_id"]: item for item in adapter_resolution["adapters"]}
    if len(adapters) != len(adapter_resolution["adapters"]):
        errors.append("architecture_policy_adapters contains duplicate adapter_id values")
    if adapter_resolution["status"] == "NOT_APPLICABLE" and adapters:
        errors.append("architecture_policy_adapters NOT_APPLICABLE requires an empty adapters list")
    if adapter_resolution["status"] == "RESOLVED" and not adapters:
        errors.append(
            "architecture_policy_adapters with no applicable adapters must use NOT_APPLICABLE"
        )
    if adapter_resolution["status"] == "RESOLVED" and any(
        item["status"] in {"UNKNOWN", "CONFLICTED"} for item in adapters.values()
    ):
        errors.append(
            "architecture_policy_adapters RESOLVED cannot contain UNKNOWN/CONFLICTED adapters"
        )
    for adapter_id, item in adapters.items():
        for aid in item["governing_authority_ids"]:
            if aid not in amap:
                errors.append(
                    f"architecture adapter {adapter_id} references unknown authority {aid}"
                )
        for eid in item["evidence_ids"]:
            if eid not in emap:
                errors.append(
                    f"architecture adapter {adapter_id} references missing evidence {eid}"
                )
        if item["status"] in {"APPLIED", "PARTIALLY_APPLIED"} and (
            not item["governing_authority_ids"]
            or not confirmed_evidence(item["evidence_ids"], emap)
        ):
            errors.append(
                f"architecture adapter {adapter_id} {item['status']} requires governing authority and CONFIRMED evidence"
            )
    adapter_ids = set(adapters)
    for conflict in adapter_resolution["conflicts"]:
        unknown = set(conflict["adapter_ids"]) - adapter_ids
        if unknown:
            errors.append(
                f"architecture adapter conflict references unknown adapters: {sorted(unknown)}"
            )

    # Boundary ownership is canonical rather than an implicit reasoning trail.
    bmap = audit["boundary_map"]
    components = {item["component_id"]: item for item in bmap["components"]}
    if len(components) != len(bmap["components"]):
        errors.append("boundary_map.components contains duplicate component_id values")
    boundaries = {item["boundary_id"]: item for item in bmap["boundaries"]}
    if len(boundaries) != len(bmap["boundaries"]):
        errors.append("boundary_map.boundaries contains duplicate boundary_id values")
    for component_id, item in components.items():
        for aid in item["authority_ids"]:
            if aid not in amap:
                errors.append(
                    f"boundary component {component_id} references unknown authority {aid}"
                )
        for eid in item["evidence_ids"]:
            if eid not in emap:
                errors.append(
                    f"boundary component {component_id} references missing evidence {eid}"
                )
    for boundary_id, item in boundaries.items():
        if item["owner_component_id"] not in components:
            errors.append(
                f"boundary {boundary_id} references unknown owner component {item['owner_component_id']}"
            )
        for aid in item["authority_ids"]:
            if aid not in amap:
                errors.append(f"boundary {boundary_id} references unknown authority {aid}")
        for eid in item["evidence_ids"]:
            if eid not in emap:
                errors.append(f"boundary {boundary_id} references missing evidence {eid}")
    if coverage["status"] == "COMPLETE" and bmap["status"] != "COMPLETE":
        errors.append("COMPLETE audit coverage requires COMPLETE boundary_map")

    # Findings: immutable head bindings, authority, root cause state, evidence reciprocity.
    for fid, finding in fmap.items():
        if finding["repository_revision"].lower() != baseline:
            errors.append(
                f"finding {fid}.repository_revision must equal audited default-branch SHA"
            )
        affected = set(finding["affected_prs"])
        if not affected.issubset(pr_by_num):
            errors.append(
                f"finding {fid} references unbound PRs: {sorted(affected - set(pr_by_num))}"
            )
        bindings = {b["pr_number"]: b["head_sha"].lower() for b in finding["pr_head_bindings"]}
        if len(bindings) != len(finding["pr_head_bindings"]):
            errors.append(f"finding {fid} pr_head_bindings contains duplicate PR bindings")
        if set(bindings) != affected:
            errors.append(f"finding {fid} pr_head_bindings must cover exactly affected_prs")
        for num in affected:
            if bindings.get(num) != heads.get(num):
                errors.append(f"finding {fid} head binding for PR {num} != canonical source head")
        aid = finding["governing_authority"]["authority_id"]
        if aid not in amap:
            errors.append(f"finding {fid} references unknown authority_id {aid}")
        elif finding["governing_authority"]["source"]["path"] != amap[aid]["source"]:
            errors.append(
                f"finding {fid} governing source does not match authority_resolution {aid}"
            )
        semantic_owner = finding["ownership"]["semantic_owner"]
        if semantic_owner != "UNKNOWN" and semantic_owner not in components:
            errors.append(
                f"finding {fid} semantic_owner {semantic_owner!r} is absent from boundary_map.components"
            )
        for eid in finding["origin_evidence_ids"]:
            if eid not in emap:
                errors.append(
                    f"finding {fid} origin_evidence_ids references missing evidence {eid}"
                )
        if finding["origin"] != "UNKNOWN":
            if not confirmed_evidence(finding["origin_evidence_ids"], emap):
                errors.append(
                    f"finding {fid} origin {finding['origin']} requires CONFIRMED origin evidence"
                )
            if not evidence_discriminates(finding["origin_evidence_ids"], emap, "finding_origin"):
                errors.append(
                    f"finding {fid} origin {finding['origin']} lacks finding_origin discriminating evidence"
                )
        basis = finding["merge_blocking_basis"]
        expected_basis = "BLOCKING" if finding["merge_blocking"] else "NON_BLOCKING"
        if basis["status"] != expected_basis:
            errors.append(f"finding {fid} merge_blocking_basis status must be {expected_basis}")
        if basis["status"] == "BLOCKING":
            if not basis.get("authority_id") or basis["authority_id"] not in amap:
                errors.append(f"finding {fid} blocking basis requires a known authority_id")
            for eid in basis["evidence_ids"]:
                if eid not in emap:
                    errors.append(f"finding {fid} blocking basis references missing evidence {eid}")
            if not confirmed_evidence(basis["evidence_ids"], emap):
                errors.append(f"finding {fid} blocking basis requires CONFIRMED evidence")
            if not evidence_discriminates(basis["evidence_ids"], emap, "merge_blocking_basis"):
                errors.append(f"finding {fid} blocking basis lacks merge_blocking_basis evidence")
            if finding["origin"] == "PRE_EXISTING" and not evidence_discriminates(
                basis["evidence_ids"], emap, "pre_existing_blocking_relevance"
            ):
                errors.append(
                    f"pre-existing finding {fid} cannot block merge without pre_existing_blocking_relevance evidence"
                )
        elif basis.get("authority_id") is not None and basis["authority_id"] not in amap:
            errors.append(f"finding {fid} non-blocking basis references unknown authority_id")
        for eid in basis["evidence_ids"]:
            if eid not in emap:
                errors.append(
                    f"finding {fid} merge_blocking_basis references missing evidence {eid}"
                )
        for eid in finding["evidence_ids"]:
            if eid not in emap:
                errors.append(f"finding {fid} references missing evidence {eid}")
            elif fid not in emap[eid]["findings_using_this_evidence"]:
                errors.append(
                    f"finding {fid} -> evidence {eid} missing reciprocal evidence finding reference"
                )
        if finding["confidence"] == "Confirmed" and not confirmed_evidence(
            finding["evidence_ids"], emap
        ):
            errors.append(f"confirmed finding {fid} requires at least one CONFIRMED evidence item")
        if finding["root_cause_state"] == "CONFIRMED" and not confirmed_evidence(
            finding["evidence_ids"], emap
        ):
            errors.append(f"finding {fid} confirmed root cause requires CONFIRMED evidence")
        if finding["finding_class"] == "PERFORMANCE" and finding["confidence"] in {
            "Confirmed",
            "Probable",
        }:
            if not any(
                emap.get(eid, {}).get("evidence_type") == "MEASUREMENT"
                for eid in finding["evidence_ids"]
            ):
                errors.append(
                    f"performance finding {fid} requires MEASUREMENT evidence for {finding['confidence']} confidence"
                )
        guard = finding["ownership"]["mutation_guard"]
        if guard != "NOT_APPLICABLE":
            if guard not in amap:
                errors.append(
                    f"finding {fid} mutation_guard must be NOT_APPLICABLE or a known authority_id"
                )
            elif amap[guard]["kind"] != "MUTATION_GUARD":
                errors.append(
                    f"finding {fid} mutation_guard authority {guard} must have kind MUTATION_GUARD"
                )
        for check in finding["closing_validation"]:
            authority_id = check["authority_id"]
            if authority_id not in amap:
                errors.append(
                    f"finding {fid} closing validation references unknown authority_id {authority_id}"
                )
            for eid in check["evidence_ids"]:
                if eid not in emap:
                    errors.append(
                        f"finding {fid} closing validation references missing evidence {eid}"
                    )
            if not confirmed_evidence(check["evidence_ids"], emap):
                errors.append(
                    f"finding {fid} closing validation requires CONFIRMED provenance evidence"
                )
            if not evidence_discriminates(check["evidence_ids"], emap, "validation_procedure"):
                errors.append(
                    f"finding {fid} closing validation lacks validation_procedure provenance evidence"
                )

    for eid, evidence in emap.items():
        for fid in evidence["findings_using_this_evidence"]:
            if fid not in fmap:
                errors.append(f"evidence {eid} references unknown finding {fid}")
            elif eid not in fmap[fid]["evidence_ids"]:
                errors.append(
                    f"evidence {eid} -> finding {fid} missing reciprocal finding evidence reference"
                )

    # Every finding gets exactly one surface record and dependency node. Implementation paths are proven.
    if set(smap) != set(fmap):
        errors.append(
            "remediation_surface_index finding IDs must exactly equal findings: "
            f"missing={sorted(set(fmap) - set(smap))}, extra={sorted(set(smap) - set(fmap))}"
        )
    if set(gmap) != set(fmap):
        errors.append(
            "finding_dependency_graph IDs must exactly equal findings: "
            f"missing={sorted(set(fmap) - set(gmap))}, extra={sorted(set(gmap) - set(fmap))}"
        )
    for fid, surface in smap.items():
        impl = surface["implementation_surfaces"]
        for path in surface["authoritative_surfaces"] + impl + surface["coupled_surfaces"]:
            if not safe_repo_path(path):
                errors.append(f"finding {fid} has unsafe/non-repository surface path: {path!r}")
        sev = surface["surface_evidence"]
        for record in sev:
            if not safe_repo_path(record["path"]):
                errors.append(f"finding {fid} surface_evidence has unsafe path {record['path']!r}")
            for eid in record["evidence_ids"]:
                if eid not in emap:
                    errors.append(
                        f"finding {fid} surface {record['path']} references missing evidence {eid}"
                    )
        for path in impl:
            records = [r for r in sev if r["path"] == path and r["role"] == "IMPLEMENTATION"]
            if not records:
                errors.append(
                    f"finding {fid} implementation surface {path!r} lacks IMPLEMENTATION surface_evidence"
                )
            elif not any(confirmed_evidence(r["evidence_ids"], emap) for r in records):
                errors.append(
                    f"finding {fid} implementation surface {path!r} lacks CONFIRMED surface evidence"
                )
            elif not any(
                evidence_discriminates(r["evidence_ids"], emap, "implementation_surface")
                for r in records
            ):
                errors.append(
                    f"finding {fid} implementation surface {path!r} lacks evidence that discriminates implementation_surface"
                )

    for fid, node in gmap.items():
        deps = node["depends_on_findings"]
        if fid in deps:
            errors.append(f"finding {fid} cannot depend on itself")
        for dep in deps:
            if dep not in fmap:
                errors.append(f"finding {fid} depends on unknown finding {dep}")
        if set(node["affected_prs"]) != set(fmap[fid]["affected_prs"]):
            errors.append(f"finding {fid} dependency node affected_prs must match finding")

    # Preservation, anti-bypass, failed-check, and regression evidence references.
    for item in audit["preservation_obligations"]:
        if item["authority"] not in amap:
            errors.append(
                f"preservation {item['obligation_id']} references unknown authority_id {item['authority']}"
            )
        for eid in item["evidence_ids"]:
            if eid not in emap:
                errors.append(
                    f"preservation {item['obligation_id']} references missing evidence {eid}"
                )
        if item["status"] in {"PRESERVED", "MIGRATION_AUTHORIZED"} and not confirmed_evidence(
            item["evidence_ids"], emap
        ):
            errors.append(
                f"preservation {item['obligation_id']} status {item['status']} requires CONFIRMED evidence"
            )
        for check in item["validation"]:
            if check["authority_id"] not in amap:
                errors.append(
                    f"preservation {item['obligation_id']} validation references unknown authority_id {check['authority_id']}"
                )
            for eid in check["evidence_ids"]:
                if eid not in emap:
                    errors.append(
                        f"preservation {item['obligation_id']} validation references missing evidence {eid}"
                    )
            if not confirmed_evidence(check["evidence_ids"], emap):
                errors.append(
                    f"preservation {item['obligation_id']} validation requires CONFIRMED provenance evidence"
                )
            if not evidence_discriminates(check["evidence_ids"], emap, "validation_procedure"):
                errors.append(
                    f"preservation {item['obligation_id']} validation lacks validation_procedure provenance evidence"
                )
    bypass_by_pr: dict[int, dict[str, Any]] = {}
    for item in audit["anti_bypass_checks"]:
        num = item["pr_number"]
        if num in bypass_by_pr:
            errors.append(f"duplicate anti_bypass_checks entry for PR {num}")
        bypass_by_pr[num] = item
        kinds = [check["kind"] for check in item["checks"]]
        if set(kinds) != ANTI_BYPASS_KINDS or len(kinds) != len(ANTI_BYPASS_KINDS):
            errors.append(
                f"PR {num} anti-bypass coverage must contain each required kind exactly once"
            )
        for check in item["checks"]:
            for eid in check["evidence_ids"]:
                if eid not in emap:
                    errors.append(
                        f"PR {num} anti-bypass {check['kind']} references missing evidence {eid}"
                    )
            if check["status"] in {"PASS", "FINDING", "NOT_APPLICABLE"} and not confirmed_evidence(
                check["evidence_ids"], emap
            ):
                errors.append(
                    f"PR {num} anti-bypass {check['kind']}={check['status']} requires CONFIRMED evidence"
                )
            if check["status"] in {
                "PASS",
                "FINDING",
                "NOT_APPLICABLE",
            } and not evidence_discriminates(
                check["evidence_ids"], emap, f"anti_bypass:{check['kind']}"
            ):
                errors.append(
                    f"PR {num} anti-bypass {check['kind']} lacks claim-specific discriminating evidence"
                )
    if set(bypass_by_pr) != set(pr_by_num):
        errors.append("anti_bypass_checks must contain exactly one entry for every bound PR")

    for item in audit["failed_check_evidence"]:
        num = item["pr_number"]
        if num not in pr_by_num:
            errors.append(f"failed_check_evidence references unbound PR {num}")
            continue
        if item["source_head_sha"].lower() != heads[num]:
            errors.append(f"failed_check_evidence PR {num} source_head_sha mismatch")
        for eid in item["evidence_ids"]:
            if eid not in emap:
                errors.append(f"failed_check_evidence PR {num} references missing evidence {eid}")
                continue
            evidence = emap[eid]
            if evidence["evidence_type"] not in EXECUTION_EVIDENCE:
                errors.append(
                    f"failed_check_evidence PR {num} evidence {eid} must be execution evidence"
                )
                continue
            if (
                evidence.get("source_head_sha", "UNKNOWN").lower()
                != item["source_head_sha"].lower()
            ):
                errors.append(f"failed_check_evidence PR {num} evidence {eid} source head mismatch")
            if evidence.get("tested_revision_sha") != item["tested_revision_sha"]:
                errors.append(
                    f"failed_check_evidence PR {num} evidence {eid} tested revision mismatch"
                )
            if evidence.get("path_or_check") != item["check"]:
                errors.append(
                    f"failed_check_evidence PR {num} evidence {eid} check identity mismatch"
                )
        for fid in item["affected_finding_ids"]:
            if fid not in fmap:
                errors.append(f"failed_check_evidence PR {num} references missing finding {fid}")
        if not any(
            emap.get(eid, {}).get("validation_result") == "FAIL"
            and emap.get(eid, {}).get("epistemic_state") == "CONFIRMED"
            for eid in item["evidence_ids"]
        ):
            errors.append(
                f"failed_check_evidence PR {num} requires at least one CONFIRMED FAIL execution evidence"
            )

    for item in audit["regression_proof"]:
        fid = item["finding_id"]
        if fid not in fmap:
            errors.append(f"regression_proof references unknown finding {fid}")
        for eid in item["evidence_ids"]:
            if eid not in emap:
                errors.append(f"regression_proof {fid} references missing evidence {eid}")
        if item["pre_remediation_result"] in {"PASS", "FAIL"}:
            matching = [
                emap[eid]
                for eid in item["evidence_ids"]
                if eid in emap
                and emap[eid].get("epistemic_state") == "CONFIRMED"
                and emap[eid].get("validation_result") == item["pre_remediation_result"]
                and emap[eid].get("evidence_type") in EXECUTION_EVIDENCE
            ]
            if not matching:
                errors.append(
                    f"regression_proof {fid} result {item['pre_remediation_result']} lacks matching CONFIRMED execution evidence"
                )

    # Cross-PR evidence is first-class when more than one PR is bound.
    cross = audit["cross_pr_evidence_pack"]
    if len(pr_by_num) == 1:
        if cross["status"] != "NOT_APPLICABLE":
            errors.append("single-PR audit requires cross_pr_evidence_pack.status NOT_APPLICABLE")
        if cross["relationships"] or cross["merge_order"]:
            errors.append(
                "single-PR audit cross_pr_evidence_pack must have empty relationships and merge_order"
            )
    else:
        relation_ids: set[str] = set()
        covered_prs: set[int] = set()
        for relation in cross["relationships"]:
            rid = relation["relationship_id"]
            if rid in relation_ids:
                errors.append(f"duplicate cross-PR relationship_id {rid}")
            relation_ids.add(rid)
            relation_prs = set(relation["prs"])
            covered_prs.update(relation_prs)
            if not relation_prs.issubset(pr_by_num):
                errors.append(f"cross-PR relationship {rid} references unbound PR")
            for eid in relation["evidence_ids"]:
                if eid not in emap:
                    errors.append(f"cross-PR relationship {rid} references missing evidence {eid}")
            if cross["status"] == "COMPLETE" and not evidence_discriminates(
                relation["evidence_ids"], emap, "cross_pr_relationship"
            ):
                errors.append(
                    f"cross-PR relationship {rid} lacks discriminating cross_pr_relationship evidence"
                )
        if cross["status"] == "COMPLETE":
            if set(cross["merge_order"]) != set(pr_by_num):
                errors.append(
                    "COMPLETE cross-PR evidence requires merge_order to contain every bound PR exactly once"
                )
            if covered_prs != set(pr_by_num):
                errors.append(
                    "COMPLETE cross-PR evidence requires every bound PR to appear in a classified relationship"
                )

    # Residual unknowns are explicit and readiness impact is typed.
    unknown_by_id = {item["unknown_id"]: item for item in audit["residual_unknowns"]}
    if len(unknown_by_id) != len(audit["residual_unknowns"]):
        errors.append("residual_unknowns contains duplicate unknown_id values")
    for uid, item in unknown_by_id.items():
        if not set(item["affected_prs"]).issubset(pr_by_num):
            errors.append(f"residual unknown {uid} references unbound PR")

    # Dependency/order analysis feeds both validation and handoff mutation eligibility.
    order, dependency_blocked = dependency_order(audit)
    if set(order) != set(fmap):
        errors.append("dependency order did not cover all findings")

    # Recursive audit passes prove search saturation instead of relying on a single model stopping point.
    passes = audit["audit_passes"]
    numbers = [item["pass_number"] for item in passes]
    if numbers != list(range(1, len(passes) + 1)):
        errors.append("audit_passes pass_number values must be contiguous starting at 1")
    if passes[0]["pass_type"] != "DISCOVERY":
        errors.append("audit_passes first pass must be DISCOVERY")
    if passes[-1]["pass_type"] != "VERIFICATION":
        errors.append("audit_passes final pass must be VERIFICATION")
    all_finding_ids = set(fmap)
    all_obligation_ids = {item["obligation_id"] for item in audit["audit_obligation_ledger"]}
    all_claim_ids = {item["claim_id"] for item in audit["claim_validation_matrix"]}
    all_falsification_ids = {item["falsification_id"] for item in audit["falsification_ledger"]}
    all_closure_ids = {item["closure_id"] for item in audit["deterministic_closure_ledger"]}
    for item in passes:
        for eid in item["evidence_ids"]:
            if eid not in emap:
                errors.append(f"audit pass {item['pass_number']} references missing evidence {eid}")
        unknown_findings = set(item["observed_finding_ids"]) - all_finding_ids
        if unknown_findings:
            errors.append(
                f"audit pass {item['pass_number']} references unknown findings: {sorted(unknown_findings)}"
            )
        unknown_obligations = set(item["observed_obligation_ids"]) - all_obligation_ids
        if unknown_obligations:
            errors.append(
                f"audit pass {item['pass_number']} references unknown obligations: {sorted(unknown_obligations)}"
            )
        unknown_claims = set(item["observed_claim_ids"]) - all_claim_ids
        if unknown_claims:
            errors.append(
                f"audit pass {item['pass_number']} references unknown claims: {sorted(unknown_claims)}"
            )
        unknown_falsifications = set(item["observed_falsification_ids"]) - all_falsification_ids
        if unknown_falsifications:
            errors.append(
                f"audit pass {item['pass_number']} references unknown falsifications: {sorted(unknown_falsifications)}"
            )
        unknown_closures = set(item["observed_closure_ids"]) - all_closure_ids
        if unknown_closures:
            errors.append(
                f"audit pass {item['pass_number']} references unknown deterministic closures: {sorted(unknown_closures)}"
            )
    final_pass = passes[-1]
    if set(final_pass["observed_finding_ids"]) != all_finding_ids:
        errors.append(
            "final VERIFICATION pass must re-observe every retained finding exactly once by ID"
        )
    if set(final_pass["observed_obligation_ids"]) != all_obligation_ids:
        errors.append(
            "final VERIFICATION pass must re-observe every audit obligation exactly once by ID"
        )
    if set(final_pass["observed_claim_ids"]) != all_claim_ids:
        errors.append("final VERIFICATION pass must re-observe every claim exactly once by ID")
    if set(final_pass["observed_falsification_ids"]) != all_falsification_ids:
        errors.append(
            "final VERIFICATION pass must re-observe every falsification probe exactly once by ID"
        )
    if set(final_pass["observed_closure_ids"]) != all_closure_ids:
        errors.append(
            "final VERIFICATION pass must re-observe every deterministic closure exactly once by ID"
        )
    if audit["executive_verdict"]["convergence_status"] == "CONVERGED":
        if final_pass["new_information_count"] != 0:
            errors.append("CONVERGED requires final VERIFICATION pass new_information_count == 0")
        if final_pass["next_pass_objective"] is not None:
            errors.append("CONVERGED requires final VERIFICATION pass next_pass_objective null")

    # Per-PR verdict consistency with concrete blockers and unknowns.
    verdicts = {item["pr_number"]: item for item in audit["per_pr_verdicts"]}
    if len(verdicts) != len(audit["per_pr_verdicts"]):
        errors.append("per_pr_verdicts contains duplicate pr_number values")
    if set(verdicts) != set(pr_by_num):
        errors.append("per_pr_verdicts must contain exactly one verdict for every bound PR")
    for num, verdict in verdicts.items():
        actual_blocking = sorted(
            fid
            for fid, finding in fmap.items()
            if finding["merge_blocking"] and num in finding["affected_prs"]
        )
        actual_unknowns = sorted(
            uid
            for uid, item in unknown_by_id.items()
            if item["blocks_readiness"] and num in item["affected_prs"]
        )
        if sorted(verdict["blocking_finding_ids"]) != actual_blocking:
            errors.append(f"PR {num} blocking_finding_ids != actual merge-blocking findings")
        if sorted(verdict["blocking_unknown_ids"]) != actual_unknowns:
            errors.append(f"PR {num} blocking_unknown_ids != actual blocking residual unknowns")
        validation_ids = verdict["mandatory_validation_evidence_ids"]
        for eid in validation_ids:
            if eid not in emap:
                errors.append(
                    f"PR {num} mandatory_validation_evidence_ids references missing evidence {eid}"
                )
                continue
            evidence = emap[eid]
            if evidence.get("epistemic_state") != "CONFIRMED":
                errors.append(f"PR {num} mandatory validation evidence {eid} must be CONFIRMED")
            if "mandatory_validation" not in evidence.get("properties_discriminated", []):
                errors.append(
                    f"PR {num} mandatory validation evidence {eid} lacks mandatory_validation property"
                )
            if evidence["evidence_type"] in EXECUTION_EVIDENCE:
                if evidence.get("source_head_sha", "UNKNOWN").lower() != heads[num]:
                    errors.append(
                        f"PR {num} mandatory validation evidence {eid} source head mismatch"
                    )
        if verdict["validation_sufficiency"] == "PASS":
            usable = [
                emap[eid]
                for eid in validation_ids
                if eid in emap
                and emap[eid].get("epistemic_state") == "CONFIRMED"
                and "mandatory_validation" in emap[eid].get("properties_discriminated", [])
                and (
                    emap[eid]["evidence_type"] not in EXECUTION_EVIDENCE
                    or emap[eid].get("validation_result") in {"PASS", "FAIL", "NOT_APPLICABLE"}
                )
            ]
            if not usable:
                errors.append(
                    f"PR {num} validation_sufficiency PASS requires usable CONFIRMED mandatory validation evidence"
                )
        readiness = verdict["merge_readiness"]
        if readiness in READY_STATES:
            domain_failures = [
                item for item in coverage["domain_assessments"] if item["status"] == "FAIL"
            ]
            if readiness == "READY" and domain_failures:
                errors.append(f"PR {num} READY requires all audit domains PASS or NOT_APPLICABLE")
            if readiness == "READY_WITH_NON_BLOCKING_NOTES":
                for domain_item in domain_failures:
                    if any(
                        fmap.get(fid, {}).get("merge_blocking")
                        for fid in domain_item["finding_ids"]
                    ):
                        errors.append(
                            f"PR {num} READY_WITH_NON_BLOCKING_NOTES cannot retain merge-blocking domain failures"
                        )
            if actual_blocking or actual_unknowns:
                errors.append(f"PR {num} cannot be {readiness} with blocking findings/unknowns")
            if verdict["validation_sufficiency"] != "PASS":
                errors.append(
                    f"PR {num} cannot be {readiness} unless validation_sufficiency is PASS"
                )
            pr = pr_by_num[num]
            if str(pr["state"]).lower() != "open":
                errors.append(f"PR {num} cannot be {readiness} unless state is open")
            if pr["draft"]:
                errors.append(f"PR {num} cannot be {readiness} while draft=true")
            if str(pr.get("mergeability", "UNKNOWN")).upper() != "MERGEABLE":
                errors.append(f"PR {num} cannot be {readiness} unless mergeability is MERGEABLE")
            required = pr["required_check_resolution"]
            if required["status"] == "UNKNOWN":
                errors.append(
                    f"PR {num} cannot be {readiness} with UNKNOWN required-check identity"
                )
            if required["status"] == "RESOLVED":
                for check_name in required.get("checks", []):
                    passed = any(
                        emap.get(eid, {}).get("evidence_type") == "CI"
                        and emap[eid].get("epistemic_state") == "CONFIRMED"
                        and emap[eid].get("source_head_sha", "UNKNOWN").lower() == heads[num]
                        and emap[eid].get("path_or_check") == check_name
                        and emap[eid].get("validation_result") == "PASS"
                        for eid in validation_ids
                        if eid in emap
                    )
                    if not passed:
                        errors.append(
                            f"PR {num} required check {check_name!r} lacks CONFIRMED PASS evidence in mandatory validation set"
                        )
            if any(
                emap[eid].get("validation_result") != "PASS"
                for eid in validation_ids
                if eid in emap and emap[eid]["evidence_type"] in EXECUTION_EVIDENCE
            ):
                errors.append(
                    f"PR {num} cannot be {readiness} while mandatory validation contains non-PASS result"
                )
            review = pr["review_thread_coverage"]
            if review["status"] != "COMPLETE":
                errors.append(f"PR {num} cannot be {readiness} without COMPLETE review coverage")
            elif review["unresolved_remaining"] != 0:
                errors.append(
                    f"PR {num} cannot be {readiness} with unresolved review threads remaining"
                )
            for preserve in audit["preservation_obligations"]:
                if num in preserve["affected_prs"] and preserve["status"] in {
                    "VIOLATED",
                    "UNPROVEN",
                    "UNKNOWN",
                }:
                    errors.append(
                        f"PR {num} cannot be {readiness} with preservation {preserve['status']}"
                    )
            for check in bypass_by_pr[num]["checks"]:
                if check["status"] in {"FINDING", "UNKNOWN"}:
                    errors.append(
                        f"PR {num} cannot be {readiness} with anti-bypass {check['kind']}={check['status']}"
                    )

    # Change-discipline readiness and convergence are fail-closed.
    discipline_unknown = (
        any(
            item["status"] in {"UNPROVEN", "CONFLICTED"} for item in discipline["objective_closure"]
        )
        or any(
            item["disposition"] == "UNKNOWN"
            for item in discipline["scope_fidelity"]["changed_surfaces"]
        )
        or any(item["disposition"] == "UNKNOWN" for item in discipline["architectural_economy"])
        or any(item["status"] == "UNKNOWN" for item in discipline["supersession_closure"])
        or any(item["status"] == "UNKNOWN" for item in discipline["failure_path_coverage"])
        or any(item["status"] == "UNKNOWN" for item in discipline["test_discrimination"])
        or any(item["status"] == "UNKNOWN" for item in discipline["control_adequacy"])
        or any(item["status"] == "UNKNOWN" for item in obligations)
        or any(item["scope_disposition"] == "UNKNOWN" for item in audit["changed_symbol_ledger"])
        or any(
            item["materiality"] == "MATERIAL" and item["status"] == "UNKNOWN"
            for item in audit["claim_validation_matrix"]
        )
        or any(
            item["result"] == "INCONCLUSIVE"
            and next(
                (c for c in audit["claim_validation_matrix"] if c["claim_id"] == item["claim_id"]),
                {},
            ).get("materiality")
            == "MATERIAL"
            for item in audit["falsification_ledger"]
        )
    )
    discipline_blocker = (
        any(item["status"] != "SATISFIED" for item in discipline["objective_closure"])
        or any(
            item["disposition"] == "SCOPE_EXTENSION"
            for item in discipline["scope_fidelity"]["changed_surfaces"]
        )
        or any(item["disposition"] == "UNJUSTIFIED" for item in discipline["architectural_economy"])
        or any(item["status"] == "RESIDUAL" for item in discipline["supersession_closure"])
        or any(item["status"] in {"WEAK", "ABSENT"} for item in discipline["test_discrimination"])
        or any(item["status"] == "UNDERBUILT" for item in discipline["control_adequacy"])
        or any(item["status"] == "FINDING" for item in obligations)
    )

    combined = audit["combined_merge_readiness"]
    if combined in READY_STATES:
        if any(v["merge_readiness"] not in READY_STATES for v in verdicts.values()):
            errors.append(f"combined {combined} requires every PR individually ready")
        if dependency_blocked:
            errors.append(
                f"combined {combined} cannot contain dependency cycles/blocked ordering: {dependency_blocked}"
            )
        if len(pr_by_num) > 1 and cross["status"] != "COMPLETE":
            errors.append(f"combined {combined} requires COMPLETE cross-PR evidence")
        if any(item["blocks_readiness"] for item in audit["residual_unknowns"]):
            errors.append(f"combined {combined} cannot retain readiness-blocking unknowns")
        if coverage["status"] != "COMPLETE":
            errors.append(f"combined {combined} requires COMPLETE audit coverage")
        if any(
            item["impact"] in {"BLOCKS_READINESS", "BLOCKS_CONVERGENCE"}
            for item in coverage["excluded_or_inaccessible"]
        ):
            errors.append(
                f"combined {combined} cannot retain readiness/convergence-blocking exclusions"
            )
        if audit["authority_resolution"]["status"] != "RESOLVED":
            errors.append(f"combined {combined} requires RESOLVED authority")
        if discipline_blocker or discipline_unknown:
            errors.append(f"combined {combined} requires clean, fully resolved change discipline")

    # Executive verdict cannot outvote deterministic blockers.
    executive = audit["executive_verdict"]
    has_blocker = any(f["merge_blocking"] for f in audit["findings"])
    has_blocking_unknown = any(item["blocks_readiness"] for item in audit["residual_unknowns"])
    has_unresolved_binding = any(
        p["required_check_resolution"]["status"] == "UNKNOWN"
        or p["review_thread_coverage"]["status"] != "COMPLETE"
        for p in audit["pr_bindings"]
    )
    if combined in READY_STATES and executive["readiness_status"] not in {
        "READY",
        "CONDITIONALLY_READY",
    }:
        errors.append(
            "combined ready state requires executive readiness READY or CONDITIONALLY_READY"
        )
    if executive["readiness_status"] in {"READY", "CONDITIONALLY_READY"}:
        if has_blocker:
            errors.append(
                "executive readiness cannot be READY/CONDITIONALLY_READY with merge-blocking findings"
            )
        if has_blocking_unknown or has_unresolved_binding:
            errors.append(
                "executive readiness cannot be READY/CONDITIONALLY_READY with readiness-blocking Unknowns"
            )
        if combined not in READY_STATES:
            errors.append(
                "executive readiness READY/CONDITIONALLY_READY requires combined ready state"
            )
    if executive["convergence_status"] == "CONVERGED":
        if coverage["status"] != "COMPLETE":
            errors.append("CONVERGED requires COMPLETE audit coverage")
        if audit["authority_resolution"]["status"] != "RESOLVED":
            errors.append("CONVERGED requires RESOLVED authority")
        if any(item["status"] == "UNKNOWN" for item in coverage["domain_assessments"]):
            errors.append("CONVERGED cannot retain UNKNOWN audit-domain assessments")
        if audit["architecture_policy_adapters"]["status"] in {"PARTIAL", "UNKNOWN", "CONFLICTED"}:
            errors.append(
                "CONVERGED requires architecture policy adapter applicability to be resolved or NOT_APPLICABLE"
            )
        if audit["boundary_map"]["status"] != "COMPLETE":
            errors.append("CONVERGED requires COMPLETE boundary_map")
        if dependency_blocked:
            errors.append("CONVERGED cannot retain dependency cycles/blocked ordering")
        if any(item["blocks_convergence"] for item in audit["residual_unknowns"]):
            errors.append("CONVERGED cannot retain convergence-blocking residual Unknowns")
        if len(pr_by_num) > 1 and cross["status"] != "COMPLETE":
            errors.append("CONVERGED multi-PR audit requires COMPLETE cross-PR evidence")
        if any(finding["origin"] == "UNKNOWN" for finding in audit["findings"]):
            errors.append("CONVERGED cannot retain UNKNOWN finding origin")
        if discipline_unknown:
            errors.append("CONVERGED cannot retain UNKNOWN change-discipline obligations")
        final_pass = audit["audit_passes"][-1]
        if set(final_pass["observed_claim_ids"]) != {
            item["claim_id"] for item in audit["claim_validation_matrix"]
        }:
            errors.append("CONVERGED final verification must re-observe every claim")
        if set(final_pass["observed_falsification_ids"]) != {
            item["falsification_id"] for item in audit["falsification_ledger"]
        }:
            errors.append("CONVERGED final verification must re-observe every falsification probe")
        if set(final_pass["observed_closure_ids"]) != {
            item["closure_id"] for item in audit["deterministic_closure_ledger"]
        }:
            errors.append(
                "CONVERGED final verification must re-observe every deterministic closure"
            )
    if executive["audit_status"] == "SUCCEEDED" and executive["convergence_status"] != "CONVERGED":
        errors.append("audit_status SUCCEEDED requires convergence_status CONVERGED")

    secret_pattern = contains_secret_material(audit)
    if secret_pattern:
        errors.append(
            f"audit contains high-confidence secret material matching packaging tripwire: {secret_pattern}"
        )
    return errors


def validate_audit(
    audit: dict[str, Any], change_ledgers: dict[int, dict[str, Any]] | None = None
) -> list[str]:
    errors = schema_errors(audit)
    if errors:
        return errors
    return validate_semantics(audit, change_ledgers=change_ledgers)


def dependency_order(audit: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Return deterministic order plus findings blocked by a dependency cycle/unresolvable chain."""
    findings = [f["finding_id"] for f in audit["findings"]]
    nodes = graph_map(audit)
    indegree = {fid: 0 for fid in findings}
    edges: dict[str, set[str]] = defaultdict(set)
    for fid in findings:
        for dep in nodes[fid]["depends_on_findings"]:
            if dep in indegree and fid not in edges[dep]:
                edges[dep].add(fid)
                indegree[fid] += 1
    priority = {
        "ROOT_CAUSE_FIRST": 0,
        "INDEPENDENT": 1,
        "DEPENDENT": 2,
        "VALIDATION_ONLY": 3,
        "UNKNOWN": 4,
    }
    ready = sorted(
        (fid for fid, degree in indegree.items() if degree == 0),
        key=lambda fid: (priority.get(nodes[fid]["remediation_order_class"], 9), fid),
    )
    queue = deque(ready)
    ordered: list[str] = []
    while queue:
        fid = queue.popleft()
        ordered.append(fid)
        newly_ready: list[str] = []
        for nxt in sorted(edges.get(fid, set())):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                newly_ready.append(nxt)
        newly_ready.sort(
            key=lambda item: (priority.get(nodes[item]["remediation_order_class"], 9), item)
        )
        queue.extend(newly_ready)
    blocked = sorted(fid for fid, degree in indegree.items() if degree > 0)
    ordered.extend(blocked)
    return ordered, blocked


def reverse_dependencies(audit: dict[str, Any]) -> dict[str, list[str]]:
    reverse: dict[str, list[str]] = defaultdict(list)
    for node in audit["finding_dependency_graph"]:
        for dep in node["depends_on_findings"]:
            reverse[dep].append(node["finding_id"])
    return {fid: sorted(items) for fid, items in reverse.items()}


def relevant_preservation(audit: dict[str, Any], affected_prs: list[int]) -> list[dict[str, Any]]:
    target = set(affected_prs)
    return [
        item
        for item in audit["preservation_obligations"]
        if target.intersection(item["affected_prs"])
    ]


def implementation_paths_with_confirmed_evidence(
    finding_id: str,
    surface: dict[str, Any],
    emap: dict[str, dict[str, Any]],
) -> list[str]:
    valid: list[str] = []
    for path in surface["implementation_surfaces"]:
        records = [
            record
            for record in surface["surface_evidence"]
            if record["path"] == path and record["role"] == "IMPLEMENTATION"
        ]
        if any(
            confirmed_evidence(record["evidence_ids"], emap)
            and evidence_discriminates(record["evidence_ids"], emap, "implementation_surface")
            for record in records
        ):
            valid.append(path)
    return valid


def make_handoff(audit: dict[str, Any], autoremediate: int = 0) -> dict[str, Any]:
    order, dependency_blocked = dependency_order(audit)
    fmap = finding_map(audit)
    smap = surface_map(audit)
    emap = evidence_map(audit)
    gmap = graph_map(audit)
    reverse = reverse_dependencies(audit)
    work_units: list[dict[str, Any]] = []

    for index, fid in enumerate(order, start=1):
        finding = fmap[fid]
        surface = smap[fid]
        ownership = finding["ownership"]
        owner_class = ownership["remediation_owner_class"]
        proven_paths = implementation_paths_with_confirmed_evidence(fid, surface, emap)
        mutation_reasons: list[str] = []
        if owner_class != MUTATION_OWNER:
            mutation_reasons.append(f"owner_class={owner_class}")
        if finding["confidence"] != "Confirmed":
            mutation_reasons.append(f"confidence={finding['confidence']}")
        if finding["root_cause_state"] != "CONFIRMED":
            mutation_reasons.append(f"root_cause_state={finding['root_cause_state']}")
        if finding["origin"] == "PRE_EXISTING":
            mutation_reasons.append("origin=PRE_EXISTING_requires_separate_authority")
        if finding["origin"] == "UNKNOWN":
            mutation_reasons.append("origin=UNKNOWN")
        guard = ownership["mutation_guard"]
        if guard != "NOT_APPLICABLE" and (
            guard not in authority_map(audit)
            or authority_map(audit)[guard]["kind"] != "MUTATION_GUARD"
        ):
            mutation_reasons.append("mutation_guard_unresolved")
        if fid in dependency_blocked:
            mutation_reasons.append("dependency_order_unresolved")
        if gmap[fid]["remediation_order_class"] == "UNKNOWN":
            mutation_reasons.append("remediation_order_class=UNKNOWN")
        if owner_class == MUTATION_OWNER and not proven_paths:
            mutation_reasons.append("no_confirmed_implementation_surface")
        mutation_eligible = not mutation_reasons

        validation_evidence = []
        for eid in finding["evidence_ids"]:
            evidence = emap[eid]
            if evidence["evidence_type"] in EXECUTION_EVIDENCE:
                validation_evidence.append(
                    {
                        "evidence_id": eid,
                        "type": evidence["evidence_type"],
                        "source_head_sha": evidence.get("source_head_sha", "UNKNOWN"),
                        "tested_revision_sha": evidence.get("tested_revision_sha", "UNKNOWN"),
                        "result": evidence.get("validation_result", "UNKNOWN"),
                        "properties_discriminated": evidence["properties_discriminated"],
                    }
                )

        work_units.append(
            {
                "order": index,
                "finding_id": fid,
                "finding_class": finding["finding_class"],
                "severity": finding["severity"],
                "confidence": finding["confidence"],
                "root_cause_state": finding["root_cause_state"],
                "origin": finding["origin"],
                "origin_evidence_ids": finding["origin_evidence_ids"],
                "merge_blocking": finding["merge_blocking"],
                "merge_blocking_basis": finding["merge_blocking_basis"],
                "affected_prs": finding["affected_prs"],
                "semantic_owner": ownership["semantic_owner"],
                "execution_owner": ownership["execution_owner"],
                "mutation_guard": ownership["mutation_guard"],
                "remediation_owner_class": owner_class,
                "mutation_eligible": mutation_eligible,
                "mutation_block_reasons": mutation_reasons,
                "depends_on_findings": gmap[fid]["depends_on_findings"],
                "blocks_findings": reverse.get(fid, []),
                "governing_authority": finding["governing_authority"],
                "observed_behavior": finding["observed_behavior"],
                "expected_behavior": finding["expected_behavior"],
                "proof_of_mismatch": finding["proof_of_mismatch"],
                "impact": finding["impact"],
                "root_cause": finding["root_cause"],
                "behavioral_closure_condition": finding["behavioral_closure_condition"],
                "closing_validation": finding["closing_validation"],
                "evidence_ids": finding["evidence_ids"],
                "prior_validation_evidence": validation_evidence,
                "authoritative_read_surfaces": surface["authoritative_surfaces"],
                "write_surfaces": proven_paths if mutation_eligible else [],
                "non_authorizing_candidate_surfaces": []
                if mutation_eligible
                else surface["implementation_surfaces"],
                "coupled_read_surfaces": surface["coupled_surfaces"],
                "excluded_false_leads": surface.get("excluded_false_leads", []),
                "preservation_obligations": relevant_preservation(audit, finding["affected_prs"]),
            }
        )

    material_claims = [
        item for item in audit["claim_validation_matrix"] if item["materiality"] == "MATERIAL"
    ]
    adversarial_assurance = {
        "changed_symbol_count": len(audit["changed_symbol_ledger"]),
        "material_claim_count": len(material_claims),
        "supported_material_claim_count": sum(
            1 for item in material_claims if item["status"] == "SUPPORTED"
        ),
        "falsification_probe_count": len(audit["falsification_ledger"]),
        "survived_probe_count": sum(
            1 for item in audit["falsification_ledger"] if item["result"] == "SURVIVED"
        ),
        "falsified_probe_count": sum(
            1 for item in audit["falsification_ledger"] if item["result"] == "FALSIFIED"
        ),
        "inconclusive_probe_count": sum(
            1 for item in audit["falsification_ledger"] if item["result"] == "INCONCLUSIVE"
        ),
        "unknown_material_claim_ids": sorted(
            item["claim_id"] for item in material_claims if item["status"] == "UNKNOWN"
        ),
    }

    return {
        "schema_version": HANDOFF_VERSION,
        "autoremediate": autoremediate,
        "audit_id": audit["audit_id"],
        "repository_binding": audit["repository_binding"],
        "audit_coverage": audit["audit_coverage"],
        "authority_resolution_status": audit["authority_resolution"]["status"],
        "architecture_policy_adapters": audit["architecture_policy_adapters"],
        "boundary_map": audit["boundary_map"],
        "pr_bindings": audit["pr_bindings"],
        "work_order": order,
        "dependency_blocked_findings": dependency_blocked,
        "work_units": work_units,
        "anti_bypass_checks": audit["anti_bypass_checks"],
        "cross_pr_evidence_pack": audit["cross_pr_evidence_pack"],
        "residual_unknowns": audit["residual_unknowns"],
        "adversarial_assurance": adversarial_assurance,
        "minimum_safe_next_action": audit["executive_verdict"]["minimum_safe_next_action"],
        "convergence_requirements": {
            "primary_objective": "RESOLVE_AUDIT_FINDINGS",
            "additional_requirements": [
                "RESOLVE_CURRENT_CI_FAILURES",
                "RESOLVE_ALL_CURRENT_CODE_REVIEW_THREADS",
            ],
            "merge_authorized": False,
            "ci_policy": (
                "After closing audit findings, re-read current CI on each affected PR head. Repair codebase-owned failures within authorized scope, "
                "rerun/poll required checks after publication, and classify truly external CI_PIPELINE/ENVIRONMENT/HUMAN blockers without weakening gates."
            ),
            "review_thread_policy": (
                "Inspect every unresolved current review thread on affected PRs regardless of author. Validate against current code; fix validated code findings, "
                "reply with the disposition, resolve the thread when appropriate, re-query after publication, and finish with zero unresolved threads unless an external blocker is explicitly reported."
            ),
        },
        "publication": {
            "command": "make pr",
            "makefile_authority": "SSOT_MAKEFILE",
            "target_repository_makefile_authorized": False,
            "preserve_pr_identity": True,
            "blocked_status": "PUBLICATION_BLOCKED",
            "merge_authorized": False,
        },
        "authority_note": (
            "This handoff describes evidence and bounded work. The audit phase remains read-only. When a remediation executor is explicitly invoked, "
            "mutation is limited to eligible work units and publication is limited to validated fixes on existing PR branches through the SSOT Makefile make pr path. "
            "PRE_EXISTING findings are report-only unless separately authorized; Merge is explicitly unauthorized by this contract (MERGE=False); deployment, policy change, and scope expansion remain unauthorized unless separately granted."
        ),
    }


def render_audit_md(audit: dict[str, Any]) -> str:
    repo = audit["repository_binding"]["repository"]
    executive = audit["executive_verdict"]
    coverage = audit["audit_coverage"]
    lines = [
        f"# L9 PR Audit: {repo}",
        "",
        f"Audit ID: `{audit['audit_id']}`",
        f"Generated: `{audit['generated_at']}`",
        f"Baseline: `{audit['repository_binding']['audited_default_branch_sha']}`",
        "",
        "## Executive verdict",
        "",
        f"- Audit: `{executive['audit_status']}`",
        f"- Readiness: `{executive['readiness_status']}`",
        f"- Convergence: `{executive['convergence_status']}`",
        f"- Coverage: `{coverage['status']}`",
        f"- Authority resolution: `{audit['authority_resolution']['status']}`",
        f"- Combined merge readiness: `{audit['combined_merge_readiness']}`",
        f"- Summary: {executive['summary']}",
        f"- Minimum safe next action: {executive['minimum_safe_next_action']['action']}",
        "",
        "## Coverage",
        "",
        "Domain assessments: "
        + ", ".join(
            f"{item['domain']}={item['status']}" for item in coverage["domain_assessments"]
        ),
        f"Architecture policy adapters: {audit['architecture_policy_adapters']['status']}",
        f"Boundary map: {audit['boundary_map']['status']} ({len(audit['boundary_map']['components'])} components / {len(audit['boundary_map']['boundaries'])} boundaries)",
    ]
    if coverage["excluded_or_inaccessible"]:
        lines.append("Excluded/inaccessible:")
        for item in coverage["excluded_or_inaccessible"]:
            lines.append(f"- `{item['surface']}` | `{item['impact']}` | {item['reason']}")
    else:
        lines.append("Excluded/inaccessible: none")

    lines += ["", "## Inspection inventory", ""]
    class_counts: dict[str, int] = defaultdict(int)
    for item in coverage["artifact_inventory"]:
        class_counts[item["classification"]] += 1
    lines.append(f"Inventoried artifacts: {len(coverage['artifact_inventory'])}")
    lines.append("Classes: " + ", ".join(f"{k}={class_counts[k]}" for k in sorted(class_counts)))

    lines += ["", "## Recursive audit passes", ""]
    for item in audit["audit_passes"]:
        next_obj = item["next_pass_objective"] or "none"
        lines.append(
            f"- Pass {item['pass_number']} `{item['pass_type']}`: new_information={item['new_information_count']} | "
            f"{item['measurable_result']} | next={next_obj}"
        )

    lines += ["", "## Deterministic red-team assurance", ""]
    material_claims = [
        item for item in audit["claim_validation_matrix"] if item["materiality"] == "MATERIAL"
    ]
    lines.append(f"Changed symbols: {len(audit['changed_symbol_ledger'])}")
    lines.append(f"Material claims: {len(material_claims)}")
    lines.append(
        "Claim states: "
        + ", ".join(
            f"{state}={sum(1 for item in material_claims if item['status'] == state)}"
            for state in ("SUPPORTED", "REFUTED", "NOT_APPLICABLE", "UNKNOWN")
        )
    )
    lines.append(
        "Falsification probes: "
        + ", ".join(
            f"{state}={sum(1 for item in audit['falsification_ledger'] if item['result'] == state)}"
            for state in ("SURVIVED", "FALSIFIED", "INCONCLUSIVE", "NOT_APPLICABLE")
        )
    )

    lines += ["", "## PR verdicts", ""]
    for item in audit["per_pr_verdicts"]:
        lines.append(
            f"- PR #{item['pr_number']}: `{item['merge_readiness']}` | completeness `{item['completeness']}` | "
            f"correctness `{item['correctness']}` | architecture `{item['architecture_alignment']}` | "
            f"validation `{item['validation_sufficiency']}`"
        )

    lines += ["", "## Findings", ""]
    for finding in audit["findings"]:
        ownership = finding["ownership"]
        lines += [
            f"### {finding['finding_id']} - {finding['finding_class']} - {finding['severity']} - "
            f"{'BLOCKING' if finding['merge_blocking'] else 'non-blocking'}",
            "",
            f"Confidence: `{finding['confidence']}` | root cause: `{finding['root_cause_state']}`",
            f"Affected PRs: {', '.join('#' + str(x) for x in finding['affected_prs'])}",
            f"Owner class: `{ownership['remediation_owner_class']}`",
            f"Semantic owner: `{ownership['semantic_owner']}` | execution owner: `{ownership['execution_owner']}`",
            f"Mutation guard: `{ownership['mutation_guard']}`",
            f"Authority: {finding['governing_authority']['rule']} ({finding['governing_authority']['source']['path']})",
            f"Origin: `{finding['origin']}` | blocking basis: `{finding['merge_blocking_basis']['status']}` - {finding['merge_blocking_basis']['rationale']}",
            f"Observed: {finding['observed_behavior']}",
            f"Expected: {finding['expected_behavior']}",
            f"Mismatch: {finding['proof_of_mismatch']}",
            f"Root cause: {finding['root_cause']}",
            f"Impact: {finding['impact']}",
            f"Closure: {finding['behavioral_closure_condition']}",
            f"Evidence IDs: {', '.join(finding['evidence_ids'])}",
            "",
        ]

    lines += ["## Preservation obligations", ""]
    if audit["preservation_obligations"]:
        for item in audit["preservation_obligations"]:
            lines.append(
                f"- `{item['obligation_id']}`: `{item['status']}` | {item['surface']} | {item['behavior_to_preserve']}"
            )
    else:
        lines.append("- None recorded.")

    lines += ["", "## Residual UNKNOWNs", ""]
    if audit["residual_unknowns"]:
        for item in audit["residual_unknowns"]:
            lines.append(
                f"- `{item['unknown_id']}` blocks_readiness=`{item['blocks_readiness']}` | "
                f"{item['description']} | need: {item['evidence_needed']}"
            )
    else:
        lines.append("- None recorded.")

    lines += [
        "",
        "## Evidence",
        "",
        "Canonical exact evidence is in `audit.json` under `shared_evidence_index`. "
        "This projection intentionally avoids duplicating source excerpts or secret material.",
        "",
    ]
    return "\n".join(lines)


def render_read_first(audit: dict[str, Any], handoff: dict[str, Any]) -> str:
    repo = audit["repository_binding"]
    lines = [
        "# Read First",
        "",
        "This bundle is cold-startable, revision-bound audit evidence for downstream remediation.",
        "",
        f"Repository: `{repo['repository']}`",
        f"Audited default branch: `{repo['default_branch']}` at `{repo['audited_default_branch_sha']}`",
        f"Audit coverage: `{audit['audit_coverage']['status']}`",
        f"Audit convergence: `{audit['executive_verdict']['convergence_status']}`",
        f"Autoremediate: `{handoff['autoremediate']}`",
        "",
        "`autoremediate=0` means this audit bundle stops at handoff generation. It does not silently launch remediation.",
        "",
        "## Audited PR source heads",
        "",
    ]
    for pr in audit["pr_bindings"]:
        lines.append(
            f"- PR #{pr['pr_number']}: source head `{pr['head_sha']}` (base `{pr['base_sha']}`)"
        )
    lines += [
        "",
        "## Identity law",
        "",
        "A PR source head is not automatically the revision that a test or CI job executed. "
        "Use each evidence entry's `tested_revision_sha`; never rewrite it as the source head by assumption.",
        "",
        "## Start order",
        "",
        "1. `00_READ_FIRST.md` for identity, freshness, and run control.",
        "2. `remediation-handoff.json` for owner-classified work units and exact scope.",
        "3. `PR_REMEDIATION_CONTRACT.md` for the downstream execution contract.",
        "4. `audit.json` only for cited evidence IDs required by active work units.",
        "5. `change-ledger.json` only to verify deterministic census provenance when needed.",
        "6. `audit.md` only when extra human context is needed.",
        "7. `MANIFEST.json` for bundle integrity when applicable.",
        "",
        "Before editing any PR, independently verify its current source head still equals the audited SHA above. "
        "If it differs or cannot be proven, do not mutate from this audit.",
        "",
        "Only work units marked `mutation_eligible: true` carry a write allowlist.",
        "Publication, when remediation is explicitly invoked, must use `make pr` from the canonical SSOT Makefile surface. "
        "The target repository Makefile is not a publication authority. If the SSOT publication path cannot be proven, return `PUBLICATION_BLOCKED`.",
        "",
    ]
    return "\n".join(lines)


def render_pr_remediation_contract(audit: dict[str, Any], handoff: dict[str, Any]) -> str:
    repo_full = audit["repository_binding"]["repository"]
    owner, name = repo_full.split("/", 1)
    repo_url = f"https://github.com/{repo_full}"
    prs = ", ".join(f"#{p['pr_number']}" for p in audit["pr_bindings"])
    audit_id = json.dumps(audit["audit_id"])
    repo_q = json.dumps(repo_url)
    owner_q = json.dumps(owner)
    name_q = json.dumps(name)
    scope_q = json.dumps(
        f"The PRs and work units defined by audit {audit['audit_id']} for {prs} that are still open and whose current source heads satisfy the pack freshness requirements."
    )
    return f"""# PR Remediation Contract

```yaml
role:
  identity: "Claude Code Fable remediation executor"

run_control:
  autoremediate: {handoff["autoremediate"]}
  default: 0
  law: >
    autoremediate=0 means audit generation stops after producing and validating
    this bundle. No remediation executor is launched automatically. A value of 1
    is valid only when the latest explicit user instruction enabled it for this run.

objective: >
  Apply the remediation defined by the provided audit pack to the affected open
  pull requests in {repo_url}.

  Fix the validated findings in-place on their existing PR branches.

  Do not expand scope, create new architecture, introduce parallel systems,
  duplicate existing responsibility, or turn bounded fixes into redesign work.

target:
  repository:
    url: {repo_q}
    owner: {owner_q}
    name: {name_q}

  PR_scope: {scope_q}

audit_pack:
  source: PROVIDED_TO_AGENT
  authority: PRIMARY_REMEDIATION_SPECIFICATION
  audit_id: {audit_id}

  read_order:
    - "00_READ_FIRST.md"
    - "remediation-handoff.json"
    - "PR_REMEDIATION_CONTRACT.md"
    - "audit.json only for evidence IDs required by an active work unit"
    - "change-ledger.json only when deterministic census provenance must be verified"
    - "audit.md only when additional context is required"
    - "MANIFEST.json for bundle integrity when applicable"

  rules:
    - >
      Reference and execute the pack. Do not duplicate its findings, work units,
      evidence, write surfaces, preservation obligations, or closure conditions
      into a new remediation plan.
    - >
      Treat remediation-handoff.json as the machine-readable work-unit authority.
    - >
      Treat PR_REMEDIATION_CONTRACT.md as the execution contract.
    - >
      Use audit.json only for cited proof required to execute or validate a work
      unit.
    - >
      Do not re-audit the repository from scratch unless a specific unresolved
      condition requires bounded read-only inspection.

authority_order:
  - latest_explicit_user_instruction
  - provided_audit_and_remediation_pack
  - repository_local_governance_and_scoped_instructions
  - authoritative_repository_invariants_contracts_and_owners
  - current_repository_state
  - executable_validation_evidence
  - UNKNOWN

scope:
  authorized:
    - fix_pack_defined_mutation_eligible_findings
    - modify_existing_open_PR_branches_covered_by_the_pack
    - use_pack_defined_write_surfaces
    - perform_pack_required_validation
    - make_required_commits_to_the_existing_PR_branches
    - publish_validated_fixes_to_the_existing_PR_branches_through_SSOT_make_pr

  prohibited:
    - unrelated_refactors
    - speculative_cleanup
    - architecture_expansion
    - new_architecture
    - parallel_systems
    - duplicate_control_planes
    - duplicate_sources_of_truth
    - replacement_subsystems_when_the_existing_owner_can_be_fixed
    - unrelated_feature_work
    - unrelated_dependency_changes
    - changes_outside_pack_authorized_write_surfaces_without_explicit_new_authority

scope_law: >
  Every source mutation must be justified by a mutation-eligible work unit in
  the supplied pack and must remain inside that work unit's authorized write
  surfaces.

  If a correct fix appears to require an unlisted path, do not silently widen
  scope. Classify the work unit as SCOPE_EXTENSION_REQUIRED and preserve the
  evidence.

freshness_gate:
  before_mutation:
    MUST:
      - independently_resolve_each_pack_target_PR_current_source_head
      - verify_the_PR_is_still_open
      - compare_current_source_head_to_the_pack_audited_source_head

  outcomes:
    exact_match_and_open: CONTINUE

    head_changed:
      status: STALE_AUDIT
      action: >
        Do not mutate that PR from stale evidence.

    PR_not_open:
      status: OUT_OF_CURRENT_SCOPE
      action: >
        Do not mutate that PR unless the pack or a stronger current instruction
        explicitly authorizes work on its current state.

    source_head_unprovable:
      status: FRESHNESS_UNPROVEN
      action: >
        Do not mutate that PR.

  identity_rule: >
    Preserve the distinction between PR source-head identity and any
    tested_revision_sha recorded by the pack.

    Never relabel historical validation as having run on a newer revision.

execution:
  work_unit_source: "remediation-handoff.json"

  selection:
    execute_only_when:
      mutation_eligible: true
      freshness_gate: CONTINUE

    non_mutating_classes: >
      Preserve pack classifications such as validation-only, CI-owned,
      environment-owned, external-owned, human-owned, or UNKNOWN unless the pack
      explicitly grants code mutation authority.

  order:
    rule: >
      Follow the pack's dependency and remediation order.

      Resolve root causes before dependent symptoms.

  for_each_work_unit:
    MUST:
      - bind_to_the_exact_current_PR_head
      - read_the_work_unit_and_only_its_needed_evidence
      - inspect_authoritative_and_coupled_surfaces_named_by_the_pack
      - understand_the_behavioral_closure_condition_before_editing
      - modify_only_authorized_write_surfaces
      - preserve_all_pack_defined_preservation_obligations
      - repair_the_root_cause
      - keep_the_existing_architectural_owner
      - avoid_new_abstractions_unless_the_existing_repository_already_requires_them
      - run_the_pack_defined_closing_validation
      - verify_the_behavioral_closure_condition
      - reread_the_final_changed_surface
      - keep_the_fix_minimal_and_complete

implementation_constraints:
  MUST:
    - reuse_existing_repository_architecture
    - reuse_existing_owners
    - reuse_existing_control_planes
    - reuse_existing_contracts
    - reuse_existing_validation_paths
    - preserve_existing_public_behavior_except_where_the_finding_requires_change
    - preserve_fail_closed_or_fail_open_semantics_defined_by_repository_authority
    - preserve_generators_and_sources_of_truth
    - preserve_pack_defined_invariants

  MUST_NOT:
    - create_a_new_framework_to_fix_a_local_defect
    - introduce_a_second_path_beside_the_existing_path
    - introduce_a_second_owner_for_the_same_responsibility
    - add_compatibility_layers_without_pack_or_repository_authority
    - move_responsibility_between_layers_without_requirement
    - redesign_neighboring_components
    - generalize_beyond_the_current_finding
    - replace_a_simple_fix_with_a_new_subsystem
    - weaken_tests_or_gates_to_make_validation_green
    - add_skips_ignores_or_suppressions_to_hide_the_defect
    - bypass_authoritative_generators
    - edit_generated_artifacts_as_competing_authority

minimal_change_rule: >
  Choose the smallest implementation that completely satisfies the pack's
  behavioral closure condition while preserving the existing architecture.

  Minimal does not mean partial.

  Do not leave the root cause reachable through another path merely to reduce
  the diff.

convergence_addenda:
  primary_objective: RESOLVE_AUDIT_FINDINGS

  ci_failures:
    required: true
    rule: >
      In addition to the audit work units, inspect current CI for every affected
      PR after each publication. Diagnose and repair every codebase-owned CI
      failure that is reachable within authorized scope. Do not weaken gates,
      skip tests, suppress scanners, or edit CI-owned infrastructure merely to
      obtain green. Re-run or poll required checks on the repaired head. A
      truly external CI_PIPELINE, ENVIRONMENT, or HUMAN blocker must be
      preserved explicitly in the final result rather than silently ignored.

  code_review_threads:
    required: true
    rule: >
      In addition to the audit work units, inspect every unresolved current code
      review thread on each affected PR regardless of author. Validate each
      comment against current code. Fix validated code findings, reply with the
      disposition for every thread, resolve the thread when appropriate, and
      re-query after every publication because new threads may appear on new
      lines. Completion requires zero unresolved review threads unless a
      specific external blocker is reported.

  merge:
    authorized: false
    rule: >
      Converge the affected PRs to audit-closed, CI-resolved, review-resolved,
      merge-ready state, then stop. Do not merge.

validation:
  authority:
    - pack_defined_closing_validation
    - pack_defined_preservation_validation
    - repository_native_validation_required_for_changed_surfaces

  execution:
    MUST:
      - execute_entries_marked_COMMAND_as_commands
      - observe_entries_marked_CHECK_through_the_named_check_surface
      - treat_entries_marked_MANUAL_as_non_shell_verification
      - rerun_required_validation_after_mutation
      - preserve_exact_command_results_and_exit_codes
      - verify_preservation_obligations_after_the_fix
      - verify_required_CI_on_the_repaired_PR_head_when_available

  result_values:
    - PASS
    - FAIL
    - BLOCKED
    - NOT_EXECUTED
    - UNKNOWN

  hard_rules:
    - "NOT_EXECUTED is not PASS."
    - "A changed file is not proof of closure."
    - "A green unrelated check is not proof of closure."
    - "Historical validation is not validation of the repaired head."
    - "Do not weaken the discriminator that originally exposed the defect."

failure_handling:
  validation_failure:
    action: >
      Diagnose within the current authorized work-unit scope, correct the
      root cause if still within that scope, and rerun the discriminating
      validation.

  scope_extension_required:
    action: >
      Stop only the affected work unit, preserve completed independent work,
      and report the exact additional path and direct-coupling evidence.

  stale_audit:
    action: >
      Do not mutate the affected PR.

  unrelated_pre_existing_failure:
    action: >
      If it is a current CI failure on an affected PR, triage it under the CI
      convergence addendum: repair codebase-owned root causes within authorized
      scope or report the exact external owner/blocker. For unrelated non-CI
      defects outside the audit objective, preserve evidence and do not absorb
      them into remediation.

publication:
  objective: >
    Land completed validated fixes onto the existing affected PR branches so the
    open PRs contain the repaired implementation while preserving PR identity.

  command: "make pr"
  makefile_authority: SSOT_MAKEFILE
  target_repository_makefile_authorized: false

  resolution_rule: >
    Resolve the canonical SSOT Makefile publication surface and its existing
    make pr invocation contract from current operator, session, or governance
    authority. Do not infer publication authority from the target repository.

  MUST:
    - invoke_make_pr_from_the_canonical_SSOT_Makefile_surface
    - keep_changes_on_the_existing_affected_PR_branches
    - preserve_PR_identity
    - publish_only_after_required_local_validation_for_the_work_unit
    - pass_target_repository_and_branch_context_only_through_the_existing_SSOT_interface
    - verify_the_remote_PR_head_after_publication
    - observe_required_checks_on_the_published_repaired_head

  MUST_NOT:
    - invoke_make_pr_from_the_target_repository_Makefile
    - substitute_raw_gh_pr_for_the_SSOT_publication_surface
    - create_parallel_replacement_PRs_for_the_same_pack_work
    - create_parallel_feature_branches_as_a_substitute_for_updating_the_existing_PR
    - force_push_unless_repository_governance_explicitly_requires_and_authorizes_it
    - broaden_the_PR_objective

  unresolved_SSOT_path:
    status: PUBLICATION_BLOCKED
    action: >
      Do not substitute another publication path. Preserve the validated work and
      report the missing SSOT Makefile location or invocation contract required
      to run make pr.

  merge: false
  merge_authority: FORBIDDEN_BY_THIS_CONTRACT

convergence:
  required: true

  sequence:
    - READ_PACK_ENTRYPOINT
    - VERIFY_PACK_INTEGRITY_WHEN_REQUIRED
    - BIND_TARGET_REPOSITORY
    - LOAD_REMEDIATION_HANDOFF
    - RESOLVE_PACK_TARGET_PRS
    - VERIFY_OPEN_STATE_AND_SOURCE_HEAD_FRESHNESS
    - SELECT_MUTATION_ELIGIBLE_WORK_UNITS
    - RESOLVE_DEPENDENCY_ORDER
    - EXECUTE_ROOT_CAUSE_FIXES
    - RUN_WORK_UNIT_CLOSING_VALIDATION
    - VERIFY_PRESERVATION_OBLIGATIONS
    - RUN_REQUIRED_REPOSITORY_NATIVE_VALIDATION
    - VERIFY_NO_SCOPE_EXPANSION
    - VERIFY_NO_NEW_OR_PARALLEL_ARCHITECTURE
    - COMMIT_VALIDATED_FIXES_TO_EXISTING_PR_BRANCHES
    - RESOLVE_SSOT_MAKEFILE_PUBLICATION_SURFACE
    - PUBLISH_WITH_SSOT_MAKE_PR
    - VERIFY_REMOTE_PR_HEADS
    - OBSERVE_REQUIRED_POST_PUBLICATION_CHECKS
    - RESOLVE_CURRENT_CODEBASE_OWNED_CI_FAILURES
    - REQUERY_AND_RESOLVE_ALL_CURRENT_CODE_REVIEW_THREADS
    - REPUBLISH_IF_REQUIRED_WITH_SSOT_MAKE_PR
    - VERIFY_REQUIRED_CHECKS_ON_FINAL_HEAD
    - VERIFY_ZERO_UNRESOLVED_REVIEW_THREADS_OR_EXPLICIT_EXTERNAL_BLOCKER
    - RECHECK_ALL_MUTATION_ELIGIBLE_FINDINGS
    - STOP_BEFORE_MERGE
    - EMIT_FINAL_REMEDIATION_RESULT

  terminal_rule: >
    Complete only when every freshness-valid, mutation-eligible finding in the
    supplied pack has been repaired at its root cause, all pack-defined closure
    and preservation conditions have been satisfied, required validation has
    been executed against the repaired state, the fixes have been published to
    the existing affected open PR branches through the canonical SSOT Makefile
    make pr path, and no scope expansion, new architecture, parallel system,
    duplicate authority, or unrelated change has been introduced; every
    codebase-owned CI failure on the affected PRs has been resolved, all current
    code review threads have been dispositioned and resolved unless an explicit
    external blocker remains, and the executor stops before merge (MERGE=False).

deliverables:
  MUST_include:
    - target_repository
    - affected_PRs
    - initial_source_head_per_PR
    - final_source_head_per_PR
    - work_units_closed
    - work_units_blocked
    - files_changed_per_work_unit
    - commits_created
    - publication_result_per_PR
    - behavioral_closure_result_per_work_unit
    - preservation_obligation_results
    - validation_results
    - post_publication_check_results
    - final_CI_failure_disposition_per_PR
    - final_unresolved_review_thread_count_per_PR
    - merge_attempted_false
    - scope_extension_required_items
    - stale_audit_items
    - residual_UNKNOWNs
    - final_remediation_status

final_remediation_status_values:
  - COMPLETE
  - COMPLETE_WITH_EXTERNAL_BLOCKERS
  - PARTIALLY_REMEDIATED
  - STALE_AUDIT
  - BLOCKED
  - UNKNOWN

stop_conditions:
  - stop_if_the_pack_cannot_be_read
  - stop_affected_PR_if_its_current_source_head_does_not_match_the_audited_binding
  - stop_affected_PR_if_its_source_head_cannot_be_proven
  - do_not_mutate_a_PR_that_is_no_longer_open_without_stronger_authority
  - do_not_mutate_work_units_without_mutation_eligible_true
  - do_not_edit_outside_pack_authorized_write_surfaces
  - do_not_expand_scope
  - do_not_create_new_architecture
  - do_not_create_parallel_systems
  - do_not_create_duplicate_authority
  - do_not_reaudit_the_entire_repository_without_specific_need
  - do_not_weaken_tests_or_gates
  - do_not_fabricate_validation_or_closure
  - do_not_claim_historical_validation_ran_on_the_repaired_head
  - do_not_publish_without_resolving_the_canonical_SSOT_Makefile_make_pr_surface
  - do_not_merge
```
"""


def verify_zip(zip_path: Path) -> list[str]:
    errors: list[str] = []
    required = {
        "00_READ_FIRST.md",
        "audit.json",
        "audit.md",
        "change-ledger.json",
        "remediation-handoff.json",
        "PR_REMEDIATION_CONTRACT.md",
        "MANIFEST.json",
    }
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        if names != required:
            errors.append(
                f"bundle file set mismatch: missing={sorted(required - names)}, extra={sorted(names - required)}"
            )
            return errors
        try:
            manifest = json.loads(zf.read("MANIFEST.json").decode("utf-8"))
            audit = json.loads(zf.read("audit.json").decode("utf-8"))
            ledger_set_doc = json.loads(zf.read("change-ledger.json").decode("utf-8"))
            handoff = json.loads(zf.read("remediation-handoff.json").decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return [f"bundle JSON decode failed: {exc}"]

        errors.extend(validate_against_schema(manifest, manifest_schema_path(), "manifest"))
        try:
            bundled_ledgers = load_change_ledger_set(ledger_set_doc)
        except ValueError as exc:
            return [f"change-ledger decode failed: {exc}"]
        errors.extend(validate_audit(audit, change_ledgers=bundled_ledgers))
        errors.extend(validate_against_schema(handoff, handoff_schema_path(), "handoff"))
        if manifest.get("schema_version") != MANIFEST_VERSION:
            errors.append("bundle manifest schema_version mismatch")
        if manifest.get("builder_version") != BUILDER_VERSION:
            errors.append("bundle manifest builder_version mismatch")
        if manifest.get("builder_sha256") != sha256(builder_path()):
            errors.append("bundle manifest builder_sha256 mismatch")
        expected_handoff = make_handoff(audit, manifest.get("autoremediate", 0))
        if handoff != expected_handoff:
            errors.append("derived remediation-handoff.json does not match canonical audit")
        expected_projections = {
            "audit.md": render_audit_md(audit).encode("utf-8"),
            "00_READ_FIRST.md": render_read_first(audit, expected_handoff).encode("utf-8"),
            "PR_REMEDIATION_CONTRACT.md": render_pr_remediation_contract(
                audit, expected_handoff
            ).encode("utf-8"),
        }
        for name, expected_bytes in expected_projections.items():
            if zf.read(name) != expected_bytes:
                errors.append(f"derived projection mismatch: {name}")
        observed_audit_sha = sha256_bytes(zf.read("audit.json"))
        if manifest.get("canonical_audit_sha256") != observed_audit_sha:
            errors.append("manifest canonical_audit_sha256 mismatch")
        observed_ledger_sha = sha256_bytes(zf.read("change-ledger.json"))
        if manifest.get("change_ledger_set_sha256") != observed_ledger_sha:
            errors.append("manifest change_ledger_set_sha256 mismatch")
        for name in required - {"MANIFEST.json"}:
            record = manifest.get("files", {}).get(name)
            if not isinstance(record, dict):
                errors.append(f"manifest missing file record: {name}")
                continue
            observed = sha256_bytes(zf.read(name))
            if observed != record.get("sha256"):
                errors.append(f"manifest hash mismatch: {name}")
            if isinstance(record.get("bytes"), int) and record.get("bytes") != len(zf.read(name)):
                errors.append(f"manifest byte-count mismatch: {name}")
        expected_schema_digests = {
            "audit_schema_sha256": sha256(schema_path()),
            "handoff_schema_sha256": sha256(handoff_schema_path()),
            "manifest_schema_sha256": sha256(manifest_schema_path()),
        }
        for key, expected in expected_schema_digests.items():
            if manifest.get(key) != expected:
                errors.append(f"manifest {key} mismatch")
    return errors


def _filename_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return token or "unknown"


def unique_bundle_filename(audit: dict[str, Any]) -> str:
    repo_name = audit["repository_binding"]["repository"].split("/", 1)[1]
    pr_numbers = [str(item["pr_number"]) for item in audit["pr_bindings"]]
    if len(pr_numbers) == 1:
        scope_tag = f"pr-{pr_numbers[0]}"
    elif len(pr_numbers) <= 6:
        scope_tag = "prs-" + "-".join(pr_numbers)
    else:
        scope_tag = "prs-" + "-".join(pr_numbers[:6]) + f"-plus-{len(pr_numbers) - 6}"
    build_tag = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    unique_tag = uuid4().hex[:8]
    return (
        f"l9-pr-audit__{_filename_token(repo_name)}__{_filename_token(scope_tag)}__"
        f"{build_tag}__{unique_tag}.zip"
    )


def build_bundle(
    audit_path: Path,
    output_dir: Path,
    change_ledgers: dict[int, dict[str, Any]],
    autoremediate: int = 0,
) -> Path:
    audit = load_json(audit_path)
    errors = validate_audit(audit, change_ledgers=change_ledgers)
    if errors:
        raise ValueError("audit validation failed:\n- " + "\n- ".join(errors))

    output_dir.mkdir(parents=True, exist_ok=True)
    stage = output_dir / "l9-pr-audit-output"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    canonical = stage / "audit.json"
    canonical.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ledger_set_path = stage / "change-ledger.json"
    ledger_set_path.write_text(
        json.dumps(change_ledger_set(change_ledgers), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    handoff = make_handoff(audit, autoremediate)
    handoff_errors = validate_against_schema(handoff, handoff_schema_path(), "handoff")
    if handoff_errors:
        raise ValueError("derived handoff validation failed:\n- " + "\n- ".join(handoff_errors))
    (stage / "remediation-handoff.json").write_text(
        json.dumps(handoff, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (stage / "audit.md").write_text(render_audit_md(audit), encoding="utf-8")
    (stage / "00_READ_FIRST.md").write_text(render_read_first(audit, handoff), encoding="utf-8")
    (stage / "PR_REMEDIATION_CONTRACT.md").write_text(
        render_pr_remediation_contract(audit, handoff), encoding="utf-8"
    )

    files = [
        stage / name
        for name in [
            "00_READ_FIRST.md",
            "audit.json",
            "audit.md",
            "change-ledger.json",
            "remediation-handoff.json",
            "PR_REMEDIATION_CONTRACT.md",
        ]
    ]
    manifest = {
        "schema_version": MANIFEST_VERSION,
        "builder_version": BUILDER_VERSION,
        "builder_sha256": sha256(builder_path()),
        "autoremediate": autoremediate,
        "audit_id": audit["audit_id"],
        "canonical_audit_sha256": sha256(canonical),
        "change_ledger_set_sha256": sha256(ledger_set_path),
        "audit_schema_sha256": sha256(schema_path()),
        "handoff_schema_sha256": sha256(handoff_schema_path()),
        "manifest_schema_sha256": sha256(manifest_schema_path()),
        "repository_binding": audit["repository_binding"],
        "pr_bindings": [
            {
                "pr_number": p["pr_number"],
                "base_sha": p["base_sha"],
                "source_head_sha": p["head_sha"],
            }
            for p in audit["pr_bindings"]
        ],
        "files": {
            path.name: {"sha256": sha256(path), "bytes": path.stat().st_size} for path in files
        },
    }
    manifest_errors = validate_against_schema(manifest, manifest_schema_path(), "manifest")
    if manifest_errors:
        raise ValueError("derived manifest validation failed:\n- " + "\n- ".join(manifest_errors))
    (stage / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    secret_pattern = contains_secret_material(
        {path.name: path.read_text(encoding="utf-8") for path in stage.iterdir() if path.is_file()}
    )
    if secret_pattern:
        raise ValueError(
            f"derived bundle contains high-confidence secret material: {secret_pattern}"
        )

    zip_path = output_dir / unique_bundle_filename(audit)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(stage.iterdir()):
            if path.is_file():
                zf.write(path, arcname=path.name)
    zip_errors = verify_zip(zip_path)
    if zip_errors:
        raise ValueError("bundle verification failed:\n- " + "\n- ".join(zip_errors))
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--verify-bundle", type=Path)
    parser.add_argument("--change-ledger", type=Path, action="append", default=[])
    parser.add_argument("--autoremediate", type=int, choices=(0, 1), default=0)
    args = parser.parse_args()

    try:
        if args.verify_bundle:
            errors = verify_zip(args.verify_bundle)
            if errors:
                for error in errors:
                    print(f"FAIL: {error}", file=sys.stderr)
                return 1
            print("PASS: bundle verification passed")
            return 0
        if not args.audit:
            parser.error("--audit is required unless --verify-bundle is used")
        if not args.change_ledger:
            parser.error("at least one --change-ledger is required unless --verify-bundle is used")
        change_ledgers = load_change_ledger_paths(args.change_ledger)
        audit = load_json(args.audit)
        errors = validate_audit(audit, change_ledgers=change_ledgers)
        if errors:
            for error in errors:
                print(f"FAIL: {error}", file=sys.stderr)
            return 1
        if args.validate_only:
            print("PASS: canonical audit validation passed")
            return 0
        path = build_bundle(
            args.audit,
            args.output_dir,
            change_ledgers=change_ledgers,
            autoremediate=args.autoremediate,
        )
        print(path)
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
