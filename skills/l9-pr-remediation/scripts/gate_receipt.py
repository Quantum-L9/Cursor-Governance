#!/usr/bin/env python3
"""Fail-closed Gate A–F latch. Stdlib only.

Replaces the checklist half of validation-gates.md. Missing or invalid
artifacts STOP. Does not invent the artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from protocol import validate_gate


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _fail(f"missing {path}")
    except json.JSONDecodeError as exc:
        _fail(f"{path} is not JSON: {exc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate one remediator gate receipt.")
    parser.add_argument("--gate", required=True, choices=("A", "B", "C", "D", "E", "F"))
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--plan", help="required for Gate B")
    parser.add_argument("--findings", help="optional ingest snapshot for Gate B")
    args = parser.parse_args(argv)

    receipt = _load(Path(args.receipt))
    if not isinstance(receipt, dict):
        _fail("receipt is not an object")
    plan = _load(Path(args.plan)) if args.plan else None
    findings = None
    if args.findings:
        snap = _load(Path(args.findings))
        if isinstance(snap, dict):
            findings = snap.get("findings")
        elif isinstance(snap, list):
            findings = snap
    if args.gate == "B" and plan is None:
        _fail("Gate B requires --plan")
    errors = validate_gate(args.gate, receipt, plan=plan, findings=findings)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr, flush=True)
        return 1
    print(f"PASS: gate {args.gate}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
