#!/usr/bin/env python3
"""Thin Claude Agent SDK harness for Cursor-Governance.

Governance is consumed, never authored here. ``setting_sources=["project"]``
makes the SDK load ``CLAUDE.md``, ``.claude/settings.json`` (permissions and
hooks) and ``.mcp.json`` exactly as Claude Code does. This module owns only
SDK runtime mechanics: working directory, permission-mode selection, budget
and turn bounds, structured report output, file checkpointing, MCP status
introspection, and SDK lifecycle/error handling.

It deliberately passes no ``allowed_tools``, ``disallowed_tools``, ``hooks``,
``agents``, ``can_use_tool`` or ``mcp_servers``: those belong to the project
settings, and a second copy here would be a shadow policy
(``validate_agent_sdk_env.py`` rejects one).

Spec: environment/agents/adapters/claude-agent-sdk/README.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("L9_REPO", HERE.parents[3]))

SETTING_SOURCES = ("project",)
PROJECT_GOVERNANCE = ("CLAUDE.md", ".claude/settings.json", ".mcp.json")
PERMISSION_MODES = ("default", "acceptEdits", "plan")
DEFAULT_MODE = "default"
DEFAULT_MAX_TURNS = 40
DEFAULT_MAX_BUDGET_USD = 2.0
# reports/* is gitignored: a run never dirties the checkout.
DEFAULT_REPORT = Path("reports") / "agent_sdk" / "latest.json"
# A server still settling after this long is reported as pending, not guessed.
MCP_SETTLE_SECONDS = 30.0
MCP_UNAVAILABLE = ("failed", "needs-auth")
# claude_agent_sdk.ResultMessage fields copied into the report.
RESULT_FIELDS = (
    "subtype",
    "is_error",
    "num_turns",
    "total_cost_usd",
    "session_id",
    "permission_denials",
    "structured_output",
)

REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "file": {"type": "string"},
                    "description": {"type": "string"},
                    "remediated": {"type": "boolean"},
                },
                "required": ["id", "severity", "file", "description"],
            },
        },
        "files_changed": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "findings", "files_changed"],
}


def missing_governance(repo: Path = REPO) -> list[str]:
    """Project governance inputs the SDK must load but cannot find."""
    return [rel for rel in PROJECT_GOVERNANCE if not (repo / rel).is_file()]


def option_kwargs(
    mode: str = DEFAULT_MODE,
    budget: float = DEFAULT_MAX_BUDGET_USD,
    turns: int = DEFAULT_MAX_TURNS,
    repo: Path = REPO,
) -> dict[str, Any]:
    """The complete ClaudeAgentOptions payload — runtime mechanics only."""
    if mode not in PERMISSION_MODES:
        raise ValueError(f"permission mode {mode!r} not in {PERMISSION_MODES}")
    if budget <= 0 or turns <= 0:
        raise ValueError("budget and turns must be positive")
    return {
        "cwd": repo,
        "setting_sources": list(SETTING_SOURCES),
        "system_prompt": {"type": "preset", "preset": "claude_code"},
        "permission_mode": mode,
        "output_format": {"type": "json_schema", "schema": REPORT_SCHEMA},
        "max_turns": turns,
        "max_budget_usd": budget,
        "enable_file_checkpointing": True,
    }


def build_options(kwargs: dict[str, Any]) -> Any:
    from claude_agent_sdk import ClaudeAgentOptions

    return ClaudeAgentOptions(
        **kwargs, stderr=lambda line: print(f"[cli] {line}", file=sys.stderr, end="")
    )


def summarize_mcp(status: Any) -> list[dict[str, Any]]:
    """Name/status/scope/error per server. ``config`` is dropped: it can carry env."""
    rows = status.get("mcpServers", []) if isinstance(status, dict) else []
    keep = ("name", "status", "scope", "error")
    return [{k: row[k] for k in keep if k in row} for row in rows if isinstance(row, dict)]


def report_document(result: Any, mcp: list[dict[str, Any]]) -> dict[str, Any]:
    """The JSON report written for one run: ResultMessage fields plus MCP status."""
    return {**{name: getattr(result, name) for name in RESULT_FIELDS}, "mcp_servers": mcp}


async def settled_mcp_status(client: Any, timeout: float = MCP_SETTLE_SECONDS) -> list[dict]:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        rows = summarize_mcp(await client.get_mcp_status())
        pending = any(row.get("status") == "pending" for row in rows)
        if not pending or loop.time() >= deadline:
            return rows
        await asyncio.sleep(1.0)


async def probe_mcp(opts: Any) -> int:
    """Connect without a prompt and report the project MCP servers the SDK loaded."""
    from claude_agent_sdk import ClaudeSDKClient

    async with ClaudeSDKClient(options=opts) as client:
        rows = await settled_mcp_status(client)
    print(json.dumps({"mcp_servers": rows}, indent=2))
    return 1 if any(row.get("status") in MCP_UNAVAILABLE for row in rows) else 0


async def run(task: str, opts: Any, report_path: Path) -> int:
    from claude_agent_sdk import AssistantMessage, ClaudeSDKClient, ResultMessage, TextBlock

    result = None
    async with ClaudeSDKClient(options=opts) as client:
        await client.query(task)
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(block.text)
            elif isinstance(msg, ResultMessage):
                result = msg
        mcp = await settled_mcp_status(client)
    if result is None:
        print("[result] no ResultMessage received", file=sys.stderr)
        return 1
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_document(result, mcp), indent=2) + "\n")
    cost = result.total_cost_usd or 0.0
    print(f"[result] {result.subtype} turns={result.num_turns} cost=${cost:.4f}")
    print(f"[report] {report_path}")
    return 0 if result.subtype == "success" and result.structured_output else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Thin Claude Agent SDK harness (project governance)")
    ap.add_argument("task", nargs="?", help="prompt to run; omit with --mcp-status")
    ap.add_argument("--mode", default=DEFAULT_MODE, choices=PERMISSION_MODES)
    ap.add_argument("--budget", type=float, default=DEFAULT_MAX_BUDGET_USD)
    ap.add_argument("--turns", type=int, default=DEFAULT_MAX_TURNS)
    ap.add_argument("--report", type=Path, default=REPO / DEFAULT_REPORT)
    ap.add_argument(
        "--mcp-status", action="store_true", help="report loaded project MCP servers and exit"
    )
    a = ap.parse_args(argv)
    if not a.mcp_status and not a.task:
        ap.error("task is required unless --mcp-status is given")
    missing = missing_governance(REPO)
    if missing:
        print(f"project governance missing under {REPO}: {missing}; set L9_REPO", file=sys.stderr)
        return 2
    try:
        from claude_agent_sdk import ClaudeSDKError, ResultError
    except ImportError:
        print(
            "claude-agent-sdk not in this environment: uv sync --locked --extra agent-sdk",
            file=sys.stderr,
        )
        return 2
    if not a.mcp_status and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 2
    opts = build_options(option_kwargs(a.mode, a.budget, a.turns))
    try:
        if a.mcp_status:
            return asyncio.run(probe_mcp(opts))
        return asyncio.run(run(a.task, opts, a.report))
    except ResultError as e:
        print(f"[fatal] {e.subtype} {e.terminal_reason} {e.result or e.errors}", file=sys.stderr)
        return 1
    except ClaudeSDKError as e:
        print(f"[fatal] {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
