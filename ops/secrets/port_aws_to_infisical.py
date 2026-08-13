#!/usr/bin/env python3
"""Port openclaw-igorbot AWS Secrets Manager values into an Infisical project.

L9_META: parent=l9-aws-secrets layer=script role=port_aws_to_infisical
owner=igor_beylin status=active version=1.0.0 updated=2026-08-13

Values never go to stdout, logs, or git. Summary is IDs / key names / counts only.

Bootstrap: openclaw-igorbot/infisical-cursor (Universal Auth).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

AWS_PREFIX = "openclaw-igorbot/"
AWS_REGION = "us-east-1"
BOOTSTRAP_SECRET = "openclaw-igorbot/infisical-cursor"
DEFAULT_PROJECT_ID = "9f92179d-3caa-4d7a-90a9-bb896499bfe6"
DEFAULT_ENV = "prod"
STRUCTURED_ROOT = "/aws/openclaw-igorbot"

# Explicit env-var names for the Infisical `/` path (matches SEO-Bot / infisical-config).
ENV_MAP: dict[tuple[str, str], str] = {
    ("anthropic", "apikey"): "ANTHROPIC_API_KEY",
    ("ceg", "API_SECRET_KEY"): "CEG_API_KEY",
    ("clawhub", "token"): "CLAWHUB_API_KEY",
    ("cloudflare", "apitoken"): "CLOUDFLARE_API_TOKEN",
    ("cloudflare", "accountid"): "CLOUDFLARE_ACCOUNT_ID",
    ("coderabbit", "apikey"): "CODERABBIT_API_KEY",
    ("context7", "apikey"): "CONTEXT7_API_KEY",
    ("coolify", "apikey"): "COOLIFY_TOKEN",
    ("coolify", "url"): "COOLIFY_API_URL",
    ("dataforseo", "apikey"): "DATAFORSEO_API_KEY",
    ("dataforseo", "login"): "DATAFORSEO_LOGIN",
    ("dataforseo", "password"): "DATAFORSEO_PASSWORD",
    ("deepseek", "apikey"): "DEEPSEEK_API_KEY",
    ("emma-telegram", "botToken"): "EMMA_TELEGRAM_BOT_TOKEN",
    ("gitguardian", "apikey"): "GITGUARDIAN_API_KEY",
    ("gemini", "apikey"): "GEMINI_API_KEY",
    ("github", "token"): "GITHUB_TOKEN",
    ("google-places", "apikey"): "GOOGLE_PLACES_API_KEY",
    ("hetzner", "apitoken"): "HCLOUD_TOKEN",
    ("igorbot-gateway-secret", "token"): "IGORBOT_GATEWAY_TOKEN",
    ("mistral", "apikey"): "MISTRAL_API_KEY",
    ("n8n", "api_key"): "N8N_API_KEY",
    ("n8n", "api_url"): "N8N_API_URL",
    ("n8n", "workflow_host"): "N8N_WORKFLOW_HOST",
    ("nano-banana-pro", "apiKey"): "NANO_BANANA_API_KEY",
    ("neo4j", "password"): "NEO4J_PASSWORD",
    ("neo4j", "uri"): "NEO4J_URI",
    ("notion", "token"): "NOTION_API_KEY",
    ("odoo-web-lead", "api_key"): "ODOO_WEB_LEAD_API_KEY",
    ("odoo-web-lead", "api_url"): "ODOO_WEB_LEAD_API_URL",
    ("odoo-web-lead", "environment"): "ODOO_WEB_LEAD_ENVIRONMENT",
    ("odoo-web-lead", "webhook_path"): "ODOO_WEB_LEAD_WEBHOOK_PATH",
    ("openai", "apikey"): "OPENAI_API_KEY",
    ("openai-whisper", "apiKey"): "OPENAI_WHISPER_API_KEY",
    ("openrouter", "apikey"): "OPENROUTER_API_KEY",
    ("pagespeed", "apikey"): "PAGESPEED_API_KEY",
    ("perplexity", "apikey"): "PERPLEXITY_API_KEY",
    ("posthog", "host"): "POSTHOG_HOST",
    ("posthog", "personal_api_key"): "POSTHOG_PERSONAL_API_KEY",
    ("posthog", "project_api_key"): "POSTHOG_PROJECT_API_KEY",
    ("posthog", "project_id"): "POSTHOG_PROJECT_ID",
    ("pypi", "token"): "PYPI_TOKEN",
    ("pypi", "username"): "PYPI_USERNAME",
    ("semgrep", "token"): "SEMGREP_APP_TOKEN",
    ("seo-bot", "apikey"): "SEO_BOT_API_KEY",
    ("sonarcloud", "token"): "SONAR_TOKEN",
    ("stripe", "apikey"): "STRIPE_API_KEY",
    ("telegram", "bottoken"): "TELEGRAM_BOT_TOKEN",
    ("telegram-allowed-users", "ids"): "TELEGRAM_ALLOWED_USER_IDS",
    ("telegram-chat-id", "id"): "TELEGRAM_CHAT_ID",
    ("vercel", "token"): "VERCEL_TOKEN",
}

# Bootstrap secrets stay under /aws/... only — do not flatten to `/` (chicken-egg).
SKIP_ROOT_PREFIXES = (
    "infisical-cursor",
    "infisical-seo-bot",
    "infisical-website-bot",
    "infisical-cursor-governance",
)

SECRET_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _die(msg: str, code: int = 1) -> None:
    print(f"port_aws_to_infisical: {msg}", file=sys.stderr)
    raise SystemExit(code)


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


def sanitize_key(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if cleaned and cleaned[0].isdigit():
        cleaned = f"K_{cleaned}"
    if not cleaned:
        cleaned = "VALUE"
    if not SECRET_NAME_RE.match(cleaned):
        cleaned = "VALUE"
    return cleaned


def env_name(suffix: str, json_key: str) -> str:
    mapped = ENV_MAP.get((suffix, json_key))
    if mapped:
        return mapped
    suffix_u = sanitize_key(suffix.replace("-", "_")).upper()
    key_u = sanitize_key(json_key).upper()
    if key_u in {"APIKEY", "API_KEY"}:
        return f"{suffix_u}_API_KEY"
    if key_u in {"TOKEN", "APITOKEN", "API_TOKEN"}:
        return f"{suffix_u}_TOKEN"
    return f"{suffix_u}_{key_u}"


def infisical_req(
    host: str,
    method: str,
    path: str,
    token: str | None = None,
    body: dict[str, Any] | None = None,
    retries: int = 6,
) -> tuple[int, dict[str, Any]]:
    data = json.dumps(body).encode() if body is not None else None
    headers: dict[str, str] = {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    delay = 1.5
    last_status = 0
    last_payload: dict[str, Any] = {}
    for attempt in range(retries):
        req = urllib.request.Request(f"{host}{path}", data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode()
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            snippet = e.read().decode(errors="replace")[:400]
            last_status, last_payload = e.code, {"error": snippet}
            if e.code != 429 or attempt == retries - 1:
                return last_status, last_payload
            time.sleep(delay)
            delay = min(delay * 2, 20)
    return last_status, last_payload


def login(host: str, client_id: str, client_secret: str) -> str:
    status, payload = infisical_req(
        host,
        "POST",
        "/api/v1/auth/universal-auth/login",
        body={"clientId": client_id, "clientSecret": client_secret},
    )
    if status != 200 or "accessToken" not in payload:
        _die(f"Infisical login failed status={status}")
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
    _die(f"folder create failed path={path} name={name} status={status}")


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
                _die(f"patch failed key={key} path={secret_path} status={pstatus}")
            updated += 1
            continue
        _die(f"create failed key={key} path={secret_path} status={status}")
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
        _die(f"list secrets failed path={secret_path} status={status}")
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

    boot = json.loads(aws_secret_string(BOOTSTRAP_SECRET))
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
                _die(f"env name collision {ekey}")
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

    print(
        f"port_aws_to_infisical: aws_secrets={len(aws_ids)} "
        f"root_keys={len(root_items)} structured_folders={len(structured)} "
        f"skipped_root={len(skipped_root)}"
    )
    if args.dry_run:
        print("root_keys:")
        for item in sorted(root_items, key=lambda x: x["secretKey"]):
            print(f"  / {item['secretKey']}")
        print("structured_folders:")
        for suffix in sorted(structured):
            keys = ",".join(i["secretKey"] for i in structured[suffix])
            print(f"  {STRUCTURED_ROOT}/{suffix}/ [{keys}]")
        return 0

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
