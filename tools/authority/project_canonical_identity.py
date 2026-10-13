#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypeGuard

import yaml

ACTOR_ARTIFACT = "l9.actor-registry/global@1"
SURFACE_ARTIFACT = "l9.surface-registry/global@1"
PROFILE_CATALOG_ARTIFACT = "l9.projection-profile-catalog/global@1"
PROFILE_REF = "l9.projection/cursor-governance-identity@1"
OUTPUT_SCHEMA = "l9.projection.cursor-governance-identity/v1"
OUTPUT_ARTIFACT = "l9.projection/cursor-governance-identity@1"
RECEIPT_SCHEMA = "l9.projection-receipt/v1"
ACTOR_PREFIX = f"{ACTOR_ARTIFACT}#"
SURFACE_PREFIX = f"{SURFACE_ARTIFACT}#"
GENERATOR_ID = "cursor-governance.canonical-identity-projector/v1"


class ProjectionError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority-root", type=Path, required=True)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("environment/agents/agent_registry.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("generated/governance/canonical_identity.yaml"),
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        default=Path("generated/governance/canonical_identity.receipt.yaml"),
    )
    parser.add_argument("--source-revision")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


SOURCE_PATHS = {
    "actor_registry": "semantics/actor_registry.yaml",
    "surface_registry": "semantics/surface_registry.yaml",
    "projection_profile": "semantics/projection_profiles.yaml",
}


def main() -> int:
    args = parse_args()
    authority_root = args.authority_root.resolve()
    sources = {
        name: _read_required(authority_root / relative) for name, relative in SOURCE_PATHS.items()
    }
    binding_bytes = _read_required(args.registry)
    source_revision = args.source_revision or _git_revision(authority_root)
    output_bytes, receipt_bytes, _ = render(
        sources=sources,
        binding_bytes=binding_bytes,
        registry_path=args.registry,
        output_path=args.output,
        source_revision=source_revision,
    )
    if args.check:
        failures: list[str] = []
        if not args.output.is_file():
            failures.append(f"missing generated projection: {args.output}")
        elif args.output.read_bytes() != output_bytes:
            failures.append(f"stale generated projection: {args.output}")
        if not args.receipt.is_file():
            failures.append(f"missing projection receipt: {args.receipt}")
        elif args.receipt.read_bytes() != receipt_bytes:
            failures.append(f"stale projection receipt: {args.receipt}")
        if not failures:
            print("canonical identity projection is current")
            return 0
        if args.output.is_file() and args.receipt.is_file():
            historical, reasons = provenance_equivalence(
                authority_root=authority_root,
                current_revision=source_revision,
                current_sources=sources,
                binding_bytes=binding_bytes,
                registry_path=args.registry,
                output_path=args.output,
                committed_output=args.output.read_bytes(),
                committed_receipt=args.receipt.read_bytes(),
            )
            if not reasons:
                print(
                    "canonical identity projection is provenance-equivalent: committed "
                    f"at Quantum-L9/.github@{historical}, governing inputs unchanged "
                    f"through @{source_revision}"
                )
                return 0
            failures.extend(f"not provenance-equivalent: {reason}" for reason in reasons)
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    _write(args.output, output_bytes)
    _write(args.receipt, receipt_bytes)
    print(args.output)
    print(args.receipt)
    return 0


def render(
    *,
    sources: Mapping[str, bytes],
    binding_bytes: bytes,
    registry_path: Path,
    output_path: Path,
    source_revision: str,
) -> tuple[bytes, bytes, dict[str, str]]:
    """Projection bytes, receipt bytes and the governing input digests."""
    actor_path = Path(SOURCE_PATHS["actor_registry"])
    surface_path = Path(SOURCE_PATHS["surface_registry"])
    profile_path = Path(SOURCE_PATHS["projection_profile"])
    actor_registry = _yaml_mapping(sources["actor_registry"], actor_path)
    surface_registry = _yaml_mapping(sources["surface_registry"], surface_path)
    profile_catalog = _yaml_mapping(sources["projection_profile"], profile_path)
    bindings = _yaml_mapping(binding_bytes, registry_path)
    _require_artifact(actor_registry, ACTOR_ARTIFACT, actor_path)
    _require_artifact(surface_registry, SURFACE_ARTIFACT, surface_path)
    _require_artifact(profile_catalog, PROFILE_CATALOG_ARTIFACT, profile_path)
    profile = _projection_profile(profile_catalog, PROFILE_REF)
    actor_ids, surface_ids = _requested_identities(bindings)
    digests = {
        "actor_registry": _digest(sources["actor_registry"]),
        "surface_registry": _digest(sources["surface_registry"]),
        "projection_profile": _object_digest(profile),
    }
    projection = project(
        actor_registry=actor_registry,
        surface_registry=surface_registry,
        actor_ids=actor_ids,
        surface_ids=surface_ids,
        source_revision=source_revision,
        actor_digest=digests["actor_registry"],
        surface_digest=digests["surface_registry"],
        profile_digest=digests["projection_profile"],
    )
    output_bytes = _dump_yaml(projection)
    receipt = build_receipt(
        projection=projection,
        output_path=output_path,
        output_digest=_digest(output_bytes),
    )
    return output_bytes, _dump_yaml(receipt), digests


def provenance_equivalence(
    *,
    authority_root: Path,
    current_revision: str,
    current_sources: Mapping[str, bytes],
    binding_bytes: bytes,
    registry_path: Path,
    output_path: Path,
    committed_output: bytes,
    committed_receipt: bytes,
) -> tuple[str | None, list[str]]:
    """Accept a committed projection whose only difference is an upstream revision advance.

    The canonical dependency model (``.github`` ``semantic_dependency_model``) marks
    dependents stale on a source or profile digest change, and on a bare upstream
    revision change requires evaluating dependency impact; historical artifacts are
    immutable. So the committed projection stays valid, keeping its own historical
    ``source_revision``, only when every condition below is proven:

    1. its source revision is a commit in the authority checkout and an ancestor of
       (or equal to) the current authority revision;
    2. the committed projection and receipt are reproduced byte-for-byte from the
       authority sources at that exact historical commit;
    3. every governing input the profile declares (actor registry, surface registry,
       selected projection profile) has the same digest at the current revision, and
       the current inputs reproduce the committed bytes under the historical label.

    Returns ``(historical_revision, reasons)``; an empty ``reasons`` means equivalent.
    Anything unprovable is a reason: this never relaxes to a permissive match.
    """

    reasons: list[str] = []
    try:
        committed = _yaml_mapping(committed_output, output_path)
        receipt = _yaml_mapping(committed_receipt, output_path)
        historical = _mapping(committed.get("projection"), "projection").get("source_revision")
        receipt_revision = _mapping(receipt.get("projection"), "receipt.projection").get(
            "source_revision"
        )
    except ProjectionError as exc:
        return None, [f"committed projection or receipt is unreadable: {exc}"]
    if not _is_git_sha(historical):
        return None, ["committed projection carries no pinned source revision"]
    if receipt_revision != historical:
        reasons.append("receipt source_revision disagrees with projection source_revision")
    if historical == current_revision:
        reasons.append("committed projection claims the current revision but its content differs")
        return historical, reasons
    if not _git_ok(authority_root, "cat-file", "-e", f"{historical}^{{commit}}"):
        reasons.append(
            f"historical revision {historical} is not a commit in the authority checkout "
            "(unverifiable provenance; a shallow checkout cannot prove it)"
        )
        return historical, reasons
    if not _git_ok(authority_root, "merge-base", "--is-ancestor", historical, current_revision):
        reasons.append(
            f"historical revision {historical} is not an ancestor of the current authority "
            f"revision {current_revision}"
        )
        return historical, reasons
    historical_sources: dict[str, bytes] = {}
    for name, relative in SOURCE_PATHS.items():
        blob = _git_show(authority_root, historical, relative)
        if blob is None:
            reasons.append(f"{relative} is missing at historical revision {historical}")
        else:
            historical_sources[name] = blob
    if reasons:
        return historical, reasons
    try:
        replay_output, replay_receipt, historical_digests = render(
            sources=historical_sources,
            binding_bytes=binding_bytes,
            registry_path=registry_path,
            output_path=output_path,
            source_revision=historical,
        )
        relabel_output, relabel_receipt, current_digests = render(
            sources=current_sources,
            binding_bytes=binding_bytes,
            registry_path=registry_path,
            output_path=output_path,
            source_revision=historical,
        )
    except ProjectionError as exc:
        return historical, [f"historical projection cannot be reproduced: {exc}"]
    if replay_output != committed_output:
        reasons.append(f"committed projection is not reproducible from @{historical}")
    if replay_receipt != committed_receipt:
        reasons.append(f"committed receipt is not reproducible from @{historical}")
    for name in SOURCE_PATHS:
        if historical_digests[name] != current_digests[name]:
            reasons.append(f"governing input {name} changed between @{historical} and current")
    if not reasons and (relabel_output, relabel_receipt) != (committed_output, committed_receipt):
        reasons.append("current governing inputs do not reproduce the committed projection")
    return historical, reasons


def project(
    *,
    actor_registry: Mapping[str, Any],
    surface_registry: Mapping[str, Any],
    actor_ids: set[str],
    surface_ids: set[str],
    source_revision: str,
    actor_digest: str,
    surface_digest: str,
    profile_digest: str,
) -> dict[str, Any]:
    actors = _select_entries(
        collection=actor_registry.get("actors"),
        requested=actor_ids,
        kind="actor",
    )
    surfaces = _select_entries(
        collection=surface_registry.get("surfaces"),
        requested=surface_ids,
        kind="surface",
    )
    actor_aliases = _select_aliases(
        actor_registry.get("aliases"),
        actor_ids,
    )
    surface_aliases = _select_aliases(
        surface_registry.get("aliases"),
        surface_ids,
    )
    return {
        "schema": OUTPUT_SCHEMA,
        "artifact_id": OUTPUT_ARTIFACT,
        "canonical": False,
        "authority": {
            "authority_class": "derived",
            "canonical_owner": "Quantum-L9/.github",
            "consumer": "Quantum-L9/Cursor-Governance",
        },
        "projection": {
            "profile_ref": PROFILE_REF,
            "profile_digest": profile_digest,
            "source_repository": "Quantum-L9/.github",
            "source_revision": source_revision,
            "sources": {
                "actor_registry": {
                    "artifact_ref": ACTOR_ARTIFACT,
                    "digest": actor_digest,
                },
                "surface_registry": {
                    "artifact_ref": SURFACE_ARTIFACT,
                    "digest": surface_digest,
                },
            },
        },
        "identity_dimensions": {
            "actor": {
                "artifact_ref": ACTOR_ARTIFACT,
                "source_schema": actor_registry.get("schema"),
            },
            "surface": {
                "artifact_ref": SURFACE_ARTIFACT,
                "source_schema": surface_registry.get("schema"),
            },
        },
        "actors": actors,
        "actor_aliases": actor_aliases,
        "surfaces": surfaces,
        "surface_aliases": surface_aliases,
    }


def build_receipt(
    *,
    projection: Mapping[str, Any],
    output_path: Path,
    output_digest: str,
) -> dict[str, Any]:
    metadata = _mapping(projection.get("projection"), "projection")
    return {
        "schema": RECEIPT_SCHEMA,
        "projection": {
            "artifact_ref": OUTPUT_ARTIFACT,
            "profile_ref": metadata["profile_ref"],
            "profile_digest": metadata["profile_digest"],
            "source_repository": metadata["source_repository"],
            "source_revision": metadata["source_revision"],
            "sources": metadata["sources"],
        },
        "output": {
            "path": output_path.as_posix(),
            "schema": OUTPUT_SCHEMA,
            "digest": output_digest,
        },
        "generator": {
            "id": GENERATOR_ID,
            "deterministic": True,
        },
    }


def _requested_identities(
    bindings: Mapping[str, Any],
) -> tuple[set[str], set[str]]:
    if bindings.get("schema") != "l9.cursor-governance.agent-bindings/v2":
        raise ProjectionError("unsupported agent binding schema")
    raw_agents = bindings.get("agents")
    if not isinstance(raw_agents, Mapping):
        raise ProjectionError("agents must be a mapping")
    actor_ids: set[str] = set()
    surface_ids: set[str] = set()
    for binding_id, raw in raw_agents.items():
        agent = _mapping(raw, f"agents.{binding_id}")
        actor_ref = _required_string(agent, "actor_ref")
        actor_ids.add(_ref_fragment(actor_ref, ACTOR_PREFIX, "actor"))
        refs = agent.get("surface_refs")
        if not isinstance(refs, list) or not refs:
            raise ProjectionError(f"agents.{binding_id}.surface_refs must be a non-empty list")
        for surface_ref in refs:
            if not isinstance(surface_ref, str):
                raise ProjectionError(f"agents.{binding_id}.surface_refs entries must be strings")
            surface_ids.add(_ref_fragment(surface_ref, SURFACE_PREFIX, "surface"))
    return actor_ids, surface_ids


def _select_entries(
    *,
    collection: Any,
    requested: set[str],
    kind: str,
) -> list[dict[str, Any]]:
    if not isinstance(collection, list):
        raise ProjectionError(f"{kind} registry collection must be a list")
    by_id: dict[str, Mapping[str, Any]] = {}
    for raw in collection:
        item = _mapping(raw, kind)
        item_id = _required_string(item, "id")
        if item_id in by_id:
            raise ProjectionError(f"duplicate canonical {kind}: {item_id}")
        by_id[item_id] = item
    missing = requested - set(by_id)
    if missing:
        raise ProjectionError(f"unresolved canonical {kind} identities: {sorted(missing)}")
    return [dict(by_id[item_id]) for item_id in sorted(requested)]


def _select_aliases(
    collection: Any,
    canonical_ids: set[str],
) -> list[dict[str, Any]]:
    if collection is None:
        return []
    if not isinstance(collection, list):
        raise ProjectionError("alias collection must be a list")
    selected: list[dict[str, Any]] = []
    for raw in collection:
        alias = _mapping(raw, "alias")
        canonical = alias.get("canonical")
        if canonical in canonical_ids:
            selected.append(dict(alias))
    selected.sort(key=lambda item: str(item.get("alias", "")))
    return selected


def _projection_profile(
    catalog: Mapping[str, Any],
    profile_ref: str,
) -> Mapping[str, Any]:
    profiles = catalog.get("projection_profiles")
    if not isinstance(profiles, list):
        raise ProjectionError("projection_profiles must be a list")
    matches = [
        _mapping(item, "projection_profile")
        for item in profiles
        if isinstance(item, Mapping) and item.get("id") == profile_ref
    ]
    if len(matches) != 1:
        raise ProjectionError(
            f"canonical projection profile must resolve exactly once: {profile_ref}"
        )
    profile = matches[0]
    if profile.get("consumer") != "Cursor-Governance":
        raise ProjectionError(f"{profile_ref} must declare consumer Cursor-Governance")
    return profile


def _require_artifact(
    document: Mapping[str, Any],
    expected: str,
    path: Path,
) -> None:
    if document.get("artifact_id") != expected:
        raise ProjectionError(
            f"{path}: expected artifact {expected}, got {document.get('artifact_id')}"
        )
    if document.get("canonical") is not True:
        raise ProjectionError(f"{path}: canonical source must declare canonical=true")


def _ref_fragment(value: str, prefix: str, kind: str) -> str:
    if not value.startswith(prefix):
        raise ProjectionError(f"{kind} ref must use canonical prefix {prefix}: {value}")
    fragment = value[len(prefix) :]
    if not fragment:
        raise ProjectionError(f"{kind} ref has empty coordinate: {value}")
    return fragment


def _git_revision(root: Path) -> str:
    git = shutil.which("git")
    if git is None:
        raise ProjectionError("git is required to resolve authority revision")
    result = subprocess.run(
        [git, "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise ProjectionError(f"unable to resolve authority revision: {result.stderr.strip()}")
    revision = result.stdout.strip()
    if len(revision) != 40:
        raise ProjectionError(f"unexpected git revision: {revision}")
    return revision


def _is_git_sha(value: Any) -> TypeGuard[str]:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(char in "0123456789abcdef" for char in value)
    )


def _git_ok(root: Path, *args: str) -> bool:
    git = shutil.which("git")
    if git is None:
        return False
    result = subprocess.run(
        [git, "-C", str(root), *args],
        capture_output=True,
        check=False,
        timeout=30,
    )
    return result.returncode == 0


def _git_show(root: Path, revision: str, relative: str) -> bytes | None:
    git = shutil.which("git")
    if git is None:
        return None
    result = subprocess.run(
        [git, "-C", str(root), "show", f"{revision}:{relative}"],
        capture_output=True,
        check=False,
        timeout=30,
    )
    return result.stdout if result.returncode == 0 else None


def _read_required(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError as exc:
        raise ProjectionError(f"required file is missing: {path}") from exc


def _yaml_mapping(raw: bytes, path: Path) -> Mapping[str, Any]:
    try:
        value = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ProjectionError(f"invalid YAML in {path}: {exc}") from exc
    return _mapping(value, str(path))


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProjectionError(f"{label} must be a mapping")
    return value


def _required_string(value: Mapping[str, Any], key: str) -> str:
    resolved = value.get(key)
    if not isinstance(resolved, str) or not resolved:
        raise ProjectionError(f"{key} must be a non-empty string")
    return resolved


def _digest(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _object_digest(value: Mapping[str, Any]) -> str:
    raw = yaml.safe_dump(
        dict(value),
        sort_keys=True,
        allow_unicode=True,
    ).encode("utf-8")
    return _digest(raw)


def _dump_yaml(value: Mapping[str, Any]) -> bytes:
    return yaml.safe_dump(
        dict(value),
        sort_keys=False,
        allow_unicode=True,
        width=100,
    ).encode("utf-8")


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


if __name__ == "__main__":
    raise SystemExit(main())
