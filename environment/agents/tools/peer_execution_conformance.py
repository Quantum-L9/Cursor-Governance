#!/usr/bin/env python3
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/tools/peer_execution_conformance.py
#   layer: tool
#   owner: governance-control-plane
#   status: active
#   version: 1.0.0
#   updated: 2026-08-10
"""Universal peer-execution conformance validator.

Cross-validates the identity plane and the execution plane so that the peer
topology is provably coherent (Universal Agent Peer Execution Plan, section 16):

    agent_registry.yaml            (who + which program adapters)
        <->  environment/agents/adapters/*        (surface adapters + bindings)
        <->  environment/program-execution/registry (execution adapters)
        <->  autonomy/                              (canonical autonomy provider)

It enforces ten rules. Every rule is fail-closed: a violation lists the exact
offending peer/adapter. This validator NEVER mutates the repository.

    R1  every executable agent has an environment (surface) adapter
    R2  every program-enabled agent maps to registered program adapter(s)
    R3  every adapter-binding file references a registered agent (unless a
        template) and agrees with agent_registry
    R4  no adapter copies root autonomy/
    R5  no adapter copies the Program Execution core / a second agent registry
    R6  adapter authority never exceeds the agent's declared role
    R7  every program adapter emits canonical lifecycle receipts
    R8  every program adapter declares a cancellation posture honestly
    R9  every program adapter reports health (registry status + health entry)
    R10 every executable peer's program adapter ships conformance tests

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
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("error: pyyaml required (pip install pyyaml)\n")
    raise SystemExit(2) from None

CANONICAL_LIFECYCLE = "program-execution-adapter.lifecycle-receipt.v1"
CANCELLATION_ENUM = {"supported", "unsupported", "conditional"}
REGISTRY_STATUS_ENUM = {"active", "conditional", "dormant", "non_routable"}
PREEXISTING_SURFACES = {"cursor", "claude-code"}

# Role -> the program adapter kinds that role is permitted to be routed to.
# Adapter authority may narrow the role, never widen it (section 14).
ROLE_ADAPTER_KINDS: dict[str, set[str]] = {
    "orchestrator": {"worker_host", "verifier"},
    "implementer": {"worker_host"},
    "researcher-builder": {"worker_host"},
    "reviewer": {"verifier"},
    "observer": set(),
}


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML document must be an object: {path}")
    return value


class PeerExecutionModel:
    """Resolved view over both planes, loaded once and shared by every rule."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.agents_root = repo_root / "environment/agents"
        self.pe_root = repo_root / "environment/program-execution"
        self.autonomy_root = repo_root / "autonomy"

        registry = _load_yaml(self.agents_root / "agent_registry.yaml")
        self.roles: dict[str, Any] = registry.get("roles") or {}
        self.agents: dict[str, Any] = registry.get("agents") or {}

        exec_registry = _load_yaml(self.pe_root / "registry/EXECUTION_ADAPTER_REGISTRY.yaml")
        self.exec_entries: list[dict[str, Any]] = list(exec_registry.get("adapters") or [])
        self.exec_by_id: dict[str, dict[str, Any]] = {
            str(item.get("adapter_id")): item for item in self.exec_entries
        }
        self._descriptors: dict[str, dict[str, Any]] = {}
        self.health_ids = self._load_health_ids()

    def _load_health_ids(self) -> set[str]:
        path = self.pe_root / "registry/EXECUTION_ADAPTER_HEALTH.yaml"
        if not path.is_file():
            return set()
        health = _load_yaml(path)
        return {str(item.get("adapter_id")) for item in health.get("entries") or []}

    def descriptor(self, adapter_id: str) -> dict[str, Any] | None:
        if adapter_id in self._descriptors:
            return self._descriptors[adapter_id]
        entry = self.exec_by_id.get(adapter_id)
        if entry is None:
            return None
        descriptor = _load_yaml(self.pe_root / str(entry["descriptor"]))
        self._descriptors[adapter_id] = descriptor
        return descriptor

    def executable_agents(self) -> dict[str, Any]:
        result = {}
        for key, agent in self.agents.items():
            if not isinstance(agent, dict):
                continue
            block = agent.get("program_execution") or {}
            if block.get("enabled"):
                result[key] = agent
        return result

    def agent_program_adapters(self, agent: dict[str, Any]) -> list[str]:
        block = agent.get("program_execution") or {}
        return [str(item) for item in block.get("adapters") or []]

    def surface_adapter_dir(self, agent: dict[str, Any], key: str) -> Path:
        adapter = str(agent.get("adapter", key))
        return self.agents_root / "adapters" / adapter

    def binding_files(self) -> list[Path]:
        return sorted((self.agents_root / "adapters").glob("*/program-execution.yaml"))


def _check_environment_adapter(model: PeerExecutionModel, errors: list[str]) -> None:
    """R1 — every executable agent has an environment (surface) adapter."""
    for key, agent in model.executable_agents().items():
        adapter = str(agent.get("adapter", key))
        if adapter in PREEXISTING_SURFACES:
            # cursor (.cursor activation) and claude-code (environment/claude-code)
            # are pre-existing activation paths, not adapters/<name> dirs.
            target = model.repo_root / "environment/claude-code"
            if adapter == "claude-code" and not target.is_dir():
                errors.append(f"[R1] {key}: environment/claude-code missing")
            continue
        adir = model.surface_adapter_dir(agent, key)
        if not adir.is_dir():
            errors.append(f"[R1] {key}: surface adapter dir missing: {adir}")


def _check_program_mapping(model: PeerExecutionModel, errors: list[str]) -> None:
    """R2 — every program-enabled agent maps to registered program adapter(s)."""
    for key, agent in model.executable_agents().items():
        adapters = model.agent_program_adapters(agent)
        if not adapters:
            errors.append(f"[R2] {key}: program_execution.enabled but no adapters listed")
        for adapter_id in adapters:
            if adapter_id not in model.exec_by_id:
                errors.append(
                    f"[R2] {key}: program adapter '{adapter_id}' not in execution registry"
                )


def _check_binding_files(model: PeerExecutionModel, errors: list[str]) -> None:
    """R3 — adapter-binding files reference a registered agent and agree."""
    for path in model.binding_files():
        binding = _load_yaml(path)
        kind = binding.get("binding_kind")
        adapters = [str(a) for a in (binding.get("program_execution") or {}).get("adapters") or []]
        for adapter_id in adapters:
            if adapter_id not in model.exec_by_id:
                errors.append(f"[R3] {path.parent.name}: unknown program adapter '{adapter_id}'")
        if kind == "template":
            continue
        agent_id = str(binding.get("agent_id"))
        agent = model.agents.get(agent_id)
        if not isinstance(agent, dict):
            errors.append(f"[R3] {path.parent.name}: agent_id '{agent_id}' not in registry")
            continue
        registry_adapters = model.agent_program_adapters(agent)
        if sorted(adapters) != sorted(registry_adapters):
            errors.append(
                f"[R3] {agent_id}: binding adapters {sorted(adapters)} "
                f"!= registry {sorted(registry_adapters)}"
            )


def _adapter_dirs(model: PeerExecutionModel) -> list[Path]:
    roots = [model.agents_root / "adapters", model.pe_root / "adapters"]
    dirs: list[Path] = []
    for root in roots:
        if root.is_dir():
            dirs.extend(child for child in root.iterdir() if child.is_dir())
    return dirs


def _check_no_autonomy_copy(model: PeerExecutionModel, errors: list[str]) -> None:
    """R4 — no adapter copies root autonomy/."""
    for adir in _adapter_dirs(model):
        for offender in adir.rglob("autonomy"):
            if offender.is_dir():
                rel = offender.relative_to(model.repo_root)
                errors.append(f"[R4] adapter copies autonomy/: {rel}")


def _check_no_core_copy(model: PeerExecutionModel, errors: list[str]) -> None:
    """R5 — no adapter copies the Program Execution core / a 2nd agent registry."""
    for adir in _adapter_dirs(model):
        if (adir / "program-execution-controller-template").exists():
            rel = (adir / "program-execution-controller-template").relative_to(model.repo_root)
            errors.append(f"[R5] adapter copies controller core: {rel}")
        for offender in adir.rglob("agent_registry.yaml"):
            rel = offender.relative_to(model.repo_root)
            errors.append(f"[R5] adapter carries a second agent registry: {rel}")


def _check_role_authority(model: PeerExecutionModel, errors: list[str]) -> None:
    """R6 — adapter authority never exceeds the agent's declared role."""
    for key, agent in model.executable_agents().items():
        role = str(agent.get("role"))
        allowed = ROLE_ADAPTER_KINDS.get(role)
        if allowed is None:
            errors.append(f"[R6] {key}: role '{role}' has no authority mapping")
            continue
        for adapter_id in model.agent_program_adapters(agent):
            entry = model.exec_by_id.get(adapter_id)
            if entry is None:
                continue
            kind = str(entry.get("adapter_kind"))
            if kind not in allowed:
                errors.append(
                    f"[R6] {key}: role '{role}' may not use adapter_kind '{kind}' ({adapter_id})"
                )


def _referenced_adapter_ids(model: PeerExecutionModel) -> set[str]:
    referenced: set[str] = set()
    for agent in model.executable_agents().values():
        referenced.update(model.agent_program_adapters(agent))
    return referenced


def _check_canonical_receipts(model: PeerExecutionModel, errors: list[str]) -> None:
    """R7 — every referenced program adapter emits canonical lifecycle receipts."""
    for adapter_id in sorted(_referenced_adapter_ids(model)):
        descriptor = model.descriptor(adapter_id)
        if descriptor is None:
            continue
        receipts = descriptor.get("receipts") or {}
        if receipts.get("lifecycle_schema") != CANONICAL_LIFECYCLE:
            errors.append(f"[R7] {adapter_id}: non-canonical lifecycle receipt schema")


def _check_cancellation(model: PeerExecutionModel, errors: list[str]) -> None:
    """R8 — every referenced program adapter declares a cancellation posture."""
    for adapter_id in sorted(_referenced_adapter_ids(model)):
        descriptor = model.descriptor(adapter_id)
        if descriptor is None:
            continue
        cancellation = (descriptor.get("capabilities") or {}).get("cancellation")
        if cancellation not in CANCELLATION_ENUM:
            errors.append(f"[R8] {adapter_id}: cancellation posture '{cancellation}' invalid")


def _check_health(model: PeerExecutionModel, errors: list[str]) -> None:
    """R9 — every referenced program adapter reports health honestly."""
    for adapter_id in sorted(_referenced_adapter_ids(model)):
        entry = model.exec_by_id.get(adapter_id)
        if entry is not None and str(entry.get("status")) not in REGISTRY_STATUS_ENUM:
            errors.append(f"[R9] {adapter_id}: registry status '{entry.get('status')}' invalid")
        if adapter_id not in model.health_ids:
            errors.append(f"[R9] {adapter_id}: missing EXECUTION_ADAPTER_HEALTH entry")


def _check_conformance_tests(model: PeerExecutionModel, errors: list[str]) -> None:
    """R10 — every referenced program adapter ships conformance tests."""
    for adapter_id in sorted(_referenced_adapter_ids(model)):
        entry = model.exec_by_id.get(adapter_id)
        if entry is None:
            continue
        adapter_dir = (model.pe_root / str(entry["provider_module"])).parent
        tests = list((adapter_dir / "tests").glob("test_*.py"))
        if not tests:
            rel = adapter_dir.relative_to(model.repo_root)
            errors.append(f"[R10] {adapter_id}: no conformance tests under {rel}/tests")


RULES = (
    _check_environment_adapter,
    _check_program_mapping,
    _check_binding_files,
    _check_no_autonomy_copy,
    _check_no_core_copy,
    _check_role_authority,
    _check_canonical_receipts,
    _check_cancellation,
    _check_health,
    _check_conformance_tests,
)


def validate(repo_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        model = PeerExecutionModel(repo_root)
    except (OSError, ValueError) as exc:
        return {
            "schema": "l9.peer-execution-conformance-report.v1",
            "status": "FAIL",
            "errors": [f"[load] {exc}"],
            "executable_peers": [],
        }
    for rule in RULES:
        rule(model, errors)
    peers = sorted(model.executable_agents())
    return {
        "schema": "l9.peer-execution-conformance-report.v1",
        "status": "PASS" if not errors else "FAIL",
        "executable_peers": peers,
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
        peers = ", ".join(report["executable_peers"])
        sys.stderr.write(f"PASS — peer-execution topology coherent; executable peers: {peers}\n")
    else:
        sys.stderr.write(f"FAIL — {len(report['errors'])} violation(s):\n")
        for item in report["errors"]:
            sys.stderr.write(f"  {item}\n")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
