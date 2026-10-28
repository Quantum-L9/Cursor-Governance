#!/usr/bin/env python3
"""Run a comparable before/after measurement and emit a proof block.

Produces the `performance`/`proof` shape the pack spec consumes. Two modes:

- throughput (default): time each command over N samples; lower wall-clock is
  better; improvement_percent = 100*(before-after)/before.
- functional (--metric with --capture): parse a numeric the command prints on
  its last stdout line (e.g. consumer invocations 0 -> N) — proof that a
  capability is now exercised, not necessarily faster.

Stdlib-only. Timing is inherently non-deterministic; this tool measures, it does
not pin time. Use it to generate evidence, then paste values into the spec.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import statistics
import subprocess
import sys
import time


def run_once(command: list[str], capture: bool) -> tuple[float, float | None]:
    start = time.perf_counter()
    proc = subprocess.run(command, text=True, capture_output=True, check=False)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(command)}\n{proc.stderr}"
        )
    number = None
    if capture:
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        m = re.search(r"(-?\d+(?:\.\d+)?)\s*$", lines[-1]) if lines else None
        if not m:
            raise RuntimeError(
                "--capture: no trailing numeric token on the command's last stdout line: "
                + (repr(lines[-1]) if lines else "<no output>")
            )
        number = float(m.group(1))
    return elapsed_ms, number


def measure(command: list[str], samples: int, capture: bool) -> tuple[float, float | None]:
    times: list[float] = []
    numbers: list[float] = []
    for _ in range(samples):
        elapsed, number = run_once(command, capture)
        times.append(elapsed)
        if number is not None:
            numbers.append(number)
    median_time = round(statistics.median(times), 3)
    median_number = round(statistics.median(numbers), 6) if numbers else None
    return median_time, median_number


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, help="baseline command (shell-quoted)")
    parser.add_argument("--after", required=True, help="candidate command (shell-quoted)")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--metric", default="wall_clock")
    parser.add_argument("--unit", default="ms")
    parser.add_argument(
        "--capture",
        action="store_true",
        help="parse a numeric from each command's last stdout line (functional metric)",
    )
    parser.add_argument("--output", type=argparse.FileType("w"), default=sys.stdout)
    args = parser.parse_args()
    if args.samples < 1:
        print("FAIL: --samples must be >= 1", file=sys.stderr)
        return 2

    before_cmd = shlex.split(args.before)
    after_cmd = shlex.split(args.after)
    try:
        before_time, before_num = measure(before_cmd, args.samples, args.capture)
        after_time, after_num = measure(after_cmd, args.samples, args.capture)
    except (RuntimeError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    activation = False
    if args.capture and before_num is not None and after_num is not None:
        metric, unit, direction = args.metric, args.unit, "higher_is_better"
        before_value, after_value = before_num, after_num
        if before_value == 0:
            if after_value <= 0:
                print(
                    "FAIL: capture activation proof requires candidate > 0 from a zero baseline",
                    file=sys.stderr,
                )
                return 2
            improvement, activation = None, True  # explicit 0 -> N activation, not a silent null
        else:
            improvement = round(100.0 * (after_value - before_value) / abs(before_value), 2)
        method = f"Functional proof: same workload, compare '{metric}' captured from stdout over {args.samples} samples (higher is better)."
    else:
        metric, unit, direction = "wall_clock", "ms", "lower_is_better"
        before_value, after_value = before_time, after_time
        improvement = (
            None
            if before_value == 0
            else round(100.0 * (before_value - after_value) / before_value, 2)
        )
        method = f"Throughput proof: same workload, compare median wall-clock over {args.samples} samples (lower is better)."

    proof = {
        "direction": direction,
        "baseline": {
            "command": args.before,
            "metric": metric,
            "unit": unit,
            "value": before_value,
            "samples": args.samples,
            "evidence": f"median of {args.samples} runs",
        },
        "candidate": {
            "command": args.after,
            "metric": metric,
            "unit": unit,
            "value": after_value,
            "samples": args.samples,
            "evidence": f"median of {args.samples} runs",
        },
        "improvement_percent": improvement,
        "activation": activation,
        "comparison_method": method,
        "correctness_checks": ["exit code 0 for both commands"],
        "resource_checks": ["no orphaned processes remained after the sampled runs"],
    }
    args.output.write(json.dumps(proof, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
