#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

QUALITY_FIELDS = [
    "correctness",
    "evidence_fidelity",
    "option_quality",
    "actionability",
    "calibration",
]


def _read_under_cwd(candidate: str, *, label: str) -> str:
    """Read a caller-named file, refusing anything outside the working tree.

    The path arrives from argv. Without containment this CLI will happily read
    and surface the contents of any file the process can reach, so an operator
    (or an agent) invoking it with a traversal path turns an analysis helper into
    a file-disclosure tool. The inputs it is meant to read are workspace
    artifacts, so confinement costs no supported use.
    """
    workspace = Path.cwd().resolve()
    try:
        resolved = Path(candidate).resolve().relative_to(workspace)
    except ValueError as error:
        raise SystemExit(f"{label} must stay inside {workspace}: {candidate!r}") from error
    return (workspace / resolved).read_text(encoding="utf-8")


def summarize(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("run file must contain at least one row")
    n = len(rows)
    out = {field: sum(float(row[field]) for row in rows) / n for field in QUALITY_FIELDS}
    out["token_count"] = sum(int(row["token_count"]) for row in rows) / n
    out["tool_calls"] = sum(int(row["tool_calls"]) for row in rows) / n
    out["unsupported_claims"] = sum(int(row["unsupported_claims"]) for row in rows)
    out["quality_score"] = sum(out[field] for field in QUALITY_FIELDS) / len(QUALITY_FIELDS)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline")
    parser.add_argument("candidate")
    args = parser.parse_args()
    baseline = summarize(json.loads(_read_under_cwd(args.baseline, label="baseline")))
    candidate = summarize(json.loads(_read_under_cwd(args.candidate, label="candidate")))
    result = {
        "baseline": baseline,
        "candidate": candidate,
        "quality_delta": candidate["quality_score"] - baseline["quality_score"],
        "token_reduction_fraction": 1 - candidate["token_count"] / baseline["token_count"]
        if baseline["token_count"]
        else 0,
        "tool_call_reduction_fraction": 1 - candidate["tool_calls"] / baseline["tool_calls"]
        if baseline["tool_calls"]
        else 0,
        "acceptance": {
            "no_correctness_regression": candidate["correctness"] >= baseline["correctness"],
            "no_unsupported_claim_regression": candidate["unsupported_claims"]
            <= baseline["unsupported_claims"],
            "quality_improved": candidate["quality_score"] > baseline["quality_score"],
        },
    }
    result["pass"] = all(result["acceptance"].values())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
