"""Adapter conformance tests (law §28): adapters may not weaken invariants."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ADAPTERS = ROOT / "adapters"

REQUIRED_MAY_NOT_WEAKEN = {
    "packet_emission",
    "provenance",
    "classification",
    "routing",
    "promotion_authority",
    "learning_closure",
}


def _load(name: str) -> dict:
    return yaml.safe_load((ADAPTERS / name).read_text(encoding="utf-8"))


class AdapterConformanceTests(unittest.TestCase):
    def test_base_declares_full_may_not_weaken(self) -> None:
        base = _load("base.yaml")
        self.assertEqual(set(base["may_not_weaken"]), REQUIRED_MAY_NOT_WEAKEN)

    def test_base_does_not_load_raw_packets_by_default(self) -> None:
        base = _load("base.yaml")
        self.assertFalse(base["context_selection"]["load_raw_packets_by_default"])

    def test_class_adapters_inherit_base_and_do_not_relax(self) -> None:
        for name in ("python.yaml", "typescript.yaml"):
            adapter = _load(name)
            self.assertEqual(adapter["inherits"], "base", name)
            # A class adapter must not redeclare a narrower may_not_weaken set.
            if "may_not_weaken" in adapter:
                self.assertTrue(
                    REQUIRED_MAY_NOT_WEAKEN <= set(adapter["may_not_weaken"]),
                    f"{name} weakens the base invariant set",
                )

    def test_memory_adapter_is_advisory_and_non_overriding(self) -> None:
        memory = _load("memory-adapter.yaml")
        guards = memory["guards"]
        self.assertTrue(guards["advisory_only"])
        self.assertFalse(guards["overrides_repository_state"])
        self.assertFalse(guards["overrides_canonical_authority"])
        self.assertTrue(guards["excludes_contested_units"])

    def test_memory_adapter_enforces_visibility(self) -> None:
        memory = _load("memory-adapter.yaml")
        vis = memory["visibility_enforcement"]
        self.assertTrue(vis["block_cross_repository_without_authorization"])


if __name__ == "__main__":
    unittest.main()
