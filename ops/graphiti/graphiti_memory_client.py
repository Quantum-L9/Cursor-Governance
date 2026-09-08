#!/usr/bin/env python3
"""Tombstone — the direct Graphiti provider client was retired at stage C11.

Cursor-Governance no longer knows how to call Graphiti. Every memory
operation crosses the canonical ``l9-graphite-memory`` control plane through
``ops/memory`` (INV-03); Graphiti receives records only as a projection memory
owns. This file stays at its historical path so that an un-migrated caller
fails loudly at a named location instead of silently doing nothing.

Replacement (same operator vocabulary, same interpreter discipline)::

    python -m ops.memory.cli health|resolve|search|write|hydrate|conflicts|readiness

Authority: CANONICAL_LAW §8.2, ADR-0030, ``ops/memory/README.md``.
"""

from __future__ import annotations

import sys

RETIRED_AT_STAGE = "C11"
REPLACEMENT = "python -m ops.memory.cli"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    requested = args[0] if args else "<no command>"
    sys.stderr.write(
        "graphiti_memory_client.py is retired (memory realignment stage "
        f"{RETIRED_AT_STAGE}); it performs no memory operation.\n"
        f"  requested: {requested}\n"
        f"  use:       {REPLACEMENT} {requested if args else '<op>'}\n"
        "  authority: CANONICAL_LAW §8.2 / ADR-0030 / ops/memory/README.md\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
