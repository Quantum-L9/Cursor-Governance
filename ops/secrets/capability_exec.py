#!/usr/bin/env python3
"""Run one allowlisted command with one vault secret in ITS environment only.

Some paid tools (Semgrep Pro via `semgrep ci --dry-run`) read their credential
from their own environment and cannot be driven in-process like the Context7
bridge. This broker is the governed way to run them on a model-controlled
surface:

* The command is an entry in capability-exec.json: argv is fixed, and only the
  entry's declared {placeholders} are substituted, each by a named validator.
  A caller cannot add arguments, choose the executable, or pick the secret.
* The secret is bound in-process by capability_bind (Infisical, as this
  surface's machine identity) and placed only in the child's environment,
  which is built from nothing (PATH, HOME, LANG + the entry's fixed env).
  It never enters this process's environment, argv, a file or a log.
* Output that echoes the secret is withheld: stdout/stderr are replaced by a
  literal notice and any declared output file containing it is truncated.
* Diagnostics are literals; nothing derived from the secret or the bind result
  is printed.

Residual, stated rather than hidden: while the child runs, its environment is
readable by the same uid through /proc/<pid>/environ — the same exposure class
as the vault bridge's in-process key. AGENTS.md CI_PARITY_HOSTED_CLAUDE_V1.

Usage:
    capability_exec.py --list
    capability_exec.py run semgrep-pro --cwd DIR --param output=PATH \
        --param baseline=SHA --param repo=owner/name
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import capability_bind as cb  # noqa: E402

REGISTRY = HERE / "capability-exec.json"
SCHEMA = "l9.capability-exec.v1"
CACHE_ROOT = Path(os.path.expanduser(os.environ.get("L9_CI_PARITY_CACHE") or "~/.cache/l9-ci-parity"))
SAFE_PATH = ":".join(
    str(p)
    for p in (
        Path.home() / ".local" / "bin",
        Path("/usr/local/bin"),
        Path("/usr/bin"),
        Path("/bin"),
    )
)
WITHHELD = "capability_exec: output withheld — it contained the credential"
_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


class ExecError(ValueError):
    """The request does not match a registered entry."""


def _validate(kind: str, value: str) -> str:
    if kind == "git_sha":
        if not re.fullmatch(r"[0-9a-f]{7,40}", value):
            raise ExecError("git_sha must be 7-40 lowercase hex")
        return value
    if kind == "repo_slug":
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
            raise ExecError("repo_slug must be owner/name")
        return value
    if kind in ("cache_path", "cache_dir"):
        resolved = Path(value).expanduser().resolve()
        root = CACHE_ROOT.resolve()
        if resolved != root and root not in resolved.parents:
            raise ExecError(f"{kind} must be under the ci-parity cache")
        return str(resolved)
    raise ExecError(f"unknown validator {kind!r}")


def load_registry(path: Path = REGISTRY) -> dict[str, dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ExecError(f"{path.name}: schema must be {SCHEMA}")
    entries = data.get("entries")
    if not isinstance(entries, dict):
        raise ExecError(f"{path.name}: entries missing")
    return entries


def _substitute(text: str, params: dict[str, str]) -> str:
    return _PLACEHOLDER.sub(lambda m: params[m.group(1)], text)


@dataclass(frozen=True)
class Plan:
    argv: list[str]
    env: dict[str, str]
    cwd: str
    outputs: list[Path]
    timeout: int
    secret_name: str
    env_name: str


def plan(name: str, params: dict[str, str], cwd: str, registry: dict[str, dict[str, object]]) -> Plan:
    """Validate a request against its entry. Binds nothing."""
    entry = registry.get(name)
    if not isinstance(entry, dict):
        raise ExecError("no such capability-exec entry")
    declared: dict[str, str] = dict(entry.get("params") or {})  # type: ignore[arg-type]
    extra = set(params) - set(declared)
    missing = set(declared) - set(params)
    if extra or missing:
        raise ExecError("params must be exactly the entry's declared placeholders")
    clean = {key: _validate(kind, params[key]) for key, kind in declared.items()}
    argv = [_substitute(str(a), clean) for a in entry["argv"]]  # type: ignore[union-attr]
    env = {
        "PATH": SAFE_PATH,
        "HOME": str(Path.home()),
        "LANG": os.environ.get("LANG") or "C.UTF-8",
    }
    for key, value in dict(entry.get("fixed_env") or {}).items():  # type: ignore[arg-type]
        env[str(key)] = _substitute(str(value), clean)
    return Plan(
        argv=argv,
        env=env,
        cwd=_validate(str(entry.get("cwd") or "cache_dir"), cwd),
        outputs=[Path(clean[o]) for o in entry.get("outputs") or []],  # type: ignore[union-attr]
        timeout=int(entry.get("timeout_seconds") or 600),  # type: ignore[arg-type]
        secret_name=str(entry["secret"]),
        env_name=str(entry["env"]),
    )


@dataclass(frozen=True)
class Result:
    status: str  # ok | failed | unbound | withheld | timeout
    returncode: int
    stdout: str
    stderr: str


def execute(p: Plan, *, bind: object = None) -> Result:
    binder = bind or cb.bind
    secret = binder(p.secret_name)  # type: ignore[operator]
    if not secret:
        return Result("unbound", 0, "", "")
    env = dict(p.env)
    env[p.env_name] = secret
    try:
        proc = subprocess.run(
            p.argv, cwd=p.cwd, env=env, capture_output=True, text=True, timeout=p.timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return Result("timeout", 124, "", "")
    except OSError:
        return Result("failed", 127, "", "capability_exec: executable not found")
    leaked = secret in proc.stdout or secret in proc.stderr
    for output in p.outputs:
        try:
            if output.is_file() and secret.encode() in output.read_bytes():
                output.write_bytes(b"")
                leaked = True
        except OSError:
            continue
    if leaked:
        return Result("withheld", proc.returncode, WITHHELD, WITHHELD)
    return Result("ok" if proc.returncode in (0, 1) else "failed", proc.returncode, proc.stdout, proc.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list")
    run_p = sub.add_parser("run")
    run_p.add_argument("name")
    run_p.add_argument("--cwd", required=True)
    run_p.add_argument("--param", action="append", default=[])
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)
    registry = load_registry()
    if args.list or args.command == "list":
        for name in sorted(registry):
            print(name)
        return 0
    if args.command != "run":
        parser.print_help()
        return 2
    params = dict(item.split("=", 1) for item in args.param if "=" in item)
    try:
        p = plan(args.name, params, args.cwd, registry)
    except ExecError as exc:
        print(f"capability_exec: refused — {exc}", file=sys.stderr)
        return 2
    result = execute(p)
    if result.status == "unbound":
        source = cb.literal_source(cb.bind_status(p.secret_name)["source"])
        name = next((n for n in cb.allowed_names() if n == p.secret_name), "the secret")
        print(f"capability_exec: {name} is not bound (source={source})", file=sys.stderr)
        return 3
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    print(f"capability_exec: status={result.status}", file=sys.stderr)
    return result.returncode if result.status in ("ok", "failed") else 4


if __name__ == "__main__":
    raise SystemExit(main())
