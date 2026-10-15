#!/usr/bin/env python3
"""Verify the producer-emitted architecture-intelligence bundle GAR consumes.

GAR is the consumer here, never the producer. This verifier executes no selector, merges or
places no payload, and authors no schema. It checks only what the producer already claimed:
file bytes against the bundle lock, envelope digests, profile and schema pins against
``integrations/ARCHITECTURE_INTELLIGENCE_BINDING.yaml``, exact source coverage, that each
namespace of the composed view is byte-for-byte its component's payload (the contract's
placement invariant), the producer's receipts, and, when an authority checkout is given,
that the bundle is current at the expected revision.

Outcomes: BOUND (0), REJECTED (1), BLOCKED (3), STALE (4); 2 is a usage error. A non-BOUND
outcome means GAR must not load the payload. There is no fallback to the historical observer
projection or to any other input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - interpreter without PyYAML
    print(
        json.dumps(
            {"status": "BLOCKED", "reason": "VERIFIER_INTERPRETER_UNRESOLVED"}, sort_keys=True
        )
    )
    sys.exit(3)

PACK = Path(__file__).resolve().parents[1]
REPO = PACK.parents[1]
DEFAULT_BINDING = PACK / "integrations/ARCHITECTURE_INTELLIGENCE_BINDING.yaml"
EXIT = {"BOUND": 0, "REJECTED": 1, "BLOCKED": 3, "STALE": 4}
LOCK_SCHEMA = "l9.gar.architecture-intelligence-bundle/v1"
PROJECTION_ENVELOPE = "l9.projection-artifact/v1"
COMPOSED_ENVELOPE = "l9.composed-projection/v1"
RECEIPT_SCHEMA = "l9.compiler-receipt/v1"
RECEIPT_TYPE = "l9.receipt/compilation@1"
PRODUCER = "l9-semantic-compiler"
_SHA = re.compile(r"^[0-9a-f]{40}$")


class Outcome(Exception):
    def __init__(self, status: str, reason: str, **detail: Any) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.detail = detail


def content_digest(value: Any) -> str:
    """sha256 of canonical JSON (sorted keys, compact separators, UTF-8): the producer's
    published digest convention for envelopes and receipts."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def bytes_digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _without(document: dict[str, Any], field: str) -> dict[str, Any]:
    return {k: v for k, v in document.items() if k != field}


def _read_json(path: Path) -> tuple[bytes, Any]:
    if not path.is_file():
        raise Outcome("REJECTED", "BUNDLE_FILE_ABSENT", path=str(path))
    raw = path.read_bytes()
    try:
        return raw, json.loads(raw)
    except json.JSONDecodeError as exc:
        raise Outcome("REJECTED", "BUNDLE_FILE_MALFORMED", path=str(path), error=str(exc))


def load_binding(path: Path) -> dict[str, Any]:
    try:
        binding = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise Outcome("BLOCKED", "BINDING_UNRESOLVED", path=str(path), error=str(exc))
    pins = (binding or {}).get("input", {}).get("authority")
    if not isinstance(pins, dict):
        raise Outcome("BLOCKED", "BINDING_UNRESOLVED", path=str(path))
    return binding


def _expect(condition: bool, reason: str, **detail: Any) -> None:
    if not condition:
        raise Outcome("REJECTED", reason, **detail)


def _receipt(
    bundle: Path,
    rel: str,
    subject: str,
    output_digest: str,
    profile: dict[str, str],
    revision: str,
    repository: str,
) -> dict[str, Any]:
    _, receipt = _read_json(bundle / rel)
    _expect(
        isinstance(receipt, dict)
        and receipt.get("schema") == RECEIPT_SCHEMA
        and receipt.get("receipt_type") == RECEIPT_TYPE,
        "RECEIPT_SCHEMA_MISMATCH",
        receipt=rel,
    )
    _expect(
        receipt.get("receipt_digest") == content_digest(_without(receipt, "receipt_digest")),
        "RECEIPT_DIGEST_MISMATCH",
        receipt=rel,
    )
    _expect(
        (receipt.get("producer_identity") or {}).get("compiler") == PRODUCER,
        "RECEIPT_PRODUCER_MISMATCH",
        receipt=rel,
    )
    _expect(receipt.get("exact_subject_ref") == subject, "RECEIPT_SUBJECT_MISMATCH", receipt=rel)
    _expect(
        (receipt.get("output") or {}).get("digest") == output_digest,
        "RECEIPT_OUTPUT_MISMATCH",
        receipt=rel,
    )
    _expect(receipt.get("profile") == profile, "RECEIPT_PROFILE_MISMATCH", receipt=rel)
    governing = receipt.get("governing_coordinates") or {}
    _expect(
        governing.get("repository") == repository and governing.get("revision") == revision,
        "RECEIPT_REVISION_MISMATCH",
        receipt=rel,
    )
    _expect(
        receipt.get("result") == "pass",
        "RECEIPT_RESULT_NOT_PASS",
        receipt=rel,
        result=receipt.get("result"),
        unresolved=(receipt.get("verification_basis") or {}).get("unresolved_criteria"),
    )
    return receipt


def _payload_schema(receipt: dict[str, Any], expected: str, rel: str) -> None:
    criterion = ((receipt.get("verification_basis") or {}).get("criteria") or {}).get(
        "payload_schema"
    ) or {}
    _expect(
        criterion.get("status") == "pass" and criterion.get("schema") == expected,
        "PAYLOAD_SCHEMA_MISMATCH",
        receipt=rel,
        expected=expected,
        observed=criterion.get("schema"),
    )


def verify_bundle(bundle: Path, binding: dict[str, Any]) -> dict[str, Any]:
    pins = binding["input"]["authority"]
    if not (bundle / "bundle.lock.json").is_file():
        raise Outcome("BLOCKED", "ARCHITECTURE_INTELLIGENCE_BUNDLE_ABSENT", bundle=str(bundle))
    _, lock = _read_json(bundle / "bundle.lock.json")
    _expect(isinstance(lock, dict) and lock.get("schema") == LOCK_SCHEMA, "LOCK_SCHEMA_MISMATCH")
    authority = lock.get("authority") or {}
    repository, revision = authority.get("repository"), authority.get("revision")
    if not (
        isinstance(repository, str)
        and repository == pins["repository"]
        and isinstance(revision, str)
        and _SHA.match(revision)
    ):
        raise Outcome("REJECTED", "AUTHORITY_IDENTITY_MISMATCH", observed=authority)
    projection_pin = {
        "ref": pins["projection_profile_ref"],
        "digest": pins["projection_profile_digest"],
    }
    composition_pin = {
        "ref": pins["composition_profile_ref"],
        "digest": pins["composition_profile_digest"],
    }
    _expect(
        lock.get("projection_profile") == projection_pin,
        "PROJECTION_PROFILE_MISMATCH",
        expected=projection_pin,
        observed=lock.get("projection_profile"),
    )
    _expect(
        lock.get("composition_profile") == composition_pin,
        "COMPOSITION_PROFILE_MISMATCH",
        expected=composition_pin,
        observed=lock.get("composition_profile"),
    )

    expected_classes = list(pins["expected_source_classes"])
    listed = lock.get("components")
    if not isinstance(listed, list) or not all(isinstance(c, dict) for c in listed):
        raise Outcome("REJECTED", "LOCK_COMPONENTS_MALFORMED")
    components: list[dict[str, Any]] = listed
    classes = [str(c.get("source_class")) for c in components]
    duplicates = sorted({c for c in classes if classes.count(c) > 1})
    _expect(not duplicates, "DUPLICATE_SOURCE", source_classes=duplicates)
    missing = [c for c in expected_classes if c not in classes]
    _expect(not missing, "MISSING_COMPONENT", source_classes=missing)
    extra = [c for c in classes if c not in expected_classes]
    _expect(not extra, "UNEXPECTED_COMPONENT", source_classes=extra)

    projections: dict[str, dict[str, Any]] = {}
    for entry in components:
        cls = entry["source_class"]
        raw, artifact = _read_json(bundle / entry["path"])
        _expect(
            bytes_digest(raw) == entry.get("sha256"), "BUNDLE_BYTES_MISMATCH", path=entry["path"]
        )
        _expect(
            isinstance(artifact, dict) and artifact.get("schema") == PROJECTION_ENVELOPE,
            "WRONG_ENVELOPE_SCHEMA",
            path=entry["path"],
            observed=artifact.get("schema") if isinstance(artifact, dict) else None,
        )
        _expect(
            artifact.get("projection_digest")
            == content_digest(_without(artifact, "projection_digest")),
            "PROJECTION_DIGEST_MISMATCH",
            path=entry["path"],
        )
        _expect(
            {
                "ref": artifact.get("projection_profile_ref"),
                "digest": artifact.get("projection_profile_digest"),
            }
            == projection_pin,
            "PROJECTION_PROFILE_MISMATCH",
            path=entry["path"],
        )
        _expect(
            artifact.get("source_ref") == entry.get("source_ref")
            and artifact.get("source_digest") == entry.get("source_digest")
            and artifact.get("projection_digest") == entry.get("projection_digest"),
            "COMPONENT_PROVENANCE_MISMATCH",
            path=entry["path"],
        )
        subject = f"{projection_pin['ref']}#{artifact['source_ref']}"
        receipt = _receipt(
            bundle,
            entry["receipt"],
            subject,
            artifact["projection_digest"],
            projection_pin,
            revision,
            repository,
        )
        _payload_schema(receipt, pins["projection_payload_schema"], entry["receipt"])
        projections[cls] = artifact

    composed_entry = lock.get("composed") or {}
    raw, composed = _read_json(bundle / str(composed_entry.get("path")))
    _expect(
        bytes_digest(raw) == composed_entry.get("sha256"),
        "BUNDLE_BYTES_MISMATCH",
        path=composed_entry.get("path"),
    )
    _expect(
        isinstance(composed, dict) and composed.get("schema") == COMPOSED_ENVELOPE,
        "WRONG_ENVELOPE_SCHEMA",
        path=composed_entry.get("path"),
        observed=composed.get("schema") if isinstance(composed, dict) else None,
    )
    _expect(
        composed.get("composition_digest")
        == content_digest(_without(composed, "composition_digest"))
        == composed_entry.get("composition_digest"),
        "COMPOSITION_DIGEST_MISMATCH",
    )
    _expect(composed.get("composition_profile") == composition_pin, "COMPOSITION_PROFILE_MISMATCH")
    expected_components = [
        {
            "projection_ref": f"{projection_pin['ref']}#{c['source_ref']}",
            "projection_digest": c["projection_digest"],
            "source_class": c["source_class"],
            "source_ref": c["source_ref"],
            "source_digest": c["source_digest"],
        }
        for c in sorted(components, key=lambda c: expected_classes.index(c["source_class"]))
    ]
    _expect(
        composed.get("components") == expected_components,
        "COMPOSED_COMPONENTS_MISMATCH",
    )
    payload = composed.get("payload")
    if not isinstance(payload, dict) or sorted(payload) != sorted(expected_classes):
        raise Outcome(
            "REJECTED",
            "COMPOSED_NAMESPACES_MISMATCH",
            observed=sorted(payload) if isinstance(payload, dict) else None,
        )
    diverged = [
        cls
        for cls in expected_classes
        if content_digest(payload[cls]) != content_digest(projections[cls]["payload"])
    ]
    _expect(not diverged, "NAMESPACE_PAYLOAD_DIVERGENCE", source_classes=diverged)
    composed_subject = f"{composition_pin['ref']}#{projection_pin['ref']}"
    receipt = _receipt(
        bundle,
        composed_entry["receipt"],
        composed_subject,
        composed["composition_digest"],
        composition_pin,
        revision,
        repository,
    )
    _payload_schema(receipt, pins["composed_payload_schema"], composed_entry["receipt"])
    return {
        "lock": lock,
        "composition_digest": composed["composition_digest"],
        "composed_path": composed_entry["path"],
        "component_digests": {c["source_class"]: c["projection_digest"] for c in components},
    }


def _git_bytes(root: Path, revision: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(root), "show", f"{revision}:{path}"],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise Outcome("BLOCKED", "AUTHORITY_OBJECT_UNRESOLVED", revision=revision, path=path)
    return completed.stdout


def verify_currentness(
    root: Path, expect_revision: str, lock: dict[str, Any], binding: dict[str, Any]
) -> None:
    """The bundle is current at *expect_revision*: same revision, same source and profile bytes."""
    if not _SHA.match(expect_revision):
        raise Outcome("BLOCKED", "AUTHORITY_PIN_MALFORMED", revision=expect_revision)
    if not (root / ".git").exists():
        raise Outcome("BLOCKED", "AUTHORITY_ROOT_ABSENT", root=str(root))
    observed = lock["authority"]["revision"]
    if observed != expect_revision:
        raise Outcome(
            "STALE", "AUTHORITY_REVISION_MISMATCH", bundle=observed, expected=expect_revision
        )
    registry = yaml.safe_load(_git_bytes(root, expect_revision, "semantics/canonical_sources.yaml"))
    paths = {s["id"]: s["path"] for s in registry.get("sources", []) if isinstance(s, dict)}
    for component in lock["components"]:
        path = paths.get(component["source_ref"])
        if path is None:
            raise Outcome("STALE", "SOURCE_UNREGISTERED", source_ref=component["source_ref"])
        current = bytes_digest(_git_bytes(root, expect_revision, path))
        if current != component["source_digest"]:
            raise Outcome(
                "STALE",
                "SOURCE_DIGEST_NOT_CURRENT",
                source_ref=component["source_ref"],
                bundle=component["source_digest"],
                current=current,
            )
    pins = binding["input"]["authority"]
    for catalog_path, collection, ref, pinned in (
        (
            "semantics/projection_profiles.yaml",
            "projection_profiles",
            pins["projection_profile_ref"],
            pins["projection_profile_digest"],
        ),
        (
            "semantics/composition_profiles.yaml",
            "profiles",
            pins["composition_profile_ref"],
            pins["composition_profile_digest"],
        ),
    ):
        catalog = yaml.safe_load(_git_bytes(root, expect_revision, catalog_path))
        entries = [
            p for p in catalog.get(collection, []) if isinstance(p, dict) and p.get("id") == ref
        ]
        if len(entries) != 1:
            raise Outcome("STALE", "PROFILE_NOT_RESOLVABLE", ref=ref, matches=len(entries))
        current = content_digest(entries[0])
        if current != pinned:
            raise Outcome(
                "STALE", "PROFILE_DIGEST_NOT_CURRENT", ref=ref, pinned=pinned, current=current
            )


def state_record(result: dict[str, Any], bundle_ref: str) -> dict[str, Any]:
    """The `$.architecture_intelligence` fragment GAR records in run state."""
    lock = result["lock"]
    return {
        "binding_ref": "integrations/ARCHITECTURE_INTELLIGENCE_BINDING.yaml",
        "status": "BOUND",
        "load_status": "LOADED",
        "bundle_ref": bundle_ref,
        "authority_repository": lock["authority"]["repository"],
        "authority_revision": lock["authority"]["revision"],
        "projection_profile": lock["projection_profile"],
        "composition_profile": lock["composition_profile"],
        "composition_digest": result["composition_digest"],
        "component_digests": result["component_digests"],
        "producer": lock.get("producer"),
        "verifier": "scripts/verify_architecture_intelligence.py",
        "fallback_used": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify GAR's architecture-intelligence bundle.")
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--binding", type=Path, default=DEFAULT_BINDING)
    parser.add_argument("--authority-root", type=Path)
    parser.add_argument("--expect-revision")
    args = parser.parse_args(argv)
    if (args.authority_root is None) != (args.expect_revision is None):
        parser.error("--authority-root and --expect-revision are given together")
    report: dict[str, Any] = {"verifier": "gar.architecture-intelligence/v1"}
    try:
        binding = load_binding(args.binding)
        bundle = args.bundle or REPO / binding["input"]["bundle"]["path"]
        result = verify_bundle(bundle, binding)
        if args.authority_root is not None:
            verify_currentness(args.authority_root, args.expect_revision, result["lock"], binding)
        record = state_record(result, binding["input"]["bundle"]["path"])
        record["currentness"] = (
            {"checked_against": args.expect_revision}
            if args.authority_root is not None
            else {"checked_against": None, "status": "NOT_CHECKED"}
        )
        report.update(status="BOUND", reason="VERIFIED", architecture_intelligence=record)
    except Outcome as outcome:
        report.update(
            status=outcome.status,
            reason=outcome.reason,
            detail=outcome.detail,
            architecture_intelligence={
                "binding_ref": "integrations/ARCHITECTURE_INTELLIGENCE_BINDING.yaml",
                "status": "UNAVAILABLE" if outcome.status == "BLOCKED" else outcome.status,
                "load_status": "NOT_LOADED",
                "refusal_reason": outcome.reason,
                "fallback_used": False,
            },
        )
    except (KeyError, TypeError, ValueError) as exc:
        report.update(
            status="REJECTED",
            reason="BUNDLE_STRUCTURE_INVALID",
            detail={"error": f"{type(exc).__name__}: {exc}"},
            architecture_intelligence={
                "binding_ref": "integrations/ARCHITECTURE_INTELLIGENCE_BINDING.yaml",
                "status": "REJECTED",
                "load_status": "NOT_LOADED",
                "refusal_reason": "BUNDLE_STRUCTURE_INVALID",
                "fallback_used": False,
            },
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return EXIT[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
