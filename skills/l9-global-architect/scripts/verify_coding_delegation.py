#!/usr/bin/env python3
"""Execute GAR's coding-delegation checks (GAR-DELEG-001..010).

Policy owner: contracts/OUTCOME_OWNERSHIP.yaml#coding_delegation_policy. GAR is the issuer and
acceptor of an implementation delegation; its sibling twin l9-coding-agent owns the execution
contract, its schema and validator, and the execution receipt. This program defines none of the
sibling's semantics. On every call it resolves them live through the sibling's
runtime/MANIFEST.yaml, using the resolution keys GAR's own policy declares, runs the sibling's
validator and schemas for sibling-owned checks, and adds only GAR's issuance and acceptance
checks on top.

Subcommands:
  resolve    resolve the sibling contract current at this moment (GAR-DELEG-010)
  issue      validate and freeze one delegation payload (GAR-DELEG-001, 002, 003, 008)
  accept     independently verify a returned result against the frozen contract
             (GAR-DELEG-003, 004, 005, 006, 007)
  carriage   observe whether an integrated runtime carries the payload verbatim (GAR-DELEG-009)
  self-test  run every GAR-DELEG check, positive and negative, on built-in fixtures

Every command prints one JSON document. Exit 0 means RESOLVED, CONTRACT_FROZEN, NONE, ACCEPTED,
CARRIED_VERBATIM, or a passing self-test; exit 1 means BLOCKED, REJECTED, NOT_CARRIABLE, or
Unknown; exit 2 is a usage error. Unknown never passes.
"""

from __future__ import annotations

import argparse
import copy
import fnmatch
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema
import yaml

sys.dont_write_bytecode = True

PACK = Path(__file__).resolve().parents[1]
REPO = PACK.parents[1]
POLICY_FILE = "contracts/OUTCOME_OWNERSHIP.yaml"
MANIFEST_FILE = "runtime/MANIFEST.yaml"
SATISFIED, VIOLATED, UNKNOWN = "SATISFIED", "VIOLATED", "UNKNOWN"
PASSING_VALIDATION = {"Passed", "NotApplicable"}
PASSING_CRITERION = {"Satisfied", "Passed", "SATISFIED"}
BARE_FLAGS = {"", "1", "true", "yes", "y", "on"}


# --------------------------------------------------------------------------- helpers


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def walk(node: Any, dotted: str) -> Any:
    for key in dotted.split("."):
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False
    )


def git_out(cwd: Path, *args: str) -> str | None:
    proc = git(cwd, *args)
    return proc.stdout.strip() if proc.returncode == 0 else None


def same_revision(a: str | None, b: str | None) -> bool:
    if not a or not b or min(len(a), len(b)) < 7:
        return False
    return a.startswith(b) or b.startswith(a)


def norm(text: Any) -> str:
    return " ".join(str(text).split()).casefold()


def check(check_id: str, name: str, result: str, detail: str) -> dict[str, str]:
    return {"check_id": check_id, "check": name, "result": result, "detail": detail}


# --------------------------------------------------------------------------- resolve


def resolve(gar_root: Path = PACK, sibling_root: Path | None = None) -> dict[str, Any]:
    """Resolve the sibling's current contract, schemas, and validator (GAR-DELEG-010)."""
    policy = walk(load(gar_root / POLICY_FILE), "coding_delegation_policy.payload.resolution")
    twin = walk(load(gar_root / MANIFEST_FILE), "twin_relation")
    if not isinstance(policy, dict) or not isinstance(twin, dict):
        return blocked("GAR resolution keys or twin_relation are absent from GAR's own owners")
    if sibling_root is None:
        sibling_root = (gar_root.parents[1] / str(twin["sibling_manifest"])).parents[1]
    manifest_path = sibling_root / MANIFEST_FILE
    if not manifest_path.is_file():
        return blocked(f"sibling manifest missing: {manifest_path}")
    manifest = load(manifest_path)
    owner = walk(manifest, str(policy["contract"]))
    contract_group = walk(manifest, str(policy["contract_schema_and_validator"])) or []
    receipt_group = walk(manifest, str(policy["receipt_schema"])) or []
    schema = next((x for x in contract_group if str(x).endswith(".json")), None)
    validator = next((x for x in contract_group if str(x).endswith(".py")), None)
    receipt = next((x for x in receipt_group if str(x).endswith(".json")), None)
    refs = {"contract": owner, "schema": schema, "validator": validator, "receipt": receipt}
    for role, ref in refs.items():
        if not ref or not (sibling_root / str(ref)).is_file():
            return blocked(f"sibling {role} unresolved: {ref!r} under {sibling_root}")
    contract_doc = load(sibling_root / str(owner))
    contract_meta = contract_doc.get("contract") if isinstance(contract_doc, dict) else None
    if not isinstance(contract_meta, dict) or not contract_meta.get("id"):
        return blocked(f"sibling contract has no contract.id: {owner}")
    try:
        jsonschema.Draft202012Validator.check_schema(load(sibling_root / str(schema)))
        jsonschema.Draft202012Validator.check_schema(load(sibling_root / str(receipt)))
    except jsonschema.SchemaError as exc:
        return blocked(f"sibling schema is invalid: {exc.message}")
    record = {
        "sibling": twin.get("sibling"),
        "sibling_manifest_ref": str(manifest_path),
        "sibling_pack_version": walk(manifest, "manifest.version"),
        "sibling_source_revision": git_out(sibling_root, "rev-parse", "HEAD"),
        "contract_owner_path": str(owner),
        "contract_id": contract_meta.get("id"),
        "contract_version": contract_meta.get("version"),
        "contract_digest": digest(sibling_root / str(owner)),
        "contract_schema_ref": str(schema),
        "contract_schema_digest": digest(sibling_root / str(schema)),
        "contract_validator_ref": str(validator),
        "receipt_schema_ref": str(receipt),
        "receipt_schema_digest": digest(sibling_root / str(receipt)),
        "resolved_at": now(),
        "evidence_refs": [f"resolved through {manifest_path} by {POLICY_FILE} keys"],
    }
    return {"status": "RESOLVED", "sibling_root": str(sibling_root), "sibling_resolution": record}


def blocked(reason: str, code: str = "MATERIAL_ASSUMPTION_UNRESOLVED") -> dict[str, Any]:
    return {"status": "BLOCKED", "reason_code": code, "reason": reason}


# --------------------------------------------------------------------------- issue


def issue(
    contract_path: Path,
    *,
    handoff_kind: str = "implementation",
    target_revision: str | None = None,
    competing: list[str] | None = None,
    prior: dict[str, Any] | None = None,
    reauthorization: str | None = None,
    sibling_root: Path | None = None,
) -> dict[str, Any]:
    """Validate and freeze one delegation payload against the sibling contract resolved now."""
    if handoff_kind != "implementation":
        return {
            "status": "NONE",
            "reason": f"{handoff_kind} handoff keeps its existing owner (GAR-DELEG-008)",
        }
    if competing:
        return blocked(
            f"competing semantic coding instructions present: {competing}", "PLAN_NOT_READY"
        )
    if prior is not None and contract_path.is_file():
        if prior.get("frozen_contract_digest") == digest(contract_path):
            return rework_reissue(prior)
    resolution = resolve(sibling_root=sibling_root)
    if resolution["status"] != "RESOLVED":
        return resolution
    root = Path(resolution["sibling_root"])
    sib = resolution["sibling_resolution"]
    if not contract_path.is_file():
        return blocked(f"delegation payload not found: {contract_path}", "PLAN_NOT_READY")
    proc = subprocess.run(
        [sys.executable, "-B", str(root / sib["contract_validator_ref"]), str(contract_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    validator_report = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0:
        return blocked(
            f"sibling validator rejected the payload: {validator_report}", "PLAN_NOT_READY"
        )
    payload = load(contract_path)
    errors = sorted(
        e.message
        for e in jsonschema.Draft202012Validator(
            load(root / sib["contract_schema_ref"])
        ).iter_errors(payload)
    )
    if errors:
        return blocked(f"payload fails the sibling schema: {errors}", "PLAN_NOT_READY")
    gaps = issuance_gaps(payload, target_revision)
    if gaps:
        return {"status": "BLOCKED", "reason_code": gaps[0][0], "reason": [g[1] for g in gaps]}
    frozen_digest = digest(contract_path)
    reauth_refs: list[str] = []
    if prior is not None:
        prior_digest = prior.get("frozen_contract_digest")
        reauth_refs = list(walk(prior, "rework.reauthorization_refs") or [])
        if prior_digest and prior_digest != frozen_digest:
            if str(reauthorization or "").strip().lower() in BARE_FLAGS:
                return blocked(
                    "objective, scope, or architecture changed after freeze without a recorded "
                    "reauthorization (GAR-DELEG-003)",
                    "SCOPE_EXPANSION_UNJUSTIFIED",
                )
            reauth_refs.append(str(reauthorization))
    record = {
        "status": "CONTRACT_FROZEN",
        "sibling_resolution": sib,
        "sibling_root": str(root),
        "frozen_contract_ref": str(contract_path.resolve()),
        "frozen_contract_id": payload.get("contract_id"),
        "frozen_contract_digest": frozen_digest,
        "frozen_target_revision": walk(payload, "target.base_revision"),
        "schema_validation_ref": f"{sib['contract_validator_ref']}: {validator_report}",
        "competing_instruction_refs": [],
        "issued_at": now(),
        "result": {
            "diff_ref": None,
            "implementation_report_ref": None,
            "execution_receipt_ref": None,
            "delivered_revision": None,
            "returned_at": None,
        },
        "verification": {"status": "NOT_EVALUATED", "discrepancy_refs": []},
        "rework": {"count": 0, "same_frozen_contract": True, "reauthorization_refs": reauth_refs},
        "transport": {"mode": None, "owner": None, "carriage_status": "NOT_EVALUATED"},
        "evidence_refs": [str(Path(__file__).resolve())],
    }
    return record


def rework_reissue(prior: dict[str, Any]) -> dict[str, Any]:
    """Rework on an unchanged payload keeps the issuance-time sibling resolution (RS-038).

    The sibling may have published a newer contract since the freeze; that newer contract
    applies only to a new freeze after an authorized material change, never to rework.
    """
    record = copy.deepcopy(prior)
    rework = record.setdefault("rework", {})
    rework["count"] = int(rework.get("count") or 0) + 1
    rework["same_frozen_contract"] = True
    rework.setdefault("reauthorization_refs", [])
    record["status"] = "CONTRACT_FROZEN"
    record["reissued_at"] = now()
    record["result"] = {
        "diff_ref": None,
        "implementation_report_ref": None,
        "execution_receipt_ref": None,
        "delivered_revision": None,
        "returned_at": None,
    }
    record["verification"] = {"status": "NOT_EVALUATED", "discrepancy_refs": []}
    return record


def issuance_gaps(payload: Any, target_revision: str | None) -> list[tuple[str, str]]:
    """GAR blocking conditions that are mechanically decidable on the payload."""
    if not isinstance(payload, dict):
        return [("PLAN_NOT_READY", "payload is not a mapping")]
    gaps: list[tuple[str, str]] = []
    base = walk(payload, "target.base_revision")
    if not walk(payload, "target.repository_or_artifact") or not base:
        gaps.append(("TARGET_BINDING_UNRESOLVED", "exact target or base revision is unknown"))
    elif target_revision and not same_revision(str(base), target_revision):
        gaps.append(
            ("TARGET_BINDING_UNRESOLVED", f"base revision {base} != bound target {target_revision}")
        )
    if not payload.get("authority_refs"):
        gaps.append(("MUTATION_AUTHORITY_UNRESOLVED", "authority_refs are empty"))
    if not payload.get("locked_invariants"):
        gaps.append(("MATERIAL_ASSUMPTION_UNRESOLVED", "locked invariants are unresolved"))
    if not payload.get("in_scope") or not payload.get("modification_scope"):
        gaps.append(("PLAN_NOT_READY", "in_scope or modification_scope is unknown"))
    return gaps


# --------------------------------------------------------------------------- accept


def diff_paths(diff_text: str) -> set[str]:
    paths: set[str] = set()
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split(" ")
            for token in parts[2:4]:
                if token[:2] in ("a/", "b/"):
                    paths.add(token[2:])
    return paths


def in_scope(path: str, scope: list[str]) -> bool:
    for entry in scope:
        entry = str(entry).strip()
        if path == entry or fnmatch.fnmatch(path, entry):
            return True
        if entry.endswith("/") and path.startswith(entry):
            return True
    return False


def covered(items: list[Any], index: int, text: str, text_key: str, index_key: str) -> Any:
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get(index_key) == index or norm(item.get(text_key, "")) == norm(text):
            return item
    return None


def receipt_schema(record: dict[str, Any]) -> tuple[Any, str]:
    """The receipt schema recorded at issuance, by digest, never a newer one."""
    sib = record.get("sibling_resolution") or {}
    root = Path(str(record.get("sibling_root", "")))
    ref, want = sib.get("receipt_schema_ref"), sib.get("receipt_schema_digest")
    if not ref or not want:
        return None, "issuance record has no receipt schema resolution"
    current = root / str(ref)
    if current.is_file() and digest(current) == want:
        return load(current), f"{current} ({want})"
    rev = sib.get("sibling_source_revision")
    top = git_out(root, "rev-parse", "--show-toplevel")
    if rev and top:
        rel = current.resolve().relative_to(Path(top).resolve()).as_posix()
        proc = subprocess.run(
            ["git", "-C", top, "show", f"{rev}:{rel}"], capture_output=True, check=False
        )
        if proc.returncode == 0 and digest_bytes(proc.stdout) == want:
            return json.loads(proc.stdout), f"{rev}:{rel} ({want})"
    return None, f"receipt schema {ref} with digest {want} is not retrievable"


def accept(
    record: dict[str, Any],
    *,
    contract_path: Path,
    diff_path: Path,
    report_path: Path,
    receipt_path: Path,
    delivered_revision: str,
    repo: Path | None,
    adjudication: dict[str, Any] | None,
) -> dict[str, Any]:
    """GAR's independent acceptance (contracts/OUTCOME_OWNERSHIP.yaml#acceptance)."""
    checks: list[dict[str, str]] = []
    present = {
        "diff": diff_path.is_file() and "diff --git " in diff_path.read_text(encoding="utf-8"),
        "implementation_report": report_path.is_file() and report_path.stat().st_size > 0,
        "execution_receipt": receipt_path.is_file() and receipt_path.stat().st_size > 0,
    }
    missing = [name for name, ok in present.items() if not ok]
    checks.append(
        check(
            "GAR-DELEG-004",
            "diff_report_and_receipt_returned",
            VIOLATED if missing else SATISFIED,
            f"missing: {missing}" if missing else "all three returned",
        )
    )
    frozen_ok = contract_path.is_file() and digest(contract_path) == record.get(
        "frozen_contract_digest"
    )
    checks.append(
        check(
            "GAR-DELEG-003",
            "frozen_contract_digest_unchanged",
            SATISFIED if frozen_ok else VIOLATED,
            f"{record.get('frozen_contract_digest')} vs "
            f"{digest(contract_path) if contract_path.is_file() else 'absent'}",
        )
    )
    contract = load(contract_path) if contract_path.is_file() else {}
    receipt = load(receipt_path) if present["execution_receipt"] else {}
    if not isinstance(receipt, dict):
        receipt = {}
    checks.append(receipt_schema_check(record, receipt, present["execution_receipt"]))
    checks.extend(revision_checks(record, receipt, delivered_revision, repo))
    paths, diff_check = diff_truth(record, diff_path, delivered_revision, repo, present["diff"])
    checks.append(diff_check)
    checks.append(scope_check(contract, paths, diff_check["result"]))
    checks.append(self_report_consistency(receipt, paths))
    checks.extend(obligation_checks(contract, receipt))
    checks.extend(adjudication_checks(contract, adjudication, record, delivered_revision))
    failing = [c for c in checks if c["result"] != SATISFIED]
    status = VIOLATED if any(c["result"] == VIOLATED for c in failing) else UNKNOWN
    status = SATISFIED if not failing else status
    out = copy.deepcopy(record)
    out["result"] = {
        "diff_ref": str(diff_path),
        "implementation_report_ref": str(report_path),
        "execution_receipt_ref": str(receipt_path),
        "delivered_revision": delivered_revision,
        "returned_at": now(),
    }
    independent = diff_check["result"] == SATISFIED and adjudication is not None
    out["verification"] = {
        "status": status,
        "independent_of_coding_agent_self_report": independent,
        "evaluation_ref": str(Path(__file__).resolve()),
        "compared_against_frozen_contract_digest": digest(contract_path)
        if contract_path.is_file()
        else None,
        "discrepancy_refs": [f"{c['check_id']} {c['check']}: {c['detail']}" for c in failing],
        "evidence_refs": [str(diff_path), str(report_path), str(receipt_path)],
        "checks": checks,
    }
    out["status"] = "ACCEPTED" if status == SATISFIED and independent else "REJECTED"
    return out


def receipt_schema_check(record: dict[str, Any], receipt: Any, present: bool) -> dict[str, str]:
    if not present:
        return check("GAR-DELEG-004", "receipt_valid", VIOLATED, "no receipt returned")
    schema, where = receipt_schema(record)
    if schema is None:
        return check("GAR-DELEG-004", "receipt_valid", UNKNOWN, where)
    errors = sorted(e.message for e in jsonschema.Draft202012Validator(schema).iter_errors(receipt))
    if errors:
        return check("GAR-DELEG-004", "receipt_valid", VIOLATED, f"{where}: {errors}")
    if receipt.get("terminal_state") != "CONVERGED":
        return check(
            "GAR-DELEG-004",
            "receipt_valid",
            VIOLATED,
            f"terminal_state {receipt.get('terminal_state')}",
        )
    return check("GAR-DELEG-004", "receipt_valid", SATISFIED, f"valid against {where}")


def revision_checks(
    record: dict[str, Any], receipt: dict[str, Any], delivered: str, repo: Path | None
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    claimed: list[str] = []
    for state in ("validated_state", "delivered_state"):
        node = receipt.get(state)
        if isinstance(node, dict):
            claimed.extend(str(node[k]) for k in ("commit", "revision") if node.get(k))
    if not claimed:
        out.append(check("GAR-DELEG-005", "receipt_bound_to_delivered_revision", UNKNOWN, "none"))
    else:
        stale = [c for c in claimed if not same_revision(c, delivered)]
        out.append(
            check(
                "GAR-DELEG-005",
                "receipt_bound_to_delivered_revision",
                VIOLATED if stale else SATISFIED,
                f"stale: {stale} vs delivered {delivered}" if stale else f"all match {delivered}",
            )
        )
    if repo is None:
        out.append(check("GAR-DELEG-005", "delivered_descends_from_base", UNKNOWN, "no repository"))
        return out
    base = str(record.get("frozen_target_revision") or "")
    full = git_out(repo, "rev-parse", "--verify", f"{delivered}^{{commit}}")
    ok = (
        bool(full and base)
        and git(repo, "merge-base", "--is-ancestor", base, delivered).returncode == 0
    )
    out.append(
        check(
            "GAR-DELEG-005",
            "delivered_descends_from_base",
            SATISFIED if ok else VIOLATED,
            f"base {base or 'unknown'} -> delivered {full or delivered}",
        )
    )
    return out


def diff_truth(
    record: dict[str, Any], diff_path: Path, delivered: str, repo: Path | None, present: bool
) -> tuple[set[str], dict[str, str]]:
    name = "diff_is_the_delivered_change"
    if not present:
        return set(), check("GAR-DELEG-004", name, VIOLATED, "no diff")
    claimed = diff_paths(diff_path.read_text(encoding="utf-8"))
    if repo is None:
        return claimed, check("GAR-DELEG-005", name, UNKNOWN, "no repository to bind the diff")
    base = str(record.get("frozen_target_revision") or "")
    listed = git_out(repo, "diff", "--name-only", base, delivered)
    if listed is None:
        return claimed, check(
            "GAR-DELEG-005", name, UNKNOWN, f"git diff {base}..{delivered} failed"
        )
    actual = {p for p in listed.splitlines() if p}
    if actual != claimed:
        detail = f"returned diff {sorted(claimed ^ actual)} differs from git {base}..{delivered}"
        return actual, check("GAR-DELEG-005", name, VIOLATED, detail)
    canonical = subprocess.run(
        ["git", "-C", str(repo), "diff", "--no-color", "--no-ext-diff", base, delivered],
        capture_output=True,
        check=False,
    )
    want = patch_id(repo, canonical.stdout) if canonical.returncode == 0 else None
    got = patch_id(repo, diff_path.read_bytes())
    if want is None or got is None:
        detail = f"patch-id unavailable (returned {got}, git {base}..{delivered} {want})"
        return actual, check("GAR-DELEG-005", name, UNKNOWN, detail)
    if want != got:
        detail = (
            f"returned patch content differs from git {base}..{delivered} "
            f"(patch-id {got[:12]} != {want[:12]}); file names alone do not bind the diff"
        )
        return actual, check("GAR-DELEG-005", name, VIOLATED, detail)
    detail = f"{len(actual)} paths and patch-id {want[:12]} match git {base}..{delivered}"
    return actual, check("GAR-DELEG-005", name, SATISFIED, detail)


def patch_id(repo: Path, patch: bytes) -> str | None:
    """git's stable patch-id: content-bound, independent of line numbers and whitespace."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "patch-id", "--stable"],
        input=patch,
        capture_output=True,
        check=False,
    )
    fields = proc.stdout.decode("utf-8", "replace").split()
    return fields[0] if proc.returncode == 0 and fields else None


def scope_check(contract: Any, paths: set[str], diff_result: str) -> dict[str, str]:
    scope = contract.get("modification_scope") if isinstance(contract, dict) else None
    if not scope:
        return check("GAR-DELEG-006", "changes_within_modification_scope", UNKNOWN, "no scope")
    if diff_result == UNKNOWN or not paths:
        return check("GAR-DELEG-006", "changes_within_modification_scope", UNKNOWN, "no bound diff")
    outside = sorted(p for p in paths if not in_scope(p, list(scope)))
    return check(
        "GAR-DELEG-006",
        "changes_within_modification_scope",
        VIOLATED if outside else SATISFIED,
        f"outside frozen scope: {outside}" if outside else f"{len(paths)} paths in scope",
    )


def self_report_consistency(receipt: dict[str, Any], paths: set[str]) -> dict[str, str]:
    claimed: set[str] = set()
    for item in receipt.get("changed_surfaces") or []:
        value = item.get("path") if isinstance(item, dict) else item
        if value:
            claimed.add(str(value))
    if claimed == paths:
        return check("GAR-DELEG-007", "receipt_surfaces_match_diff", SATISFIED, "consistent")
    return check(
        "GAR-DELEG-007",
        "receipt_surfaces_match_diff",
        VIOLATED,
        f"claimed-only {sorted(claimed - paths)}; unreported {sorted(paths - claimed)}",
    )


def obligation_checks(contract: Any, receipt: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(contract, dict):
        return [check("GAR-DELEG-007", "contract_readable", UNKNOWN, "frozen contract unreadable")]
    matrix = receipt.get("acceptance_matrix") or []
    for i, criterion in enumerate(contract.get("acceptance_criteria") or []):
        entry = covered(matrix, i, criterion, "criterion", "criterion_index")
        ok = (
            bool(entry) and entry.get("status") in PASSING_CRITERION and bool(entry.get("evidence"))
        )
        out.append(
            check(
                "GAR-DELEG-007",
                f"acceptance_criterion[{i}]_evidenced",
                SATISFIED if ok else (UNKNOWN if entry is None else VIOLATED),
                "evidenced" if ok else f"receipt entry: {entry}",
            )
        )
    results = receipt.get("validation") or []
    for i, obligation in enumerate(contract.get("validation_obligations") or []):
        entry = covered(results, i, obligation, "obligation", "obligation_index")
        result = entry.get("result") if entry else None
        verdict = SATISFIED if result in PASSING_VALIDATION else VIOLATED
        out.append(
            check(
                "GAR-DELEG-007",
                f"validation_obligation[{i}]_observed",
                UNKNOWN if entry is None else verdict,
                f"result {result}",
            )
        )
    actions = receipt.get("external_actions") or []
    permitted = {norm(p) for p in contract.get("external_action_permissions") or []}
    unmatched = [a for a in actions if action_name(a) not in permitted]
    out.append(
        check(
            "GAR-DELEG-007",
            "external_actions_authorized",
            VIOLATED if unmatched else SATISFIED,
            f"unpermitted actions {unmatched}; permitted {sorted(permitted)}"
            if unmatched
            else f"{len(actions)} actions, each matched to a permission",
        )
    )
    return out


def action_name(action: Any) -> str:
    """One external action's kind, matched exactly against one permission entry."""
    if isinstance(action, dict):
        return norm(action.get("action") or action.get("type") or action.get("name") or "")
    return norm(action)


def gar_identity(gar_root: Path = PACK) -> str:
    """GAR's own declared identity, read from its manifest, never a constant or an alias."""
    return norm(walk(load(gar_root / MANIFEST_FILE), "manifest.name") or "")


def adjudication_checks(
    contract: Any,
    adjudication: dict[str, Any] | None,
    record: dict[str, Any],
    delivered: str,
) -> list[dict[str, str]]:
    """GAR's own verdicts on what no diff can decide mechanically.

    The adjudicator must be exactly GAR's manifest identity (an allowlist, not a denylist of
    known self-reporters), and the adjudication must name this freeze's contract digest and
    the delivered revision, so a verdict written for another delegation cannot be replayed.
    The identity is a declared field, not a signature; the pack holds no signing key.
    """
    name = "gar_adjudication"
    if adjudication is None:
        return [check("GAR-DELEG-007", name, UNKNOWN, "no GAR adjudication supplied")]
    who, gar = norm(adjudication.get("adjudicator", "")), gar_identity()
    if not gar or who != gar:
        detail = f"adjudicator {who!r} is not GAR ({gar!r})"
        return [check("GAR-DELEG-007", name, VIOLATED, detail)]
    bound_digest = adjudication.get("frozen_contract_digest")
    if bound_digest != record.get("frozen_contract_digest"):
        detail = f"adjudication names digest {bound_digest!r}, not this freeze"
        return [check("GAR-DELEG-007", name, VIOLATED, detail)]
    bound_revision = adjudication.get("delivered_revision")
    if not same_revision(str(bound_revision or ""), delivered):
        detail = f"adjudication names revision {bound_revision!r}, not delivered {delivered}"
        return [check("GAR-DELEG-007", name, VIOLATED, detail)]
    out: list[dict[str, str]] = [
        check("GAR-DELEG-007", name, SATISFIED, f"{gar}, bound to digest and revision")
    ]
    sections = {
        "acceptance_criteria": "acceptance_criteria",
        "forbidden_actions": "forbidden_actions",
        "locked_invariants": "locked_invariants",
    }
    for section, key in sections.items():
        verdicts = {
            v.get("index"): v for v in adjudication.get(section) or [] if isinstance(v, dict)
        }
        for i, _ in enumerate(contract.get(key) or [] if isinstance(contract, dict) else []):
            v = verdicts.get(i)
            if v is None:
                result, detail = UNKNOWN, "no GAR verdict"
            elif v.get("verdict") == SATISFIED and v.get("evidence_refs"):
                result, detail = SATISFIED, "; ".join(map(str, v["evidence_refs"]))[:160]
            else:
                result, detail = VIOLATED, str(v.get("verdict"))
            out.append(check("GAR-DELEG-007", f"gar_adjudicated_{section}[{i}]", result, detail))
    return out


# --------------------------------------------------------------------------- carriage


def carriage(
    record: dict[str, Any], runtime_root: Path, compiled: list[Path], owner: str
) -> dict[str, Any]:
    """Observe whether the integrated runtime carries the frozen payload verbatim."""
    sib = record.get("sibling_resolution") or {}
    root = Path(str(record.get("sibling_root", "")))
    schema_id = (load(root / str(sib.get("contract_schema_ref"))) or {}).get("$id")
    frozen_ref = Path(str(record.get("frozen_contract_ref"))).resolve()
    frozen = load(frozen_ref)
    runtime = runtime_root.resolve()
    scanned = sorted((runtime / "contracts").glob("*.schema.json"))
    slots = [
        str(p.relative_to(runtime))
        for p in scanned
        if schema_id and schema_id in json.dumps(load(p))
    ]
    admitted, refused = runtime_artifacts(compiled, runtime, frozen_ref)
    hits = [str(p.relative_to(runtime)) for p in admitted if contains(load(p), frozen)]
    if hits and slots:
        status, blocker = "CARRIED_VERBATIM", None
    elif slots:
        status = "NOT_EVALUATED"
        blocker = (
            f"{owner} declares a slot in {slots} but no compiled artifact of that runtime "
            f"carries the payload; refused evidence {refused}"
        )
    else:
        status = "NOT_CARRIABLE"
        blocker = (
            f"{owner}: no contract schema under {runtime / 'contracts'} references the payload "
            f"schema {schema_id!r}; scanned {[p.name for p in scanned]}"
            + (f"; payload found in {hits} without a declared slot" if hits else "")
        )
    transport = {
        "mode": "L9_INTEGRATED",
        "owner": owner,
        "carriage_status": status,
        "blocker_ref": blocker,
    }
    out: dict[str, Any] = {
        "status": status,
        "transport": transport,
        "admitted_evidence": [str(p) for p in admitted],
        "refused_evidence": refused,
    }
    if status != "CARRIED_VERBATIM":
        out["block_receipt"] = block_receipt(
            record, owner, str(blocker), scanned, admitted, refused, schema_id
        )
    return out


def runtime_artifacts(
    compiled: list[Path], runtime: Path, frozen_ref: Path
) -> tuple[list[Path], list[str]]:
    """Only files inside the runtime root, other than the frozen payload itself, are evidence."""
    admitted: list[Path] = []
    refused: list[str] = []
    for raw in compiled:
        path = raw.resolve()
        if not path.is_file():
            refused.append(f"{raw}: not a file")
        elif path == frozen_ref:
            refused.append(f"{raw}: the frozen payload itself, not a runtime artifact")
        elif not path.is_relative_to(runtime):
            refused.append(f"{raw}: outside the runtime root {runtime}")
        else:
            admitted.append(path)
    return admitted, refused


def block_receipt(
    record: dict[str, Any],
    owner: str,
    blocker: str,
    scanned: list[Path],
    admitted: list[Path],
    refused: list[str],
    schema_id: Any,
) -> dict[str, Any]:
    """A shape-complete EXTERNAL_DEPENDENCY receipt per OUTCOME_OWNERSHIP block requirements."""
    receipt: dict[str, Any] = {
        "block_type": "EXTERNAL_DEPENDENCY",
        "reason_code": "EXTERNAL_DEPENDENCY_BLOCK",
        "specific_required_action": (
            f"{owner} must declare a contract slot referencing {schema_id!r} and emit the "
            "frozen payload verbatim in a compiled artifact"
        ),
        "evidence_refs": [str(p) for p in scanned] + [str(p) for p in admitted] + refused,
        "completed_work_refs": [
            str(record.get("frozen_contract_ref")),
            f"frozen_contract_digest {record.get('frozen_contract_digest')}",
            str(record.get("schema_validation_ref")),
        ],
        "remaining_action": (
            f"deliver the frozen payload to the Coding Agent once {owner} carries it, or "
            "obtain explicit release of integrated orchestration and deliver in STANDALONE mode"
        ),
        "legitimacy_evidence_refs": [
            f"dependency necessary: integrated mode transfers transport to {owner} "
            "(integrations/L9_RUNTIME_BINDING.yaml#coding_delegation_transport)",
            f"no bounded substitute: GAR may not add fields to or fork {owner} contracts; "
            f"scanned {[p.name for p in scanned]}, blocker: {blocker}",
        ],
        "integrated_coverage_claimed": False,
    }
    required = walk(load(PACK / POLICY_FILE), "block_receipt_requirements.required_fields") or []
    missing = [f for f in required if not receipt.get(f)]
    receipt["shape_complete"] = bool(required) and not missing
    receipt["missing_required_fields"] = missing
    return receipt


def contains(node: Any, target: Any) -> bool:
    if node == target:
        return True
    if isinstance(node, dict):
        return any(contains(v, target) for v in node.values())
    if isinstance(node, list):
        return any(contains(v, target) for v in node)
    return False


# --------------------------------------------------------------------------- self-test


class Fixture:
    """A throwaway git repository and delegation inputs for the self-test."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.repo = tmp / "repo"
        (self.repo / "src").mkdir(parents=True)
        self.run("init", "-q", "-b", "main")
        (self.repo / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        self.base = self.commit("base")
        (self.repo / "src" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        self.delivered = self.commit("in-scope change")
        (self.repo / "ops.py").write_text("DRIFT = True\n", encoding="utf-8")
        self.drift = self.commit("out-of-scope change")

    def run(self, *args: str) -> str:
        proc = git(
            self.repo,
            "-c",
            "user.name=gar-self-test",
            "-c",
            "user.email=gar-self-test@invalid",
            "-c",
            "commit.gpgsign=false",
            *args,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr)
        return proc.stdout.strip()

    def commit(self, message: str) -> str:
        self.run("add", "-A")
        self.run("commit", "-q", "--no-verify", "-m", message)
        return self.run("rev-parse", "HEAD")

    def contract(self, name: str = "contract.yaml", **changes: Any) -> Path:
        body: dict[str, Any] = {
            "contract_id": "GAR-SELF-TEST-001",
            "objective": "change VALUE",
            "target": {"repository_or_artifact": str(self.repo), "base_revision": self.base},
            "authority_refs": ["self-test authority"],
            "in_scope": ["src/app.py"],
            "out_of_scope": ["everything else"],
            "locked_invariants": ["VALUE stays an int"],
            "acceptance_criteria": ["VALUE is 2"],
            "forbidden_actions": ["push"],
            "validation_obligations": ["read VALUE"],
            "delivery_mode": "in_place_patch",
            "modification_scope": ["src/app.py"],
            "external_action_permissions": [],
        }
        for key, value in changes.items():
            if value is None:
                body.pop(key, None)
            else:
                body[key] = value
        path = self.tmp / name
        path.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")
        return path

    def diff(self, head: str, name: str) -> Path:
        path = self.tmp / name
        path.write_text(self.run("diff", self.base, head) + "\n", encoding="utf-8")
        return path

    def receipt(self, head: str, name: str = "receipt.json", **changes: Any) -> Path:
        state = {"revision": head}
        body: dict[str, Any] = {
            "terminal_state": "CONVERGED",
            "objective_status": "VALUE is 2",
            "target": {"repository_or_artifact": str(self.repo)},
            "changed_surfaces": [{"path": "src/app.py"}],
            "validation": [{"obligation_index": 0, "result": "Passed"}],
            "acceptance_matrix": [
                {"criterion_index": 0, "status": "Satisfied", "evidence": "diff"}
            ],
            "external_actions": [],
            "delivery_status": "in_place_patch",
            "validated_state": dict(state),
            "delivered_state": dict(state),
        }
        for key, value in changes.items():
            if value is None:
                body.pop(key, None)
            else:
                body[key] = value
        path = self.tmp / name
        path.write_text(json.dumps(body), encoding="utf-8")
        return path

    def report(self) -> Path:
        path = self.tmp / "report.md"
        path.write_text("# report\nVALUE changed to 2.\n", encoding="utf-8")
        return path


def adjudication_for(record: dict[str, Any], delivered: str, **changes: Any) -> dict[str, Any]:
    """A GAR adjudication bound to one freeze and one delivered revision."""
    body: dict[str, Any] = {
        "adjudicator": "l9-global-architect",
        "frozen_contract_digest": record.get("frozen_contract_digest"),
        "delivered_revision": delivered,
        "acceptance_criteria": [{"index": 0, "verdict": SATISFIED, "evidence_refs": ["diff"]}],
        "forbidden_actions": [{"index": 0, "verdict": SATISFIED, "evidence_refs": ["no remote"]}],
        "locked_invariants": [{"index": 0, "verdict": SATISFIED, "evidence_refs": ["VALUE = 2"]}],
    }
    body.update(changes)
    return body


def self_test() -> dict[str, Any]:
    results: list[dict[str, str]] = []

    def expect(check_id: str, name: str, ok: bool, detail: Any) -> None:
        results.append(
            {
                "check_id": check_id,
                "case": name,
                "result": "PASS" if ok else "FAIL",
                "detail": str(detail)[:240],
            }
        )

    with tempfile.TemporaryDirectory(prefix="gar-deleg-") as raw:
        tmp = Path(raw)
        fx = Fixture(tmp)
        live = resolve()
        expect(
            "GAR-DELEG-010",
            "live sibling resolves",
            live["status"] == "RESOLVED",
            live.get("reason"),
        )
        sibling = Path(live["sibling_root"]) if live["status"] == "RESOLVED" else None
        bumped = sibling_cases(tmp, sibling, live, expect) if sibling is not None else None
        good = fx.contract()
        record = issue(good, target_revision=fx.base)
        expect(
            "GAR-DELEG-001",
            "canonical payload freezes",
            record.get("status") == "CONTRACT_FROZEN",
            record.get("reason"),
        )
        competing = issue(good, competing=["plan.md as contract"])
        expect(
            "GAR-DELEG-001",
            "competing instructions block",
            competing["status"] == "BLOCKED",
            competing.get("reason"),
        )
        alternate = tmp / "alternate.yaml"
        alternate.write_text("gar_coding_template: v1\ntask: do it\n", encoding="utf-8")
        alt = issue(alternate)
        expect(
            "GAR-DELEG-001",
            "alternate contract blocks",
            alt["status"] == "BLOCKED",
            alt.get("reason"),
        )
        incomplete = issue(fx.contract("incomplete.yaml", acceptance_criteria=None))
        expect(
            "GAR-DELEG-002",
            "missing required field blocks",
            incomplete["status"] == "BLOCKED",
            incomplete.get("reason"),
        )
        no_base = issue(fx.contract("nobase.yaml", target={"repository_or_artifact": "r"}))
        expect(
            "GAR-DELEG-002",
            "unknown base revision blocks",
            no_base["status"] == "BLOCKED",
            no_base.get("reason"),
        )
        if record.get("status") != "CONTRACT_FROZEN":
            return summary(results)
        changed = fx.contract("changed.yaml", objective="change VALUE and more")
        refreeze = issue(changed, prior=record)
        expect(
            "GAR-DELEG-003",
            "changed objective without reauthorization blocks",
            refreeze["status"] == "BLOCKED",
            refreeze.get("reason"),
        )
        reauth = issue(changed, prior=record, reauthorization="operator approved the new objective")
        expect(
            "GAR-DELEG-003",
            "changed objective with reauthorization refreezes",
            reauth.get("status") == "CONTRACT_FROZEN",
            reauth.get("reason"),
        )
        if bumped is not None:
            frozen_version = record["sibling_resolution"]["contract_version"]
            again = issue(good, prior=record, sibling_root=bumped)
            expect(
                "GAR-DELEG-003",
                "rework keeps the issuance-time sibling resolution after a sibling bump",
                again.get("status") == "CONTRACT_FROZEN"
                and again["sibling_resolution"] == record["sibling_resolution"]
                and again["sibling_resolution"]["contract_version"] == frozen_version
                and again["rework"]["count"] == 1,
                again.get("sibling_resolution", {}).get("contract_version"),
            )
        acceptance_cases(fx, good, changed, record, expect)
        expect(
            "GAR-DELEG-008",
            "non-coding handoff stays NONE",
            issue(good, handoff_kind="analysis")["status"] == "NONE",
            "analysis",
        )
        carriage_cases(tmp, record, expect)
    return summary(results)


def sibling_cases(tmp: Path, sibling: Path, live: dict[str, Any], expect: Any) -> Path:
    bumped, broken = tmp / "sibling-bumped", tmp / "sibling-broken"
    ignore = shutil.ignore_patterns("__pycache__")
    shutil.copytree(sibling, bumped, ignore=ignore)
    shutil.copytree(sibling, broken, ignore=ignore)
    owner = bumped / live["sibling_resolution"]["contract_owner_path"]
    doc = load(owner)
    doc["contract"]["version"] = "99.0.0"
    owner.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    newer = resolve(sibling_root=bumped)
    expect(
        "GAR-DELEG-010",
        "newer sibling version is picked up",
        newer.get("sibling_resolution", {}).get("contract_version") == "99.0.0",
        newer.get("sibling_resolution", {}).get("contract_version"),
    )
    (broken / live["sibling_resolution"]["contract_owner_path"]).unlink()
    gone = resolve(sibling_root=broken)
    expect(
        "GAR-DELEG-010",
        "unresolvable sibling blocks",
        gone["status"] == "BLOCKED",
        gone.get("reason"),
    )
    return bumped


def acceptance_cases(
    fx: Fixture, good: Path, changed: Path, record: dict[str, Any], expect: Any
) -> None:
    report, diff = fx.report(), fx.diff(fx.delivered, "good.diff")
    receipt = fx.receipt(fx.delivered)
    adjudication = adjudication_for(record, fx.delivered)

    def run(rec: dict[str, Any] = record, **over: Any) -> dict[str, Any]:
        args: dict[str, Any] = {
            "contract_path": good,
            "diff_path": diff,
            "report_path": report,
            "receipt_path": receipt,
            "delivered_revision": fx.delivered,
            "repo": fx.repo,
            "adjudication": adjudication,
        }
        args.update(over)
        return accept(rec, **args)

    def rejected(result: dict[str, Any], check_id: str) -> bool:
        failing = [c for c in result["verification"]["checks"] if c["result"] != SATISFIED]
        return result["status"] == "REJECTED" and any(c["check_id"] == check_id for c in failing)

    ok = run()
    expect(
        "POSITIVE",
        "complete independently verified result is ACCEPTED",
        ok["status"] == "ACCEPTED",
        ok["verification"]["discrepancy_refs"],
    )
    expect(
        "GAR-DELEG-003",
        "changed contract after freeze is rejected",
        rejected(run(contract_path=changed), "GAR-DELEG-003"),
        "digest",
    )
    expect(
        "GAR-DELEG-004",
        "missing receipt is rejected",
        rejected(run(receipt_path=fx.tmp / "absent.json"), "GAR-DELEG-004"),
        "receipt",
    )
    thin = fx.receipt(fx.delivered, "thin.json", changed_surfaces=None, validated_state=None)
    expect(
        "GAR-DELEG-004",
        "receipt missing fields is rejected",
        rejected(run(receipt_path=thin), "GAR-DELEG-004"),
        "schema",
    )
    expect(
        "GAR-DELEG-004",
        "missing diff is rejected",
        rejected(run(diff_path=fx.tmp / "absent.diff"), "GAR-DELEG-004"),
        "diff",
    )
    stale = fx.receipt(fx.base, "stale.json")
    expect(
        "GAR-DELEG-005",
        "receipt for another revision is rejected",
        rejected(run(receipt_path=stale), "GAR-DELEG-005"),
        "stale",
    )
    drift_receipt = fx.receipt(
        fx.drift, "drift.json", changed_surfaces=[{"path": "src/app.py"}, {"path": "ops.py"}]
    )
    drift = run(
        diff_path=fx.diff(fx.drift, "drift.diff"),
        receipt_path=drift_receipt,
        delivered_revision=fx.drift,
    )
    expect(
        "GAR-DELEG-006",
        "out-of-scope change is rejected",
        rejected(drift, "GAR-DELEG-006"),
        drift["verification"]["discrepancy_refs"],
    )
    expect(
        "GAR-DELEG-007",
        "self-report and CONVERGED alone are rejected",
        rejected(run(adjudication=None), "GAR-DELEG-007"),
        "no adjudication",
    )
    for alias in ("l9-coding-agent", "L9-Coding-Agent", "worker", "gar"):
        forged = adjudication_for(record, fx.delivered, adjudicator=alias)
        expect(
            "GAR-DELEG-007",
            f"adjudicator {alias!r} that is not GAR's manifest identity is rejected",
            rejected(run(adjudication=forged), "GAR-DELEG-007"),
            alias,
        )
    replayed = adjudication_for(record, fx.delivered, frozen_contract_digest="sha256:" + "0" * 64)
    expect(
        "GAR-DELEG-007",
        "adjudication bound to another freeze is rejected",
        rejected(run(adjudication=replayed), "GAR-DELEG-007"),
        "digest",
    )
    moved = adjudication_for(record, fx.base)
    expect(
        "GAR-DELEG-007",
        "adjudication bound to another revision is rejected",
        rejected(run(adjudication=moved), "GAR-DELEG-007"),
        "revision",
    )
    permit = fx.contract("permit.yaml", external_action_permissions=["push"])
    permit_record = issue(permit, target_revision=fx.base)
    if permit_record.get("status") == "CONTRACT_FROZEN":
        bound = adjudication_for(permit_record, fx.delivered)
        merged = fx.receipt(fx.delivered, "merge.json", external_actions=["merge"])
        expect(
            "GAR-DELEG-007",
            "external action outside the granted permission is rejected",
            rejected(
                run(permit_record, contract_path=permit, receipt_path=merged, adjudication=bound),
                "GAR-DELEG-007",
            ),
            "merge vs push",
        )
        pushed = fx.receipt(fx.delivered, "push.json", external_actions=[{"action": "push"}])
        allowed = run(permit_record, contract_path=permit, receipt_path=pushed, adjudication=bound)
        expect(
            "GAR-DELEG-007",
            "external action matching its permission is accepted",
            allowed["status"] == "ACCEPTED",
            allowed["verification"]["discrepancy_refs"],
        )
    else:
        expect("GAR-DELEG-007", "permission fixture freezes", False, permit_record)
    forged_diff = fx.tmp / "forged.diff"
    forged_diff.write_text(
        diff.read_text(encoding="utf-8").replace("+VALUE = 2", "+VALUE = 3"), encoding="utf-8"
    )
    expect(
        "GAR-DELEG-005",
        "fabricated hunks under correct headers are rejected",
        rejected(run(diff_path=forged_diff), "GAR-DELEG-005"),
        "patch-id",
    )
    unknown = fx.receipt(
        fx.delivered, "unknown.json", validation=[{"obligation_index": 0, "result": "Unknown"}]
    )
    expect(
        "GAR-DELEG-007",
        "Unknown validation is rejected",
        rejected(run(receipt_path=unknown), "GAR-DELEG-007"),
        "Unknown",
    )
    expect(
        "GAR-DELEG-005",
        "unbound diff without a repository is rejected",
        rejected(run(repo=None), "GAR-DELEG-005"),
        "no repo",
    )


def carriage_cases(tmp: Path, record: dict[str, Any], expect: Any) -> None:
    sib = record["sibling_resolution"]
    schema_id = load(Path(record["sibling_root"]) / sib["contract_schema_ref"]).get("$id")
    bare, slotted = tmp / "runtime-bare", tmp / "runtime-slotted"
    for root in (bare, slotted):
        (root / "contracts").mkdir(parents=True)
    (bare / "contracts" / "handoff_contract.schema.json").write_text(
        json.dumps({"type": "object", "properties": {"next_action": {"type": "string"}}}),
        encoding="utf-8",
    )
    (slotted / "contracts" / "handoff_contract.schema.json").write_text(
        json.dumps({"type": "object", "properties": {"payload": {"$ref": schema_id}}}),
        encoding="utf-8",
    )
    frozen = load(Path(record["frozen_contract_ref"]))
    payload = yaml.safe_dump({"payload": frozen})
    compiled = slotted / "HANDOFF_CONTRACT.yaml"
    outside = tmp / "HANDOFF_CONTRACT.yaml"
    unslotted = bare / "HANDOFF_CONTRACT.yaml"
    for path in (compiled, outside, unslotted):
        path.write_text(payload, encoding="utf-8")
    no = carriage(record, bare, [], "l9-cognitive-runtime")
    expect(
        "GAR-DELEG-009",
        "uncarriable path blocks without coverage claim",
        no["status"] == "NOT_CARRIABLE"
        and no["block_receipt"]["integrated_coverage_claimed"] is False,
        no["transport"]["blocker_ref"],
    )
    receipt = no["block_receipt"]
    expect(
        "GAR-DELEG-009",
        "block receipt is shape-complete against OUTCOME_OWNERSHIP required_fields",
        receipt["shape_complete"] is True and not receipt["missing_required_fields"],
        receipt["missing_required_fields"],
    )
    stray = carriage(record, slotted, [outside], "l9-cognitive-runtime")
    expect(
        "GAR-DELEG-009",
        "compiled evidence outside the runtime root is refused",
        stray["status"] == "NOT_EVALUATED" and bool(stray["refused_evidence"]),
        stray["refused_evidence"],
    )
    itself = carriage(
        record, slotted, [Path(record["frozen_contract_ref"])], "l9-cognitive-runtime"
    )
    expect(
        "GAR-DELEG-009",
        "the frozen payload itself is not carriage evidence",
        itself["status"] == "NOT_EVALUATED" and bool(itself["refused_evidence"]),
        itself["refused_evidence"],
    )
    no_slot = carriage(record, bare, [unslotted], "l9-cognitive-runtime")
    expect(
        "GAR-DELEG-009",
        "payload in a runtime without a declared slot is not carriage",
        no_slot["status"] == "NOT_CARRIABLE",
        no_slot["transport"]["blocker_ref"],
    )
    yes = carriage(record, slotted, [compiled], "l9-cognitive-runtime")
    expect(
        "GAR-DELEG-009",
        "verbatim carriage is observed",
        yes["status"] == "CARRIED_VERBATIM",
        yes["transport"],
    )
    slot_only = carriage(record, slotted, [], "l9-cognitive-runtime")
    expect(
        "GAR-DELEG-009",
        "a slot without an instance is not coverage",
        slot_only["status"] == "NOT_EVALUATED",
        slot_only["transport"],
    )


def summary(results: list[dict[str, str]]) -> dict[str, Any]:
    failed = [r for r in results if r["result"] != "PASS"]
    required = {f"GAR-DELEG-{i:03d}" for i in range(1, 11)}
    exercised = {r["check_id"] for r in results}
    gaps = sorted(required - exercised)
    status = "PASS" if not failed and not gaps else "FAIL"
    return {
        "status": status,
        "cases": len(results),
        "failed": failed,
        "unexercised": gaps,
        "results": results,
    }


# --------------------------------------------------------------------------- cli


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    sub = parser.add_subparsers(dest="command", required=True)
    p_resolve = sub.add_parser("resolve")
    p_resolve.add_argument("--sibling-root", type=Path)
    p_issue = sub.add_parser("issue")
    p_issue.add_argument("--contract", type=Path, required=True)
    p_issue.add_argument("--handoff-kind", default="implementation")
    p_issue.add_argument("--target-revision")
    p_issue.add_argument("--competing-instruction", action="append", default=[])
    p_issue.add_argument("--prior-delegation", type=Path)
    p_issue.add_argument("--reauthorization")
    p_issue.add_argument("--sibling-root", type=Path)
    p_accept = sub.add_parser("accept")
    p_accept.add_argument("--delegation", type=Path, required=True)
    p_accept.add_argument("--contract", type=Path, required=True)
    p_accept.add_argument("--diff", type=Path, required=True)
    p_accept.add_argument("--report", type=Path, required=True)
    p_accept.add_argument("--receipt", type=Path, required=True)
    p_accept.add_argument("--delivered-revision", required=True)
    p_accept.add_argument("--repo", type=Path)
    p_accept.add_argument("--adjudication", type=Path)
    p_carriage = sub.add_parser("carriage")
    p_carriage.add_argument("--delegation", type=Path, required=True)
    p_carriage.add_argument("--runtime-root", type=Path, required=True)
    p_carriage.add_argument("--compiled", type=Path, action="append", default=[])
    p_carriage.add_argument("--owner", default="l9-cognitive-runtime")
    sub.add_parser("self-test")
    args = parser.parse_args(argv)

    if args.command == "resolve":
        out = resolve(sibling_root=args.sibling_root)
        ok = out["status"] == "RESOLVED"
    elif args.command == "issue":
        prior = load(args.prior_delegation) if args.prior_delegation else None
        out = issue(
            args.contract,
            handoff_kind=args.handoff_kind,
            target_revision=args.target_revision,
            competing=args.competing_instruction,
            prior=prior,
            reauthorization=args.reauthorization,
            sibling_root=args.sibling_root,
        )
        ok = out["status"] in ("CONTRACT_FROZEN", "NONE")
    elif args.command == "accept":
        out = accept(
            load(args.delegation),
            contract_path=args.contract,
            diff_path=args.diff,
            report_path=args.report,
            receipt_path=args.receipt,
            delivered_revision=args.delivered_revision,
            repo=args.repo,
            adjudication=load(args.adjudication) if args.adjudication else None,
        )
        ok = out["status"] == "ACCEPTED"
    elif args.command == "carriage":
        out = carriage(load(args.delegation), args.runtime_root, args.compiled, args.owner)
        ok = out["status"] == "CARRIED_VERBATIM"
    else:
        out = self_test()
        ok = out["status"] == "PASS"
    print(json.dumps(out, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
