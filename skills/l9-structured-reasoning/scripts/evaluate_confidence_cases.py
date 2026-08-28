#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from validate_ledger import validate


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    cases = json.loads((root / "fixtures" / "confidence_cases.json").read_text(encoding="utf-8"))[
        "cases"
    ]
    failures = []
    for case in cases:
        if case.get("path"):
            data = json.loads((root / case["path"]).read_text(encoding="utf-8"))
        else:
            data = case["ledger"]
        errors = validate(data)
        passed = not errors
        expect_pass = case["expect"] == "pass"
        if passed != expect_pass:
            failures.append(
                f"{case['id']}: expected {case['expect']}, got "
                f"{'pass' if passed else 'fail'} {errors}"
            )
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(f"PASS: {len(cases)} confidence cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
