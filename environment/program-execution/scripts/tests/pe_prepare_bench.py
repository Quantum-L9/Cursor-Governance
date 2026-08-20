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


def _stage_timings(workspace: Path) -> tuple[dict[str, float], set[str], dict[str, str]]:
    """Per-stage seconds, which stages reported a hit, and why the rest ran.

    Reads `duration_s`, the `cached` flag, and the recorded decision written by
    `pe_timing.StageTimer`. A benchmark that reports a repeat cost without
    saying which stage refused to be reused, and why, cannot be acted on.
    Returns empty results when the campaign recorded nothing.
    """
    timings = workspace / "runtime/TIMINGS.json"
    if not timings.is_file():
        return {}, set(), {}
    try:
        doc = json.loads(timings.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, set(), {}
    out: dict[str, float] = {}
    cached: set[str] = set()
    reasons: dict[str, str] = {}
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
        else:
            reasons[str(stage)] = str((entry.get("detail") or {}).get("reason") or "always_runs")
    return out, cached, reasons


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


def bench(task_count: int, *, repeat: int = 3) -> dict[str, Any]:
    """Prepare a fresh N-task campaign, then prepare it again `repeat`-1 times.

    Three runs rather than two, because the second run is not yet steady state:
    the first run's admission mutates the blueprint after validation has already
    been recorded against the pre-admission content, so run two re-validates
    once and run three is the repeat cost an operator actually lives with.
    """
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

        result: dict[str, Any] = {"tasks": task_count, "runs": []}
        env = {"L9_CAMPAIGN_UNTIL_DEBUG": "1"}
        with unittest.mock.patch.dict("os.environ", {**os.environ, **env}):
            workspace = l9 / "programs" / str(seed["campaign_id"])
            for index in range(repeat):
                # A failure on a repeat run is itself the measurement, so record
                # it rather than letting it abort the whole benchmark.
                try:
                    report, elapsed = _prepare(
                        mod, entry, root=root, l9=l9, primary=tmp / "primary"
                    )
                except Exception as exc:  # noqa: BLE001 - the failure IS the finding
                    result["runs"].append(
                        {"run": index + 1, "failed": f"{type(exc).__name__}: {exc}"}
                    )
                    break
                stages, cached, reasons = _stage_timings(workspace)
                result["runs"].append(
                    {
                        "run": index + 1,
                        "seconds": round(elapsed, 3),
                        "stages_completed": list(report.stages_completed),
                        "stage_seconds": {k: round(v, 3) for k, v in stages.items()},
                        "cached_stages": sorted(cached),
                        "recompute_reasons": reasons,
                    }
                )
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
    parser.add_argument(
        "--repeat",
        type=int,
        default=3,
        help="prepare invocations per campaign, first is cold (default: 3)",
    )
    parser.add_argument("--json", action="store_true", help="emit the raw JSON report")
    args = parser.parse_args(argv)

    report: dict[str, Any] = {"prepare_last_stage": PREPARE_LAST_STAGE, "campaigns": []}
    for count in args.tasks:
        outcome = bench(count, repeat=args.repeat)
        report["campaigns"].append(outcome)
        if args.json:
            continue
        print(f"\n=== {count} tasks ===")
        cold_seconds = None
        for run in outcome["runs"]:
            label = "cold" if run["run"] == 1 else f"run {run['run']}"
            if "failed" in run:
                print(f"{label}: FAILED  {run['failed']}")
                continue
            if cold_seconds is None:
                cold_seconds = run["seconds"]
                print(f"{label}: {run['seconds']:>8.3f}s")
                for stage, seconds in sorted(run["stage_seconds"].items(), key=lambda kv: -kv[1]):
                    print(f"        {stage:<22} {seconds:>8.3f}s")
                continue
            speedup = cold_seconds / run["seconds"] if run["seconds"] else float("inf")
            print(f"{label}: {run['seconds']:>8.3f}s  ({speedup:.2f}x vs cold)")
            recomputed = sorted(set(run["stage_seconds"]) - set(run["cached_stages"]))
            if not recomputed:
                print("        recomputed: NONE")
            for stage in recomputed:
                reason = run.get("recompute_reasons", {}).get(stage, "unknown")
                print(f"        recomputed {stage:<22} {reason}")

    if args.json:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
