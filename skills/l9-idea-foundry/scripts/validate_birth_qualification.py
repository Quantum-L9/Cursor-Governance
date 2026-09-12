#!/usr/bin/env python3
"""Revalidate a Foundry birth-qualification receipt against exact source and factory state."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

SCHEMA = "l9.idea-foundry.birth-qualification/v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=False)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate exact-state Foundry factory qualification evidence.")
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    try:
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        if receipt.get("schema") != SCHEMA:
            raise RuntimeError("unexpected qualification schema")
        if receipt.get("status") not in {"FACTORY_COMPILE_PASS", "LOCAL_BIRTH_PASS"}:
            raise RuntimeError("qualification status is not a passing state")
        source = Path(receipt["source"]["path"])
        factory = Path(receipt["factory"]["path"])
        freeze = Path(receipt["source"]["foundry_freeze_receipt"])
        probe = Path(receipt["factory"]["probe"])
        contract = Path(receipt["compiled_birth_payload"]["path"])
        if git(source, "rev-parse", "HEAD") != receipt["source"]["revision"]:
            raise RuntimeError("source revision drift")
        if git(source, "rev-parse", "HEAD^{tree}") != receipt["source"]["tree_sha"]:
            raise RuntimeError("source tree drift")
        if git(factory, "rev-parse", "HEAD") != receipt["factory"]["revision"]:
            raise RuntimeError("factory revision drift")
        if git(factory, "rev-parse", "HEAD^{tree}") != receipt["factory"]["tree_sha"]:
            raise RuntimeError("factory tree drift")
        if sha(freeze) != receipt["source"]["foundry_freeze_receipt_sha256"]:
            raise RuntimeError("Foundry freeze receipt drift")
        if sha(probe) != receipt["factory"]["probe_sha256"]:
            raise RuntimeError("factory probe drift")
        if sha(contract) != receipt["compiled_birth_payload"]["sha256"]:
            raise RuntimeError("compiled birth payload drift")
        birth = json.loads(contract.read_text(encoding="utf-8"))
        if birth.get("schema") != "l9.birth-payload/v1" or birth.get("mode") != "authoritative":
            raise RuntimeError("compiled birth payload no longer satisfies authoritative contract")
        if birth.get("manifest_sha256") != receipt["compiled_birth_payload"]["manifest_sha256"]:
            raise RuntimeError("compiled manifest digest drift")
        for item in receipt["factory"].get("contract_files", {}).values():
            path = factory / item["path"]
            if not path.is_file() or sha(path) != item["sha256"]:
                raise RuntimeError(f"factory contract file drift: {item['path']}")
        if receipt["status"] == "LOCAL_BIRTH_PASS" and receipt.get("local_birth", {}).get("status") != "PASS":
            raise RuntimeError("LOCAL_BIRTH_PASS lacks local birth PASS evidence")
        if receipt.get("remote_birth", {}).get("status") != "NOT_PERFORMED":
            raise RuntimeError("qualification receipt may not claim remote birth")
        if receipt.get("deployment", {}).get("performed") is not False:
            raise RuntimeError("qualification receipt may not claim deployment")
    except (OSError, KeyError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"BIRTH_QUALIFICATION_VALIDATION: FAIL: {exc}", file=sys.stderr)
        return 1
    print("BIRTH_QUALIFICATION_VALIDATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
