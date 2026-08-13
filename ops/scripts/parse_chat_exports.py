#!/usr/bin/env python3
"""RETIRED 2026-08-13 — sqlite/hash indexer for hourly chat dumps.

Replacement: ops.graphiti.hydration.archive_transcript (words + timestamps → S3).
See ops/scripts/RETIRED_export_chats_and_learning_processor.md
"""

import sys


def main() -> None:
    print(
        "RETIRED: parse_chat_exports.py — closed chats archive to S3 "
        "(python -m ops.graphiti.hydration.archive_transcript)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
