#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from repo_docs import (
    audit_repository,
    exit_code_for_receipt,
    pointer_validate_root,
    resolve_under_root,
)


def validate_root(root: Path) -> dict:
    return pointer_validate_root(root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--changed-since")
    parser.add_argument("--adapter")
    parser.add_argument("--receipt")
    parser.add_argument("--llms-base-url")
    parser.add_argument("--write-llms", action="store_true")
    parser.add_argument("--harvest")
    parser.add_argument("--fail-on-partial", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    receipt = audit_repository(
        root,
        changed_since=args.changed_since,
        adapter=args.adapter,
        llms_base_url_value=args.llms_base_url,
        write_llms=args.write_llms,
        harvest_path=args.harvest,
    )
    if args.receipt:
        target = resolve_under_root(root, args.receipt)
        if target is None:
            return 2
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        for item in validate_root(root)["files"]:
            print(f"{item['path']}: {item['status']}")
        print(receipt["final_status"])
    return exit_code_for_receipt(receipt, args.fail_on_partial)


if __name__ == "__main__":
    raise SystemExit(main())
