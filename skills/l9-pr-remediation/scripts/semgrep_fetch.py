#!/usr/bin/env python3
"""Fail-closed, secret-safe Semgrep App findings snapshot fetcher (stdlib only).

Retrieves the complete open finding set for a deployment (optionally scoped to
one repository and ref) from the Semgrep AppSec Platform API and writes a
single secret-free JSON snapshot (`semgrep-findings-before.json` by convention).

Read-only against Semgrep: this never starts a scan, never POSTs a source
bundle, and never mutates finding or triage state. Authenticated *scan*
(``semgrep ci``, App upload) stays forbidden on a model-controlled surface —
that is ``run_pr_security.sh`` unsetting the token in a CE child. This module
is the Sonar-shaped **GET** of findings that already exist.

Authentication: ``capability_bind.bind_first`` resolves SEMGREP_APP_TOKEN
in-process (already-present env, then ``~/.infisical/l9-machine.json`` via
the Infisical HTTP client). AWS is not a bind path. The value is never exported to
``os.environ``, never printed, and never written to the snapshot. The retired
capability broker is not involved. The App findings API is not public: without
a bound token the snapshot is BLOCKED, never an empty pass. Authorization
headers are redacted.

Semgrep findings never block merge (that is the PR board's call); they are
work the remediator resolves when they exist.

Fail-closed: if pagination cannot prove the set is complete (a full page
remains after the page cap), the snapshot is marked BLOCKED and the process
exits non-zero rather than emitting a smaller-than-real set.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

_OPS_SECRETS = Path(__file__).resolve().parents[3] / "ops" / "secrets"
_OPS_LIB = Path(__file__).resolve().parents[3] / "ops" / "lib"
for _extra in (_OPS_SECRETS, _OPS_LIB):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from capability_bind import bind_first  # noqa: E402
from safe_https import https_exchange  # noqa: E402
from surface_trust import classify  # noqa: E402

TOKEN_ENV = ("SEMGREP_APP_TOKEN",)
DEPLOYMENT_ENV = "SEMGREP_DEPLOYMENT_SLUG"

_SEMGREP_HOSTS = frozenset({"semgrep.dev"})
_TOKENS: dict[int, str | None] = {}

PAGE_SIZE = 100
MAX_PAGES = 50  # 100 * 50 = 5000 findings; a repo above this needs an explicit wider run
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?$")


class DirectTransport:
    """HTTPS transport; bearer only when a token was bound in-process.

    The token never appears in ``repr``/``vars`` output and is never written
    to the snapshot. Surface trust is recorded for the receipt, not consulted
    to refuse a bound inventory token.
    """

    def __init__(self, base_url: str, token: str | None, surface: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.surface_trust = classify(surface).trust_class
        _TOKENS[id(self)] = token

    @property
    def authenticated(self) -> bool:
        return bool(_TOKENS.get(id(self)))

    def get(self, path: str, params: dict[str, str] | None = None) -> dict:
        query = urllib.parse.urlencode(
            {k: v for k, v in (params or {}).items() if v not in (None, "")}
        )
        suffix = f"?{query}" if query else ""
        request = urllib.request.Request(f"{self.base_url}{path}{suffix}", method="GET")
        token = _TOKENS.get(id(self))
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with https_exchange(
                request, timeout=45, allowed_hosts=_SEMGREP_HOSTS, label="Semgrep API URL"
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise SystemExit(f"BLOCKED: Semgrep {path} returned HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise SystemExit(f"BLOCKED: Semgrep {path} request failed: {exc}") from exc
        if not isinstance(body, dict):
            raise SystemExit(f"BLOCKED: Semgrep {path} returned a non-object payload")
        return body


def build_transport(base_url: str, surface: str | None = None) -> DirectTransport:
    """Authenticated when an inventory token can be bound, on any surface.

    Bind is use, not export: an already-present env value, else the Infisical
    machine profile (``~/.infisical/l9-machine.json`` over HTTP). The Infisical
    CLI keyring and AWS are not bind paths. A miss is a vault miss, not a
    reason to paste a token.
    """
    token = bind_first(*TOKEN_ENV)
    if not token:
        print(
            "semgrep_fetch: SEMGREP_APP_TOKEN unbound "
            "(not in env; Infisical machine profile absent or missed); "
            "App findings cannot be read — do not paste a token",
            file=sys.stderr,
        )
    return DirectTransport(base_url, token, surface)


def _validated_base_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or parsed.hostname != "semgrep.dev":
        raise SystemExit("BLOCKED: --base-url must be https://semgrep.dev")
    return value.rstrip("/")


def _validated_output(value: str) -> Path:
    base = Path.cwd().resolve()
    resolved = (base / value).resolve()
    if resolved != base and base not in resolved.parents:
        raise SystemExit("BLOCKED: --output must stay within the working directory")
    return resolved


def _validated_slug(value: str) -> str:
    if not _SLUG_RE.match(value):
        raise SystemExit("BLOCKED: --deployment must be a Semgrep deployment slug")
    return value


def _validated_repo(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if not _REPO_RE.match(value):
        raise SystemExit("BLOCKED: --repo must be a repository name or owner/name")
    return value


def _scope_params(
    repo: str | None, ref: str | None, pull_request: str | None, issue_type: str, status: str
) -> dict[str, str]:
    params = {"issue_type": issue_type, "status": status}
    if repo:
        params["repos"] = repo
    if pull_request:
        params["ref"] = f"refs/pull/{pull_request}/head"
    elif ref:
        params["ref"] = ref
    return params


def _slugs_from_deployments_payload(payload: dict) -> list[str]:
    slugs: list[str] = []
    deployment = payload.get("deployment")
    if isinstance(deployment, dict) and deployment.get("slug"):
        slugs.append(str(deployment["slug"]))
    deployments = payload.get("deployments")
    if isinstance(deployments, list):
        for item in deployments:
            if isinstance(item, dict) and item.get("slug"):
                slugs.append(str(item["slug"]))
    if payload.get("slug") and isinstance(payload.get("slug"), str):
        slugs.append(payload["slug"])
    seen: set[str] = set()
    unique: list[str] = []
    for slug in slugs:
        if slug not in seen:
            seen.add(slug)
            unique.append(slug)
    return unique


def resolve_deployment(transport: DirectTransport, explicit: str | None) -> str:
    if explicit:
        return _validated_slug(explicit)
    env_slug = os.environ.get(DEPLOYMENT_ENV) or ""
    if env_slug:
        return _validated_slug(env_slug)
    payload = transport.get("/deployments")
    slugs = _slugs_from_deployments_payload(payload)
    if len(slugs) == 1:
        return _validated_slug(slugs[0])
    if not slugs:
        raise SystemExit("BLOCKED: Semgrep returned no deployment slug — pass --deployment")
    raise SystemExit("BLOCKED: Semgrep token can see multiple deployments — pass --deployment")


def fetch_findings(transport: DirectTransport, slug: str, scope: dict[str, str]) -> dict:
    findings: list[dict] = []
    pages = 0
    truncated = False
    while pages < MAX_PAGES:
        params = {**scope, "page": str(pages), "page_size": str(PAGE_SIZE)}
        payload = transport.get(f"/deployments/{slug}/findings", params)
        batch = payload.get("findings")
        if not isinstance(batch, list):
            raise SystemExit("BLOCKED: unexpected Semgrep findings payload (not a list)")
        findings.extend(batch)
        pages += 1
        if len(batch) < PAGE_SIZE:
            break
    else:
        truncated = True
    return {
        "findings": findings,
        "retrieved": len(findings),
        "pages": pages,
        "complete": not truncated,
    }


def _normalize(finding: dict) -> dict:
    location = finding.get("location") or {}
    rule = finding.get("rule") or {}
    repository = finding.get("repository") or {}
    return {
        "id": finding.get("id"),
        "state": finding.get("state"),
        "status": finding.get("status"),
        "severity": finding.get("severity"),
        "confidence": finding.get("confidence") or rule.get("confidence"),
        "rule_name": finding.get("rule_name") or rule.get("name"),
        "message": finding.get("rule_message") or rule.get("message"),
        "path": location.get("file_path"),
        "start_line": location.get("line"),
        "end_line": location.get("end_line"),
        "ref": finding.get("ref"),
        "repository": repository.get("name"),
        "categories": finding.get("categories") or rule.get("category"),
    }


def _severity_breakdown(findings: list[dict]) -> dict[str, int]:
    breakdown: dict[str, int] = {}
    for finding in findings:
        level = str(finding.get("severity") or "unknown")
        breakdown[level] = breakdown.get(level, 0) + 1
    return breakdown


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch a secret-free Semgrep App findings snapshot."
    )
    parser.add_argument("--deployment", help="Semgrep deployment slug")
    parser.add_argument("--repo", help="repository name or owner/name")
    parser.add_argument("--ref", help="git ref (mutually exclusive with --pull-request)")
    parser.add_argument("--pull-request", help="pull request number (sends refs/pull/{n}/head)")
    parser.add_argument("--issue-type", default="sast", help="sast (default), sca, or ai_sast")
    parser.add_argument("--status", default="open", help="open (default), fixed, ignored, …")
    parser.add_argument("--base-url", default="https://semgrep.dev/api/v1")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.ref and args.pull_request:
        raise SystemExit("BLOCKED: pass only one of --ref / --pull-request")

    base_url = _validated_base_url(args.base_url)
    output_path = _validated_output(args.output)
    repo = _validated_repo(args.repo)
    transport = build_transport(base_url)
    if not transport.authenticated:
        raise SystemExit("BLOCKED: SEMGREP_APP_TOKEN is required for the App findings API")

    slug = resolve_deployment(transport, args.deployment)
    scope = _scope_params(repo, args.ref, args.pull_request, args.issue_type, args.status)
    result = fetch_findings(transport, slug, scope)
    normalized = [_normalize(item) for item in result["findings"]]

    snapshot = {
        "schema_version": "semgrep-snapshot-1.0",
        "status": "COMPLETE" if result["complete"] else "BLOCKED",
        "api_metadata": {
            "base_url": base_url,
            "endpoints": ["/deployments", f"/deployments/{slug}/findings"],
            "authenticated": True,
            "authorization_header": "REDACTED",
            "fetched_at": datetime.now(tz=UTC).isoformat(),
            "request_scope": scope,
            "pagination": {
                "page_size": PAGE_SIZE,
                "pages": result["pages"],
                "retrieved": result["retrieved"],
                "complete": result["complete"],
            },
        },
        "deployment": slug,
        "repository": repo,
        "severity_breakdown": _severity_breakdown(normalized),
        "findings": normalized,
    }
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(
        f"snapshot: {output_path} status={snapshot['status']} "
        f"findings={result['retrieved']} deployment={slug} authenticated=true"
    )
    if not result["complete"]:
        print("BLOCKED: incomplete pagination — a full page remained after the page cap")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
