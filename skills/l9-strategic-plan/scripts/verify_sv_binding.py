#!/usr/bin/env python3
"""Admitted Strategic Value consumer verifier. Requires genuine compiler + real artifacts.

This script never fabricates receipts or reports a canonical binding from its own
unit tests. It delegates semantic replay to l9_semantic_compiler at the exact
admitted .github git commit, then applies the pinned admission artifact lock.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROFILE = "l9.projection/strategic-planner-value@1"
COMPOSITION = "l9.compose/strategic-planner-value@1"
MODEL = "l9.strategic.value@1"
CONTRACT = "l9.contract/strategic-value-assessment@1"
SOURCE_CLASSES = frozenset(
    {"strategic_value_model", "vocabulary", "invariants", "contracts", "authority_model"}
)
ADMITTED_INVARIANTS = frozenset({"L9-SV-001", "L9-SV-002"})
REPO = "Quantum-L9/.github"
MANIFEST_SCHEMA = "l9.planner-strategic-value-binding-request/v1"
LOCK_REL = "references/strategic-value-admission-lock.json"


class BindingBlocked(Exception):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise BindingBlocked(reason)


def parse_json(path: Path) -> dict:
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise BindingBlocked(f"READ_OR_PARSE_FAILED: {path}: {e}") from e
    need(isinstance(o, dict), f"EXPECTED_JSON_OBJECT: {path}")
    return o


def read_lock(path: Path | None = None) -> dict:
    p = path or Path(__file__).resolve().parents[1] / LOCK_REL
    lock = parse_json(p)
    need(
        lock.get("schema") == "l9.planner-strategic-value-admission-lock/v1",
        "ADMISSION_LOCK_SCHEMA_MISMATCH",
    )
    need(
        lock.get("repository") == REPO and lock.get("release") == "v3.32.0",
        "ADMISSION_LOCK_IDENTITY_MISMATCH",
    )
    need(
        lock.get("model") == MODEL and lock.get("contract") == CONTRACT,
        "ADMISSION_LOCK_MODEL_CONTRACT_MISMATCH",
    )
    need(
        lock.get("projection_profile") == PROFILE
        and lock.get("composition_profile") == COMPOSITION,
        "ADMISSION_LOCK_PROFILE_MISMATCH",
    )
    need(
        frozenset(lock.get("new_global_invariants", [])) == ADMITTED_INVARIANTS,
        "ADMISSION_LOCK_EXPECTS_NONADMITTED_SV_LAWS",
    )
    need(
        set(lock.get("required_source_classes", [])) == SOURCE_CLASSES,
        "ADMISSION_LOCK_MISSING_SOURCE_CLASSES",
    )
    need(
        set(lock.get("producer_projection_digests", {})) == SOURCE_CLASSES,
        "ADMISSION_LOCK_DIGEST_COVERAGE",
    )
    hashes = list(lock["producer_projection_digests"].values()) + [
        lock.get("producer_composition_digest"),
        lock.get("composition_profile_digest"),
    ]
    need(
        all(isinstance(h, str) and re.fullmatch("sha256:[0-9a-f]{64}", h) for h in hashes),
        "ADMISSION_LOCK_DIGEST_FORMAT",
    )
    return lock


def source_set(manifest: dict) -> dict[str, dict]:
    need(manifest.get("schema") == MANIFEST_SCHEMA, "BINDING_REQUEST_SCHEMA_MISMATCH")
    projections = manifest.get("projections")
    need(
        isinstance(projections, list) and len(projections) == 5, "FIVE_SOURCE_PROJECTIONS_REQUIRED"
    )
    out: dict[str, dict] = {}
    for item in projections:
        need(isinstance(item, dict), "PROJECTION_ENTRY_INVALID")
        cls = item.get("source_class")
        need(
            isinstance(cls, str) and cls in SOURCE_CLASSES and (cls not in out),
            "UNEXPECTED_OR_DUPLICATE_SOURCE_CLASS",
        )
        for f in ("artifact_path", "receipt_path"):
            need(
                isinstance(item.get(f), str)
                and item[f].strip()
                and (not item[f].startswith("REPLACE")),
                f"MISSING_{f.upper()}: {cls}",
            )
        out[cls] = item
    need(set(out) == SOURCE_CLASSES, "EXACT_FIVE_SOURCE_COVERAGE_REQUIRED")
    for f in ("composition_artifact_path", "composition_receipt_path"):
        need(
            isinstance(manifest.get(f), str)
            and manifest[f].strip()
            and (not manifest[f].startswith("REPLACE")),
            f"MISSING_{f.upper()}",
        )
    return out


def _status_pass(artifact: dict, receipt: dict, role: str) -> None:
    need(receipt.get("result") == "pass", f"{role}: NOT_A_PASS_RECEIPT")
    basis = receipt.get("verification_basis")
    need(
        isinstance(basis, dict)
        and basis.get("coverage") == "complete"
        and (not basis.get("unresolved_criteria")),
        f"{role}: UNRESOLVED_PRODUCER_VERIFICATION",
    )
    need(
        receipt.get("producer_identity", {}).get("compiler") == "l9-semantic-compiler",
        f"{role}: UNEXPECTED_PRODUCER",
    )


def _load_compiler():
    try:
        from l9_semantic_compiler.engine.registry import CanonicalAuthority
        from l9_semantic_compiler.passes.projection import (
            verify_composed_projection,
            verify_composed_receipt,
            verify_projection_artifact,
            verify_projection_receipt,
        )

        return (
            CanonicalAuthority,
            verify_projection_artifact,
            verify_projection_receipt,
            verify_composed_projection,
            verify_composed_receipt,
        )
    except ImportError as e:
        raise BindingBlocked(
            "CANONICAL_COMPILER_UNAVAILABLE: install the admitted compatible "
            "l9-semantic-compiler-engine; " + str(e)
        ) from e


def verify_binding(
    authority_root: Path, manifest_path: Path, *, engine=None, lock_path: Path | None = None
) -> dict:
    """Only the compiler engine can grant canonical replay; synthetic engines are not proof."""
    lock = read_lock(lock_path)
    m = parse_json(manifest_path)
    need(
        m.get("authority_revision") == lock["admission_revision"],
        "AUTHORITY_REVISION_NOT_ADMITTED_RELEASE",
    )
    entries = source_set(m)
    canon_cls, verify_projection, verify_receipt, verify_composition, verify_composed_receipt = (
        engine or _load_compiler()
    )
    try:
        authority = canon_cls(authority_root, m["authority_revision"], repository=REPO)
        profile = authority.resolve_profile(PROFILE)
        source_defs = profile.record["sources"]
        need(set(source_defs) == SOURCE_CLASSES, "CANONICAL_PROFILE_SOURCE_COVERAGE_DRIFT")
        cm = authority.resolve_profile(COMPOSITION)
        need(
            cm.record.get("composes", {}).get("projection_profile") == PROFILE,
            "CANONICAL_COMPOSITION_PROFILE_WRONG_INPUT",
        )
        need(cm.digest == lock["composition_profile_digest"], "COMPOSITION_PROFILE_DIGEST_DRIFT")
        need(
            set(cm.record.get("required_provenance", []))
            == {
                "source_projection_refs",
                "source_projection_digests",
                "composition_profile_ref",
                "composition_profile_digest",
            },
            "CANONICAL_REQUIRED_PROVENANCE_DRIFT",
        )
        source_model = authority.load("semantics/strategic_value_model.yaml").document
        need(
            source_model.get("artifact_id") == MODEL and source_model.get("canonical") is True,
            "ADMITTED_MODEL_MISSING",
        )
        sv_invariants = {
            i
            for i in source_model.get("governed_by", {}).get("invariants", [])
            if isinstance(i, str) and i.startswith("L9-SV-")
        }
        need(sv_invariants == ADMITTED_INVARIANTS, "RETIRED_CANDIDATE_LAW_CREEP")
        need(
            source_model.get("identity", {}).get("assessment_contract_ref") == CONTRACT,
            "MODEL_ASSESSMENT_CONTRACT_DRIFT",
        )
        need(
            source_model.get("assessment_applicability", {}).get("claim_gate")
            == (
                "applies_only_to_assessments_asserting_objective_relative_"
                "quantitative_strategic_value"
            ),
            "ASSESSMENT_APPLICABILITY_DRIFT",
        )
        artifacts: list[dict] = []
        for cls in sorted(SOURCE_CLASSES):
            entry = entries[cls]
            src = authority.resolve_source(profile.catalog, cls)
            artifact = parse_json((manifest_path.parent / entry["artifact_path"]).resolve())
            receipt = parse_json((manifest_path.parent / entry["receipt_path"]).resolve())
            need(artifact.get("source_ref") == src.ref, f"{cls}: SOURCE_IDENTITY_MISMATCH")
            need(
                artifact.get("projection_profile_ref") == PROFILE
                and artifact.get("projection_profile_digest") == profile.digest,
                f"{cls}: WRONG_PROFILE_OR_DIGEST",
            )
            need(
                artifact.get("projection_digest") == lock["producer_projection_digests"][cls],
                f"{cls}: DIFFERS_FROM_ADMITTED_PRODUCER_DIGEST",
            )
            need(
                receipt.get("governing_coordinates", {}).get("revision")
                == lock["admission_revision"]
                and receipt.get("governing_coordinates", {}).get("repository") == REPO,
                f"{cls}: RECEIPT_GOVERNING_COORDINATES_MISMATCH",
            )
            _status_pass(artifact, receipt, cls)
            result = verify_projection(authority, artifact)
            need(
                result.get("result") in (None, "pass") and (not result.get("unresolved_criteria")),
                f"{cls}: PROJECTION_REPLAY_UNRESOLVED",
            )
            rec = verify_receipt(authority, artifact, receipt)
            need(rec.get("status") == "pass", f"{cls}: RECEIPT_REPLAY_FAILED")
            artifacts.append(artifact)
        composed = parse_json((manifest_path.parent / m["composition_artifact_path"]).resolve())
        receipt = parse_json((manifest_path.parent / m["composition_receipt_path"]).resolve())
        need(
            composed.get("composition_profile", {}).get("ref") == COMPOSITION
            and composed.get("composition_profile", {}).get("digest") == cm.digest,
            "COMPOSITION_PROFILE_BINDING_MISMATCH",
        )
        need(
            composed.get("composition_digest") == lock["producer_composition_digest"],
            "COMPOSITION_DIFFERS_FROM_ADMITTED_PRODUCER_DIGEST",
        )
        expected = {f"{PROFILE}#{c['source_ref']}": c["projection_digest"] for c in artifacts}
        comp_items = composed.get("components")
        need(
            isinstance(comp_items, list) and len(comp_items) == 5,
            "COMPOSITION_EXACT_FIVE_COMPONENTS_REQUIRED",
        )
        observed = {
            c.get("projection_ref"): c.get("projection_digest")
            for c in comp_items
            if isinstance(c, dict)
        }
        need(
            len(observed) == 5 and observed == expected,
            "COMPOSITION_COMPONENT_COVERAGE_OR_DIGEST_MISMATCH",
        )
        payload = composed.get("payload")
        need(
            isinstance(payload, dict) and set(payload) == SOURCE_CLASSES,
            "COMPOSITION_NAMESPACED_PAYLOAD_COVERAGE_MISMATCH",
        )
        _status_pass(composed, receipt, "composition")
        need(
            receipt.get("governing_coordinates", {}).get("revision") == lock["admission_revision"],
            "COMPOSITION_RECEIPT_GOVERNING_REVISION_MISMATCH",
        )
        report = verify_composition(authority, composed, artifacts)
        need(
            report.get("result") in (None, "pass") and (not report.get("unresolved_criteria")),
            "COMPOSITION_REPLAY_UNRESOLVED",
        )
        rec = verify_composed_receipt(authority, composed, artifacts, receipt)
        need(rec.get("status") == "pass", "COMPOSITION_RECEIPT_REPLAY_FAILED")
    except BindingBlocked:
        raise
    except Exception as e:
        raise BindingBlocked(
            f"CANONICAL_ENGINE_REFUTED_OR_COULD_NOT_VERIFY: {type(e).__name__}: {e}"
        ) from e
    return {
        "status": "CANONICAL_BINDING_VERIFIED" if engine is None else "SYNTHETIC_ADAPTER_TEST_ONLY",
        "repository": REPO,
        "admission_release": lock["release"],
        "admission_revision": lock["admission_revision"],
        "projection_profile": PROFILE,
        "composition_profile": COMPOSITION,
        "source_projection_count": 5,
        "projection_receipts_pass": 5,
        "composition_receipt_pass": 1,
        "composition_digest": composed["composition_digest"],
        "authority_effect": "none",
        "numerical_model_verified": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--authority-root",
        type=Path,
        required=True,
        help="Git checkout containing exact admitted .github objects",
    )
    p.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Paths of real five projection+receipt pairs and composed artifact+receipt",
    )
    ns = p.parse_args(argv)
    try:
        result = verify_binding(ns.authority_root, ns.manifest.resolve())
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except BindingBlocked as e:
        print(json.dumps({"status": "CANONICAL_BINDING_BLOCKED", "reason": str(e)}, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
