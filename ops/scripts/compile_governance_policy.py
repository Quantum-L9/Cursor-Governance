#!/usr/bin/env python3
"""Compile immutable PolicyChange transactions into deterministic invariant catalogs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from jsonschema import Draft202012Validator

VERSION = "1.0.0"
CONTRACTS = Path("governance/policy/contracts")
CHANGE_SCHEMA = CONTRACTS / "policy-change.v1.schema.json"
ORG_SCHEMA = CONTRACTS / "org-invariants.compiled.v1.schema.json"
REPO_SCHEMA = CONTRACTS / "repo-invariants.schema.json"
RECEIPT_SCHEMA = CONTRACTS / "policy-compile-receipt.v1.schema.json"
DEFAULT_CHANGES = "governance/policy/changes"
DEFAULT_ORG = "ORG_INVARIANTS.yaml"
DEFAULT_REPO = "governance/REPO_INVARIANTS.yaml"
DEFAULT_RECEIPT = ".artifacts/governance/policy-compile-receipt.json"


class PolicyError(RuntimeError):
    """Policy/schema/freshness failure."""


class InvocationError(RuntimeError):
    """Malformed invocation or unreadable input."""


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _mapping(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode, deep: bool = False):
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise InvocationError(f"duplicate YAML mapping key: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvocationError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise InvocationError(f"JSON root must be object: {path}")
    return value


def _yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except (OSError, yaml.YAMLError, InvocationError) as exc:
        raise InvocationError(f"cannot load YAML {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise InvocationError(f"YAML root must be a mapping: {path}")
    return value


def _unsafe_binding(path: str) -> bool:
    if not path or path.startswith(("/", "\\")) or "\\" in path:
        return True
    return any(part == ".." for part in PurePosixPath(path).parts)


def _catalog(schema: str, owner_key: str, owner: str) -> dict[str, Any]:
    return {
        "schema": schema,
        "policy_digest": "",
        owner_key: owner,
        "source_transaction_digest": _digest([]),
        "status": "active",
        "invariants": [],
        "retired_ids": [],
    }


def _seal(repo: dict[str, Any], org: dict[str, Any], applied: list[dict[str, Any]]) -> str:
    tx_digest = _digest(applied)
    repo["source_transaction_digest"] = tx_digest
    org["source_transaction_digest"] = tx_digest
    body = {
        "org": {key: value for key, value in org.items() if key != "policy_digest"},
        "repo": {key: value for key, value in repo.items() if key != "policy_digest"},
    }
    digest = _digest(body)
    repo["policy_digest"] = digest
    org["policy_digest"] = digest
    return digest


def _invariant_from(tx: dict[str, Any]) -> dict[str, Any]:
    requirement = tx["requirement"]
    body = {
        "id": tx["invariant_id"],
        "title": requirement["title"],
        "statement": requirement["statement"],
        "applicability": requirement["applicability"],
        "relationships": tx.get("relationships") or [],
        "bindings": tx.get("bindings") or [],
        "verifiers": tx.get("verifiers") or [],
        "projection": tx["projection"],
        "source_change_ids": [tx["change_id"]],
    }
    body["invariant_digest"] = _digest(body)
    return body


def _order(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {tx["change_id"]: tx for tx in transactions}
    children: dict[str, list[str]] = defaultdict(list)
    indegree = {change_id: 0 for change_id in by_id}
    for change_id, tx in by_id.items():
        for dep in tx.get("depends_on") or []:
            if dep not in by_id:
                raise PolicyError(f"unknown dependency {dep}")
            children[dep].append(change_id)
            indegree[change_id] += 1
    ready = sorted(change_id for change_id, degree in indegree.items() if degree == 0)
    ordered: list[dict[str, Any]] = []
    while ready:
        change_id = ready.pop(0)
        ordered.append(by_id[change_id])
        nxt: list[str] = []
        for child in children[change_id]:
            indegree[child] -= 1
            if indegree[child] == 0:
                nxt.append(child)
        ready.extend(sorted(nxt))
        ready.sort()
    if len(ordered) != len(transactions):
        raise PolicyError("dependency cycle")
    return ordered


class PolicyCompiler:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _schema(self, relative: Path) -> dict[str, Any]:
        return _json(self.root / relative)

    def _transactions(self) -> list[dict[str, Any]]:
        directory = self.root / DEFAULT_CHANGES
        if not directory.is_dir():
            return []
        validator = Draft202012Validator(self._schema(CHANGE_SCHEMA))
        loaded: list[dict[str, Any]] = []
        seen: set[str] = set()
        paths = sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))
        for path in paths:
            tx = _yaml(path)
            errors = sorted(validator.iter_errors(tx), key=lambda item: list(item.path))
            if errors:
                raise PolicyError(errors[0].message)
            change_id = tx["change_id"]
            if change_id in seen:
                raise PolicyError(f"duplicate change_id {change_id}")
            seen.add(change_id)
            for binding in tx.get("bindings") or []:
                if _unsafe_binding(str(binding.get("path", ""))):
                    raise PolicyError(f"unsafe binding path: {binding.get('path')}")
            loaded.append(tx)
        return _order(loaded)

    def compile(self) -> dict[str, Any]:
        org = _catalog("l9.org-invariants.compiled.v1", "organization", "Quantum-L9")
        repo = _catalog("l9.repo-invariants.v1", "repository", "Quantum-L9/Cursor-Governance")
        digest = _seal(repo, org, [])
        applied: list[dict[str, Any]] = []
        for tx in self._transactions():
            claimed = tx["preconditions"]["base_policy_digest"]
            if claimed != digest:
                raise PolicyError("stale base_policy_digest")
            self._apply(tx, repo, org)
            applied.append(tx)
            digest = _seal(repo, org, applied)
        repo_bytes = yaml.safe_dump(repo, sort_keys=True, allow_unicode=True).encode("utf-8")
        schema_paths = (CHANGE_SCHEMA, ORG_SCHEMA, REPO_SCHEMA, RECEIPT_SCHEMA)
        receipt = {
            "schema": "l9.policy-compile-receipt.v1",
            "status": "PASS",
            "compiler_version": VERSION,
            "transaction_count": len(applied),
            "transaction_set_digest": _digest(applied),
            "schema_digests": {
                path.as_posix(): _bytes_digest((self.root / path).read_bytes())
                for path in schema_paths
                if (self.root / path).is_file()
            },
            "policy_digest": digest,
            "outputs": [
                {"path": DEFAULT_REPO, "digest": _bytes_digest(repo_bytes), "current": True}
            ],
            "errors": [],
        }
        return {
            "receipt": receipt,
            "repo_bytes": repo_bytes,
            "repository": repo,
            "organization": org,
        }

    def _apply(self, tx: dict[str, Any], repo: dict[str, Any], org: dict[str, Any]) -> None:
        catalog = repo if tx["scope"] == "repository" else org
        operation = tx["operation"]
        invariant_id = tx["invariant_id"]
        active = {item["id"]: item for item in catalog["invariants"]}
        retired = set(catalog["retired_ids"])
        if operation == "add":
            if invariant_id in active or invariant_id in retired:
                raise PolicyError(f"invariant {invariant_id} already used or retired")
            catalog["invariants"].append(_invariant_from(tx))
            catalog["invariants"].sort(key=lambda item: item["id"])
            return
        if operation == "retire":
            current = active.get(invariant_id)
            if current is None:
                raise PolicyError(f"invariant {invariant_id} already used or retired")
            target = tx["preconditions"].get("target_invariant_digest")
            if target != current["invariant_digest"]:
                raise PolicyError("target_invariant_digest mismatch")
            catalog["invariants"] = [
                item for item in catalog["invariants"] if item["id"] != invariant_id
            ]
            catalog["retired_ids"] = sorted(retired | {invariant_id})
            return
        if operation == "amend":
            current = active.get(invariant_id)
            if current is None:
                raise PolicyError(f"invariant {invariant_id} is not active")
            target = tx["preconditions"].get("target_invariant_digest")
            if target != current["invariant_digest"]:
                raise PolicyError("target_invariant_digest mismatch")
            replacement = _invariant_from(tx)
            catalog["invariants"] = [
                replacement if item["id"] == invariant_id else item
                for item in catalog["invariants"]
            ]
            return
        raise PolicyError(f"unsupported operation {operation}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile governance policy transactions")
    parser.add_argument("command", choices=("compile", "check"))
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    try:
        result = PolicyCompiler(args.root).compile()
    except (PolicyError, InvocationError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    target = args.root / DEFAULT_REPO
    if args.command == "check":
        current = target.read_bytes() if target.is_file() else b""
        return 0 if current == result["repo_bytes"] else 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(result["repo_bytes"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
