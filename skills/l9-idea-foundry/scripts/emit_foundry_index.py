#!/usr/bin/env python3
"""Emit the deterministic downstream ingress for a realized Foundry payload."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from _common import (
    FoundryContractError,
    load_yaml_mapping,
    require_schema,
    semantic_yaml_digest,
    sha256_file,
    valid_sha256,
)

AUTHORITY_REL = Path("docs/idea-origin/AUTHORITY_MAP.yaml")
BLUEPRINT_REL = Path("docs/idea-origin/IMPLEMENTATION_BLUEPRINT.yaml")
TRACEABILITY_REL = Path("docs/idea-origin/TRACEABILITY.yaml")
UNKNOWN_REL = Path("docs/idea-origin/UNKNOWN_REGISTER.md")
RECEIPT_REL = Path("docs/idea-origin/FOUNDRY_RECEIPT.yaml")
ARCH_REL = Path(".l9/architecture.yaml")
INDEX_REL = Path("docs/idea-origin/FOUNDRY_INDEX.json")

EXPECTED_SCHEMAS = {
    AUTHORITY_REL: "l9.idea-foundry.authority-map/v1",
    BLUEPRINT_REL: "l9.idea-foundry.implementation-blueprint/v1",
    TRACEABILITY_REL: "l9.idea-foundry.traceability/v1",
    RECEIPT_REL: "l9.idea-foundry.receipt/v1",
    ARCH_REL: "l9.architecture-spec/v1",
}

PLAN_HANDOFFS = {"EMBEDDED", "EMBEDDED_PRE_BIRTH"}


def artifact_entry(root: Path, rel: Path, semantic: bool = True) -> dict[str, str]:
    path = root / rel
    return {
        "path": rel.as_posix(),
        "digest": semantic_yaml_digest(path) if semantic else sha256_file(path),
    }


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FoundryContractError(f"{label} must be a mapping")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit docs/idea-origin/FOUNDRY_INDEX.json as the post-realization single ingress"
    )
    parser.add_argument("payload", type=Path)
    parser.add_argument("--inventory-digest", required=True)
    parser.add_argument("--plan-ref", required=True)
    parser.add_argument("--plan-digest", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    root = args.payload.resolve()
    if not root.is_dir():
        raise SystemExit(f"payload is not a directory: {root}")
    if not valid_sha256(args.inventory_digest):
        raise SystemExit("--inventory-digest must be sha256:<64 lowercase hex>")
    if not valid_sha256(args.plan_digest):
        raise SystemExit("--plan-digest must be sha256:<64 lowercase hex>")
    if not args.plan_ref.strip():
        raise SystemExit("--plan-ref must be non-empty")

    loaded: dict[Path, dict[str, Any]] = {}
    try:
        for rel, schema in EXPECTED_SCHEMAS.items():
            path = root / rel
            if not path.is_file():
                raise FoundryContractError(f"missing required control artifact: {rel.as_posix()}")
            mapping = load_yaml_mapping(path)
            require_schema(mapping, schema, rel.as_posix())
            loaded[rel] = mapping
    except FoundryContractError as exc:
        raise SystemExit(str(exc)) from exc

    unknown_path = root / UNKNOWN_REL
    if not unknown_path.is_file():
        raise SystemExit(f"missing required control artifact: {UNKNOWN_REL.as_posix()}")

    receipt = loaded[RECEIPT_REL]
    source = _mapping(receipt.get("source"), "FOUNDRY_RECEIPT.source")
    composition = _mapping(receipt.get("composition"), "FOUNDRY_RECEIPT.composition")
    planning = _mapping(composition.get("planning"), "FOUNDRY_RECEIPT.composition.planning")
    deployment = _mapping(receipt.get("deployment"), "FOUNDRY_RECEIPT.deployment")
    run = _mapping(receipt.get("run"), "FOUNDRY_RECEIPT.run")

    if planning.get("owner") != "l9-plan-simple":
        raise SystemExit("FOUNDRY_RECEIPT planning owner must be l9-plan-simple")
    if planning.get("validation_status") != "PASSED":
        raise SystemExit("FOUNDRY_RECEIPT planning validation_status must be PASSED")
    handoff = planning.get("plan_handoff")
    if handoff not in PLAN_HANDOFFS:
        raise SystemExit(f"FOUNDRY_RECEIPT plan_handoff must be one of {sorted(PLAN_HANDOFFS)}")
    if deployment.get("performed") is not False:
        raise SystemExit("FOUNDRY_RECEIPT deployment.performed must be false")

    receipt_plan_digest = planning.get("plan_digest")
    if receipt_plan_digest != args.plan_digest:
        raise SystemExit("--plan-digest does not match FOUNDRY_RECEIPT planning.plan_digest")
    receipt_plan_ref = planning.get("plan_document_ref")
    if receipt_plan_ref != args.plan_ref:
        raise SystemExit("--plan-ref does not match FOUNDRY_RECEIPT planning.plan_document_ref")
    receipt_inventory = source.get("inventory_digest")
    if receipt_inventory != args.inventory_digest:
        raise SystemExit("--inventory-digest does not match FOUNDRY_RECEIPT source.inventory_digest")

    intelligence_harvest = composition.get("intelligence_harvest") or {"status": "NOT_APPLICABLE"}
    gar = composition.get("gar") or {"status": "NOT_USED"}

    artifacts = {
        "authority_map": artifact_entry(root, AUTHORITY_REL),
        "implementation_blueprint": artifact_entry(root, BLUEPRINT_REL),
        "traceability": artifact_entry(root, TRACEABILITY_REL),
        "unknown_register": artifact_entry(root, UNKNOWN_REL, semantic=False),
        "foundry_receipt": artifact_entry(root, RECEIPT_REL),
        "architecture": artifact_entry(root, ARCH_REL),
    }

    payload = {
        "schema": "l9.idea-foundry.index/v1",
        "source": {
            "input_ref": source.get("input_ref"),
            "inventory_digest": args.inventory_digest,
            "source_revision": source.get("source_revision"),
        },
        "compiled_intent": {
            "pre_code_ingress": BLUEPRINT_REL.as_posix(),
            "authority_map": artifacts["authority_map"],
            "implementation_blueprint": artifacts["implementation_blueprint"],
            "raw_source_policy": "EVIDENCE_ONLY_AFTER_ACCEPTANCE",
        },
        "composition": {
            "intelligence_harvest": intelligence_harvest,
            "gar": gar,
            "planning": {
                "owner": "l9-plan-simple",
                "plan_document_ref": args.plan_ref,
                "plan_digest": args.plan_digest,
                "validation_status": "PASSED",
                "plan_handoff": handoff,
                "compatibility_fallback": bool(planning.get("compatibility_fallback", False)),
            },
        },
        "artifacts": artifacts,
        "lineage": {
            "inventory_digest": args.inventory_digest,
            "authority_digest": artifacts["authority_map"]["digest"],
            "blueprint_digest": artifacts["implementation_blueprint"]["digest"],
            "traceability_digest": artifacts["traceability"]["digest"],
            "plan_digest": args.plan_digest,
        },
        "resume": {
            "entrypoint": INDEX_REL.as_posix(),
            "current_state": run.get("status"),
            "repair_policy": "EARLIEST_INVALID_LAYER",
            "after_remote_birth": "ORIGIN_EVIDENCE_ONLY_REPO_GROUND_TRUTH_WINS",
        },
        "deployment": {"performed": False},
    }

    out = args.out.resolve() if args.out else (root / INDEX_REL)
    if out != root / INDEX_REL:
        # The contract is useful because the newborn carries it. Alternate paths are for tests only.
        if root not in out.parents:
            raise SystemExit("FOUNDRY_INDEX must be emitted inside the payload repository")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"FOUNDRY_INDEX: PASS digest={sha256_file(out)} handoff={handoff}")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
