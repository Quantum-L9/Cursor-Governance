#!/usr/bin/env python3
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/tools/validate_executable_peers.py
#   layer: tool
#   owner: governance-control-plane
#   status: active
#   version: 1.0.0
#   updated: 2026-08-10
"""Executable Peer Contract cross-registry validator (rules E1-E15).

Proves the executable-peer topology is structurally coherent across the
identity plane (agent_registry.yaml), the execution plane
(environment/program-execution), and the canonical autonomy provider. This is
the structural gate; live availability is proven separately by
probe_executable_peers.py. This validator NEVER mutates the repository.

    E1  execution.enabled must be boolean
    E2  active + execution.enabled requires >=1 binding
    E3  binding.surface must exist in agents.<id>.surfaces
    E4  binding.adapter_id must exist exactly once in the execution registry
    E5  bound adapter must have adapter_kind == worker_host
    E6  bound descriptor must validate against execution-adapter-spec.schema.json
    E7  descriptor.identity.binding must equal agent_registry
    E8  descriptor.identity.agent_ref must equal the registry agent_id
    E9  bound adapter may not be dormant or non_routable
    E10 root autonomy provider must resolve from COMPATIBILITY.yaml
    E11 root autonomy PROVIDER.yaml must exist and declare owns_program_state: false
    E12 canonical autonomy path must resolve inside the governance root
    E13 no agent/program adapter may contain a copied autonomy implementation
    E14 an executable peer must have a supported readiness/bootstrap carrier
    E15 no readiness state may be statically asserted by agent_registry.yaml

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
ALLOWED_EXECUTION_KEYS = {"enabled", "bindings"}


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
        registry = _load_yaml(self.agents_root / "agent_registry.yaml")
        self.agents: dict[str, Any] = registry.get("agents") or {}
        exec_registry = _load_yaml(self.pe_root / "registry/EXECUTION_ADAPTER_REGISTRY.yaml")
        self.exec_entries: list[dict[str, Any]] = list(exec_registry.get("adapters") or [])
        schema_path = self.pe_root / "conformance/schemas/execution-adapter-spec.schema.json"
        self.spec_validator = Draft202012Validator(
            json.loads(schema_path.read_text(encoding="utf-8"))
        )
        self._descriptors: dict[str, dict[str, Any]] = {}

    def entries_for(self, adapter_id: str) -> list[dict[str, Any]]:
        return [e for e in self.exec_entries if e.get("adapter_id") == adapter_id]

    def descriptor(self, entry: dict[str, Any]) -> dict[str, Any]:
        adapter_id = str(entry.get("adapter_id"))
        if adapter_id not in self._descriptors:
            self._descriptors[adapter_id] = _load_yaml(self.pe_root / str(entry["descriptor"]))
        return self._descriptors[adapter_id]

    def enabled_agents(self) -> dict[str, Any]:
        result = {}
        for key, agent in self.agents.items():
            if isinstance(agent, dict) and (agent.get("execution") or {}).get("enabled") is True:
                result[key] = agent
        return result


def _check_execution_shape(model: ExecutablePeerModel, errors: list[str]) -> None:
    """E1, E2, E15."""
    for key, agent in model.agents.items():
        if not isinstance(agent, dict):
            continue
        execution = agent.get("execution")
        if execution is None:
            continue
        enabled = execution.get("enabled")
        if not isinstance(enabled, bool):
            errors.append(f"[E1] {key}: execution.enabled must be boolean")
        extra = set(execution) - ALLOWED_EXECUTION_KEYS
        if extra:
            errors.append(f"[E15] {key}: execution declares non-contract keys {sorted(extra)}")
        bindings = execution.get("bindings") or []
        if agent.get("status", "active") == "active" and enabled is True and not bindings:
            errors.append(f"[E2] {key}: active + enabled requires >=1 binding")


def _iter_bindings(model: ExecutablePeerModel):
    for key, agent in model.enabled_agents().items():
        for binding in (agent.get("execution") or {}).get("bindings") or []:
            yield key, agent, binding


def _check_bindings(model: ExecutablePeerModel, errors: list[str]) -> None:
    """E3-E9 for every binding of an enabled agent."""
    for key, agent, binding in _iter_bindings(model):
        surface = binding.get("surface")
        adapter_id = str(binding.get("adapter_id"))
        if surface not in (agent.get("surfaces") or []):
            errors.append(f"[E3] {key}: binding surface '{surface}' not in agent surfaces")
        entries = model.entries_for(adapter_id)
        if len(entries) != 1:
            errors.append(f"[E4] {key}: adapter '{adapter_id}' not unique in execution registry")
            continue
        entry = entries[0]
        descriptor = model.descriptor(entry)
        if entry.get("adapter_kind") != "worker_host":
            errors.append(f"[E5] {key}: bound adapter '{adapter_id}' is not worker_host")
        if list(model.spec_validator.iter_errors(descriptor)):
            errors.append(f"[E6] {key}: descriptor '{adapter_id}' fails spec schema")
        identity = descriptor.get("identity") or {}
        if identity.get("binding") != "agent_registry":
            errors.append(f"[E7] {key}: '{adapter_id}' identity.binding is not agent_registry")
        if identity.get("agent_ref") != key:
            errors.append(
                f"[E8] {key}: descriptor '{adapter_id}' agent_ref "
                f"'{identity.get('agent_ref')}' != '{key}'"
            )
        if entry.get("status") in DORMANT_STATUSES:
            errors.append(f"[E9] {key}: bound adapter '{adapter_id}' is {entry.get('status')}")


def _check_autonomy(model: ExecutablePeerModel, errors: list[str]) -> None:
    """E10, E11, E12."""
    compat_path = model.pe_root / "COMPATIBILITY.yaml"
    provider_path = model.pe_root / "integrations/autonomy-control-plane/PROVIDER.yaml"
    compat = _load_yaml(compat_path) if compat_path.is_file() else {}
    compat_autonomy = (compat.get("providers") or {}).get("root_autonomy") or {}
    compat_path_value = compat_autonomy.get("path")
    if not compat_path_value:
        errors.append("[E10] COMPATIBILITY.yaml providers.root_autonomy.path is missing")
    if not provider_path.is_file():
        errors.append("[E11] autonomy-control-plane/PROVIDER.yaml is missing")
        return
    provider = _load_yaml(provider_path)
    if provider.get("owns_program_state") is not False:
        errors.append("[E11] root autonomy PROVIDER.yaml must declare owns_program_state: false")
    canonical = provider.get("canonical_path")
    if not canonical or not (model.repo_root / str(canonical)).is_dir():
        errors.append("[E12] canonical autonomy path does not resolve inside governance root")
    elif compat_path_value and canonical != compat_path_value:
        errors.append("[E10] PROVIDER canonical_path disagrees with COMPATIBILITY.yaml")


def _adapter_dirs(model: ExecutablePeerModel) -> list[Path]:
    dirs: list[Path] = []
    for root in (model.agents_root / "adapters", model.pe_root / "adapters"):
        if root.is_dir():
            dirs.extend(child for child in root.iterdir() if child.is_dir())
    return dirs


def _check_no_copied_autonomy(model: ExecutablePeerModel, errors: list[str]) -> None:
    """E13."""
    for adir in _adapter_dirs(model):
        for offender in adir.rglob("autonomy"):
            if offender.is_dir():
                rel = offender.relative_to(model.repo_root)
                errors.append(f"[E13] adapter copies autonomy/: {rel}")


def _check_bootstrap_carrier(model: ExecutablePeerModel, errors: list[str]) -> None:
    """E14 — every executable peer resolves a readiness/bootstrap carrier."""
    for key, agent in model.enabled_agents().items():
        adapter = str(agent.get("adapter", key))
        if adapter in PREEXISTING_SURFACES:
            # cursor (.cursor activation) / claude-code (environment/claude-code
            # SessionStart) ship their own session-start bootstrap.
            continue
        adir = model.agents_root / "adapters" / adapter
        if not any((adir / name).is_file() for name in BOOTSTRAP_GLOBS):
            errors.append(f"[E14] {key}: no bootstrap carrier in adapters/{adapter}/")


RULES = (
    _check_execution_shape,
    _check_bindings,
    _check_autonomy,
    _check_no_copied_autonomy,
    _check_bootstrap_carrier,
)


def validate(repo_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        model = ExecutablePeerModel(repo_root)
    except (OSError, ValueError) as exc:
        return {
            "schema": "l9.executable-peer-conformance-report.v1",
            "status": "FAIL",
            "errors": [f"[load] {exc}"],
            "executable_peers": [],
        }
    for rule in RULES:
        rule(model, errors)
    return {
        "schema": "l9.executable-peer-conformance-report.v1",
        "status": "PASS" if not errors else "FAIL",
        "executable_peers": sorted(model.enabled_agents()),
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[3]
    parser.add_argument("--repo-root", type=Path, default=default_root)
    parser.add_argument("--json", action="store_true", help="emit the full JSON report")
    args = parser.parse_args(argv)
    root = args.repo_root.resolve()
    if not root.is_dir():
        sys.stderr.write(f"error: repo root not found: {root}\n")
        return 2
    report = validate(root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["status"] == "PASS":
        peers = ", ".join(report["executable_peers"]) or "(none enabled)"
        sys.stderr.write(f"PASS — executable-peer topology coherent; enabled peers: {peers}\n")
    else:
        sys.stderr.write(f"FAIL — {len(report['errors'])} violation(s):\n")
        for item in report["errors"]:
            sys.stderr.write(f"  {item}\n")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
