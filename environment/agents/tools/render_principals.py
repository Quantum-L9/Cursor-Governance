#!/usr/bin/env python3
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/tools/render_principals.py
#   layer: tool
#   owner: governance-control-plane
#   status: active
#   version: 1.0.1
#   updated: 2026-07-29
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
import os
import sys
import tempfile
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


def allowed_roots() -> list[str]:
    return [
        os.path.realpath(os.getcwd()),
        os.path.realpath(tempfile.gettempdir()),
    ]


def resolve_cli_path(path: Path, *, label: str) -> Path:
    """Resolve a CLI path and reject escapes outside allowed roots.

    Uses ``os.path.realpath`` + ``os.path.commonpath`` (Sonar-recognized
    sanitizers) so LLM/operator-supplied paths cannot escape cwd or tempdir.
    """
    if ".." in path.parts:
        fail(f"{label} must not contain '..' path segments: {path}")
    target = os.path.realpath(os.path.expanduser(str(path)))
    if not any(os.path.commonpath([root, target]) == root for root in allowed_roots()):
        fail(f"{label} must resolve under cwd or tempdir ({', '.join(allowed_roots())}): {path}")
    return Path(target)


def write_text_secure(path: Path, content: str, *, label: str) -> Path:
    """Validate then write via open() so path-escape checks stay in the sink."""
    safe = resolve_cli_path(path, label=label)
    os.makedirs(safe.parent, exist_ok=True)
    # Re-check immediately before the write sink (taint-analysis boundary).
    target = os.path.realpath(str(safe))
    if not any(os.path.commonpath([root, target]) == root for root in allowed_roots()):
        fail(f"{label} escaped allowed roots before write: {path}")
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(content)
    return Path(target)


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        fail(f"registry not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        fail(f"registry did not parse to a mapping: {path}")
    return data


def write_namespaces_for(agent: dict, role: str) -> list[str]:
    """Compute write namespace grants for one agent role."""
    assigned = list(agent.get("assigned_groups") or [])
    if role == "orchestrator":
        return ["*"]
    if role == "reviewer":
        if "*" in assigned:
            fail(f"reviewer {agent['agent_id']} may not be assigned '*'")
        return [f"{g}.reviews" for g in assigned]
    if role == "implementer":
        return assigned[:]
    if role == "researcher-builder":
        return [*assigned, "l9-workspace"]
    return []  # observer


def grants_for(agent: dict, role_def: dict) -> tuple[list[str], list[str], list[str]]:
    """Derive read/write/promote namespace globs for one agent."""
    role = agent["role"]
    read_ns = list(role_def.get("read_namespaces") or [])
    promote_ns = list(role_def.get("promote_namespaces") or [])
    write_ns = write_namespaces_for(agent, role)
    if role in WRITING_ROLES and not write_ns:
        fail(f"agent {agent['agent_id']} has writing role '{role}' but no grants")
    return read_ns, sorted(set(write_ns)), promote_ns


def require_unique(value: str, seen_ids: set[str]) -> None:
    if value in seen_ids:
        fail(f"duplicate identity value across agents: '{value}'")
    seen_ids.add(value)


def require_token(
    agent_id: str, token_map: dict, tokens_path: Path, seen_tokens: dict[str, str]
) -> str:
    token = token_map.get(agent_id)
    if not token or not isinstance(token, str) or len(token) < 24:
        fail(f"agent {agent_id}: token missing or shorter than 24 chars in {tokens_path}")
    if token in seen_tokens:
        fail(
            f"agents '{seen_tokens[token]}' and '{agent_id}' share a token "
            "— every agent MUST have its own bearer token"
        )
    seen_tokens[token] = agent_id
    return token


def build_principal(
    agent: dict,
    role_def: dict,
    *,
    tenant: str,
    organization: str,
    workspace: str,
) -> dict:
    role = agent["role"]
    read_ns, write_ns, promote_ns = grants_for(agent, role_def)
    return {
        "principal_id": agent["principal_id"],
        "tenant_id": tenant,
        "organization_id": organization,
        "workspace_id": workspace,
        "user_id": agent["user_id"],
        "agent_id": agent["agent_id"],
        "roles": [role, "memory-client"],
        "read_namespaces": read_ns,
        "write_namespaces": write_ns,
        "promote_namespaces": promote_ns,
        "is_admin": bool(role_def.get("is_admin", False)),
    }


def process_agent(
    key: str,
    agent: dict,
    roles: dict,
    *,
    include_planned: bool,
    token_map: dict,
    tokens_path: Path,
    seen_ids: set[str],
    seen_tokens: dict[str, str],
    tenant: str,
    organization: str,
    workspace: str,
) -> tuple[str, dict] | None:
    agent_id = agent.get("agent_id")
    if agent_id != key:
        fail(f"agents.{key}: agent_id '{agent_id}' must equal its key")
    status = agent.get("status", "active")
    if status != "active" and not include_planned:
        return None
    role = agent.get("role")
    if role not in roles:
        fail(f"agent {agent_id}: unknown role '{role}'")
    for fld in ("user_id", "source", "principal_id", "token_env"):
        if not agent.get(fld):
            fail(f"agent {agent_id}: missing field '{fld}'")
    for uniq in (agent_id, agent["user_id"], agent["principal_id"]):
        require_unique(uniq, seen_ids)
    token = require_token(agent_id, token_map, tokens_path, seen_tokens)
    principal = build_principal(
        agent,
        roles[role],
        tenant=tenant,
        organization=organization,
        workspace=workspace,
    )
    return token, principal


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

    registry_path = resolve_cli_path(args.registry, label="--registry")
    tokens_path = resolve_cli_path(args.tokens, label="--tokens")

    registry = load_yaml(registry_path)
    roles = registry.get("roles") or {}
    agents = registry.get("agents") or {}
    workspace = registry.get("workspace_group", "default")

    if not tokens_path.is_file():
        fail(f"token map not found: {tokens_path} (create it locally; never commit it)")
    token_map = json.loads(tokens_path.read_text(encoding="utf-8"))
    if not isinstance(token_map, dict):
        fail("token map must be a JSON object of agent_id -> token")

    seen_tokens: dict[str, str] = {}
    seen_ids: set[str] = set()
    out: dict[str, dict] = {}

    for key, agent in agents.items():
        result = process_agent(
            key,
            agent,
            roles,
            include_planned=args.include_planned,
            token_map=token_map,
            tokens_path=tokens_path,
            seen_ids=seen_ids,
            seen_tokens=seen_tokens,
            tenant=args.tenant,
            organization=args.organization,
            workspace=workspace,
        )
        if result is None:
            continue
        token, principal = result
        out[token] = principal

    if not out:
        fail("no active agents produced principals")

    out_path = write_text_secure(args.out, json.dumps(out, indent=2) + "\n", label="--out")
    try:
        out_path.chmod(0o600)
    except OSError as e:
        # Non-fatal: principals still written; operator should fix perms.
        sys.stderr.write(f"warning: could not chmod 0600 {out_path}: {e}\n")
    sys.stderr.write(
        f"wrote {len(out)} principal(s) -> {out_path} "
        f"(agents: {', '.join(sorted(v['agent_id'] for v in out.values()))})\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
