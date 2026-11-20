"""Direct coverage for ``_bind_rendered_admission_evidence``.

A rendered plan skips default_admit, so evidence marked
``collect_at_admission`` must be bound before bootstrap freezes the catalog.
These cases pin that seam at its owner: nothing pending binds nothing, an
unreadable target refuses, every pending row is collected at the measured
revision, a collector refusal surfaces as ``ADMISSION_EVIDENCE``, and the
manifest's bound ``source_sha256`` survives the collector's rewrite.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PE_ROOT / "scripts/run_campaign.py"


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _FakeCollector:
    """Records each collect call and rewrites the manifest like the real one."""

    def __init__(self, manifest: Path, *, fail_on: str | None = None) -> None:
        self.manifest = manifest
        self.fail_on = fail_on
        self.calls: list[dict[str, Any]] = []

    def collect_evidence(self, blueprint: Path, **kwargs: Any) -> dict[str, Any]:
        if kwargs["evidence_id"] == self.fail_on:
            raise RuntimeError(f"cannot collect {self.fail_on}")
        self.calls.append({"blueprint": blueprint, **kwargs})
        if self.manifest.is_file():
            data = yaml.safe_load(self.manifest.read_text(encoding="utf-8")) or {}
            data["source_sha256"] = "rewritten-by-collector"
            self.manifest.write_text(yaml.safe_dump(data), encoding="utf-8")
        return {"id": kwargs["evidence_id"]}


class BindRenderedAdmissionEvidenceTest(unittest.TestCase):
    mod: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("run_campaign_rendered_admission_under_test", SCRIPT)

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.blueprint = Path(tmp.name) / "blueprint"
        self.blueprint.mkdir()
        self.target = Path(tmp.name) / "target"
        self.target.mkdir()
        self.checkouts = 0

    def _run(self) -> SimpleNamespace:
        def ensure_target_checkout_once() -> None:
            self.checkouts += 1

        return SimpleNamespace(
            blueprint=self.blueprint,
            campaign_id="CAMPAIGN-TEST",
            target_worktree=str(self.target),
            ensure_target_checkout_once=ensure_target_checkout_once,
        )

    def _catalog(self, rows: list[Any]) -> None:
        (self.blueprint / "EVIDENCE_CATALOG.yaml").write_text(
            yaml.safe_dump({"evidence": rows}), encoding="utf-8"
        )

    def _manifest(self, source_sha256: str) -> Path:
        path = self.blueprint / "MANIFEST.yaml"
        path.write_text(yaml.safe_dump({"source_sha256": source_sha256}), encoding="utf-8")
        return path

    def _patched(self, collector: _FakeCollector, measured: dict[str, Any]) -> Any:
        real_load = self.mod._load_script

        def fake_load(name: str, path: Path) -> Any:
            if name == "collect_evidence":
                return collector
            return real_load(name, path)

        return unittest.mock.patch.multiple(
            self.mod,
            _load_script=fake_load,
            measure_admission_evidence=lambda _path: measured,
        )

    def test_no_catalog_binds_nothing(self) -> None:
        self.assertEqual(self.mod._bind_rendered_admission_evidence(self._run()), {"bound": []})
        self.assertEqual(self.checkouts, 0)

    def test_no_pending_rows_binds_nothing_without_checkout(self) -> None:
        self._catalog(
            [
                {"id": "EV-1", "freshness": "collect_at_admission", "status": "collected"},
                {"id": "EV-2", "freshness": "collect_at_runtime", "status": "planned"},
                "not-a-row",
            ]
        )
        self.assertEqual(self.mod._bind_rendered_admission_evidence(self._run()), {"bound": []})
        self.assertEqual(self.checkouts, 0)

    def test_unreadable_target_refuses(self) -> None:
        self._catalog([{"id": "EV-1", "freshness": "collect_at_admission", "status": "planned"}])
        collector = _FakeCollector(self.blueprint / "MANIFEST.yaml")
        with self._patched(collector, {"available": False}):
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod._bind_rendered_admission_evidence(self._run())
        self.assertEqual(ctx.exception.error_code, "ADMISSION_EVIDENCE")
        self.assertIn("not a readable git checkout", str(ctx.exception))
        self.assertEqual(self.checkouts, 1)
        self.assertEqual(collector.calls, [])

    def test_pending_rows_bind_at_measured_revision_and_keep_source(self) -> None:
        self._catalog(
            [
                {"id": "EV-1", "freshness": "collect_at_admission", "status": "planned"},
                {"id": "EV-2", "freshness": "collect_at_admission", "status": "planned"},
                {"id": "EV-3", "freshness": "collect_at_admission", "status": "collected"},
            ]
        )
        manifest = self._manifest("bound-source-digest")
        collector = _FakeCollector(manifest)
        with self._patched(collector, {"available": True, "revision": "abc123"}):
            result = self.mod._bind_rendered_admission_evidence(self._run())
        self.assertEqual(result, {"bound": ["EV-1", "EV-2"], "revision": "abc123"})
        self.assertEqual([call["evidence_id"] for call in collector.calls], ["EV-1", "EV-2"])
        for call in collector.calls:
            self.assertEqual(call["revision"], "abc123")
            self.assertEqual(call["producer"], "make-campaign")
            self.assertIsNone(call["digest"])
            self.assertIsNone(call["expires_at"])
        written = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        self.assertEqual(written["source_sha256"], "bound-source-digest")

    def test_pending_rows_without_manifest_still_bind(self) -> None:
        self._catalog([{"id": "EV-1", "freshness": "collect_at_admission", "status": "planned"}])
        collector = _FakeCollector(self.blueprint / "MANIFEST.yaml")
        with self._patched(collector, {"available": True, "revision": "def456"}):
            result = self.mod._bind_rendered_admission_evidence(self._run())
        self.assertEqual(result, {"bound": ["EV-1"], "revision": "def456"})
        self.assertFalse((self.blueprint / "MANIFEST.yaml").exists())

    def test_collector_refusal_surfaces_as_admission_evidence(self) -> None:
        self._catalog([{"id": "EV-1", "freshness": "collect_at_admission", "status": "planned"}])
        collector = _FakeCollector(self._manifest("bound"), fail_on="EV-1")
        with self._patched(collector, {"available": True, "revision": "abc123"}):
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod._bind_rendered_admission_evidence(self._run())
        self.assertEqual(ctx.exception.error_code, "ADMISSION_EVIDENCE")
        self.assertIn("cannot collect EV-1", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
