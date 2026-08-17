#!/usr/bin/env python3
"""Structural validator for the Claude Code environment adapter.

Checks that are cheap, deterministic, and never fabricate a live fact:

* every declared file exists,
* every JSON template parses,
* no real secret is committed (only ``REPLACE_WITH_*`` / ``${...}`` placeholders),
* the MCP template carries no literal bearer token.

Run: ``python3 environment/agents/adapters/claude-code/validate_claude_env.py``
(or ``make claude-env``).
Exit 0 on PASS, 1 on FAIL. Stdlib only, so it runs on a fresh sandbox.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

# Graphiti front door is env-sourced (cloud HTTPS or CLI loopback tunnel).
# Template must reference ${GRAPHITI_MCP_URL}; never register l9-shared-memory.
GRAPHITI_MCP_URL_ENV_REF = "${GRAPHITI_MCP_URL}"
# Scheme prefixes assembled from parts (SonarCloud python:S5332). Detection only.
_URL_SCHEME_PREFIXES = tuple(f"{scheme}://" for scheme in ("http", "https"))

HERE = Path(__file__).resolve().parent

REQUIRED_FILES: tuple[str, ...] = (
    "README.md",
    "install.sh",
    "render.claude.json",
    "settings.template.json",
    "mcp.template.json",
    "hooks/session_start_claude_governance.sh",
    "hooks/SESSION_START_SPEC.md",
    "hooks/merge_gate_wrap.py",
    "hooks/local_execution_gate_wrap.py",
    "web/README.md",
    "web/network-policy.md",
    "web/environment.env.example",
    "web/setup.sh",
    "adapters/claude-code.md",
    "hooks/user_prompt_skill_router.py",
    "hooks/skill_usage_logger.py",
    "hooks/context7_stack_pretool.py",
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


def _governance_root() -> Path:
    """Walk up to the governance clone root (CANONICAL_LAW.md / .git marker)."""
    for parent in HERE.parents:
        if (parent / "CANONICAL_LAW.md").is_file() or (parent / ".git").exists():
            return parent
    return HERE


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
    root = HERE
    for parent in HERE.parents:
        if (parent / "CANONICAL_LAW.md").is_file() or (parent / ".git").exists():
            root = parent
            break
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


def _iter_http_urls(obj: object) -> Iterator[str]:
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _iter_http_urls(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _iter_http_urls(value)
    elif isinstance(obj, str) and obj.startswith(_URL_SCHEME_PREFIXES):
        yield obj


def check_mcp_uses_env_refs(failures: list[str]) -> None:
    path = HERE / "mcp.template.json"
    if not path.is_file():
        return
    server = json.loads(path.read_text(encoding="utf-8"))
    servers = server.get("mcpServers", {})
    if "l9-shared-memory" in servers:
        _fail(
            "mcp.template.json must not register l9-shared-memory HTTP side door; "
            "use graphiti-memory front door only",
            failures,
        )
    mem = servers.get("graphiti-memory", {})
    if not mem:
        _fail("mcp.template.json must define graphiti-memory front door", failures)
        return
    auth = mem.get("headers", {}).get("Authorization", "")
    url = mem.get("url", "")
    if "${GRAPHITI_MCP_TOKEN}" in auth and "Bearer" in auth:
        print("  OK: mcp auth is GRAPHITI_MCP_TOKEN env-reference")
    else:
        _fail(
            "mcp.template.json Authorization must be Bearer ${GRAPHITI_MCP_TOKEN}",
            failures,
        )
    if url == GRAPHITI_MCP_URL_ENV_REF:
        print("  OK: mcp URL is GRAPHITI_MCP_URL env-reference (cloud HTTPS or CLI tunnel)")
    else:
        _fail(
            f"mcp.template.json URL must be {GRAPHITI_MCP_URL_ENV_REF!r}",
            failures,
        )
    raw = (HERE / "mcp.template.json").read_text(encoding="utf-8")
    for banned in ("L9_MEMORY_HTTP_URL", "L9_MEMORY_CLIENT_TOKEN"):
        if banned in raw:
            _fail(f"mcp.template.json must not reference {banned}", failures)


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


def check_dependency_policy(failures: list[str]) -> None:
    """uv.lock is the only source of dependency and interpreter versions.

    The adapter must apply it through the ``ensure_uv_environment.sh`` wrapper
    and must never re-declare a governance runtime dependency by name — a second
    version list drifts from the lock silently and installs into whatever
    interpreter happens to be on PATH.
    """
    installer = HERE / "install.sh"
    if not installer.is_file():
        _fail("missing install.sh — the Claude Code adapter installer", failures)
        return
    text = installer.read_text(encoding="utf-8")

    # The adapter must DELEGATE to the shared, surface-agnostic bootstrap rather
    # than applying the lock itself — every agent surface uses that one path.
    if "bootstrap_agent_environment.sh" not in text:
        _fail(
            "install.sh must delegate to ops/scripts/bootstrap_agent_environment.sh "
            "(the bootstrap shared by every agent surface)",
            failures,
        )
        return
    print("  OK: install.sh delegates to the shared agent bootstrap")

    shared = _governance_root() / "ops" / "scripts" / "bootstrap_agent_environment.sh"
    if not shared.is_file():
        _fail("missing ops/scripts/bootstrap_agent_environment.sh", failures)
    elif "ensure_uv_environment.sh" in shared.read_text(encoding="utf-8"):
        print("  OK: shared bootstrap applies uv.lock via ensure_uv_environment.sh")
    else:
        _fail(
            "shared bootstrap must apply uv.lock via ops/scripts/ensure_uv_environment.sh",
            failures,
        )

    # Generic machinery must not creep back into the vendor adapter, or the
    # surfaces silently diverge again.
    adapter_only = {
        "ensure_uv_environment.sh": "locked toolchain",
        "gitleaks": "checker provisioning",
        "hydrate_infisical": "secret resolution",
        "scratch_hold.py": "scratch-hold restore",
    }
    leaked = [f"{token} ({why})" for token, why in adapter_only.items() if token in text]
    if leaked:
        _fail(
            "install.sh re-implements shared bootstrap concerns: "
            + ", ".join(leaked)
            + " — move them to ops/scripts/bootstrap_agent_environment.sh",
            failures,
        )
    else:
        print("  OK: adapter holds vendor wiring only; generic concerns stay shared")

    # Runtime deps owned by the governance pyproject/uv.lock. Naming one in an
    # install command means a pin was rewritten instead of being consumed.
    governed = ("pydantic", "pyyaml", "structlog", "langgraph", "jsonschema")
    install_re = re.compile(r"(?:pip|uv pip)\s+install[^\n|&;]*", re.IGNORECASE)
    before = len(failures)
    for path in sorted(HERE.rglob("*.sh")):
        try:
            body = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for command in install_re.findall(body):
            named = [dep for dep in governed if dep in command.lower()]
            if named:
                _fail(
                    f"{path.relative_to(HERE)} installs governed dependencies by name "
                    f"({', '.join(named)}); consume uv.lock instead",
                    failures,
                )
    if len(failures) == before:
        print("  OK: no adapter script re-declares a governed dependency pin")


def check_publish_path_alignment(failures: list[str]) -> None:
    """The permission layer must agree with the enforcement layer.

    ``permissions.allow`` is what an agent reads as "approved, no prompt". If it
    lists an action ``ops/autonomy/local_execution_gate.py`` denies, the agent is
    actively taught to attempt something that will be blocked a layer later —
    which is exactly how a raw ``git push`` and an MCP ``create_pull_request``
    got attempted on this repo. Being impossible is not enough; the agent must
    not be told it is permitted.

    So: every publish-bypass form must be absent from allow AND present in deny.
    """
    path = HERE / "settings.template.json"
    if not path.is_file():
        return
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _fail(f"settings.template.json unreadable: {exc}", failures)
        return

    permissions = settings.get("permissions") or {}
    allow = [str(entry) for entry in permissions.get("allow", [])]
    deny = [str(entry) for entry in permissions.get("deny", [])]

    # Keep in step with local_execution_gate: RAW_PUBLISH_PATTERNS + DENY_MCP_TOOLS.
    forbidden = {
        "Bash(git push:*)": ("git push", ("git push",)),
        "Bash(gh pr create:*)": ("gh pr create", ("gh pr create",)),
        "Bash(gh pr edit:*)": ("gh pr edit", ("gh pr edit",)),
        "Bash(make push:*)": ("make push", ("make push",)),
        "mcp__github__create_pull_request": ("create_pull_request", ("create_pull_request",)),
        "mcp__github__push_files": ("push_files", ("push_files",)),
    }

    problems = 0
    for canonical, (label, needles) in forbidden.items():
        leaked = [entry for entry in allow if any(needle in entry for needle in needles)]
        if leaked:
            _fail(
                f"permissions.allow lists `{leaked[0]}`, which the publish-path gate denies "
                f"({label}) — an agent reads this as approved and will attempt it",
                failures,
            )
            problems += 1
        if canonical not in deny:
            _fail(
                f"permissions.deny is missing `{canonical}` — the gate denies it, so the "
                "permission layer must say so too",
                failures,
            )
            problems += 1

    if "Bash(make pr:*)" not in allow:
        _fail(
            "permissions.allow must include `Bash(make pr:*)` — the sanctioned publish "
            "path has to be the frictionless one, or the agent looks for another way",
            failures,
        )
        problems += 1

    required_context7 = (
        "mcp__context7__resolve-library-id",
        "mcp__context7__query-docs",
    )
    for entry in required_context7:
        if entry not in allow:
            _fail(
                f"permissions.allow must include `{entry}` so Claude can self-serve Context7",
                failures,
            )
            problems += 1

    if not problems:
        print("  OK: permission layer agrees with the publish-path gate")


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


def check_session_lifecycle_parity(failures: list[str]) -> None:
    """Both surfaces must close a session, not just open one.

    Cursor registers sessionEnd (PICKUP write + governance backup) in
    ops/hooks/hooks.json.template. The Claude adapter declared SessionStart and
    no SessionEnd at all, so no Claude session ever wrote a PICKUP and every
    subsequent hydrate came back "empty PICKUP search". Nothing caught it: every
    other check here is structural, and a missing lifecycle event is invisible
    to file-existence and JSON-validity tests.

    Parity is asserted against the shared closers in ops/hooks/ — the same
    scripts Cursor runs. A Claude-private reimplementation would satisfy the
    letter of this check and defeat its purpose, so the script names are pinned.
    """
    path = HERE / "settings.template.json"
    if not path.is_file():
        return
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _fail(f"settings.template.json unreadable: {exc}", failures)
        return

    hooks = settings.get("hooks") or {}
    if "SessionEnd" not in hooks:
        _fail(
            "settings.template.json declares no SessionEnd hook — a Claude session "
            "cannot write a Graphiti PICKUP, so every later hydrate starts empty "
            "(Cursor registers sessionEnd in ops/hooks/hooks.json.template)",
            failures,
        )
        return

    blob = json.dumps(hooks["SessionEnd"])
    for script in ("graphiti-session-end.sh", "session_end_governance_backup.sh"):
        if script not in blob:
            _fail(
                f"SessionEnd must invoke the shared closer ops/hooks/{script}; "
                "adapters must not fork a private session-close path",
                failures,
            )
    if "/ops/hooks/" not in blob:
        _fail(
            "SessionEnd must reference the shared ops/hooks/ closers, not an "
            "adapter-local copy",
            failures,
        )
    print("  OK: session lifecycle parity — SessionEnd wired to shared closers")


def main() -> int:
    print("=== Claude Code environment — structural validation ===")
    print(f"  root: {HERE}\n")
    failures: list[str] = []
    check_files_exist(failures)
    check_json_parses(failures)
    check_no_secrets(failures)
    check_mcp_uses_env_refs(failures)
    check_setup_linux_sandbox_hygiene(failures)
    check_dependency_policy(failures)
    check_publish_path_alignment(failures)
    check_memory_identity_distinct(failures)
    check_skill_activation(failures)
    check_memory_enforcement(failures)
    check_session_lifecycle_parity(failures)
    print()
    if failures:
        print(f"RESULT: FAIL — {len(failures)} issue(s)")
        return 1
    print("RESULT: PASS — Claude Code environment adapter is structurally sound")
    return 0


if __name__ == "__main__":
    sys.exit(main())
