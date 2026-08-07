#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from route_reasoning import route


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    cases = json.loads((root / "fixtures" / "router_cases.json").read_text(encoding="utf-8"))
    failures = []
    for case in cases:
        actual = route(case["request"])
        expected = case["expected"]
        for key, value in expected.items():
            if key == "proof_contains":
                missing = [item for item in value if item not in actual["proof_obligations"]]
                if missing:
                    failures.append(f"{case['id']}: missing proofs {missing}")
            elif actual.get(key) != value:
                failures.append(f"{case['id']}: {key} expected {value!r}, got {actual.get(key)!r}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    activated = sum(1 for case in cases if route(case["request"])["activate"])
    print(json.dumps({"status": "PASS", "cases": len(cases), "activated": activated, "rejected": len(cases) - activated}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
