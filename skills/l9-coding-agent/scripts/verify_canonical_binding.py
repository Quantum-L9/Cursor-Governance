#!/usr/bin/env python3
"""Verify a canonical L9 invariant projection before Coding Agent mutation.

Consumer-side verifier only. It never emits, synthesizes, or repairs a
projection: it checks a producer-emitted `l9.projection-artifact/v1` and its
`l9.compiler-receipt/v1` against an exact `Quantum-L9/.github` checkout and
prints one binding record for `runtime/RUN_STATE.yaml` `authority.sources`.

Law, schemas, and the profile are read from the authority root at its exact
revision; nothing upstream is copied here. Constants below are identity
coordinates, not doctrine.

Exit codes: 0 BOUND/CURRENT, 1 REJECTED, 2 usage, 3 BLOCKED (Unknown), 4 STALE.

Usage:
  verify_canonical_binding.py --authority-root DIR --artifact FILE --receipt FILE
      [--expect-revision SHA] [--require-invariant ID ...]
  verify_canonical_binding.py --authority-root DIR --prior-binding FILE
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:
    raise SystemExit(f"PyYAML is required: {exc}")

OWNER_REPOSITORY = "Quantum-L9/.github"
PROFILE_REF = "l9.projection/cursor-governance-operating-plane@1"
PROFILE_CONSUMER = "Cursor-Governance"
SOURCE_CLASS = "invariants"
SOURCE_REF = "l9.source/invariants@1"
SELECTOR = '$.invariants[?(@.scope=="global")]'
PROFILES_PATH = "semantics/projection_profiles.yaml"
SOURCES_PATH = "semantics/canonical_sources.yaml"
ARTIFACT_SCHEMA_PATH = "semantics/projection_artifact.schema.yaml"
RECEIPT_SCHEMA_PATH = "semantics/compiler_receipt.schema.yaml"

EXIT = {"BOUND": 0, "CURRENT": 0, "REJECTED": 1, "BLOCKED": 3, "STALE": 4}
_ORIGIN = re.compile(r"github\.com[/:]quantum-l9/\.github(\.git)?/?$", re.IGNORECASE)


class Outcome(Exception):
    def __init__(self, status: str, reason: str, **detail: Any) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.detail = detail


# Digest conventions. `.github` defines `semantic_digest` without fixing an
# algorithm, so the consumer accepts only digests it can recompute:
# - source digests: sha256 of raw file bytes, as `.github` ledgers record them
#   (e.g. `receipt_catalog.yaml` derivation.source_artifacts[].sha256);
# - content digests: sha256 of canonical JSON, as the candidate producer
#   `l9-semantic-compiler-engine` computes them (`engine/canonical.py`).
# A producer using another canonicalization fails closed here, never open.
def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _normalize(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    return value


def content_digest(value: Any) -> str:
    raw = json.dumps(_normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def bytes_digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _load(path: Path, what: str, missing_status: str = "BLOCKED") -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise Outcome(missing_status, f"{what}_UNREADABLE", path=str(path), error=str(exc)) from exc
    try:
        return json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    except Exception as exc:
        raise Outcome("REJECTED", f"{what}_MALFORMED", path=str(path), error=str(exc)) from exc


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True)
    if result.returncode != 0:
        raise Outcome(
            "BLOCKED",
            "AUTHORITY_ROOT_PROVENANCE_UNKNOWN",
            git=list(args),
            error=result.stderr.strip(),
        )
    return result.stdout.strip()


def authority_root(root: Path, expect_revision: str | None) -> dict[str, Any]:
    if not root.is_dir():
        raise Outcome("BLOCKED", "AUTHORITY_ROOT_ABSENT", path=str(root))
    origin = _git(root, "remote", "get-url", "origin")
    if not _ORIGIN.search(origin):
        raise Outcome(
            "BLOCKED",
            "AUTHORITY_ROOT_NOT_CANONICAL_OWNER",
            origin=origin,
            expected=OWNER_REPOSITORY,
        )
    revision = _git(root, "rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise Outcome("BLOCKED", "AUTHORITY_ROOT_PROVENANCE_UNKNOWN", revision=revision)
    if _git(root, "status", "--porcelain", "--", "semantics"):
        raise Outcome("BLOCKED", "AUTHORITY_ROOT_SEMANTICS_UNCOMMITTED", revision=revision)
    if expect_revision and revision != expect_revision:
        raise Outcome(
            "STALE", "AUTHORITY_REVISION_MISMATCH", observed=revision, expected=expect_revision
        )
    return {"repository": OWNER_REPOSITORY, "revision": revision}


def resolve_law(root: Path) -> dict[str, Any]:
    """Resolve source, profile, and current digests at the authority root."""
    registry = _load(root / SOURCES_PATH, "SOURCE_REGISTRY")
    entries = [
        s
        for s in (registry or {}).get("sources", [])
        if isinstance(s, dict) and s.get("id") == SOURCE_REF
    ]
    if len(entries) != 1:
        raise Outcome(
            "BLOCKED", "CANONICAL_SOURCE_UNRESOLVED", source_ref=SOURCE_REF, matches=len(entries)
        )
    source = entries[0]
    if source.get("canonical") is not True or source.get("projection_allowed") is not True:
        raise Outcome("BLOCKED", "CANONICAL_SOURCE_NOT_PROJECTABLE", source_ref=SOURCE_REF)

    catalog = _load(root / PROFILES_PATH, "PROFILE_CATALOG")
    profiles = [
        p
        for p in (catalog or {}).get("projection_profiles", [])
        if isinstance(p, dict) and p.get("id") == PROFILE_REF
    ]
    if len(profiles) != 1:
        raise Outcome(
            "BLOCKED", "PROFILE_UNRESOLVED", profile_ref=PROFILE_REF, matches=len(profiles)
        )
    profile = profiles[0]
    if profile.get("class") != "consumer" or profile.get("consumer") != PROFILE_CONSUMER:
        raise Outcome("BLOCKED", "PROFILE_CONSUMER_MISMATCH", profile_ref=PROFILE_REF)
    selectors = ((profile.get("sources") or {}).get(SOURCE_CLASS) or {}).get("selectors") or []
    if SELECTOR not in selectors:
        raise Outcome(
            "BLOCKED",
            "PROFILE_SELECTOR_COVERAGE_INCOMPLETE",
            source_class=SOURCE_CLASS,
            selector=SELECTOR,
        )
    class_artifact = ((catalog.get("source_classes") or {}).get(SOURCE_CLASS) or {}).get(
        "canonical_artifact"
    )
    if Path(str(source.get("path"))).name != class_artifact:
        raise Outcome(
            "BLOCKED",
            "SOURCE_CLASS_REGISTRY_CONFLICT",
            registry_path=source.get("path"),
            class_artifact=class_artifact,
        )

    source_path = root / str(source["path"])
    try:
        raw = source_path.read_bytes()
    except OSError as exc:
        raise Outcome(
            "BLOCKED", "CANONICAL_SOURCE_UNREADABLE", path=str(source_path), error=str(exc)
        ) from exc
    document = yaml.safe_load(raw)
    global_entries = [
        e
        for e in (document or {}).get("invariants", [])
        if isinstance(e, dict) and e.get("scope") == "global"
    ]
    return {
        "source": {"ref": SOURCE_REF, "path": str(source["path"]), "digest": bytes_digest(raw)},
        "profile": {"ref": PROFILE_REF, "digest": content_digest(profile)},
        "global_entries": {str(e.get("id")): e for e in global_entries},
    }


def _required(root: Path, schema_path: str) -> tuple[list[str], dict[str, Any]]:
    schema = _load(root / schema_path, "UPSTREAM_SCHEMA")
    required = (schema or {}).get("required")
    if not isinstance(required, list) or not required:
        raise Outcome("BLOCKED", "UPSTREAM_SCHEMA_INCOMPLETE", path=schema_path)
    return [str(r) for r in required], (schema.get("properties") or {})


def _check_shape(doc: Any, root: Path, schema_path: str, what: str) -> None:
    if not isinstance(doc, dict):
        raise Outcome("REJECTED", f"{what}_NOT_A_MAPPING")
    required, properties = _required(root, schema_path)
    missing = sorted(set(required) - set(doc))
    if missing:
        raise Outcome(
            "REJECTED", f"{what}_MISSING_REQUIRED_FIELDS", missing=missing, schema=schema_path
        )
    for key, rule in properties.items():
        if isinstance(rule, dict) and "const" in rule and doc.get(key) != rule["const"]:
            raise Outcome(
                "REJECTED",
                f"{what}_CONST_MISMATCH",
                field=key,
                observed=doc.get(key),
                expected=rule["const"],
            )


def verify_projection(args: argparse.Namespace) -> dict[str, Any]:
    if not args.artifact or not args.receipt:
        raise Outcome(
            "BLOCKED",
            "PROJECTION_OR_RECEIPT_ABSENT",
            hint="no producer-emitted projection supplied; local law text is not a substitute",
        )
    artifact_path, receipt_path = Path(args.artifact), Path(args.receipt)
    if not artifact_path.is_file() or not receipt_path.is_file():
        raise Outcome(
            "BLOCKED",
            "PROJECTION_OR_RECEIPT_ABSENT",
            artifact=str(artifact_path),
            receipt=str(receipt_path),
        )
    root = Path(args.authority_root)
    coordinates = authority_root(root, args.expect_revision)
    law = resolve_law(root)

    artifact = _load(artifact_path, "ARTIFACT", missing_status="BLOCKED")
    _check_shape(artifact, root, ARTIFACT_SCHEMA_PATH, "ARTIFACT")
    if artifact["projection_profile_ref"] != PROFILE_REF:
        raise Outcome(
            "REJECTED",
            "PROFILE_IDENTITY_MISMATCH",
            observed=artifact["projection_profile_ref"],
            expected=PROFILE_REF,
        )
    if artifact["source_ref"] != SOURCE_REF:
        raise Outcome(
            "REJECTED",
            "SOURCE_IDENTITY_MISMATCH",
            observed=artifact["source_ref"],
            expected=SOURCE_REF,
        )
    if artifact["source_digest"] != law["source"]["digest"]:
        raise Outcome(
            "STALE",
            "SOURCE_DIGEST_NOT_CURRENT",
            observed=artifact["source_digest"],
            current=law["source"]["digest"],
        )
    if artifact["projection_profile_digest"] != law["profile"]["digest"]:
        raise Outcome(
            "STALE",
            "PROFILE_DIGEST_NOT_CURRENT",
            observed=artifact["projection_profile_digest"],
            current=law["profile"]["digest"],
        )
    payload = artifact["payload"]
    if artifact["projection_digest"] != content_digest(payload):
        raise Outcome(
            "REJECTED", "PROJECTION_DIGEST_MISMATCH", observed=artifact["projection_digest"]
        )

    # Fidelity: digests are unkeyed, so the only anchor against a forged but
    # self-consistent artifact is the canonical source at the bound revision.
    if not isinstance(payload, list) or not all(isinstance(e, dict) and "id" in e for e in payload):
        raise Outcome(
            "REJECTED",
            "PAYLOAD_SHAPE_UNRESOLVED",
            expected="list of invariant entries selected by " + SELECTOR,
        )
    ids = [str(e["id"]) for e in payload]
    if len(ids) != len(set(ids)):
        raise Outcome("REJECTED", "PAYLOAD_DUPLICATE_IDENTITY")
    expected = law["global_entries"]
    if set(ids) != set(expected):
        raise Outcome(
            "REJECTED",
            "PAYLOAD_SELECTOR_COVERAGE_MISMATCH",
            missing=sorted(set(expected) - set(ids)),
            extra=sorted(set(ids) - set(expected)),
        )
    altered = sorted(
        i for i, e in zip(ids, payload) if content_digest(e) != content_digest(expected[i])
    )
    if altered:
        raise Outcome("REJECTED", "PAYLOAD_NOT_FAITHFUL_TO_SOURCE", altered=altered)

    receipt = _load(receipt_path, "RECEIPT", missing_status="BLOCKED")
    _check_shape(receipt, root, RECEIPT_SCHEMA_PATH, "RECEIPT")
    if receipt["operation"] != "projection" or receipt["result"] != "pass":
        raise Outcome(
            "REJECTED",
            "RECEIPT_NOT_A_PASSING_PROJECTION",
            operation=receipt["operation"],
            result=receipt["result"],
        )
    profile = receipt.get("profile") or {}
    if (
        profile.get("ref") != PROFILE_REF
        or profile.get("digest") != artifact["projection_profile_digest"]
    ):
        raise Outcome("REJECTED", "RECEIPT_PROFILE_MISMATCH", receipt_profile=profile)
    inputs = receipt.get("inputs") or []
    if {"ref": SOURCE_REF, "digest": artifact["source_digest"]} not in [
        {"ref": i.get("ref"), "digest": i.get("digest")} for i in inputs if isinstance(i, dict)
    ]:
        raise Outcome("REJECTED", "RECEIPT_INPUT_NOT_BOUND", inputs=inputs)
    if (receipt.get("output") or {}).get("digest") != artifact["projection_digest"]:
        raise Outcome("REJECTED", "RECEIPT_OUTPUT_NOT_BOUND", output=receipt.get("output"))
    if receipt["receipt_digest"] != content_digest(
        {k: v for k, v in receipt.items() if k != "receipt_digest"}
    ):
        raise Outcome("REJECTED", "RECEIPT_DIGEST_MISMATCH", observed=receipt["receipt_digest"])
    producer = receipt.get("producer_identity") or {}
    if not producer.get("compiler") or not producer.get("version"):
        raise Outcome("REJECTED", "RECEIPT_PRODUCER_UNIDENTIFIED")

    required = list(dict.fromkeys(args.require_invariant or []))
    unknown = [i for i in required if i not in expected]
    if unknown:
        raise Outcome("BLOCKED", "REQUIRED_INVARIANT_NOT_PROJECTED", invariant_ids=unknown)
    applicable = required or ids
    return {
        "status": "BOUND",
        "reason": "PROJECTION_VERIFIED",
        "authority_root": coordinates,
        "profile": law["profile"],
        "source": law["source"],
        "projection": {
            "digest": artifact["projection_digest"],
            "file_digest": bytes_digest(artifact_path.read_bytes()),
        },
        "receipt": {
            "identity": receipt["receipt_identity"],
            "digest": receipt["receipt_digest"],
            "producer": producer,
        },
        "applicable_invariants": [
            {"id": i, "digest": content_digest(expected[i])} for i in applicable
        ],
        "global_invariant_count": len(expected),
    }


def verify_prior(args: argparse.Namespace) -> dict[str, Any]:
    """Freshness of an earlier binding under `.github` invalidation rules."""
    prior = _load(Path(args.prior_binding), "PRIOR_BINDING")
    if not isinstance(prior, dict) or prior.get("status") != "BOUND":
        raise Outcome("BLOCKED", "PRIOR_BINDING_NOT_BOUND")
    root = Path(args.authority_root)
    coordinates = authority_root(root, args.expect_revision)
    law = resolve_law(root)
    bound = {
        str(i.get("id")): i.get("digest")
        for i in prior.get("applicable_invariants", [])
        if isinstance(i, dict)
    }
    affected = sorted(
        i
        for i, d in bound.items()
        if i not in law["global_entries"] or content_digest(law["global_entries"][i]) != d
    )
    revision_changed = (prior.get("authority_root") or {}).get("revision") != coordinates[
        "revision"
    ]
    record = {
        "authority_root": coordinates,
        "prior_revision": (prior.get("authority_root") or {}).get("revision"),
        "revision_changed": revision_changed,
        "affected_applicable_invariants": affected,
    }
    if (prior.get("source") or {}).get("digest") != law["source"]["digest"]:
        raise Outcome("STALE", "SOURCE_DIGEST_CHANGED", **record)
    if (prior.get("profile") or {}).get("digest") != law["profile"]["digest"]:
        raise Outcome("STALE", "PROFILE_DIGEST_CHANGED", **record)
    reason = (
        "UPSTREAM_REVISION_CHANGED_WITHOUT_DEPENDENCY_IMPACT" if revision_changed else "UNCHANGED"
    )
    return {"status": "CURRENT", "reason": reason, **record}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--authority-root", required=True, help="exact Quantum-L9/.github checkout")
    parser.add_argument(
        "--artifact", help="producer-emitted l9.projection-artifact/v1 (yaml or json)"
    )
    parser.add_argument("--receipt", help="producer-emitted l9.compiler-receipt/v1 (yaml or json)")
    parser.add_argument("--expect-revision", help="pinned 40-hex authority revision for this run")
    parser.add_argument(
        "--require-invariant", action="append", help="applicable invariant id (repeatable)"
    )
    parser.add_argument("--prior-binding", help="earlier BOUND record to re-check for currentness")
    args = parser.parse_args(argv)
    try:
        record = verify_prior(args) if args.prior_binding else verify_projection(args)
    except Outcome as outcome:
        record = {"status": outcome.status, "reason": outcome.reason, **outcome.detail}
    record = {"verifier": "l9-coding-agent/scripts/verify_canonical_binding.py", **record}
    print(json.dumps(record, indent=2, sort_keys=True))
    return EXIT[record["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
