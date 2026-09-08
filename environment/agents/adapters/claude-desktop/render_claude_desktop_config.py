#!/usr/bin/env python3
"""Render Claude Desktop's MCP config from the governed master inventory.

Claude Desktop reads ``claude_desktop_config.json`` and, unlike Claude Code,
expands no ``${VAR}`` references, accepts only stdio servers (``command`` /
``args`` / ``env``), and needs absolute commands because a GUI app does not
inherit a login shell's PATH. This renderer is the third consumer of
``environment/mcp/master.mcp.json`` (after the Cursor and Claude Code CLI
symlinks) and applies those constraints instead of symlinking:

- stdio servers are copied with ``command`` resolved to an absolute path;
- ``url`` servers are skipped (Desktop adds remote servers through its
  Connectors UI), and each skip is named in the receipt;
- ``env`` values referencing ``${VAR}`` are resolved from the invoking shell
  **only for non-credential variables**; a server whose env names a token, key,
  secret, or password is skipped, because the Desktop file is secret-free by
  policy (rules/61, ADR-016) and a wrapper script is the right carrier;
- servers Desktop users added themselves are preserved byte for byte;
- the ``l9-graphite-memory`` entry is never authored here. When
  ``L9_MEMORY_INTERPRETER`` names an interpreter carrying the pinned package,
  the memory package's own configurator writes it
  (``l9-memory client cursor install --path <desktop config>``), so the same
  atomic, digest-backed, secret-free entry lands on every surface.

Usage:
    render_claude_desktop_config.py [--check] [--json] [--path FILE] [--master FILE]
                                    [--memory-interpreter PY | --skip-memory] [--verify]
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
MASTER_PATH = REPO_ROOT / "environment" / "mcp" / "master.mcp.json"
MEMORY_KEY = "l9-graphite-memory"
ENV_MEMORY_INTERPRETER = "L9_MEMORY_INTERPRETER"

_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")
_SECRET_MARKERS = ("TOKEN", "KEY", "SECRET", "PASSWORD", "CREDENTIAL", "DSN")
# Claude Code-only keys that Desktop does not understand.
_DROP_KEYS = frozenset({"type", "timeout", "alwaysLoad", "headers", "url"})


def default_desktop_config_path() -> Path:
    system = platform.system()
    if system == "Darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    if system == "Windows":
        return (
            Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
            / "Claude"
            / "claude_desktop_config.json"
        )
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def _is_secret_var(name: str) -> bool:
    upper = name.upper()
    return any(marker in upper for marker in _SECRET_MARKERS)


def _expand(value: str, environ: dict[str, str]) -> tuple[str | None, str | None]:
    """Expand ``${VAR}`` / ``${VAR:-default}``. Returns (text, skip_reason)."""

    reason: str | None = None

    def _sub(match: re.Match[str]) -> str:
        nonlocal reason
        name, default = match.group(1), match.group(2)
        if _is_secret_var(name):
            reason = reason or f"credential-bearing env {name}: Desktop config is secret-free"
            return ""
        resolved = environ.get(name, "").strip()
        if resolved:
            return resolved
        if default is not None:
            return default
        reason = reason or f"requires {name} (unset in the invoking shell)"
        return ""

    text = _VAR_RE.sub(_sub, value)
    return (None, reason) if reason else (text, None)


def render_server(
    name: str, spec: Any, environ: dict[str, str]
) -> tuple[dict[str, Any] | None, str | None]:
    """Return (desktop entry, None) or (None, skip reason)."""

    if not isinstance(spec, dict):
        return None, "not an object"
    if name == MEMORY_KEY:
        return None, "owned by the memory package configurator"
    if spec.get("url") or spec.get("type") in {"http", "sse", "streamable-http", "ws"}:
        return None, "remote server: add it through Claude Desktop → Settings → Connectors"
    command = spec.get("command")
    if not isinstance(command, str) or not command.strip():
        return None, "no stdio command"
    expanded_command, reason = _expand(command, environ)
    if reason or expanded_command is None:
        return None, reason
    absolute = (
        expanded_command if Path(expanded_command).is_absolute() else shutil.which(expanded_command)
    )
    if not absolute:
        return (
            None,
            f"command {expanded_command!r} not found on PATH (Desktop needs an absolute path)",
        )
    args: list[str] = []
    for item in spec.get("args") or []:
        expanded_arg, reason = _expand(str(item), environ)
        if reason or expanded_arg is None:
            return None, reason
        args.append(expanded_arg)
    entry: dict[str, Any] = {"command": absolute, "args": args}
    env_block = spec.get("env")
    if isinstance(env_block, dict) and env_block:
        rendered_env: dict[str, str] = {}
        for key, raw in env_block.items():
            if _is_secret_var(str(key)):
                return None, f"credential-bearing env {key}: Desktop config is secret-free"
            expanded_env, reason = _expand(str(raw), environ)
            if reason or expanded_env is None:
                return None, reason
            rendered_env[str(key)] = expanded_env
        entry["env"] = rendered_env
    for key, value in spec.items():
        if key.startswith("_") or key in _DROP_KEYS or key in entry or key in {"args", "env"}:
            continue
        entry[key] = value
    return entry, None


def render_config(
    master: dict[str, Any],
    existing: dict[str, Any] | None,
    environ: dict[str, str],
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    """Merge managed servers over the existing Desktop config.

    Returns (config, skipped-by-name, preserved unmanaged keys). Keys the
    master does not define — including the memory entry — are preserved.
    """

    managed = master.get("mcpServers") or {}
    # Start from the existing order so a re-render after the memory configurator
    # appended its key (or after Desktop added one) is byte-stable: managed
    # entries are refreshed in place, new ones appended, skipped ones removed.
    servers: dict[str, Any] = dict((existing or {}).get("mcpServers") or {})
    preserved = sorted(name for name in servers if name not in managed or name == MEMORY_KEY)
    skipped: dict[str, str] = {}
    for name, spec in managed.items():
        entry, reason = render_server(name, spec, environ)
        if entry is None:
            skipped[name] = reason or "skipped"
            if name not in preserved:
                servers.pop(name, None)
            continue
        servers[name] = entry
    config = dict(existing or {})
    config["mcpServers"] = servers
    return config, skipped, preserved


def _atomic_write(path: Path, payload: str) -> str | None:
    backup: str | None = None
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_path = path.with_name(f"{path.name}.backup.{stamp}")
        shutil.copy2(path, backup_path)
        backup = str(backup_path)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return backup


def _memory_entry(
    *,
    config_path: Path,
    interpreter: str | None,
    check: bool,
    verify: bool,
    runner: Any = subprocess.run,
) -> dict[str, Any]:
    """Delegate the memory entry to the package's own configurator."""

    if not interpreter:
        return {"status": "skipped", "reason": f"{ENV_MEMORY_INTERPRETER} unset"}
    interpreter_path = Path(interpreter).expanduser()
    cli = interpreter_path.parent / "l9-memory"
    if not interpreter_path.is_file():
        return {"status": "unavailable", "reason": f"interpreter not found: {interpreter_path}"}
    if not cli.is_file():
        return {
            "status": "unavailable",
            "reason": f"l9-memory not installed beside {interpreter_path}",
        }
    argv = [
        str(cli),
        "client",
        "cursor",
        "install",
        "--path",
        str(config_path),
        "--interpreter",
        str(interpreter_path),
    ]
    if check:
        argv.append("--dry-run")
    result = runner(argv, capture_output=True, text=True, check=False, timeout=60)
    receipt: dict[str, Any] = {"argv": argv, "exit_code": result.returncode}
    try:
        receipt["install"] = json.loads(result.stdout)
    except ValueError:
        receipt["install"] = {
            "raw": (result.stdout or "")[:400],
            "stderr": (result.stderr or "")[-400:],
        }
    receipt["status"] = "installed" if result.returncode == 0 else "blocked"
    if verify and result.returncode == 0 and not check:
        probe = runner(
            [
                str(cli),
                "client",
                "cursor",
                "verify",
                "--path",
                str(config_path),
                "--interpreter",
                str(interpreter_path),
                "--timeout",
                "60",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=90,
        )
        try:
            receipt["verify"] = json.loads(probe.stdout)
        except ValueError:
            receipt["verify"] = {"raw": (probe.stdout or "")[:400]}
        receipt["verify_exit_code"] = probe.returncode
        if probe.returncode != 0:
            receipt["status"] = "installed_unverified"
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--master", default=str(MASTER_PATH))
    parser.add_argument("--path", default=None, help="Desktop config (default: platform location)")
    parser.add_argument("--check", action="store_true", help="report drift; write nothing")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--memory-interpreter", default=os.environ.get(ENV_MEMORY_INTERPRETER))
    parser.add_argument("--skip-memory", action="store_true")
    parser.add_argument(
        "--verify", action="store_true", help="run the memory MCP handshake after install"
    )
    args = parser.parse_args(argv)

    target = Path(args.path).expanduser() if args.path else default_desktop_config_path()
    master = json.loads(Path(args.master).read_text(encoding="utf-8"))
    existing: dict[str, Any] | None = None
    if target.is_file():
        try:
            decoded = json.loads(target.read_text(encoding="utf-8"))
            existing = decoded if isinstance(decoded, dict) else None
        except (OSError, json.JSONDecodeError):
            existing = None
    config, skipped, preserved = render_config(master, existing, dict(os.environ))
    payload = json.dumps(config, indent=2) + "\n"
    current = target.read_text(encoding="utf-8") if target.is_file() else None
    changed = current != payload

    receipt: dict[str, Any] = {
        "path": str(target),
        "master": str(args.master),
        "mode": "check" if args.check else "install",
        "managed_servers": sorted(
            name for name in (master.get("mcpServers") or {}) if name not in skipped
        ),
        "skipped": skipped,
        "preserved_unmanaged": preserved,
        "changed": changed,
    }
    status = "unchanged"
    if changed and args.check:
        status = "drift"
    elif changed:
        receipt["backup"] = _atomic_write(target, payload)
        status = "written"
    receipt["status"] = status
    if not args.skip_memory:
        receipt["memory"] = _memory_entry(
            config_path=target,
            interpreter=args.memory_interpreter,
            check=args.check,
            verify=args.verify,
        )

    if args.json:
        sys.stdout.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(f"claude desktop mcp [{receipt['mode']}]: {status} -> {target}\n")
        for name in receipt["managed_servers"]:
            sys.stdout.write(f"  managed    {name}\n")
        for name, reason in sorted(skipped.items()):
            sys.stdout.write(f"  skipped    {name}: {reason}\n")
        for name in preserved:
            sys.stdout.write(f"  preserved  {name}\n")
        memory = receipt.get("memory")
        if memory:
            sys.stdout.write(f"  memory     {memory.get('status')}: {memory.get('reason', '')}\n")
    if status == "drift":
        return 2
    memory_status = (receipt.get("memory") or {}).get("status")
    return 1 if memory_status == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
