from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

import yaml

FORBIDDEN_IMPORT_PREFIXES = (
    "adapters.common.base",
    "adapters.common.core_receipts",
    "adapters.common.receipts",
    "adapters.common.runtime_store",
    "peer_execution.base",
    "peer_execution.core_receipts",
    "peer_execution.receipts",
    "peer_execution.runtime_store",
)
FORBIDDEN_BASE_NAMES = {"BaseExecutionAdapter", "PeerExecutionAdapter", "DriverExecutionAdapter"}
FORBIDDEN_LEGACY_FILES = {"driver.py", "receipt_mapper.py"}


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML document must be an object: {path}")
    return value


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_name(node.value)}.{node.attr}"
    return ""


def _provider_shape(provider_path: Path) -> tuple[ast.Module, bool]:
    tree = ast.parse(provider_path.read_text(encoding="utf-8"), filename=str(provider_path))
    exported = False
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(
            isinstance(target, ast.Name) and target.id == "PROVIDER_CLASS" for target in targets
        ):
            exported = True
    return tree, exported


def _provider_errors(subsystem: Path, entry: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    provider_ref = str(entry["adapter_id"])
    descriptor_path = subsystem / str(entry["descriptor"])
    provider_path = subsystem / str(entry["provider_module"])
    tree, exported = _provider_shape(provider_path)
    descriptor = _load_yaml(descriptor_path)
    identity = descriptor.get("identity") or {}
    peer_bound = identity.get("binding") == "peer_runtime_binding"
    non_routable = entry.get("status") == "non_routable"
    if non_routable:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if _name(base).split(".")[-1] in FORBIDDEN_BASE_NAMES:
                        errors.append(
                            f"{provider_ref}: non-routable factory inherits runtime lifecycle owner"
                        )
        if exported:
            errors.append(f"{provider_ref}: non-routable factory must not export PROVIDER_CLASS")
        return True, errors
    thin_expected = True
    if peer_bound and "agent_ref" in identity:
        errors.append(f"{provider_ref}: provider descriptor must not carry agent_ref")
    adapter_dir = provider_path.parent
    for name in sorted(FORBIDDEN_LEGACY_FILES):
        if (adapter_dir / name).is_file():
            errors.append(f"{provider_ref}: legacy thick-provider file remains: {name}")
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith(FORBIDDEN_IMPORT_PREFIXES):
                errors.append(f"{provider_ref}: forbidden shared-authority import: {module}")
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if _name(base).split(".")[-1] in FORBIDDEN_BASE_NAMES:
                    errors.append(
                        f"{provider_ref}: thin provider inherits lifecycle owner: {_name(base)}"
                    )
    if not exported:
        errors.append(f"{provider_ref}: routable execution module must export PROVIDER_CLASS")
    if peer_bound:
        peer_forbidden = {
            "peer_execution.context",
            "peer_execution.permissions",
            "peer_execution.approvals",
            "peer_execution.terminal_receipts",
            "peer_execution.driver_execution",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "") in peer_forbidden:
                errors.append(
                    f"{provider_ref}: peer provider owns upstream execution concern: {node.module}"
                )
    return True, errors


def validate(subsystem: Path) -> dict[str, Any]:
    registry = _load_yaml(subsystem / "registry/EXECUTION_ADAPTER_REGISTRY.yaml")
    errors: list[str] = []
    checked: list[str] = []
    for raw in registry.get("adapters") or []:
        entry = dict(raw)
        if entry.get("adapter_id") == "claude-code-bounded-autonomy":
            errors.append("bounded execution must not be modeled as a Claude provider adapter")
        provider_path = subsystem / str(entry["provider_module"])
        if not provider_path.is_file():
            continue
        expected, provider_errors = _provider_errors(subsystem, entry)
        if expected:
            checked.append(str(entry["adapter_id"]))
            errors.extend(provider_errors)
    adapter_roots = [subsystem / "adapters"]
    for root in adapter_roots:
        if not root.is_dir():
            continue
        for autonomy in root.rglob("autonomy"):
            if autonomy.is_dir():
                errors.append(
                    "adapter-owned autonomy runtime forbidden: "
                    + autonomy.relative_to(subsystem).as_posix()
                )
    return {
        "schema": "l9.peer-execution.thin-provider-conformance.v1",
        "status": "PASS" if not errors else "FAIL",
        "checked_thin_providers": sorted(checked),
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    subsystem = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[1]
    report = validate(subsystem)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
