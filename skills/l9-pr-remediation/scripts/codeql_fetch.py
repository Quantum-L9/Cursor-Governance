#!/usr/bin/env python3
"""Fail-closed, secret-safe CodeQL code-scanning alert snapshot fetcher (stdlib only).

Retrieves the complete active (and, for review, dismissed) CodeQL alert set for a
repository's branch from the GitHub code-scanning API, plus the most recent analysis
metadata for the exact analyzed commit, and writes a single secret-free JSON snapshot
(`codeql-alerts-before.json` by convention).

Read-only against GitHub: this never dismisses, reopens, or otherwise mutates alert
state (dismissal is fail-closed policy, not a fetcher action). The API token is read
from the environment by reference only (GITHUB_TOKEN / GH_TOKEN) and is never printed,
stored, or written to the snapshot; the Authorization header is redacted in the receipt.

Fail-closed: if pagination cannot be proven complete (the Link header still advertises a
next page after the page cap), the snapshot is marked BLOCKED and the process exits
non-zero rather than emitting a smaller-than-real alert set. Code-scanning requires
authentication; an unauthenticated or forbidden response is BLOCKED, never an empty pass.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

_OPS_LIB = Path(__file__).resolve().parents[3] / "ops" / "lib"
if str(_OPS_LIB) not in sys.path:
    sys.path.insert(0, str(_OPS_LIB))

from safe_https import https_exchange  # noqa: E402

PAGE_SIZE = 100
MAX_PAGES = 50  # 100 * 50 = 5000 alerts; a repo above this needs an explicit wider run
API_VERSION = "2022-11-28"
_GITHUB_HOSTS = frozenset({"api.github.com"})


def _request(
    base_url: str, path: str, params: dict[str, str], token: str | None
) -> tuple[list | dict, str | None]:
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
    url = f"{base_url.rstrip('/')}{path}?{query}"
    request = urllib.request.Request(url, method="GET")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", API_VERSION)
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with https_exchange(
            request, timeout=45, allowed_hosts=_GITHUB_HOSTS, label="CodeQL API URL"
        ) as response:
            body = json.loads(response.read().decode("utf-8"))
            return body, response.headers.get("Link")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise SystemExit(
            f"BLOCKED: code-scanning {path} returned HTTP {exc.code}: {detail}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise SystemExit(f"BLOCKED: code-scanning {path} request failed: {exc}") from exc


def _validated_base_url(value: str) -> str:
    """Sanitize the API base URL before any network use (SSRF).

    Require HTTPS and the public GitHub API host so a crafted --base-url cannot redirect
    requests (and the Authorization header) to an attacker-controlled endpoint. A GitHub
    Enterprise host would extend this allow-list explicitly.
    """
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or parsed.hostname != "api.github.com":
        raise SystemExit("BLOCKED: --base-url must be https://api.github.com")
    return value


def _validated_output(value: str) -> Path:
    """Require --output to stay within the working directory (path traversal)."""
    base = Path.cwd().resolve()
    resolved = (base / value).resolve()
    if resolved != base and base not in resolved.parents:
        raise SystemExit("BLOCKED: --output must stay within the working directory")
    return resolved


def _has_next(link_header: str | None) -> bool:
    return bool(link_header) and 'rel="next"' in link_header


def fetch_alerts(
    base_url: str, owner: str, repo: str, ref: str, state: str, token: str | None
) -> dict:
    alerts: list[dict] = []
    page = 1
    truncated = False
    while page <= MAX_PAGES:
        params = {
            "state": state,
            "ref": ref,
            "tool_name": "CodeQL",
            "per_page": str(PAGE_SIZE),
            "page": str(page),
        }
        body, link = _request(
            base_url, f"/repos/{owner}/{repo}/code-scanning/alerts", params, token
        )
        if not isinstance(body, list):
            raise SystemExit("BLOCKED: unexpected code-scanning alerts payload (not a list)")
        alerts.extend(body)
        if not _has_next(link) or not body:
            break
        page += 1
    else:
        truncated = _has_next(link)
    return {"alerts": alerts, "retrieved": len(alerts), "complete": not truncated}


def _normalize(alert: dict) -> dict:
    rule = alert.get("rule") or {}
    instance = alert.get("most_recent_instance") or {}
    location = instance.get("location") or {}
    return {
        "alert_number": alert.get("number"),
        "alert_url": alert.get("html_url"),
        "rule_id": rule.get("id"),
        "rule_name": rule.get("name"),
        "cwe_tags": [
            tag for tag in (rule.get("tags") or []) if str(tag).startswith("external/cwe")
        ],
        "problem_severity": rule.get("severity"),
        "security_severity": rule.get("security_severity_level"),
        "state": alert.get("state"),
        "dismissed_reason": alert.get("dismissed_reason"),
        "dismissed_comment": alert.get("dismissed_comment"),
        "analyzed_commit_sha": instance.get("commit_sha"),
        "ref": instance.get("ref"),
        "path": location.get("path"),
        "start_line": location.get("start_line"),
        "end_line": location.get("end_line"),
        "message": (instance.get("message") or {}).get("text"),
        "tool_version": (alert.get("tool") or {}).get("version"),
    }


def _severity_breakdown(alerts: list[dict]) -> dict[str, int]:
    breakdown: dict[str, int] = {}
    for alert in alerts:
        level = (
            (alert.get("rule") or {}).get("security_severity_level")
            or (alert.get("rule") or {}).get("severity")
            or "unknown"
        )
        breakdown[level] = breakdown.get(level, 0) + 1
    return breakdown


def latest_analysis(
    base_url: str, owner: str, repo: str, ref: str, token: str | None
) -> dict | None:
    body, _ = _request(
        base_url,
        f"/repos/{owner}/{repo}/code-scanning/analyses",
        {"ref": ref, "tool_name": "CodeQL", "per_page": "1"},
        token,
    )
    if isinstance(body, list) and body:
        analysis = body[0]
        return {
            "commit_sha": analysis.get("commit_sha"),
            "analysis_key": analysis.get("analysis_key"),
            "created_at": analysis.get("created_at"),
            "tool": analysis.get("tool"),
            "results_count": analysis.get("results_count"),
        }
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch a secret-free CodeQL alert snapshot.")
    parser.add_argument("--owner", required=True, help="repository owner")
    parser.add_argument("--repo", required=True, help="repository name")
    parser.add_argument("--ref", default="refs/heads/main", help="git ref (branch or PR)")
    parser.add_argument("--base-url", default="https://api.github.com")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    base_url = _validated_base_url(args.base_url)
    output_path = _validated_output(args.output)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    open_result = fetch_alerts(base_url, args.owner, args.repo, args.ref, "open", token)
    dismissed_result = fetch_alerts(base_url, args.owner, args.repo, args.ref, "dismissed", token)
    analysis = latest_analysis(base_url, args.owner, args.repo, args.ref, token)

    complete = open_result["complete"] and dismissed_result["complete"]
    snapshot = {
        "schema_version": "codeql-snapshot-1.0",
        "status": "COMPLETE" if complete else "BLOCKED",
        "api_metadata": {
            "base_url": base_url,
            "endpoints": [
                "/code-scanning/alerts",
                "/code-scanning/analyses",
            ],
            "authenticated": bool(token),
            "authorization_header": "REDACTED" if token else None,
            "fetched_at": datetime.now(tz=UTC).isoformat(),
            "ref": args.ref,
            "pagination": {
                "page_size": PAGE_SIZE,
                "open_retrieved": open_result["retrieved"],
                "dismissed_retrieved": dismissed_result["retrieved"],
                "complete": complete,
            },
        },
        "repository": f"{args.owner}/{args.repo}",
        "ref": args.ref,
        "latest_analysis": analysis,
        "severity_breakdown": _severity_breakdown(open_result["alerts"]),
        "alerts": [_normalize(alert) for alert in open_result["alerts"]],
        "dismissed_alerts": [_normalize(alert) for alert in dismissed_result["alerts"]],
    }
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(
        f"snapshot: {output_path} status={snapshot['status']} "
        f"open={open_result['retrieved']} dismissed={dismissed_result['retrieved']} "
        f"authenticated={bool(token)}"
    )
    if not complete:
        print("BLOCKED: incomplete pagination — a next page remained after the page cap")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
