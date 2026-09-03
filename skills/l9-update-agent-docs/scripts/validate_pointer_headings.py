#!/usr/bin/env python3
"""Backward-compatible repo-docs front door with pointer-stack validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from repo_docs import audit_repository, pointer_validate_root, resolve_under_root


def validate_root(root: Path) -> dict:
    """Preserve the original pointer-only callable for tests and focused callers."""
    return pointer_validate_root(root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root to inspect")
    parser.add_argument("--changed-since")
    parser.add_argument("--adapter")
    parser.add_argument("--receipt", help="write repo-docs-receipt JSON under the repo root")
    parser.add_argument("--llms-base-url")
    parser.add_argument("--write-llms", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    receipt = audit_repository(
        root,
        changed_since=args.changed_since,
        adapter=args.adapter,
        llms_base_url_value=args.llms_base_url,
        write_llms=args.write_llms,
    )

    if args.receipt:
        target = resolve_under_root(root, args.receipt)
        if target is None:
            print(f"BLOCKED: receipt path escapes repository root: {args.receipt}", file=sys.stderr)
            return 2
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        pointer = next(
            (
                item
                for item in receipt.get("validators_executed", [])
                if item.get("name") == "pointer_headings"
            ),
            None,
        )
        pointer_result = validate_root(root)
        for item in pointer_result["files"]:
            print(f"{item['path']}: {item['status']}")
        if pointer:
            for finding in pointer.get("findings", []):
                print(f"  - {finding}")
        impacted = receipt.get("impact", {}).get("impacted_surfaces", [])
        if impacted:
            print("IMPACTED: " + ", ".join(impacted))
        print(receipt["final_status"])
        print("RECEIPT: " + json.dumps(receipt, sort_keys=True))

    return {"PASS": 0, "PARTIAL": 0, "BLOCKED": 2, "FAIL": 1}[receipt["final_status"]]


if __name__ == "__main__":
    raise SystemExit(main())
