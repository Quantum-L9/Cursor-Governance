#!/usr/bin/env python3
"""Read SonarCloud results for a pull request — never run a scanner.

`sonar-scanner` publishes an analysis, so a local run would compete with
SonarCloud's own. This client only READS, with SONAR_TOKEN bound in-process by
capability_bind (Infisical, as this surface's machine identity) and sent only
as a header over safe_https to sonarcloud.io. The token never enters the
environment, argv, a file or a log; output is literal status plus the
quality-gate verdict and new issues.

    sonar_status.py --pr 123            quality gate + open issues for PR 123
    sonar_status.py --auto              resolve this branch's open PR (REST GET)
    sonar_status.py --ce-activity       recent analysis tasks (why analysis stalls)

Project key and organization come from sonar-project.properties.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
for _path in (HERE, HERE.parent / "secrets", HERE.parent / "lib"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import capability_bind as cb  # noqa: E402
import manifest  # noqa: E402
from safe_https import https_exchange  # noqa: E402

HOST = "sonarcloud.io"
API = f"https://{HOST}/api"
TIMEOUT = 20.0
TOKEN_NAMES = ("SONAR_TOKEN", "SONARCLOUD_TOKEN")


def project_key(workspace: Path) -> str:
    for name in ("sonar-project.properties", ".sonarcloud.properties"):
        path = workspace / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "sonar.projectKey" and value.strip():
                return value.strip()
    return ""


def get(path: str, params: dict[str, str], token: str, *, send: Any = None) -> dict[str, Any]:
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, method="GET", headers={"Authorization": f"Bearer {token}"})
    response = (send or https_exchange)(request, timeout=TIMEOUT, allowed_hosts=frozenset({HOST}), label="sonar")
    return json.loads(response.read() or b"{}")


def open_pr(workspace: Path) -> int | None:
    gh = shutil.which("gh")
    branch = subprocess.run(
        ["git", "-C", str(workspace), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=False
    ).stdout.strip()
    url = subprocess.run(
        ["git", "-C", str(workspace), "remote", "get-url", "origin"], capture_output=True, text=True, check=False
    ).stdout.strip()
    parts = url.rstrip("/").removesuffix(".git").replace(":", "/").split("/")
    if gh is None or not branch or branch == "HEAD" or len(parts) < 2:
        return None
    owner, name = parts[-2], parts[-1]
    proc = subprocess.run(
        [gh, "api", "--method", "GET", f"repos/{owner}/{name}/pulls", "-f", f"head={owner}:{branch}",
         "-f", "state=open", "--jq", ".[0].number // empty"],
        capture_output=True, text=True, timeout=15, check=False,
    )
    text = proc.stdout.strip()
    return int(text) if proc.returncode == 0 and text.isdigit() else None


def pr_report(key: str, pr: int, token: str, *, send: Any = None) -> dict[str, Any]:
    gate = get("qualitygates/project_status", {"projectKey": key, "pullRequest": str(pr)}, token, send=send)
    issues = get(
        "issues/search",
        {"componentKeys": key, "pullRequest": str(pr), "resolved": "false", "ps": "100"},
        token,
        send=send,
    )
    return {
        "pr": pr,
        "quality_gate": ((gate.get("projectStatus") or {}).get("status")) or "NONE",
        "issues": [
            {
                "rule": i.get("rule"),
                "severity": i.get("severity"),
                "path": str(i.get("component") or "").split(":", 1)[-1],
                "line": i.get("line"),
                "message": str(i.get("message") or "")[:300],
            }
            for i in issues.get("issues") or []
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pr", type=int)
    mode.add_argument("--auto", action="store_true")
    mode.add_argument("--ce-activity", action="store_true")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    if manifest.disabled():
        return 0
    workspace = args.workspace.resolve()
    key = project_key(workspace)
    if not key:
        print("sonar: SKIP — no sonar.projectKey in this workspace")
        return 0
    token = cb.bind_first(*TOKEN_NAMES)
    if not token:
        source = cb.literal_source(cb.bind_status("SONAR_TOKEN")["source"])
        print(f"sonar: SKIP — SONAR_TOKEN not bound (source={source})")
        return 0
    try:
        if args.ce_activity:
            data = get("ce/activity", {"component": key, "ps": "10"}, token)
            for task in data.get("tasks") or []:
                print(
                    f"sonar: task {task.get('submittedAt')} status={task.get('status')} "
                    f"type={task.get('type')} error={str(task.get('errorMessage') or '')[:200]}"
                )
            return 0
        pr = args.pr if args.pr is not None else open_pr(workspace)
        if pr is None:
            print("sonar: SKIP — no open PR for this branch")
            return 0
        report = pr_report(key, pr, token)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"sonar: unavailable ({type(exc).__name__})")
        return 0
    loaded = manifest.load()
    out = loaded.cache_root / "sonar" / f"{key}-pr-{report['pr']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"sonar: PR #{report['pr']} quality_gate={report['quality_gate']} open_issues={len(report['issues'])} ({out})")
    for issue in report["issues"][:20]:
        print(f"  {issue['path']}:{issue['line']}: [{issue['severity']}] {issue['rule']} — {issue['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
