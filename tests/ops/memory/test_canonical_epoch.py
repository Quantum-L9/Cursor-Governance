"""The canonical epoch record agrees with the binding manifest and the boundary."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EPOCH = ROOT / "ops" / "config" / "memory-canonical-epoch.json"
BINDING = ROOT / "ops" / "config" / "memory-binding.json"


def test_epoch_matches_the_binding_manifest() -> None:
    epoch = json.loads(EPOCH.read_text(encoding="utf-8"))
    binding = json.loads(BINDING.read_text(encoding="utf-8"))
    assert epoch["epoch"]["memory_release"] == binding["expected_package_version"]
    assert epoch["epoch"]["memory_source_ref"] == binding["source"]["ref"]
    assert epoch["epoch"]["control_plane_contract"] == binding["expected_contract_version"]


def test_epoch_names_existing_modules_only() -> None:
    epoch = json.loads(EPOCH.read_text(encoding="utf-8"))
    for value in epoch["session_lifecycle"].values():
        path = value.split(" ")[0]
        if "/" in path:
            assert (ROOT / path).exists(), path
    assert (ROOT / epoch["legacy_reconciliation"]["classifier"]).is_file()


def test_epoch_grants_nothing_and_names_the_provider_as_projection() -> None:
    epoch = json.loads(EPOCH.read_text(encoding="utf-8"))
    assert epoch["authority"]["provider_role"].startswith("projection-only")
    assert "grants nothing" in epoch["description"]
    from ops.memory import legacy_reconciliation as lr

    expected = [
        lr.CLASS_CANONICAL_KNOWN,
        lr.CLASS_CONTINUATION,
        lr.CLASS_DURABLE,
        lr.CLASS_MALFORMED,
        lr.CLASS_DUPLICATE,
        lr.CLASS_FORBIDDEN,
        lr.CLASS_REFUSED,
    ]
    assert epoch["legacy_reconciliation"]["classes"] == expected
    assert epoch["legacy_reconciliation"]["export_schema"] == lr.EXPORT_SCHEMA
