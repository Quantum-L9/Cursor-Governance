#!/usr/bin/env python3
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/tools/validate_agents.py
#   layer: tool
#   owner: governance-control-plane
#   status: active
#   version: 1.3.0
#   updated: 2026-07-31
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
      L9_MEMORY_AGENT_ID, L9_MEMORY_SOURCE) and GRAPHITI_MCP_URL matches
      production_url+mcp_path (or explicit full URL) when set
  A3  adapter contract (ADAPTER_CONTRACT.md): README.md, env example,
      MCP carrier file, bootstrap/instructions file present
  A4  MCP carriers must not default to loopback (127.0.0.1 / localhost)
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
PREEXISTING_ADAPTERS = frozenset({"cursor", "claude-code"})
ENV_FIELD_CHECKS = (
    ("USER_ID", "user_id"),
    ("L9_MEMORY_AGENT_ID", "agent_id"),
    ("L9_MEMORY_SOURCE", "source"),
)
MCP_CARRIERS = (
    "mcp.template.json",
    "mcp-connector.json",
    "settings.template.json",
    "config.toml.example",
)
BOOTSTRAP_GLOBS = (
    "session_bootstrap.md",
    "agents-block.md",
    "gemini-block.md",
    "bootstrap.template.md",
)

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


def _expected_identity_fields(aid: str) -> dict[str, str]:
    snake = aid.replace("-", "_")
    return {
        "user_id": f"{snake}_agent",
        "source": aid,
        "principal_id": f"{aid}-memory-client",
        "token_env": f"L9_MEMORY_TOKEN__{snake.upper()}",
    }


def _check_identity_fields(key: str, agent: dict) -> None:
    aid = agent.get("agent_id", "")
    if aid != key:
        err("R2", f"agents.{key}: agent_id '{aid}' != key")
    if not KEBAB.match(aid or ""):
        err("R2", f"agents.{key}: agent_id not kebab-case")
    for fld, want in _expected_identity_fields(aid or "").items():
        got = agent.get(fld)
        if got != want:
            err("R3", f"agents.{key}.{fld}: '{got}' != expected '{want}'")


def _check_uniqueness(key: str, agent: dict, seen: dict[str, str]) -> None:
    for fld in ("agent_id", "user_id", "principal_id", "token_env"):
        val = agent.get(fld)
        if val in seen:
            err("R4", f"duplicate {fld} '{val}' (also {seen[val]})")
        elif val:
            seen[val] = key


def _check_role_and_groups(key: str, agent: dict, roles: dict) -> None:
    role = agent.get("role")
    if role not in roles:
        err("R5", f"agents.{key}: unknown role '{role}'")
    if agent.get("status", "active") not in VALID_STATUS:
        err("R5", f"agents.{key}: bad status '{agent.get('status')}'")
    groups = agent.get("assigned_groups") or []
    if role and role != "observer" and not groups:
        err("R6", f"agents.{key}: writing role '{role}' with no assigned_groups")
    if role == "reviewer" and "*" in groups:
        err("R6", f"agents.{key}: reviewer may not be assigned '*'")


def check_one_agent(key: str, agent: dict, roles: dict, seen: dict[str, str]) -> None:
    if not isinstance(agent, dict):
        err("R2", f"agents.{key} is not a mapping")
        return
    _check_identity_fields(key, agent)
    _check_uniqueness(key, agent, seen)
    _check_role_and_groups(key, agent, roles)


def check_agents(reg: dict) -> None:
    roles = reg.get("roles") or {}
    agents = reg.get("agents") or {}
    seen: dict[str, str] = {}
    for key, agent in agents.items():
        check_one_agent(key, agent, roles, seen)


def _check_env_example(envf: Path, agent: dict, production_url: str | None) -> None:
    text = envf.read_text(encoding="utf-8")
    for var, fld in ENV_FIELD_CHECKS:
        m = re.search(rf"^{var}=(.+)$", text, re.M)
        if not m:
            err("A2", f"{envf.name}: missing {var}")
        elif m.group(1).strip() != agent.get(fld):
            err(
                "A2",
                f"{envf.name}: {var}='{m.group(1).strip()}' != registry '{agent.get(fld)}'",
            )
    url_m = re.search(r"^GRAPHITI_MCP_URL=(.+)$", text, re.M)
    tok_m = re.search(r"^GRAPHITI_MCP_TOKEN=(.+)$", text, re.M)
    if not url_m:
        err("A2", f"{envf.name}: missing GRAPHITI_MCP_URL")
    elif production_url:
        got = url_m.group(1).strip()
        expected_full = production_url.rstrip("/") + "/graphiti/mcp"
        if got not in (production_url, expected_full) and not got.endswith("/graphiti/mcp"):
            err(
                "A2",
                f"{envf.name}: GRAPHITI_MCP_URL='{got}' "
                f"expected '{expected_full}' (cloud Graphiti path)",
            )
    # A2 (inverted by the zero-static-secret contract, §12/S3): the bearer must
    # be ABSENT from an agent surface example, not present-as-a-placeholder.
    #
    # This rule used to require GRAPHITI_MCP_TOKEN and merely police its shape.
    # That encoded the old posture — every surface carried a bearer, and review
    # only checked it was not a live one. A placeholder in a committed example is
    # an instruction to paste a real token into a model-controlled environment,
    # which is exactly what the capability plane removes. Memory now resolves
    # through the brokered graphiti.* capabilities, so a token here is a
    # violation regardless of its value.
    if tok_m:
        err(
            "A2",
            f"{envf.name}: GRAPHITI_MCP_TOKEN must be ABSENT from a model-controlled "
            "surface; memory resolves through the brokered graphiti.* capabilities "
            "(contract S3/§12)",
        )


def _check_mcp_no_loopback_default(key: str, adir: Path) -> None:
    for name in MCP_CARRIERS:
        path = adir / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if "127.0.0.1" in text or "localhost" in text:
            err(
                "A4",
                f"agents.{key}: {name} must not default to loopback "
                "(use https://memory.quantumaipartners.com/graphiti/mcp via GRAPHITI_MCP_URL)",
            )


def _check_adapter_contract(key: str, adir: Path) -> None:
    if not (adir / "README.md").is_file():
        err("A3", f"agents.{key}: missing README.md in {adir.name}/")
    env_examples = list(adir.glob("*.env.example"))
    if not env_examples:
        err("A3", f"agents.{key}: missing environment.env.example in {adir.name}/")
    if not any((adir / name).is_file() for name in MCP_CARRIERS):
        err(
            "A3",
            f"agents.{key}: missing MCP carrier (one of {', '.join(MCP_CARRIERS)}) in {adir.name}/",
        )
    if not any((adir / name).is_file() for name in BOOTSTRAP_GLOBS):
        err(
            "A3",
            f"agents.{key}: missing bootstrap/instructions "
            f"(one of {', '.join(BOOTSTRAP_GLOBS)}) in {adir.name}/",
        )
    _check_mcp_no_loopback_default(key, adir)


def check_one_adapter(key: str, agent: dict, root: Path, production_url: str | None) -> None:
    if not isinstance(agent, dict) or agent.get("status", "active") != "active":
        return
    adapter = agent.get("adapter", key)
    if adapter in PREEXISTING_ADAPTERS:
        return
    adir = root / "adapters" / adapter
    if not adir.is_dir():
        err("A1", f"agents.{key}: adapter dir missing: {adir}")
        return
    _check_adapter_contract(key, adir)
    for envf in adir.glob("*.env.example"):
        _check_env_example(envf, agent, production_url)


def check_adapters(reg: dict, root: Path) -> None:
    production_url = None
    mem = reg.get("memory") or {}
    if isinstance(mem, dict):
        production_url = mem.get("production_url")
        if production_url and not str(production_url).startswith("https://"):
            err("R1", f"memory.production_url must be https://…, got '{production_url}'")
    for key, agent in (reg.get("agents") or {}).items():
        check_one_adapter(key, agent, root, production_url)


def _is_secret_literal(match: re.Match[str]) -> bool:
    value = match.group(2)
    if PLACEHOLDER.search(value) or PLACEHOLDER.search(match.group(0)):
        return False
    if ENV_VAR_NAME.match(value):
        return False  # e.g. token_env: L9_MEMORY_TOKEN__MANUS (a name, not a value)
    return True


def _scan_file_for_secrets(path: Path) -> None:
    if path.suffix == ".env" and not path.name.endswith(".env.example"):
        err("S1", f"raw .env file committed: {path}")
        return
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return
    for match in SECRET_ASSIGN.finditer(text):
        if _is_secret_literal(match):
            err(
                "S1",
                f"{path}: possible committed secret "
                f"('{match.group(1)}...' = '{match.group(2)[:8]}…')",
            )


def check_secrets(root: Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        _scan_file_for_secrets(path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
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
    n = len(reg.get("agents") or {})
    sys.stderr.write(
        f"PASS — registry valid, {n} agent(s), adapters consistent, no committed secrets\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
