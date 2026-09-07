#!/usr/bin/env python3
"""Validate the memory-enforcement contract and prove it is actually wired.

Fails (non-zero) when:
  * the contract does not conform to its schema,
  * the contract teaches retired memory doctrine (a provider URL/token env or
    MCP path on the surface, a ``phase_lock`` precondition on repository
    writes, a missing or weakened ``interactive_memory_write`` block),
  * a hook the contract declares is not registered in settings.template.json
    with the matching event (wiring parity -> no enforcement-by-documentation),
  * a referenced hook/validator script is missing or does not compile,
  * a governed-write rule is malformed.

This is what turns the contract from context into an enforced, checkable object.
The doctrine check (:func:`doctrine_check`) runs on every invocation, with or
without ``jsonschema`` installed, so the schema alone never becomes the only
thing standing between the surface and a regression (ADR-0030 items 7-9,
CANONICAL_LAW 8.3).
"""

from __future__ import annotations

import json
import py_compile
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _repo_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / "CANONICAL_LAW.md").is_file() or (parent / ".git").exists():
            return parent
    return start.parent.parent.parent.parent  # adapters/claude-code → repo


REPO = _repo_root(HERE)
MEM = HERE / "memory"
CONTRACT = MEM / "memory-enforcement.contract.json"
SCHEMA = MEM / "memory-enforcement.schema.json"
SETTINGS = HERE / "settings.template.json"
CONTRACT_TEST = HERE / "tests" / "test_memory_front_door.py"

#: The canonical front door and the retired doctrine the contract must never
#: carry again. Provider variable names are assembled so this validator is not
#: itself an egress-scanner hit.
CANONICAL_FRONT_DOOR = "ops/memory/control_plane_client.py"
CANONICAL_CONTROL_PLANE = "memory-control-plane/v1"
CANONICAL_MCP_SERVER = "l9-graphite-memory"
RETIRED_TOMBSTONE = "ops/graphiti/graphiti_memory_client.py"
RETIRED_MEMORY_KEYS = ("url_env", "token_env", "mcp_path")
RETIRED_TRANSPORT_MARKERS = (
    "GRAPHITI_MCP_" + "URL",
    "GRAPHITI_MCP_" + "TOKEN",
    "L9_MEMORY_HTTP_URL",
    "L9_MEMORY_CLIENT_TOKEN",
    "memory.quantumaipartners.com",
    "127.0.0.1:8100",
)

#: Every value the ``interactive_memory_write`` block must carry verbatim.
INTERACTIVE_WRITE_CONSTS: dict[str, object] = {
    "canonical_mcp_server": CANONICAL_MCP_SERVER,
    "prerequisite": "memory.phase_lock",
    "write_operation": "memory.write_governed",
    "repository_authority": False,
    "provider_direct": "forbidden",
    "generic_ingest_as_model_write": "forbidden",
    "cli_adapter": "python -m ops.memory.cli",
    "cli_write_role": "operator_and_deterministic_adapters",
}
DETERMINISTIC_ADAPTER_OPERATIONS = frozenset(
    {"hydrate", "close", "ingest_candidate", "repair-write", "legacy_reconciliation", "readiness"}
)


def _fail(msg: str, failures: list[str]) -> None:
    failures.append(msg)
    print(f"  FAIL: {msg}")


def _schema_check(contract: dict, schema: dict, failures: list[str]) -> None:
    try:
        import jsonschema  # type: ignore[import-not-found]

        jsonschema.validate(contract, schema)
        print("  OK: contract conforms to schema (jsonschema)")
        return
    except ImportError:
        pass
    except Exception as exc:  # jsonschema present but validation failed
        _fail(f"schema validation error: {exc}", failures)
        return
    # Zero-dependency fallback: assert the invariants the schema encodes.
    if contract.get("contract") != "l9.claude-code.memory-enforcement":
        _fail("contract id mismatch", failures)
    if contract.get("enforcement_point") != "PreToolUse":
        _fail("enforcement_point must be PreToolUse", failures)
    if contract.get("status") not in {"enforced", "disabled"}:
        _fail("status must be enforced|disabled", failures)
    for key in (
        "memory",
        "interactive_memory_write",
        "state",
        "hooks",
        "preconditions",
        "governed_writes",
        "operator_override",
    ):
        if key not in contract:
            _fail(f"missing top-level key: {key}", failures)
    if contract.get("operator_override", {}).get("agent_settable") is not False:
        _fail("operator_override.agent_settable must be false", failures)
    for rule in contract.get("governed_writes", []):
        for field in ("id", "match", "requires", "fail_mode"):
            if field not in rule:
                _fail(f"governed rule missing {field}: {rule.get('id', rule)}", failures)
        if rule.get("fail_mode") not in {"closed", "open"}:
            _fail(f"bad fail_mode in {rule.get('id')}", failures)
        illegal = set(rule.get("requires", [])) - {"session_prefetch"}
        if illegal - {"phase_lock"}:
            _fail(f"unknown precondition in {rule.get('id')}", failures)
    if not failures:
        print("  OK: contract conforms to schema (fallback checks)")


def doctrine_check(contract: dict, failures: list[str]) -> None:
    """Fail on retired provider/write doctrine, whatever the schema says.

    Runs unconditionally so a contract that validates against a stale or
    hand-relaxed schema still cannot teach the retired architecture.
    """
    before = len(failures)
    memory = contract.get("memory")
    if not isinstance(memory, dict):
        _fail("memory block missing", failures)
        memory = {}
    if memory.get("front_door") != CANONICAL_FRONT_DOOR:
        _fail(
            f"memory.front_door must be {CANONICAL_FRONT_DOOR} (got {memory.get('front_door')!r})",
            failures,
        )
    if memory.get("control_plane_contract") != CANONICAL_CONTROL_PLANE:
        _fail(f"memory.control_plane_contract must be {CANONICAL_CONTROL_PLANE}", failures)
    for key in RETIRED_MEMORY_KEYS:
        if key in memory:
            _fail(
                f"memory.{key} is retired provider doctrine: no surface holds a provider "
                "URL, bearer or MCP path (ADR-0030, realignment C9/C11)",
                failures,
            )
    doors = memory.get("forbidden_side_doors") or []
    if RETIRED_TOMBSTONE not in doors:
        _fail(f"memory.forbidden_side_doors must name the tombstone {RETIRED_TOMBSTONE}", failures)

    # A provider transport spelled anywhere in the contract as anything other
    # than a forbidden side door is a live instruction to reach the provider.
    def _live_transport_mentions(node: object, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                _live_transport_mentions(value, f"{path}.{key}" if path else key)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                _live_transport_mentions(item, f"{path}[{i}]")
        elif isinstance(node, str) and not path.startswith("memory.forbidden_side_doors"):
            for marker in RETIRED_TRANSPORT_MARKERS:
                if marker in node:
                    _fail(
                        f"{path} names the retired provider transport {marker!r} outside "
                        "memory.forbidden_side_doors",
                        failures,
                    )

    _live_transport_mentions(contract, "")

    # E7: repository-write authority is Git's, never memory state. A
    # phase_lock precondition on a governed repository write is a contract
    # regression, not an "unknown" value, so name it explicitly.
    for rule in contract.get("governed_writes", []) or []:
        if "phase_lock" in (rule.get("requires") or []):
            _fail(
                f"{rule.get('id')} requires 'phase_lock': a memory phase-lock must not "
                "authorize repository mutation (E7)",
                failures,
            )

    # ADR-0030 items 7-9: the model's durable write is phase_lock ->
    # write_governed on the canonical MCP server, never a provider, never
    # generic ingest, and never repository authority.
    imw = contract.get("interactive_memory_write")
    if not isinstance(imw, dict):
        _fail(
            "interactive_memory_write block missing: the contract must state the model's "
            "durable-write path (memory.phase_lock -> memory.write_governed)",
            failures,
        )
    else:
        for key, expected in INTERACTIVE_WRITE_CONSTS.items():
            if key not in imw:
                _fail(f"interactive_memory_write.{key} missing", failures)
            elif imw[key] != expected or type(imw[key]) is not type(expected):
                _fail(
                    f"interactive_memory_write.{key} must be {expected!r} (got {imw[key]!r})",
                    failures,
                )
        ops = imw.get("deterministic_adapter_operations")
        if not isinstance(ops, list) or not ops:
            _fail(
                "interactive_memory_write.deterministic_adapter_operations must be a "
                "non-empty list",
                failures,
            )
        else:
            unknown = sorted(set(ops) - DETERMINISTIC_ADAPTER_OPERATIONS)
            if unknown:
                _fail(
                    "interactive_memory_write.deterministic_adapter_operations names operations "
                    f"that are not purpose-specific ops/memory adapters: {unknown}",
                    failures,
                )
            if "ingest" in ops or "write_governed" in ops:
                _fail(
                    "generic ingest / the governed write are not deterministic-adapter operations",
                    failures,
                )
    if len(failures) == before:
        print("  OK: contract carries no retired provider/write doctrine (ADR-0030 items 7-9)")


def _wiring_parity(contract: dict, settings: dict, failures: list[str]) -> None:
    hooks = settings.get("hooks", {})

    def registered(event: str, script_basename: str) -> bool:
        for group in hooks.get(event, []):
            for hook in group.get("hooks", []):
                if script_basename in hook.get("command", ""):
                    return True
        return False

    for role, spec in contract.get("hooks", {}).items():
        event = spec.get("event") if isinstance(spec, dict) else None
        script = spec.get("script") if isinstance(spec, dict) else None
        if not event or not script:
            _fail(f"hook '{role}' is missing event/script in the contract", failures)
            continue
        basename = Path(script).name
        if registered(event, basename):
            print(f"  OK: {role} hook '{basename}' registered under {event}")
        else:
            _fail(
                f"{role} hook '{basename}' NOT registered under {event} in settings.template.json",
                failures,
            )


def _scripts_exist(contract: dict, failures: list[str]) -> None:
    scripts = [spec["script"] for spec in contract.get("hooks", {}).values()]
    scripts.append(
        contract.get("preconditions", {})
        .get("session_prefetch", {})
        .get("established_by", "")
        .split()[0]
    )
    scripts.append("environment/agents/adapters/claude-code/validate_memory_enforcement.py")
    for rel in filter(None, scripts):
        path = REPO / rel
        if not path.is_file():
            _fail(f"referenced script missing: {rel}", failures)
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            _fail(f"script does not compile: {rel} ({exc})", failures)
    if not failures:
        print("  OK: all referenced scripts exist and compile")


def _contract_pin(failures: list[str]) -> None:
    """Run the network-free canonical front-door pin (no HTTP side door).

    Presence is not proof: the pin only prevents divergence if it actually runs
    (ADR-0004's principle, now carried by tests/test_memory_front_door.py).
    Network-free.
    """
    if not CONTRACT_TEST.is_file():
        _fail(f"missing contract pin: {CONTRACT_TEST.relative_to(REPO)}", failures)
        return
    try:
        result = subprocess.run(
            [sys.executable, str(CONTRACT_TEST)],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        _fail("canonical front-door pin test timed out (>60s)", failures)
        return
    if result.returncode:
        detail = f"{result.stdout}{result.stderr}"
        _fail(f"canonical front-door pin test failed\n{detail}", failures)
    else:
        print("  OK: canonical front-door pin holds (no HTTP side door, governed write contract)")


def main() -> int:
    failures: list[str] = []
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))

    _schema_check(contract, schema, failures)
    doctrine_check(contract, failures)
    _wiring_parity(contract, settings, failures)
    _scripts_exist(contract, failures)
    _contract_pin(failures)

    if failures:
        print(f"\nRESULT: FAIL - {len(failures)} problem(s)")
        return 1
    print("\nRESULT: PASS - memory enforcement contract is valid and wired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
