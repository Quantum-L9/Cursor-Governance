"""W2 — machine-readable counterexample registry. No product fixes in this module."""

from __future__ import annotations

from pathlib import Path

import yaml


def test_counterexample_registry_covers_at_002_through_at_008() -> None:
    path = Path(__file__).resolve().parent / "counterexamples.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["schema"] == "l9.pec.counterexample-registry.v1"
    ats = {entry["at"] for entry in data["entries"]}
    assert ats == {f"AT-00{n}" for n in range(2, 9)}
