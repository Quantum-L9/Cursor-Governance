#!/usr/bin/env python3
"""Port openclaw-igorbot AWS Secrets Manager values into an Infisical project.

L9_META: parent=l9-secrets layer=script role=port_aws_to_infisical
owner=igor_beylin status=active version=1.0.0 updated=2026-08-13

Values never go to stdout, logs, or git. Summary is IDs / key names / counts only.

Bootstrap: openclaw-igorbot/infisical-cursor (Universal Auth).
"""

# L9-TRUSTED-OPERATOR-ONLY — raw-secret paths in this file are reachable only
# beyond the model boundary and are guarded by surface_trust.require_trusted /
# the broker's boundary self-check. The marker declares that status for review;
# it is not a bypass, and it does not disable those runtime guards.

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

_OPS_LIB = Path(__file__).resolve().parent.parent / "lib"
if str(_OPS_LIB) not in sys.path:
    sys.path.insert(0, str(_OPS_LIB))


AWS_PREFIX = "openclaw-igorbot/"
AWS_REGION = "us-east-1"
BOOTSTRAP_SECRET_REF = "openclaw-igorbot/infisical-cursor"
DEFAULT_PROJECT_ID = "9f92179d-3caa-4d7a-90a9-bb896499bfe6"
DEFAULT_ENV = "prod"
STRUCTURED_ROOT = "/aws/openclaw-igorbot"

# Legacy ref -> Infisical name map: owned by legacy_refs.py (ADR-0053).
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
# ENV_MAP, sanitize_key and env_name: one translation for the port and the bind check.
from legacy_refs import ENV_MAP, env_name, sanitize_key  # noqa: E402

# Bootstrap secrets stay under /aws/... only — do not flatten to `/` (chicken-egg).
SKIP_ROOT_PREFIXES = (
    "infisical-cursor",
    "infisical-seo-bot",
    "infisical-website-bot",
    "infisical-cursor-governance",
)

SECRET_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# Literal env-var names only — never derived from SecretString JSON keys/values.
_ROOT_LOG_NAMES: tuple[str, ...] = tuple(
    sorted({*ENV_MAP.values(), "GH_TOKEN", "GOOGLE_SERVICE_ACCOUNT_JSON"})
)


def _die(reason: str, status: int | None = None, code: int = 1) -> None:
    """Log a static reason plus optional HTTP status. Never interpolate secrets."""
    if status is None:
        print(f"port_aws_to_infisical: {reason}", file=sys.stderr)
    else:
        print(f"port_aws_to_infisical: {reason} status={status}", file=sys.stderr)
    raise SystemExit(code)


def format_dry_run(
    aws_ids: list[str],
    used_env: dict[str, str],
    structured_counts: dict[str, int],
    skipped_root_count: int,
    root_count: int,
) -> list[str]:
    """Summary lines: AWS secret IDs, allowlisted env names, folder counts. No values."""
    lines = [
        (
            f"port_aws_to_infisical: aws_secrets={len(aws_ids)} "
            f"root_keys={root_count} structured_folders={len(structured_counts)} "
            f"skipped_root={skipped_root_count}"
        ),
        "aws_secret_ids:",
    ]
    lines.extend(f"  {sid}" for sid in aws_ids)
    lines.append("root_env_names:")
    lines.extend(f"  / {name}" for name in _ROOT_LOG_NAMES if name in used_env)
    lines.append("structured_folders:")
    for suffix in sorted(structured_counts):
        lines.append(f"  {STRUCTURED_ROOT}/{suffix}/ count={structured_counts[suffix]}")
    return lines


def aws_secret_string(secret_id: str) -> str:
    return subprocess.check_output(
        [
            "aws",
            "secretsmanager",
            "get-secret-value",
            "--secret-id",
            secret_id,
            "--region",
            AWS_REGION,
            "--query",
            "SecretString",
            "--output",
            "text",
        ],
        text=True,
    )


def list_aws_ids(prefix: str = AWS_PREFIX) -> list[str]:
    names: list[str] = []
    next_token: str | None = None
    while True:
        cmd = [
            "aws",
            "secretsmanager",
            "list-secrets",
            "--region",
            AWS_REGION,
            "--filters",
            f"Key=name,Values={prefix}",
            "--output",
            "json",
        ]
        if next_token:
            cmd.extend(["--next-token", next_token])
        payload = json.loads(subprocess.check_output(cmd, text=True))
        for item in payload.get("SecretList") or []:
            name = item.get("Name")
            if isinstance(name, str) and name.startswith(prefix):
                names.append(name)
        next_token = payload.get("NextToken")
        if not next_token:
            break
    return sorted(set(names))


def parse_secret_payload(raw: str) -> dict[str, str]:
    raw = raw.strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"value": raw}
    if isinstance(parsed, dict):
        out: dict[str, str] = {}
        for k, v in parsed.items():
            if v is None:
                continue
            if isinstance(v, str):
                out[str(k)] = v
            else:
                out[str(k)] = json.dumps(v, separators=(",", ":"))
        return out
    return {"value": raw}


# The Infisical transport lives in infisical_http (re-exported for callers).
from infisical_http import infisical_req  # noqa: E402,F401


def login(host: str, client_id: str, client_secret: str) -> str:
    status, payload = infisical_req(
        host,
        "POST",
        "/api/v1/auth/universal-auth/login",
        body={"clientId": client_id, "clientSecret": client_secret},
    )
    if status != 200 or "accessToken" not in payload:
        _die("Infisical login failed", status=status)
    return str(payload["accessToken"])


def ensure_folder(
    host: str, token: str, project_id: str, environment: str, path: str, name: str
) -> None:
    status, payload = infisical_req(
        host,
        "POST",
        "/api/v2/folders",
        token,
        {
            "projectId": project_id,
            "environment": environment,
            "path": path,
            "name": name,
        },
    )
    if status in {200, 201}:
        return
    err = str(payload.get("error") or "")
    if status in {400, 409} and any(x in err.lower() for x in ("already", "exist", "duplicate")):
        return
    _die("folder create failed", status=status)


def ensure_folder_chain(
    host: str, token: str, project_id: str, environment: str, abs_path: str
) -> None:
    parts = [p for p in abs_path.strip("/").split("/") if p]
    cur = "/"
    for part in parts:
        ensure_folder(host, token, project_id, environment, cur, part)
        cur = f"{cur.rstrip('/')}/{part}"


def upsert_batch(
    host: str,
    token: str,
    project_id: str,
    environment: str,
    secret_path: str,
    items: list[dict[str, Any]],
) -> tuple[int, int]:
    """Create or patch secrets at secret_path. Returns (created, updated)."""
    created = 0
    updated = 0
    # Infisical batch create fails the whole set if one exists; do per-item upsert.
    for item in items:
        key = item["secretKey"]
        body = {
            "projectId": project_id,
            "environment": environment,
            "secretPath": secret_path,
            "secretValue": item["secretValue"],
            "secretComment": item.get("secretComment") or "",
            "skipMultilineEncoding": item.get("skipMultilineEncoding") or False,
            "type": "shared",
        }
        status, payload = infisical_req(
            host, "POST", f"/api/v4/secrets/{urllib.parse.quote(key, safe='')}", token, body
        )
        if status in {200, 201}:
            created += 1
            continue
        err = str(payload.get("error") or "")
        if status in {400, 409} or "already" in err.lower() or "exist" in err.lower():
            patch_body = {
                "projectId": project_id,
                "environment": environment,
                "secretPath": secret_path,
                "secretValue": item["secretValue"],
                "secretComment": item.get("secretComment") or "",
                "skipMultilineEncoding": item.get("skipMultilineEncoding") or False,
            }
            pstatus, _pp = infisical_req(
                host,
                "PATCH",
                f"/api/v4/secrets/{urllib.parse.quote(key, safe='')}",
                token,
                patch_body,
            )
            if pstatus not in {200, 201}:
                _die("patch failed", status=pstatus)
            updated += 1
            continue
        _die("create failed", status=status)
    return created, updated


def list_infisical_keys(
    host: str, token: str, project_id: str, environment: str, secret_path: str, recursive: bool
) -> list[tuple[str, str]]:
    qs = urllib.parse.urlencode(
        {
            "workspaceId": project_id,
            "environment": environment,
            "secretPath": secret_path,
            "viewSecretValue": "false",
            "include_imports": "false",
            "recursive": "true" if recursive else "false",
        }
    )
    status, payload = infisical_req(host, "GET", f"/api/v3/secrets/raw?{qs}", token)
    if status != 200:
        _die("list secrets failed", status=status)
    out: list[tuple[str, str]] = []
    for sec in payload.get("secrets") or []:
        k = sec.get("secretKey") or ""
        p = sec.get("secretPath") or secret_path
        if k:
            out.append((p, k))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--environment", default=DEFAULT_ENV)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    boot = json.loads(aws_secret_string(BOOTSTRAP_SECRET_REF))
    host = str(boot["host"]).rstrip("/")
    token = login(host, str(boot["client_id"]), str(boot["client_secret"]))

    aws_ids = list_aws_ids()
    root_items: list[dict[str, Any]] = []
    structured: dict[str, list[dict[str, Any]]] = {}
    skipped_root: list[str] = []
    used_env: dict[str, str] = {}

    for sid in aws_ids:
        suffix = sid.removeprefix(AWS_PREFIX)
        payload = parse_secret_payload(aws_secret_string(sid))
        folder_items: list[dict[str, Any]] = []
        for json_key, value in payload.items():
            structured_key = sanitize_key(json_key)
            skip_ml = "\n" in value or json_key in {"private_key"}
            folder_items.append(
                {
                    "secretKey": structured_key,
                    "secretValue": value,
                    "secretComment": f"ported from {sid}#{json_key}",
                    "skipMultilineEncoding": skip_ml,
                }
            )
            if suffix.startswith(SKIP_ROOT_PREFIXES) or suffix in SKIP_ROOT_PREFIXES:
                skipped_root.append(f"{sid}#{json_key}")
                continue
            ekey = env_name(suffix, json_key)
            if ekey in used_env and used_env[ekey] != f"{sid}#{json_key}":
                ekey = sanitize_key(f"{suffix}_{json_key}".replace("-", "_")).upper()
            if ekey in used_env:
                _die("env name collision")
            used_env[ekey] = f"{sid}#{json_key}"
            root_items.append(
                {
                    "secretKey": ekey,
                    "secretValue": value,
                    "secretComment": f"ported from {sid}#{json_key}",
                    "skipMultilineEncoding": skip_ml,
                }
            )
        if suffix == "google-service-account":
            raw = aws_secret_string(sid).strip()
            root_items.append(
                {
                    "secretKey": "GOOGLE_SERVICE_ACCOUNT_JSON",
                    "secretValue": raw,
                    "secretComment": ("ported from openclaw-igorbot/google-service-account"),
                    "skipMultilineEncoding": True,
                }
            )
            used_env["GOOGLE_SERVICE_ACCOUNT_JSON"] = sid
        if suffix == "github" and "token" in payload:
            root_items.append(
                {
                    "secretKey": "GH_TOKEN",
                    "secretValue": payload["token"],
                    "secretComment": "alias of GITHUB_TOKEN (CANONICAL_LAW §14)",
                    "skipMultilineEncoding": False,
                }
            )
            used_env["GH_TOKEN"] = "openclaw-igorbot/github#token"
        structured[suffix] = folder_items

    if args.dry_run:
        for line in format_dry_run(
            aws_ids,
            used_env,
            {suffix: len(items) for suffix, items in structured.items()},
            len(skipped_root),
            len(root_items),
        ):
            print(line)
        return 0

    print(
        f"port_aws_to_infisical: aws_secrets={len(aws_ids)} "
        f"root_keys={len(root_items)} structured_folders={len(structured)} "
        f"skipped_root={len(skipped_root)}"
    )

    created_total = 0
    updated_total = 0
    ensure_folder_chain(host, token, args.project_id, args.environment, STRUCTURED_ROOT)
    for suffix, items in structured.items():
        folder_path = f"{STRUCTURED_ROOT}/{suffix}"
        ensure_folder_chain(host, token, args.project_id, args.environment, folder_path)
        c, u = upsert_batch(host, token, args.project_id, args.environment, folder_path, items)
        created_total += c
        updated_total += u
        print(f"  folder {suffix}: created={c} updated={u} keys={len(items)}")

    c, u = upsert_batch(host, token, args.project_id, args.environment, "/", root_items)
    created_total += c
    updated_total += u
    print(f"  root /: created={c} updated={u} keys={len(root_items)}")

    listed = list_infisical_keys(
        host, token, args.project_id, args.environment, "/", recursive=True
    )
    print(
        f"port_aws_to_infisical: done created={created_total} updated={updated_total} "
        f"listed_recursive={len(listed)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
