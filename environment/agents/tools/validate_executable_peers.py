#!/usr/bin/env python3
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/tools/validate_executable_peers.py
#   layer: tool
#   owner: governance-control-plane
#   status: active
#   version: 2.0.0
#   updated: 2026-08-12
"""Executable Peer Contract cross-registry validator (rules E1-E15).

Topology SSOT is PEER_RUNTIME_BINDINGS.yaml (not agent_registry.execution).
Proves structural coherence across the identity plane (agent_registry.yaml),
the binding plane (PEER_RUNTIME_BINDINGS.yaml), the execution plane
(environment/program-execution), and the canonical autonomy provider.
Live availability is proven separately by probe_executable_peers.py.
This validator NEVER mutates the repository.

    E1  PEER_RUNTIME_BINDINGS.yaml must exist and parse
    E2  bindings document validates against peer-runtime-bindings.schema.json
    E3  every active agent_registry agent has a peer entry (no silent omission)
    E4  peer.agent_ref resolves in agent_registry (unknown agent_ref)
    E5  peer.agent_ref equals the peer map key
    E6  execution.required boolean; active + required implies >=1 binding
    E7  binding.surface exists in agent surfaces (unknown surface)
    E8  binding.adapter_id unique in EXECUTION_ADAPTER_REGISTRY (unknown adapter)
    E9  bound adapter adapter_kind == worker_host
    E10 bound descriptor validates; identity.binding == agent_registry
    E11 descriptor.identity.agent_ref equals peer.agent_ref
    E12 bound adapter not dormant / non_routable
    E13 autonomy.required: provider resolves; owns_program_state == false; path OK
    E14 no copied autonomy/; bootstrap carrier; roles_manifest when subagents.enabled
    E15 no duplicate (surface, adapter_id) bindings; agent_registry has no execution:

Exit 0 = pass, 1 = violations, 2 = environment error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
    from jsonschema import Draft202012Validator
except ModuleNotFoundError as exc:  # pragma: no cover
    sys.stderr.write(f"error: dependency required ({exc.name}); pip install pyyaml jsonschema\n")
    raise SystemExit(2) from None

PREEXISTING_SURFACES = {"cursor", "claude-code"}
DORMANT_STATUSES = {"dormant", "non_routable"}
BOOTSTRAP_GLOBS = (
    "session_bootstrap.md",
    "agents-block.md",
    "gemini-block.md",
    "bootstrap.template.md",
)
ROOT_AUTONOMY_PROVIDER_ID = "root-autonomy-control-plane"


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
        self.schema_path = self.agents_root / "schemas" / "peer-runtime-bindings.schema.json"
        if not self.bindings_path.is_file():
            raise FileNotFoundError(f"PEER_RUNTIME_BINDINGS.yaml missing at {self.bindings_path}")
        registry = _load_yaml(self.agents_root / "agent_registry.yaml")
        self.agents: dict[str, Any] = registry.get("agents") or {}
        self.bindings_doc = _load_yaml(self.bindings_path)
        self.peers: dict[str, Any] = self.bindings_doc.get("peers") or {}
        if not self.schema_path.is_file():
            raise FileNotFoundError(f"peer-runtime-bindings schema missing at {self.schema_path}")
        self.bindings_validator = Draft202012Validator(
            json.loads(self.schema_path.read_text(encoding="utf-8"))
        )
        exec_registry = _load_yaml(self.pe_root / "registry/EXECUTION_ADAPTER_REGISTRY.yaml")
        self.exec_entries: list[dict[str, Any]] = list(exec_registry.get("adapters") or [])
        spec_path = self.pe_root / "conformance/schemas/execution-adapter-spec.schema.json"
        self.spec_validator = Draft202012Validator(
            json.loads(spec_path.read_text(encoding="utf-8"))
        )
        self._descriptors: dict[str, dict[str, Any]] = {}

    def entries_for(self, adapter_id: str) -> list[dict[str, Any]]:
        return [e for e in self.exec_entries if e.get("adapter_id") == adapter_id]

    def descriptor(self, entry: dict[str, Any]) -> dict[str, Any]:
        adapter_id = str(entry.get("adapter_id"))
        if adapter_id not in self._descriptors:
            self._descriptors[adapter_id] = _load_yaml(self.pe_root / str(entry["descriptor"]))
        return self._descriptors[adapter_id]

    def required_peers(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, peer in self.peers.items():
            if isinstance(peer, dict) and (peer.get("execution") or {}).get("required") is True:
                result[key] = peer
        return result


def validate_bindings_schema(repo_root: Path) -> dict[str, Any]:
    """Schema-only gate for `make agents-runtime-bindings-validate`."""
    errors: list[str] = []
    try:
        model = ExecutablePeerModel(repo_root)
    except (OSError, ValueError, FileNotFoundError) as exc:
        return {
            "schema": "l9.peer-runtime-bindings-report.v1",
            "status": "FAIL",
            "errors": [f"[E1] {exc}"],
        }
    _check_bindings_schema(model, errors)
    return {
        "schema": "l9.peer-runtime-bindings-report.v1",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "peer_count": len(model.peers),
    }


def _check_bindings_present(model: ExecutablePeerModel, errors: list[str]) -> None:
    """E1 — document loaded (constructor already required the file)."""
    if not isinstance(model.peers, dict) or not model.peers:
        errors.append("[E1] PEER_RUNTIME_BINDINGS.peers must be a non-empty object")


def _check_bindings_schema(model: ExecutablePeerModel, errors: list[str]) -> None:
    """E2."""
    for err in sorted(model.bindings_validator.iter_errors(model.bindings_doc), key=str):
        path = ".".join(str(p) for p in err.path) or "<root>"
        errors.append(f"[E2] schema: {path}: {err.message}")


def _check_registry_coverage(model: ExecutablePeerModel, errors: list[str]) -> None:
    """E3 — every active registry agent appears in bindings."""
    for key, agent in model.agents.items():
        if not isinstance(agent, dict):
            continue
        if agent.get("status", "active") != "active":
            continue
        if key not in model.peers:
            errors.append(f"[E3] active registry agent '{key}' omitted from PEER_RUNTIME_BINDINGS")


def _check_agent_refs(model: ExecutablePeerModel, errors: list[str]) -> None:
    """E4, E5."""
    for key, peer in model.peers.items():
        if not isinstance(peer, dict):
            continue
        agent_ref = peer.get("agent_ref")
        if agent_ref not in model.agents:
            errors.append(f"[E4] {key}: unknown agent_ref '{agent_ref}'")
        if agent_ref != key:
            errors.append(f"[E5] {key}: agent_ref '{agent_ref}' does not match peer key")


def _check_execution_shape(model: ExecutablePeerModel, errors: list[str]) -> None:
    """E6."""
    for key, peer in model.peers.items():
        if not isinstance(peer, dict):
            continue
        execution = peer.get("execution") or {}
        required = execution.get("required")
        if not isinstance(required, bool):
            errors.append(f"[E6] {key}: execution.required must be boolean")
        bindings = execution.get("bindings") or []
        agent = model.agents.get(peer.get("agent_ref"), {})
        if (
            isinstance(agent, dict)
            and agent.get("status", "active") == "active"
            and required is True
            and not bindings
        ):
            errors.append(f"[E6] {key}: active + execution.required requires >=1 binding")


def _iter_required_bindings(model: ExecutablePeerModel):
    for key, peer in model.required_peers().items():
        for binding in (peer.get("execution") or {}).get("bindings") or []:
            yield key, peer, binding


def _check_bindings(model: ExecutablePeerModel, errors: list[str]) -> None:
    """E7-E12 for every binding of an execution.required peer."""
    for key, peer, binding in _iter_required_bindings(model):
        agent_ref = peer.get("agent_ref")
        agent = model.agents.get(agent_ref) or {}
        surface = binding.get("surface")
        adapter_id = str(binding.get("adapter_id"))
        if surface not in (agent.get("surfaces") or []):
            errors.append(
                f"[E7] {key}: unknown surface '{surface}' "
                f"(not in agent_registry surfaces for '{agent_ref}')"
            )
        entries = model.entries_for(adapter_id)
        if len(entries) != 1:
            errors.append(
                f"[E8] {key}: unknown adapter '{adapter_id}' "
                "(not unique in EXECUTION_ADAPTER_REGISTRY)"
            )
            continue
        entry = entries[0]
        descriptor = model.descriptor(entry)
        if entry.get("adapter_kind") != "worker_host":
            errors.append(f"[E9] {key}: adapter '{adapter_id}' is not worker_host")
        if list(model.spec_validator.iter_errors(descriptor)):
            errors.append(f"[E10] {key}: descriptor '{adapter_id}' fails spec schema")
        identity = descriptor.get("identity") or {}
        if identity.get("binding") != "agent_registry":
            errors.append(f"[E10] {key}: '{adapter_id}' identity.binding is not agent_registry")
        if identity.get("agent_ref") != agent_ref:
            errors.append(
                f"[E11] {key}: descriptor '{adapter_id}' agent_ref "
                f"'{identity.get('agent_ref')}' != '{agent_ref}'"
            )
        if entry.get("status") in DORMANT_STATUSES:
            errors.append(f"[E12] {key}: bound adapter '{adapter_id}' is {entry.get('status')}")


def _check_autonomy(model: ExecutablePeerModel, errors: list[str]) -> None:
    """E13 — per-peer autonomy.required plus root provider invariants."""
    provider_path = model.pe_root / "integrations/autonomy-control-plane/PROVIDER.yaml"
    compat_path = model.pe_root / "COMPATIBILITY.yaml"
    provider: dict[str, Any] | None = None
    if provider_path.is_file():
        provider = _load_yaml(provider_path)
    compat = _load_yaml(compat_path) if compat_path.is_file() else {}
    compat_autonomy = (compat.get("providers") or {}).get("root_autonomy") or {}
    compat_path_value = compat_autonomy.get("path")

    any_autonomy_required = False
    for key, peer in model.peers.items():
        if not isinstance(peer, dict):
            continue
        autonomy = peer.get("autonomy")
        if not isinstance(autonomy, dict):
            continue
        if autonomy.get("required") is not True:
            continue
        any_autonomy_required = True
        provider_id = autonomy.get("provider_id")
        if not provider_id:
            errors.append(f"[E13] {key}: missing autonomy provider_id")
            continue
        if provider is None:
            errors.append(f"[E13] {key}: missing autonomy provider (PROVIDER.yaml absent)")
            continue
        if provider.get("provider_id") != provider_id:
            errors.append(
                f"[E13] {key}: autonomy provider_id '{provider_id}' "
                f"does not match PROVIDER.yaml '{provider.get('provider_id')}'"
            )
        if provider.get("owns_program_state") is not False:
            errors.append(
                f"[E13] {key}: autonomy owns_program_state != false "
                f"(got {provider.get('owns_program_state')!r})"
            )

    if any_autonomy_required:
        if provider is None:
            errors.append("[E13] root autonomy PROVIDER.yaml is missing")
            return
        if provider.get("owns_program_state") is not False:
            errors.append(
                "[E13] root autonomy PROVIDER.yaml must declare owns_program_state: false"
            )
        canonical = provider.get("canonical_path")
        if not canonical or not (model.repo_root / str(canonical)).is_dir():
            errors.append("[E13] canonical autonomy path does not resolve inside governance root")
        elif compat_path_value and canonical != compat_path_value:
            errors.append("[E13] PROVIDER canonical_path disagrees with COMPATIBILITY.yaml")
        if not compat_path_value:
            errors.append("[E13] COMPATIBILITY.yaml providers.root_autonomy.path is missing")
        if provider.get("provider_id") != ROOT_AUTONOMY_PROVIDER_ID:
            errors.append(
                f"[E13] expected root provider_id {ROOT_AUTONOMY_PROVIDER_ID!r}, "
                f"got {provider.get('provider_id')!r}"
            )


def _adapter_dirs(model: ExecutablePeerModel) -> list[Path]:
    dirs: list[Path] = []
    for root in (model.agents_root / "adapters", model.pe_root / "adapters"):
        if root.is_dir():
            dirs.extend(child for child in root.iterdir() if child.is_dir())
    return dirs


def _check_no_copied_autonomy_and_carriers(model: ExecutablePeerModel, errors: list[str]) -> None:
    """E14."""
    # Owned Claude scheduler is not a forbidden copy of root autonomy/.
    _E14_AUTONOMY_ALLOW = {
        Path("environment/agents/adapters/claude-code/autonomy"),
        Path("environment/claude-code/autonomy"),  # transitional symlink target pre/post move
    }
    for adir in _adapter_dirs(model):
        for offender in adir.rglob("autonomy"):
            if offender.is_dir():
                rel = offender.relative_to(model.repo_root)
                if rel in _E14_AUTONOMY_ALLOW or rel.as_posix().endswith(
                    "adapters/claude-code/autonomy"
                ):
                    continue
                errors.append(f"[E14] adapter copies autonomy/: {rel}")

    for key, peer in model.required_peers().items():
        agent = model.agents.get(peer.get("agent_ref")) or {}
        adapter = str(agent.get("adapter", key))
        if adapter in PREEXISTING_SURFACES:
            continue
        adir = model.agents_root / "adapters" / adapter
        if not any((adir / name).is_file() for name in BOOTSTRAP_GLOBS):
            errors.append(f"[E14] {key}: no bootstrap carrier in adapters/{adapter}/")

    for key, peer in model.peers.items():
        if not isinstance(peer, dict):
            continue
        subagents = peer.get("subagents") or {}
        if subagents.get("enabled") is not True:
            continue
        manifest = subagents.get("roles_manifest")
        if not manifest:
            errors.append(f"[E14] {key}: missing roles manifest (subagents.enabled)")
            continue
        manifest_path = model.repo_root / str(manifest)
        if not manifest_path.is_file():
            errors.append(f"[E14] {key}: missing roles manifest at {manifest}")


def _check_duplicates_and_identity_plane(model: ExecutablePeerModel, errors: list[str]) -> None:
    """E15 — duplicate bindings; agent_registry must not carry execution:."""
    for key, peer in model.peers.items():
        if not isinstance(peer, dict):
            continue
        seen: set[tuple[str, str]] = set()
        for binding in (peer.get("execution") or {}).get("bindings") or []:
            pair = (str(binding.get("surface")), str(binding.get("adapter_id")))
            if pair in seen:
                errors.append(
                    f"[E15] {key}: duplicate peer binding "
                    f"surface={pair[0]!r} adapter_id={pair[1]!r}"
                )
            seen.add(pair)

    for key, agent in model.agents.items():
        if isinstance(agent, dict) and "execution" in agent:
            errors.append(
                f"[E15] {key}: agent_registry must not declare execution: "
                "(topology SSOT is PEER_RUNTIME_BINDINGS.yaml)"
            )


RULES = (
    _check_bindings_present,
    _check_bindings_schema,
    _check_registry_coverage,
    _check_agent_refs,
    _check_execution_shape,
    _check_bindings,
    _check_autonomy,
    _check_no_copied_autonomy_and_carriers,
    _check_duplicates_and_identity_plane,
)


def validate(repo_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        model = ExecutablePeerModel(repo_root)
    except (OSError, ValueError, FileNotFoundError) as exc:
        return {
            "schema": "l9.executable-peer-conformance-report.v1",
            "status": "FAIL",
            "errors": [f"[E1] {exc}"],
            "executable_peers": [],
        }
    for rule in RULES:
        rule(model, errors)
    return {
        "schema": "l9.executable-peer-conformance-report.v1",
        "status": "PASS" if not errors else "FAIL",
        "executable_peers": sorted(model.required_peers()),
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[3]
    parser.add_argument("--repo-root", type=Path, default=default_root)
    parser.add_argument("--json", action="store_true", help="emit the full JSON report")
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="validate PEER_RUNTIME_BINDINGS schema only (agents-runtime-bindings-validate)",
    )
    args = parser.parse_args(argv)
    root = args.repo_root.resolve()
    if not root.is_dir():
        sys.stderr.write(f"error: repo root not found: {root}\n")
        return 2
    report = validate_bindings_schema(root) if args.schema_only else validate(root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["status"] == "PASS":
        if args.schema_only:
            sys.stderr.write(
                f"PASS — peer-runtime-bindings schema valid; "
                f"{report.get('peer_count', 0)} peer(s)\n"
            )
        else:
            peers = ", ".join(report["executable_peers"]) or "(none required)"
            sys.stderr.write(
                f"PASS — executable-peer topology coherent; execution.required peers: {peers}\n"
            )
    else:
        sys.stderr.write(f"FAIL — {len(report['errors'])} violation(s):\n")
        for item in report["errors"]:
            sys.stderr.write(f"  {item}\n")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
