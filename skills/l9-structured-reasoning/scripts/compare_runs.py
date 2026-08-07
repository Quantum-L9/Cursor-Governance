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
    baseline = summarize(json.loads(Path(args.baseline).read_text(encoding="utf-8")))
    candidate = summarize(json.loads(Path(args.candidate).read_text(encoding="utf-8")))
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
