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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from circuit_breaker import CircuitBreaker
from episode_contract import FORBIDDEN_GROUPS, EpisodeContract
from graphiti_env_loader import load_graphiti_env
from group_resolver import load_registry, resolve_group_id
from rate_limiter import RateLimiter

_circuit = CircuitBreaker()
_rate = RateLimiter()


def load_env() -> None:
    load_graphiti_env()


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


def mcp_call(
    method: str, params: dict[str, Any] | None = None, timeout: int = 30
) -> dict[str, Any]:
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


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    result = mcp_call("tools/call", {"name": name, "arguments": arguments or {}})
    content = result.get("content", []) if isinstance(result, dict) else []
    if content and isinstance(content[0], dict):
        text = content[0].get("text", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return result


def resolve_read_groups(group_id: str) -> list[str]:
    registry = load_registry()
    workspace = registry.get("workspace_group", "igor-workspace")
    return [group_id, workspace] if group_id != workspace else [group_id]


def _bootstrap_seed_name(group_id: str) -> str:
    return f"manifest:{group_id}:{hashlib.sha256(group_id.encode()).hexdigest()[:8]}"


def _facts_from_search(data: Any) -> list[Any]:
    if isinstance(data, dict):
        return list(data.get("facts") or data.get("results") or data.get("nodes") or [])
    if isinstance(data, list):
        return data
    return []


def _search_group(query: str, group_id: str, limit: int = 10) -> list[Any]:
    errors: list[str] = []
    for tool, arg_key in (("search_facts", "max_facts"), ("search_nodes", "max_nodes")):
        try:
            data = call_tool(tool, {"query": query, "group_id": group_id, arg_key: limit})
            facts = _facts_from_search(data)
            if facts:
                return facts
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{tool}: {exc}")
            continue
    # Distinguish a genuinely empty result from a transport/tool failure so the
    # problem is not silently hidden behind an empty list.
    if errors:
        print(
            f"WARN: search tool calls failed for {group_id}: {'; '.join(errors)}", file=sys.stderr
        )
    return []


def _is_already_seeded(group_id: str, seed_name: str) -> bool:
    return bool(_search_group(seed_name, group_id, limit=1))


def _find_supersedes_uuid(body: str, group_id: str) -> str | None:
    facts = _search_group(body[:200], group_id, limit=3)
    if facts and isinstance(facts[0], dict):
        return facts[0].get("uuid") or facts[0].get("id")
    return None


def _probe_tool_plane(timeout: int = 10) -> dict[str, Any]:
    """Probe the MCP tool plane via tools/list.

    Liveness (/healthcheck) only proves the process is up; it does NOT prove the
    MCP transport/tool endpoint that reads & writes actually use is reachable.
    A transport/path mismatch (e.g. server not serving streamable-HTTP at /mcp/)
    surfaces here as reachable=false instead of being silently swallowed.
    """
    try:
        result = mcp_call("tools/list", {}, timeout=timeout)
        tools = result.get("tools", result) if isinstance(result, dict) else result
        names = (
            [t.get("name") for t in tools if isinstance(t, dict)] if isinstance(tools, list) else []
        )
        probe: dict[str, Any] = {"reachable": True, "tool_count": len(names)}
        if names:
            probe["tools"] = sorted(n for n in names if n)[:25]
        return probe
    except Exception as exc:  # noqa: BLE001
        return {"reachable": False, "error": str(exc), "endpoint": mcp_url()}


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

    # 1. Liveness — GET /healthcheck (process up?)
    try:
        health_url = mcp_url().replace("/mcp/", "/healthcheck").replace("/mcp", "/healthcheck")
        req = urllib.request.Request(health_url, headers=mcp_headers())
        _ssl_ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=10, context=_ssl_ctx) as resp:
            out["liveness"] = json.loads(resp.read().decode())
        out["liveness_ok"] = True
    except Exception as exc:  # noqa: BLE001
        out["liveness_ok"] = False
        out["liveness_error"] = str(exc)

    # 2. Tool plane — MCP tools/list (the surface reads & writes depend on)
    tools = _probe_tool_plane()
    out["tools"] = tools
    # Back-compat: keep the legacy "mcp" key consumers may read.
    out["mcp"] = out.get("liveness", {"status": "unknown"})

    out["healthy"] = bool(out.get("liveness_ok")) and bool(tools.get("reachable"))
    if out["liveness_ok"] and not tools.get("reachable"):
        out["degraded"] = "liveness OK but MCP tool plane unreachable — reads/writes will fail"
    print(json.dumps(out, indent=2))
    return 0 if out["healthy"] else 1


def cmd_resolve(_args: argparse.Namespace) -> int:
    load_env()
    print(json.dumps(resolve_group_id(Path.cwd()), indent=2))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    load_env()
    resolved = resolve_group_id(Path.cwd(), explicit=getattr(args, "group_id", None))
    group_id = resolved.get("group_id")
    if not group_id:
        raise SystemExit(resolved.get("error", "no group_id"))
    budget = int(os.environ.get("MEMORY_TOKEN_BUDGET", "400"))
    results: list[Any] = []
    for gid in resolve_read_groups(group_id):
        found = _search_group(args.query, gid, limit=args.limit)
        if not found:
            print(f"WARN: search empty for {gid}", file=sys.stderr)
        results.extend(found)
    print(
        json.dumps(
            {
                "group_id": group_id,
                "read_groups": resolve_read_groups(group_id),
                "budget_tokens": budget,
                "results": results,
            },
            indent=2,
        )
    )
    return 0


def cmd_write(args: argparse.Namespace) -> int:
    load_env()
    resolved = resolve_group_id(Path.cwd(), explicit=getattr(args, "group_id", None))
    if resolved.get("readonly"):
        raise SystemExit(f"write blocked: {resolved.get('error') or resolved.get('warning')}")
    group_id = resolved.get("group_id")
    if not group_id or group_id in FORBIDDEN_GROUPS:
        raise SystemExit("forbidden or missing group_id")
    if not _rate.allow():
        raise SystemExit("rate limited")
    now = datetime.now(UTC)
    episode_name = (
        getattr(args, "episode_name", None) or f"{args.kind}-{group_id}-{int(now.timestamp())}"
    )
    contract = EpisodeContract(
        name=episode_name,
        episode_body=args.body,
        source="json" if args.body.strip().startswith("{") else "text",
        source_description=f"CLI write kind={args.kind}",
        reference_time=now,
        group_id=group_id,
        kind=args.kind,
    )
    if args.dry_run:
        payload = contract.to_mcp_payload()
        supersedes_uuid = _find_supersedes_uuid(args.body, group_id)
        if supersedes_uuid:
            payload["supersedes_uuid"] = supersedes_uuid
        print(json.dumps(payload, indent=2))
        return 0
    payload = contract.to_mcp_payload()
    supersedes_uuid = _find_supersedes_uuid(args.body, group_id)
    if supersedes_uuid:
        payload["supersedes_uuid"] = supersedes_uuid
        print(f"INFO: near-duplicate — Supersedes {supersedes_uuid}", file=sys.stderr)
    try:
        result = call_tool("add_episode", payload)
    except RuntimeError as exc:
        if supersedes_uuid and "supersedes" in str(exc).lower():
            payload.pop("supersedes_uuid", None)
            result = call_tool("add_episode", payload)
        else:
            raise
    _rate.record()
    print(
        json.dumps(
            {
                "written": True,
                "group_id": group_id,
                "supersedes": supersedes_uuid,
                "result": result,
            },
            indent=2,
        )
    )
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
    prefetch_parts: list[str] = []
    for gid in resolve_read_groups(group_id):
        try:
            prefetch_parts.append(
                str(
                    call_tool("search_facts", {"query": args.task, "group_id": gid, "max_facts": 8})
                )
            )
        except Exception:  # noqa: BLE001
            continue
    prefetch_text = "".join(prefetch_parts)[: int(os.environ.get("MEMORY_TOKEN_BUDGET", "400")) * 4]
    bank = _read_memory_bank(repo)
    state = {
        "group_id": group_id,
        "prefetch_ts": datetime.now(UTC).isoformat(),
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
        "docs/adr/README.md",
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


def _write_episode(name: str, body: str, group_id: str, source_description: str) -> Any:
    now = datetime.now(UTC)
    contract = EpisodeContract(
        name=name,
        episode_body=body,
        source="json" if body.strip().startswith("{") else "text",
        source_description=source_description,
        reference_time=now,
        group_id=group_id,
        kind="manifest",
    )
    return call_tool("add_episode", contract.to_mcp_payload())


def cmd_bootstrap(args: argparse.Namespace) -> int:
    load_env()
    repo = Path.cwd()
    resolved = resolve_group_id(repo, explicit=args.group_id)
    group_id = resolved.get("group_id")
    if not group_id:
        raise SystemExit(resolved.get("error", "no group_id"))
    if resolved.get("readonly") and not args.dry_run:
        raise SystemExit(f"write blocked: {resolved.get('warning') or resolved.get('error')}")

    registry = load_registry()
    repo_meta = (registry.get("repos") or {}).get(group_id, {})
    workspace_group = registry.get("workspace_group", "igor-workspace")
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

    integrates_with = [
        {"group_id": dep, "via": "group_registry.yaml"}
        for dep in repo_meta.get("integrates_with", [])
    ]
    manifest = {
        "repo_slug": group_id,
        "github": remote or repo_meta.get("github", ""),
        "stack": "Odoo 19 / PlasticOS" if (repo / "plasticos_base").is_dir() else "governance",
        "branch_model": {"dev": "Staging", "prod": "Production"},
        "integrates_with": integrates_with,
        "sources": [str(p.relative_to(repo)) for p in _discover_bootstrap_sources(repo)],
        "seeded_at": datetime.now(UTC).isoformat(),
    }
    seed_name = _bootstrap_seed_name(group_id)
    body = json.dumps(manifest, indent=2)

    if args.dry_run:
        print(json.dumps({"dry_run": True, "seed_name": seed_name, "manifest": manifest}, indent=2))
        return 0

    if _is_already_seeded(group_id, seed_name):
        print(
            json.dumps(
                {
                    "skipped": True,
                    "reason": "already seeded",
                    "slug": group_id,
                    "seed_name": seed_name,
                },
                indent=2,
            )
        )
        return 0

    if not _rate.allow():
        raise SystemExit("rate limited")

    result = _write_episode(seed_name, body, group_id, "graphiti_memory_client bootstrap")
    _rate.record()
    mirror_results: list[Any] = []
    for integration in integrates_with:
        dep = integration["group_id"]
        edge_body = json.dumps(
            {
                "type": "integration_edge",
                "from": group_id,
                "to": dep,
                "via": integration.get("via", "group_registry.yaml"),
            }
        )
        try:
            mirror_results.append(
                _write_episode(
                    f"integration_edge:{group_id}:{dep}",
                    edge_body,
                    workspace_group,
                    "graphiti_memory_client bootstrap mirror",
                )
            )
            _rate.record()
        except Exception as exc:  # noqa: BLE001
            print(f"WARN: workspace mirror to {dep} failed: {exc}", file=sys.stderr)

    print(
        json.dumps(
            {
                "bootstrapped": True,
                "slug": group_id,
                "seed_name": seed_name,
                "manifest": manifest,
                "workspace_edges": len(integrates_with),
                "result": result,
                "mirror_results": mirror_results,
            },
            indent=2,
        )
    )
    return 0


def cmd_autoseed_check(args: argparse.Namespace) -> int:
    load_env()
    resolved = resolve_group_id(Path.cwd(), explicit=getattr(args, "group_id", None))
    group_id = resolved.get("group_id")
    if not group_id or resolved.get("readonly"):
        return 0
    seed_name = _bootstrap_seed_name(group_id)
    if _is_already_seeded(group_id, seed_name):
        print(json.dumps({"seeded": True, "group_id": group_id, "seed_name": seed_name}, indent=2))
        return 0
    print(json.dumps({"seeded": False, "group_id": group_id, "seed_name": seed_name}, indent=2))
    return 2


def cmd_stats(args: argparse.Namespace) -> int:
    load_env()
    group_id = args.group or resolve_group_id(Path.cwd()).get("group_id")
    if not group_id:
        raise SystemExit("no group_id")
    episodes: list[Any] = []
    try:
        data = call_tool("get_episodes", {"group_id": group_id, "last_n": 999})
        episodes = data.get("episodes", []) if isinstance(data, dict) else []
    except Exception:  # noqa: BLE001
        data = call_tool("search_nodes", {"query": "*", "group_id": group_id, "max_nodes": 50})
        print(json.dumps({"group_id": group_id, "stats": data, "episode_count": None}, indent=2))
        return 0
    print(
        json.dumps({"group_id": group_id, "episode_count": len(episodes), "stats": data}, indent=2)
    )
    return 0


def cmd_conflicts(_args: argparse.Namespace) -> int:
    load_env()
    group_id = resolve_group_id(Path.cwd()).get("group_id")
    if not group_id:
        raise SystemExit("no group_id")
    data = _search_group("conflicts_with", group_id, limit=20)
    print(json.dumps({"group_id": group_id, "conflicts": data}, indent=2))
    return 0


def _state_path() -> Path:
    conv = os.environ.get("CURSOR_CONVERSATION_ID", "default")
    state_dir = Path.home() / ".cursor" / "graphiti-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / f"{conv}.json"


def _append_satisfied(key: str) -> dict:
    path = _state_path()
    data: dict = {}
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
    satisfied = data.setdefault("memory_satisfied_for", [])
    if key not in satisfied:
        satisfied.append(key)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {"state_file": str(path), "memory_satisfied_for": satisfied}


def cmd_phase_lock(_args: argparse.Namespace) -> int:
    """Run conflicts check and mark gmp:phase_lock in session state."""
    load_env()
    rc = cmd_conflicts(_args)
    if rc != 0:
        return rc
    result = _append_satisfied("gmp:phase_lock")
    print(json.dumps({"phase_lock": "granted", **result}, indent=2))
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
    p_search.add_argument("--group-id", default=None)
    p_write = sub.add_parser("write")
    p_write.add_argument("body")
    p_write.add_argument("--kind", default="lesson")
    p_write.add_argument("--group-id", default=None)
    p_write.add_argument("--dry-run", action="store_true")
    p_inject = sub.add_parser("inject")
    p_inject.add_argument("task", default="session start")
    p_bootstrap = sub.add_parser("bootstrap")
    p_bootstrap.add_argument("--dry-run", action="store_true")
    p_bootstrap.add_argument("--group-id", default=None)
    p_stats = sub.add_parser("stats")
    p_stats.add_argument("--group", default=None)
    sub.add_parser("conflicts")
    sub.add_parser("phase-lock")
    p_autoseed = sub.add_parser("autoseed-check")
    p_autoseed.add_argument("--group-id", default=None)
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
        "phase-lock": cmd_phase_lock,
        "autoseed-check": cmd_autoseed_check,
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
