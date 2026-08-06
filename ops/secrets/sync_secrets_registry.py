#!/usr/bin/env python3
"""Sync openclaw-igorbot.registry.yaml from AWS Secrets Manager (Cursor-Governance SSOT).

This repository owns the secrets inventory. Other repos (igorbot, bots, CI) consume
refs from here — we do NOT fetch manifests from any external git repo.

Behavior:
  1. Load existing local registry (annotations: mode, notes, enabled, keys).
  2. List AWS Secrets Manager names under namespace prefix (default openclaw-igorbot/).
  3. Auto-add new secret_ids discovered in AWS; optionally inspect JSON key *names*
     only (values never written to disk, stdout summary, or logs).
  4. Merge governance overlays (e.g. ui-session-* stubs with provisioned: false).
  5. Write ops/secrets/openclaw-igorbot.registry.yaml (refs metadata only).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

NAMESPACE = "openclaw-igorbot"
REGION_DEFAULT = "us-east-1"
SCHEMA_VERSION = "1.0.0"
AWS_CALL_TIMEOUT_SECONDS = 30

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "openclaw-igorbot.registry.yaml"
DEFAULT_OVERLAYS = HERE / "registry.overlays.yaml"


def _die(msg: str, code: int = 1) -> None:
    print(f"sync_secrets_registry: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _safe_path(path: Path | str) -> Path:
    """Resolve a CLI/file path; require it stay under cwd or system temp (S8707)."""
    resolved = Path(path).expanduser().resolve()
    allowed = (Path.cwd().resolve(), Path(tempfile.gettempdir()).resolve())
    for root in allowed:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    _die(f"path escapes allowed roots: {path}")


def _require_yaml() -> Any:
    if yaml is None:
        _die("PyYAML required (install via project deps / uv sync --extra dev)")
    return yaml


def load_registry(path: Path) -> dict[str, Any]:
    path = _safe_path(path)
    if not path.is_file():
        return {
            "schema_version": SCHEMA_VERSION,
            "namespace": NAMESPACE,
            "region_default": REGION_DEFAULT,
            "source": {},
            "secrets": [],
        }
    y = _require_yaml()
    data = y.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        _die(f"invalid registry: {path}")
    data.setdefault("secrets", [])
    return data


def load_overlays(path: Path) -> list[dict[str, Any]]:
    path = _safe_path(path)
    if not path.is_file():
        return []
    y = _require_yaml()
    data = y.safe_load(path.read_text(encoding="utf-8")) or {}
    overlays = data.get("overlays") or []
    if not isinstance(overlays, list):
        _die(f"overlays must be a list in {path}")
    return overlays


def list_aws_secret_ids(
    *,
    region: str,
    prefix: str,
    runner: Any = subprocess.run,
) -> list[str]:
    """Return secret names under prefix via aws CLI. Never returns secret values."""
    names: list[str] = []
    next_token: str | None = None
    while True:
        cmd = [
            "aws",
            "secretsmanager",
            "list-secrets",
            "--region",
            region,
            "--filters",
            f"Key=name,Values={prefix}",
            "--output",
            "json",
        ]
        if next_token:
            cmd.extend(["--next-token", next_token])
        try:
            proc = runner(
                cmd,
                capture_output=True,
                text=True,
                timeout=AWS_CALL_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            _die("TIMEOUT listing secrets")
        except FileNotFoundError:
            _die("AWS_CLI_NOT_FOUND")
        if proc.returncode != 0:
            _die(f"list-secrets failed: {(proc.stderr or '').strip() or 'unknown'}")
        payload = json.loads(proc.stdout or "{}")
        for item in payload.get("SecretList") or []:
            name = item.get("Name")
            if isinstance(name, str) and name.startswith(prefix):
                names.append(name)
        next_token = payload.get("NextToken")
        if not next_token:
            break
    return sorted(set(names))


def inspect_json_keys(
    secret_id: str,
    region: str,
    *,
    runner: Any = subprocess.run,
) -> tuple[list[str] | None, str | None]:
    """Return (json_key_names, error). Values are discarded — never returned."""
    try:
        proc = runner(
            [
                "aws",
                "secretsmanager",
                "get-secret-value",
                "--secret-id",
                secret_id,
                "--region",
                region,
                "--query",
                "SecretString",
                "--output",
                "text",
            ],
            capture_output=True,
            text=True,
            timeout=AWS_CALL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT"
    except FileNotFoundError:
        return None, "AWS_CLI_NOT_FOUND"
    if proc.returncode != 0:
        stderr = proc.stderr or ""
        if "ResourceNotFoundException" in stderr:
            return None, "NOT_FOUND"
        return None, "RESOLUTION_ERROR"
    raw = (proc.stdout or "").strip()
    # Discard raw ASAP after key extraction.
    keys: list[str] | None
    err: str | None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        keys, err = None, None  # plain string secret — no JSON keys
        return keys, err
    if isinstance(parsed, dict):
        return sorted(str(k) for k in parsed), None
    return None, None


def merge_entry(
    prior: dict[str, Any] | None,
    *,
    secret_id: str,
    region: str,
    key_names: list[str] | None,
    origin: str,
    provisioned: bool = True,
    enabled: bool = True,
) -> dict[str, Any]:
    prior = prior or {}
    prior_keys = {
        k.get("json_key"): dict(k) for k in (prior.get("keys") or []) if k.get("json_key")
    }
    if key_names is not None:
        keys_out: list[dict[str, Any]] = []
        for name in key_names:
            if name in prior_keys:
                keys_out.append(prior_keys[name])
            else:
                keys_out.append({"json_key": name})
    else:
        keys_out = list(prior.get("keys") or [])

    if "provisioned" in prior:
        provisioned_out = bool(prior["provisioned"])
    else:
        provisioned_out = provisioned
    if "enabled" in prior:
        enabled_out = bool(prior["enabled"])
    else:
        enabled_out = enabled

    entry: dict[str, Any] = {
        "secret_id": secret_id,
        "enabled": enabled_out,
        "region": prior.get("region") or region,
        "provisioned": provisioned_out,
        "origin": origin,
        "keys": keys_out,
    }
    if isinstance(prior.get("note"), str) and prior["note"]:
        entry["note"] = prior["note"]
    return entry


def merge_overlays(
    secrets: list[dict[str, Any]], overlays: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_id = {s["secret_id"]: s for s in secrets}
    order = [s["secret_id"] for s in secrets]
    for ov in overlays:
        sid = ov.get("secret_id")
        if not sid:
            _die("overlay missing secret_id")
        existing = by_id.get(sid)
        if existing and existing.get("provisioned") is True and existing.get("origin") == "aws_sm":
            # AWS-provisioned entry wins over stub overlay for the same id.
            continue
        entry = {
            "secret_id": sid,
            "enabled": bool(ov.get("enabled", True)),
            "region": ov.get("region") or REGION_DEFAULT,
            "provisioned": bool(ov.get("provisioned", False)),
            "origin": ov.get("origin") or "governance_overlay",
            "keys": list(ov.get("keys") or []),
        }
        if sid in by_id:
            by_id[sid] = entry
        else:
            order.append(sid)
            by_id[sid] = entry
    return [by_id[sid] for sid in order]


def build_registry_from_aws(
    *,
    prior: dict[str, Any],
    aws_ids: list[str],
    overlays: list[dict[str, Any]],
    region: str,
    refresh_keys: bool,
    inspect_new: bool,
    runner: Any = subprocess.run,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Returns (registry, stats)."""
    prior_by_id = {s["secret_id"]: s for s in (prior.get("secrets") or [])}
    secrets: list[dict[str, Any]] = []
    added: list[str] = []
    refreshed: list[str] = []

    for sid in aws_ids:
        prior_entry = prior_by_id.get(sid)
        is_new = prior_entry is None
        key_names: list[str] | None = None
        should_inspect = (
            (is_new and inspect_new)
            or (refresh_keys)
            or (prior_entry is not None and not (prior_entry.get("keys") or []) and inspect_new)
        )
        if should_inspect:
            key_names, err = inspect_json_keys(sid, region, runner=runner)
            if err:
                print(
                    f"sync_secrets_registry: warn inspect {sid} code={err} (keeping prior keys)",
                    file=sys.stderr,
                )
                key_names = None
            elif not is_new:
                refreshed.append(sid)
        if is_new:
            added.append(sid)
        entry = merge_entry(
            prior_entry,
            secret_id=sid,
            region=region,
            key_names=key_names if should_inspect else None,
            origin="aws_sm",
            provisioned=True,
            enabled=True,
        )
        if should_inspect and key_names is None and prior_entry is None:
            # plain string or inspect failed — empty keys list
            entry["keys"] = []
        secrets.append(entry)

    # Preserve local-only prior entries that are not in AWS (disabled / legacy notes)
    # only when they were explicitly disabled or marked not provisioned.
    for sid, prior_entry in prior_by_id.items():
        if sid in {s["secret_id"] for s in secrets}:
            continue
        if prior_entry.get("origin") == "governance_overlay":
            continue
        if prior_entry.get("enabled") is False or prior_entry.get("provisioned") is False:
            kept = dict(prior_entry)
            kept["origin"] = "local_ssot"
            secrets.append(kept)

    secrets = merge_overlays(secrets, overlays)
    stats = {
        "aws_count": len(aws_ids),
        "added": added,
        "refreshed_keys": refreshed,
        "total": len(secrets),
    }
    registry = {
        "schema_version": SCHEMA_VERSION,
        "namespace": NAMESPACE,
        "region_default": region,
        "source": {
            "authority": "cursor-governance",
            "path": "ops/secrets/openclaw-igorbot.registry.yaml",
            "sync": "aws_secrets_manager",
            "region": region,
            "namespace_prefix": f"{NAMESPACE}/",
            "synced_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "note": (
                "SSOT is this file in Cursor-Governance. Consumers (igorbot, bots, CI) "
                "must depend on this registry — do not reverse the dependency."
            ),
        },
        "secrets": secrets,
    }
    return registry, stats


def write_registry(path: Path, registry: dict[str, Any]) -> None:
    y = _require_yaml()
    path = _safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        y.safe_dump(registry, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def enabled_secret_ids(registry: dict[str, Any]) -> list[str]:
    return sorted({s["secret_id"] for s in registry["secrets"] if s.get("enabled")})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--region",
        default=REGION_DEFAULT,
        help=f"AWS region (default {REGION_DEFAULT})",
    )
    parser.add_argument(
        "--prefix",
        default=f"{NAMESPACE}/",
        help="Secret name prefix to sync",
    )
    parser.add_argument(
        "--overlays",
        type=Path,
        default=DEFAULT_OVERLAYS,
        help="Local overlay stubs (not yet in AWS)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Local SSOT registry path",
    )
    parser.add_argument(
        "--refresh-keys",
        action="store_true",
        help="Re-inspect JSON key names for all AWS secrets (values still discarded)",
    )
    parser.add_argument(
        "--no-inspect-new",
        action="store_true",
        help="Do not fetch SecretString for newly discovered IDs (IDs only)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary only; do not write registry",
    )
    parser.add_argument(
        "--json-summary",
        action="store_true",
        help="Print enabled secret_id list as JSON (no secret values)",
    )
    parser.add_argument(
        "--aws-ids-file",
        type=Path,
        default=None,
        help="Test helper: JSON list of secret ids (skips live list-secrets)",
    )
    args = parser.parse_args(argv)

    prior = load_registry(args.out)
    overlays = load_overlays(args.overlays)

    if args.aws_ids_file is not None:
        ids_path = _safe_path(args.aws_ids_file)
        aws_ids = json.loads(ids_path.read_text(encoding="utf-8"))
        if not isinstance(aws_ids, list):
            _die("--aws-ids-file must be a JSON list")
        aws_ids = sorted(str(x) for x in aws_ids)
    else:
        aws_ids = list_aws_secret_ids(region=args.region, prefix=args.prefix)

    registry, stats = build_registry_from_aws(
        prior=prior,
        aws_ids=aws_ids,
        overlays=overlays,
        region=args.region,
        refresh_keys=args.refresh_keys,
        inspect_new=not args.no_inspect_new,
    )

    if not args.dry_run:
        write_registry(args.out, registry)

    ids = enabled_secret_ids(registry)
    print(
        f"sync_secrets_registry: "
        f"{'dry-run ' if args.dry_run else ''}{args.out} "
        f"(aws={stats['aws_count']} added={len(stats['added'])} "
        f"total={stats['total']} enabled={len(ids)})",
        file=sys.stderr,
    )
    if stats["added"]:
        print(
            "sync_secrets_registry: added " + ", ".join(stats["added"]),
            file=sys.stderr,
        )
    if args.json_summary:
        json.dump(
            {
                "enabled_secret_ids": ids,
                "added": stats["added"],
                "authority": "cursor-governance",
            },
            sys.stdout,
        )
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
