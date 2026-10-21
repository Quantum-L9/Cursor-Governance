#!/usr/bin/env python3
"""Verify the producer-emitted architecture-intelligence bundle GAR consumes.

GAR is the consumer here, never the producer. This verifier executes no selector, merges or
places no payload, and authors no schema. It holds no bundle verification of its own: every
component (bytes, envelope, provenance, currency, receipt, producer), the authority checkout,
and the admission decision are checked by the one consumer verifier Coding Agent uses,
``skills/l9-coding-agent/scripts/verify_canonical_binding.py``, parameterized by this binding.
What stays here is what only GAR consumes: the composed view (its envelope, components, the
contract's placement invariant that each namespace is byte-for-byte its component's payload,
and its composition receipt), the run-state slot, and citation.

Two questions are kept apart. BUNDLE_VERIFIED answers "is this the coherent output the bundle
claims to be?". ADMITTED_AND_CURRENT additionally answers "is that revision admitted global
law?", resolved independently of the bundle lock by the shared admission resolver: integration
into the independently resolved tip of the authority's main, content currency at that tip, an
explicit decision record bound to each exact candidate digest, and then the bundle re-verified
against that tip with every law byte read from hash-checked commit objects. The digests are
recomputable, so neither status attests that the canonical compiler produced the bytes;
production is proven by the CI replay the binding names (AIB-006).

Modes: ``admitted`` (default) loads only ADMITTED_AND_CURRENT and requires an authority checkout
whose HEAD is its main; ``candidate`` permits non-authoritative inspection of a BUNDLE_VERIFIED
bundle.

Outcomes: ADMITTED_AND_CURRENT (0), REJECTED (1), BLOCKED (3), STALE (4), BUNDLE_VERIFIED (5);
2 is a usage error. There is no fallback to the historical observer projection or to any other
input.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
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
CORE_PATH = PACK.parent / "l9-coding-agent/scripts/verify_canonical_binding.py"
EXIT = {"ADMITTED_AND_CURRENT": 0, "REJECTED": 1, "BLOCKED": 3, "STALE": 4, "BUNDLE_VERIFIED": 5}
BINDING_REF = "integrations/ARCHITECTURE_INTELLIGENCE_BINDING.yaml"
# The committed architecture lock was cut under the architecture-only driver's schema id.
# It is re-cut under the shared lock schema by the first bundle refresh after the shared driver
# lands on main, because trusted replay can only attest a lock the default-branch driver
# reproduces; this transitional id is removed with that refresh.
TRANSITIONAL_LOCK_SCHEMA = "l9.gar.architecture-intelligence-bundle/v1"
COMPOSED_ENVELOPE = "l9.composed-projection/v1"
PROFILES_PATH = "semantics/projection_profiles.yaml"
COMPOSITIONS_PATH = "semantics/composition_profiles.yaml"


def _load_core() -> ModuleType:
    """The shared consumer verifier, loaded by path as tools/authority/verify_coding_projection.py
    loads it. The pack forbids residue directories, so the import writes no bytecode."""
    spec = importlib.util.spec_from_file_location("l9_projection_verifier_core", CORE_PATH)
    if spec is None or spec.loader is None or not CORE_PATH.is_file():
        print(
            json.dumps(
                {"status": "BLOCKED", "reason": "VERIFIER_CORE_UNRESOLVED", "path": str(CORE_PATH)},
                sort_keys=True,
            )
        )
        sys.exit(3)
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


core = _load_core()
Outcome = core.Outcome
content_digest = core.content_digest
bytes_digest = core.bytes_digest
resolve_authority_main = core.resolve_authority_main
LOCK_SCHEMAS = (core.LOCK_SCHEMA, TRANSITIONAL_LOCK_SCHEMA)


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


def profile_spec(binding: dict[str, Any]) -> Any:
    """The binding's coordinates for the shared verifier; it selects, it adds no check."""
    pins = binding["input"]["authority"]
    return core.ProfileSpec(
        ref=pins["projection_profile_ref"],
        profile_class=pins["projection_profile_class"],
        consumer=pins["projection_profile_consumer"],
        lock_schemas=LOCK_SCHEMAS,
        payload_schema=pins["projection_payload_schema"],
    )


def _expect(condition: bool, reason: str, **detail: Any) -> None:
    if not condition:
        raise Outcome("REJECTED", reason, **detail)


def _pins(binding: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    pins = binding["input"]["authority"]
    return (
        {"ref": pins["projection_profile_ref"], "digest": pins["projection_profile_digest"]},
        {"ref": pins["composition_profile_ref"], "digest": pins["composition_profile_digest"]},
    )


def _composed_receipt(
    bundle: Path,
    lock: dict[str, Any],
    composed: dict[str, Any],
    binding: dict[str, Any],
    tree: Any = None,
) -> None:
    """The composition receipt, through the shared receipt check, bound to every component."""
    projection_pin, composition_pin = _pins(binding)
    entry = lock["composed"]
    receipt = core.verify_receipt(
        bundle / entry["receipt"],
        tree=tree,
        operation="composition",
        subject=f"{composition_pin['ref']}#{projection_pin['ref']}",
        output_digest=composed["composition_digest"],
        profile=composition_pin,
        inputs=[
            {"ref": c["projection_ref"], "digest": c["projection_digest"]}
            for c in composed["components"]
        ],
        payload_schema=binding["input"]["authority"]["composed_payload_schema"],
        revision=lock["authority"]["revision"],
        source_class="composed",
    )
    producer, lock_producer = receipt["producer_identity"], lock["producer"]
    if producer.get("compiler") != lock_producer.get("compiler") or producer.get(
        "version"
    ) != lock_producer.get("version"):
        raise Outcome("REJECTED", "LOCK_PRODUCER_MISMATCH", source_class="composed")


def verify_bundle(bundle: Path, binding: dict[str, Any]) -> dict[str, Any]:
    """Structural verification: the bundle is the coherent output it claims to be.

    Every component goes through the shared ``verify_component`` without an authority checkout;
    the composed view is GAR's own consumption and is checked here."""
    pins = binding["input"]["authority"]
    if not (bundle / "bundle.lock.json").is_file():
        raise Outcome("BLOCKED", "ARCHITECTURE_INTELLIGENCE_BUNDLE_ABSENT", bundle=str(bundle))
    _, lock = _read_json(bundle / "bundle.lock.json")
    _expect(isinstance(lock, dict) and lock.get("schema") in LOCK_SCHEMAS, "LOCK_SCHEMA_MISMATCH")
    authority = lock.get("authority") or {}
    repository, revision = authority.get("repository"), authority.get("revision")
    if not (
        isinstance(repository, str)
        and repository == pins["repository"]
        and isinstance(revision, str)
        and core._SHA1.fullmatch(revision)
    ):
        raise Outcome("REJECTED", "AUTHORITY_IDENTITY_MISMATCH", observed=authority)
    projection_pin, composition_pin = _pins(binding)
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
    # Without an authority checkout the producer role cannot be read from the owner's
    # vocabulary; the binding's named producer stands in, and admitted mode checks the role.
    lock_producer = lock.get("producer")
    named = binding["input"]["producer"]["compiler"]
    if not isinstance(lock_producer, dict) or lock_producer.get("compiler") != named:
        raise Outcome(
            "REJECTED",
            "LOCK_PRODUCER_NOT_ASSIGNED_PROJECTION_ROLE",
            observed=lock_producer,
            assigned=[named],
            basis="binding",
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
        _, projections[cls] = core.verify_component(
            bundle,
            entry,
            {"source_class": cls, "source_ref": entry.get("source_ref")},
            tree=None,
            profile=projection_pin,
            payload_schema=pins["projection_payload_schema"],
            revision=revision,
            lock_producer=lock_producer,
        )

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
    _composed_receipt(bundle, lock, composed, binding)
    return {
        "lock": lock,
        "composition_digest": composed["composition_digest"],
        "composed": composed,
        "composed_path": composed_entry["path"],
        "component_digests": {c["source_class"]: c["projection_digest"] for c in components},
    }


def _require_root(root: Path) -> None:
    if not (root / ".git").exists():
        raise Outcome("BLOCKED", "AUTHORITY_ROOT_ABSENT", root=str(root))


def verify_currentness(
    root: Path, expect_revision: str, lock: dict[str, Any], binding: dict[str, Any]
) -> None:
    """The bundle is current at *expect_revision*: same revision, same source and profile bytes."""
    if not core._SHA1.fullmatch(expect_revision):
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
    and the binding's expected source classes are exactly that profile's sources. Law bytes are
    read from hash-checked commit objects (the shared ``PinnedTree``)."""
    tree = core.PinnedTree(root, expect_revision)
    registry = tree.load(core.SOURCES_PATH, "SOURCE_REGISTRY")
    paths = {s["id"]: s["path"] for s in (registry or {}).get("sources", []) if isinstance(s, dict)}
    for component in lock["components"]:
        path = paths.get(component["source_ref"])
        if path is None:
            raise Outcome("STALE", "SOURCE_UNREGISTERED", source_ref=component["source_ref"])
        current = bytes_digest(tree.read(path, "CANONICAL_SOURCE"))
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
            PROFILES_PATH,
            "projection_profiles",
            pins["projection_profile_ref"],
            pins["projection_profile_digest"],
        ),
        (
            COMPOSITIONS_PATH,
            "profiles",
            pins["composition_profile_ref"],
            pins["composition_profile_digest"],
        ),
    ):
        catalog = tree.load(catalog_path, "PROFILE_CATALOG")
        entries = [
            p
            for p in (catalog or {}).get(collection, [])
            if isinstance(p, dict) and p.get("id") == ref
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


def resolve_admission(
    root: Path, revision: str, main_tip: str, lock: dict[str, Any], binding: dict[str, Any]
) -> dict[str, Any]:
    """Whether *revision* is admitted global law, decided without the bundle lock by the shared
    admission resolver: integration into *main_tip*, currency there, and the binding's explicit
    decision record for each exact candidate (the projection and the composition profile)."""
    projection_pin, composition_pin = _pins(binding)
    admission = binding.get("admission") or {}
    result = core.resolve_admission(
        root,
        revision=revision,
        main_tip=main_tip,
        subjects=[
            {**projection_pin, "catalog": PROFILES_PATH, "collection": "projection_profiles"},
            {**composition_pin, "catalog": COMPOSITIONS_PATH, "collection": "profiles"},
        ],
        decisions=admission.get("decisions"),
        currency=lambda at: verify_content_at(root, at, lock, binding),
    )
    return {
        **result,
        "decision_record_required_by": (admission.get("decision_record") or {}).get("required_by"),
    }


def anchor(
    root: Path, bundle: Path, main_tip: str, result: dict[str, Any], binding: dict[str, Any]
) -> dict[str, Any]:
    """Re-verify an admitted bundle against the authority tip with the shared verifier.

    Every law byte comes from hash-checked commit objects of *main_tip*; the checkout's origin,
    HEAD and clean ``semantics/`` are observed; the producer role is read from the owner's
    vocabulary; and the composed receipt is shape-checked against the upstream schema."""
    anchored = core.verify_profile_bundle(root, bundle, main_tip, profile_spec(binding))
    _composed_receipt(bundle, result["lock"], result["composed"], binding, anchored["tree"])
    return anchored["coordinates"]


def _slot(**fields: Any) -> dict[str, Any]:
    """A complete `$.architecture_intelligence` slot: every field the run-state template owns,
    except the session-owned `citations`, so recording a verdict replaces the whole slot and no
    field of an earlier verdict survives into a later one."""
    slot: dict[str, Any] = {
        "binding_ref": BINDING_REF,
        "mode": None,
        "status": None,
        "bundle_status": None,
        "authority_status": None,
        "authoritative": False,
        "load_status": "NOT_LOADED",
        "bundle_ref": None,
        "authority_repository": None,
        "authority_revision": None,
        "projection_profile": None,
        "composition_profile": None,
        "composition_digest": None,
        "component_digests": {},
        "component_sources": {},
        "producer": None,
        "production_attested_by_verifier": False,
        "assurance_limitations": [],
        "verifier": "scripts/verify_architecture_intelligence.py",
        "currentness": None,
        "refusal_reason": None,
        "fallback_used": False,
    }
    unknown = set(fields) - set(slot)
    if unknown:
        raise KeyError(f"not a run-state slot field: {sorted(unknown)}")
    slot.update(fields)
    return slot


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
    return _slot(
        mode=mode,
        status=status,
        bundle_status="BUNDLE_VERIFIED",
        authority_status=admission,
        authoritative=authoritative,
        load_status=load_status,
        bundle_ref=binding["input"]["bundle"]["path"],
        authority_repository=lock["authority"]["repository"],
        authority_revision=lock["authority"]["revision"],
        projection_profile=lock["projection_profile"],
        composition_profile=lock["composition_profile"],
        composition_digest=result["composition_digest"],
        component_digests=result["component_digests"],
        component_sources={
            c["source_class"]: {
                "source_ref": c["source_ref"],
                "source_digest": c["source_digest"],
                "projection_digest": c["projection_digest"],
            }
            for c in lock["components"]
        },
        producer=lock.get("producer"),
        assurance_limitations=binding.get("assurance_limitations") or [],
        refusal_reason=admission.get("reason") if load_status == "NOT_LOADED" else None,
    )


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


def _refusal(outcome: Any, mode: str) -> dict[str, Any]:
    """The slot for a refused verdict; *outcome* is the shared verifier's ``Outcome``."""
    return _slot(
        mode=mode,
        status="UNAVAILABLE" if outcome.status == "BLOCKED" else outcome.status,
        refusal_reason=outcome.reason,
    )


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
    report: dict[str, Any] = {"verifier": "gar.architecture-intelligence/v3", "mode": args.mode}
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
            if admission["status"] == "ADMITTED_AND_CURRENT":
                coordinates = anchor(args.authority_root, bundle, main_tip, result, binding)
                admission = {**admission, "authority_root": coordinates}
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
        invalid = Outcome("REJECTED", "BUNDLE_STRUCTURE_INVALID")
        report.update(
            status="REJECTED",
            reason="BUNDLE_STRUCTURE_INVALID",
            detail={"error": f"{type(exc).__name__}: {exc}"},
            architecture_intelligence=_refusal(invalid, args.mode),
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return EXIT[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
