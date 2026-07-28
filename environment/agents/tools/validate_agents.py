#!/usr/bin/env python3
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/tools/validate_agents.py
#   layer: tool
#   owner: governance-control-plane
#   status: active
#   version: 1.0.0
#   updated: 2026-07-28
"""N-agent registry and adapter validator (peer of validate_claude_env.py).

Checks:
  R1  registry parses and has schema_version, roles, agents
  R2  agent key == agent_id; kebab-case
  R3  user_id == "<agent_id with _>_agent"; source == agent_id;
      principal_id == "<agent_id>-memory-client";
      token_env == "L9_MEMORY_TOKEN__<AGENT upper snake>"
  R4  agent_id / user_id / principal_id / token_env unique across all agents
  R5  role exists in the roles catalog; status in {active, planned, retired}
  R6  writing roles (non-observer) declare non-empty assigned_groups;
      reviewer never assigned "*"
  A1  every active agent's adapter directory exists (adapters/<adapter>/)
      unless adapter is cursor/claude-code (pre-existing activation paths)
  A2  adapter env examples agree with the registry (USER_ID,
      L9_MEMORY_AGENT_ID, L9_MEMORY_SOURCE lines match the agent entry)
  S1  no secret-looking values anywhere in the pack (long opaque literals
      assigned to *TOKEN*/*SECRET*/*KEY* vars); .env files allowed only as
      *.example

Exit 0 = pass, 1 = violations (all listed), 2 = environment error.
Usage: validate_agents.py [--root environment/agents]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("error: pyyaml required (pip install pyyaml)\n")
    sys.exit(2)

KEBAB = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
VALID_STATUS = {"active", "planned", "retired"}
SECRET_ASSIGN = re.compile(
    r"(?i)\b[\w-]*(token|secret|apikey|api_key|password)[\w-]*\s*[:=]\s*"
    r"['\"]?([A-Za-z0-9_\-\.\+/]{24,})['\"]?"
)
PLACEHOLDER = re.compile(r"[<>{}$*]|value of|example|CHANGE|REPLACE|\.\.\.")
ENV_VAR_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")  # values that are env-var NAMES, not secrets

errors: list[str] = []


def err(rule: str, msg: str) -> None:
    errors.append(f"[{rule}] {msg}")


def check_registry(root: Path) -> dict:
    reg_path = root / "agent_registry.yaml"
    if not reg_path.is_file():
        err("R1", f"missing {reg_path}")
        return {}
    try:
        reg = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        err("R1", f"registry does not parse: {exc}")
        return {}
    if not isinstance(reg, dict):
        err("R1", "registry is not a mapping")
        return {}
    for fld in ("schema_version", "roles", "agents"):
        if fld not in reg:
            err("R1", f"registry missing '{fld}'")
    return reg


def check_agents(reg: dict) -> None:
    roles = reg.get("roles") or {}
    agents = reg.get("agents") or {}
    seen: dict[str, str] = {}
    for key, a in agents.items():
        if not isinstance(a, dict):
            err("R2", f"agents.{key} is not a mapping")
            continue
        aid = a.get("agent_id", "")
        if aid != key:
            err("R2", f"agents.{key}: agent_id '{aid}' != key")
        if not KEBAB.match(aid or ""):
            err("R2", f"agents.{key}: agent_id not kebab-case")
        snake = (aid or "").replace("-", "_")
        expect = {
            "user_id": f"{snake}_agent",
            "source": aid,
            "principal_id": f"{aid}-memory-client",
            "token_env": f"L9_MEMORY_TOKEN__{snake.upper()}",
        }
        for fld, want in expect.items():
            got = a.get(fld)
            if got != want:
                err("R3", f"agents.{key}.{fld}: '{got}' != expected '{want}'")
        for fld in ("agent_id", "user_id", "principal_id", "token_env"):
            val = a.get(fld)
            if val in seen:
                err("R4", f"duplicate {fld} '{val}' (also {seen[val]})")
            elif val:
                seen[val] = key
        role = a.get("role")
        if role not in roles:
            err("R5", f"agents.{key}: unknown role '{role}'")
        if a.get("status", "active") not in VALID_STATUS:
            err("R5", f"agents.{key}: bad status '{a.get('status')}'")
        groups = a.get("assigned_groups") or []
        if role and role != "observer" and not groups:
            err("R6", f"agents.{key}: writing role '{role}' with no assigned_groups")
        if role == "reviewer" and "*" in groups:
            err("R6", f"agents.{key}: reviewer may not be assigned '*'")


def check_adapters(reg: dict, root: Path) -> None:
    preexisting = {"cursor", "claude-code"}
    for key, a in (reg.get("agents") or {}).items():
        if not isinstance(a, dict) or a.get("status", "active") != "active":
            continue
        adapter = a.get("adapter", key)
        if adapter in preexisting:
            continue
        adir = root / "adapters" / adapter
        if not adir.is_dir():
            err("A1", f"agents.{key}: adapter dir missing: {adir}")
            continue
        env_files = list(adir.glob("*.env.example"))
        for envf in env_files:
            text = envf.read_text(encoding="utf-8")
            for var, fld in (("USER_ID", "user_id"),
                             ("L9_MEMORY_AGENT_ID", "agent_id"),
                             ("L9_MEMORY_SOURCE", "source")):
                m = re.search(rf"^{var}=(.+)$", text, re.M)
                if not m:
                    err("A2", f"{envf.name}: missing {var}")
                elif m.group(1).strip() != a.get(fld):
                    err("A2", f"{envf.name}: {var}='{m.group(1).strip()}' "
                              f"!= registry '{a.get(fld)}'")


def check_secrets(root: Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if path.suffix == ".env" and not path.name.endswith(".env.example"):
            err("S1", f"raw .env file committed: {path}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for m in SECRET_ASSIGN.finditer(text):
            if PLACEHOLDER.search(m.group(2)) or PLACEHOLDER.search(
                    m.group(0)):
                continue
            if ENV_VAR_NAME.match(m.group(2)):
                continue  # e.g. token_env: L9_MEMORY_TOKEN__MANUS (a name, not a value)
            err("S1", f"{path}: possible committed secret "
                      f"('{m.group(1)}...' = '{m.group(2)[:8]}…')")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path,
                    default=Path(__file__).resolve().parent.parent)
    args = ap.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        sys.stderr.write(f"error: root not found: {root}\n")
        return 2

    reg = check_registry(root)
    if reg:
        check_agents(reg)
        check_adapters(reg, root)
    check_secrets(root)

    if errors:
        sys.stderr.write(f"FAIL — {len(errors)} violation(s):\n")
        for e in errors:
            sys.stderr.write(f"  {e}\n")
        return 1
    n = len((reg.get("agents") or {}))
    sys.stderr.write(f"PASS — registry valid, {n} agent(s), adapters "
                     "consistent, no committed secrets\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
