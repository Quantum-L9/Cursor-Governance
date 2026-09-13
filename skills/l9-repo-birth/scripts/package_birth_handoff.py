#!/usr/bin/env python3
"""Package a proven PE source snapshot for l9-repo-template without birthing it."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "birth-contract.schema.json"


class HandoffError(ValueError):
    pass


def git(source: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(source), *args], text=True, capture_output=True, check=False
    )
    if proc.returncode:
        raise HandoffError(
            f"source git {' '.join(args)} failed: {(proc.stderr or proc.stdout).strip()}"
        )
    return proc.stdout.strip()


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"cannot load evidence {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise HandoffError("birth evidence must be a JSON object")
    return value


def require_digest(evidence: dict[str, Any], key: str) -> str:
    value = str(evidence.get(key) or "")
    if not value.startswith("sha256:") or len(value) != 71:
        raise HandoffError(f"evidence.{key} must be a sha256: digest")
    return value


def validate_evidence(evidence: dict[str, Any], source: Path) -> tuple[str, str, str]:
    if evidence.get("schema") != "l9.repo-birth-evidence/v1":
        raise HandoffError("evidence.schema must equal l9.repo-birth-evidence/v1")
    for key in ("idea_execute_receipt", "gar_decision", "plan", "campaign_source", "pe_receipt"):
        require_digest(evidence, key)
    refs = evidence.get("acceptance_evidence_refs")
    if (
        not isinstance(refs, list)
        or not refs
        or not all(isinstance(ref, str) and ref.strip() for ref in refs)
    ):
        raise HandoffError("evidence.acceptance_evidence_refs must be a non-empty string list")
    revision = git(source, "rev-parse", "HEAD")
    tree_sha = git(source, "rev-parse", "HEAD^{tree}")
    if git(source, "status", "--porcelain"):
        raise HandoffError("source worktree is dirty; commit verified PE output before packaging")
    if evidence.get("source_revision") != revision or evidence.get("source_tree_sha") != tree_sha:
        raise HandoffError(
            "PE evidence source revision/tree does not match the current clean source"
        )
    repository = str(evidence.get("source_repository") or "").strip()
    if "/" not in repository:
        raise HandoffError("evidence.source_repository must be owner/name")
    return repository, revision, tree_sha


def package(
    *,
    source: Path,
    evidence_path: Path,
    factory: Path,
    out_dir: Path,
    operation: str,
    source_repository: str | None = None,
) -> dict[str, Any]:
    source, factory, out_dir = source.resolve(), factory.resolve(), out_dir.resolve()
    compiler = factory / "scripts/birth-runner/compile_birth_payload.py"
    birth_front_door = factory / "scripts/birth-runner/new_repo.py"
    if not compiler.is_file() or not birth_front_door.is_file():
        raise HandoffError(
            "FACTORY_BIRTH_INTERFACE_UNAVAILABLE: factory compiler or birth front door is missing"
        )
    evidence = load_json(evidence_path)
    repository, revision, tree_sha = validate_evidence(evidence, source)
    if source_repository:
        repository = source_repository
    out_dir.mkdir(parents=True, exist_ok=True)
    payload_path = out_dir / "birth-payload.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(compiler),
            "--source",
            str(source),
            "--template-src",
            str(factory),
            "--out",
            str(payload_path),
            "--source-repository",
            repository,
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode:
        raise HandoffError(
            f"factory payload compiler failed: {(proc.stderr or proc.stdout).strip()}"
        )
    payload = load_json(payload_path)
    if payload.get("schema") != "l9.birth-payload/v1":
        raise HandoffError("factory compiler did not emit l9.birth-payload/v1")
    if (
        payload.get("source", {}).get("revision") != revision
        or payload.get("source", {}).get("tree_sha") != tree_sha
    ):
        raise HandoffError("factory payload does not bind the verified PE source snapshot")
    factory_revision = git(factory, "rev-parse", "HEAD")
    contract = {
        "schema": "l9.repo-birth-contract/v1",
        "operation": operation,
        "source": {
            "path": str(source),
            "repository": repository,
            "revision": revision,
            "tree_sha": tree_sha,
            "clean": True,
        },
        "lineage": {
            "idea_execute_receipt": evidence["idea_execute_receipt"],
            "gar_decision": evidence["gar_decision"],
            "plan": evidence["plan"],
            "campaign_source": evidence["campaign_source"],
            "pe_receipt": evidence["pe_receipt"],
            "acceptance_evidence_refs": evidence["acceptance_evidence_refs"],
        },
        "factory": {
            "path": str(factory),
            "revision": factory_revision,
            "compiler": str(compiler),
            "birth_front_door": str(birth_front_door),
        },
        "payload": {
            "ref": str(payload_path),
            "digest": sha256(payload_path),
            "schema": "l9.birth-payload/v1",
        },
    }
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(contract))
    if errors:
        raise HandoffError(
            "birth contract schema failure: " + "; ".join(err.message for err in errors)
        )
    contract_path = out_dir / "birth-contract.json"
    contract_path.write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"payload": str(payload_path), "contract": str(contract_path), "operation": operation}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--factory", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--operation", choices=("local_validation", "remote_birth"), default="local_validation"
    )
    parser.add_argument("--source-repository")
    args = parser.parse_args()
    try:
        result = package(
            source=Path(args.source),
            evidence_path=Path(args.evidence),
            factory=Path(args.factory),
            out_dir=Path(args.out_dir),
            operation=args.operation,
            source_repository=args.source_repository,
        )
    except (HandoffError, OSError, json.JSONDecodeError) as exc:
        print(f"REPO_BIRTH_HANDOFF: FAIL\n- {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "PASS", **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
