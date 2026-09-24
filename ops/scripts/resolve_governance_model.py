#!/usr/bin/env python3
"""Resolve compiled governance policy against deterministic repository facts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from jsonschema import Draft202012Validator

RESOLVER_VERSION = "1.0.0"
ORG_OUTPUT = "ORG_INVARIANTS.yaml"
REPO_OUTPUT = "governance/REPO_INVARIANTS.yaml"
MODEL_SCHEMA = "governance/policy/contracts/resolved-governance-model.v1.schema.json"
RECEIPT_SCHEMA = "governance/policy/contracts/governance-resolve-receipt.v1.schema.json"
DEFAULT_MODEL = ".artifacts/governance/resolved-governance-model.json"
DEFAULT_RECEIPT = ".artifacts/governance/governance-resolve-receipt.json"


class ResolveError(RuntimeError):
    pass


class InvocationError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _digest(value: Any) -> str:
    return _sha256(_canonical(value))


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvocationError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise InvocationError(f"JSON root must be an object: {path}")
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise InvocationError(f"cannot load YAML {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise InvocationError(f"YAML root must be a mapping: {path}")
    return value


def _schema_errors(value: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema)
    return [
        f"{'.'.join(str(part) for part in error.path) or '$'}: {error.message}"
        for error in sorted(validator.iter_errors(value), key=lambda item: list(item.path))
    ]


def _safe_rel(raw: str) -> str:
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or ".." in path.parts or raw.startswith("./"):
        raise ResolveError(f"unsafe repository-relative path: {raw!r}")
    return raw


def _repo_revision(root: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InvocationError "source revision unavailable; pass --source-revision" from exc
    if result.returncode != 0 or not result.stdout.strip():
        raise InvocationError("source revision unavailable; pass --source-revision")
    return result.stdout.strip()


def _file_fact(root: Path, path: str, *, adapter: str, claim: str) -> dict[str, Any]:
    rel = _safe_rel(path)
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ResolveError(f"resolved path escapes repository: {path}") from exc
    if not target.is_file():
        raise FileNotFoundError(path)
    digest = _sha256(target.read_bytes())
    fact_id = "fact:" + hashlib.sha256(f"{adapter}\0{rel}\0{digest}".encode()).hexdigest()[:16]
    return {"id": fact_id, "adapter": adapter, "source": rel, "digest": digest, "claim": claim}


def _load_evidence(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    value = _load_json(path)
    allowed = {"verifier_results"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise InvocationError(f"evidence file has unknown fields: {', '.join(unknown)}")
    results = value.get("verifier_results") or {}
    if not isinstance(results, dict):
        raise InvocationError("evidence.verifier_results must be an object")
    return value


def resolve(
    root: Path,
    *,
    source_revision: str,
    evidence: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    root = root.resolve()
    org = _load_yaml(root / ORG_OUTPUT)
    repo = _load_yaml(root / REPO_OUTPUT)
    if org.get("policy_digest") != repo.get("policy_digest"):
        raise ResolveError("compiled catalog policy digests disagree")
    policy_digest = str(org.get("policy_digest"))
    if not policy_digest.startswith("sha256:"):
        raise ResolveError("compiled catalogs do not contain a valid policy digest")

    admitted = (evidence or {}).get("verifier_results") or {}
    facts: list[dict[str, Any]] = []
    resolved_rows: list[dict[str, Any]] = []
    blocked_ids: list[str] = []

    for scope, catalog in (("organization", org), ("repository", repo)):
        for invariant in catalog.get("invariants") or []:
            invariant_id = invariant["id"]
            evidence_ids: list[str] = []
            required_binding_missing = False
            required_verifier_missing = False
            external_unknown = False
            explicit_failure = False

            for binding in invariant.get("bindings") or []:
                try:
                    fact = _file_fact(
                        root,
                        binding["path"],
                        adapter="path-binding-v1",
                        claim=f"{binding['kind']} binding exists at resolved repository revision",
                    )
                    facts.append(fact)
                    evidence_ids.append(fact["id"])
                except FileNotFoundError:
                    if binding.get("required", False):
                        required_binding_missing = True

            for verifier in invariant.get("verifiers") or []:
                kind = verifier.get("kind")
                path = verifier["path"]
                try:
                    fact = _file_fact(
                        root,
                        path,
                        adapter="verifier-registration-v1",
                        claim=f"{kind} verifier is registered at resolved repository revision",
                    )
                    facts.append(fact)
                    evidence_ids.append(fact["id"])
                except FileNotFoundError:
                    if verifier.get("required", False):
                        required_verifier_missing = True
                    continue

                invocation_id = verifier.get("invocation_id")
                admitted_key = invocation_id or path
                if admitted_key in admitted:
                    verdict = admitted[admitted_key]
                    if verdict not in {"PASS", "FAIL", "UNKNOWN"}:
                        raise InvocationError(
                            f"unsupported verifier verdict for {admitted_key}: {verdict!r}"
                        )
                    fact = {
                        "id": "fact:"
                        + hashlib.sha256(
                            f"evidence\0{admitted_key}\0{verdict}".encode()
                        ).hexdigest()[:16],
                        "adapter": "admitted-verifier-evidence-v1",
                        "source": admitted_key,
                        "digest": _digest({"key": admitted_key, "verdict": verdict}),
                        "claim": f"admitted verifier result is {verdict}",
                    }
                    facts.append(fact)
                    evidence_ids.append(fact["id"])
                    explicit_failure = explicit_failure or verdict == "FAIL"
                    external_unknown = external_unknown or verdict == "UNKNOWN"
                elif (
                    kind in {"ruleset_evidence", "manual_external"}
                    and verifier.get("required", False)
                ):
                    external_unknown = True

            if explicit_failure:
                status = "CONFLICT"
            elif required_binding_missing or required_verifier_missing:
                status = "MISSING"
            elif external_unknown:
                status = "UNKNOWN"
            else:
                required_verifiers = [
                    row
                    for row in invariant.get("verifiers") or []
                    if row.get("required", False)
                ]
                passed = 0
                for verifier in required_verifiers :
                    key = verifier.get("invocation_id") or verifier["path"]
                    if admitted.get(key) == "PASS":
                        passed += 1
                status = (
                    "VERIFIED"
                    if required_verifiers and passed == len(required_verifiers)
                    else "IMPLEMENTED"
                )

            if status in {"MISSING", "UNKNOWN", "CONFLICT"} and (
                invariant.get("projection", {}).get("invariants")
                or invariant.get("projection", {}).get("agents")
                or invariant.get("projection", {}).get("providers")
            ):
                blocked_ids.append(invariant_id)

            resolved_rows.append(
                {
                    "id": invariant_id,
                    "scope": scope,
                    "requirement": invariant["statement"],
                    "authority": {"source_change_ids": invariant.get("source_change_ids") or []},
                    "relationships": deepcopy(invariant.get("relationships") or []),
                    "bindings": [
                        {"path": row["path"], "kind": row["kind"]}
                        for row in invariant.get("bindings") or []
                    ],
                    "verifiers": [
                        {"path": row["path"], "kind": row["kind"]}
                        for row in invariant.get("verifiers") or []
                    ],
                    "implementation": {"status": status, "evidence_ids": sorted(set(evidence_ids))},
                    "projection": deepcopy(invariant["projection"]),
                    "source_digest": invariant["invariant_digest"],
                }
            )

    deduped_facts = {fact["id"]: fact for fact in facts}
    facts = [deduped_facts[key] for key in sorted(deduped_facts)]
    resolved_rows.sort(key=lambda row: (row["scope"], row["id"]))
    evidence_set_digest = _digest(facts)
    status = "BLOCKED" if blocked_ids else "PASS"
    model_base = {
        "schema": "l9.resolved-governance-model.v1",
        "repository": "Quantum-L9/Cursor-Governance",
        "source_revision": source_revision,
        "policy_digest": policy_digest,
        "evidence_set_digest": evidence_set_digest,
        "status": status,
        "invariants": resolved_rows,
        "facts": facts,
    }
    model_digest = _digest(model_base)
    model = {**model_base, "model_digest": model_digest}
    counts = Counter(row["implementation"]["status"] for row in resolved_rows)
    receipt = {
        "schema": "l9.governance-resolve-receipt.v1",
        "status": status,
        "resolver_version": RESOLVER_VERSION,
        "source_revision": source_revision,
        "policy_digest": policy_digest,
        "model_digest": model_digest,
        "evidence_set_digest": evidence_set_digest,
        "counts": {
            name: counts.get(name, 0)
            for name in ("VERIFIED", "IMPLEMENTED", "MISSING", "UNKNOWN", "CONFLICT")
        },
        "blocked_ids": sorted(set(blocked_ids)),
    }
    return model, receipt


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("resolve", "check", "inspect"))
    parser.add_argument("--root", default=".")
    parser.add_argument("--source-revision")
    parser.add_argument("--evidence")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--receipt", default=DEFAULT_RECEIPT)
    parser.add_argument("--json", action="store_true")
    ns = parser.parse_args(argv)
    try:
        root = Path(ns.root).resolve()
        revision = _repo_revision(root, ns.source_revision)
        evidence_path = Path(ns.evidence).resolve() if ns.evidence else None
        evidence = _load_evidence(evidence_path)
        model, receipt = resolve(root, source_revision=revision, evidence=evidence)
        model_schema = _load_json(root / MODEL_SCHEMA)
        receipt_schema = _load_json(root / RECEIPT_SCHEMA)
        model_errors = _schema_errors(model, model_schema)
        receipt_errors = _schema_errors(receipt, receipt_schema)
        if model_errors or receipt_errors:
            raise ResolveError(
                "schema validation failed: " + "; ".join(model_errors + receipt_errors)
            )
        model_path = root / _safe_rel(ns.model)
        receipt_path = root / _safe_rel(ns.receipt)
        expected_model = (json.dumps(model, indent=2, sort_keys=True) + "\n").encode()
        if ns.command == "check":
            if not model_path.is_file() or model_path.read_bytes() != expected_model:
                print(
                    f"[governance-resolve] STALE {ns.model}: expected={_sha256(expected_model)} "
                    f"actual="
                    f"{_sha256(model_path.read_bytes()) if model_path.is_file() else 'missing'}",
                    file=sys.stderr,
                )
                return 1
        elif ns.command == "resolve":
            _write_json(model_path, model)
        _write_json(receipt_path, receipt)
        payload = {
            "status": receipt["status"],
            "model_digest": receipt["model_digest"],
            "policy_digest": receipt["policy_digest"],
            "blocked_ids": receipt["blocked_ids"],
            "counts": receipt["counts"],
        }
        if ns.json or ns.command == "inspect":
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(
                f"[governance-resolve] {payload['status']} "
                f"model_digest={payload['model_digest']}"
            )
        return 0 if receipt["status"] == "PASS" else 1
    except ResolveError as exc:
        print(f"[governance-resolve] BLOCKED: {exc}", file=sys.stderr)
        return 1
    except InvocationError as exc:
        print(f"[governance-resolve] FATAL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
