"""Per-machine Cursor MCP instantiation (campaign stage C7).

``~/.cursor/mcp.json`` used to be a symlink to the governed master inventory
(``environment/mcp/master.mcp.json``). That shape had two defects the
realignment removes: the master carried the legacy direct-provider front door
(``graphiti-memory``), and a symlink cannot receive the memory package's own
managed entry — ``l9-memory client cursor install`` refuses a symlinked target
by design (memory ADR-064). This module renders a **real per-machine file**:

- every non-memory server the master declares is copied verbatim (Cursor
  expands nothing, and the master already carries only ``${VAR}`` references
  for credentials, so no secret value is ever written here);
- servers the user added on this machine are preserved;
- the legacy ``graphiti-memory`` key is dropped wherever it appears;
- the ``l9-graphite-memory`` entry is never authored here. It is delegated to
  the memory package configurator against the runtime this checkout is bound
  to (``ops/memory/runtime_binding.py``), and proven by the package's own
  ``client cursor verify --path`` handshake when asked.

The receipt written beside the session state carries ``authority: none``:
it records what was rendered and what memory reported, never a claim that
memory is healthy.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ops.memory.runtime_binding import RuntimeBinding, resolve_runtime_binding

_REPO_ROOT = Path(__file__).resolve().parents[2]
MASTER_PATH = _REPO_ROOT / "environment" / "mcp" / "master.mcp.json"

MEMORY_KEY = "l9-graphite-memory"
#: Legacy direct-provider front door keys, removed from every rendered file.
LEGACY_KEYS = frozenset({"graphiti-memory"})
RECEIPT_SCHEMA = "cursor.mcp-instantiation/v1"
ENV_MEMORY_INTERPRETER = "L9_MEMORY_INTERPRETER"

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


def default_cursor_config_path() -> Path:
    return Path.home() / ".cursor" / "mcp.json"


def default_receipt_path() -> Path:
    return Path.home() / ".l9" / "memory" / "cursor-mcp-instantiation.json"


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_machine_config(
    master: Mapping[str, Any], existing: Mapping[str, Any] | None
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    """Return ``(config, dropped-by-name, preserved unmanaged keys)``.

    Managed servers take the master's definition (private ``_``-prefixed keys
    stripped). The memory key and the legacy front door are never rendered from
    the master; the memory key is preserved when the configurator already
    wrote it, the legacy key is removed unconditionally.
    """

    managed = {
        str(name): spec
        for name, spec in (master.get("mcpServers") or {}).items()
        if isinstance(spec, dict)
    }
    servers: dict[str, Any] = dict((existing or {}).get("mcpServers") or {})
    dropped: dict[str, str] = {}
    for name, spec in managed.items():
        if name == MEMORY_KEY:
            dropped[name] = "owned by the memory package configurator"
            continue
        if name in LEGACY_KEYS:
            dropped[name] = "legacy direct-provider front door retired (stage C7)"
            servers.pop(name, None)
            continue
        servers[name] = {key: value for key, value in spec.items() if not str(key).startswith("_")}
    for name in sorted(LEGACY_KEYS):
        if name in servers:
            servers.pop(name)
            dropped[name] = "legacy direct-provider front door retired (stage C7)"
    preserved = sorted(name for name in servers if name not in managed or name == MEMORY_KEY)
    config: dict[str, Any] = {
        key: value
        for key, value in (existing or {}).items()
        if key != "mcpServers" and not str(key).startswith("_")
    }
    config["mcpServers"] = servers
    return config, dropped, preserved


def read_existing(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Decode the current file (through a symlink) and name the link target."""

    link_target = os.readlink(path) if path.is_symlink() else None
    if not path.is_file():
        return None, link_target
    try:
        decoded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, link_target
    return (decoded if isinstance(decoded, dict) else None), link_target


def _atomic_write(path: Path, payload: str) -> dict[str, str | None]:
    """Replace ``path`` with a real file; back up a regular file, unlink a symlink."""

    evidence: dict[str, str | None] = {"backup": None, "replaced_symlink": None}
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        evidence["replaced_symlink"] = os.readlink(path)
        path.unlink()
    elif path.is_file():
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_path = path.with_name(f"{path.name}.backup.{stamp}")
        shutil.copy2(path, backup_path)
        evidence["backup"] = str(backup_path)
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
    return evidence


# ---------------------------------------------------------------------------
# Memory entry: delegated, never authored
# ---------------------------------------------------------------------------


def _decode(stdout: str, stderr: str) -> dict[str, Any]:
    try:
        decoded = json.loads(stdout)
    except ValueError:
        return {"raw": (stdout or "")[:400], "stderr": (stderr or "")[-400:]}
    return decoded if isinstance(decoded, dict) else {"raw": str(decoded)[:400]}


def memory_entry(
    *,
    config_path: Path,
    binding: RuntimeBinding | None,
    interpreter: str | None,
    check: bool,
    verify: bool,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    """Install (and optionally verify) the managed entry through the package.

    The interpreter is the bound runtime's unless an explicit one is given; a
    checkout with no binding and no explicit interpreter installs nothing —
    an entry naming a guessed Python would be a claim memory never made.
    """

    if interpreter:
        interpreter_path = Path(interpreter).expanduser()
        cli = interpreter_path.parent / "l9-memory"
        source = "explicit"
    elif binding is not None and binding.ok and binding.interpreter and binding.memory_cli:
        interpreter_path = Path(binding.interpreter)
        cli = Path(binding.memory_cli)
        source = f"runtime_binding:{binding.runtime_mode}"
    else:
        reasons = list(binding.reasons) if binding is not None else []
        return {
            "status": "skipped",
            "reason": "no bound memory runtime and no --interpreter",
            "binding_reasons": reasons,
        }
    if not interpreter_path.is_file():
        return {"status": "unavailable", "reason": f"interpreter not found: {interpreter_path}"}
    if not cli.is_file():
        return {"status": "unavailable", "reason": f"l9-memory not installed beside {cli.parent}"}
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
    receipt: dict[str, Any] = {
        "interpreter_source": source,
        "argv": argv,
        "exit_code": result.returncode,
        "install": _decode(result.stdout, result.stderr),
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
        receipt["verify"] = _decode(probe.stdout, probe.stderr)
        receipt["verify_exit_code"] = probe.returncode
        receipt["status"] = "verified" if probe.returncode == 0 else "installed_unverified"
    return receipt


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def instantiate(
    *,
    path: Path,
    master_path: Path = MASTER_PATH,
    check: bool = False,
    interpreter: str | None = None,
    skip_memory: bool = False,
    verify: bool = False,
    binding_resolver: Callable[[], RuntimeBinding] | None = None,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    master = json.loads(master_path.read_text(encoding="utf-8"))
    existing, link_target = read_existing(path)
    config, dropped, preserved = render_machine_config(master, existing)
    payload = json.dumps(config, indent=2) + "\n"
    current = path.read_text(encoding="utf-8") if path.is_file() else None
    # A symlink is never "current": the file must become a real file even
    # when its bytes would not change, or the configurator can never write it.
    changed = current != payload or link_target is not None

    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "authority": "none",
        "path": str(path),
        "master": str(master_path),
        "mode": "check" if check else "install",
        "was_symlink_to": link_target,
        "managed_servers": sorted(
            name for name in (master.get("mcpServers") or {}) if name not in dropped
        ),
        "dropped": dropped,
        "preserved_unmanaged": preserved,
        "changed": changed,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    status = "unchanged"
    if changed and check:
        status = "drift"
    elif changed:
        receipt.update(_atomic_write(path, payload))
        status = "written"
    receipt["status"] = status

    if skip_memory:
        receipt["memory"] = {"status": "skipped", "reason": "--skip-memory"}
    else:
        binding: RuntimeBinding | None = None
        if not interpreter:
            resolver = binding_resolver or resolve_runtime_binding
            # Broad by design: an unresolved binding is reported, never raised
            # out of a config renderer.
            # nosemgrep: l9.baseline.python.broad-except
            try:
                binding = resolver()
            except Exception as exc:  # noqa: BLE001
                receipt["binding_error"] = f"{type(exc).__name__}: {exc}"
        receipt["binding_status"] = binding.status if binding is not None else None
        if check and link_target is not None:
            receipt["memory"] = {
                "status": "skipped",
                "reason": "target is still a symlink; install replaces it first",
            }
        else:
            receipt["memory"] = memory_entry(
                config_path=path,
                binding=binding,
                interpreter=interpreter,
                check=check,
                verify=verify,
                runner=runner,
            )
    return receipt


def write_receipt(receipt: Mapping[str, Any], receipt_path: Path) -> Path:
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(dict(receipt), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt_path


def exit_code(receipt: Mapping[str, Any]) -> int:
    if receipt.get("status") == "drift":
        return 2
    memory_status = str((receipt.get("memory") or {}).get("status") or "")
    return 1 if memory_status == "blocked" else 0


def _render_text(receipt: Mapping[str, Any]) -> str:
    lines = [f"cursor mcp [{receipt['mode']}]: {receipt['status']} -> {receipt['path']}"]
    if receipt.get("was_symlink_to"):
        lines.append(f"  symlink    was -> {receipt['was_symlink_to']}")
    for name in receipt.get("managed_servers") or []:
        lines.append(f"  managed    {name}")
    for name, reason in sorted((receipt.get("dropped") or {}).items()):
        lines.append(f"  dropped    {name}: {reason}")
    for name in receipt.get("preserved_unmanaged") or []:
        lines.append(f"  preserved  {name}")
    memory = receipt.get("memory") or {}
    lines.append(f"  memory     {memory.get('status')}: {memory.get('reason', '')}".rstrip(": "))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--path", default=None, help="Cursor MCP config (default: ~/.cursor/mcp.json)"
    )
    parser.add_argument("--master", default=str(MASTER_PATH))
    parser.add_argument("--check", action="store_true", help="report drift; write nothing")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--interpreter",
        default=os.environ.get(ENV_MEMORY_INTERPRETER) or None,
        help="Python carrying the pinned memory package (default: the bound runtime)",
    )
    parser.add_argument("--skip-memory", action="store_true")
    parser.add_argument("--verify", action="store_true", help="run the memory MCP handshake")
    parser.add_argument("--receipt", default=None, help="receipt path (default under ~/.l9/memory)")
    parser.add_argument("--no-receipt", action="store_true")
    args = parser.parse_args(argv)

    target = Path(args.path).expanduser() if args.path else default_cursor_config_path()
    receipt = instantiate(
        path=target,
        master_path=Path(args.master).expanduser(),
        check=args.check,
        interpreter=args.interpreter,
        skip_memory=args.skip_memory,
        verify=args.verify,
    )
    if not args.no_receipt:
        receipt["receipt_path"] = str(
            write_receipt(
                receipt, Path(args.receipt).expanduser() if args.receipt else default_receipt_path()
            )
        )
    if args.json:
        sys.stdout.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(_render_text(receipt))
    return exit_code(receipt)


__all__ = [
    "LEGACY_KEYS",
    "MEMORY_KEY",
    "RECEIPT_SCHEMA",
    "default_cursor_config_path",
    "default_receipt_path",
    "exit_code",
    "instantiate",
    "main",
    "memory_entry",
    "read_existing",
    "render_machine_config",
    "write_receipt",
]


if __name__ == "__main__":
    raise SystemExit(main())
