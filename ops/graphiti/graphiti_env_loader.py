"""Machine-level Graphiti environment loader.

Repo clones never carry graphiti secrets. Configure once per Mac:
  ~/.cursor/graphiti.env          — optional overrides (no secrets required if using keychain)
  ~/.cursor/secrets/graphiti.env  — optional secrets overlay (gitignored globally)
  macOS Keychain                  — graphiti-mcp-token, graphiti-c1-ssh-key

Safe defaults live in graphiti.env.defaults (bash) and DEFAULTS below (python).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

DEFAULTS: dict[str, str] = {
    "GRAPHITI_MEMORY_ENABLED": "1",
    "GRAPHITI_WRITE_GATES": "0",
    "GRAPHITI_MCP_URL": "http://127.0.0.1:8100/mcp/",
    "GRAPHITI_SSH_HOST": "46.62.243.82",
    "GRAPHITI_SSH_USER": "root",
    "GRAPHITI_SSH_KEY": str(Path.home() / ".ssh" / "Hetzner-C1-nopass"),
    "GRAPHITI_SSH_KEYCHAIN_SERVICE": "graphiti-c1-ssh-key",
    "GRAPHITI_TUNNEL_LOCAL_PORT": "8100",
    "GRAPHITI_TUNNEL_REMOTE_PORT": "8100",
    "GRAPHITI_TUNNEL_AUTOSTART": "1",
    "MEMORY_TOKEN_BUDGET": "400",
    "MEMORY_RATE_LIMIT_MIN": "10",
    "MEMORY_RATE_LIMIT_HR": "200",
    "GRAPHITI_TELEMETRY_ENABLED": "false",
}

ENV_FILES: tuple[Path, ...] = (
    Path.home() / ".cursor" / "graphiti.env",
    Path.home() / ".cursor" / "secrets" / "graphiti.env",
)

KEYCHAIN_SERVICES: dict[str, str] = {
    "GRAPHITI_MCP_TOKEN": "graphiti-mcp-token",
}


def _load_env_file(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if val.startswith("$HOME"):
            val = val.replace("$HOME", str(Path.home()), 1)
        os.environ.setdefault(key, val)


def _keychain_get(service: str) -> str | None:
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-w"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            token = result.stdout.strip()
            return token or None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def load_graphiti_env() -> None:
    """Load Graphiti config: defaults → machine files → keychain."""
    for key, value in DEFAULTS.items():
        os.environ.setdefault(key, value)
    for path in ENV_FILES:
        if path.is_file():
            _load_env_file(path)
    for env_key, service in KEYCHAIN_SERVICES.items():
        if not os.environ.get(env_key, "").strip():
            secret = _keychain_get(service)
            if secret:
                os.environ[env_key] = secret


def env_status() -> dict[str, str]:
    """Non-secret status for doctor/init scripts."""
    load_graphiti_env()
    return {
        "machine_env": str(Path.home() / ".cursor" / "graphiti.env"),
        "machine_env_exists": str((Path.home() / ".cursor" / "graphiti.env").is_file()),
        "secrets_overlay_exists": str(
            (Path.home() / ".cursor" / "secrets" / "graphiti.env").is_file()
        ),
        "mcp_token_set": str(bool(os.environ.get("GRAPHITI_MCP_TOKEN", "").strip())),
        "ssh_key_exists": str(Path(os.environ.get("GRAPHITI_SSH_KEY", "")).expanduser().is_file()),
        "memory_enabled": os.environ.get("GRAPHITI_MEMORY_ENABLED", "1"),
        "mcp_url": os.environ.get("GRAPHITI_MCP_URL", ""),
    }
