#!/usr/bin/env python3
"""L9 governed harness for the Claude Agent SDK.

Loads committed project governance (CLAUDE.md, .claude/settings.json, .mcp.json)
via setting_sources=["project"], routes hook events through l9_hook_exec.sh,
hard-denies SSOT mutations in-process, and emits a schema-validated JSON report.

Spec: environment/agents/adapters/claude-agent-sdk/README.md
Config SSOT: environment/agents/adapters/claude-agent-sdk/config.yaml
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("L9_REPO", HERE.parents[3]))
GOV_HOME = Path(os.environ.get("L9_GOV_HOME", Path.home() / ".cursor-governance"))
CONFIG_PATH = HERE / "config.yaml"
AUDIT_LOG = REPO / "telemetry" / "agent_sdk_audit.jsonl"

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


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with path.open() as f:
        return yaml.safe_load(f)


# ---- Governance primitives (pure; unit-tested without the SDK) --------------
def is_protected(path: str, cfg: dict[str, Any], repo: Path = REPO) -> bool:
    if not path:
        return False
    try:
        rel = os.path.relpath(path, repo)
    except ValueError:
        rel = path
    rel = rel.replace(os.sep, "/")
    if rel.startswith(".."):
        return True  # outside repo is always protected
    if Path(rel).name in set(cfg["protected_files"]):
        return True
    return any(rel.startswith(p) for p in cfg["protected_prefixes"])


def deny(input_data: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "systemMessage": f"[L9] blocked: {reason}",
        "hookSpecificOutput": {
            "hookEventName": input_data.get("hook_event_name", "PreToolUse"),
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }


def map_launcher_result(
    returncode: int, stdout: str, stderr: str, hook_class: str, input_data: dict[str, Any],
    veto_code: int, script: str,
) -> dict[str, Any]:
    if returncode == veto_code and hook_class == "governor":
        return deny(input_data, stderr.strip() or f"{script} vetoed")
    if stdout.strip() and input_data.get("hook_event_name") == "PostToolUse":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": stdout.strip()[:4000],
            }
        }
    return {}


def audit_record(input_data: dict[str, Any], tool_use_id: str | None) -> dict[str, Any]:
    return {
        "ts": time.time(),
        "event": input_data.get("hook_event_name"),
        "tool": input_data.get("tool_name"),
        "tool_use_id": tool_use_id,
        "agent": input_data.get("agent_type"),
        "session": input_data.get("session_id"),
    }


def write_audit(record: dict[str, Any], log: Path = AUDIT_LOG) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as f:
        f.write(json.dumps(record) + "\n")


# ---- SDK wiring --------------------------------------------------------------
def build_hooks(cfg: dict[str, Any]):
    from claude_agent_sdk import HookMatcher

    launcher = GOV_HOME / cfg["hook_launcher"]
    veto = int(cfg.get("governor_veto_exit_code", 2))

    async def invariant_guard(input_data, tool_use_id, context):
        path = (input_data.get("tool_input") or {}).get("file_path", "")
        if is_protected(path, cfg):
            return deny(input_data, f"{path} is governance SSOT; change via PR with CODEOWNERS review")
        return {}

    def l9_dispatch(hook_class: str, script: str):
        async def _hook(input_data, tool_use_id, context):
            if not launcher.exists():
                return {}  # same no-op fallback as committed .claude/settings.json

            def run():
                return subprocess.run(
                    ["bash", str(launcher), "--class", hook_class, script],
                    input=json.dumps(input_data), text=True, capture_output=True,
                    timeout=15, cwd=REPO,
                )

            try:
                r = await asyncio.to_thread(run)
            except subprocess.TimeoutExpired:
                return {}
            return map_launcher_result(r.returncode, r.stdout, r.stderr, hook_class, input_data, veto, script)

        return _hook

    async def audit_logger(input_data, tool_use_id, context):
        rec = audit_record(input_data, tool_use_id)
        asyncio.get_running_loop().run_in_executor(None, write_audit, rec)
        return {"async_": True, "asyncTimeout": 5000}

    return {
        "PreToolUse": [
            HookMatcher(matcher="Write|Edit|MultiEdit", hooks=[invariant_guard]),
            HookMatcher(matcher="Bash|Write|Edit|MultiEdit",
                        hooks=[l9_dispatch("governor", "root_file_advisory_wrap.py")]),
            HookMatcher(hooks=[audit_logger]),
        ],
        "PostToolUse": [
            HookMatcher(matcher="Write|Edit|MultiEdit",
                        hooks=[l9_dispatch("observer", "bootstrap_capability_preflight.sh")]),
            HookMatcher(hooks=[audit_logger]),
        ],
        "SubagentStop": [HookMatcher(hooks=[audit_logger])],
        "Stop": [HookMatcher(hooks=[audit_logger])],
    }


def build_agents():
    from claude_agent_sdk import AgentDefinition

    return {
        "l9-auditor": AgentDefinition(
            description="Read-only invariant and drift auditor. Use for any audit/gap-analysis task.",
            prompt=("You are the L9 auditor. Compare ORG_INVARIANTS.yaml, INVARIANTS.md and "
                    "CANONICAL_LAW.md against the live tree. Report drift as a table. Never edit files."),
            tools=["Read", "Grep", "Glob"],
            model="sonnet",
        ),
        "l9-remediator": AgentDefinition(
            description="Applies minimal, reversible fixes for findings the auditor produced.",
            prompt=("You are the L9 remediator. Apply the smallest reversible change per finding, "
                    "run `make lint` and `pytest -q` after each, and stop on first failure."),
            tools=["Read", "Grep", "Glob", "Edit", "Write", "Bash"],
        ),
    }


def build_options(cfg: dict[str, Any], mode: str, budget: float, turns: int):
    from claude_agent_sdk import ClaudeAgentOptions

    return ClaudeAgentOptions(
        cwd=REPO,
        setting_sources=list(cfg["setting_sources"]),
        system_prompt={
            "type": "preset", "preset": "claude_code",
            "append": ("Governance SSOT is CANONICAL_LAW.md. Advisory-first: propose before "
                       "mutating anything outside the task scope."),
        },
        permission_mode=mode,
        allowed_tools=list(cfg["allowed_tools"]),
        disallowed_tools=[d["rule"] for d in cfg["disallowed_tools"]],
        agents=build_agents(),
        hooks=build_hooks(cfg),
        output_format={"type": "json_schema", "schema": REPORT_SCHEMA},
        max_turns=turns,
        max_budget_usd=budget,
        enable_file_checkpointing=True,
        env={"CLAUDE_AGENT_SDK_CLIENT_APP": "l9-agent-sdk/0.1"},
        stderr=lambda line: print(f"[cli] {line}", file=sys.stderr, end=""),
    )


async def run(task: str, opts, report_path: Path) -> int:
    from claude_agent_sdk import (AssistantMessage, ClaudeSDKClient, ResultMessage,
                                  TextBlock, ToolUseBlock)

    async with ClaudeSDKClient(options=opts) as client:
        await client.query(task)
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print(b.text)
                    elif isinstance(b, ToolUseBlock):
                        print(f"  -> {b.name} {json.dumps(b.input)[:160]}")
            elif isinstance(msg, ResultMessage):
                cost = msg.total_cost_usd or 0.0
                print(f"\n[result] {msg.subtype} turns={msg.num_turns} cost=${cost:.4f} session={msg.session_id}")
                if msg.subtype != "success":
                    print(f"[result] terminal_reason={getattr(msg, 'terminal_reason', None)!r}")
                    return 1
                payload = getattr(msg, "structured_output", None) or msg.result
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(payload if isinstance(payload, str) else json.dumps(payload, indent=2))
                print(f"[report] {report_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    cfg = load_config()
    ap = argparse.ArgumentParser(description="L9 governed Claude Agent SDK harness")
    ap.add_argument("task", nargs="?", default=os.environ.get(
        "L9_TASK", "Use l9-auditor to audit ORG_INVARIANTS.yaml against the repo and report drift."))
    ap.add_argument("--mode", default=cfg["permission_mode_default"], choices=["default", "acceptEdits", "plan"])
    ap.add_argument("--budget", type=float, default=float(cfg["max_budget_usd"]))
    ap.add_argument("--turns", type=int, default=int(cfg["max_turns"]))
    ap.add_argument("--report", type=Path, default=REPO / "reports/agent_sdk/latest.json")
    a = ap.parse_args(argv)
    if not (REPO / "CLAUDE.md").exists():
        print(f"CLAUDE.md not found at {REPO}; set L9_REPO", file=sys.stderr)
        return 2
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 2
    try:
        from claude_agent_sdk import ResultError
    except ImportError:
        print("claude-agent-sdk not installed: uv add claude-agent-sdk", file=sys.stderr)
        return 2
    try:
        return asyncio.run(run(a.task, build_options(cfg, a.mode, a.budget, a.turns), a.report))
    except ResultError as e:
        print(f"[fatal] {e.subtype} {getattr(e, 'terminal_reason', None)} {e.result or e.errors}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
