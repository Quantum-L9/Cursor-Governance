#!/usr/bin/env python3
"""Validate static activation and rejection contract coverage."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    cases = json.loads((ROOT / "assets" / "activation-cases.json").read_text(encoding="utf-8"))
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
    failures: list[str] = []
    for case in cases:
        if not isinstance(case, dict) or "required_text" not in case:
            failures.append(f"malformed activation case: {case!r}"); continue
        required = str(case["required_text"]).lower()
        if required not in text:
            failures.append(f"{case.get('id')} missing {case.get('expected')} signal: {case['required_text']}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(f"PASS: {len(cases)} static activation and rejection contract cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
