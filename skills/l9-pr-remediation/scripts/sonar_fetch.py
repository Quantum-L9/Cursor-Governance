#!/usr/bin/env python3
"""Fail-closed, secret-safe SonarCloud issue snapshot fetcher (stdlib only).

Retrieves the complete issue set for a project's branch or pull request, plus the
distinct rule metadata, the quality gate, and headline measures, and writes a single
secret-free JSON snapshot (`sonarcloud-issues-before.json` by convention).

Read-only against SonarCloud: this never mutates issue or hotspot state.

Authenticated access is BROKERED on model-controlled surfaces (contract §13). This
process does not read SONAR_TOKEN from the environment when it is running inside an
agent runtime, because a token there is a token the model possesses. It asks the
shared capability plane for `sonar.read_issues` and receives sanitized results:

    l9-pr-remediation -> capability client -> L9 broker -> Sonar API

Repository identity still comes from sonar-project.properties via --project /
--organization; the broker receives project/organization identifiers, never a token.
A trusted operator running this by hand keeps the direct path. Either way no token is
printed, stored, or written to the snapshot; Authorization headers are redacted.

Fail-closed: if pagination cannot retrieve every reported issue, the snapshot is marked
BLOCKED and the process exits non-zero rather than emitting a smaller-than-real set.
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

# The capability plane lives in ops/secrets (the SSOT). Import it rather than
# re-implementing a second client inside a skill.
_OPS_SECRETS = Path(__file__).resolve().parents[3] / "ops" / "secrets"
_OPS_LIB = Path(__file__).resolve().parents[3] / "ops" / "lib"
for _extra in (_OPS_SECRETS, _OPS_LIB):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from capability_client import CapabilityClient  # noqa: E402
from safe_https import https_exchange  # noqa: E402
from surface_trust import classify, require_trusted  # noqa: E402

_SONAR_HOSTS = frozenset({"sonarcloud.io"})

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


class DirectTransport:
    """Token-in-process path. TRUSTED OPERATOR ONLY.

    Constructing this on a model-controlled surface raises, so the direct path
    cannot be reached from an agent runtime even by importing this module.
    """

    def __init__(self, base_url: str, token: str | None, surface: str | None = None) -> None:
        if token:
            require_trusted(surface)
        self.base_url = base_url.rstrip("/")
        self._token = token

    @property
    def authenticated(self) -> bool:
        return bool(self._token)

    def get(self, path: str, params: dict[str, str]) -> dict:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
        request = urllib.request.Request(f"{self.base_url}{path}?{query}", method="GET")
        if self._token:
            request.add_header("Authorization", f"Bearer {self._token}")
        try:
            with https_exchange(
                request, timeout=45, allowed_hosts=_SONAR_HOSTS, label="SonarCloud URL"
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise SystemExit(
                f"BLOCKED: SonarCloud {path} returned HTTP {exc.code}: {detail}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise SystemExit(f"BLOCKED: SonarCloud {path} request failed: {exc}") from exc


class BrokerTransport:
    """Capability path. The credential stays beyond the model boundary.

    Only registry-declared caller params are forwarded; project and organization
    are workspace-derived on the broker side, so this process cannot ask for a
    repository it is not working in.
    """

    CAPABILITY = "sonar.read_issues"

    def __init__(self, client: CapabilityClient) -> None:
        self.client = client

    @property
    def authenticated(self) -> bool:
        return True

    def get(self, path: str, params: dict[str, str]) -> dict:
        forward = {
            key: str(value)
            for key, value in params.items()
            if key in ("branch", "pullRequest", "p", "ps") and value not in (None, "")
        }
        forward["path"] = path
        try:
            return self.client.invoke(self.CAPABILITY, forward).get("result", {})
        except (LookupError, RuntimeError) as exc:
            raise SystemExit(f"BLOCKED: brokered SonarCloud {path} failed: {exc}") from exc


def build_transport(base_url: str, surface: str | None = None) -> DirectTransport | BrokerTransport:
    """Pick the transport from the caller's trust class, not from a flag.

    A model-controlled surface gets the broker or nothing. It never falls back to
    reading SONAR_TOKEN, because that fallback is the vulnerability.
    """
    trust = classify(surface)
    if trust.raw_secret_allowed:
        token = os.environ.get("SONAR_TOKEN") or os.environ.get("SONARCLOUD_TOKEN")
        return DirectTransport(base_url, token, surface)

    client = CapabilityClient()
    status = client.status(BrokerTransport.CAPABILITY)
    if status.status == "ENABLED":
        return BrokerTransport(client)
    # Unauthenticated public read. Honest degradation: fewer issues are visible,
    # and the snapshot records that it was unauthenticated (contract §18).
    print(
        f"sonar_fetch: {BrokerTransport.CAPABILITY} {status.status} ({status.detail}); "
        "continuing UNAUTHENTICATED — private findings will be absent",
        file=sys.stderr,
    )
    return DirectTransport(base_url, None, surface)


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
    transport: DirectTransport | BrokerTransport,
    project: str,
    organization: str,
    scope: dict[str, str],
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
        payload = transport.get("/issues/search", params)
        total = payload.get("total", 0)
        issues.extend(payload.get("issues", []))
        if len(issues) >= total or not payload.get("issues"):
            break
        page += 1
    complete = total is not None and len(issues) == total
    return {"issues": issues, "total": total, "retrieved": len(issues), "complete": complete}


def fetch_rules(
    transport: DirectTransport | BrokerTransport, rule_keys: list[str], organization: str
) -> dict:
    rules: dict[str, dict] = {}
    for rule_key in sorted(set(rule_keys)):
        payload = transport.get("/rules/show", {"key": rule_key, "organization": organization})
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
    transport = build_transport(base_url)
    scope = _scope_params(args.branch, args.pull_request)

    issues_result = fetch_issues(transport, args.project, args.organization, scope)
    rule_keys = [issue.get("rule", "") for issue in issues_result["issues"] if issue.get("rule")]
    rules = fetch_rules(transport, rule_keys, args.organization)

    gate = transport.get(
        "/qualitygates/project_status",
        {"projectKey": args.project, "organization": args.organization, **scope},
    )
    measures = transport.get(
        "/measures/component",
        {
            "component": args.project,
            "organization": args.organization,
            "metricKeys": ",".join(MEASURE_METRICS),
            **scope,
        },
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
            "authenticated": transport.authenticated,
            "authorization_header": "REDACTED" if transport.authenticated else None,
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
        f"rules={len(rules)} authenticated={transport.authenticated}"
    )
    if not issues_result["complete"]:
        print("BLOCKED: incomplete pagination — retrieved count does not equal API total")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
