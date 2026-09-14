#!/usr/bin/env python3
"""Emit the ADR-0031 agent MCP assertion env for ONE principal (no human secret).

Formats written to a 0600 file (never to stdout):
  shell (default) — export KEY='value' lines, consumed by
                    ops/memory/export_agent_assertion_env.sh
  json            — one object, consumed by the sessionStart env merge

stdout is the absolute path of that file, or empty when assertion is skipped.
It is never a log of secrets: the helper refuses a terminal, emits only the
launching principal's signing key and grant entry, and never emits the human
door.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

# Allow running as a script from anywhere: the repository root is the import
# root for ``ops.memory``. Inserted before the import inside main(), so no
# module-level import has to follow a path mutation.
_ROOT = Path(__file__).resolve().parents[2]

HUMAN_PRINCIPAL = "human"


def _shell_escape(value: str) -> str:
    """Escape a value for use inside single-quoted shell strings."""
    return value.replace("'", "'\"'\"'")


def _default_tokens_map() -> Path:
    return Path(
        os.environ.get(
            "L9_MEMORY_SECRET_MAP",
            str(Path.home() / ".config/l9-memory/agent_tokens.local.json"),
        )
    )


def _default_grants_map() -> Path:
    return Path(
        os.environ.get(
            "L9_MEMORY_GRANTS_MAP",
            str(Path.home() / ".config/l9-memory/agent_grants.json"),
        )
    )


def _runtime_dir() -> str | None:
    runtime = os.environ.get("XDG_RUNTIME_DIR", "").strip()
    if runtime and Path(runtime).is_dir() and os.access(runtime, os.W_OK):
        return runtime
    return None


def _write_secret_file(payload: str) -> Path:
    """Write payload to a 0600 tempfile. stdout later gets only this path."""
    fd, name = tempfile.mkstemp(
        prefix="l9-agent-assertion-",
        suffix=".tmp",
        dir=_runtime_dir(),
        text=True,
    )
    try:
        os.fchmod(fd, 0o600)
        data = payload if payload.endswith("\n") else f"{payload}\n"
        os.write(fd, data.encode("utf-8"))
    except Exception:
        os.close(fd)
        Path(name).unlink(missing_ok=True)
        raise
    else:
        os.close(fd)
    return Path(name)


def main(argv: list[str] | None = None) -> int:
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    from ops.memory.agent_assertion import ENV_HUMAN_DOOR_SECRET, env_from_local_secret_map

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--agent-id", default=os.environ.get("L9_MEMORY_AGENT_ID", "cursor"))
    ap.add_argument(
        "--format",
        choices=("shell", "json"),
        default="shell",
        help="shell export lines (default) or JSON object",
    )
    ap.add_argument(
        "--secret-map",
        dest="tokens_map",
        type=Path,
        default=_default_tokens_map(),
        help="local agent token store (agents door secret + per-agent signing keys)",
    )
    ap.add_argument(
        "--grants-map",
        type=Path,
        default=_default_grants_map(),
        help="registry-rendered grants map (environment/agents/tools/render_principals.py)",
    )
    args = ap.parse_args(argv)
    if args.agent_id == HUMAN_PRINCIPAL:
        print("refusing to export human private entrance into agent env", file=sys.stderr)
        return 2
    if not args.tokens_map.is_file() or not args.grants_map.is_file():
        if args.format != "json":
            print(
                "# assertion skipped: local agent token store or grants map not found "
                "(memory-blind cold start OK)",
                file=sys.stderr,
            )
        return 0
    if sys.stdout.isatty():
        print(
            "refusing to write assertion env to a terminal: pipe it to a consumer "
            "that reads the emitted path (--format shell or --format json)",
            file=sys.stderr,
        )
        return 2
    env = env_from_local_secret_map(args.agent_id, args.tokens_map, args.grants_map)
    # Structural guarantee from the library; kept as a hard refusal here too.
    env.pop(ENV_HUMAN_DOOR_SECRET, None)
    if args.format == "json":
        payload = json.dumps(env, separators=(",", ":"))
    else:
        payload = "\n".join(f"export {key}='{_shell_escape(value)}'" for key, value in env.items())
    path = _write_secret_file(payload)
    print(str(path.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
