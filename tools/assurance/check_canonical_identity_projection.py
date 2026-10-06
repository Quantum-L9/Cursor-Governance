#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
BINDING_PATH = ROOT / "governance" / "authority-bindings" / "canonical-agent-identity.yaml"
AGENT_REGISTRY_PATH = ROOT / "environment" / "agents" / "agent_registry.yaml"
PROJECTION_PATH = ROOT / "generated" / "governance" / "canonical_identity.yaml"
RECEIPT_PATH = ROOT / "generated" / "governance" / "canonical_identity.receipt.yaml"
ACTOR_PREFIX = "l9.actor-registry/global@1#"
SURFACE_PREFIX = "l9.surface-registry/global@1#"
FORBIDDEN_AGENT_FIELDS = {
    "agent_id",
    "source",
    "surfaces",
    "actor_kind",
    "actor_status",
    "surface_status",
    "aliases",
}


def main() -> int:
    failures: list[str] = []
    for path in (
        BINDING_PATH,
        AGENT_REGISTRY_PATH,
        PROJECTION_PATH,
        RECEIPT_PATH,
    ):
        if not path.is_file():
            failures.append(f"missing required file: {path}")
    if failures:
        return _report(failures)
    binding = _load_yaml(BINDING_PATH, failures)
    registry = _load_yaml(AGENT_REGISTRY_PATH, failures)
    projection = _load_yaml(PROJECTION_PATH, failures)
    receipt = _load_yaml(RECEIPT_PATH, failures)
    if failures:
        return _report(failures)
    _validate_binding(binding, failures)
    _validate_projection(binding, projection, failures)
    _validate_receipt(binding, projection, receipt, failures)
    _validate_agent_registry(registry, projection, failures)
    if failures:
        return _report(failures)
    agents = _mapping(registry.get("agents"))
    print(f"canonical identity projection governance: PASS ({len(agents)} operating bindings)")
    return 0


def _validate_binding(
    binding: Mapping[str, Any],
    failures: list[str],
) -> None:
    if binding.get("schema") != "l9.cursor-governance.identity-binding/v1":
        failures.append("invalid identity governing binding schema")
    if binding.get("canonical") is not True:
        failures.append("local identity governing binding must be canonical")
    authority = _mapping(binding.get("authority"))
    if authority.get("authority_class") != "local_canonical_binding":
        failures.append("identity binding authority class is invalid")
    governing = _mapping(binding.get("governing_binding"))
    if governing.get("enabled") is not True:
        failures.append("identity governing binding must be enabled")
    if governing.get("failure_mode") != "fail_closed":
        failures.append("identity governing binding must fail closed")


def _validate_projection(
    binding: Mapping[str, Any],
    projection: Mapping[str, Any],
    failures: list[str],
) -> None:
    generated = _mapping(binding.get("generated_projection"))
    if projection.get("schema") != generated.get("schema"):
        failures.append("identity projection schema disagrees with binding")
    if projection.get("artifact_id") != generated.get("artifact_ref"):
        failures.append("identity projection artifact disagrees with binding")
    if projection.get("canonical") is not False:
        failures.append("generated identity projection must be non-canonical")
    authority = _mapping(projection.get("authority"))
    if authority.get("authority_class") != "derived":
        failures.append("identity projection authority must be derived")
    if authority.get("canonical_owner") != "Quantum-L9/.github":
        failures.append("identity projection canonical owner must be Quantum-L9/.github")
    metadata = _mapping(projection.get("projection"))
    upstream = _mapping(binding.get("upstream"))
    expected_profile = _mapping(upstream.get("projection_profile")).get("artifact_ref")
    if metadata.get("profile_ref") != expected_profile:
        failures.append("identity projection profile disagrees with binding")
    profile_digest = metadata.get("profile_digest")
    if not _sha256_value(profile_digest):
        failures.append("identity projection has invalid profile digest")
    source_revision = metadata.get("source_revision")
    if not _git_sha(source_revision):
        failures.append("identity projection must carry a pinned git SHA")
    sources = _mapping(metadata.get("sources"))
    actor_source = _mapping(sources.get("actor_registry"))
    surface_source = _mapping(sources.get("surface_registry"))
    if actor_source.get("artifact_ref") != "l9.actor-registry/global@1":
        failures.append("actor registry source coordinate is invalid")
    if surface_source.get("artifact_ref") != "l9.surface-registry/global@1":
        failures.append("surface registry source coordinate is invalid")
    if not _sha256_value(actor_source.get("digest")):
        failures.append("actor registry source digest is invalid")
    if not _sha256_value(surface_source.get("digest")):
        failures.append("surface registry source digest is invalid")


def _validate_receipt(
    binding: Mapping[str, Any],
    projection: Mapping[str, Any],
    receipt: Mapping[str, Any],
    failures: list[str],
) -> None:
    if receipt.get("schema") != "l9.projection-receipt/v1":
        failures.append("invalid identity projection receipt schema")
        return
    generated = _mapping(binding.get("generated_projection"))
    projected = _mapping(projection.get("projection"))
    receipt_projection = _mapping(receipt.get("projection"))
    if receipt_projection.get("artifact_ref") != generated.get("artifact_ref"):
        failures.append("receipt artifact reference disagrees with binding")
    for key in (
        "profile_ref",
        "profile_digest",
        "source_repository",
        "source_revision",
    ):
        if receipt_projection.get(key) != projected.get(key):
            failures.append(f"receipt {key} disagrees with projection")
    if receipt_projection.get("sources") != projected.get("sources"):
        failures.append("receipt source coordinates disagree with projection")
    output = _mapping(receipt.get("output"))
    actual_digest = "sha256:" + hashlib.sha256(PROJECTION_PATH.read_bytes()).hexdigest()
    if output.get("digest") != actual_digest:
        failures.append("identity projection output digest does not match receipt")


def _validate_agent_registry(
    registry: Mapping[str, Any],
    projection: Mapping[str, Any],
    failures: list[str],
) -> None:
    if registry.get("schema") != "l9.cursor-governance.agent-bindings/v2":
        failures.append("invalid operating-plane agent binding schema")
        return
    agents = registry.get("agents")
    roles = registry.get("roles")
    if not isinstance(agents, Mapping):
        failures.append("agents must be a mapping")
        return
    if not isinstance(roles, Mapping):
        failures.append("roles must be a mapping")
        roles = {}
    actors = _index(projection.get("actors"), "actor", failures)
    surfaces = _index(projection.get("surfaces"), "surface", failures)
    seen_principals: set[str] = set()
    seen_users: set[str] = set()
    for binding_id, raw_agent in agents.items():
        agent = _mapping(raw_agent)
        forbidden = FORBIDDEN_AGENT_FIELDS.intersection(agent)
        if forbidden:
            failures.append(
                f"agents.{binding_id} redeclares canonical identity fields: {sorted(forbidden)}"
            )
        actor_ref = agent.get("actor_ref")
        if not isinstance(actor_ref, str) or not actor_ref.startswith(ACTOR_PREFIX):
            failures.append(
                f"agents.{binding_id}.actor_ref must reference canonical actor registry"
            )
            continue
        actor_id = actor_ref[len(ACTOR_PREFIX) :]
        actor = actors.get(actor_id)
        if actor is None:
            failures.append(f"agents.{binding_id} references unresolved actor {actor_id}")
        elif agent.get("binding_status") == "active" and actor.get("status") != "current":
            failures.append(f"active binding {binding_id} references non-current actor {actor_id}")
        surface_refs = agent.get("surface_refs")
        if not isinstance(surface_refs, list) or not surface_refs:
            failures.append(f"agents.{binding_id}.surface_refs must be a non-empty list")
        else:
            for surface_ref in surface_refs:
                if not isinstance(surface_ref, str) or not surface_ref.startswith(SURFACE_PREFIX):
                    failures.append(
                        f"agents.{binding_id} has invalid surface reference {surface_ref}"
                    )
                    continue
                surface_id = surface_ref[len(SURFACE_PREFIX) :]
                surface = surfaces.get(surface_id)
                if surface is None:
                    failures.append(
                        f"agents.{binding_id} references unresolved surface {surface_id}"
                    )
                elif agent.get("binding_status") == "active" and surface.get("status") != "current":
                    failures.append(
                        f"active binding {binding_id} references non-current surface {surface_id}"
                    )
        role = agent.get("role")
        if role not in roles:
            failures.append(f"agents.{binding_id} references unknown local role {role}")
        principal = agent.get("principal_id")
        if not isinstance(principal, str) or not principal:
            failures.append(f"agents.{binding_id}.principal_id must be non-empty")
        elif principal in seen_principals:
            failures.append(f"duplicate principal_id: {principal}")
        else:
            seen_principals.add(principal)
        user_id = agent.get("user_id")
        if not isinstance(user_id, str) or not user_id:
            failures.append(f"agents.{binding_id}.user_id must be non-empty")
        elif user_id in seen_users:
            failures.append(f"duplicate user_id: {user_id}")
        else:
            seen_users.add(user_id)


def _index(
    raw: Any,
    kind: str,
    failures: list[str],
) -> dict[str, Mapping[str, Any]]:
    if not isinstance(raw, list):
        failures.append(f"projection {kind} collection must be a list")
        return {}
    result: dict[str, Mapping[str, Any]] = {}
    for item in raw:
        mapped = _mapping(item)
        item_id = mapped.get("id")
        if not isinstance(item_id, str) or not item_id:
            failures.append(f"projected {kind} has no id")
            continue
        if item_id in result:
            failures.append(f"duplicate projected {kind}: {item_id}")
            continue
        result[item_id] = mapped
    return result


def _load_yaml(
    path: Path,
    failures: list[str],
) -> Mapping[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        failures.append(f"unable to load {path}: {exc}")
        return {}
    if not isinstance(value, Mapping):
        failures.append(f"{path} must contain a mapping")
        return {}
    return value


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _git_sha(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 40:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _sha256_value(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    if len(digest) != 64:
        return False
    try:
        int(digest, 16)
    except ValueError:
        return False
    return True


def _report(failures: list[str]) -> int:
    for failure in failures:
        print(
            f"FAIL canonical-identity-projection: {failure}",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
