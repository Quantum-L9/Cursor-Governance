#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def classify(risk: str, evidence: str) -> str:
    risk = (risk or "low").lower()
    evidence = (evidence or "sufficient").lower()
    if risk in {"high", "irreversible"} or evidence in {"conflicting", "absent"}:
        return "deep"
    if risk == "medium" or evidence == "partial":
        return "standard"
    return "standard"


def omitted_gates(_depth: str) -> list[str]:
    # Escalate-only: never omit.
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Escalate-only plan depth router")
    parser.add_argument("--risk", default="low")
    parser.add_argument("--evidence", default="sufficient")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        cases = json.loads((ROOT / "assets" / "route-cases.json").read_text(encoding="utf-8"))[
            "cases"
        ]
        failed = 0
        for case in cases:
            got = classify(case["risk"], case["evidence"])
            if got != case["expect_depth"]:
                print(
                    f"FAIL: {case['id']} expected {case['expect_depth']} got {got}", file=sys.stderr
                )
                failed += 1
            if omitted_gates(got):
                print(f"FAIL: {case['id']} omitted gates {omitted_gates(got)}", file=sys.stderr)
                failed += 1
        if failed:
            return 1
        print(f"PASS: route_plan self-test ({len(cases)} cases)")
        return 0

    depth = classify(args.risk, args.evidence)
    payload = {
        "depth": depth,
        "omit_gates": omitted_gates(depth),
        "note": "baseline gates always apply; depth only escalates",
    }
    if args.json:
        print(json.dumps(payload))
    else:
        print(f"depth={depth}")
        print("omit_gates=[]")
        print(payload["note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
