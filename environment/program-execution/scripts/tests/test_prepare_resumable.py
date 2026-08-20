"""Preparing an already-prepared campaign must resume it, not rebuild it.

`quarantine_occupied` used to run unconditionally before compile, so the second
`make campaign` for an id stepped the live runtime aside and rebuilt it from
nothing. That made the repeat cost identical to the first run and, once the
caches below it started working, was the only thing still forcing the work.

Resuming is only sound when the live runtime came from the same compile inputs,
so the interesting cases here are both directions: an unchanged campaign must be
resumed, and a campaign whose source moved must still be quarantined.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

TESTS_DIR = Path(__file__).resolve().parent
PE_ROOT = TESTS_DIR.parents[1]
SCRIPT = PE_ROOT / "scripts/run_campaign.py"
ACTIVATE = PE_ROOT.parents[1] / "skills/l9-pe-campaign-activate/scripts/compile_activation_files.py"

if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from test_run_campaign import (  # type: ignore[import-not-found]  # noqa: E402
    READY_SEED,
    _dump,
    _git_init,
    _host_repo,
    _load,
    _stack_ok,
)

CAMPAIGN_ID = str(READY_SEED["campaign_id"])


class PrepareResumeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("run_campaign_resume", SCRIPT)
        cls.activate = _load("compile_activation_resume", ACTIVATE)

    def _fixture(self, tmp: Path) -> tuple[Path, Path, Path]:
        """A host repo with a Ready campaign source and an initialised target."""
        root = _host_repo(tmp / "host")
        source = self.activate.build_source(READY_SEED, stamp="2026-01-01T00:00:00Z")
        source["tasks"][1]["depends_on"] = ["TASK-001"]
        entry = root / "CAMPAIGN_SOURCE.yaml"
        _dump(entry, source)
        l9 = tmp / "l9"
        target = l9 / "program-worktrees" / CAMPAIGN_ID
        target.mkdir(parents=True)
        _git_init(target)
        return root, entry, l9

    def _prepare(self, entry: Path, *, root: Path, l9: Path, primary: Path) -> Any:
        return self.mod.run_campaign(
            entry,
            until="arm",
            primary=primary,
            repo_root=root,
            l9_root=l9,
            fast=True,
            hooks=self.mod.Hooks(context7_stack=_stack_ok),
        )

    def _prepare_twice(self, tmp: Path, *, mutate=None) -> tuple[Path, Path]:
        root, entry, l9 = self._fixture(tmp)
        with unittest.mock.patch.dict("os.environ", {**os.environ, "L9_CAMPAIGN_UNTIL_DEBUG": "1"}):
            self._prepare(entry, root=root, l9=l9, primary=tmp / "primary")
            if mutate is not None:
                mutate(entry)
            self._prepare(entry, root=root, l9=l9, primary=tmp / "primary")
        return l9, entry

    def test_repeating_prepare_does_not_quarantine_the_live_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            l9, _ = self._prepare_twice(Path(raw))

            stale = l9 / "programs" / "stale"
            self.assertFalse(
                stale.exists() and any(stale.iterdir()),
                f"live runtime was stepped aside on an unchanged repeat: "
                f"{sorted(p.name for p in stale.iterdir()) if stale.exists() else []}",
            )
            self.assertFalse(
                (l9 / "blueprints" / "stale").exists(),
                "blueprint was stepped aside on an unchanged repeat",
            )

    def test_repeating_prepare_reuses_the_expensive_stages(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            l9, _ = self._prepare_twice(Path(raw))
            state = _prepare_state(l9)

            for stage in ("compile", "accept", "bootstrap", "emit"):
                self.assertTrue(
                    state[stage]["reused"],
                    f"{stage} recomputed on an unchanged repeat: {state[stage]}",
                )

    def test_every_recompute_records_a_reason(self) -> None:
        """The operator's question is "why did it do that again?"."""
        with tempfile.TemporaryDirectory() as raw:
            l9, _ = self._prepare_twice(Path(raw))
            for stage, entry in _prepare_state(l9).items():
                self.assertIn("reason", entry, f"{stage} recorded no reason")
                self.assertTrue(str(entry["reason"]).strip(), f"{stage} reason is empty")

    def test_a_changed_campaign_source_is_still_quarantined(self) -> None:
        """The safety property: a moved source is a different campaign."""
        import yaml

        def mutate(entry: Path) -> None:
            doc = yaml.safe_load(entry.read_text(encoding="utf-8"))
            doc["objective"] = "A materially different objective for the same id."
            _dump(entry, doc)

        with tempfile.TemporaryDirectory() as raw:
            l9, _ = self._prepare_twice(Path(raw), mutate=mutate)

            stale = l9 / "programs" / "stale"
            self.assertTrue(
                stale.is_dir() and any(stale.iterdir()),
                "a campaign whose source moved was attached to instead of rebuilt",
            )
            self.assertFalse(_prepare_state(l9)["compile"]["reused"])

    def test_a_deleted_blueprint_forces_a_rebuild(self) -> None:
        """A cache entry is not evidence that the work is still done."""
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root, entry, l9 = self._fixture(tmp)
            with unittest.mock.patch.dict(
                "os.environ", {**os.environ, "L9_CAMPAIGN_UNTIL_DEBUG": "1"}
            ):
                report = self._prepare(entry, root=root, l9=l9, primary=tmp / "primary")

                import shutil

                shutil.rmtree(Path(report.blueprint))
                self._prepare(entry, root=root, l9=l9, primary=tmp / "primary")

            state = _prepare_state(l9)
            self.assertFalse(
                state["compile"]["reused"],
                "compile was skipped even though its blueprint had been deleted",
            )
            self.assertTrue(Path(report.blueprint).is_dir(), "blueprint was not rebuilt")


def _prepare_state(l9: Path) -> dict[str, Any]:
    path = l9 / "primed" / CAMPAIGN_ID / "PREPARE_STATE.json"
    if not path.is_file():
        raise AssertionError(f"no prepare state recorded at {path}")
    return dict(json.loads(path.read_text(encoding="utf-8"))["stages"])


if __name__ == "__main__":
    unittest.main()
