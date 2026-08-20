"""Preparation reuse must be evidence-based, and must explain itself.

The interesting cases are all the ones where a cache entry exists but reusing it
would be wrong. A stage that wrote a blueprint and then had that blueprint
deleted is not "done", however healthy its cache entry looks.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

PE_SCRIPTS = Path(__file__).resolve().parents[1]
if str(PE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PE_SCRIPTS))

from pe_prepare_state import (  # type: ignore[import-not-found]  # noqa: E402
    CACHE_DISABLED,
    INPUT_CHANGED,
    NO_RECORD,
    OUTPUT_MISSING,
    PREPARE_STATE_SCHEMA,
    REUSED,
    PrepareCache,
    PrepareState,
)
from pe_timing import (  # type: ignore[import-not-found]  # noqa: E402
    StageCache,
    StageTimer,
    write_json_atomic,
)


class PrepareStateTests(unittest.TestCase):
    def test_state_round_trips_through_the_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "PREPARE_STATE.json"
            state = PrepareState(path=path, campaign_id="demo-v1")
            state.record(
                "compile",
                key="abc123",
                decision=_decision(False, NO_RECORD),
                outputs=["/tmp/blueprint"],
                seconds=1.25,
            )
            reloaded = PrepareState.load(path)
            self.assertEqual(reloaded.campaign_id, "demo-v1")
            self.assertEqual(reloaded.stages["compile"]["key"], "abc123")
            self.assertEqual(reloaded.stages["compile"]["duration_s"], 1.25)
            self.assertEqual(reloaded.stages["compile"]["outputs"], ["/tmp/blueprint"])

    def test_unreadable_or_foreign_state_is_a_rebuild_not_a_crash(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "PREPARE_STATE.json"
            path.write_text("{not json", encoding="utf-8")
            self.assertEqual(PrepareState.load(path).stages, {})

            path.write_text(json.dumps({"schema": "something.else.v9"}), encoding="utf-8")
            self.assertEqual(PrepareState.load(path).stages, {})

    def test_saved_state_declares_its_schema(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "PREPARE_STATE.json"
            PrepareState(path=path).save()
            doc = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(doc["schema"], PREPARE_STATE_SCHEMA)

    def test_save_leaves_no_temporary_files_behind(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state = PrepareState(path=root / "PREPARE_STATE.json")
            for index in range(3):
                state.record(f"stage{index}", key="k", decision=_decision(True, REUSED))
            self.assertEqual([p.name for p in root.glob("*.tmp")], [])


class AtomicWriteTests(unittest.TestCase):
    """Preparation is the phase that gets interrupted, so its record must survive it."""

    def test_a_failed_write_leaves_the_previous_content_intact(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = root / "state.json"
            write_json_atomic(path, {"generation": 1})

            with unittest.mock.patch("os.replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    write_json_atomic(path, {"generation": 2})

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"generation": 1})
            self.assertEqual([p.name for p in root.glob("*.tmp")], [])

    def test_a_reader_never_sees_a_partial_file(self) -> None:
        """os.replace is atomic, so the file is only ever one whole document."""
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "state.json"
            for generation in range(1, 6):
                write_json_atomic(path, {"generation": generation, "pad": "x" * 100_000})
                doc = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(doc["generation"], generation)


class PrepareCacheDecisionTests(unittest.TestCase):
    def _cache(self, root: Path, *, enabled: bool = True) -> PrepareCache:
        return PrepareCache(
            StageCache(root / "cache", enabled=enabled),
            PrepareState(path=root / "PREPARE_STATE.json"),
        )

    def test_disabled_cache_never_reuses(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cache = self._cache(Path(raw), enabled=False)
            decision = cache.decide("compile", "key-1")
            self.assertFalse(decision.reuse)
            self.assertEqual(decision.reason, CACHE_DISABLED)

    def test_first_ever_run_reports_no_prior_record(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cache = self._cache(Path(raw))
            decision = cache.decide("compile", "key-1")
            self.assertFalse(decision.reuse)
            self.assertEqual(decision.reason, NO_RECORD)

    def test_unchanged_inputs_reuse_and_return_the_cached_value(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cache = self._cache(Path(raw))
            first = cache.decide("compile", "key-1")
            cache.commit("compile", "key-1", first, value={"errors": []})

            second = cache.decide("compile", "key-1")
            self.assertTrue(second.reuse)
            self.assertEqual(second.reason, REUSED)
            self.assertEqual(second.value, {"errors": []})

    def test_changed_input_is_reported_as_a_changed_input(self) -> None:
        """The operator asked "why did it recompile?"; "input_changed" answers it."""
        with tempfile.TemporaryDirectory() as raw:
            cache = self._cache(Path(raw))
            first = cache.decide("compile", "key-1")
            cache.commit("compile", "key-1", first, value={"errors": []})

            decision = cache.decide("compile", "key-2")
            self.assertFalse(decision.reuse)
            self.assertEqual(decision.reason, INPUT_CHANGED)
            self.assertIn("→", decision.detail)

    def test_a_hit_whose_output_was_deleted_is_a_miss(self) -> None:
        """The case that makes a bare cache unsafe for a side-effecting stage."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cache = self._cache(root)
            blueprint = root / "blueprint"
            blueprint.mkdir()

            first = cache.decide("compile", "key-1", outputs=[blueprint])
            cache.commit("compile", "key-1", first, outputs=[blueprint], value={"ok": True})
            self.assertTrue(cache.decide("compile", "key-1", outputs=[blueprint]).reuse)

            blueprint.rmdir()
            decision = cache.decide("compile", "key-1", outputs=[blueprint])
            self.assertFalse(decision.reuse, "reused a stage whose output is gone")
            self.assertEqual(decision.reason, OUTPUT_MISSING)
            self.assertIn("blueprint", decision.detail)

    def test_commit_records_the_decision_in_durable_state(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cache = self._cache(root)
            decision = cache.decide("launchability", "key-1")
            cache.commit("launchability", "key-1", decision, value={"status": "PASS"}, seconds=0.5)

            doc = json.loads((root / "PREPARE_STATE.json").read_text(encoding="utf-8"))
            entry = doc["stages"]["launchability"]
            self.assertEqual(entry["key"], "key-1")
            self.assertEqual(entry["reason"], NO_RECORD)
            self.assertFalse(entry["reused"])
            self.assertEqual(entry["duration_s"], 0.5)

    def test_reused_stage_is_not_rewritten_to_the_cache(self) -> None:
        """A reuse must not rewrite the entry it just read; that hides staleness."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cache = self._cache(root)
            first = cache.decide("accept", "key-1")
            cache.commit("accept", "key-1", first, value={"generation": 1})

            hit = cache.decide("accept", "key-1")
            cache.commit("accept", "key-1", hit, value={"generation": 2})
            self.assertEqual(cache.cache.get("accept", "key-1"), {"generation": 1})


class StageContextTests(unittest.TestCase):
    """The wrapper the campaign actually calls: time it, skip it, explain it."""

    def _cache(self, root: Path, *, enabled: bool = True) -> PrepareCache:
        return PrepareCache(
            StageCache(root / "cache", enabled=enabled),
            PrepareState(path=root / "PREPARE_STATE.json"),
        )

    def test_second_run_skips_the_body_and_hands_back_the_value(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cache = self._cache(root)
            timer = StageTimer()
            calls = []

            for _ in range(2):
                with cache.stage(timer, "compile", "key-1") as run:
                    if not run.reused:
                        calls.append("ran")
                        run.value = {"errors": []}

            self.assertEqual(calls, ["ran"], "body ran twice for an unchanged input")
            entries = {entry["stage"]: entry for entry in timer.stages}
            self.assertTrue(entries["compile"]["cached"])
            self.assertEqual(entries["compile"]["detail"]["reason"], REUSED)

    def test_a_changed_key_runs_the_body_again_and_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cache = self._cache(Path(raw))
            timer = StageTimer()
            calls = []
            for key in ("key-1", "key-2"):
                with cache.stage(timer, "compile", key) as run:
                    if not run.reused:
                        calls.append(key)
                        run.value = {"key": key}

            self.assertEqual(calls, ["key-1", "key-2"])
            self.assertEqual(timer.stages[-1]["detail"]["reason"], INPUT_CHANGED)

    def test_verify_downgrades_a_hit_to_a_miss(self) -> None:
        """For stages whose output path is only known from the cached value."""
        with tempfile.TemporaryDirectory() as raw:
            cache = self._cache(Path(raw))
            timer = StageTimer()
            calls = []

            def run_once(verify):
                with cache.stage(timer, "plan_window", "key-1", verify=verify) as run:
                    if not run.reused:
                        calls.append("ran")
                        run.value = {"intent_path": "/nowhere/intent.yaml"}

            run_once(None)
            run_once(lambda value: Path(str(value["intent_path"])).is_file())

            self.assertEqual(calls, ["ran", "ran"], "reused a receipt pointing at nothing")
            self.assertEqual(timer.stages[-1]["detail"]["reason"], OUTPUT_MISSING)

    def test_the_body_raising_does_not_record_a_completed_stage(self) -> None:
        """A stage that failed must not be remembered as done."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cache = self._cache(root)
            timer = StageTimer()

            with self.assertRaises(RuntimeError):
                with cache.stage(timer, "compile", "key-1") as run:
                    run.value = {"half": "written"}
                    raise RuntimeError("compile blew up")

            self.assertIsNone(cache.cache.get("compile", "key-1"))
            self.assertNotIn("compile", cache.state.stages)

    def test_stage_timings_are_recorded_for_reused_stages_too(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cache = self._cache(Path(raw))
            timer = StageTimer()
            for _ in range(2):
                with cache.stage(timer, "accept", "key-1") as run:
                    if not run.reused:
                        run.value = {"ok": True}
            self.assertEqual(len(timer.stages), 2)
            for entry in timer.stages:
                self.assertIn("duration_s", entry)


class ReportedReasonTests(unittest.TestCase):
    """The operator-facing line must say why a stage ran, not just how long."""

    def _cache(self, root: Path) -> PrepareCache:
        return PrepareCache(
            StageCache(root / "cache.json"), PrepareState.load(root / "PREPARE_STATE.json")
        )

    def _formatted(self, timer: StageTimer, stage: str) -> str:
        """The most recent line for `stage`, which is the decision under test."""
        matches = [line for line in timer.format().splitlines() if line.strip().startswith(stage)]
        if not matches:
            raise AssertionError(f"{stage} missing from {timer.format()!r}")
        return matches[-1]

    def test_a_changed_input_is_named_as_the_reason(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cache = self._cache(Path(raw))
            timer = StageTimer()
            for key in ("key-1", "key-2"):
                with cache.stage(timer, "compile", key) as run:
                    if not run.reused:
                        run.value = {"ok": True}

            self.assertIn("input_changed", self._formatted(timer, "compile"))

    def test_a_reused_stage_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cache = self._cache(Path(raw))
            timer = StageTimer()
            for _ in range(2):
                with cache.stage(timer, "accept", "key-1") as run:
                    if not run.reused:
                        run.value = {"ok": True}

            self.assertIn("(reused)", self._formatted(timer, "accept"))

    def test_a_stage_outside_the_cache_still_gets_a_reason(self) -> None:
        timer = StageTimer()
        with timer.stage("arm"):
            pass

        self.assertIn("(always runs)", self._formatted(timer, "arm"))


def _decision(reuse: bool, reason: str):
    from pe_prepare_state import Decision  # type: ignore[import-not-found]

    return Decision(reuse, reason)


if __name__ == "__main__":
    unittest.main()
