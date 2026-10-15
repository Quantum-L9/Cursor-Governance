#!/usr/bin/env python3
"""Verify the producer-emitted architecture-intelligence bundle GAR consumes.

GAR is the consumer here, never the producer. This verifier executes no selector, merges or
places no payload, and authors no schema. It checks only what the producer already claimed:
file bytes against the bundle lock, envelope digests, profile and schema pins against
``integrations/ARCHITECTURE_INTELLIGENCE_BINDING.yaml``, exact source coverage, that each
namespace of the composed view is byte-for-byte its component's payload (the contract's
placement invariant), the producer's receipts, and the authority status of the revision the bundle names.

Two questions are kept apart. BUNDLE_VERIFIED answers "is this the coherent, current output
the bundle claims to be?". ADMITTED_AND_CURRENT additionally answers "is that revision admitted
global law?", and is resolved independently of the bundle lock: integration into the
independently resolved tip of the authority's main, content currency at that tip, and an
admission decision record bound to the exact revision. The verifier's digests are recomputable,
so neither status attests that the canonical compiler produced the bytes; production is proven
by the CI replay the binding names (AIB-006).

Modes: ``admitted`` (default) loads only ADMITTED_AND_CURRENT and requires an authority checkout;
``candidate`` permits non-authoritative inspection of a BUNDLE_VERIFIED bundle.

Outcomes: ADMITTED_AND_CURRENT (0), REJECTED (1), BLOCKED (3), STALE (4), BUNDLE_VERIFIED (5);
2 is a usage error. There is no fallback to the historical observer projection or to any other
input.
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
EXIT = {"ADMITTED_AND_CURRENT": 0, "REJECTED": 1, "BLOCKED": 3, "STALE": 4, "BUNDLE_VERIFIED": 5}
AUTHORITY_MAIN_REF = "refs/remotes/origin/main"
BINDING_REF = "integrations/ARCHITECTURE_INTELLIGENCE_BINDING.yaml"
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


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )


def _require_root(root: Path) -> None:
    if not (root / ".git").exists():
        raise Outcome("BLOCKED", "AUTHORITY_ROOT_ABSENT", root=str(root))


def verify_currentness(
    root: Path, expect_revision: str, lock: dict[str, Any], binding: dict[str, Any]
) -> None:
    """The bundle is current at *expect_revision*: same revision, same source and profile bytes."""
    if not _SHA.match(expect_revision):
        raise Outcome("BLOCKED", "AUTHORITY_PIN_MALFORMED", revision=expect_revision)
    _require_root(root)
    observed = lock["authority"]["revision"]
    if observed != expect_revision:
        raise Outcome(
            "STALE", "AUTHORITY_REVISION_MISMATCH", bundle=observed, expected=expect_revision
        )
    verify_content_at(root, expect_revision, lock, binding)


def verify_content_at(
    root: Path, expect_revision: str, lock: dict[str, Any], binding: dict[str, Any]
) -> None:
    """Every source and profile the bundle was produced from is byte-identical at *expect_revision*,
    and the binding's expected source classes are exactly that profile's sources."""
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
        if collection == "projection_profiles":
            # Source-set closure: the binding's expected classes are derived facts of this exact
            # canonical profile, never a second declaration that may drift from it.
            canonical = list((entries[0].get("sources") or {}).keys())
            expected = list(pins["expected_source_classes"])
            if canonical != expected:
                raise Outcome(
                    "REJECTED",
                    "EXPECTED_SOURCE_SET_MISMATCH",
                    ref=ref,
                    revision=expect_revision,
                    missing_from_binding=[c for c in canonical if c not in expected],
                    absent_from_profile=[c for c in expected if c not in canonical],
                    order_differs=sorted(canonical) == sorted(expected),
                )
        current = content_digest(entries[0])
        if current != pinned:
            raise Outcome(
                "STALE", "PROFILE_DIGEST_NOT_CURRENT", ref=ref, pinned=pinned, current=current
            )


def resolve_authority_main(root: Path, override: str | None) -> str:
    """The tip of the authority's main, resolved from the authority checkout, never the lock."""
    _require_root(root)
    if override is not None:
        if not _SHA.match(override):
            raise Outcome("BLOCKED", "AUTHORITY_PIN_MALFORMED", revision=override)
        if _git(root, "cat-file", "-e", f"{override}^{{commit}}").returncode != 0:
            raise Outcome("BLOCKED", "AUTHORITY_MAIN_UNRESOLVED", revision=override)
        return override
    resolved = _git(root, "rev-parse", "--verify", "--quiet", f"{AUTHORITY_MAIN_REF}^{{commit}}")
    if resolved.returncode != 0 or not _SHA.match(resolved.stdout.strip()):
        raise Outcome("BLOCKED", "AUTHORITY_MAIN_UNRESOLVED", ref=AUTHORITY_MAIN_REF)
    return resolved.stdout.strip()


def resolve_admission(
    root: Path, revision: str, main_tip: str, lock: dict[str, Any], binding: dict[str, Any]
) -> dict[str, Any]:
    """Whether *revision* is admitted global law, decided without the bundle lock.

    Integration: *revision* is *main_tip* or an ancestor of it. Currency: every governing input
    is byte-identical at *main_tip* (otherwise STALE). Decision: an admission decision record
    bound to the exact revision (authority_model.yaml#admission_rules). The semantic owner
    defines no such record yet, so a revision that passes the first two remains
    ADMISSION_UNRESOLVED: integration alone is not admission."""
    rule = (binding.get("admission") or {}).get("decision_record") or {}
    base = {"revision": revision, "authority_main": main_tip}
    if _git(root, "cat-file", "-e", f"{revision}^{{commit}}").returncode != 0 or (
        _git(root, "merge-base", "--is-ancestor", revision, main_tip).returncode != 0
    ):
        return {
            **base,
            "status": "NOT_ADMITTED",
            "reason": "AUTHORITY_REVISION_NOT_INTEGRATED",
        }
    verify_content_at(root, revision, lock, binding)
    if main_tip != revision:
        try:
            verify_content_at(root, main_tip, lock, binding)
        except Outcome as outcome:
            raise Outcome(
                "STALE",
                "NOT_CURRENT_AT_AUTHORITY_MAIN",
                authority_main=main_tip,
                cause=outcome.reason,
                **outcome.detail,
            ) from None
    return {
        **base,
        "status": "ADMISSION_UNRESOLVED",
        "reason": "ADMISSION_DECISION_RECORD_UNDEFINED",
        "integrated": True,
        "current_at_authority_main": True,
        "decision_record_required_by": rule.get("required_by"),
    }


def state_record(
    result: dict[str, Any], binding: dict[str, Any], *, mode: str, status: str, admission: dict
) -> dict[str, Any]:
    """The `$.architecture_intelligence` fragment GAR records in run state."""
    lock = result["lock"]
    authoritative = status == "ADMITTED_AND_CURRENT"
    if authoritative:
        load_status = "LOADED"
    elif mode == "candidate":
        load_status = "LOADED_AS_CANDIDATE"
    else:
        load_status = "NOT_LOADED"
    record: dict[str, Any] = {
        "binding_ref": BINDING_REF,
        "mode": mode,
        "status": status,
        "bundle_status": "BUNDLE_VERIFIED",
        "authority_status": admission,
        "authoritative": authoritative,
        "load_status": load_status,
        "bundle_ref": binding["input"]["bundle"]["path"],
        "authority_repository": lock["authority"]["repository"],
        "authority_revision": lock["authority"]["revision"],
        "projection_profile": lock["projection_profile"],
        "composition_profile": lock["composition_profile"],
        "composition_digest": result["composition_digest"],
        "component_digests": result["component_digests"],
        "component_sources": {
            c["source_class"]: {
                "source_ref": c["source_ref"],
                "source_digest": c["source_digest"],
                "projection_digest": c["projection_digest"],
            }
            for c in lock["components"]
        },
        "producer": lock.get("producer"),
        "production_attested_by_verifier": False,
        "assurance_limitations": binding.get("assurance_limitations") or [],
        "verifier": "scripts/verify_architecture_intelligence.py",
        "fallback_used": False,
    }
    if load_status == "NOT_LOADED":
        record["refusal_reason"] = admission.get("reason")
    return record


def _pointer(document: Any, pointer: str) -> Any:
    """Read one value by RFC 6901 JSON pointer; reading is not selection or composition."""
    if not pointer.startswith("/"):
        raise Outcome("REJECTED", "CITATION_POINTER_MALFORMED", pointer=pointer)
    value = document
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and token in value:
            value = value[token]
        elif isinstance(value, list) and token.isdigit() and int(token) < len(value):
            value = value[int(token)]
        else:
            raise Outcome("REJECTED", "CITATION_POINTER_UNRESOLVED", pointer=pointer)
    return value


def cite(bundle: Path, result: dict[str, Any], record: dict[str, Any], target: str) -> dict:
    """Read one namespaced fact from the composed view with its exact source provenance.

    Called only after the record (provenance) exists and only when it is loadable (RS-034)."""
    source_class, _, pointer = target.partition(":")
    if record["load_status"] not in ("LOADED", "LOADED_AS_CANDIDATE"):
        raise Outcome("REJECTED", "CITATION_REFUSED_NOT_LOADED", record_status=record["status"])
    provenance = record["component_sources"].get(source_class)
    if provenance is None:
        raise Outcome("REJECTED", "CITATION_SOURCE_CLASS_UNKNOWN", source_class=source_class)
    _, composed = _read_json(bundle / result["composed_path"])
    return {
        "source_class": source_class,
        "namespace_pointer": f"/payload/{source_class}{pointer}",
        "value": _pointer(composed["payload"][source_class], pointer),
        "authoritative": record["authoritative"],
        "mode": record["mode"],
        **provenance,
        "composition_digest": record["composition_digest"],
        "authority_repository": record["authority_repository"],
        "authority_revision": record["authority_revision"],
    }


def _refusal(outcome: Outcome, mode: str) -> dict[str, Any]:
    return {
        "binding_ref": BINDING_REF,
        "mode": mode,
        "status": "UNAVAILABLE" if outcome.status == "BLOCKED" else outcome.status,
        "authoritative": False,
        "load_status": "NOT_LOADED",
        "refusal_reason": outcome.reason,
        "fallback_used": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify GAR's architecture-intelligence bundle.")
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--binding", type=Path, default=DEFAULT_BINDING)
    parser.add_argument("--mode", choices=("admitted", "candidate"), default="admitted")
    parser.add_argument("--authority-root", type=Path)
    parser.add_argument("--authority-main", help="independently resolved tip of authority main")
    parser.add_argument("--expect-revision", help="candidate mode: revision to check currency at")
    parser.add_argument("--cite", metavar="SOURCE_CLASS:/POINTER")
    args = parser.parse_args(argv)
    if args.mode == "admitted" and args.expect_revision is not None:
        parser.error("--expect-revision is candidate-mode only; admitted mode resolves main")
    if args.mode == "candidate" and args.expect_revision and args.authority_root is None:
        parser.error("--expect-revision needs --authority-root")
    report: dict[str, Any] = {"verifier": "gar.architecture-intelligence/v2", "mode": args.mode}
    try:
        binding = load_binding(args.binding)
        bundle = args.bundle or REPO / binding["input"]["bundle"]["path"]
        result = verify_bundle(bundle, binding)
        lock = result["lock"]
        if args.mode == "admitted":
            if args.authority_root is None:
                raise Outcome("BLOCKED", "AUTHORITY_ROOT_REQUIRED")
            main_tip = resolve_authority_main(args.authority_root, args.authority_main)
            admission = resolve_admission(
                args.authority_root, lock["authority"]["revision"], main_tip, lock, binding
            )
            currentness: dict[str, Any] = {"checked_against": main_tip, "basis": "authority_main"}
        else:
            if args.authority_root is not None and args.expect_revision is not None:
                verify_currentness(args.authority_root, args.expect_revision, lock, binding)
                currentness = {"checked_against": args.expect_revision, "basis": "named_revision"}
            else:
                currentness = {"checked_against": None, "status": "NOT_CHECKED"}
            admission = {"status": "NOT_EVALUATED", "reason": "CANDIDATE_MODE"}
        status = (
            "ADMITTED_AND_CURRENT"
            if admission.get("status") == "ADMITTED_AND_CURRENT"
            else "BUNDLE_VERIFIED"
        )
        record = state_record(result, binding, mode=args.mode, status=status, admission=admission)
        record["currentness"] = currentness
        report.update(
            status=status,
            reason="ADMITTED" if status == "ADMITTED_AND_CURRENT" else admission["reason"],
            bundle_status="BUNDLE_VERIFIED",
            authority_status=admission.get("status"),
            architecture_intelligence=record,
        )
        if args.cite is not None:
            try:
                report["citation"] = cite(bundle, result, record, args.cite)
            except Outcome as refused:
                report["citation"] = {"refused": refused.reason, **refused.detail}
    except Outcome as outcome:
        report.update(
            status=outcome.status,
            reason=outcome.reason,
            detail=outcome.detail,
            architecture_intelligence=_refusal(outcome, args.mode),
        )
        if args.cite is not None:
            report["citation"] = {"refused": "CITATION_REFUSED_NOT_LOADED"}
    except (KeyError, TypeError, ValueError) as exc:
        refused = Outcome("REJECTED", "BUNDLE_STRUCTURE_INVALID")
        report.update(
            status="REJECTED",
            reason="BUNDLE_STRUCTURE_INVALID",
            detail={"error": f"{type(exc).__name__}: {exc}"},
            architecture_intelligence=_refusal(refused, args.mode),
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return EXIT[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
