#!/usr/bin/env python3
"""Structural validator for the Claude Code environment adapter.

Checks that are cheap, deterministic, and never fabricate a live fact:

* every declared file exists,
* every JSON template parses,
* no real secret is committed (only ``REPLACE_WITH_*`` / ``${...}`` placeholders),
* the MCP template carries no literal bearer token.

Run: ``python3 environment/claude-code/validate_claude_env.py`` (or ``make claude-env``).
Exit 0 on PASS, 1 on FAIL. Stdlib only, so it runs on a fresh sandbox.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

PROD_MEMORY_MCP_DEFAULT = "${L9_MEMORY_HTTP_URL:-https://memory.quantumaipartners.com}/mcp"

HERE = Path(__file__).resolve().parent

REQUIRED_FILES: tuple[str, ...] = (
    "README.md",
    "render.claude.json",
    "settings.template.json",
    "mcp.template.json",
    "hooks/session_start_claude_governance.sh",
    "web/README.md",
    "web/network-policy.md",
    "web/environment.env.example",
    "web/setup.sh",
    "adapters/claude-code.md",
    "hooks/user_prompt_skill_router.py",
    "hooks/skill_usage_logger.py",
    "tests/test_skill_reconciliation.py",
    "tests/test_cursor_skill_router.py",
    "validate_skill_activation.py",
)

JSON_FILES: tuple[str, ...] = (
    "render.claude.json",
    "settings.template.json",
    "mcp.template.json",
)

# A committed secret looks like a long opaque token. Placeholders are allowed:
# REPLACE_WITH_*, ${...} env-references, and loopback URLs.
SECRET_RE = re.compile(
    r"(gh[pousr]_[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_-]{20,}|sq[pa]_[A-Za-z0-9]{20,})"
)


def _fail(msg: str, failures: list[str]) -> None:
    print(f"  FAIL: {msg}")
    failures.append(msg)


def check_files_exist(failures: list[str]) -> None:
    for rel in REQUIRED_FILES:
        path = HERE / rel
        if path.is_file():
            print(f"  OK: present  {rel}")
        else:
            _fail(f"missing required file: {rel}", failures)
    # Shared routing SSOT lives under ops/ (CANONICAL_LAW §2.1), not this adapter tree.
    root = HERE.parents[1]
    shared_registry = root / "ops" / "generated" / "skill-registry.json"
    shared_scorer = root / "ops" / "skill_routing" / "route_prompt.py"
    for path in (shared_registry, shared_scorer):
        if path.is_file():
            print(f"  OK: present  {path.relative_to(root)}")
        else:
            _fail(f"missing Cursor-primary routing artifact: {path.relative_to(root)}", failures)


def check_json_parses(failures: list[str]) -> None:
    for rel in JSON_FILES:
        path = HERE / rel
        if not path.is_file():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            print(f"  OK: json     {rel}")
        except (json.JSONDecodeError, OSError) as exc:
            _fail(f"invalid JSON in {rel}: {exc}", failures)


def check_no_secrets(failures: list[str]) -> None:
    for path in sorted(HERE.rglob("*")):
        if not path.is_file() or path.name == Path(__file__).name:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        match = SECRET_RE.search(text)
        if match:
            _fail(
                f"possible committed secret in {path.relative_to(HERE)}: {match.group(0)[:8]}...",
                failures,
            )
    print("  OK: no committed secrets detected")


def check_mcp_uses_env_refs(failures: list[str]) -> None:
    path = HERE / "mcp.template.json"
    if not path.is_file():
        return
    server = json.loads(path.read_text(encoding="utf-8"))
    mem = server.get("mcpServers", {}).get("l9-shared-memory", {})
    auth = mem.get("headers", {}).get("Authorization", "")
    url = mem.get("url", "")
    if "${" in auth and "Bearer" in auth:
        print("  OK: mcp auth is an env-reference, not a literal token")
    else:
        _fail("mcp.template.json Authorization must be a ${...} env-reference", failures)
    loopback = url.startswith("http://127.0.0.1") or url.startswith("http://localhost")
    if loopback:
        _fail(
            "mcp.template.json default URL must not be loopback (use production HTTPS fallback)",
            failures,
        )
    elif url == PROD_MEMORY_MCP_DEFAULT:
        print("  OK: mcp URL defaults to production HTTPS / env expansion")
    else:
        parsed = urlsplit(url)
        if parsed.scheme == "https" and parsed.hostname == "memory.quantumaipartners.com":
            print("  OK: mcp URL is production HTTPS host")
        else:
            _fail(
                "mcp.template.json URL must be production HTTPS default "
                f"({PROD_MEMORY_MCP_DEFAULT!r}) or https://memory.quantumaipartners.com/…",
                failures,
            )


def check_setup_linux_sandbox_hygiene(failures: list[str]) -> None:
    """Web setup must stay GitHub-main / Linux-sandbox shaped (no host-IDE SSOT)."""
    setup = HERE / "web" / "setup.sh"
    if not setup.is_file():
        return
    text = setup.read_text(encoding="utf-8")
    banned = ("Dropbox", "CloudStorage", "Keychain", "LaunchAgent", "Homebrew")
    hits = [b for b in banned if b in text]
    if hits:
        _fail(f"web/setup.sh must not reference host-IDE paths/tools: {', '.join(hits)}", failures)
    else:
        print("  OK: web/setup.sh has no host-IDE path/tool residue")
    if (
        'GOV_DIR="$HOME/.cursor-governance"' not in text
        and "GOV_DIR='$HOME/.cursor-governance'" not in text
    ):
        _fail("web/setup.sh must pin GOV_DIR to $HOME/.cursor-governance", failures)
    else:
        print("  OK: web/setup.sh pins governance to $HOME/.cursor-governance")


def check_memory_identity_distinct(failures: list[str]) -> None:
    """Claude Code's memory identity must differ from Cursor's (`cursor_agent`).

    The repo namespace (group_id) is shared with Cursor on purpose; the writing
    agent identity is not. Guard the env template so that invariant cannot
    silently regress into Claude Code writing as ``cursor_agent``.
    """
    path = HERE / "web" / "environment.env.example"
    if not path.is_file():
        return
    assignments: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        assignments[key.strip()] = value.strip()

    agent_id = assignments.get("L9_MEMORY_AGENT_ID", "")
    user_id = assignments.get("USER_ID", "")
    if not agent_id:
        _fail(
            "environment.env.example must set L9_MEMORY_AGENT_ID (distinct memory identity)",
            failures,
        )
    if user_id == "cursor_agent" or agent_id == "cursor_agent":
        _fail("memory identity collides with Cursor's cursor_agent — must be distinct", failures)
    if agent_id and agent_id != "cursor_agent" and user_id != "cursor_agent":
        print(f"  OK: memory identity distinct from Cursor (agent_id={agent_id!r})")


def check_skill_activation(failures: list[str]) -> None:
    script = HERE / "validate_skill_activation.py"
    if not script.is_file():
        return
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired:
        _fail("proactive skill activation validation timed out", failures)
        return
    if result.returncode == 0:
        print("  OK: proactive skill activation validation passed")
    else:
        _fail(
            "proactive skill activation validation failed:\n" + result.stdout + result.stderr,
            failures,
        )


def check_memory_enforcement(failures: list[str]) -> None:
    script = HERE / "validate_memory_enforcement.py"
    if not script.is_file():
        return
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired:
        _fail("memory enforcement validation timed out", failures)
        return
    if result.returncode == 0:
        print("  OK: memory enforcement contract valid and wired")
    else:
        _fail(
            "memory enforcement validation failed:\n" + result.stdout + result.stderr,
            failures,
        )


def main() -> int:
    print("=== Claude Code environment — structural validation ===")
    print(f"  root: {HERE}\n")
    failures: list[str] = []
    check_files_exist(failures)
    check_json_parses(failures)
    check_no_secrets(failures)
    check_mcp_uses_env_refs(failures)
    check_setup_linux_sandbox_hygiene(failures)
    check_memory_identity_distinct(failures)
    check_skill_activation(failures)
    check_memory_enforcement(failures)
    print()
    if failures:
        print(f"RESULT: FAIL — {len(failures)} issue(s)")
        return 1
    print("RESULT: PASS — Claude Code environment adapter is structurally sound")
    return 0


if __name__ == "__main__":
    sys.exit(main())
