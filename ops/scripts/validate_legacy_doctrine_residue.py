#!/usr/bin/env python3
"""Fail if active surfaces teach retired Dropbox SSOT or L9_MEMORY_HTTP side doors.

HistoricalEvidence (ADRs, reports, archives) is out of scope. Mentions that
explicitly mark residue as forbidden/retired/historical are allowed.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ACTIVE_ROOTS = (
    "rules",
    "skills",
    "commands",
    "ops/scripts",
    "environment/agents/adapters",
    "environment/agents/tools",
    "environment/generated/llm-rules",
    "environment/agents/adapters/claude-code",
    "learning/failures",
)

# Root / top-level active contracts not covered by ACTIVE_ROOTS directories.
ACTIVE_FILES = (
    ".mcp.json",
    ".env.example",
    "end-session.yaml",
)

# Governance authority + session-protocol surfaces that must never carry a
# LIVE instruction to the retired memory client. Scoped deliberately: the
# execution engine (workflows/) and rules corpus migrate under a separate
# memory-front-door plan; this gate protects the authority/protocol class.
AUTHORITY_PROTOCOL_SURFACES = (
    "end-session.yaml",
    "AGENTS.md",
    "CANONICAL_LAW.md",
    "README.md",
    "CONTRIBUTING.md",
    "PULL_REQUEST_TEMPLATE.md",
    ".github/pull_request_template.md",
)

# Retired session-memory client. Graphiti (ops/graphiti/graphiti_memory_client.py,
# runtime .cursor-commands/ops/graphiti/...) is the single front door.
RETIRED_MEMORY_CLIENT = re.compile(r"agents/cursor/cursor_memory_client\.py")

# A mention that teaches the client is gone (a retirement notice) is allowed;
# only a live invocation on an authority surface is a violation.
RETIRED_CLIENT_ALLOW = re.compile(
    r"(?i)("
    r"deprecated|retired|replaced by|superseded|no longer|historical|"
    r"do not use|don't use|use graphiti|instead of|forbidden|removed"
    r")"
)

SKIP_DIR_PARTS = {
    "_archived",
    "archived",
    "reports",
    "WIP",
    "__pycache__",
    ".git",
    "tests",
}

SKIP_NAME_SUFFIXES = (
    "test_graphiti_front_door.py",
    "validate_legacy_doctrine_residue.py",
    "validate_claude_env.py",
    "memory-enforcement.contract.json",
    "memory-enforcement.schema.json",
)

# Path / name teaching Dropbox as live SSOT or fallback.
DROPBOX_LIVE = re.compile(
    r"(?i)("
    r"Dropbox/Cursor Governance|"
    r"Dropbox/cursor governance|"
    r"Dropbox governance SSOT|"
    r"against the Dropbox|"
    r"legacy Dropbox is fallback|"
    r"Use Dropbox GlobalCommands as single source of truth|"
    r"points at Dropbox|"
    r"→ Dropbox|"
    r"under \$HOME/Dropbox"
    r")"
)

# Live HTTP side-door assignments / MCP server registration (not forbid lists).
HTTP_LIVE = re.compile(
    r"(?i)("
    r"L9_MEMORY_HTTP_URL\s*=|"
    r"L9_MEMORY_CLIENT_TOKEN\s*=|"
    r"L9_MEMORY_HTTP_TOKEN\s*=|"
    r'["\']l9-shared-memory["\']\s*:|'
    r"\[mcp_servers\.l9-shared-memory\]|"
    r'"name"\s*:\s*"l9-shared-memory"|'
    r"claude mcp add-json[^\n]*l9-shared-memory"
    r")"
)

ALLOW_LINE = re.compile(
    r"(?i)("
    r"forbidden|"
    r"retired|"
    r"historical|"
    r"not a fallback|"
    r"must not|"
    r"do \*\*not\*\*|"
    r"do not use|"
    r"do not probe|"
    r"\*\*Wrong:\*\*|"
    r"^Wrong:|"
    r"assertNotIn|"
    r"FORBIDDEN|"
    r"banned|"
    r"ADR-0006|"
    r"side door|"
    r"side-door|"
    r"no longer|"
    r"was retired|"
    r"Dropbox is not|"
    r"Dropbox governance fallback is retired|"
    r"never Dropbox|"
    r"must not be probed"
    r")"
)

TEXT_SUFFIXES = {
    ".md",
    ".mdc",
    ".py",
    ".sh",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".example",
    ".txt",
}


def _skip_path(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIR_PARTS:
        return True
    if path.name in SKIP_NAME_SUFFIXES:
        return True
    if path.suffix not in TEXT_SUFFIXES and path.name != "environment.env.example":
        # allow *.env.example via suffix .example already
        if not path.name.endswith(".env.example"):
            return True
    return False


def _iter_active_files() -> list[Path]:
    out: list[Path] = []
    for rel in ACTIVE_ROOTS:
        base = ROOT / rel
        if not base.exists():
            continue
        if base.is_file():
            out.append(base)
            continue
        for path in base.rglob("*"):
            if path.is_file() and not _skip_path(path.relative_to(ROOT)):
                out.append(path)
    # agent_registry + analysis notes + root active contracts
    for extra in (
        *(ROOT / rel for rel in ACTIVE_FILES),
        ROOT / "environment/agents/agent_registry.yaml",
        ROOT / "environment/agents/analysis_notes.md",
        ROOT / "environment/agents/HANDOFF.md",
        ROOT / "environment/agents/README.md",
        ROOT / "environment/agents/adapters/ADAPTER_CONTRACT.md",
    ):
        if extra.is_file():
            out.append(extra)
    return sorted(set(out))


def _scan_retired_client(rel: str, text: str, sink: set[str]) -> None:
    """Record any LIVE retired-client invocation (retirement notices exempt)."""
    for i, line in enumerate(text.splitlines(), 1):
        if not RETIRED_MEMORY_CLIENT.search(line):
            continue
        if ALLOW_LINE.search(line) or RETIRED_CLIENT_ALLOW.search(line):
            continue
        sink.add(f"{rel}:{i}: {line.strip()[:160]}")


def main() -> int:
    findings: list[str] = []
    client_findings: set[str] = set()

    # Full active corpus: Dropbox/HTTP side doors AND the retired memory client.
    for path in _iter_active_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(ROOT).as_posix()
        _scan_retired_client(rel, text, client_findings)
        for i, line in enumerate(text.splitlines(), 1):
            if ALLOW_LINE.search(line):
                continue
            if DROPBOX_LIVE.search(line) or HTTP_LIVE.search(line):
                findings.append(f"{rel}:{i}: {line.strip()[:160]}")

    # Authority / session-protocol root surfaces not covered by ACTIVE_ROOTS.
    for rel in AUTHORITY_PROTOCOL_SURFACES:
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        _scan_retired_client(rel, text, client_findings)

    if findings or client_findings:
        if findings:
            print("FAIL: active doctrine teaches retired Dropbox SSOT or L9_MEMORY_HTTP side door")
            print("Active surfaces must use $HOME/.cursor-governance + Graphiti only (ADR-0006).")
            for hit in findings[:80]:
                print(f"  {hit}")
            if len(findings) > 80:
                print(f"  ... and {len(findings) - 80} more")
        if client_findings:
            print("FAIL: active surface calls the retired memory client (agents/cursor/cursor_memory_client.py)")
            print("Use the Graphiti front door (ops/graphiti/graphiti_memory_client.py) instead.")
            for hit in sorted(client_findings):
                print(f"  {hit}")
        return 1

    print("PASS: no active Dropbox SSOT / L9_MEMORY_HTTP side-door or retired-client teaching")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
