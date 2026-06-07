#!/usr/bin/env python3
"""Graphiti memory CLI — HTTP MCP client for VPS Graphiti stack."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from circuit_breaker import CircuitBreaker
from episode_contract import EpisodeContract, FORBIDDEN_GROUPS
from group_resolver import load_registry, resolve_group_id
from rate_limiter import RateLimiter

_ENV_PATH = Path.home() / ".cursor" / "graphiti.env"
_circuit = CircuitBreaker()
_rate = RateLimiter()


def load_env() -> None:
    if _ENV_PATH.is_file():
        for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


def memory_enabled() -> bool:
    return os.environ.get("GRAPHITI_MEMORY_ENABLED", "1").strip() not in ("0", "false", "False")


def mcp_url() -> str:
    base = os.environ.get("GRAPHITI_MCP_URL", "http://127.0.0.1:8100/mcp/").rstrip("/")
    return base if base.endswith("/mcp") or base.endswith("/mcp/") else f"{base}/mcp/"


def mcp_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    token = os.environ.get("GRAPHITI_MCP_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def mcp_call(method: str, params: Optional[dict[str, Any]] = None, timeout: int = 30) -> dict[str, Any]:
    if not _circuit.can_execute():
        raise RuntimeError("circuit breaker OPEN")
    payload = {"jsonrpc": "2.0", "id": "cli", "method": method, "params": params or {}}
    req = urllib.request.Request(
        mcp_url(),
        data=json.dumps(payload).encode(),
        headers=mcp_headers(),
        method="POST",
    )
    _ssl_ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        _circuit.record_failure()
        detail = exc.read().decode()[:500]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        _circuit.record_failure()
        raise RuntimeError(f"MCP unreachable: {exc.reason}") from exc

    if "error" in body:
        _circuit.record_failure()
        raise RuntimeError(json.dumps(body["error"]))
    _circuit.record_success()
    return body.get("result", body)


def call_tool(name: str, arguments: Optional[dict[str, Any]] = None) -> Any:
    result = mcp_call("tools/call", {"name": name, "arguments": arguments or {}})
    content = result.get("content", []) if isinstance(result, dict) else []
    if content and isinstance(content[0], dict):
        text = content[0].get("text", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return result


def health_check() -> int:
    load_env()
    if not memory_enabled():
        print(json.dumps({"healthy": False, "reason": "GRAPHITI_MEMORY_ENABLED=0"}))
        return 1
    resolved = resolve_group_id()
    out: dict[str, Any] = {
        "healthy": False,
        "circuit": _circuit.status(),
        "resolver": resolved,
    }
    try:
        health_url = mcp_url().replace("/mcp/", "/healthcheck").replace("/mcp", "/healthcheck")
        req = urllib.request.Request(health_url, headers=mcp_headers())
        _ssl_ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=10, context=_ssl_ctx) as resp:
            out["mcp"] = json.loads(resp.read().decode())
        out["healthy"] = True
        print(json.dumps(out, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)
        print(json.dumps(out, indent=2))
        return 1


def cmd_resolve(_args: argparse.Namespace) -> int:
    load_env()
    print(json.dumps(resolve_group_id(Path.cwd()), indent=2))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    load_env()
    resolved = resolve_group_id(Path.cwd())
    group_id = resolved.get("group_id")
    if not group_id:
        raise SystemExit(resolved.get("error", "no group_id"))
    budget = int(os.environ.get("MEMORY_TOKEN_BUDGET", "400"))
    data = call_tool(
        "search_facts",
        {"query": args.query, "group_id": group_id, "max_facts": args.limit},
    )
    print(json.dumps({"group_id": group_id, "budget_tokens": budget, "results": data}, indent=2))
    return 0


def cmd_write(args: argparse.Namespace) -> int:
    load_env()
    resolved = resolve_group_id(Path.cwd())
    if resolved.get("readonly"):
        raise SystemExit(f"write blocked: {resolved.get('error') or resolved.get('warning')}")
    group_id = resolved.get("group_id")
    if not group_id or group_id in FORBIDDEN_GROUPS:
        raise SystemExit("forbidden or missing group_id")
    if not _rate.allow():
        raise SystemExit("rate limited")
    now = datetime.now(timezone.utc)
    contract = EpisodeContract(
        name=f"{args.kind}-{group_id}-{int(now.timestamp())}",
        episode_body=args.body,
        source="json" if args.body.strip().startswith("{") else "text",
        source_description=f"CLI write kind={args.kind}",
        reference_time=now,
        group_id=group_id,
        kind=args.kind,
    )
    if args.dry_run:
        print(json.dumps(contract.to_mcp_payload(), indent=2))
        return 0
    result = call_tool("add_episode", contract.to_mcp_payload())
    _rate.record()
    print(json.dumps(result, indent=2))
    return 0


def _read_memory_bank(repo: Path) -> str:
    parts: list[str] = []
    bank = repo / "memory-bank"
    for name in ("activeContext.md", "tasks.md", "progress.md", "tech-debt.md"):
        path = bank / name
        if path.is_file():
            parts.append(f"## {name}\n{path.read_text(encoding='utf-8')[:2000]}")
    return "\n\n".join(parts)


def cmd_inject(args: argparse.Namespace) -> int:
    load_env()
    repo = Path.cwd()
    resolved = resolve_group_id(repo)
    group_id = resolved.get("group_id") or "igor-workspace"
    task_sig = hashlib.sha256(args.task.encode()).hexdigest()[:16]
    prefetch_text = ""
    try:
        prefetch_text = str(
            call_tool("search_facts", {"query": args.task, "group_id": group_id, "max_facts": 8})
        )[: int(os.environ.get("MEMORY_TOKEN_BUDGET", "400")) * 4]
    except Exception:  # noqa: BLE001 — degrade gracefully
        prefetch_text = ""
    bank = _read_memory_bank(repo)
    state = {
        "group_id": group_id,
        "prefetch_ts": datetime.now(timezone.utc).isoformat(),
        "prefetch_hash": hashlib.sha256(prefetch_text.encode()).hexdigest(),
        "task_signature": task_sig,
        "memory_satisfied_for": [task_sig] if prefetch_text else [],
        "circuit_state": _circuit.status()["state"],
        "cache_ttl_minutes": 30,
    }
    state_dir = Path.home() / ".cursor" / "graphiti-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    conv = os.environ.get("CURSOR_CONVERSATION_ID", "default")
    (state_dir / f"{conv}.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "state_file": str(state_dir / f"{conv}.json"),
                "task_signature": task_sig,
                "memory_bank_chars": len(bank),
                "prefetch_chars": len(prefetch_text),
                "group_id": group_id,
            },
            indent=2,
        )
    )
    return 0


def _discover_bootstrap_sources(repo: Path) -> list[Path]:
    priority = [
        "AGENTS.md",
        "ARCHITECTURE.md",
        "README.md",
        "memory-bank/activeContext.md",
    ]
    found: list[Path] = []
    for rel in priority:
        path = repo / rel
        if path.is_file():
            found.append(path)
    adr = repo / "docs" / "adr"
    if adr.is_dir():
        found.extend(sorted(adr.glob("*.md"))[:10])
    return found


def cmd_bootstrap(args: argparse.Namespace) -> int:
    load_env()
    repo = Path.cwd()
    resolved = resolve_group_id(repo, explicit=args.group_id)
    group_id = resolved.get("group_id")
    if not group_id:
        raise SystemExit(resolved.get("error", "no group_id"))
    remote = ""
    import subprocess

    try:
        remote = subprocess.check_output(
            ["git", "-C", str(repo), "remote", "get-url", "origin"],
            text=True,
            timeout=5,
        ).strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        pass
    manifest = {
        "repo_slug": group_id,
        "github": remote,
        "stack": "Odoo 19 / PlasticOS" if (repo / "plasticos_base").is_dir() else "governance",
        "branch_model": {"dev": "Staging", "prod": "Production"},
        "sources": [str(p.relative_to(repo)) for p in _discover_bootstrap_sources(repo)],
    }
    body = json.dumps(manifest, indent=2)
    if args.dry_run:
        print(body)
        return 0
    return cmd_write(
        argparse.Namespace(body=body, kind="manifest", dry_run=False)
    )


def cmd_stats(args: argparse.Namespace) -> int:
    load_env()
    group_id = args.group or resolve_group_id(Path.cwd()).get("group_id")
    if not group_id:
        raise SystemExit("no group_id")
    data = call_tool("search_nodes", {"query": "*", "group_id": group_id, "max_nodes": 50})
    print(json.dumps({"group_id": group_id, "stats": data}, indent=2))
    return 0


def cmd_conflicts(_args: argparse.Namespace) -> int:
    load_env()
    group_id = resolve_group_id(Path.cwd()).get("group_id")
    if not group_id:
        raise SystemExit("no group_id")
    data = call_tool("search_facts", {"query": "conflicts_with", "group_id": group_id, "max_facts": 20})
    print(json.dumps({"group_id": group_id, "conflicts": data}, indent=2))
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    from prune import run_prune_report

    load_env()
    report = run_prune_report(dry_run=not args.apply)
    print(json.dumps(report, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Graphiti memory CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("health")
    sub.add_parser("resolve")
    p_search = sub.add_parser("search")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=10)
    p_write = sub.add_parser("write")
    p_write.add_argument("body")
    p_write.add_argument("--kind", default="lesson")
    p_write.add_argument("--dry-run", action="store_true")
    p_inject = sub.add_parser("inject")
    p_inject.add_argument("task", default="session start")
    p_bootstrap = sub.add_parser("bootstrap")
    p_bootstrap.add_argument("--dry-run", action="store_true")
    p_bootstrap.add_argument("--group-id", default=None)
    p_stats = sub.add_parser("stats")
    p_stats.add_argument("--group", default=None)
    sub.add_parser("conflicts")
    p_prune = sub.add_parser("prune")
    p_prune.add_argument("--dry-run", action="store_true")
    p_prune.add_argument("--apply", action="store_true")

    args = parser.parse_args()
    handlers = {
        "health": lambda a: health_check(),
        "resolve": cmd_resolve,
        "search": cmd_search,
        "write": cmd_write,
        "inject": cmd_inject,
        "bootstrap": cmd_bootstrap,
        "stats": cmd_stats,
        "conflicts": cmd_conflicts,
        "prune": cmd_prune,
    }
    try:
        return handlers[args.cmd](args)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
