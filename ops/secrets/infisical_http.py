#!/usr/bin/env python3
"""Infisical HTTP transport — the one client every secrets consumer shares.

Split out of ``port_aws_to_infisical.py`` so binding a secret no longer imports
the AWS migration tool: the agent secrets plane is Infisical only, and nothing
on the bind path may depend on AWS. Never logs hosts, paths or payloads — those
can carry secret material; callers map status 0 to unreachable.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_OPS_LIB = Path(__file__).resolve().parent.parent / "lib"
if str(_OPS_LIB) not in sys.path:
    sys.path.insert(0, str(_OPS_LIB))

from safe_https import exchange  # noqa: E402

DEFAULT_HOST = "https://app.infisical.com"

#: The only host this transport will send a machine identity to.
CANONICAL_HTTPS_HOSTS = frozenset({"app.infisical.com"})


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
    timeout = float(os.environ.get("L9_INFISICAL_HTTP_TIMEOUT", "8"))
    for attempt in range(retries):
        req = urllib.request.Request(f"{host}{path}", data=data, method=method, headers=headers)
        try:
            with exchange(
                req,
                timeout=timeout,
                allowed_https_hosts=CANONICAL_HTTPS_HOSTS,
                label="Infisical URL",
            ) as resp:
                raw = resp.read().decode()
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            snippet = e.read().decode(errors="replace")[:400]
            last_status, last_payload = e.code, {"error": snippet}
            if e.code != 429 or attempt == retries - 1:
                return last_status, last_payload
            time.sleep(delay)
            delay = min(delay * 2, 20)
        except (urllib.error.URLError, TimeoutError, OSError):
            # DNS / TLS / socket / deadline. Do not echo host, path, or
            # exception text — those can carry secret material. Callers map
            # status 0 to unbound/degraded.
            last_status, last_payload = 0, {"error": "infisical-unreachable"}
            if attempt == retries - 1:
                return last_status, last_payload
            time.sleep(delay)
            delay = min(delay * 2, 20)
    return last_status, last_payload


def universal_auth_login(host: str, client_id: str, client_secret: str, *, retries: int = 2) -> str:
    """An access token for a machine identity, or "" on failure. Never logs values."""
    status, payload = infisical_req(
        host,
        "POST",
        "/api/v1/auth/universal-auth/login",
        body={"clientId": client_id, "clientSecret": client_secret},
        retries=retries,
    )
    token = str((payload or {}).get("accessToken") or "").strip()
    return token if status == 200 else ""


__all__ = ["DEFAULT_HOST", "infisical_req", "universal_auth_login"]
