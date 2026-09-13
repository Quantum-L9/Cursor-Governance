#!/usr/bin/env python3
"""Print ADR-0031 agent MCP assertion env (no human secret).

Formats:
  shell (default) — export KEY='value' lines for eval
  json — object suitable for sessionStart env merge
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Allow running as python -m ops.memory.print_agent_assertion_env from gov root
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ops.memory.agent_assertion import env_from_local_secret_map  # noqa: E402


def _shell_escape(value: str) -> str:
    """Escape a value for use inside single-quoted shell strings."""
    return value.replace("'", "'\"'\"'")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent-id", default=os.environ.get("L9_MEMORY_AGENT_ID", "cursor"))
    ap.add_argument(
        "--format",
        choices=("shell", "json"),
        default="shell",
        help="shell export lines (default) or JSON object",
    )
    ap.add_argument(
        "--secret-map",
        type=Path,
        default=Path(
            os.environ.get(
                "L9_MEMORY_SECRET_MAP",
                str(Path.home() / ".config/l9-memory/agent_tokens.local.json"),
            )
        ),
    )
    ap.add_argument(
        "--grants-map",
        type=Path,
        default=Path(
            os.environ.get(
                "L9_MEMORY_GRANTS_MAP",
                str(Path.home() / ".config/l9-memory/agent_grants.json"),
            )
        ),
    )
    args = ap.parse_args()
    if args.agent_id == "human":
        print("refusing to export human private entrance into agent env", file=sys.stderr)
        return 2
    if not args.secret_map.is_file() or not args.grants_map.is_file():
        if args.format == "json":
            print("{}")
        else:
            print(
                f"# assertion skipped: missing {args.secret_map} or {args.grants_map}",
                file=sys.stderr,
            )
        return 0
    env = env_from_local_secret_map(args.agent_id, args.secret_map, args.grants_map)
    # Hard refuse human private entrance leakage.
    env.pop("L9_MEMORY_HUMAN_DOOR_SECRET", None)
    if args.format == "json":
        print(json.dumps(env, separators=(",", ":")))
        return 0
    for key, value in env.items():
        print(f"export {key}='{_shell_escape(value)}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
