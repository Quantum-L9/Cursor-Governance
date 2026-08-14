#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

DORMANT_STATUSES = {"dormant", "non_routable"}
ROOT_AUTONOMY_PROVIDER_ID = "root-autonomy-control-plane"
BOOTSTRAP_GLOBS = (
    "session_bootstrap.md",
    "agents-block.md",
    "gemini-block.md",
    "bootstrap.template.md",
)
PREEXISTING_SURFACES = {"cursor", "claude-code"}


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML document must be an object: {path}")
    return value


class ExecutablePeerModel:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.agents_root = repo_root / "environment/agents"
        self.pe_root = repo_root / "environment/program-execution"
        self.bindings_path = self.agents_root / "PEER_RUNTIME_BINDINGS.yaml"
        self.bindings_doc = _load_yaml(self.bindings_path)
        self.peers = self.bindings_doc.get("peers") or {}
        registry = _load_yaml(self.agents_root / "agent_registry.yaml")
        self.agents = registry.get("agents") or {}
        bindings_schema = json.loads(
            (self.agents_root / "schemas/peer-runtime-bindings.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.bindings_validator = Draft202012Validator(bindings_schema)
        exec_registry = _load_yaml(self.pe_root / "registry/EXECUTION_ADAPTER_REGISTRY.yaml")
        self.exec_entries = list(exec_registry.get("adapters") or [])
        spec_schema = json.loads(
            (self.pe_root / "conformance/schemas/execution-adapter-spec.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.spec_validator = Draft202012Validator(spec_schema)
        self.profile_registry = _load_yaml(
            self.pe_root / "registry/EXECUTION_PROFILE_REGISTRY.yaml"
        )
        profile_schema = json.loads(
            (self.pe_root / "conformance/schemas/execution-profile.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.profile_validator = Draft202012Validator(profile_schema)
        self._descriptors: dict[str, dict[str, Any]] = {}

    def entries_for(self, provider_ref: str) -> list[dict[str, Any]]:
        return [item for item in self.exec_entries if item.get("adapter_id") == provider_ref]

    def descriptor(self, entry: dict[str, Any]) -> dict[str, Any]:
        provider_ref = str(entry["adapter_id"])
        if provider_ref not in self._descriptors:
            self._descriptors[provider_ref] = _load_yaml(self.pe_root / str(entry["descriptor"]))
        return self._descriptors[provider_ref]

    def required_peers(self) -> dict[str, Any]:
        return {
            key: peer
            for key, peer in self.peers.items()
            if isinstance(peer, dict) and (peer.get("execution") or {}).get("required") is True
        }


def _check_schema(model: ExecutablePeerModel, errors: list[str]) -> None:
    for err in sorted(model.bindings_validator.iter_errors(model.bindings_doc), key=str):
        errors.append(f"[E2] bindings schema: {err.message}")
    for err in sorted(
        model.profile_validator.iter_errors(model.profile_registry),
        key=str,
    ):
        errors.append(f"[E2] profile registry schema: {err.message}")


def _check_registry_coverage(model: ExecutablePeerModel, errors: list[str]) -> None:
    for key, agent in model.agents.items():
        if not isinstance(agent, dict) or agent.get("status", "active") != "active":
            continue
        if key not in model.peers:
            errors.append(f"[E3] active registry agent '{key}' omitted from bindings")


def _check_peer_identity(model: ExecutablePeerModel, errors: list[str]) -> None:
    for key, peer in model.peers.items():
        if not isinstance(peer, dict):
            continue
        agent_ref = peer.get("agent_ref")
        if agent_ref not in model.agents:
            errors.append(f"[E4] {key}: unknown agent_ref '{agent_ref}'")
        if agent_ref != key:
            errors.append(f"[E5] {key}: agent_ref '{agent_ref}' != peer key")
        execution = peer.get("execution") or {}
        required = execution.get("required")
        if not isinstance(required, bool):
            errors.append(f"[E6] {key}: execution.required must be boolean")
        if required is True and not execution.get("bindings"):
            errors.append(f"[E6] {key}: required execution needs at least one binding")


def _check_bindings(model: ExecutablePeerModel, errors: list[str]) -> None:
    profiles = model.profile_registry.get("profiles") or {}
    for key, peer in model.peers.items():
        if not isinstance(peer, dict):
            continue
        required = (peer.get("execution") or {}).get("required") is True
        agent = model.agents.get(peer.get("agent_ref")) or {}
        seen: set[tuple[str, str, str]] = set()
        for binding in (peer.get("execution") or {}).get("bindings") or []:
            surface = str(binding.get("surface"))
            provider_ref = str(binding.get("provider_ref"))
            profile_ref = str(binding.get("execution_profile_ref"))
            identity = (surface, provider_ref, profile_ref)
            if identity in seen:
                errors.append(f"[E15] {key}: duplicate binding {identity}")
            seen.add(identity)
            if surface not in (agent.get("surfaces") or []):
                errors.append(f"[E7] {key}: unknown surface '{surface}'")
            entries = model.entries_for(provider_ref)
            if len(entries) != 1:
                errors.append(f"[E8] {key}: provider_ref '{provider_ref}' not unique")
                continue
            entry = entries[0]
            if entry.get("adapter_kind") not in {"worker_host", "verifier"}:
                errors.append(f"[E9] {key}: provider '{provider_ref}' is not a peer execution kind")
            descriptor = model.descriptor(entry)
            if list(model.spec_validator.iter_errors(descriptor)):
                errors.append(f"[E10] {key}: descriptor '{provider_ref}' fails schema")
            provider_identity = descriptor.get("identity") or {}
            if provider_identity.get("binding") != "peer_runtime_binding":
                errors.append(f"[E10] {key}: '{provider_ref}' is not peer_runtime_binding")
            if "agent_ref" in provider_identity:
                errors.append(f"[E11] {key}: provider '{provider_ref}' embeds agent_ref")
            if profile_ref not in profiles:
                errors.append(f"[E11] {key}: unknown execution profile '{profile_ref}'")
            if required and entry.get("status") in DORMANT_STATUSES:
                errors.append(f"[E12] {key}: provider '{provider_ref}' is not routable")


def _check_autonomy(model: ExecutablePeerModel, errors: list[str]) -> None:
    provider_path = model.pe_root / "integrations/autonomy-control-plane/PROVIDER.yaml"
    compat_path = model.pe_root / "COMPATIBILITY.yaml"
    provider = _load_yaml(provider_path) if provider_path.is_file() else {}
    compat = _load_yaml(compat_path) if compat_path.is_file() else {}
    compat_path_value = ((compat.get("providers") or {}).get("root_autonomy") or {}).get("path")
    for key, peer in model.peers.items():
        autonomy = peer.get("autonomy") if isinstance(peer, dict) else None
        if not isinstance(autonomy, dict) or autonomy.get("required") is not True:
            continue
        if autonomy.get("provider_id") != provider.get("provider_id"):
            errors.append(f"[E13] {key}: autonomy provider mismatch")
    if any(
        isinstance(peer, dict)
        and isinstance(peer.get("autonomy"), dict)
        and peer["autonomy"].get("required") is True
        for peer in model.peers.values()
    ):
        if provider.get("provider_id") != ROOT_AUTONOMY_PROVIDER_ID:
            errors.append("[E13] canonical root autonomy provider missing")
        if provider.get("owns_program_state") is not False:
            errors.append("[E13] autonomy must not own Program state")
        canonical = provider.get("canonical_path")
        if not canonical or not (model.repo_root / str(canonical)).is_dir():
            errors.append("[E13] canonical autonomy path does not resolve")
        if compat_path_value and canonical != compat_path_value:
            errors.append("[E13] autonomy provider path disagrees with compatibility")


def _check_carriers(model: ExecutablePeerModel, errors: list[str]) -> None:
    for root in (model.agents_root / "adapters", model.pe_root / "adapters"):
        if not root.is_dir():
            continue
        for autonomy in root.glob("*/autonomy"):
            if autonomy.is_dir():
                errors.append(
                    f"[E14] adapter-owned autonomy runtime forbidden: "
                    f"{autonomy.relative_to(model.repo_root)}"
                )
    for key, peer in model.required_peers().items():
        agent = model.agents.get(peer.get("agent_ref")) or {}
        adapter = str(agent.get("adapter", key))
        if adapter in PREEXISTING_SURFACES:
            continue
        root = model.agents_root / "adapters" / adapter
        if not any((root / name).is_file() for name in BOOTSTRAP_GLOBS):
            errors.append(f"[E14] {key}: missing bootstrap carrier")
    for key, agent in model.agents.items():
        if isinstance(agent, dict) and "execution" in agent:
            errors.append(f"[E15] {key}: agent_registry must not own execution topology")


def validate_bindings_schema(repo_root: Path) -> dict[str, Any]:
    try:
        model = ExecutablePeerModel(repo_root)
    except (OSError, ValueError, FileNotFoundError) as exc:
        return {"status": "FAIL", "errors": [f"[E1] {exc}"]}
    errors: list[str] = []
    _check_schema(model, errors)
    return {
        "schema": "l9.peer-runtime-bindings-report.v2",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "peer_count": len(model.peers),
    }


def validate(repo_root: Path) -> dict[str, Any]:
    try:
        model = ExecutablePeerModel(repo_root)
    except (OSError, ValueError, FileNotFoundError) as exc:
        return {
            "schema": "l9.executable-peer-conformance-report.v2",
            "status": "FAIL",
            "errors": [f"[E1] {exc}"],
            "executable_peers": [],
        }
    errors: list[str] = []
    _check_schema(model, errors)
    _check_registry_coverage(model, errors)
    _check_peer_identity(model, errors)
    _check_bindings(model, errors)
    _check_autonomy(model, errors)
    _check_carriers(model, errors)
    return {
        "schema": "l9.executable-peer-conformance-report.v2",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "executable_peers": sorted(model.required_peers()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--schema-only", action="store_true")
    args = parser.parse_args(argv)
    root = args.repo_root.resolve()
    if not root.is_dir():
        sys.stderr.write(f"error: repo root not found: {root}\n")
        return 2
    report = validate_bindings_schema(root) if args.schema_only else validate(root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["status"] == "PASS":
        sys.stderr.write("PASS — executable-peer topology coherent\n")
    else:
        sys.stderr.write(f"FAIL — {len(report['errors'])} violation(s):\n")
        for item in report["errors"]:
            sys.stderr.write(f"  {item}\n")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
