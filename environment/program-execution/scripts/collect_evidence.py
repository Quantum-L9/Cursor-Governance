#!/usr/bin/env python3
"""Collect admission evidence into the Blueprint Evidence Catalog (pre-bootstrap).

The compiler stamps every EVID-* entry as ``planned`` / ``revision: UNKNOWN``.
This tool binds one entry to the operator's collected evidence, regenerates the
Blueprint MANIFEST.yaml, and re-validates in template mode.

Ordering is load-bearing: bootstrap freezes the Blueprint source digests into
the Program Lock, so collecting evidence AFTER bootstrap silently poisons every
later verification with STALE. This tool refuses when a program-lock already
binds the Blueprint.

Usage:
    python3 collect_evidence.py --blueprint <dir> --evidence-id EVID-002 \\
        --revision <sha-or-ref> [--digest <sha256>] [--notes "..."] \\
        [--producer operator] [--expires-at <ISO-8601>]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Sibling import safety (see compile_campaign_source.py for rationale).
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from blueprint_ops import (  # noqa: E402
    dump_yaml,
    load_yaml,
    lock_exists_for_blueprint,
    validate_blueprint,
    write_manifest,
)

PE_ROOT = Path(__file__).resolve().parents[1]
#: What the compiler writes before evidence is bound; never accepted as a binding.
UNKNOWN_REVISION = "UNKNOWN"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def collect_evidence(
    blueprint: Path,
    *,
    evidence_id: str,
    revision: str | None,
    digest: str | None,
    notes: str | None,
    producer: str,
    expires_at: str | None,
) -> dict[str, Any]:
    root = blueprint.resolve()
    catalog_path = root / "EVIDENCE_CATALOG.yaml"
    if not catalog_path.is_file():
        raise RuntimeError(f"not a Blueprint root (EVIDENCE_CATALOG.yaml missing): {root}")
    if lock_exists_for_blueprint(root):
        raise RuntimeError(
            "a Controller workspace already bootstrapped from this Blueprint; "
            "catalog edits after bootstrap poison every verification with STALE — "
            "start a fresh workspace instead"
        )

    catalog = load_yaml(catalog_path)
    entries = list(catalog.get("evidence") or [])
    entry = next((item for item in entries if item.get("id") == evidence_id), None)
    if entry is None:
        known = ", ".join(sorted(item.get("id", "?") for item in entries)) or "<none>"
        raise RuntimeError(f"unknown evidence id {evidence_id!r}; catalog has: {known}")

    bound_revision = str(revision).strip() if revision is not None else ""
    if not bound_revision or bound_revision.upper() == UNKNOWN_REVISION:
        # The compiler stamps `revision: UNKNOWN` on purpose: it is the marker
        # that no evidence has been bound yet. Marking the entry `available`
        # while keeping that marker recorded evidence about nothing.
        raise RuntimeError(
            f"evidence {evidence_id} needs the revision it was observed at; "
            f"got {revision!r}. Pass --revision <sha-or-ref>."
        )
    entry.update(
        {
            "revision": bound_revision,
            "digest": digest,
            "method": "read_only_inspection",
            "environment": "local",
            "producer": producer,
            "produced_at": _utc_now(),
            "expires_at": expires_at,
            "result": "INFORMATIONAL",
            "status": "available",
        }
    )
    if notes:
        entry["notes"] = notes

    catalog["evidence"] = entries
    dump_yaml(catalog_path, catalog)
    write_manifest(root, "collect_evidence")

    errors = validate_blueprint(root, "template")
    if errors:
        raise RuntimeError(
            "Blueprint failed template validation after evidence collection: "
            + "; ".join(errors[:5])
        )
    return {
        "status": "COLLECTED",
        "blueprint": str(root),
        "evidence_id": evidence_id,
        "revision": entry.get("revision"),
        "producer": producer,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="collect_evidence")
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--evidence-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--digest", default=None)
    parser.add_argument("--notes", default=None)
    parser.add_argument("--producer", default="operator")
    parser.add_argument("--expires-at", default=None)
    args = parser.parse_args(argv)
    try:
        result = collect_evidence(
            args.blueprint,
            evidence_id=args.evidence_id,
            revision=args.revision,
            digest=args.digest,
            notes=args.notes,
            producer=args.producer,
            expires_at=args.expires_at,
        )
    except RuntimeError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
