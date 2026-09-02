from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # fail closed for skill-local machine contracts
    raise SystemExit("PyYAML is required for l9-idea-execute scripts") from exc


class ContractError(ValueError):
    pass


def load_data(path: str | Path) -> Any:
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"cannot read {p}: {exc}") from exc
    try:
        if p.suffix.lower() == ".json":
            return json.loads(text)
        return yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ContractError(f"cannot parse {p}: {exc}") from exc


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be a mapping")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{label} must be a list")
    return value


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def semantic_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def dump_yaml(value: Any) -> str:
    return yaml.safe_dump(value, sort_keys=False, allow_unicode=True)


def assert_acyclic(nodes: set[str], edges: dict[str, set[str]], label: str) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            raise ContractError(f"{label} contains a dependency cycle at {node}")
        visiting.add(node)
        for dep in edges.get(node, set()):
            if dep not in nodes:
                raise ContractError(f"{label} references unknown dependency {dep}")
            visit(dep)
        visiting.remove(node)
        visited.add(node)

    for node in sorted(nodes):
        visit(node)
