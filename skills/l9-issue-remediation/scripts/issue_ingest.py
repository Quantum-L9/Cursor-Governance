#!/usr/bin/env python3
"""Ingest open GitHub issues for a fleet or single repo via gh (read-only).

Emits secret-free normalized JSON findings. Never prints tokens.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

REF_RE = re.compile(
    r"\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(\d+)\b|"
    r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\d+)"
)
_SECRETISH = re.compile(r"(?i)(token|secret|password|api[_-]?key)\s*[=:]\s*\S+")


_GH_REPO_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}")


def _validated_repo(value: str) -> str:
    """Return ``value`` once proven to be an ``owner/name`` slug.

    It is passed to ``gh`` as a command argument. The rule that matters is the
    leading character: a value such as ``--template=...`` is an ordinary string
    to ``subprocess`` but an option to ``gh``, which turns an issue query into an
    attacker-chosen gh invocation.
    """
    if not _GH_REPO_RE.fullmatch(value) or value.endswith((".", ".git")):
        raise SystemExit(f"BLOCKED: not a valid owner/name repository: {value!r}")
    return value


def _validated_output(value: str) -> Path:
    base = Path.cwd().resolve()
    resolved = (base / value).resolve()
    if resolved != base and base not in resolved.parents:
        raise SystemExit("BLOCKED: --output must stay within the working directory")
    return resolved


def _redact(text: str) -> str:
    return _SECRETISH.sub(r"\1=[REDACTED]", text or "")


def _gh_json(args: list[str]) -> object:
    if not shutil.which("gh"):
        raise SystemExit("BLOCKED: gh CLI not found on PATH")
    try:
        raw = subprocess.check_output(["gh", *args], text=True, timeout=180)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"BLOCKED: gh {' '.join(args[:4])} failed: {exc}") from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f"BLOCKED: gh error: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"BLOCKED: gh returned non-JSON: {exc}") from exc


def _extract_links(body: str) -> list[str]:
    links: list[str] = []
    for match in REF_RE.finditer(body or ""):
        if match.group(1) and match.group(2):
            links.append(f"{match.group(1)}#{match.group(2)}")
        elif match.group(3) and match.group(4):
            links.append(f"{match.group(3)}#{match.group(4)}")
    # stable unique
    seen: set[str] = set()
    out: list[str] = []
    for item in links:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _severity(labels: list[str], title: str) -> str:
    joined = " ".join(labels).lower() + " " + (title or "").lower()
    if any(x in joined for x in ("critical", "sev1", "p0")):
        return "critical"
    if any(x in joined for x in ("high", "sev2", "p1", "blocker", "blocking")):
        return "high"
    if any(x in joined for x in ("medium", "sev3", "p2")):
        return "medium"
    return "low"


def _normalize(full_name: str, issue: dict) -> dict:
    labels = [str(x.get("name", "")) for x in (issue.get("labels") or []) if isinstance(x, dict)]
    if labels and isinstance(issue.get("labels"), list) and isinstance(issue["labels"][0], str):
        labels = [str(x) for x in issue["labels"]]
    title = _redact(str(issue.get("title") or ""))
    body = _redact(str(issue.get("body") or ""))
    number = issue.get("number")
    return {
        "id": f"{full_name}#{number}",
        "repo": full_name,
        "number": number,
        "title": title,
        "body_excerpt": body[:800],
        "labels": labels,
        "severity": _severity(labels, title),
        "url": issue.get("url") or issue.get("html_url"),
        "updated_at": issue.get("updatedAt") or issue.get("updated_at"),
        "linked_issues": _extract_links(f"{title}\n{body}"),
        "state": issue.get("state") or "OPEN",
    }


def _list_repo_issues(full_name: str, limit: int) -> list[dict]:
    data = _gh_json(
        [
            "issue",
            "list",
            "--repo",
            full_name,
            "--state",
            "open",
            "--limit",
            str(limit),
            "--json",
            "number,title,body,labels,url,updatedAt,state",
        ]
    )
    if not isinstance(data, list):
        raise SystemExit(f"BLOCKED: unexpected issues payload for {full_name}")
    return [_normalize(full_name, row) for row in data]


def _repos_from_fleet(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    repos = payload.get("repos") or []
    out: list[str] = []
    for row in repos:
        name = row.get("full_name")
        if name:
            out.append(str(name))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fleet", help="fleet.json from fleet_discover.py")
    parser.add_argument("--repo", help="single owner/name")
    parser.add_argument("--limit-per-repo", type=int, default=50)
    parser.add_argument("--output", default="issues.json")
    args = parser.parse_args()
    if bool(args.fleet) == bool(args.repo):
        raise SystemExit("BLOCKED: provide exactly one of --fleet or --repo")
    if args.limit_per_repo < 1 or args.limit_per_repo > 200:
        raise SystemExit("BLOCKED: --limit-per-repo must be 1..200")

    if args.repo:
        repos = [_validated_repo(args.repo)]
    else:
        fleet_path = Path(args.fleet)
        if not fleet_path.is_file():
            raise SystemExit(f"BLOCKED: fleet file missing: {fleet_path}")
        repos = _repos_from_fleet(fleet_path.resolve())

    findings: list[dict] = []
    errors: list[str] = []
    for full_name in repos:
        try:
            findings.extend(_list_repo_issues(full_name, args.limit_per_repo))
        except SystemExit as exc:
            errors.append(str(exc))
            continue

    # Rank: severity then updated_at
    sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(
        key=lambda f: (sev_rank.get(str(f.get("severity")), 9), str(f.get("updated_at") or "")),
    )

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "repo_count": len(repos),
        "issue_count": len(findings),
        "errors": errors,
        "issues": findings,
    }
    path = _validated_output(args.output)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": len(errors) == 0 or len(findings) > 0,
                "issue_count": len(findings),
                "error_count": len(errors),
                "output": str(path),
            }
        )
    )
    return 0 if findings or not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
