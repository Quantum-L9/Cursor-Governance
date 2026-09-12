#!/usr/bin/env python3
"""Revalidate a Foundry birth-qualification receipt against exact source and factory state.

Git object identities (HEAD, HEAD^{tree}) prove what was committed, not what is
on disk now. Revalidation therefore also proves the source worktree is clean and
that its tracked bytes still hash to the digest bound at qualification, and it
recomputes the organization-profile binding a local birth consumed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from _common import FoundryContractError, tracked_tree_digest
from qualify_birth_handoff import bind_org_profile

SCHEMA = "l9.idea-foundry.birth-qualification/v1"
GIT_TIMEOUT_SECONDS = 120
EXPECTED_FOUNDRY_STATE = {
    "FACTORY_COMPILE_PASS": "BIRTH_READY",
    "LOCAL_BIRTH_PASS": "LOCAL_BIRTH_PASS",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"git {' '.join(args)} exceeded {GIT_TIMEOUT_SECONDS}s in {root}"
        ) from exc
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def require_source_exact_state(source: Path, bound: dict[str, Any]) -> None:
    if git(source, "rev-parse", "HEAD") != bound["revision"]:
        raise RuntimeError("source revision drift")
    if git(source, "rev-parse", "HEAD^{tree}") != bound["tree_sha"]:
        raise RuntimeError("source tree drift")
    dirty = git(source, "status", "--porcelain", "--untracked-files=all")
    if dirty.strip():
        raise RuntimeError("source worktree is dirty; qualified bytes are no longer on disk")
    try:
        records, digest = tracked_tree_digest(source)
    except FoundryContractError as exc:
        raise RuntimeError(f"cannot recompute source tracked bytes: {exc}") from exc
    if digest != bound["tracked_tree_digest"]:
        raise RuntimeError("source tracked bytes drift")
    if len(records) != bound["tracked_file_count"]:
        raise RuntimeError("source tracked file count drift")


def require_local_birth_inputs(local_birth: dict[str, Any]) -> None:
    if local_birth.get("status") != "PASS":
        raise RuntimeError("LOCAL_BIRTH_PASS lacks local birth PASS evidence")
    bound = local_birth.get("org_profile")
    if not isinstance(bound, dict) or not bound.get("path"):
        raise RuntimeError("LOCAL_BIRTH_PASS lacks organization profile binding")
    current = bind_org_profile(Path(bound["path"]))
    if current["content_sha256"] != bound.get("content_sha256"):
        raise RuntimeError("organization profile content drift; rerun local birth")
    if current["git_revision"] != bound.get("git_revision"):
        raise RuntimeError("organization profile revision drift; rerun local birth")
    if bound.get("git_clean") is False or current["git_clean"] is False:
        raise RuntimeError("organization profile checkout is dirty; rerun local birth")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate exact-state Foundry factory qualification evidence."
    )
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    try:
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        if receipt.get("schema") != SCHEMA:
            raise RuntimeError("unexpected qualification schema")
        status = receipt.get("status")
        if status not in EXPECTED_FOUNDRY_STATE:
            raise RuntimeError("qualification status is not a passing state")
        if receipt.get("foundry_state") != EXPECTED_FOUNDRY_STATE[status]:
            raise RuntimeError(
                f"foundry_state {receipt.get('foundry_state')!r} does not follow from {status}"
            )
        source = Path(receipt["source"]["path"])
        factory = Path(receipt["factory"]["path"])
        freeze = Path(receipt["source"]["foundry_freeze_receipt"])
        probe = Path(receipt["factory"]["probe"])
        contract = Path(receipt["compiled_birth_payload"]["path"])
        require_source_exact_state(source, receipt["source"])
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
        if status == "LOCAL_BIRTH_PASS":
            require_local_birth_inputs(receipt.get("local_birth") or {})
        if receipt.get("remote_birth", {}).get("status") != "NOT_PERFORMED":
            raise RuntimeError("qualification receipt may not claim remote birth")
        if receipt.get("deployment", {}).get("performed") is not False:
            raise RuntimeError("qualification receipt may not claim deployment")
    except (OSError, KeyError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"BIRTH_QUALIFICATION_VALIDATION: FAIL: {exc}", file=sys.stderr)
        return 1
    print("BIRTH_QUALIFICATION_VALIDATION: PASS")
    print(f"- foundry_state={receipt['foundry_state']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
