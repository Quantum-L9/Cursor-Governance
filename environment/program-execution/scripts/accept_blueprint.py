#!/usr/bin/env python3
"""Accept a compiled Blueprint — the operator's admission act.

Implements the pipeline step ``accept_blueprint_only_after_evidence_and_authority_resolution``.

Ordering is load-bearing:

1. flip ``program.definition_status`` to ``accepted`` FIRST (the instantiated
   validator hard-requires the accepted status, so validating a draft would
   always fail);
2. scan for unresolved placeholders (belt-and-braces on top of the compiler's
   own scan);
3. write an append-only acceptance receipt (evidence + actor bound);
4. regenerate the Blueprint MANIFEST.yaml via the canonical generator;
5. re-validate in instantiated mode — any error aborts with a non-zero exit.

Refuses when a Controller workspace already bootstrapped from this Blueprint
(post-bootstrap acceptance would poison every verification with STALE).

Usage:
    python3 accept_blueprint.py --blueprint <dir> --actor <name> [--evidence-id EVID-*]...
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

# Sibling import safety (see compile_campaign_source.py for rationale).
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from blueprint_ops import (  # noqa: E402
    dump_yaml,
    load_yaml,
    lock_exists_for_blueprint,
    scan_placeholders,
    validate_blueprint,
    write_manifest,
)

PE_ROOT = Path(__file__).resolve().parents[1]
RECEIPT_SCHEMA_PATH = (
    PE_ROOT
    / "core"
    / "program-execution-blueprint-template"
    / "schemas"
    / "acceptance-receipt.schema.json"
)


def _restore_unaccepted(
    program_path: Path, original_program: bytes, receipt_path: Path, root: Path
) -> None:
    """Undo a partial acceptance so the next attempt starts from a clean tree."""
    program_path.write_bytes(original_program)
    receipt_path.unlink(missing_ok=True)
    write_manifest(root, "accept_blueprint")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _validate_receipt(receipt: dict[str, Any]) -> None:
    schema = json.loads(RECEIPT_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(receipt), key=lambda item: list(item.path)
    )
    if errors:
        raise RuntimeError(
            "acceptance receipt schema: "
            + "; ".join(
                f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors
            )
        )


def accept_blueprint(blueprint: Path, *, actor: str, evidence_ids: list[str]) -> dict[str, Any]:
    root = blueprint.resolve()
    program_path = root / "PROGRAM.yaml"
    if not program_path.is_file():
        raise RuntimeError(f"not a Blueprint root (PROGRAM.yaml missing): {root}")
    if lock_exists_for_blueprint(root):
        raise RuntimeError(
            "a Controller workspace already bootstrapped from this Blueprint; "
            "acceptance must precede bootstrap (start a fresh workspace to re-accept)"
        )

    program = load_yaml(program_path)
    status = (program.get("program") or {}).get("definition_status")
    if status == "accepted":
        raise RuntimeError(f"Blueprint already accepted: {root}")

    # Every check that needs no write runs BEFORE PROGRAM.yaml changes. A
    # status flipped ahead of a failed check left the tree "already accepted"
    # with a stale manifest, and every retry refused.
    placeholders = scan_placeholders(root)
    if placeholders:
        raise RuntimeError(
            "unresolved placeholders in Blueprint; refuse acceptance: "
            + "; ".join(placeholders[:5])
        )
    receipt = {
        "schema": "program-execution-blueprint.acceptance-receipt.v1",
        "schema_version": "1.0.0",
        "program_id": program["program"]["id"],
        "accepted_at": _utc_now(),
        "actor": actor,
        "evidence_ids": sorted(set(evidence_ids)),
    }
    _validate_receipt(receipt)

    original_program = program_path.read_bytes()
    receipt_path = root / "ACCEPTANCE_RECEIPT.yaml"
    program["program"]["definition_status"] = "accepted"
    dump_yaml(program_path, program)
    try:
        dump_yaml(receipt_path, receipt)
        write_manifest(root, "accept_blueprint")
        errors = validate_blueprint(root, "instantiated")
    except BaseException:
        _restore_unaccepted(program_path, original_program, receipt_path, root)
        raise
    if errors:
        _restore_unaccepted(program_path, original_program, receipt_path, root)
        raise RuntimeError(
            "Blueprint failed instantiated validation; acceptance not recorded: "
            + "; ".join(errors[:5])
        )
    return {
        "status": "ACCEPTED",
        "blueprint": str(root),
        "program_id": program["program"]["id"],
        "actor": actor,
        "evidence_ids": receipt["evidence_ids"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="accept_blueprint")
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--evidence-id", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        result = accept_blueprint(args.blueprint, actor=args.actor, evidence_ids=args.evidence_id)
    except RuntimeError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
