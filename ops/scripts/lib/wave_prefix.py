#!/usr/bin/env python3
"""Prefix stdin lines with ``[wave:NAME] `` and tee the raw bytes to a log.

Used by ``run_pr_gate.sh`` so the reader wave streams live instead of sitting
silent until every job finishes. The log file is unprefixed so a failure recap
and ``last-gate.log`` stay grep-stable.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def prefix_stream(name: str, log_path: Path) -> int:
    prefix = f"[wave:{name}] "
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        while True:
            line = sys.stdin.readline()
            if line == "":
                break
            log.write(line)
            log.flush()
            sys.stdout.write(prefix + line)
            sys.stdout.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--log", required=True)
    args = parser.parse_args(argv)
    return prefix_stream(args.name, Path(args.log))


if __name__ == "__main__":
    raise SystemExit(main())
