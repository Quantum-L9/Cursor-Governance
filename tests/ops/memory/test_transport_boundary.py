"""Architectural transport boundary of the memory plane (audit P3-01).

The lexical egress scanner (``ops/scripts/validate_memory_egress_boundary.py``)
catches provider vocabulary; a module can dodge it by spelling a URL or a tool
name differently. This suite enforces the *shape* of the boundary instead, on
the AST and at runtime:

1. No module on the memory path imports a network or provider transport
   (``urllib``, ``http``, ``socket``, ``ssl``, ``requests``, ``httpx``,
   ``aiohttp``, ``websockets``, the MCP client SDK, ``graphiti_core``,
   ``neo4j``). Memory bytes leave Cursor only through the bound ``l9-memory``
   console script's stdio (INV-03).
2. Process spawning is confined to the three modules whose job it is
   (``runtime_binding`` proves and launches the bound CLI; ``namespace_context``
   asks git for repository identity; ``mcp_instantiation`` delegates to the
   memory-owned ``l9-memory client cursor`` installer), always as an argv
   list, never a shell string.
3. At runtime every operation of :class:`MemoryControlPlaneClient` launches
   exactly the bound executable — nothing else — and the launch goes through
   the runner the binding supplies.

The semgrep rules ``l9.memory-boundary-*`` in ``.semgrep/l9-pr.yml`` enforce
the same two static invariants on ``make pr-security``; this suite is the
interpreter-level twin that runs on every ``pytest`` and cannot be silenced
by a ``nosemgrep`` comment.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from memory_boundary_fixtures import (
    FakeMemoryCli,
    close_payload,
    health_payload,
    hydration_payload,
    search_payload,
)

from ops.memory.control_plane_client import MemoryControlPlaneClient

ROOT = Path(__file__).resolve().parents[3]

#: Production modules that carry memory bytes across the boundary. Tests and
#: the OpenAI distiller helper (an LLM transport, not a memory provider, and
#: fixed-host by construction) are outside this set on purpose.
MEMORY_PATH_MODULES: tuple[str, ...] = (
    *sorted(
        str(path.relative_to(ROOT))
        for path in (ROOT / "ops" / "memory").glob("*.py")
        if not path.name.startswith("test_")
    ),
    "ops/graphiti/hydration/close_session.py",
    "ops/graphiti/hydration/pickup_write.py",
    "ops/graphiti/hydration/compile_session_packet.py",
    "ops/graphiti/hydration/session_latches.py",
    "environment/agents/adapters/claude-code/memory/memory_bridge.py",
    "environment/agents/adapters/claude-code/memory/memory_state.py",
)

#: Top-level packages that would let a memory-path module reach a provider or
#: any network peer directly.
FORBIDDEN_TRANSPORT_ROOTS = frozenset(
    {
        "urllib",
        "urllib3",
        "http",
        "socket",
        "ssl",
        "requests",
        "httpx",
        "aiohttp",
        "websockets",
        "websocket",
        "mcp",
        "graphiti_core",
        "neo4j",
        "asyncio",  # no event loop on the memory path: the transport is a subprocess
    }
)

#: The only modules allowed to spawn a process, and why.
SPAWN_ALLOWED = frozenset(
    {
        "ops/memory/runtime_binding.py",  # proves + launches the bound l9-memory
        "ops/memory/namespace_context.py",  # git identity of the checkout
        "ops/memory/mcp_instantiation.py",  # memory-owned MCP installer/verify
        "environment/agents/adapters/claude-code/memory/memory_state.py",  # git toplevel
    }
)

SPAWN_CALLS = frozenset(
    {
        ("subprocess", "run"),
        ("subprocess", "Popen"),
        ("subprocess", "call"),
        ("subprocess", "check_call"),
        ("subprocess", "check_output"),
        ("subprocess", "getoutput"),
        ("subprocess", "getstatusoutput"),
        ("os", "system"),
        ("os", "popen"),
        ("os", "execv"),
        ("os", "execve"),
        ("os", "execvp"),
        ("os", "execvpe"),
        ("os", "spawnv"),
        ("os", "spawnve"),
        ("os", "spawnvp"),
        ("os", "posix_spawn"),
    }
)


def _module(rel: str) -> ast.Module:
    return ast.parse((ROOT / rel).read_text(encoding="utf-8"), filename=rel)


def _import_roots(tree: ast.Module) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def _dotted(node: ast.AST) -> tuple[str, ...] | None:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return None if base is None else (*base, node.attr)
    return None


def _spawn_calls(tree: ast.Module) -> list[tuple[int, str, ast.Call]]:
    found: list[tuple[int, str, ast.Call]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        dotted = _dotted(node.func)
        if dotted and len(dotted) >= 2 and (dotted[-2], dotted[-1]) in SPAWN_CALLS:
            found.append((node.lineno, ".".join(dotted), node))
    return found


def test_memory_path_modules_exist() -> None:
    missing = [rel for rel in MEMORY_PATH_MODULES if not (ROOT / rel).is_file()]
    assert not missing, missing
    assert len(MEMORY_PATH_MODULES) >= 15


@pytest.mark.parametrize("rel", MEMORY_PATH_MODULES)
def test_memory_path_imports_no_network_or_provider_transport(rel: str) -> None:
    roots = _import_roots(_module(rel))
    leaked = sorted(roots & FORBIDDEN_TRANSPORT_ROOTS)
    assert not leaked, f"{rel} imports a transport the memory boundary forbids: {leaked}"


@pytest.mark.parametrize("rel", MEMORY_PATH_MODULES)
def test_process_spawning_is_confined_to_the_binding_modules(rel: str) -> None:
    calls = _spawn_calls(_module(rel))
    if rel in SPAWN_ALLOWED:
        for lineno, name, call in calls:
            shell = [kw for kw in call.keywords if kw.arg == "shell" and not _is_false(kw.value)]
            assert not shell, f"{rel}:{lineno} {name} with shell= — argv lists only"
            assert call.args, f"{rel}:{lineno} {name} without an argv list"
            first = call.args[0]
            assert not isinstance(first, ast.Constant) or not isinstance(first.value, str), (
                f"{rel}:{lineno} {name} launches a shell string"
            )
        return
    assert not calls, (
        f"{rel} spawns a process ({[(line, name) for line, name, _ in calls]}); "
        f"only {sorted(SPAWN_ALLOWED)} may, through the bound runtime"
    )


def _is_false(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is False


def test_spawn_allowlist_names_only_real_modules() -> None:
    for rel in SPAWN_ALLOWED:
        assert rel in MEMORY_PATH_MODULES, rel


def test_the_control_plane_client_launches_only_the_bound_executable(
    fake_cli: FakeMemoryCli, bound
) -> None:
    """Runtime twin of the static rules: every operation runs ``binding.memory_cli``."""

    launched: list[list[str]] = []

    def runner(argv, **kwargs):
        launched.append(list(argv))
        return fake_cli.run(argv, **kwargs)

    fake_cli.reply("health", 0, health_payload())
    fake_cli.reply("hydrate", 0, hydration_payload("r1"))
    fake_cli.reply("search", 0, search_payload())
    fake_cli.reply("close", 0, close_payload())
    fake_cli.reply(
        "conflicts",
        0,
        {"namespace": "cursor-governance", "conflicts": [], "snapshot_digest": "s" * 64},
    )
    client = MemoryControlPlaneClient(bound, runner=runner, session_id="sess")
    client.health()
    client.hydrate(
        "t",
        workspace="/w",
        write_namespace_hint="cursor-governance",
        read_namespace_hints=("cursor-governance",),
    )
    client.search(
        "t",
        workspace="/w",
        write_namespace_hint="cursor-governance",
        read_namespace_hints=("cursor-governance",),
    )
    client.close(workspace="/w", namespace="cursor-governance", summary="s")
    client.conflicts(workspace="/w", namespace="cursor-governance")
    assert len(launched) == 5
    assert {argv[0] for argv in launched} == {bound.memory_cli}
    assert all(isinstance(argv, list) for argv in launched)
    # No URL, no token, no provider tool name anywhere on the launched argv.
    flat = " ".join(" ".join(argv) for argv in launched)
    for forbidden in ("http://", "https://", "Bearer", "add_memory", "search_memory_facts"):
        assert forbidden not in flat


def test_the_default_runner_is_argv_only_and_shell_free() -> None:
    from ops.memory import runtime_binding as rb

    tree = _module("ops/memory/runtime_binding.py")
    runner = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "default_runner"
    )
    calls = _spawn_calls(runner)
    assert [name for _l, name, _c in calls] == ["subprocess.run"]
    _lineno, _name, call = calls[0]
    assert not any(kw.arg == "shell" for kw in call.keywords)
    assert rb.default_runner.__module__ == "ops.memory.runtime_binding"
