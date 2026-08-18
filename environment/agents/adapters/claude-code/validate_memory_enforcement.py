#!/usr/bin/env python3
"""Validate the memory-enforcement contract and prove it is actually wired.

Fails (non-zero) when:
  * the contract does not conform to its schema,
  * a hook the contract declares is not registered in settings.template.json
    with the matching event (wiring parity -> no enforcement-by-documentation),
  * a referenced hook/validator script is missing or does not compile,
  * a governed-write rule is malformed.

This is what turns the contract from context into an enforced, checkable object.
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
CONTRACT_TEST = HERE / "tests" / "test_graphiti_front_door.py"


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
        # E7: repository-write authority is Git's, never memory state. A
        # phase_lock precondition here is a contract regression, not an
        # "unknown" value, so name it explicitly.
        illegal = set(rule.get("requires", [])) - {"session_prefetch"}
        if "phase_lock" in illegal:
            _fail(
                f"{rule.get('id')} requires 'phase_lock': a Graphiti phase-lock must not "
                "authorize repository mutation (E7)",
                failures,
            )
        if illegal - {"phase_lock"}:
            _fail(f"unknown precondition in {rule.get('id')}", failures)
    if not failures:
        print("  OK: contract conforms to schema (fallback checks)")


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
    """Run the network-free Graphiti front-door pin (no HTTP side door).

    Presence is not proof: the pin only prevents divergence if it actually runs
    (see docs/decisions/ADR-0006). Network-free.
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
        _fail("Graphiti front-door pin test timed out (>60s)", failures)
        return
    if result.returncode:
        detail = f"{result.stdout}{result.stderr}"
        _fail(f"Graphiti front-door pin test failed\n{detail}", failures)
    else:
        print("  OK: Graphiti front-door pin holds (no HTTP side door)")


def main() -> int:
    failures: list[str] = []
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))

    _schema_check(contract, schema, failures)
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
