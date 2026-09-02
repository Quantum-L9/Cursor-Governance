#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from urllib.parse import urlparse

from _common import dump, load_json, schema
from jsonschema import Draft202012Validator

SKIP = {".git", "__pycache__", ".DS_Store"}


def inventory(path):
    root = Path(path)
    rows = []
    if not root.exists():
        return None, []
    items = (
        [root]
        if root.is_file()
        else [p for p in root.rglob("*") if p.is_file() and not any(x in SKIP for x in p.parts)]
    )
    for p in sorted(items):
        rel = p.name if root.is_file() else str(p.relative_to(root))
        raw = p.read_bytes()
        rows.append(
            {
                "path": rel,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "classification": "candidate",
            }
        )
    ident = {
        "kind": "file" if root.is_file() else "directory",
        "path": str(root.resolve()),
        "file_count": len(rows),
    }
    return ident, rows


def _validate_acquisition(receipt):
    errors = sorted(
        Draft202012Validator(schema("source-acquisition.schema.json")).iter_errors(receipt),
        key=lambda error: list(error.path),
    )
    messages = [error.message for error in errors]
    if receipt.get("adapter") == "remote_repository":
        identity = receipt.get("source_identity") or {}
        if identity.get("kind") != "repository" or not identity.get("immutable_ref"):
            messages.append("remote_repository requires repository identity with immutable_ref")
        if receipt.get("transport") == "connector" and not receipt.get("inventory"):
            messages.append("connector-backed remote_repository requires hashed inventory")
    if receipt.get("adapter") == "url":
        identity = receipt.get("source_identity") or {}
        if not any(
            identity.get(key)
            for key in ("content_sha256", "response_etag", "response_last_modified")
        ):
            messages.append("url requires response identity or content_sha256")
    return messages


def inventory_acquisition(path):
    receipt = load_json(path)
    errors = _validate_acquisition(receipt)
    if errors:
        return None, [], receipt.get("verification"), "invalid_acquisition_receipt", errors
    if receipt.get("status") not in {"PASS", "PARTIAL"}:
        return None, [], receipt.get("verification"), "acquisition_not_admitted", []
    root = receipt.get("materialized_root")
    expected = sorted(receipt.get("inventory") or [], key=lambda item: item["path"])
    if root:
        ident, rows = inventory(root)
        if ident is None:
            return None, [], receipt.get("verification"), "materialized_root_inaccessible", []
        if rows != expected:
            return None, [], receipt.get("verification"), "acquisition_inventory_mismatch", []
        verification = "CONTENT_REHASHED"
    else:
        rows = expected
        verification = receipt.get("verification")
    identity = dict(receipt.get("source_identity") or {})
    identity.update(
        {
            "adapter": receipt.get("adapter"),
            "locator": receipt.get("locator"),
            "transport": receipt.get("transport"),
            "file_count": len(rows),
        }
    )
    return identity, rows, verification, None, []


def _remote_block(locator):
    parsed = urlparse(locator)
    is_github_repo = (
        parsed.netloc.lower() == "github.com" and len(parsed.path.strip("/").split("/")) >= 2
    )
    adapter = "remote_repository" if is_github_repo else "url"
    required = (
        "immutable revision plus hashed inventory"
        if is_github_repo
        else "response identity or content digest"
    )
    return {
        "status": "BLOCKED",
        "reason": "remote_transport_required",
        "adapter": adapter,
        "locator": locator,
        "required": required,
        "transport_owner": "active runtime connector/repository client/HTTPS client",
        "next": "supply a source-acquisition receipt via --acquisition; do not fabricate local checkout proof",
    }


def main():
    if len(sys.argv) < 2:
        dump(
            {
                "status": "FAIL",
                "errors": ["usage: inventory_source.py <path>|--acquisition <receipt>"],
            }
        )
        return 2
    if sys.argv[1] == "--acquisition":
        if len(sys.argv) < 3:
            dump({"status": "FAIL", "errors": ["--acquisition requires a receipt path"]})
            return 2
        ident, rows, verification, error, errors = inventory_acquisition(sys.argv[2])
        if error:
            payload = {"status": "BLOCKED", "reason": error}
            if errors:
                payload["errors"] = errors
            dump(payload)
            return 3
        dump(
            {
                "status": "PASS",
                "source_identity": ident,
                "inventory": rows,
                "verification": verification,
            }
        )
        return 0
    locator = sys.argv[1]
    if urlparse(locator).scheme in {"http", "https"}:
        dump(_remote_block(locator))
        return 3
    ident, rows = inventory(locator)
    if ident is None:
        dump({"status": "BLOCKED", "reason": "donor_inaccessible"})
        return 3
    dump({"status": "PASS", "source_identity": ident, "inventory": rows})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
