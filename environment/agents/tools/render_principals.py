#!/usr/bin/env python3
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/tools/render_principals.py
#   layer: tool
#   owner: governance-control-plane
#   status: active
#   version: 1.0.0
#   updated: 2026-07-28
"""Render l9-graphiti-memory auth_tokens.json from the agent registry.

Reads:
  * agent_registry.yaml               (committed; identities + roles, NO tokens)
  * agent_tokens.local.json           (gitignored; {"<agent_id>": "<bearer token>"})

Writes:
  * auth_tokens.json for the memory server: one principal per active agent,
    namespace grants derived from role + assigned_groups.

Fails loudly on: duplicate identities, unknown roles, missing/duplicate tokens,
tokens that look committed (registry path), or empty grants for writing roles.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("error: pyyaml required (pip install pyyaml)\n")
    sys.exit(2)

WRITING_ROLES = {"orchestrator", "implementer", "researcher-builder", "reviewer"}


def fail(msg: str) -> None:
    sys.stderr.write(f"error: {msg}\n")
    sys.exit(1)


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        fail(f"registry not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        fail(f"registry did not parse to a mapping: {path}")
    return data


def grants_for(agent: dict, role_def: dict) -> tuple[list[str], list[str], list[str]]:
    """Derive read/write/promote namespace globs for one agent."""
    role = agent["role"]
    assigned = list(agent.get("assigned_groups") or [])
    read_ns = list(role_def.get("read_namespaces") or [])
    promote_ns = list(role_def.get("promote_namespaces") or [])

    if role == "orchestrator":
        write_ns = ["*"]
    elif role == "reviewer":
        if "*" in assigned:
            fail(f"reviewer {agent['agent_id']} may not be assigned '*'")
        write_ns = [f"{g}.reviews" for g in assigned]
    elif role in ("implementer", "researcher-builder"):
        write_ns = assigned[:]
        if role == "researcher-builder":
            write_ns.append("l9-workspace")
    else:  # observer
        write_ns = []

    if role in WRITING_ROLES and not write_ns:
        fail(f"agent {agent['agent_id']} has writing role '{role}' but no grants")
    return read_ns, sorted(set(write_ns)), promote_ns


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", required=True, type=Path)
    ap.add_argument(
        "--tokens", required=True, type=Path, help="agent_tokens.local.json — gitignored token map"
    )
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--tenant", default="l9")
    ap.add_argument("--organization", default="quantum-l9")
    ap.add_argument(
        "--include-planned",
        action="store_true",
        help="also emit principals for status=planned agents",
    )
    args = ap.parse_args()

    registry = load_yaml(args.registry)
    roles = registry.get("roles") or {}
    agents = registry.get("agents") or {}
    workspace = registry.get("workspace_group", "default")

    if not args.tokens.is_file():
        fail(f"token map not found: {args.tokens} (create it locally; never commit it)")
    token_map = json.loads(args.tokens.read_text(encoding="utf-8"))
    if not isinstance(token_map, dict):
        fail("token map must be a JSON object of agent_id -> token")

    seen_tokens: dict[str, str] = {}
    seen_ids: set[str] = set()
    out: dict[str, dict] = {}

    for key, agent in agents.items():
        agent_id = agent.get("agent_id")
        if agent_id != key:
            fail(f"agents.{key}: agent_id '{agent_id}' must equal its key")
        status = agent.get("status", "active")
        if status != "active" and not args.include_planned:
            continue
        role = agent.get("role")
        if role not in roles:
            fail(f"agent {agent_id}: unknown role '{role}'")
        for fld in ("user_id", "source", "principal_id", "token_env"):
            if not agent.get(fld):
                fail(f"agent {agent_id}: missing field '{fld}'")
        for uniq in (agent_id, agent["user_id"], agent["principal_id"]):
            if uniq in seen_ids:
                fail(f"duplicate identity value across agents: '{uniq}'")
            seen_ids.add(uniq)

        token = token_map.get(agent_id)
        if not token or not isinstance(token, str) or len(token) < 24:
            fail(f"agent {agent_id}: token missing or shorter than 24 chars in {args.tokens}")
        if token in seen_tokens:
            fail(
                f"agents '{seen_tokens[token]}' and '{agent_id}' share a token "
                "— every agent MUST have its own bearer token"
            )
        seen_tokens[token] = agent_id

        read_ns, write_ns, promote_ns = grants_for(agent, roles[role])
        out[token] = {
            "principal_id": agent["principal_id"],
            "tenant_id": args.tenant,
            "organization_id": args.organization,
            "workspace_id": workspace,
            "user_id": agent["user_id"],
            "agent_id": agent_id,
            "roles": [role, "memory-client"],
            "read_namespaces": read_ns,
            "write_namespaces": write_ns,
            "promote_namespaces": promote_ns,
            "is_admin": bool(roles[role].get("is_admin", False)),
        }

    if not out:
        fail("no active agents produced principals")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    try:
        args.out.chmod(0o600)
    except OSError as e:
        # Non-fatal: principals still written; operator should fix perms.
        sys.stderr.write(f"warning: could not chmod 0600 {args.out}: {e}\n")
    sys.stderr.write(
        f"wrote {len(out)} principal(s) -> {args.out} "
        f"(agents: {', '.join(sorted(v['agent_id'] for v in out.values()))})\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
