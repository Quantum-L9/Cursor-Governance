"""Peer adapter default profiles are registry data, not code inference."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from peer_execution.imports import pe_script

_loader = pe_script("provider_loader")
PE_ROOT = Path(__file__).resolve().parents[1]


class ProfileDefaultTests(unittest.TestCase):
    def test_every_peer_adapter_declares_its_default_in_the_registry(self) -> None:
        registry = yaml.safe_load(
            (PE_ROOT / "registry/EXECUTION_ADAPTER_REGISTRY.yaml").read_text(encoding="utf-8")
        )
        profiles = yaml.safe_load(
            (PE_ROOT / "registry/EXECUTION_PROFILE_REGISTRY.yaml").read_text(encoding="utf-8")
        )["profiles"]
        for entry in registry["adapters"]:
            descriptor = yaml.safe_load((PE_ROOT / entry["descriptor"]).read_text(encoding="utf-8"))
            if (descriptor.get("identity") or {}).get("binding") != "peer_runtime_binding":
                continue
            ref = _loader.default_execution_profile_ref(entry["adapter_id"], entry)
            self.assertIn(ref, profiles, entry["adapter_id"])

    def test_registry_default_is_the_fallback_after_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            adapter = _loader.instantiate("manus-cloud", Path(raw))
            self.assertEqual(adapter.execution_profile["profile_ref"], "worker-read-only")
            reviewer = _loader.instantiate("gemini-review", Path(raw))
            self.assertEqual(reviewer.execution_profile["profile_ref"], "reviewer-default")

    def test_a_missing_registry_default_is_refused_not_inferred(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            _loader.default_execution_profile_ref("manus-cloud", {"adapter_id": "manus-cloud"})
        self.assertIn("default_execution_profile_ref", str(ctx.exception))
