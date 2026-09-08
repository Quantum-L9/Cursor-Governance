#!/usr/bin/env python3
"""Fail-closed remediation-plan schema check. Stdlib only.

Blocks edits until every ingested finding has ownership + disposition +
evidence + root_cause. Does not invent those values.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

from protocol import validate_plan


def _fail(msg: str) -> NoReturn:
    print(f"FAIL: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _fail(f"missing {path}")
    except json.JSONDecodeError as exc:
        _fail(f"{path} is not JSON: {exc}")


def _findings_list(doc: Any) -> list[dict[str, Any]] | None:
    if doc is None:
        return None
    if isinstance(doc, list):
        return [item for item in doc if isinstance(item, dict)]
    if isinstance(doc, dict):
        items = doc.get("findings")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    _fail("findings file must be a list or an object with findings[]")
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a remediator plan ledger.")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--findings", help="ingest_signals.py snapshot (optional)")
    args = parser.parse_args(argv)

    plan = _load(Path(args.plan))
    findings = _findings_list(_load(Path(args.findings))) if args.findings else None
    errors = validate_plan(plan, findings)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr, flush=True)
        return 1
    print("PASS: remediation plan", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
