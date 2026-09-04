#!/usr/bin/env python3
"""Blocking cross-peer semantic parity gate (program-execution.replan.v1).

Usage:
    run_parity_gate.py <repository_root> --workspace <pec-workspace>

Exits 0 when the parity report is PASS, 1 when BLOCKED. The report itself is
printed as JSON on stdout either way.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# APPEND, never insert(0): Program Execution needs its own PE-exclusive
# packages here, but `scripts` is a top-level name it SHARES with the
# repository root. Prepending would hand PE's `scripts/` that name for the
# whole process. See peer_execution.imports.pe_script.
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from peer_execution.golden_vectors import run_parity_gate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Blocking cross-peer replan parity gate")
    parser.add_argument("repository_root", type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args(argv)
    report = run_parity_gate(args.repository_root, args.workspace)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
