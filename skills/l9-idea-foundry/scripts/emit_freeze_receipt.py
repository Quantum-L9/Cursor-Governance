#!/usr/bin/env python3
"""Emit an external receipt binding a clean Foundry payload git revision."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from _common import (
    FoundryContractError,
    git_require,
    sha256_file,
    tracked_tree_digest,
    valid_sha256,
)

INDEX_REL = Path("docs/idea-origin/FOUNDRY_INDEX.json")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=Path)
    parser.add_argument("--inventory-digest", required=True)
    parser.add_argument("--plan-ref", required=True)
    parser.add_argument("--plan-digest", required=True)
    parser.add_argument("--harvest-ref")
    parser.add_argument("--harvest-receipt-ref")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    root = args.payload.resolve()
    out = args.out.resolve()
    if not root.is_dir():
        raise SystemExit(f"payload is not a directory: {root}")
    if out == root or root in out.parents:
        raise SystemExit("freeze receipt must be written outside the payload repository")
    if not valid_sha256(args.inventory_digest):
        raise SystemExit("--inventory-digest must be sha256:<64 lowercase hex>")
    if not valid_sha256(args.plan_digest):
        raise SystemExit("--plan-digest must be sha256:<64 lowercase hex>")
    if not args.plan_ref.strip():
        raise SystemExit("--plan-ref must be non-empty")

    index_path = root / INDEX_REL
    if not index_path.is_file():
        raise SystemExit(
            f"missing {INDEX_REL.as_posix()}; emit the downstream Foundry index before freezing"
        )
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot parse {INDEX_REL.as_posix()}: {exc}") from exc
    if index.get("schema") != "l9.idea-foundry.index/v1":
        raise SystemExit("FOUNDRY_INDEX schema mismatch")
    lineage = index.get("lineage")
    if not isinstance(lineage, dict):
        raise SystemExit("FOUNDRY_INDEX missing lineage mapping")
    if lineage.get("inventory_digest") != args.inventory_digest:
        raise SystemExit("FOUNDRY_INDEX inventory digest does not match --inventory-digest")
    if lineage.get("plan_digest") != args.plan_digest:
        raise SystemExit("FOUNDRY_INDEX plan digest does not match --plan-digest")

    try:
        inside = git_require(root, "rev-parse", "--is-inside-work-tree").strip()
        if inside != "true":
            raise FoundryContractError("payload is not a git working tree")
        dirty = git_require(root, "status", "--porcelain", "--untracked-files=all")
        if dirty.strip():
            raise FoundryContractError("payload git tree is not clean")
        head = git_require(root, "rev-parse", "HEAD").strip()
        records, tree_digest = tracked_tree_digest(root)
    except FoundryContractError as exc:
        raise SystemExit(str(exc)) from exc

    payload = {
        "schema": "l9.idea-foundry.freeze-receipt/v1",
        "git_revision": head,
        "tracked_file_count": len(records),
        "tracked_tree_digest": tree_digest,
        "inventory_digest": args.inventory_digest,
        "plan_ref": args.plan_ref,
        "plan_digest": args.plan_digest,
        "foundry_index_ref": INDEX_REL.as_posix(),
        "foundry_index_digest": sha256_file(index_path),
        "harvest_ref": args.harvest_ref,
        "harvest_receipt_ref": args.harvest_receipt_ref,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"FOUNDRY_FREEZE: PASS head={head} files={len(records)} tree={tree_digest}")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
