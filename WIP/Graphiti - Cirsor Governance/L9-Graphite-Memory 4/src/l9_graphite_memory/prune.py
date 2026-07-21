#!/usr/bin/env python3
"""Weekly prune report — stale edges and episodes (dry-run default, no auto-delete)."""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

STALE_EDGE_DAYS = int(os.environ.get("GRAPHITI_PRUNE_EDGE_DAYS", "90"))
STALE_EPISODE_DAYS = int(os.environ.get("GRAPHITI_PRUNE_EPISODE_DAYS", "180"))


def _mcp_call(tool: str, params: dict[str, Any]) -> Any:
    url = os.environ.get("GRAPHITI_MCP_URL", "http://127.0.0.1:8100/mcp/").rstrip("/")
    if not url.endswith("/mcp"):
        url = f"{url}/mcp/"
    token = os.environ.get("GRAPHITI_MCP_TOKEN", "")
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": "prune", "method": "tools/call", "params": {"name": tool, "arguments": params}}
    ).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    _ssl_ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=20, context=_ssl_ctx) as resp:
        body = json.loads(resp.read())
    if "error" in body:
        raise RuntimeError(json.dumps(body["error"]))
    content = body.get("result", {}).get("content", [])
    text = content[0].get("text", "") if content else ""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}


def _load_registry() -> dict[str, Any]:
    reg_path = Path(__file__).parent / "group_registry.yaml"
    if not reg_path.is_file():
        return {}
    import yaml

    return yaml.safe_load(reg_path.read_text(encoding="utf-8")) or {}


def _fetch_episodes(group: str) -> list[dict[str, Any]]:
    try:
        result = _mcp_call("get_episodes", {"group_id": group, "last_n": 500})
        episodes = result.get("episodes", []) if isinstance(result, dict) else []
        if episodes:
            return episodes
    except (RuntimeError, urllib.error.URLError):
        pass
    try:
        result = _mcp_call("search_facts", {"query": "", "group_id": group, "max_facts": 200})
        if isinstance(result, dict):
            return list(result.get("facts") or result.get("results") or [])
        if isinstance(result, list):
            return result
    except (RuntimeError, urllib.error.URLError):
        pass
    return []


def run_prune_report(dry_run: bool = True) -> dict[str, Any]:
    reg = _load_registry()
    ws_group = reg.get("workspace_group", "igor-workspace")
    all_groups = list((reg.get("repos") or {}).keys()) + [ws_group]
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=STALE_EDGE_DAYS)
    episode_cutoff = now - timedelta(days=STALE_EPISODE_DAYS)
    report: dict[str, Any] = {
        "generated_at": now.isoformat(),
        "dry_run": dry_run,
        "stale_edges": [],
        "expired_episodes": [],
        "conflict_episodes": [],
        "old_episodes": [],
        "summary": {},
    }

    for group in all_groups:
        for ep in _fetch_episodes(group):
            if not isinstance(ep, dict):
                continue
            ts = ep.get("created_at") or ep.get("reference_time", "")
            try:
                ep_time = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue
            body_str = json.dumps(ep.get("episode_body", ep.get("content", "")))
            name = ep.get("name", "")
            if group == ws_group and "integration_edge" in body_str and ep_time < stale_cutoff:
                report["stale_edges"].append(
                    {"group": group, "name": name, "days_old": (now - ep_time).days, "action": "REVIEW_DEMOTE"}
                )
            if "conflicts_with" in body_str.lower() or "ConflictsWith" in body_str:
                report["conflict_episodes"].append(
                    {"group": group, "name": name, "action": "HUMAN_REVIEW_REQUIRED"}
                )
            if ep_time < episode_cutoff and not str(name).startswith("manifest:"):
                report["old_episodes"].append(
                    {"group": group, "name": name, "days_old": (now - ep_time).days, "action": "REVIEW_DEMOTE"}
                )

    report["summary"] = {
        "stale_edges": len(report["stale_edges"]),
        "expired_episodes": len(report["expired_episodes"]),
        "conflicts": len(report["conflict_episodes"]),
        "old_episodes": len(report["old_episodes"]),
        "note": "No data deleted. All entries require human review.",
        "telemetry": {"graphiti.prune.demoted_count": len(report["stale_edges"]) + len(report["old_episodes"])},
    }
    out = Path(__file__).parent / f"prune_report_{now.strftime('%Y%m%d')}.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    report["report_file"] = str(out)
    return report


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Graphiti prune report (dry-run default)")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true", help="Reserved — no auto-delete yet")
    args = parser.parse_args()
    dry_run = not args.apply
    env_path = Path.home() / ".cursor" / "graphiti.env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())
    report = run_prune_report(dry_run=dry_run)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
