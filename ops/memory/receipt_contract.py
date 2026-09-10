"""Canonical memory-control-plane/v1 receipt contract (consumer SSOT).

The bound ``l9-graphite-memory`` release owns the pydantic models. This
repository was missing a checked-in consumer contract: the only copy lived
inside test fixtures, so a failed live schema probe left validation with
nothing to apply.

This module loads ``ops/config/memory-receipt-contract.json``. Cursor narrows
required fields; it does not restate the package models and does not reject a
superset. A live probe from the bound interpreter still wins when it exports a
model. Compatible package majors are every V2 (2.2 and 2.3.x).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

CONTRACT_SCHEMA = "l9.memory.receipt-contract/v1"
DEFAULT_CONTRACT_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "memory-receipt-contract.json"
)


class ReceiptContractError(ValueError):
    """The checked-in receipt contract is missing or not canonical."""


def load_receipt_contract(path: Path | None = None) -> dict[str, Any]:
    target = path or DEFAULT_CONTRACT_PATH
    if not target.is_file():
        raise ReceiptContractError(f"canonical receipt contract missing: {target}")
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptContractError(f"canonical receipt contract unreadable: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("schema") != CONTRACT_SCHEMA:
        raise ReceiptContractError(f"receipt contract is not {CONTRACT_SCHEMA}: {target}")
    models = raw.get("models")
    if not isinstance(models, dict) or not models:
        raise ReceiptContractError("receipt contract has no models")
    # #region agent log
    try:
        import time

        _debug_log = Path(__file__).resolve().parents[2] / ".cursor" / "debug-01ef49.log"
        with _debug_log.open("a", encoding="utf-8") as _dbg:
            _dbg.write(
                json.dumps(
                    {
                        "sessionId": "01ef49",
                        "runId": "receipt-contract",
                        "hypothesisId": "H-contract",
                        "location": "ops/memory/receipt_contract.py:load",
                        "message": "loaded canonical receipt contract",
                        "data": {
                            "path": str(target),
                            "models": sorted(models),
                            "majors": raw.get("compatible_package_majors"),
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
    except OSError:
        # Best-effort debug NDJSON; a log-write failure must not fail contract load.
        pass
    # #endregion
    return raw


def canonical_receipt_schemas(path: Path | None = None) -> dict[str, Any]:
    """JSON Schema map keyed by Cursor receipt names."""

    return dict(load_receipt_contract(path)["models"])


def compatible_package_majors(path: Path | None = None) -> frozenset[int]:
    raw = load_receipt_contract(path).get("compatible_package_majors") or [2]
    return frozenset(int(item) for item in raw)


def merge_receipt_schemas(
    probed: Mapping[str, Any] | None,
    *,
    path: Path | None = None,
) -> tuple[dict[str, Any], str]:
    """Prefer a live probe; fill gaps from the checked-in V2 contract."""

    canonical = canonical_receipt_schemas(path)
    if not probed:
        return canonical, "canonical-file"
    merged = dict(canonical)
    merged.update({key: value for key, value in probed.items() if isinstance(value, dict)})
    source = "probed+canonical-file" if set(canonical) - set(probed) else "probed"
    return merged, source


__all__ = [
    "CONTRACT_SCHEMA",
    "DEFAULT_CONTRACT_PATH",
    "ReceiptContractError",
    "canonical_receipt_schemas",
    "compatible_package_majors",
    "load_receipt_contract",
    "merge_receipt_schemas",
]
