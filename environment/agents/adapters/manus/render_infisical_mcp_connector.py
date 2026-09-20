#!/usr/bin/env python3
"""Render a local Custom MCP draft for the native Manus Infisical adapter.

The only secret input is a mode-0600 file containing the one Universal Auth
client secret. The renderer neither prints the value nor places it in command
arguments. The generated connector draft is mode 0600 and should be removed as
soon as Manus has accepted it.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path

ADAPTER_ROOT = Path(__file__).resolve().parent


def _read_secret_file(path: Path) -> str:
    file_mode = stat.S_IMODE(path.stat().st_mode)
    if file_mode & 0o077:
        raise ValueError("client secret file must not be readable by group or others")
    value = path.read_text(encoding="utf-8").strip()
    if not value or "\n" in value:
        raise ValueError("client secret file must contain one non-empty line")
    return value


def _write_private_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    payload_text = json.dumps(payload, indent=2) + "\n"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(payload_text)
    except Exception:
        if fd >= 0:
            os.close(fd)
        temporary.unlink(missing_ok=True)
        raise
    temporary.replace(path)
    os.chmod(path, 0o600)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--client-id", required=True, help="Infisical Universal Auth client ID")
    parser.add_argument("--client-secret-file", required=True, type=Path)
    parser.add_argument("--project-id", required=True, help="Infisical project ID")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--environment", default="prod")
    parser.add_argument("--secret-path", default="/")
    parser.add_argument("--site-url", default="https://app.infisical.com")
    args = parser.parse_args(argv)

    secret = _read_secret_file(args.client_secret_file)
    launcher = (ADAPTER_ROOT / "serve_infisical_mcp.sh").resolve()
    if not launcher.is_file():
        raise ValueError(f"missing launcher: {launcher}")
    payload = {
        "mcpServers": {
            "l9-manus-infisical": {
                "command": "bash",
                "args": [str(launcher)],
                "env": {
                    "L9_MANUS_INFISICAL_CLIENT_ID": args.client_id,
                    "L9_MANUS_INFISICAL_CLIENT_SECRET": secret,
                    "L9_MANUS_INFISICAL_PROJECT_ID": args.project_id,
                    "L9_MANUS_INFISICAL_ENV": args.environment,
                    "L9_MANUS_INFISICAL_SECRET_PATH": args.secret_path,
                    "L9_MANUS_INFISICAL_SITE_URL": args.site_url,
                },
            }
        }
    }
    _write_private_json(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
