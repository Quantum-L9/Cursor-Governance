#!/usr/bin/env python3
"""Prepare-path benchmark: what does it cost to prepare a campaign twice?

PE-FAST-002 is a performance contract, so it needs a number to hold itself to.
This harness drives the public `run_campaign` entry point against a synthetic
campaign of N tasks, stops at the end of preparation, and then does it again
against the same `l9_root`. The second run is the one that matters: preparing an
already-prepared campaign is the operation an operator performs dozens of times
a day, and it is the operation the contract wants to be near-free.

Run it directly; it is a measurement tool, not a test:

    .venv/bin/python environment/program-execution/scripts/tests/pe_prepare_bench.py --tasks 2 7

Stage numbers come from the campaign's own `runtime/TIMINGS.json`, so the
benchmark reports what PE recorded rather than a second opinion about it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
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
    _dump,
    _git_init,
    _host_repo,
    _load,
    _stack_ok,
)

# Preparation ends at `arm`: everything up to and including the point where the
# campaign is ready to hand a task to a worker. `execute` is deliberately out of
# scope -- it runs real workers, and its cost is the worker's, not prepare's.
PREPARE_LAST_STAGE = "arm"


def _seed(task_count: int, *, campaign_id: str = "demo-activate-v1") -> dict[str, Any]:
    """A Ready seed with `task_count` linearly dependent tasks.

    The chain is linear because that is the shape that makes lazy materialization
    observable: with `TASK-00n` depending on `TASK-00(n-1)`, exactly one task is
    ever on the runnable frontier, so any prepare cost proportional to the total
    task count is by definition work that did not need doing yet.
    """
    tasks = []
    for index in range(1, task_count + 1):
        task_id = f"TASK-{index:03d}"
        task: dict[str, Any] = {
            "id": task_id,
            "title": f"Task {index}",
            "objective": f"Do the {index}th unit of declared work.",
            "actions": ["edit_only_declared_paths"],
            "consumers": ["pec"],
            "entrypoints": ["make campaign"],
            "validation": [{"command": "python3 -c 'print(0)'"}],
            "nugget_id": f"nugget-task-{index:03d}",
            "acceptance": [
                {
                    "id": f"AC-{index:03d}",
                    "statement": f"Task {index} produced its declared output.",
                    "required_evidence_types": ["runtime_behavior"],
                }
            ],
        }
        if index > 1:
            task["depends_on"] = [f"TASK-{index - 1:03d}"]
        tasks.append(task)
    return {
        "campaign_id": campaign_id,
        "title": "Prepare Benchmark",
        "objective": "Measure what preparing this campaign costs.",
        "plan_status": "Ready",
        "tasks": tasks,
    }


def _stage_timings(workspace: Path) -> tuple[dict[str, float], set[str]]:
    """Per-stage seconds as PE recorded them, plus which stages reported a hit.

    Reads `duration_s` and the `cached` flag written by `pe_timing.StageTimer`.
    Returns ({}, set()) when the campaign recorded nothing.
    """
    timings = workspace / "runtime/TIMINGS.json"
    if not timings.is_file():
        return {}, set()
    try:
        doc = json.loads(timings.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, set()
    out: dict[str, float] = {}
    cached: set[str] = set()
    for entry in doc.get("stages") or []:
        stage = entry.get("stage")
        seconds = entry.get("duration_s")
        if stage is None or seconds is None:
            continue
        # A resumed campaign appends a second span for the same stage; the sum
        # is the honest total cost of that stage across the run.
        out[str(stage)] = out.get(str(stage), 0.0) + float(seconds)
        if entry.get("cached"):
            cached.add(str(stage))
    return out, cached


def _prepare(mod: Any, entry: Path, *, root: Path, l9: Path, primary: Path) -> tuple[Any, float]:
    started = time.monotonic()
    report = mod.run_campaign(
        entry,
        until=PREPARE_LAST_STAGE,
        primary=primary,
        repo_root=root,
        l9_root=l9,
        fast=True,
        hooks=mod.Hooks(context7_stack=_stack_ok),
    )
    return report, time.monotonic() - started


def bench(task_count: int) -> dict[str, Any]:
    """Prepare a fresh N-task campaign, then prepare it again. Report both."""
    mod = _load(f"run_campaign_bench_{task_count}", SCRIPT)
    activate = _load(f"compile_activation_bench_{task_count}", ACTIVATE)

    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        root = _host_repo(tmp / "host")
        seed = _seed(task_count)
        source = activate.build_source(seed, stamp="2026-01-01T00:00:00Z")
        # build_source drops declared dependencies; restore the linear chain so
        # the runnable frontier stays at one task.
        by_id = {str(task["id"]): task for task in source["tasks"]}
        for index in range(2, task_count + 1):
            by_id[f"TASK-{index:03d}"]["depends_on"] = [f"TASK-{index - 1:03d}"]

        entry = root / "CAMPAIGN_SOURCE.yaml"
        _dump(entry, source)

        l9 = tmp / "l9"
        target = l9 / "program-worktrees" / str(seed["campaign_id"])
        target.mkdir(parents=True)
        _git_init(target)

        result: dict[str, Any] = {"tasks": task_count}
        env = {"L9_CAMPAIGN_UNTIL_DEBUG": "1"}
        with unittest.mock.patch.dict("os.environ", {**os.environ, **env}):
            cold_report, cold_elapsed = _prepare(
                mod, entry, root=root, l9=l9, primary=tmp / "primary"
            )
            workspace = l9 / "programs" / str(seed["campaign_id"])
            cold_stages, cold_cached = _stage_timings(workspace)
            result["cold"] = {
                "seconds": round(cold_elapsed, 3),
                "stages_completed": list(cold_report.stages_completed),
                "stage_seconds": {k: round(v, 3) for k, v in cold_stages.items()},
                "cached_stages": sorted(cold_cached),
            }

            # The warm run is the contract's real subject: same seed, same l9
            # root, nothing changed. Any failure here is itself the finding, so
            # record it rather than letting it abort the benchmark.
            try:
                warm_report, warm_elapsed = _prepare(
                    mod, entry, root=root, l9=l9, primary=tmp / "primary"
                )
                warm_stages, warm_cached = _stage_timings(workspace)
                result["warm"] = {
                    "seconds": round(warm_elapsed, 3),
                    "stages_completed": list(warm_report.stages_completed),
                    "stage_seconds": {k: round(v, 3) for k, v in warm_stages.items()},
                    "cached_stages": sorted(warm_cached),
                }
            except Exception as exc:  # noqa: BLE001 - the failure IS the measurement
                result["warm"] = {
                    "failed": f"{type(exc).__name__}: {exc}",
                }
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tasks",
        type=int,
        nargs="+",
        default=[2, 7],
        help="task counts to benchmark (default: 2 7)",
    )
    parser.add_argument("--json", action="store_true", help="emit the raw JSON report")
    args = parser.parse_args(argv)

    report = {"prepare_last_stage": PREPARE_LAST_STAGE, "runs": []}
    for count in args.tasks:
        outcome = bench(count)
        report["runs"].append(outcome)
        if args.json:
            continue
        cold = outcome["cold"]
        warm = outcome["warm"]
        print(f"\n=== {count} tasks ===")
        print(f"cold: {cold['seconds']:>8.3f}s  stages={','.join(cold['stages_completed'])}")
        for stage, seconds in sorted(cold["stage_seconds"].items(), key=lambda kv: -kv[1]):
            print(f"        {stage:<22} {seconds:>8.3f}s")
        if "failed" in warm:
            print(f"warm: FAILED  {warm['failed']}")
        else:
            speedup = cold["seconds"] / warm["seconds"] if warm["seconds"] else float("inf")
            print(f"warm: {warm['seconds']:>8.3f}s  ({speedup:.2f}x vs cold)")
            hits = ",".join(warm["cached_stages"]) or "NONE"
            print(f"        cache hits on warm run: {hits}")

    if args.json:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
