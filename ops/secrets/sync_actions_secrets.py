#!/usr/bin/env python3
"""Mirror Infisical (cursor-governance) secrets into GitHub Actions repo secrets.

OPERATOR-ONLY. Hosted agent sessions cannot write Actions secrets (the session
proxy returns 403 on ``repos/*/actions/secrets*``); run this on a machine whose
``gh`` may write repository secrets.

The plan is data: ``actions-secret-sync.json`` beside this file, a list of
``{repo, secret, vault_name}`` plus an optional ``sdk_token`` block. Every
``vault_name`` must be in ``root_env_keys`` of
``infisical-cursor-governance.yaml``; the plan fails to load otherwise.

Value handling:

* Values are bound in-process through ``capability_bind`` (Infisical, as this
  surface's machine identity). They are never exported, printed or written.
* A value reaches ``gh secret set NAME --repo R`` on stdin only, never argv.
* ``gh`` output is scrubbed of every bound value before any of it is printed.
* ``--dry-run`` binds and writes nothing.
* ``SDK_TOKEN`` is opt-in (``--with-sdk-token``). It is the Infisical
  ``GITHUB_TOKEN`` (never the shell's ``GH_TOKEN`` / ``GITHUB_TOKEN``) and is set
  only after that PAT proves it can read ``must_read``.

Exit codes: 0 every planned set succeeded (or would, under ``--dry-run``);
1 any skip or failure; 2 the plan did not load.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import capability_bind as cb  # noqa: E402

try:  # pragma: no cover - import guard mirrors capability_bind
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

SCHEMA = "l9.actions-secret-sync.v1"
DEFAULT_PLAN = HERE / "actions-secret-sync.json"
DEFAULT_INVENTORY = HERE / "infisical-cursor-governance.yaml"
SDK_SECRET_NAME = "SDK_TOKEN"
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SECRET_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SHELL_GH_VARS = ("GITHUB_TOKEN", "GH_TOKEN")
_REDACTED = "<redacted>"


class PlanError(ValueError):
    """The plan file is malformed or names a vault key outside ``root_env_keys``."""


@dataclass(frozen=True)
class Entry:
    repo: str
    secret: str
    vault_name: str


@dataclass(frozen=True)
class SdkToken:
    repos: tuple[str, ...]
    vault_name: str
    must_read: str


@dataclass(frozen=True)
class Plan:
    entries: tuple[Entry, ...]
    sdk_token: SdkToken | None = None
    vault_names: frozenset[str] = field(default_factory=frozenset)


def root_env_keys(inventory: Path = DEFAULT_INVENTORY) -> frozenset[str]:
    if yaml is None:
        raise PlanError("PyYAML is required to read the Infisical inventory")
    raw = yaml.safe_load(inventory.read_text(encoding="utf-8")) or {}
    keys = raw.get("root_env_keys") if isinstance(raw, dict) else None
    if not isinstance(keys, list) or not keys:
        raise PlanError(f"{inventory}: root_env_keys missing or empty")
    return frozenset(str(k) for k in keys if k)


def _require_str(obj: dict, key: str, where: str, pattern: re.Pattern[str]) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not pattern.match(value):
        raise PlanError(f"{where}: {key!r} missing or malformed")
    return value


def _check_vault(name: str, allowed: frozenset[str], where: str) -> None:
    if name not in allowed:
        raise PlanError(
            f"{where}: vault_name {name!r} is not in root_env_keys of the Infisical inventory"
        )


def load_plan(path: Path = DEFAULT_PLAN, inventory: Path = DEFAULT_INVENTORY) -> Plan:
    allowed = root_env_keys(inventory)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlanError(f"{path}: unreadable plan ({type(exc).__name__})") from exc
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        raise PlanError(f"{path}: schema must be {SCHEMA!r}")
    items = raw.get("secrets")
    if not isinstance(items, list):
        raise PlanError(f"{path}: 'secrets' must be a list")
    entries: list[Entry] = []
    seen: set[tuple[str, str]] = set()
    for i, item in enumerate(items):
        where = f"{path.name}: secrets[{i}]"
        if not isinstance(item, dict):
            raise PlanError(f"{where}: must be an object")
        entry = Entry(
            repo=_require_str(item, "repo", where, _REPO_RE),
            secret=_require_str(item, "secret", where, _SECRET_RE),
            vault_name=_require_str(item, "vault_name", where, _SECRET_RE),
        )
        _check_vault(entry.vault_name, allowed, where)
        if (entry.repo, entry.secret) in seen:
            raise PlanError(f"{where}: duplicate {entry.repo} {entry.secret}")
        seen.add((entry.repo, entry.secret))
        entries.append(entry)

    sdk: SdkToken | None = None
    block = raw.get("sdk_token")
    if block is not None:
        where = f"{path.name}: sdk_token"
        if not isinstance(block, dict):
            raise PlanError(f"{where}: must be an object")
        repos = block.get("repos")
        if not isinstance(repos, list) or not all(
            isinstance(r, str) and _REPO_RE.match(r) for r in repos
        ):
            raise PlanError(f"{where}: 'repos' must be a list of owner/name")
        vault_name = _require_str(block, "vault_name", where, _SECRET_RE)
        _check_vault(vault_name, allowed, where)
        for repo in repos:
            if (repo, SDK_SECRET_NAME) in seen:
                raise PlanError(f"{where}: {repo} {SDK_SECRET_NAME} also in 'secrets'")
        sdk = SdkToken(
            repos=tuple(repos),
            vault_name=vault_name,
            must_read=_require_str(block, "must_read", where, _REPO_RE),
        )
    names = {e.vault_name for e in entries} | ({sdk.vault_name} if sdk else set())
    return Plan(entries=tuple(entries), sdk_token=sdk, vault_names=frozenset(names))


def _scrub(text: str, secrets: Iterable[str]) -> str:
    for value in secrets:
        if value:
            text = text.replace(value, _REDACTED)
    return text


def _last_line(text: str) -> str:
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def vault_pat(vault_name: str) -> str | None:
    """Bind the vault PAT, never the shell's ``GH_TOKEN`` / ``GITHUB_TOKEN``."""
    env = {k: v for k, v in os.environ.items() if k not in _SHELL_GH_VARS}
    cb.reset_cache()
    return cb.bind(vault_name, env=env)


def pat_can_read(pat: str, repo: str) -> bool:
    """Probe with the PAT in the child's environment only (never argv)."""
    env = {k: v for k, v in os.environ.items() if k not in _SHELL_GH_VARS}
    env["GH_TOKEN"] = pat
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents", "--jq", "length"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def set_secret(repo: str, name: str, value: str, secrets: Iterable[str]) -> bool:
    """``gh secret set`` with the value on stdin only."""
    result = subprocess.run(
        ["gh", "secret", "set", name, "--repo", repo],
        input=value,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        reason = _scrub(_last_line(result.stderr or ""), secrets) or f"exit {result.returncode}"
        print(f"  FAIL {repo} {name}: {reason}")
        return False
    return True


def run(plan: Plan, *, dry_run: bool, with_sdk_token: bool) -> int:
    failures = 0
    bound: list[str] = []
    for entry in plan.entries:
        value = cb.bind(entry.vault_name)
        if not value:
            source = cb._SOURCES.get(entry.vault_name, "unbound")
            print(
                f"  SKIP {entry.repo} {entry.secret}: vault {entry.vault_name} unbound ({source})"
            )
            failures += 1
            continue
        bound.append(value)
        if dry_run:
            print(f"  would set {entry.repo} {entry.secret} <- vault {entry.vault_name}")
        elif set_secret(entry.repo, entry.secret, value, bound):
            print(f"  set  {entry.repo} {entry.secret} <- vault {entry.vault_name}")
        else:
            failures += 1

    if with_sdk_token:
        sdk = plan.sdk_token
        if sdk is None:
            print(f"  SKIP {SDK_SECRET_NAME}: plan has no sdk_token block")
            return 1
        pat = vault_pat(sdk.vault_name)
        if not pat:
            print(f"  SKIP {SDK_SECRET_NAME}: vault {sdk.vault_name} unbound")
            failures += 1
        elif not pat_can_read(pat, sdk.must_read):
            print(f"  SKIP {SDK_SECRET_NAME}: vault {sdk.vault_name} cannot read {sdk.must_read}")
            failures += 1
        else:
            bound.append(pat)
            for repo in sdk.repos:
                if dry_run:
                    print(f"  would set {repo} {SDK_SECRET_NAME} <- vault {sdk.vault_name}")
                elif set_secret(repo, SDK_SECRET_NAME, pat, bound):
                    print(f"  set  {repo} {SDK_SECRET_NAME} <- vault {sdk.vault_name}")
                else:
                    failures += 1
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    ap.add_argument("--dry-run", action="store_true", help="bind and report; write nothing")
    ap.add_argument(
        "--with-sdk-token",
        action="store_true",
        help="also set SDK_TOKEN from the vault GITHUB_TOKEN after a read probe",
    )
    ap.add_argument("--plan", type=Path, default=DEFAULT_PLAN, help=argparse.SUPPRESS)
    ap.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        plan = load_plan(args.plan, args.inventory)
    except PlanError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return run(plan, dry_run=args.dry_run, with_sdk_token=args.with_sdk_token)


if __name__ == "__main__":
    sys.exit(main())
