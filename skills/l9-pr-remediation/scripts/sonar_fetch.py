#!/usr/bin/env python3
"""Fail-closed, secret-safe SonarCloud issue snapshot fetcher (stdlib only).

Retrieves the complete issue set for a project's branch or pull request, plus the
distinct rule metadata, the quality gate, and headline measures, and writes a single
secret-free JSON snapshot (`sonarcloud-issues-before.json` by convention).

Read-only against SonarCloud: this never mutates issue or hotspot state. The API token
is read from the environment by reference only (SONAR_TOKEN) and is never printed,
stored, or written to the snapshot; Authorization headers are redacted in the receipt.

Fail-closed: if pagination cannot retrieve every reported issue, the snapshot is marked
BLOCKED and the process exits non-zero rather than emitting a smaller-than-real set.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

MEASURE_METRICS = [
    "bugs",
    "vulnerabilities",
    "code_smells",
    "security_hotspots",
    "coverage",
    "duplicated_lines_density",
    "reliability_rating",
    "security_rating",
    "sqale_rating",
]
PAGE_SIZE = 500
MAX_PAGES = 40  # 500 * 40 = 20000 issues; SonarCloud caps /issues/search near 10000


def _request(base_url: str, path: str, params: dict[str, str], token: str | None) -> dict:
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
    url = f"{base_url.rstrip('/')}{path}?{query}"
    request = urllib.request.Request(url, method="GET")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=45) as response:  # noqa: S310 (https only)
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise SystemExit(f"BLOCKED: SonarCloud {path} returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise SystemExit(f"BLOCKED: SonarCloud {path} request failed: {exc}") from exc


def _validated_base_url(value: str) -> str:
    """Sanitize the base URL before any network use (S8703 / SSRF).

    Require HTTPS and an allow-listed SonarCloud host so a crafted --base-url cannot
    redirect requests (and any Authorization header) to an attacker-controlled or
    internal endpoint. A self-hosted SonarQube would extend this allow-list explicitly.
    """
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or parsed.hostname != "sonarcloud.io":
        raise SystemExit("BLOCKED: --base-url must be https://sonarcloud.io")
    return value


def _validated_output(value: str) -> Path:
    """Sanitize the output path before any file write (S8707 / path traversal).

    Resolve the requested path and require it to stay within the current working
    directory, so a crafted --output cannot escape the working tree. The snapshot is a
    working-directory artifact (e.g. sonarcloud-issues-before.json), so this preserves
    the intended use while making arbitrary out-of-tree writes fail closed.
    """
    base = Path.cwd().resolve()
    resolved = (base / value).resolve()
    if resolved != base and base not in resolved.parents:
        raise SystemExit("BLOCKED: --output must stay within the working directory")
    return resolved


def _scope_params(branch: str | None, pull_request: str | None) -> dict[str, str]:
    if pull_request:
        return {"pullRequest": pull_request}
    if branch:
        return {"branch": branch}
    return {}


def fetch_issues(
    base_url: str, project: str, organization: str, scope: dict[str, str], token: str | None
) -> dict:
    issues: list[dict] = []
    page = 1
    total = None
    while page <= MAX_PAGES:
        params = {
            "componentKeys": project,
            "organization": organization,
            "ps": str(PAGE_SIZE),
            "p": str(page),
            "additionalFields": "rules",
            **scope,
        }
        payload = _request(base_url, "/issues/search", params, token)
        total = payload.get("total", 0)
        issues.extend(payload.get("issues", []))
        if len(issues) >= total or not payload.get("issues"):
            break
        page += 1
    complete = total is not None and len(issues) == total
    return {"issues": issues, "total": total, "retrieved": len(issues), "complete": complete}


def fetch_rules(base_url: str, rule_keys: list[str], organization: str, token: str | None) -> dict:
    rules: dict[str, dict] = {}
    for rule_key in sorted(set(rule_keys)):
        payload = _request(
            base_url, "/rules/show", {"key": rule_key, "organization": organization}, token
        )
        rule = payload.get("rule", {})
        rules[rule_key] = {
            "name": rule.get("name"),
            "lang": rule.get("lang"),
            "type": rule.get("type"),
            "severity": rule.get("severity"),
            "tags": rule.get("sysTags") or rule.get("tags"),
            "remediation": rule.get("remFnType"),
        }
    return rules


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch a secret-free SonarCloud issue snapshot.")
    parser.add_argument("--project", required=True, help="sonar.projectKey")
    parser.add_argument("--organization", required=True, help="sonar.organization")
    parser.add_argument("--branch", help="analyzed branch (mutually exclusive with --pull-request)")
    parser.add_argument(
        "--pull-request", help="pull request number (mutually exclusive with --branch)"
    )
    parser.add_argument("--base-url", default="https://sonarcloud.io/api")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.branch and args.pull_request:
        raise SystemExit("BLOCKED: pass only one of --branch / --pull-request")

    # Sanitize both tainted CLI inputs before they reach a network or file-system sink.
    base_url = _validated_base_url(args.base_url)
    output_path = _validated_output(args.output)
    token = os.environ.get("SONAR_TOKEN") or os.environ.get("SONARCLOUD_TOKEN")
    scope = _scope_params(args.branch, args.pull_request)

    issues_result = fetch_issues(base_url, args.project, args.organization, scope, token)
    rule_keys = [issue.get("rule", "") for issue in issues_result["issues"] if issue.get("rule")]
    rules = fetch_rules(base_url, rule_keys, args.organization, token)

    gate = _request(
        base_url,
        "/qualitygates/project_status",
        {"projectKey": args.project, "organization": args.organization, **scope},
        token,
    )
    measures = _request(
        base_url,
        "/measures/component",
        {
            "component": args.project,
            "organization": args.organization,
            "metricKeys": ",".join(MEASURE_METRICS),
            **scope,
        },
        token,
    )

    # The analysis identifier from the quality gate. A per-issue `hash` is a line hash,
    # not the analyzed revision, so it must not stand in for identity binding.
    revision = gate.get("projectStatus", {}).get("analysisId")
    snapshot = {
        "schema_version": "sonarcloud-snapshot-1.0",
        "status": "COMPLETE" if issues_result["complete"] else "BLOCKED",
        "api_metadata": {
            "base_url": base_url,
            "endpoints": [
                "/issues/search",
                "/rules/show",
                "/qualitygates/project_status",
                "/measures/component",
            ],
            "authenticated": bool(token),
            "authorization_header": "REDACTED" if token else None,
            "fetched_at": datetime.now(tz=UTC).isoformat(),
            "request_scope": scope or {"scope": "main-analysis"},
            "pagination": {
                "page_size": PAGE_SIZE,
                "total": issues_result["total"],
                "retrieved": issues_result["retrieved"],
            },
        },
        "project": args.project,
        "organization": args.organization,
        "branch_or_pull_request": scope or {"scope": "main-analysis"},
        "analysis_revision": revision,
        "quality_gate": gate.get("projectStatus"),
        "measures": measures.get("component", {}).get("measures", []),
        "rules": rules,
        "issues": issues_result["issues"],
    }
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(
        f"snapshot: {output_path} status={snapshot['status']} "
        f"issues={issues_result['retrieved']}/{issues_result['total']} "
        f"rules={len(rules)} authenticated={bool(token)}"
    )
    if not issues_result["complete"]:
        print("BLOCKED: incomplete pagination — retrieved count does not equal API total")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
