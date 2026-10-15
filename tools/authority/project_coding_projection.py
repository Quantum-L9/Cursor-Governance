#!/usr/bin/env python3
"""Project ``l9.projection/coding-agent-execution@1`` from Quantum-L9/.github.

The profile is canonical upstream (Quantum-L9/.github, admitted in #179); this
module only executes it. Every source byte is read from the authority checkout
at the revision pinned in the local binding
(``governance/authority-bindings/coding-agent-execution.yaml``) with
``git show <revision>:<path>`` — never from a working tree, never fetched — and
the checkout must prove it is ``Quantum-L9/.github`` by its origin remote.

Output, one artifact per source ledger plus one receipt:

* ``generated/governance/coding_projection/<source>.projection.yaml``
  (``l9.projection-artifact/v1``; the schema carries one ``source_ref``, the
  profile reads three ledgers, so each ledger gets its own artifact).
* ``generated/governance/coding_projection/compiler_receipt.yaml``
  (``l9.compiler-receipt/v1``).

Digests: ``source_digest`` is sha256 over the raw ledger bytes; profile,
payload, output and receipt digests are sha256 over canonical JSON (sorted
keys, compact separators, UTF-8) — the form ``validate-semantics.py`` RC-028
pins the admitted profile entry with. Upstream does not declare a
``semantic_digest`` canonicalization; this is a consumer-local choice and the
binding says so.

``--check`` re-renders at the pinned revision and byte-compares; it never
writes. This module grants no execution, publication or merge authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.authority.project_canonical_identity import (  # noqa: E402
    ProjectionError,
    _digest,
    _dump_yaml,
    _is_git_sha,
    _mapping,
    _required_string,
    _write,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BINDING_PATH = Path("governance/authority-bindings/coding-agent-execution.yaml")
BINDING_SCHEMA = "l9.cursor-governance.coding-projection-binding/v1"
OUTPUT_DIR = Path("generated/governance/coding_projection")
RECEIPT_NAME = "compiler_receipt.yaml"
ARTIFACT_SCHEMA = "l9.projection-artifact/v1"
RECEIPT_SCHEMA = "l9.compiler-receipt/v1"
RECEIPT_TYPE = "l9.receipt/compilation@1"
GENERATOR_ID = "cursor-governance.coding-projection-producer/v1"
GENERATOR_VERSION = "1"
PROFILE_KEYS = frozenset({"id", "class", "consumer", "purpose", "sources", "output", "forbidden"})

#: Only the canonical authority repository may be projected from.
_ORIGIN = re.compile(
    r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"Quantum-L9/\.github(?:\.git)?/?$",
    re.IGNORECASE,
)
_RECORD_SELECTOR = re.compile(r'^\$\.([a-z_]+)\[\?\(@\.id=="([^"]+)"\)\]$')
_SECTION_SELECTOR = re.compile(r"^\$\.([a-z_]+)$")


def canonical_digest(value: Any) -> str:
    """sha256 over canonical JSON (the RC-028 form), ``sha256:``-prefixed."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"sha256:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    env = {**os.environ, "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=False,
        timeout=30,
        env=env,
    )


def verify_authority(root: Path) -> None:
    """Fail unless ``root`` is the top of a Quantum-L9/.github checkout."""
    top = _git(root, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        raise ProjectionError(f"authority root is not a git checkout: {root}")
    if Path(top.stdout.decode().strip()).resolve() != root.resolve():
        raise ProjectionError(f"authority root is not a repository top level: {root}")
    origin = _git(root, "remote", "get-url", "origin")
    url = origin.stdout.decode().strip()
    if origin.returncode != 0 or not _ORIGIN.match(url):
        raise ProjectionError(f"authority origin is not Quantum-L9/.github: {url or '<none>'}")


def has_commit(root: Path, revision: str) -> bool:
    return _git(root, "cat-file", "-e", f"{revision}^{{commit}}").returncode == 0


def resolve_ref(root: Path, ref: str) -> str | None:
    result = _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    value = result.stdout.decode().strip()
    return value if result.returncode == 0 and _is_git_sha(value) else None


def is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    return _git(root, "merge-base", "--is-ancestor", ancestor, descendant).returncode == 0


def _show(root: Path, revision: str, path: str) -> bytes:
    result = _git(root, "show", f"{revision}:{path}")
    if result.returncode != 0:
        raise ProjectionError(f"source missing at {revision[:12]}: {path}")
    return result.stdout


def _load(raw: bytes, label: str) -> Mapping[str, Any]:
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    try:
        return _mapping(yaml.load(raw, Loader=loader), label)  # noqa: S506 - safe loader
    except yaml.YAMLError as exc:
        raise ProjectionError(f"invalid YAML in {label}: {exc}") from exc


def load_binding(path: Path) -> dict[str, Any]:
    binding = dict(_load(path.read_bytes() if path.is_file() else b"", str(path)))
    if binding.get("schema") != BINDING_SCHEMA:
        raise ProjectionError(f"{path}: schema must be {BINDING_SCHEMA}")
    upstream = _mapping(binding.get("upstream"), "binding.upstream")
    if not _is_git_sha(upstream.get("revision")):
        raise ProjectionError("binding.upstream.revision must be a 40-hex commit")
    pin = _required_string(upstream, "profile_digest")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", pin):
        raise ProjectionError("binding.upstream.profile_digest must be sha256:<64 hex>")
    sources = _mapping(binding.get("sources"), "binding.sources")
    for name, entry in sources.items():
        entry = _mapping(entry, f"binding.sources.{name}")
        for key in ("source_ref", "path", "artifact_id"):
            _required_string(entry, key)
    return binding


def _profile(catalog: Mapping[str, Any], binding: Mapping[str, Any]) -> Mapping[str, Any]:
    upstream = binding["upstream"]
    ref = upstream["profile_ref"]
    matches = [
        item
        for item in catalog.get("projection_profiles") or []
        if isinstance(item, Mapping) and item.get("id") == ref
    ]
    if len(matches) != 1:
        raise ProjectionError(f"profile must resolve exactly once: {ref}")
    profile = matches[0]
    if set(profile) != PROFILE_KEYS:
        raise ProjectionError(f"{ref}: unexpected profile keys {sorted(map(str, profile))}")
    if profile.get("consumer") != "Cursor-Governance" or profile.get("class") != "runtime":
        raise ProjectionError(f"{ref}: must be a runtime profile for Cursor-Governance")
    digest = canonical_digest(profile)
    if digest != upstream["profile_digest"]:
        raise ProjectionError(
            f"{ref}: profile digest {digest} does not match the binding pin "
            f"{upstream['profile_digest']} (profile changed upstream: rebind deliberately)"
        )
    output = _mapping(profile.get("output"), f"{ref}.output")
    if output.get("schema") != upstream["output_schema"]:
        raise ProjectionError(f"{ref}: output schema is not {upstream['output_schema']}")
    return profile


def _select(document: Mapping[str, Any], selectors: list[Any], label: str) -> list[Any]:
    selected: list[Any] = []
    for selector in selectors:
        if not isinstance(selector, str):
            raise ProjectionError(f"{label}: selector must be a string")
        record = _RECORD_SELECTOR.match(selector)
        section = _SECTION_SELECTOR.match(selector)
        if record:
            collection, record_id = record.groups()
            items = document.get(collection)
            if not isinstance(items, list):
                raise ProjectionError(f"{label}: {collection} is not a list")
            hits = [i for i in items if isinstance(i, Mapping) and i.get("id") == record_id]
            if len(hits) != 1:
                raise ProjectionError(f"{label}: {selector} matched {len(hits)} records")
            selected.append(hits[0])
        elif section:
            (key,) = section.groups()
            if key not in document:
                raise ProjectionError(f"{label}: {selector} names no section")
            selected.append({key: document[key]})
        else:
            # Only exact-id filters and top-level sections are admitted (RC-028);
            # anything else would be executable selector code.
            raise ProjectionError(f"{label}: unsupported selector {selector}")
    return selected


def _registered(registry: Mapping[str, Any], source_ref: str, path: str) -> None:
    entries = [
        e
        for e in registry.get("canonical_sources") or registry.get("sources") or []
        if isinstance(e, Mapping) and e.get("id") == source_ref
    ]
    if len(entries) != 1:
        raise ProjectionError(f"{source_ref} must be registered exactly once")
    entry = entries[0]
    if entry.get("path") != path or entry.get("canonical") is not True:
        raise ProjectionError(f"{source_ref}: registry path/canonical mismatch")
    if entry.get("projection_allowed") is not True:
        raise ProjectionError(f"{source_ref}: projection is not allowed")


def render(root: Path, binding: Mapping[str, Any], revision: str) -> dict[str, bytes]:
    """Every output file (relative name -> bytes) for ``revision``."""
    upstream = binding["upstream"]
    catalog = _load(_show(root, revision, upstream["profile_path"]), "projection_profiles")
    profile = _profile(catalog, binding)
    registry = _load(_show(root, revision, upstream["registry_path"]), "canonical_sources")
    profile_digest = canonical_digest(profile)
    profile_sources = _mapping(profile.get("sources"), "profile.sources")
    if set(profile_sources) != set(binding["sources"]):
        raise ProjectionError(
            f"profile source classes {sorted(profile_sources)} differ from the binding "
            f"{sorted(binding['sources'])}"
        )

    files: dict[str, bytes] = {}
    inputs: list[dict[str, str]] = []
    outputs: dict[str, str] = {}
    for name in sorted(binding["sources"]):
        entry = binding["sources"][name]
        _registered(registry, entry["source_ref"], entry["path"])
        raw = _show(root, revision, entry["path"])
        document = _load(raw, entry["path"])
        if (
            document.get("artifact_id") != entry["artifact_id"]
            or document.get("canonical") is not True
        ):
            raise ProjectionError(f"{entry['path']}: not canonical {entry['artifact_id']}")
        selectors = _mapping(profile_sources[name], f"sources.{name}").get("selectors")
        records = _select(document, list(selectors or []), name)
        payload = {
            "output_schema": upstream["output_schema"],
            "source_class": name,
            "records": records,
        }
        artifact = {
            "schema": ARTIFACT_SCHEMA,
            "source_ref": entry["source_ref"],
            "source_digest": _digest(raw),
            "projection_profile_ref": upstream["profile_ref"],
            "projection_profile_digest": profile_digest,
            "provenance": {
                "source_repository": upstream["repository"],
                "source_revision": revision,
                "source_path": entry["path"],
                "canonical": False,
                "derived": True,
            },
            "generated_by": {"compiler": GENERATOR_ID, "version": GENERATOR_VERSION},
            "payload": payload,
            "projection_digest": canonical_digest(payload),
        }
        filename = f"{name}.projection.yaml"
        files[filename] = _dump_yaml(artifact)
        inputs.append({"ref": entry["source_ref"], "digest": artifact["source_digest"]})
        outputs[filename] = artifact["projection_digest"]

    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "receipt_identity": f"{GENERATOR_ID}#{revision}",
        "receipt_type": RECEIPT_TYPE,
        "exact_subject_ref": upstream["profile_ref"],
        "claim": (
            f"{upstream['profile_ref']} executed against {upstream['repository']}@{revision}; "
            "one projection artifact per selected source ledger"
        ),
        "operation": "projection",
        "inputs": inputs,
        "profile": {"ref": upstream["profile_ref"], "digest": profile_digest},
        "output": {"ref": upstream["output_schema"], "digest": canonical_digest(outputs)},
        "outputs": outputs,
        "governing_coordinates": {
            "source_repository": upstream["repository"],
            "source_revision": revision,
            "profile_pin": upstream["profile_digest"],
        },
        "result": "pass",
        "verification_basis": {
            "source_read": "git show <revision>:<path> from a checkout whose origin is "
            "Quantum-L9/.github",
            "profile_pin": "canonical JSON digest equals the binding pin (RC-028 form)",
            "selectors": "exact-id filters and top-level sections only; each resolves once",
            "digest_canonicalization": "consumer-local: sha256 over canonical JSON "
            "(sorted keys, compact separators, UTF-8); upstream declares none",
        },
        "producer_identity": {"compiler": GENERATOR_ID, "version": GENERATOR_VERSION},
    }
    receipt["receipt_digest"] = canonical_digest(receipt)
    files[RECEIPT_NAME] = _dump_yaml(receipt)
    return files


def check_integrity(output_dir: Path, binding: Mapping[str, Any]) -> list[str]:
    """Problems with the committed outputs, read without any upstream access.

    Detects tampering (a digest that no longer matches its content), a forged
    or partial receipt, and a projection bound to another revision or profile.
    """
    problems: list[str] = []
    upstream = binding["upstream"]
    receipt_path = output_dir / RECEIPT_NAME
    if not receipt_path.is_file():
        return [f"missing receipt: {receipt_path}"]
    try:
        receipt = dict(_load(receipt_path.read_bytes(), str(receipt_path)))
    except ProjectionError as exc:
        return [str(exc)]
    claimed = receipt.pop("receipt_digest", None)
    if claimed != canonical_digest(receipt):
        problems.append("receipt digest does not match its content (forged or edited)")
    coordinates = receipt.get("governing_coordinates") or {}
    if coordinates.get("source_revision") != upstream["revision"]:
        problems.append("receipt is bound to a different upstream revision than the binding")
    if (receipt.get("profile") or {}).get("digest") != upstream["profile_digest"]:
        problems.append("receipt profile digest differs from the binding pin")
    if receipt.get("result") != "pass":
        problems.append(f"receipt result is {receipt.get('result')!r}, not pass")
    outputs = receipt.get("outputs")
    if not isinstance(outputs, dict) or set(outputs) != {
        f"{name}.projection.yaml" for name in binding["sources"]
    }:
        return [*problems, "receipt does not list exactly one artifact per bound source"]
    if (receipt.get("output") or {}).get("digest") != canonical_digest(outputs):
        problems.append("receipt output digest does not cover its artifact list")
    for filename, digest in sorted(outputs.items()):
        path = output_dir / filename
        if not path.is_file():
            problems.append(f"missing artifact: {filename}")
            continue
        try:
            artifact = _load(path.read_bytes(), filename)
        except ProjectionError as exc:
            problems.append(str(exc))
            continue
        if artifact.get("projection_digest") != canonical_digest(artifact.get("payload")):
            problems.append(f"{filename}: payload does not match projection_digest (tampered)")
        if artifact.get("projection_digest") != digest:
            problems.append(f"{filename}: not the artifact the receipt names")
        if artifact.get("projection_profile_digest") != upstream["profile_digest"]:
            problems.append(f"{filename}: profile digest differs from the binding pin")
    return problems


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--authority-root", type=Path, required=True)
    parser.add_argument("--binding", type=Path, default=REPO_ROOT / BINDING_PATH)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / OUTPUT_DIR)
    parser.add_argument("--check", action="store_true", help="byte-compare; never write")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        binding = load_binding(args.binding)
        root = args.authority_root.resolve()
        verify_authority(root)
        revision = binding["upstream"]["revision"]
        if not has_commit(root, revision):
            raise ProjectionError(f"pinned revision {revision} is not in {root} (fetch it)")
        files = render(root, binding, revision)
    except ProjectionError as exc:
        print(f"FAIL coding-projection: {exc}", file=sys.stderr)
        return 1
    if args.check:
        stale = [
            name
            for name, content in files.items()
            if not (args.output_dir / name).is_file()
            or (args.output_dir / name).read_bytes() != content
        ]
        extra = (
            sorted(p.name for p in args.output_dir.glob("*.yaml") if p.name not in files)
            if args.output_dir.is_dir()
            else []
        )
        if stale or extra:
            for name in stale:
                print(f"FAIL coding-projection: missing/stale {name}", file=sys.stderr)
            for name in extra:
                print(f"FAIL coding-projection: unexpected {name}", file=sys.stderr)
            return 1
        print(f"PASS coding-projection: reproduces from Quantum-L9/.github@{revision[:12]}")
        return 0
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        _write(args.output_dir / name, content)
    print(f"wrote {len(files)} files to {args.output_dir} from @{revision[:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
