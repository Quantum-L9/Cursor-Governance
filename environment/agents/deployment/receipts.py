# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/deployment/receipts.py
#   layer: library
#   owner: governance-control-plane
#   status: active
#   version: 1.0.0
#   updated: 2026-08-12
"""Deployment receipt write/verify helpers via runtime_paths."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

RECEIPT_SCHEMA = "l9.agents.deployment-receipt.v1"

_HERE = Path(__file__).resolve().parent
_AGENTS_ROOT = _HERE.parent


def _load_runtime_paths():
    path = _AGENTS_ROOT / "runtime_paths.py"
    spec = importlib.util.spec_from_file_location("l9_agents_runtime_paths", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load runtime_paths from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def compute_receipt_digest(receipt: Mapping[str, Any]) -> str:
    payload = dict(receipt)
    payload.pop("receipt_digest", None)
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def with_receipt_digest(receipt: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(receipt)
    body["receipt_digest"] = compute_receipt_digest(body)
    return body


def verify_receipt_digest(receipt: Mapping[str, Any]) -> bool:
    expected = compute_receipt_digest(receipt)
    return str(receipt.get("receipt_digest") or "") == expected


def workspace_id_for(workspace: Path) -> str:
    resolved = str(Path(workspace).expanduser().resolve())
    return hashlib.sha256(resolved.encode("utf-8")).hexdigest()


def receipt_path(*, surface: str, workspace_id: str) -> Path:
    rp = _load_runtime_paths()
    return (rp.deployment_receipt_root() / surface / f"{workspace_id}.json").resolve()


def write_deployment_receipt(
    receipt: Mapping[str, Any],
    *,
    surface: str,
    workspace_id: str,
) -> Path:
    body = with_receipt_digest(receipt)
    if body.get("schema") != RECEIPT_SCHEMA:
        body["schema"] = RECEIPT_SCHEMA
        body = with_receipt_digest(body)
    path = receipt_path(surface=surface, workspace_id=workspace_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def read_deployment_receipt(*, surface: str, workspace_id: str) -> dict[str, Any] | None:
    path = receipt_path(surface=surface, workspace_id=workspace_id)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"deployment receipt must be an object: {path}")
    return data
