from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


def _require_string(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


@dataclass(frozen=True)
class PeerBinding:
    agent_ref: str
    surface: str
    provider_ref: str
    execution_profile_ref: str

    def __post_init__(self) -> None:
        for name in (
            "agent_ref",
            "surface",
            "provider_ref",
            "execution_profile_ref",
        ):
            _require_string(name, getattr(self, name))

    def to_dict(self) -> dict[str, str]:
        return {
            "agent_ref": self.agent_ref,
            "surface": self.surface,
            "provider_ref": self.provider_ref,
            "execution_profile_ref": self.execution_profile_ref,
        }


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML document must be an object: {path}")
    return value


def load_peer_bindings(repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root).expanduser().resolve()
    bindings_path = root / "environment/agents/PEER_RUNTIME_BINDINGS.yaml"
    schema_path = root / "environment/agents/schemas/peer-runtime-bindings.schema.json"
    value = _load_yaml(bindings_path)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise ValueError(f"peer runtime bindings schema must be an object: {schema_path}")
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda item: list(item.path),
    )
    if errors:
        rendered = [
            f"{'.'.join(str(part) for part in item.path) or '<root>'}: {item.message}"
            for item in errors
        ]
        raise ValueError(f"peer runtime bindings schema errors: {rendered}")
    return value


def resolve_peer_binding(
    repository_root: str | Path,
    agent_ref: str,
    surface: str,
    provider_ref: str | None = None,
) -> PeerBinding:
    agent_ref = _require_string("agent_ref", agent_ref)
    surface = _require_string("surface", surface)
    if provider_ref is not None:
        provider_ref = _require_string("provider_ref", provider_ref)
    doc = load_peer_bindings(repository_root)
    peer = (doc.get("peers") or {}).get(agent_ref)
    if not isinstance(peer, dict):
        raise ValueError(f"unknown peer agent_ref: {agent_ref}")
    declared_agent = peer.get("agent_ref")
    if declared_agent != agent_ref:
        raise ValueError(
            f"peer key and agent_ref differ: key={agent_ref} declared={declared_agent!r}"
        )
    candidates: list[dict[str, Any]] = []
    for binding in (peer.get("execution") or {}).get("bindings") or []:
        if binding.get("surface") != surface:
            continue
        if provider_ref is not None and binding.get("provider_ref") != provider_ref:
            continue
        candidates.append(dict(binding))
    if len(candidates) != 1:
        refs = sorted(str(item.get("provider_ref")) for item in candidates)
        raise ValueError(
            f"peer binding must resolve uniquely: agent_ref={agent_ref} "
            f"surface={surface} provider_ref={provider_ref!r} candidates={refs}"
        )
    binding = candidates[0]
    return PeerBinding(
        agent_ref=agent_ref,
        surface=surface,
        provider_ref=_require_string("provider_ref", binding.get("provider_ref")),
        execution_profile_ref=_require_string(
            "execution_profile_ref",
            binding.get("execution_profile_ref"),
        ),
    )
