#!/usr/bin/env python3
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/tools/render_principals.py
#   layer: tool
#   owner: governance-control-plane
#   status: active
#   version: 1.1.0
#   updated: 2026-07-30
"""Render l9-graphiti-memory auth_tokens.json from the agent registry.

Reads (relative to trusted bases — never free-form absolute CLI paths):
  * ``--root`` / ``--registry``     agent_registry.yaml (identities + roles, NO tokens)
  * ``--out-dir`` / ``--tokens``    agent_tokens.local.json (gitignored token map)

Writes:
  * ``--out-dir`` / ``--out``       auth_tokens.json for the memory server

CLI contract (Sonar LLM/CLI path-escape):
  * ``--root`` and ``--out-dir`` are the only trusted directory roots.
  * ``--registry``, ``--tokens``, and ``--out`` MUST be basenames only
    (single path segment — no directories, no ``..``, no absolute paths, no
    ``~``, no ``/`` or ``\\``); they are joined under the matching root via
    ``os.path.join`` + ``realpath`` + ``commonpath``.

Fails loudly on: path escape, duplicate identities, unknown roles,
missing/duplicate tokens, or empty grants for writing roles.
"""

from __future__ import annotations

import argparse
import json
import os
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


def require_basename(name: str, *, label: str) -> str:
    """Reject anything that is not a single path segment (basename only)."""
    if not name or name.strip() != name:
        fail(f"{label} must be a non-empty basename without surrounding whitespace")
    if name in (".", ".."):
        fail(f"{label} must be a basename (single path segment; not '.' or '..'): {name}")
    if "/" in name or "\\" in name or os.sep in name or (os.altsep and os.altsep in name):
        fail(
            f"{label} must be a basename only (no directories, absolute paths, "
            f"relative multi-segment paths, ~, or '..'): {name}"
        )
    path = Path(name)
    if path.is_absolute() or path.expanduser() != path:
        fail(f"{label} must be a basename (no absolute path or ~): {name}")
    if path.name != name or len(path.parts) != 1:
        fail(f"{label} must be a basename (single path segment): {name}")
    return name


def under_root(root: Path, rel: str, *, label: str) -> Path:
    """Join basename under trusted ``root``; refuse escapes (Sonar-recognized pattern)."""
    name = require_basename(rel, label=label)
    base = os.path.realpath(str(root))
    if not os.path.isdir(base):
        fail(f"trusted root is not a directory: {root}")
    # Construct from base + basename only — never trust a free-form relative escape.
    target = os.path.realpath(os.path.join(base, name))
    if os.path.commonpath([base, target]) != base:
        fail(f"{label} escapes trusted root {base}: {name}")
    return Path(target)


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        fail(f"registry not found: {path}")
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        fail(f"registry did not parse to a mapping: {path}")
    return data


def write_namespaces_for(agent: dict, role: str, workspace: str) -> list[str]:
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
        # The registry's workspace_group, not a hardcoded literal — must stay
        # in lockstep with ops/graphiti/group_registry.yaml.
        return [*assigned, workspace]
    return []  # observer


def grants_for(
    agent: dict, role_def: dict, workspace: str
) -> tuple[list[str], list[str], list[str]]:
    """Derive read/write/promote namespace globs for one agent."""
    role = agent["role"]
    read_ns = list(role_def.get("read_namespaces") or [])
    promote_ns = list(role_def.get("promote_namespaces") or [])
    write_ns = write_namespaces_for(agent, role, workspace)
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
    read_ns, write_ns, promote_ns = grants_for(agent, role_def, workspace)
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


def write_under_root(root: Path, rel: str, content: str, *, label: str) -> Path:
    """Validate relative path under root, then write via open()."""
    path = under_root(root, rel, label=label)
    parent = path.parent
    # Parent is still under root (commonpath already enforced on ``path``).
    os.makedirs(parent, exist_ok=True)
    target = os.path.realpath(str(path))
    base = os.path.realpath(str(root))
    if os.path.commonpath([base, target]) != base:
        fail(f"{label} escaped trusted root before write: {rel}")
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(content)
    return Path(target)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--root",
        type=Path,
        required=True,
        help="Trusted pack directory (registry is resolved under this root)",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Trusted directory for --tokens and --out (default: same as --root)",
    )
    ap.add_argument(
        "--registry",
        default="agent_registry.yaml",
        help="Registry basename under --root (default: agent_registry.yaml)",
    )
    ap.add_argument(
        "--tokens",
        default="agent_tokens.local.json",
        help="Token map basename under --out-dir (default: agent_tokens.local.json)",
    )
    ap.add_argument(
        "--out",
        default="auth_tokens.json",
        help="Output basename under --out-dir (default: auth_tokens.json)",
    )
    ap.add_argument("--tenant", default="l9")
    ap.add_argument("--organization", default="quantum-l9")
    ap.add_argument(
        "--include-planned",
        action="store_true",
        help="also emit principals for status=planned agents",
    )
    args = ap.parse_args()

    root = Path(os.path.realpath(str(args.root.expanduser())))
    out_dir = Path(os.path.realpath(str((args.out_dir or args.root).expanduser())))

    # Validate basename-only path contracts up front (before any file I/O).
    registry_path = under_root(root, args.registry, label="--registry")
    tokens_path = under_root(out_dir, args.tokens, label="--tokens")
    _ = under_root(out_dir, args.out, label="--out")  # reject .. / absolute early

    registry = load_yaml(registry_path)
    roles = registry.get("roles") or {}
    agents = registry.get("agents") or {}
    workspace = registry.get("workspace_group", "igor-workspace")

    if not tokens_path.is_file():
        fail(f"token map not found: {tokens_path} (create it locally; never commit it)")
    with open(tokens_path, encoding="utf-8") as fh:
        token_map = json.load(fh)
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

    out_path = write_under_root(out_dir, args.out, json.dumps(out, indent=2) + "\n", label="--out")
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
