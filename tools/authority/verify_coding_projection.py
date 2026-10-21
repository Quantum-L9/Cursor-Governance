#!/usr/bin/env python3
"""Verify producer-emitted pairs of ``l9.projection/coding-agent-execution@1``.

Cursor-Governance is a consumer of this projection and never produces it.
Quantum-L9/.github ``docs/PROJECTION_PUBLICATION.md`` (#180) fixes the roles:
``l9-semantic-compiler`` holds the ``projection`` role and emits one
artifact/receipt pair per profile source class, the upstream publisher moves
the pair to the ``projections`` branch, and consumers verify independently
without running the producer.

This module re-derives every pin from the authority's own commit objects and
checks a published pair against them, mirroring the publisher's conventions:
sha256 of raw source bytes; sha256 of canonical JSON (sorted keys, compact,
UTF-8) for payload, profile entry and receipt; schema rules read from the same
revision. Receipts are unsigned, so a verified pair proves digest integrity and
the declared producer role, not the producer's identity.

Nothing here fetches, writes, or grants authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

OWNER_REPOSITORY = "Quantum-L9/.github"
PRODUCER = "l9-semantic-compiler"
CATALOG_REF = "l9.source/projection-profiles@1"
REGISTRY_PATH = "semantics/canonical_sources.yaml"
ARTIFACT_SCHEMA_PATH = "semantics/projection_artifact.schema.yaml"
RECEIPT_SCHEMA_PATH = "semantics/compiler_receipt.schema.yaml"
ARTIFACT_SCHEMA = "l9.projection-artifact/v1"
RECEIPT_SCHEMA = "l9.compiler-receipt/v1"
RECEIPT_TYPE = "l9.receipt/compilation@1"
INDEX_PATH = "index.json"
INDEX_FORMAT = "quantum-l9-github/projections-index@1"
PROJECTION_FILE = "projection.json"
RECEIPT_FILE = "receipt.json"

_ORIGIN = re.compile(
    r"(?:https://(?:[^@/\s]+@)?github\.com/|ssh://git@github\.com/|git@github\.com:)"
    r"quantum-l9/\.github(?:\.git)?/?",
    re.IGNORECASE,
)
_SHA1 = re.compile(r"[0-9a-f]{40}")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "semantic_ref": lambda v: isinstance(v, str) and bool(v),
    "semantic_digest": lambda v: isinstance(v, str) and bool(_DIGEST.fullmatch(v)),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "any": lambda v: True,
}


class Rejected(Exception):
    """A pair, index or authority input failed verification (``BLOCKED``)."""


class Unobserved(Exception):
    """Proof is not available here (``UNVERIFIED``); nothing was contradicted."""


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return digest_bytes(encoded.encode("utf-8"))


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    env = {**os.environ, "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False, timeout=30, env=env
    )


def blob_at(root: Path, commit: str, path: str) -> bytes | None:
    result = _git(root, "cat-file", "blob", f"{commit}:{path}")
    return result.stdout if result.returncode == 0 else None


def resolve(root: Path, ref: str) -> str | None:
    result = _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    value = result.stdout.decode().strip()
    return value if result.returncode == 0 and _SHA1.fullmatch(value) else None


def is_ancestor(root: Path, older: str, newer: str) -> bool:
    return _git(root, "merge-base", "--is-ancestor", older, newer).returncode == 0


def verify_authority(root: Path) -> None:
    """Raise ``Unobserved`` unless ``root`` is the top of a Quantum-L9/.github clone."""
    top = _git(root, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        raise Unobserved(f"{root} is not a git checkout")
    if Path(top.stdout.decode().strip()).resolve() != root.resolve():
        raise Unobserved(f"{root} is not a repository top level")
    origin = _git(root, "config", "--get", "remote.origin.url").stdout.decode().strip()
    if not _ORIGIN.fullmatch(origin):
        raise Unobserved(f"{root}: origin is not {OWNER_REPOSITORY} ({origin or 'none'})")


def _yaml(data: bytes, what: str) -> dict[str, Any]:
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    try:
        doc = yaml.load(data, Loader=loader)  # noqa: S506 - safe loader
    except yaml.YAMLError as exc:
        raise Rejected(f"{what}: unreadable YAML") from exc
    if not isinstance(doc, dict):
        raise Rejected(f"{what}: not a mapping")
    return doc


def _json(data: bytes, what: str) -> dict[str, Any]:
    try:
        doc = json.loads(data.decode("utf-8"), parse_constant=_no_constant)
    except ValueError as exc:
        raise Rejected(f"{what}: malformed JSON") from exc
    if not isinstance(doc, dict):
        raise Rejected(f"{what}: not an object")
    return doc


def _no_constant(name: str) -> Any:
    raise ValueError(f"non-JSON number {name}")


def compute_pins(root: Path, revision: str, profile_ref: str, source_class: str) -> dict[str, Any]:
    """Everything a pair must bind, read from ``revision``'s objects only."""

    def read(path: str) -> bytes:
        data = blob_at(root, revision, path)
        if data is None:
            raise Rejected(f"{path} absent at {revision[:12]}")
        return data

    registry_bytes = read(REGISTRY_PATH)
    registry = _yaml(registry_bytes, REGISTRY_PATH)
    entries = [e for e in registry.get("sources") or [] if isinstance(e, dict)]

    def entry(**match: str) -> dict[str, Any]:
        found = [e for e in entries if all(e.get(k) == v for k, v in match.items())]
        if len(found) != 1:
            raise Rejected(f"canonical source registry does not resolve {match} once")
        return found[0]

    catalog_bytes = read(str(entry(id=CATALOG_REF).get("path")))
    catalog = _yaml(catalog_bytes, "projection profile catalog")
    profiles = [
        p
        for p in catalog.get("projection_profiles") or []
        if isinstance(p, dict) and p.get("id") == profile_ref
    ]
    if len(profiles) != 1:
        raise Rejected(f"{profile_ref} does not resolve once at {revision[:12]}")
    profile = profiles[0]
    spec = (profile.get("sources") or {}).get(source_class)
    if not isinstance(spec, dict) or not isinstance(spec.get("selectors"), list):
        raise Rejected(f"{profile_ref} declares no source class {source_class}")
    class_entry = (catalog.get("source_classes") or {}).get(source_class) or {}
    artifact = class_entry.get("canonical_artifact") if isinstance(class_entry, dict) else None
    if not isinstance(artifact, str) or not artifact:
        raise Rejected(f"source class {source_class} names no canonical artifact")
    source = entry(path=f"semantics/{artifact}")
    if source.get("canonical") is not True or source.get("projection_allowed") is not True:
        raise Rejected(f"{source.get('id')} is not projectable")
    return {
        "authority_revision": revision,
        "profile_ref": profile_ref,
        "profile_digest": digest(profile),
        "source_class": source_class,
        "selectors": spec["selectors"],
        "source_ref": source.get("id"),
        "source_digest": digest_bytes(read(str(source.get("path")))),
        "catalog_digest": digest_bytes(catalog_bytes),
        "registry_digest": digest_bytes(registry_bytes),
        "schemas": {
            "artifact": _yaml(read(ARTIFACT_SCHEMA_PATH), ARTIFACT_SCHEMA_PATH),
            "receipt": _yaml(read(RECEIPT_SCHEMA_PATH), RECEIPT_SCHEMA_PATH),
        },
    }


def _rule(value: Any, rule: Mapping[str, Any], where: str) -> None:
    if "const" in rule and value != rule["const"]:
        raise Rejected(f"{where}: const mismatch")
    if "enum" in rule:
        if not isinstance(rule["enum"], list):
            raise Rejected(f"{where}: schema enum unresolved")
        if value not in rule["enum"]:
            raise Rejected(f"{where}: not in enum")
    kind = rule.get("type")
    if kind is not None:
        check = _TYPE_CHECKS.get(kind)
        if check is None:
            raise Rejected(f"{where}: schema type {kind} unresolved")
        if not check(value):
            raise Rejected(f"{where}: not {kind}")
    nested = rule.get("required")
    if isinstance(nested, list):
        missing = set(nested) - (set(value) if isinstance(value, dict) else set())
        if missing:
            raise Rejected(f"{where}: missing {sorted(missing)}")
    items = rule.get("items")
    if isinstance(items, dict) and isinstance(value, list):
        for index, item in enumerate(value):
            _rule(item, items, f"{where}[{index}]")


def _schema(doc: Mapping[str, Any], schema: Mapping[str, Any], what: str) -> None:
    required = schema.get("required")
    if not isinstance(required, list) or not required:
        raise Rejected(f"{what}: schema declares no required fields")
    missing = sorted(set(required) - set(doc))
    if missing:
        raise Rejected(f"{what}: missing {missing}")
    for key, rule in (schema.get("properties") or {}).items():
        if key in doc and isinstance(rule, dict):
            _rule(doc[key], rule, f"{what}.{key}")


def verify_pair(artifact_bytes: bytes, receipt_bytes: bytes, pins: Mapping[str, Any]) -> str:
    """Check one pair against ``pins``; return the receipt digest or raise ``Rejected``."""
    artifact = _json(artifact_bytes, PROJECTION_FILE)
    receipt = _json(receipt_bytes, RECEIPT_FILE)
    _schema(artifact, pins["schemas"]["artifact"], PROJECTION_FILE)
    _schema(receipt, pins["schemas"]["receipt"], RECEIPT_FILE)
    checks = [
        (artifact.get("schema") == ARTIFACT_SCHEMA, "artifact schema"),
        (receipt.get("schema") == RECEIPT_SCHEMA, "receipt schema"),
        (receipt.get("receipt_type") == RECEIPT_TYPE, "receipt type"),
        (
            receipt.get("operation") == "projection" and receipt.get("result") == "pass",
            "receipt is not a passing projection",
        ),
        (
            artifact.get("source_ref") == pins["source_ref"]
            and artifact.get("source_digest") == pins["source_digest"],
            "source digest",
        ),
        (
            artifact.get("projection_profile_ref") == pins["profile_ref"]
            and artifact.get("projection_profile_digest") == pins["profile_digest"],
            "profile digest",
        ),
        (
            "payload" in artifact and artifact.get("projection_digest") == _payload(artifact),
            "projection digest does not match payload (tampered)",
        ),
        (
            (artifact.get("generated_by") or {}).get("compiler") == PRODUCER
            and (receipt.get("producer_identity") or {}).get("compiler") == PRODUCER
            and (artifact.get("generated_by") or {}).get("version")
            == (receipt.get("producer_identity") or {}).get("version")
            and isinstance((receipt.get("producer_identity") or {}).get("version"), str),
            f"producer role is not {PRODUCER}",
        ),
        (receipt.get("exact_subject_ref") == pins["profile_ref"], "receipt subject"),
        (
            receipt.get("profile")
            == {"ref": pins["profile_ref"], "digest": pins["profile_digest"]},
            "receipt profile",
        ),
        (
            receipt.get("output")
            == {
                "ref": f"{pins['profile_ref']}#{pins['source_class']}",
                "digest": artifact.get("projection_digest"),
            },
            "receipt output does not bind the artifact",
        ),
        (
            {"ref": pins["source_ref"], "digest": pins["source_digest"]}
            in (receipt.get("inputs") or [])
            and {"ref": CATALOG_REF, "digest": pins["catalog_digest"]}
            in (receipt.get("inputs") or []),
            "receipt inputs",
        ),
        (
            (receipt.get("governing_coordinates") or {}).get("source_class") == pins["source_class"]
            and (receipt.get("governing_coordinates") or {}).get("selectors") == pins["selectors"]
            and (receipt.get("governing_coordinates") or {}).get("canonical_source_registry_digest")
            == pins["registry_digest"]
            and (receipt.get("governing_coordinates") or {}).get("authority_owner")
            == OWNER_REPOSITORY
            and (receipt.get("governing_coordinates") or {}).get("authority_revision")
            == pins["authority_revision"],
            "receipt governing coordinates",
        ),
    ]
    for ok, what in checks:
        if not ok:
            raise Rejected(f"{pins['source_class']}: {what}")
    body = {k: v for k, v in receipt.items() if k != "receipt_digest"}
    if receipt.get("receipt_digest") != digest(body):
        raise Rejected(f"{pins['source_class']}: receipt digest (forged or edited)")
    identity = "l9.receipt-instance/" + digest({**body, "receipt_identity": "pending"})[7:]
    if receipt.get("receipt_identity") != identity:
        raise Rejected(f"{pins['source_class']}: receipt identity")
    return str(receipt["receipt_digest"])


def _payload(artifact: Mapping[str, Any]) -> str | None:
    try:
        return digest(artifact.get("payload"))
    except (TypeError, ValueError):
        return None


def verify_published(
    root: Path,
    publication: str,
    main: str,
    profile_ref: str,
    source_class: str,
) -> dict[str, Any]:
    """Verify the current published pair for one class against observed ``main``.

    Returns ``{"current": bool, ...}``: ``current`` is False when the pair is
    genuine but ``main`` has since changed its source or profile digest.
    """
    index_bytes = blob_at(root, publication, INDEX_PATH)
    if index_bytes is None:
        raise Unobserved(f"no {INDEX_PATH} on the projections branch")
    index = _json(index_bytes, INDEX_PATH)
    if index.get("transport_format") != INDEX_FORMAT or not isinstance(index.get("entries"), dict):
        raise Rejected(f"{INDEX_PATH}: unsupported transport format")
    entry = index["entries"].get(f"{profile_ref}#{source_class}")
    if not entry:
        raise Unobserved(f"no published pair for {source_class}")
    current = entry.get("current") or {}
    files = []
    for name in (PROJECTION_FILE, RECEIPT_FILE):
        data = blob_at(root, publication, f"{current.get('pair')}/{name}")
        if data is None:
            raise Rejected(f"{source_class}: indexed {name} is absent")
        if digest_bytes(data) != (current.get("files") or {}).get(name):
            raise Rejected(f"{source_class}: {name} does not match the index")
        files.append(data)
    asserted = (_json(files[1], RECEIPT_FILE).get("governing_coordinates") or {}).get(
        "authority_revision"
    )
    if not isinstance(asserted, str) or not _SHA1.fullmatch(asserted):
        raise Rejected(f"{source_class}: receipt asserts no authority revision")
    if not is_ancestor(root, asserted, main):
        raise Rejected(f"{source_class}: published revision {asserted[:12]} is not on main")
    receipt_digest = verify_pair(
        files[0], files[1], compute_pins(root, asserted, profile_ref, source_class)
    )
    if receipt_digest != current.get("receipt_digest"):
        raise Rejected(f"{source_class}: index names a different receipt")
    now = compute_pins(root, main, profile_ref, source_class)
    published = compute_pins(root, asserted, profile_ref, source_class)
    material = (now["source_digest"], now["profile_digest"]) != (
        published["source_digest"],
        published["profile_digest"],
    )
    return {"current": not material, "published_revision": asserted, "receipt": receipt_digest}
