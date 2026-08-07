#!/usr/bin/env python3
"""Validate proactive skill discovery, routing, and invocation controls."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REGISTRY_PATH = ROOT / "ops" / "generated" / "skill-registry.json"
MANIFEST_PATH = ROOT / "skills" / "AUTONOMY_MANIFEST.yaml"
SETTINGS_PATH = HERE / "settings.template.json"
SHARED_ROUTER_PATH = ROOT / "ops" / "skill_routing" / "route_prompt.py"
CLAUDE_ADAPTER_PATH = HERE / "hooks" / "user_prompt_skill_router.py"
CURSOR_ROUTER_PATH = ROOT / "ops" / "hooks" / "before_submit_skill_router.py"
HOOKS_TEMPLATE_PATH = ROOT / "ops" / "hooks" / "hooks.json.template"
CURSOR_RULE_PATH = ROOT / "rules" / "23-l9-skill-routing.mdc"
CASES_PATH = ROOT / "ops" / "skill_routing" / "tests" / "skill_routing_cases.json"
RULE_PATH = ROOT / "environment" / "generated" / "llm-rules" / "l9-skill-routing.md"


def frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unterminated frontmatter")
    data: dict[str, Any] = {}
    for line in text[4:end].splitlines():
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip('"').strip("'")
        if value.lower() in {"true", "false"}:
            data[key.strip()] = value.lower() == "true"
        else:
            data[key.strip()] = value
    return data


def load_shared_router():
    spec = importlib.util.spec_from_file_location("l9_skill_router_validation", SHARED_ROUTER_PATH)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load shared skill routing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def hook_commands(settings: dict[str, Any], event: str) -> list[str]:
    commands: list[str] = []
    for group in settings.get("hooks", {}).get(event, []):
        for hook in group.get("hooks", []):
            if hook.get("type") == "command":
                commands.append(str(hook.get("command", "")))
    return commands


def check_ownership_guard(failures: list[str]) -> None:
    """Fail closed if Cursor/ops adapters load Claude-owned scoring (CANONICAL_LAW §2.1)."""
    cursor_src = CURSOR_ROUTER_PATH.read_text(encoding="utf-8")
    forbidden_markers = (
        "environment/claude-code/hooks/user_prompt_skill_router",
        "environment/claude-code/hooks/",
    )
    for marker in forbidden_markers:
        if marker in cursor_src:
            failures.append(
                f"ownership inverted: {CURSOR_ROUTER_PATH.relative_to(ROOT)} loads {marker!r}"
            )
            print(f"  FAIL: Cursor adapter must not load {marker!r}")
            return
    if "ops/skill_routing/route_prompt.py" not in cursor_src:
        failures.append("Cursor adapter does not load ops/skill_routing/route_prompt.py")
        print("  FAIL: Cursor adapter missing ops/skill_routing load path")
        return
    claude_src = CLAUDE_ADAPTER_PATH.read_text(encoding="utf-8")
    if "def route_prompt(" in claude_src:
        failures.append("Claude adapter still owns route_prompt() implementation")
        print("  FAIL: Claude adapter must be thin — route_prompt belongs in ops/")
        return
    if "ops/skill_routing/route_prompt.py" not in claude_src:
        failures.append("Claude adapter does not load ops/skill_routing/route_prompt.py")
        print("  FAIL: Claude adapter missing ops/skill_routing load path")
        return
    print("  OK: ownership guard — scoring in ops/; adapters are thin")


def main() -> int:
    failures: list[str] = []

    def fail(message: str) -> None:
        failures.append(message)
        print(f"  FAIL: {message}")

    print("=== Proactive skill activation validation (Cursor-primary) ===")
    for path in (
        REGISTRY_PATH,
        MANIFEST_PATH,
        SETTINGS_PATH,
        SHARED_ROUTER_PATH,
        CLAUDE_ADAPTER_PATH,
        CURSOR_ROUTER_PATH,
        HOOKS_TEMPLATE_PATH,
        CURSOR_RULE_PATH,
        CASES_PATH,
        RULE_PATH,
    ):
        if path.is_file():
            print(f"  OK: present {path.relative_to(ROOT)}")
        else:
            fail(f"missing {path.relative_to(ROOT)}")
    if failures:
        return 1

    check_ownership_guard(failures)

    hooks_template = json.loads(HOOKS_TEMPLATE_PATH.read_text(encoding="utf-8"))
    before_submit = hooks_template.get("hooks", {}).get("beforeSubmitPrompt", [])
    if not any(
        "before-submit-skill-router.py" in str(entry.get("command", ""))
        for entry in before_submit
        if isinstance(entry, dict)
    ):
        fail("hooks.json.template does not register Cursor beforeSubmitPrompt skill router")
    else:
        print("  OK: Cursor beforeSubmitPrompt skill router registered in template")

    cursor_rule = CURSOR_RULE_PATH.read_text(encoding="utf-8")
    if "alwaysApply: true" not in cursor_rule:
        fail("rules/23-l9-skill-routing.mdc must be alwaysApply")
    else:
        print("  OK: Cursor skill-routing rule is alwaysApply")

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    actual_manifest_hash = hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
    if registry.get("source_manifest_sha256") != actual_manifest_hash:
        fail("generated skill registry is stale relative to AUTONOMY_MANIFEST.yaml")
    else:
        print("  OK: generated registry matches manifest hash")

    names: set[str] = set()
    explicit: set[str] = set()
    auto: set[str] = set()
    for record in registry.get("skills", []):
        name = str(record.get("name", ""))
        if not name or name in names:
            fail(f"duplicate or empty skill name: {name!r}")
            continue
        names.add(name)
        skill_file = ROOT / str(record.get("path", "")) / "SKILL.md"
        if not skill_file.is_file():
            fail(f"missing SKILL.md for {name}")
            continue
        try:
            fm = frontmatter(skill_file)
        except ValueError as exc:
            fail(f"{name}: {exc}")
            continue
        if fm.get("name") != name:
            fail(f"{name}: frontmatter name mismatch")
        if not str(fm.get("description", "")).strip():
            fail(f"{name}: description missing")
        invocation = record.get("invocation")
        disabled = bool(fm.get("disable-model-invocation", False))
        if invocation == "explicit_only":
            explicit.add(name)
            if not disabled:
                fail(f"{name}: explicit-only skill is model-invocable")
        elif invocation == "model_allowed":
            auto.add(name)
            if disabled:
                fail(f"{name}: auto skill disables model invocation")
        else:
            fail(f"{name}: unknown invocation mode {invocation!r}")
    if auto & explicit:
        fail(f"skills appear in both invocation sets: {sorted(auto & explicit)}")
    else:
        print(f"  OK: invocation tiers disjoint ({len(auto)} auto, {len(explicit)} explicit)")

    settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    submit_commands = hook_commands(settings, "UserPromptSubmit")
    if not any("user_prompt_skill_router.py" in command for command in submit_commands):
        fail("settings.template.json does not register UserPromptSubmit skill router")
    else:
        print("  OK: UserPromptSubmit router registered")
    pre_commands = hook_commands(settings, "PreToolUse")
    expansion_commands = hook_commands(settings, "UserPromptExpansion")
    if not any("skill_usage_logger.py" in command for command in pre_commands):
        fail("PreToolUse skill usage logger missing")
    if not any("skill_usage_logger.py" in command for command in expansion_commands):
        fail("UserPromptExpansion skill usage logger missing")
    overrides = settings.get("skillOverrides", {})
    wrong_overrides = sorted(
        name for name in explicit if overrides.get(name) != "user-invocable-only"
    )
    if wrong_overrides:
        fail(f"explicit-only skillOverrides missing or wrong: {wrong_overrides}")
    else:
        print("  OK: explicit-only skills hidden from model by settings override")

    router = load_shared_router()
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8")).get("cases", [])
    for case in cases:
        result = router.route_prompt(case["prompt"], registry)
        actual = result["primary"] if result else None
        if actual != case.get("expected_primary"):
            fail(
                f"routing case mismatch: {case['prompt']!r}: expected "
                f"{case.get('expected_primary')!r}, got {actual!r}"
            )
            continue
        if result and result.get("supporting", []) != case.get("expected_supporting", []):
            fail(f"supporting route mismatch for: {case['prompt']!r}")
        for forbidden in case.get("forbidden", []):
            if result and (forbidden == result["primary"] or forbidden in result["supporting"]):
                fail(f"forbidden skill routed: {forbidden}")
    if not any(message.startswith("routing case") for message in failures):
        print(f"  OK: {len(cases)} routing fixtures passed")

    tests = [
        ROOT / "ops" / "skill_routing" / "tests" / "test_route_prompt.py",
        HERE / "tests" / "test_skill_reconciliation.py",
        HERE / "tests" / "test_cursor_skill_router.py",
    ]
    for test in tests:
        result = subprocess.run([sys.executable, str(test)], capture_output=True, text=True)
        if result.returncode:
            fail(f"test failed: {test.name}\n{result.stdout}{result.stderr}")
        else:
            print(f"  OK: {test.name}")

    print()
    if failures:
        print(f"RESULT: FAIL - {len(failures)} issue(s)")
        return 1
    print("RESULT: PASS - proactive skill activation is structurally and behaviorally sound")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
