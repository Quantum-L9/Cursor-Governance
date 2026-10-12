#!/usr/bin/env python3
"""Verify a canonical L9 invariant projection before Coding Agent mutation.

Consumer-side verifier only. It never emits, synthesizes, or repairs a
projection, and it never runs a producer: it checks an externally supplied,
producer-emitted `l9.projection-artifact/v1` and its `l9.compiler-receipt/v1`
against an exact `Quantum-L9/.github` checkout and prints one binding record
for `runtime/RUN_STATE.yaml` `authority.sources`.

Law, schemas, and the profile are read from the commit objects of the pinned
authority revision, each object hash recomputed, so neither the working tree,
the index, nor replace refs can substitute bytes. The pin is required and must
come from an independent record; the verifier binds bytes to the pin but
cannot authenticate the pin itself. Nothing upstream is copied here. Constants
below are identity coordinates, not doctrine.

Exit codes: 0 BOUND/CURRENT, 1 REJECTED, 2 usage, 3 BLOCKED (Unknown), 4 STALE.

Usage:
  verify_canonical_binding.py --authority-root DIR --artifact FILE --receipt FILE
      --expect-revision SHA [--require-invariant ID ...]
  verify_canonical_binding.py --authority-root DIR --prior-binding FILE
      --artifact FILE --receipt FILE --expect-revision SHA
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

try:
    import yaml
except Exception as exc:  # wrong interpreter is Unknown, never a REJECTED-looking rc 1
    print(
        json.dumps(
            {"status": "BLOCKED", "reason": "VERIFIER_INTERPRETER_UNRESOLVED", "error": repr(exc)}
        )
    )
    raise SystemExit(3) from exc

OWNER_REPOSITORY = "Quantum-L9/.github"
PROFILE_REF = "l9.projection/cursor-governance-operating-plane@1"
PROFILE_CONSUMER = "Cursor-Governance"
SOURCE_CLASS = "invariants"
SOURCE_REF = "l9.source/invariants@1"
SELECTOR = '$.invariants[?(@.scope=="global")]'
PROFILES_PATH = "semantics/projection_profiles.yaml"
SOURCES_PATH = "semantics/canonical_sources.yaml"
ARTIFACT_SCHEMA_PATH = "semantics/projection_artifact.schema.yaml"
RECEIPT_SCHEMA_PATH = "semantics/compiler_receipt.schema.yaml"
VOCABULARY_PATH = "semantics/vocabulary.yaml"
PRODUCER_ROLE = "projection"

GIT_TIMEOUT_S = 30
# Replace refs would let a local ref swap object content; hashes are rechecked too.
GIT_ENV = {**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"}
EXIT = {"BOUND": 0, "CURRENT": 0, "REJECTED": 1, "BLOCKED": 3, "STALE": 4}
_SHA1 = re.compile(r"[0-9a-f]{40}")
# Exact host and repository; a suffix match would accept any path ending in it.
_ORIGIN = re.compile(
    r"(?:https://(?:[^@/\s]+@)?github\.com/|ssh://git@github\.com/|git@github\.com:)"
    r"quantum-l9/\.github(?:\.git)?/?",
    re.IGNORECASE,
)


class Outcome(Exception):
    def __init__(self, status: str, reason: str, **detail: Any) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.detail = detail


# Digest conventions. `.github` defines `semantic_digest` without fixing an
# algorithm, so the consumer accepts only digests it can recompute:
# - source digests: sha256 of raw file bytes, as `.github` ledgers record them
#   (e.g. `receipt_catalog.yaml` derivation.source_artifacts[].sha256);
# - content digests: sha256 of canonical JSON, as the candidate producer
#   `l9-semantic-compiler-engine` computes them (`engine/canonical.py`).
# A producer using another canonicalization fails closed here, never open.
def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _normalize(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    return value


def content_digest(value: Any) -> str:
    raw = json.dumps(_normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def bytes_digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _load(path: Path, what: str, missing_status: str = "BLOCKED") -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise Outcome(missing_status, f"{what}_UNREADABLE", path=str(path), error=str(exc)) from exc
    try:
        return json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    except Exception as exc:
        raise Outcome("REJECTED", f"{what}_MALFORMED", path=str(path), error=str(exc)) from exc


def _git_raw(root: Path, *args: str) -> tuple[int, bytes, str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            timeout=GIT_TIMEOUT_S,
            env=GIT_ENV,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Outcome(
            "BLOCKED", "AUTHORITY_ROOT_PROVENANCE_UNKNOWN", git=list(args), error=repr(exc)
        ) from exc
    return result.returncode, result.stdout, result.stderr.decode("utf-8", "replace").strip()


def _git(root: Path, *args: str) -> str:
    returncode, stdout, stderr = _git_raw(root, *args)
    if returncode != 0:
        raise Outcome("BLOCKED", "AUTHORITY_ROOT_PROVENANCE_UNKNOWN", git=list(args), error=stderr)
    return stdout.decode("utf-8", "replace").strip()


def authority_root(root: Path, expect_revision: str | None) -> dict[str, Any]:
    if not root.is_dir():
        raise Outcome("BLOCKED", "AUTHORITY_ROOT_ABSENT", path=str(root))
    # The checkout's own HEAD, origin, and refs are local state anyone can set,
    # so an unpinned run would bind whatever revision the checkout claims.
    if not expect_revision:
        raise Outcome(
            "BLOCKED",
            "AUTHORITY_REVISION_PIN_ABSENT",
            detail="pass --expect-revision from an independent record of the published revision",
        )
    if not _SHA1.fullmatch(expect_revision):
        raise Outcome(
            "BLOCKED", "AUTHORITY_REVISION_PIN_MALFORMED", expected="40-hex lowercase commit id"
        )
    origin = _git(root, "remote", "get-url", "origin")
    if not _ORIGIN.fullmatch(origin):
        raise Outcome(
            "BLOCKED",
            "AUTHORITY_ROOT_NOT_CANONICAL_OWNER",
            origin=origin,
            expected=OWNER_REPOSITORY,
        )
    object_format = _git(root, "rev-parse", "--show-object-format")
    if object_format != "sha1":
        raise Outcome("BLOCKED", "AUTHORITY_OBJECT_FORMAT_UNSUPPORTED", object_format=object_format)
    revision = _git(root, "rev-parse", "HEAD")
    if not _SHA1.fullmatch(revision):
        raise Outcome("BLOCKED", "AUTHORITY_ROOT_PROVENANCE_UNKNOWN", revision=revision)
    if _git(root, "status", "--porcelain", "--", "semantics"):
        raise Outcome("BLOCKED", "AUTHORITY_ROOT_SEMANTICS_UNCOMMITTED", revision=revision)
    if revision != expect_revision:
        raise Outcome(
            "STALE", "AUTHORITY_REVISION_MISMATCH", observed=revision, expected=expect_revision
        )
    # A commit no fetched origin ref contains exists only locally. Tracking refs
    # are local state too: this excludes local-only commits, it does not prove
    # publication.
    tracking = _git(root, "for-each-ref", "--format=%(refname)", "refs/remotes/origin")
    if not any(
        _git_raw(root, "merge-base", "--is-ancestor", revision, ref)[0] == 0
        for ref in tracking.splitlines()
        if ref and ref != "refs/remotes/origin/HEAD"
    ):
        raise Outcome(
            "BLOCKED",
            "AUTHORITY_REVISION_NOT_ON_ORIGIN_TRACKING_REF",
            revision=revision,
            detail="fetch the canonical owner; a local-only commit is not authority",
        )
    return {
        "repository": OWNER_REPOSITORY,
        "revision": revision,
        "revision_basis": "caller_pinned_not_authenticated",
        "content_basis": "pinned_commit_objects_hash_verified",
    }


class PinnedTree:
    """Read law bytes from the pinned commit, recomputing every object hash.

    The working tree, the index (`--skip-worktree`, `--assume-unchanged`),
    replace refs, and rewritten loose objects cannot substitute content: bytes
    are returned only when the commit, every tree on the path, and the blob each
    hash to the id that links them to the pinned revision.
    """

    def __init__(self, root: Path, revision: str) -> None:
        self.root = root
        self.revision = revision

    def _object(self, oid: str, kind: str) -> bytes:
        returncode, raw, stderr = _git_raw(self.root, "cat-file", kind, oid)
        if returncode != 0:
            raise Outcome(
                "BLOCKED", "AUTHORITY_OBJECT_UNREADABLE", oid=oid, kind=kind, error=stderr
            )
        header = f"{kind} {len(raw)}\0".encode()
        if hashlib.sha1(header + raw).hexdigest() != oid:  # noqa: S324 - git object identity
            raise Outcome("REJECTED", "AUTHORITY_OBJECT_NOT_BOUND_TO_PIN", oid=oid, kind=kind)
        return raw

    @staticmethod
    def _entry(tree: bytes, name: bytes) -> tuple[bytes, str] | None:
        i = 0
        while i < len(tree):
            space = tree.index(b" ", i)
            nul = tree.index(b"\0", space)
            if tree[space + 1 : nul] == name:
                return tree[i:space], tree[nul + 1 : nul + 21].hex()
            i = nul + 21
        return None

    def read(self, rel: str, what: str, missing_status: str = "BLOCKED") -> bytes:
        parts = PurePosixPath(rel).parts
        if (
            not parts
            or PurePosixPath(rel).is_absolute()
            or any(p in ("", ".", "..") for p in parts)
        ):
            raise Outcome("BLOCKED", "AUTHORITY_PATH_UNRESOLVED", path=rel)
        commit = self._object(self.revision, "commit")
        first = commit.split(b"\n", 1)[0]
        tree_oid = first[5:].decode("ascii", "replace")
        if not first.startswith(b"tree ") or not _SHA1.fullmatch(tree_oid):
            raise Outcome("REJECTED", "AUTHORITY_COMMIT_MALFORMED", revision=self.revision)
        missing = Outcome(missing_status, f"{what}_UNREADABLE", path=rel, revision=self.revision)
        oid, mode = tree_oid, b"40000"
        for part in parts:
            if mode != b"40000":
                raise missing
            entry = self._entry(self._object(oid, "tree"), part.encode("utf-8"))
            if entry is None:
                raise missing
            mode, oid = entry
        if mode not in (b"100644", b"100755"):
            raise missing
        return self._object(oid, "blob")

    def load(self, rel: str, what: str) -> Any:
        raw = self.read(rel, what)
        try:
            return yaml.safe_load(raw)
        except Exception as exc:
            raise Outcome("REJECTED", f"{what}_MALFORMED", path=rel, error=str(exc)) from exc


def resolve_law(tree: PinnedTree) -> dict[str, Any]:
    """Resolve source, profile, and current digests at the pinned revision."""
    registry = tree.load(SOURCES_PATH, "SOURCE_REGISTRY")
    entries = [
        s
        for s in (registry or {}).get("sources", [])
        if isinstance(s, dict) and s.get("id") == SOURCE_REF
    ]
    if len(entries) != 1:
        raise Outcome(
            "BLOCKED", "CANONICAL_SOURCE_UNRESOLVED", source_ref=SOURCE_REF, matches=len(entries)
        )
    source = entries[0]
    if source.get("canonical") is not True or source.get("projection_allowed") is not True:
        raise Outcome("BLOCKED", "CANONICAL_SOURCE_NOT_PROJECTABLE", source_ref=SOURCE_REF)

    catalog = tree.load(PROFILES_PATH, "PROFILE_CATALOG")
    profiles = [
        p
        for p in (catalog or {}).get("projection_profiles", [])
        if isinstance(p, dict) and p.get("id") == PROFILE_REF
    ]
    if len(profiles) != 1:
        raise Outcome(
            "BLOCKED", "PROFILE_UNRESOLVED", profile_ref=PROFILE_REF, matches=len(profiles)
        )
    profile = profiles[0]
    if profile.get("class") != "consumer" or profile.get("consumer") != PROFILE_CONSUMER:
        raise Outcome("BLOCKED", "PROFILE_CONSUMER_MISMATCH", profile_ref=PROFILE_REF)
    selectors = ((profile.get("sources") or {}).get(SOURCE_CLASS) or {}).get("selectors") or []
    if SELECTOR not in selectors:
        raise Outcome(
            "BLOCKED",
            "PROFILE_SELECTOR_COVERAGE_INCOMPLETE",
            source_class=SOURCE_CLASS,
            selector=SELECTOR,
        )
    class_artifact = ((catalog.get("source_classes") or {}).get(SOURCE_CLASS) or {}).get(
        "canonical_artifact"
    )
    if Path(str(source.get("path"))).name != class_artifact:
        raise Outcome(
            "BLOCKED",
            "SOURCE_CLASS_REGISTRY_CONFLICT",
            registry_path=source.get("path"),
            class_artifact=class_artifact,
        )

    raw = tree.read(str(source["path"]), "CANONICAL_SOURCE")
    document = yaml.safe_load(raw)
    global_entries = [
        e
        for e in (document or {}).get("invariants", [])
        if isinstance(e, dict) and e.get("scope") == "global"
    ]
    return {
        "source": {"ref": SOURCE_REF, "path": str(source["path"]), "digest": bytes_digest(raw)},
        "profile": {"ref": PROFILE_REF, "digest": content_digest(profile)},
        "global_entries": {str(e.get("id")): e for e in global_entries},
    }


def _mapping(doc: dict[str, Any], key: str, what: str) -> dict[str, Any]:
    value = doc.get(key)
    if not isinstance(value, dict):
        raise Outcome("REJECTED", f"{what}_{key.upper()}_NOT_A_MAPPING", observed=repr(value))
    return value


def projection_producers(tree: PinnedTree) -> list[str]:
    """Components `.github` assigns the projection role (`organizational_target`)."""
    vocabulary = tree.load(VOCABULARY_PATH, "VOCABULARY")
    targets = (vocabulary or {}).get("organizational_target")
    if not isinstance(targets, dict):
        raise Outcome("BLOCKED", "PRODUCER_ROLE_REGISTRY_UNRESOLVED", path=VOCABULARY_PATH)
    return sorted(
        str(name)
        for name, entry in targets.items()
        if isinstance(entry, dict) and PRODUCER_ROLE in (entry.get("role") or [])
    )


def _required(tree: PinnedTree, schema_path: str) -> tuple[list[str], dict[str, Any]]:
    schema = tree.load(schema_path, "UPSTREAM_SCHEMA")
    required = (schema or {}).get("required")
    if not isinstance(required, list) or not required:
        raise Outcome("BLOCKED", "UPSTREAM_SCHEMA_INCOMPLETE", path=schema_path)
    return [str(r) for r in required], (schema.get("properties") or {})


def _check_shape(doc: Any, tree: PinnedTree, schema_path: str, what: str) -> None:
    if not isinstance(doc, dict):
        raise Outcome("REJECTED", f"{what}_NOT_A_MAPPING")
    required, properties = _required(tree, schema_path)
    missing = sorted(set(required) - set(doc))
    if missing:
        raise Outcome(
            "REJECTED", f"{what}_MISSING_REQUIRED_FIELDS", missing=missing, schema=schema_path
        )
    for key, rule in properties.items():
        if isinstance(rule, dict) and "const" in rule and doc.get(key) != rule["const"]:
            raise Outcome(
                "REJECTED",
                f"{what}_CONST_MISMATCH",
                field=key,
                observed=doc.get(key),
                expected=rule["const"],
            )


def verify_projection(args: argparse.Namespace) -> dict[str, Any]:
    if (
        not args.artifact
        or not args.receipt
        or not Path(args.artifact).is_file()
        or not Path(args.receipt).is_file()
    ):
        raise Outcome(
            "BLOCKED",
            "BLOCKED_UPSTREAM_PROJECTION_PRODUCER",
            detail="no externally supplied producer-emitted projection and receipt; this run"
            " never produces one, and local law is no substitute",
            artifact=args.artifact,
            receipt=args.receipt,
        )
    artifact_path, receipt_path = Path(args.artifact), Path(args.receipt)
    root = Path(args.authority_root)
    coordinates = authority_root(root, args.expect_revision)
    tree = PinnedTree(root, coordinates["revision"])
    law = resolve_law(tree)

    artifact = _load(artifact_path, "ARTIFACT", missing_status="BLOCKED")
    _check_shape(artifact, tree, ARTIFACT_SCHEMA_PATH, "ARTIFACT")
    if artifact["projection_profile_ref"] != PROFILE_REF:
        raise Outcome(
            "REJECTED",
            "PROFILE_IDENTITY_MISMATCH",
            observed=artifact["projection_profile_ref"],
            expected=PROFILE_REF,
        )
    if artifact["source_ref"] != SOURCE_REF:
        raise Outcome(
            "REJECTED",
            "SOURCE_IDENTITY_MISMATCH",
            observed=artifact["source_ref"],
            expected=SOURCE_REF,
        )
    if artifact["source_digest"] != law["source"]["digest"]:
        raise Outcome(
            "STALE",
            "SOURCE_DIGEST_NOT_CURRENT",
            observed=artifact["source_digest"],
            current=law["source"]["digest"],
        )
    if artifact["projection_profile_digest"] != law["profile"]["digest"]:
        raise Outcome(
            "STALE",
            "PROFILE_DIGEST_NOT_CURRENT",
            observed=artifact["projection_profile_digest"],
            current=law["profile"]["digest"],
        )
    payload = artifact["payload"]
    if artifact["projection_digest"] != content_digest(payload):
        raise Outcome(
            "REJECTED", "PROJECTION_DIGEST_MISMATCH", observed=artifact["projection_digest"]
        )

    # Fidelity: digests are unkeyed, so the only anchor against a forged but
    # self-consistent artifact is the canonical source at the bound revision.
    if not isinstance(payload, list) or not all(isinstance(e, dict) and "id" in e for e in payload):
        raise Outcome(
            "BLOCKED",
            "PAYLOAD_SHAPE_UNRESOLVED",
            expected="list of invariant entries selected by " + SELECTOR,
        )
    if not all(isinstance(e["id"], str) for e in payload):
        raise Outcome("REJECTED", "PAYLOAD_IDENTITY_NOT_A_STRING")
    ids = [e["id"] for e in payload]
    if len(ids) != len(set(ids)):
        raise Outcome("REJECTED", "PAYLOAD_DUPLICATE_IDENTITY")
    expected = law["global_entries"]
    if set(ids) != set(expected):
        raise Outcome(
            "REJECTED",
            "PAYLOAD_SELECTOR_COVERAGE_MISMATCH",
            missing=sorted(set(expected) - set(ids)),
            extra=sorted(set(ids) - set(expected)),
        )
    altered = sorted(
        i for i, e in zip(ids, payload) if content_digest(e) != content_digest(expected[i])
    )
    if altered:
        raise Outcome("REJECTED", "PAYLOAD_NOT_FAITHFUL_TO_SOURCE", altered=altered)

    receipt = _load(receipt_path, "RECEIPT", missing_status="BLOCKED")
    _check_shape(receipt, tree, RECEIPT_SCHEMA_PATH, "RECEIPT")
    if receipt["operation"] != "projection" or receipt["result"] != "pass":
        raise Outcome(
            "REJECTED",
            "RECEIPT_NOT_A_PASSING_PROJECTION",
            operation=receipt["operation"],
            result=receipt["result"],
        )
    profile = _mapping(receipt, "profile", "RECEIPT")
    if (
        profile.get("ref") != PROFILE_REF
        or profile.get("digest") != artifact["projection_profile_digest"]
    ):
        raise Outcome("REJECTED", "RECEIPT_PROFILE_MISMATCH", receipt_profile=profile)
    inputs = receipt.get("inputs")
    if not isinstance(inputs, list):
        raise Outcome("REJECTED", "RECEIPT_INPUTS_NOT_A_LIST", observed=repr(inputs))
    if {"ref": SOURCE_REF, "digest": artifact["source_digest"]} not in [
        {"ref": i.get("ref"), "digest": i.get("digest")} for i in inputs if isinstance(i, dict)
    ]:
        raise Outcome("REJECTED", "RECEIPT_INPUT_NOT_BOUND", inputs=inputs)
    if _mapping(receipt, "output", "RECEIPT").get("digest") != artifact["projection_digest"]:
        raise Outcome("REJECTED", "RECEIPT_OUTPUT_NOT_BOUND", output=receipt.get("output"))
    if receipt["receipt_digest"] != content_digest(
        {k: v for k, v in receipt.items() if k != "receipt_digest"}
    ):
        raise Outcome("REJECTED", "RECEIPT_DIGEST_MISMATCH", observed=receipt["receipt_digest"])
    producer = _mapping(receipt, "producer_identity", "RECEIPT")
    if not producer.get("compiler") or not producer.get("version"):
        raise Outcome("REJECTED", "RECEIPT_PRODUCER_UNIDENTIFIED")
    # Receipts are unkeyed: this narrows identity to the upstream-assigned
    # producer role but cannot authenticate it (an upstream signing gap).
    producers = projection_producers(tree)
    if producer["compiler"] not in producers:
        raise Outcome(
            "REJECTED",
            "RECEIPT_PRODUCER_NOT_ASSIGNED_PROJECTION_ROLE",
            observed=producer["compiler"],
            assigned=producers,
        )

    required = list(dict.fromkeys(args.require_invariant or []))
    unknown = [i for i in required if i not in expected]
    if unknown:
        raise Outcome("BLOCKED", "REQUIRED_INVARIANT_NOT_PROJECTED", invariant_ids=unknown)
    applicable = required or ids
    return {
        "status": "BOUND",
        "reason": "PROJECTION_VERIFIED",
        "authority_root": coordinates,
        "profile": law["profile"],
        "source": law["source"],
        "projection": {
            "digest": artifact["projection_digest"],
            "file_digest": bytes_digest(artifact_path.read_bytes()),
        },
        "receipt": {
            "identity": receipt["receipt_identity"],
            "digest": receipt["receipt_digest"],
            "producer": producer,
            # Receipts are unkeyed: the role is checked, the identity is not proven.
            "producer_authentication": "unauthenticated_unkeyed_receipt",
        },
        "applicable_invariants": [
            {"id": i, "digest": content_digest(expected[i])} for i in applicable
        ],
        "global_invariant_count": len(expected),
    }


def verify_prior(args: argparse.Namespace) -> dict[str, Any]:
    """Re-verify an earlier binding under `.github` invalidation rules.

    A prior record is never trusted on its own: its artifact and receipt are
    re-verified against the current authority root, and every bound digest must
    still match.
    """
    prior = _load(Path(args.prior_binding), "PRIOR_BINDING")
    if not isinstance(prior, dict) or prior.get("status") != "BOUND":
        raise Outcome("BLOCKED", "PRIOR_BINDING_NOT_BOUND")
    bound = prior.get("applicable_invariants")
    if (
        not isinstance(bound, list)
        or not bound
        or not all(
            isinstance(i, dict)
            and isinstance(i.get("id"), str)
            and isinstance(i.get("digest"), str)
            for i in bound
        )
    ):
        raise Outcome("BLOCKED", "PRIOR_BINDING_MALFORMED", field="applicable_invariants")
    prior_root = prior.get("authority_root")
    prior_revision = prior_root.get("revision") if isinstance(prior_root, dict) else None
    if not isinstance(prior_revision, str) or not re.fullmatch(r"[0-9a-f]{40}", prior_revision):
        raise Outcome("BLOCKED", "PRIOR_BINDING_MALFORMED", field="authority_root.revision")
    if args.require_invariant:
        raise Outcome("BLOCKED", "PRIOR_BINDING_SELECTION_IS_FIXED")

    root = Path(args.authority_root)
    coordinates = authority_root(root, args.expect_revision)
    law = resolve_law(PinnedTree(root, coordinates["revision"]))
    current = law["global_entries"]
    affected = sorted(
        i["id"]
        for i in bound
        if i["id"] not in current or content_digest(current[i["id"]]) != i["digest"]
    )
    record = {
        "authority_root": coordinates,
        "prior_revision": prior_revision,
        "revision_changed": prior_revision != coordinates["revision"],
        "affected_applicable_invariants": affected,
    }
    if prior.get("source", {}).get("digest") != law["source"]["digest"]:
        raise Outcome("STALE", "SOURCE_DIGEST_CHANGED", **record)
    if prior.get("profile", {}).get("digest") != law["profile"]["digest"]:
        raise Outcome("STALE", "PROFILE_DIGEST_CHANGED", **record)
    if affected:
        raise Outcome("STALE", "APPLICABLE_INVARIANT_DIGEST_CHANGED", **record)

    args.require_invariant = [i["id"] for i in bound]
    reverified = verify_projection(args)
    if reverified["projection"]["digest"] != prior.get("projection", {}).get("digest"):
        raise Outcome("STALE", "PROJECTION_DIGEST_CHANGED", **record)
    reason = (
        "UPSTREAM_REVISION_CHANGED_WITHOUT_DEPENDENCY_IMPACT"
        if record["revision_changed"]
        else "UNCHANGED"
    )
    return {**reverified, "status": "CURRENT", "reason": reason, **record}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--authority-root", required=True, help="exact Quantum-L9/.github checkout")
    parser.add_argument(
        "--artifact", help="producer-emitted l9.projection-artifact/v1 (yaml or json)"
    )
    parser.add_argument("--receipt", help="producer-emitted l9.compiler-receipt/v1 (yaml or json)")
    parser.add_argument("--expect-revision", help="pinned 40-hex authority revision for this run")
    parser.add_argument(
        "--require-invariant", action="append", help="applicable invariant id (repeatable)"
    )
    parser.add_argument("--prior-binding", help="earlier BOUND record to re-check for currentness")
    args = parser.parse_args(argv)
    try:
        record = verify_prior(args) if args.prior_binding else verify_projection(args)
    except Outcome as outcome:
        record = {"status": outcome.status, "reason": outcome.reason, **outcome.detail}
    except Exception as exc:  # any unanticipated shape is Unknown, never a pass
        record = {"status": "BLOCKED", "reason": "VERIFIER_INPUT_UNRESOLVED", "error": repr(exc)}
    record = {"verifier": "l9-coding-agent/scripts/verify_canonical_binding.py", **record}
    print(json.dumps(record, indent=2, sort_keys=True))
    return EXIT[record["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
