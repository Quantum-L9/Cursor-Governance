#!/usr/bin/env python3
"""Shared PlasticOS code-graph gate logic for Cursor hooks and GMP baseline."""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EVIDENCE_REL = ".cursor/code-graph-phase0-evidence.json"
EVIDENCE_TTL_HOURS = 4

HIGH_IMPACT_PATH_RE = re.compile(
    r"^(plasticos_base/|plasticos_security_base/|plasticos_[^/]+/models/[^/]+\.py$)"
)

FOUNDATION_PREFIXES = ("plasticos_base/", "plasticos_security_base/")

SHARED_MODEL_HINTS: dict[str, str] = {
    "plasticos_material_profile/models/material_profile.py": "PlasticosMaterialProfile",
    "plasticos_facility_profile/models/facility_profile.py": "PlasticosFacilityProfile",
    "plasticos_transaction/models/transaction.py": "PlasticosTransaction",
    "plasticos_intake/models/intake.py": "PlasticosIntake",
    "plasticos_offer/models/offer.py": "PlasticosOffer",
    "plasticos_matching/models/match_result.py": "PlasticosMatchResult",
}

MCP_DENY_TOOLS = frozenset(
    {
        "batch_index",
        "index",
        "clean_index",
        "reset_graph",
        "get_graph",
        "detect_code_clones",
        "jscpd_detect_clones",
        "suggest_refactoring",
    }
)

MCP_ASK_TOOLS = frozenset({"semantic_search"})


def is_plasticos_repo(repo: Path) -> bool:
    return (repo / "plasticos_base").is_dir()


def normalize_rel_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def is_high_impact_path(rel_path: str) -> bool:
    rel = normalize_rel_path(rel_path)
    return bool(HIGH_IMPACT_PATH_RE.match(rel))


def is_foundation_path(rel_path: str) -> bool:
    rel = normalize_rel_path(rel_path)
    return rel.startswith(FOUNDATION_PREFIXES)


def entity_hint_for_path(rel_path: str) -> str | None:
    rel = normalize_rel_path(rel_path)
    if rel in SHARED_MODEL_HINTS:
        return SHARED_MODEL_HINTS[rel]
    parts = Path(rel).stem.split("_")
    if "models" in rel and parts:
        return "".join(p.capitalize() for p in parts)
    return None


def load_evidence(repo: Path) -> dict[str, Any] | None:
    evidence_path = repo / EVIDENCE_REL
    if not evidence_path.is_file():
        return None
    try:
        data = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def evidence_is_fresh(data: dict[str, Any]) -> bool:
    expires = data.get("expires_at")
    if not expires:
        return False
    try:
        exp_dt = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
    except ValueError:
        return False
    return exp_dt > datetime.now(UTC)


def evidence_covers_path(data: dict[str, Any], rel_path: str) -> bool:
    if data.get("status") != "complete":
        return False
    if not data.get("healthy"):
        return False
    if not evidence_is_fresh(data):
        return False

    rel = normalize_rel_path(rel_path)
    targets = {normalize_rel_path(str(t)) for t in data.get("targets", [])}
    if rel in targets:
        return True

    for prefix in data.get("covered_prefixes", []):
        if rel.startswith(normalize_rel_path(str(prefix))):
            return True

    for module in data.get("modules", []):
        mod = str(module).strip("/")
        if rel.startswith(f"{mod}/"):
            return True

    return False


def extract_tool_path(hook_input: dict[str, Any]) -> tuple[str | None, str | None]:
    tool_name = (
        hook_input.get("tool_name") or hook_input.get("tool") or hook_input.get("name") or ""
    )
    tool_input = (
        hook_input.get("tool_input") or hook_input.get("parameters") or hook_input.get("args") or {}
    )
    if not isinstance(tool_input, dict):
        tool_input = {}

    path = (
        tool_input.get("path")
        or tool_input.get("file_path")
        or tool_input.get("target_file")
        or tool_input.get("filePath")
    )
    return str(tool_name) if tool_name else None, str(path) if path else None


def extract_mcp_tool(hook_input: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    tool = hook_input.get("tool_name") or hook_input.get("tool") or hook_input.get("name") or ""
    if isinstance(tool, str) and "/" in tool:
        tool = tool.rsplit("/", 1)[-1]
    if isinstance(tool, str) and tool.startswith("MCP:"):
        tool = tool.split(":", 1)[-1].strip()
        if "/" in tool:
            tool = tool.rsplit("/", 1)[-1]

    args = (
        hook_input.get("arguments")
        or hook_input.get("tool_input")
        or hook_input.get("parameters")
        or {}
    )
    if not isinstance(args, dict):
        args = {}
    return str(tool) if tool else None, args


def hook_response(
    permission: str, user_message: str = "", agent_message: str = "", **extra: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"permission": permission}
    if user_message:
        payload["user_message"] = user_message
    if agent_message:
        payload["agent_message"] = agent_message
    payload.update(extra)
    return payload


def check_pre_tool_use(hook_input: dict[str, Any]) -> dict[str, Any]:
    repo_raw = hook_input.get(
        "workspace_roots", hook_input.get("workspace_root", [hook_input.get("cwd", "")])
    )
    if isinstance(repo_raw, list):
        repo_raw = repo_raw[0] if repo_raw else ""
    repo = Path(str(repo_raw or hook_input.get("CURSOR_PROJECT_DIR", "."))).expanduser().resolve()

    if not is_plasticos_repo(repo):
        return hook_response("allow")

    tool_name, path = extract_tool_path(hook_input)
    if not tool_name or not path:
        return hook_response("allow")

    write_tools = {"Write", "StrReplace", "search_replace", "EditNotebook", "ApplyPatch"}
    if tool_name not in write_tools:
        return hook_response("allow")

    rel = normalize_rel_path(path)
    if not is_high_impact_path(rel):
        return hook_response("allow")

    evidence = load_evidence(repo)
    if evidence and evidence_covers_path(evidence, rel):
        return hook_response("allow")

    baseline = (
        'bash "$HOME/.cursor-governance/skills/l9-code-graph-rag-mcp/scripts/'
        f'code_graph_gmp_baseline.sh" "{repo}" --run-id gmp-$(date +%Y%m%d) --files {rel}'
    )
    matrix = (
        "skills/l9-code-graph-rag-mcp/assets/plasticos-trigger-matrix.md "
        "(when to read from graph vs grep)"
    )
    msg = (
        f"High-impact PlasticOS path `{rel}` requires code-graph Phase 0 evidence. "
        f"Run: {baseline}. See trigger matrix: {matrix}."
    )
    return hook_response("ask", user_message=msg, agent_message=msg)


def check_before_mcp(hook_input: dict[str, Any]) -> dict[str, Any]:
    repo_raw = hook_input.get(
        "workspace_roots", hook_input.get("workspace_root", [hook_input.get("cwd", "")])
    )
    if isinstance(repo_raw, list):
        repo_raw = repo_raw[0] if repo_raw else ""
    repo = Path(str(repo_raw or hook_input.get("CURSOR_PROJECT_DIR", "."))).expanduser().resolve()

    if not is_plasticos_repo(repo):
        return hook_response("allow")

    tool_name, _args = extract_mcp_tool(hook_input)
    if not tool_name:
        return hook_response("allow")

    if tool_name in MCP_DENY_TOOLS:
        msg = (
            f"code-graph tool `{tool_name}` is denied in chat for PlasticOS. "
            "Run code_graph_batch_index.sh in Terminal only. "
            "See plasticos-trigger-matrix.md."
        )
        return hook_response("deny", user_message=msg, agent_message=msg)

    if tool_name in MCP_ASK_TOOLS:
        msg = (
            f"code-graph `{tool_name}` is last-resort only. Prefer grep/read or structural tools. "
            "Include a module path in the query if you proceed."
        )
        return hook_response("ask", user_message=msg, agent_message=msg)

    return hook_response("allow")


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: code_graph_plasticos_gate.py pre_tool_use|before_mcp [json stdin]",
            file=sys.stderr,
        )
        return 2

    mode = sys.argv[1]
    raw = sys.stdin.read().strip() or (sys.argv[2] if len(sys.argv) > 2 else "{}")
    try:
        hook_input = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        hook_input = {}

    if mode == "pre_tool_use":
        result = check_pre_tool_use(hook_input)
    elif mode == "before_mcp":
        result = check_before_mcp(hook_input)
    else:
        print(f"Unknown mode: {mode}", file=sys.stderr)
        return 2

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
