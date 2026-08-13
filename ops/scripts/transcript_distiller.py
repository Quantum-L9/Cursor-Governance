#!/usr/bin/env python3
"""Transcript Distiller — Graphiti queue worker front door (C1 path retired).

RETIRED (2026-08-12): The former C1 ``save_memory`` / Dropbox LaunchAgent
pipeline is tombstoned. SessionEnd enqueues redacted excerpts to S3; the
canonical batch processor is:

    python -m ops.graphiti.distill_queue.worker

This module remains at the historical path (CANONICAL_LAW §9) as a thin
CLI wrapper so cron docs and ``run_distiller.sh`` keep working.

Environment (same as GHA worker):
    MEMORY_DISTILL_S3_BUCKET   required
    OPENAI_API_KEY             or resolve AWS SM l9/OPENAI_API_KEY
    GRAPHITI_MCP_URL           default https://memory.quantumaipartners.com/graphiti/mcp
    GRAPHITI_MCP_TOKEN         required for live ingest

One-time LaunchAgent unload:
    launchctl bootout "gui/$(id -u)/com.l9.transcript-distiller"
    rm -f ~/Library/LaunchAgents/com.l9.transcript-distiller.plist
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Graphiti distill queue worker (C1/Dropbox path retired). "
            "Prefer: python -m ops.graphiti.distill_queue.worker"
        )
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=20,
        help="Max pending S3 jobs to process",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Distill without Graphiti writes / S3 done move",
    )
    # Accept legacy flags so old LaunchAgent plists fail loudly with guidance
    # instead of FileNotFoundError on removed C1 knobs.
    parser.add_argument("--source", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--file", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--since", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--until", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--l9-root", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--with-llm", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--force-legacy-c1", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.force_legacy_c1:
        print(
            "ERROR: C1 save_memory sink is retired. "
            "Use ops.graphiti.distill_queue.worker → Graphiti only.",
            file=sys.stderr,
        )
        return 2
    if args.source or args.file:
        print(
            "WARN: --source/--file Dropbox/flat-txt mode retired; "
            "processing S3 distill-queue pending jobs instead.",
            file=sys.stderr,
        )

    from ops.graphiti.distill_queue.worker import main as worker_main

    worker_argv: list[str] = ["--max-jobs", str(args.max_jobs)]
    if args.dry_run:
        worker_argv.append("--dry-run")
    return int(worker_main(worker_argv))


if __name__ == "__main__":
    raise SystemExit(main())
