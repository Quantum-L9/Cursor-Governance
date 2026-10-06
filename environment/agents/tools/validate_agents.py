#!/usr/bin/env python3
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/tools/validate_agents.py
#   layer: tool
#   owner: governance-control-plane
#   status: active
#   version: 2.0.0
#   updated: 2026-10-06
"""Operating-plane agent-bindings validator (peer of validate_claude_env.py).

Validates ``environment/agents/agent_registry.yaml`` as
``l9.cursor-governance.agent-bindings/v2`` (ADR-0039): the registry owns
local operating-plane bindings only. Canonical ActorIdentity and
SurfaceIdentity are *referenced* from the committed, receipted projection
``generated/governance/canonical_identity.yaml`` (ADR-0038), whose
provenance, digests and receipt are owned by
``tools/assurance/check_canonical_identity_projection.py``. ``make agents-env``
runs that assurance first and this validator second; this file never fetches
the upstream authority and never re-implements the receipt assurance.

Checks:
  R1  registry parses; schema == l9.cursor-governance.agent-bindings/v2;
      roles and agents are mappings
  R2  binding key == canonical actor id derived from actor_ref's fragment
      (l9.actor-registry/global@1#<id>); kebab-case
  R3  no local redeclaration of canonical identity (agent_id, source,
      surfaces, actor_kind, actor_status, surface_status, aliases, plus any
      field the registry's own forbidden_local_identity_fields names)
  R4  actor_ref / user_id / principal_id / token_env unique across bindings
  R5  role exists in the roles catalog; binding_status in
      {active, planned, retired}; user_id and principal_id non-empty;
      token_env (when present) is an environment-variable NAME
  R6  writing roles (non-observer) declare non-empty assigned_groups;
      reviewer never assigned "*"
  R7  the canonical identity projection is present, parses, carries the
      expected schema, is non-canonical, and is not the UNGENERATED
      placeholder (full git SHA source_revision); its actors / surfaces
      collections are lists
  R8  actor_ref resolves to a projected canonical actor (an alias is not a
      canonical ref); an active binding requires a current actor
  R9  surface_refs is a non-empty list of l9.surface-registry/global@1#<id>
      refs, each resolving to a projected canonical surface (aliases
      rejected); an active binding requires current surfaces
  R10 PEER_RUNTIME_BINDINGS.yaml: every peer is an active binding with
      agent_ref == key; every execution surface is a projected canonical
      surface and is among that binding's resolved surface_refs
  A1  every active binding's adapter directory exists (adapters/<adapter>/)
      unless adapter is cursor/claude-code/none (pre-existing or private)
  A2  adapter env examples agree with the binding: USER_ID == user_id,
      L9_MEMORY_AGENT_ID == canonical actor id derived from actor_ref,
      L9_MEMORY_SOURCE == that same derived actor id; GRAPHITI_MCP_URL /
      GRAPHITI_MCP_TOKEN must be absent (retired provider transport)
  A3  adapter contract (ADAPTER_CONTRACT.md): README.md, env example,
      MCP carrier file, bootstrap/instructions file present
  A4  MCP carriers must not default to loopback (127.0.0.1 / localhost)
  S1  no secret-looking values anywhere in the pack (long opaque literals
      assigned to *TOKEN*/*SECRET*/*KEY* vars); .env files allowed only as
      *.example

Exit 0 = pass, 1 = violations (all listed), 2 = environment error.
Usage: validate_agents.py [--root environment/agents] [--projection PATH]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("error: pyyaml required (pip install pyyaml)\n")
    sys.exit(2)

BINDINGS_SCHEMA = "l9.cursor-governance.agent-bindings/v2"
PROJECTION_SCHEMA = "l9.projection.cursor-governance-identity/v1"
DEFAULT_PROJECTION_PATH = Path("generated/governance/canonical_identity.yaml")
ACTOR_PREFIX = "l9.actor-registry/global@1#"
SURFACE_PREFIX = "l9.surface-registry/global@1#"
FORBIDDEN_LOCAL_IDENTITY_FIELDS = frozenset(
    {
        "agent_id",
        "source",
        "surfaces",
        "actor_kind",
        "actor_status",
        "surface_status",
        "aliases",
    }
)

KEBAB = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
VALID_BINDING_STATUS = {"active", "planned", "retired"}
SECRET_ASSIGN = re.compile(
    r"(?i)\b[\w-]*(token|secret|apikey|api_key|password)[\w-]*\s*[:=]\s*"
    r"['\"]?([A-Za-z0-9_\-\.\+/]{24,})['\"]?"
)
PLACEHOLDER = re.compile(r"[<>{}$*]|value of|example|CHANGE|REPLACE|\.\.\.")
ENV_VAR_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")  # values that are env-var NAMES, not secrets
PREEXISTING_ADAPTERS = frozenset({"cursor", "claude-code", "none"})
DEFAULT_IDENTITY_ENV = {
    "user_id": "USER_ID",
    "agent_id": "L9_MEMORY_AGENT_ID",
    "source": "L9_MEMORY_SOURCE",
}
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
NOT_CANONICAL_REF = "aliases are not canonical refs"


def derive_actor_id(actor_ref: Any) -> str | None:
    """Canonical actor id from an actor_ref; None when the ref is not canonical.

    The fragment of ``l9.actor-registry/global@1#<id>`` IS the agent_id and the
    memory source (ADR-0039). Neither is stored locally.
    """
    return _fragment(actor_ref, ACTOR_PREFIX)


def derive_surface_id(surface_ref: Any) -> str | None:
    return _fragment(surface_ref, SURFACE_PREFIX)


def _fragment(ref: Any, prefix: str) -> str | None:
    if not isinstance(ref, str) or not ref.startswith(prefix):
        return None
    return ref[len(prefix) :] or None


class Projection:
    """Canonical identities indexed from the committed projection (R7)."""

    def __init__(self, document: Mapping[str, Any]) -> None:
        self.actors = _index_by_id(document.get("actors"))
        self.surfaces = _index_by_id(document.get("surfaces"))
        self.actor_aliases = _alias_targets(document.get("actor_aliases"))
        self.surface_aliases = _alias_targets(document.get("surface_aliases"))


def _index_by_id(collection: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(collection, list):
        return {}
    indexed: dict[str, Mapping[str, Any]] = {}
    for item in collection:
        if isinstance(item, Mapping) and isinstance(item.get("id"), str) and item["id"]:
            indexed.setdefault(item["id"], item)
    return indexed


def _alias_targets(collection: Any) -> dict[str, str]:
    if not isinstance(collection, list):
        return {}
    return {
        str(item["alias"]): str(item.get("canonical"))
        for item in collection
        if isinstance(item, Mapping) and item.get("alias")
    }


class Validator:
    def __init__(self, root: Path, projection_path: Path) -> None:
        self.root = root
        self.projection_path = projection_path
        self.errors: list[str] = []
        self.registry: dict[str, Any] = {}
        self.projection: Projection | None = None
        self.forbidden_fields: frozenset[str] = FORBIDDEN_LOCAL_IDENTITY_FIELDS
        self.identity_env: dict[str, str] = dict(DEFAULT_IDENTITY_ENV)

    def err(self, rule: str, msg: str) -> None:
        self.errors.append(f"[{rule}] {msg}")

    # ------------------------------------------------------------------ R1
    def load_registry(self) -> dict[str, Any]:
        reg_path = self.root / "agent_registry.yaml"
        if not reg_path.is_file():
            self.err("R1", f"missing {reg_path}")
            return {}
        try:
            reg = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            self.err("R1", f"registry does not parse: {exc}")
            return {}
        return self.adopt_registry(reg)

    def adopt_registry(self, reg: Any) -> dict[str, Any]:
        if not isinstance(reg, dict):
            self.err("R1", "registry is not a mapping")
            return {}
        if reg.get("schema") != BINDINGS_SCHEMA:
            self.err("R1", f"registry schema must be {BINDINGS_SCHEMA}, got '{reg.get('schema')}'")
        for fld in ("roles", "agents"):
            if not isinstance(reg.get(fld), dict):
                self.err("R1", f"registry '{fld}' missing or not a mapping")
        declared = reg.get("forbidden_local_identity_fields")
        if isinstance(declared, list):
            self.forbidden_fields = FORBIDDEN_LOCAL_IDENTITY_FIELDS | {
                item for item in declared if isinstance(item, str)
            }
        memory = reg.get("memory")
        identity_env = memory.get("identity_env") if isinstance(memory, dict) else None
        if isinstance(identity_env, dict):
            for key, default in DEFAULT_IDENTITY_ENV.items():
                value = identity_env.get(key, default)
                if isinstance(value, str) and ENV_VAR_NAME.match(value):
                    self.identity_env[key] = value
                else:
                    self.err(
                        "R1", f"memory.identity_env.{key} must be an env-var name, got '{value}'"
                    )
        self.registry = reg
        return reg

    # ------------------------------------------------------------------ R7
    def load_projection(self) -> Projection | None:
        path = self.projection_path
        if not path.is_file():
            self.err("R7", f"canonical identity projection missing: {path}")
            return None
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            self.err("R7", f"canonical identity projection does not parse: {exc}")
            return None
        return self.adopt_projection(doc)

    def adopt_projection(self, doc: Any) -> Projection | None:
        if not isinstance(doc, dict):
            self.err("R7", "canonical identity projection is not a mapping")
            return None
        before = len(self.errors)
        if doc.get("schema") != PROJECTION_SCHEMA:
            self.err(
                "R7", f"projection schema must be {PROJECTION_SCHEMA}, got '{doc.get('schema')}'"
            )
        if doc.get("canonical") is not False:
            self.err("R7", "projection must declare canonical: false (derived, non-canonical)")
        meta = doc.get("projection")
        revision = meta.get("source_revision") if isinstance(meta, dict) else None
        if not FULL_SHA.match(str(revision or "")):
            self.err(
                "R7",
                "projection source_revision is not a pinned git SHA "
                f"('{revision}'): a placeholder or unresolved projection cannot resolve identity",
            )
        for collection in ("actors", "surfaces"):
            if not isinstance(doc.get(collection), list):
                self.err("R7", f"projection '{collection}' must be a list")
        authority = self.registry.get("identity_authority")
        expected_ref = authority.get("projection_ref") if isinstance(authority, dict) else None
        if expected_ref and doc.get("artifact_id") != expected_ref:
            self.err(
                "R7",
                f"projection artifact_id '{doc.get('artifact_id')}' != "
                f"identity_authority.projection_ref '{expected_ref}'",
            )
        if len(self.errors) != before:
            return None
        self.projection = Projection(doc)
        return self.projection

    # ----------------------------------------------------------- bindings
    def check_agents(self) -> None:
        roles = self.registry.get("roles") or {}
        agents = self.registry.get("agents") or {}
        if not isinstance(agents, dict):
            return
        seen: dict[str, dict[str, str]] = {}
        for key, agent in agents.items():
            self.check_one_agent(str(key), agent, roles, seen)

    def check_one_agent(
        self,
        key: str,
        agent: Any,
        roles: Any,
        seen: dict[str, dict[str, str]],
    ) -> None:
        if not isinstance(agent, dict):
            self.err("R2", f"agents.{key} is not a mapping")
            return
        self._check_forbidden_fields(key, agent)
        self._check_actor_binding(key, agent)
        self._check_uniqueness(key, agent, seen)
        self._check_local_fields(key, agent, roles)
        self._check_surface_bindings(key, agent)

    def _check_forbidden_fields(self, key: str, agent: dict) -> None:
        forbidden = sorted(self.forbidden_fields.intersection(agent))
        if forbidden:
            self.err(
                "R3",
                f"agents.{key} redeclares canonical identity locally: {forbidden} "
                "(derive from actor_ref / surface_refs; ADR-0039)",
            )

    def _is_active(self, agent: dict) -> bool:
        return agent.get("binding_status", "active") == "active"

    def _check_actor_binding(self, key: str, agent: dict) -> None:
        actor_ref = agent.get("actor_ref")
        actor_id = derive_actor_id(actor_ref)
        if actor_id is None:
            self.err(
                "R2", f"agents.{key}.actor_ref must be '{ACTOR_PREFIX}<id>', got '{actor_ref}'"
            )
            return
        if not KEBAB.match(actor_id):
            self.err("R2", f"agents.{key}: canonical actor id '{actor_id}' not kebab-case")
        if actor_id != key:
            self.err("R2", f"agents.{key}: binding key != canonical actor id '{actor_id}'")
        if self.projection is None:
            return
        actor = self.projection.actors.get(actor_id)
        if actor is None:
            alias_of = self.projection.actor_aliases.get(actor_id)
            if alias_of is not None:
                self.err(
                    "R8",
                    f"agents.{key}.actor_ref uses alias '{actor_id}' (canonical: '{alias_of}'); "
                    f"{NOT_CANONICAL_REF}",
                )
            else:
                self.err(
                    "R8",
                    f"agents.{key}.actor_ref does not resolve to a projected actor: {actor_id}",
                )
            return
        if self._is_active(agent) and actor.get("status") != "current":
            self.err(
                "R8",
                f"agents.{key}: active binding references non-current actor '{actor_id}' "
                f"(status '{actor.get('status')}')",
            )

    def _check_surface_bindings(self, key: str, agent: dict) -> None:
        refs = agent.get("surface_refs")
        if not isinstance(refs, list) or not refs:
            self.err("R9", f"agents.{key}.surface_refs must be a non-empty list")
            return
        for ref in refs:
            surface_id = derive_surface_id(ref)
            if surface_id is None:
                self.err(
                    "R9",
                    f"agents.{key}.surface_refs entry must be '{SURFACE_PREFIX}<id>', got '{ref}'",
                )
            elif self.projection is not None:
                self._check_surface_resolves(key, agent, surface_id)

    def _check_surface_resolves(self, key: str, agent: dict, surface_id: str) -> None:
        assert self.projection is not None
        surface = self.projection.surfaces.get(surface_id)
        if surface is None:
            alias_of = self.projection.surface_aliases.get(surface_id)
            if alias_of is not None:
                self.err(
                    "R9",
                    f"agents.{key}.surface_refs uses alias '{surface_id}' "
                    f"(canonical: '{alias_of}'); {NOT_CANONICAL_REF}",
                )
            else:
                self.err(
                    "R9",
                    f"agents.{key}.surface_refs does not resolve to a projected surface: "
                    f"{surface_id}",
                )
            return
        if self._is_active(agent) and surface.get("status") != "current":
            self.err(
                "R9",
                f"agents.{key}: active binding references non-current surface '{surface_id}' "
                f"(status '{surface.get('status')}')",
            )

    def _check_uniqueness(self, key: str, agent: dict, seen: dict[str, dict[str, str]]) -> None:
        for fld in ("actor_ref", "user_id", "principal_id", "token_env"):
            val = agent.get(fld)
            if not isinstance(val, str) or not val:
                continue
            owners = seen.setdefault(fld, {})
            if val in owners:
                self.err("R4", f"duplicate {fld} '{val}' (agents.{key}, also agents.{owners[val]})")
            else:
                owners[val] = key

    def _check_local_fields(self, key: str, agent: dict, roles: Any) -> None:
        role = agent.get("role")
        if not isinstance(roles, dict) or role not in roles:
            self.err("R5", f"agents.{key}: unknown role '{role}'")
        status = agent.get("binding_status", "active")
        if status not in VALID_BINDING_STATUS:
            self.err("R5", f"agents.{key}: bad binding_status '{status}'")
        for fld in ("user_id", "principal_id"):
            val = agent.get(fld)
            if not isinstance(val, str) or not val:
                self.err("R5", f"agents.{key}.{fld} must be a non-empty string")
        token_env = agent.get("token_env")
        if token_env is not None and not (
            isinstance(token_env, str) and ENV_VAR_NAME.match(token_env)
        ):
            self.err(
                "R5",
                f"agents.{key}.token_env must be an environment-variable name, got '{token_env}'",
            )
        groups = agent.get("assigned_groups") or []
        if role and role not in {"observer"} and not groups:
            self.err("R6", f"agents.{key}: writing role '{role}' with no assigned_groups")
        if role == "reviewer" and "*" in groups:
            self.err("R6", f"agents.{key}: reviewer may not be assigned '*'")

    # ------------------------------------------------------------ R10 peers
    def active_bindings(self) -> dict[str, dict]:
        return {
            str(key): agent
            for key, agent in (self.registry.get("agents") or {}).items()
            if isinstance(agent, dict) and self._is_active(agent)
        }

    def check_peer_bindings(self, peers_doc: Any) -> None:
        peers = peers_doc.get("peers") if isinstance(peers_doc, dict) else None
        if not isinstance(peers, dict):
            self.err("R10", "PEER_RUNTIME_BINDINGS.yaml: peers missing")
            return
        if self.projection is None:
            self.err(
                "R10", "peer surfaces cannot be resolved without a verified canonical projection"
            )
            return
        active = self.active_bindings()
        for key, peer in peers.items():
            if not isinstance(peer, dict):
                self.err("R10", f"peers.{key} is not a mapping")
                continue
            agent = active.get(key)
            if agent is None:
                self.err("R10", f"peers.{key}: not an active agent binding")
            if peer.get("agent_ref") != key:
                self.err("R10", f"peers.{key}.agent_ref '{peer.get('agent_ref')}' != key")
            bound = {
                surface_id
                for surface_id in map(derive_surface_id, (agent or {}).get("surface_refs") or [])
                if surface_id is not None
            }
            for binding in (peer.get("execution") or {}).get("bindings") or []:
                surface = binding.get("surface") if isinstance(binding, dict) else None
                if surface not in self.projection.surfaces:
                    self.err(
                        "R10",
                        f"peers.{key}: surface '{surface}' is not a projected canonical "
                        "SurfaceIdentity",
                    )
                if agent is not None and surface not in bound:
                    self.err(
                        "R10", f"peers.{key}: surface '{surface}' not in agents.{key}.surface_refs"
                    )

    def load_and_check_peers(self) -> None:
        path = self.root / "PEER_RUNTIME_BINDINGS.yaml"
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            self.err("R10", f"cannot load {path.name}: {exc}")
            return
        self.check_peer_bindings(doc)

    # ------------------------------------------------------------ adapters
    def expected_env(self, agent: dict) -> dict[str, str | None]:
        """Adapter env values derived from the binding (A2).

        USER_ID comes from the local user_id; L9_MEMORY_AGENT_ID and
        L9_MEMORY_SOURCE are both the canonical actor id derived from actor_ref.
        """
        actor_id = derive_actor_id(agent.get("actor_ref"))
        user_id = agent.get("user_id")
        return {
            self.identity_env["user_id"]: user_id if isinstance(user_id, str) else None,
            self.identity_env["agent_id"]: actor_id,
            self.identity_env["source"]: actor_id,
        }

    def check_env_example_text(self, label: str, text: str, agent: dict) -> None:
        for var, want in self.expected_env(agent).items():
            m = re.search(rf"^{re.escape(var)}=(.+)$", text, re.M)
            if not m:
                self.err("A2", f"{label}: missing {var}")
            elif want is None:
                self.err(
                    "A2",
                    f"{label}: {var} cannot be derived from the binding "
                    "(actor_ref / user_id invalid)",
                )
            elif m.group(1).strip() != want:
                self.err("A2", f"{label}: {var}='{m.group(1).strip()}' != derived '{want}'")
        # Realignment stage C9: no surface example may assign the retired
        # provider transport. Memory is reached through the canonical control
        # plane (ops/memory), bound per checkout; a URL here would re-create the
        # direct front door the campaign removed.
        if re.search(r"^GRAPHITI_MCP_URL=(.+)$", text, re.M):
            self.err(
                "A2",
                f"{label}: GRAPHITI_MCP_URL is a retired provider transport (stage C9); "
                "memory is the canonical l9-graphite-memory control plane, never a URL",
            )
        # Zero-static-secret contract (§12/S3): the bearer must be ABSENT from an
        # agent surface example, not present-as-a-placeholder. A placeholder in a
        # committed example is an instruction to paste a real token into a
        # model-controlled environment.
        if re.search(r"^GRAPHITI_MCP_TOKEN=(.+)$", text, re.M):
            self.err(
                "A2",
                f"{label}: GRAPHITI_MCP_TOKEN must be ABSENT from a model-controlled "
                "surface; memory is the bound stdio control plane "
                "(L9_MEMORY_INTERPRETER), not GRAPHITI_MCP_URL (contract S3/§12)",
            )

    def _check_mcp_no_loopback_default(self, key: str, adir: Path) -> None:
        for name in MCP_CARRIERS:
            path = adir / name
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if "127.0.0.1" in text or "localhost" in text:
                self.err(
                    "A4",
                    f"agents.{key}: {name} must not default to loopback "
                    "(memory is the canonical l9-graphite-memory stdio server, "
                    "never a provider URL)",
                )
            # Stage C7/C8: no adapter carrier may declare the retired provider
            # front door; the only memory server is the package-owned stdio entry.
            try:
                carrier = json.loads(text)
            except json.JSONDecodeError:
                continue
            servers = carrier.get("mcpServers") if isinstance(carrier, dict) else None
            if isinstance(servers, dict) and "graphiti-memory" in servers:
                self.err(
                    "A4",
                    f"agents.{key}: {name} declares the retired graphiti-memory front door; "
                    "declare l9-graphite-memory (stdio) or nothing",
                )

    def _check_adapter_contract(self, key: str, adir: Path) -> None:
        if not (adir / "README.md").is_file():
            self.err("A3", f"agents.{key}: missing README.md in {adir.name}/")
        if not list(adir.glob("*.env.example")):
            self.err("A3", f"agents.{key}: missing environment.env.example in {adir.name}/")
        if not any((adir / name).is_file() for name in MCP_CARRIERS):
            self.err(
                "A3",
                f"agents.{key}: missing MCP carrier (one of {', '.join(MCP_CARRIERS)}) "
                f"in {adir.name}/",
            )
        if not any((adir / name).is_file() for name in BOOTSTRAP_GLOBS):
            self.err(
                "A3",
                f"agents.{key}: missing bootstrap/instructions "
                f"(one of {', '.join(BOOTSTRAP_GLOBS)}) in {adir.name}/",
            )
        self._check_mcp_no_loopback_default(key, adir)

    def check_one_adapter(self, key: str, agent: Any) -> None:
        if not isinstance(agent, dict) or not self._is_active(agent):
            return
        if agent.get("private_entrance") or agent.get("adapter") == "none":
            return
        adapter = agent.get("adapter", key)
        if adapter in PREEXISTING_ADAPTERS:
            return
        adir = self.root / "adapters" / str(adapter)
        if not adir.is_dir():
            self.err("A1", f"agents.{key}: adapter dir missing: {adir}")
            return
        self._check_adapter_contract(key, adir)
        for envf in adir.glob("*.env.example"):
            self.check_env_example_text(envf.name, envf.read_text(encoding="utf-8"), agent)

    def check_adapters(self) -> None:
        for key, agent in (self.registry.get("agents") or {}).items():
            self.check_one_adapter(str(key), agent)

    # ------------------------------------------------------------- secrets
    def _scan_file_for_secrets(self, path: Path) -> None:
        if path.suffix == ".env" and not path.name.endswith(".env.example"):
            self.err("S1", f"raw .env file committed: {path}")
            return
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return
        for match in SECRET_ASSIGN.finditer(text):
            if _is_secret_literal(match):
                self.err(
                    "S1",
                    f"{path}: possible committed secret "
                    f"('{match.group(1)}...' = '{match.group(2)[:8]}…')",
                )

    def check_secrets(self) -> None:
        for path in self.root.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            self._scan_file_for_secrets(path)

    # ---------------------------------------------------------------- run
    def run(self) -> list[str]:
        reg = self.load_registry()
        if reg:
            self.load_projection()
            self.check_agents()
            self.load_and_check_peers()
            self.check_adapters()
        self.check_secrets()
        return self.errors


def _is_secret_literal(match: re.Match[str]) -> bool:
    value = match.group(2)
    if PLACEHOLDER.search(value) or PLACEHOLDER.search(match.group(0)):
        return False
    if ENV_VAR_NAME.match(value):
        return False  # e.g. token_env: L9_MEMORY_TOKEN__MANUS (a name, not a value)
    return True


def default_projection_path(root: Path) -> Path:
    """The committed projection, located from the registry's declared path.

    ``root`` is ``<repo>/environment/agents``; the repository root is two levels
    up. The registry's ``identity_authority.projection_path`` wins when it is a
    relative path; otherwise the ADR-0038 default applies.
    """
    repo_root = root.parent.parent
    reg_path = root / "agent_registry.yaml"
    try:
        reg = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        reg = None
    declared = None
    if isinstance(reg, dict) and isinstance(reg.get("identity_authority"), dict):
        declared = reg["identity_authority"].get("projection_path")
    if isinstance(declared, str) and declared and not Path(declared).is_absolute():
        return repo_root / declared
    return repo_root / DEFAULT_PROJECTION_PATH


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument(
        "--projection",
        type=Path,
        default=None,
        help=(
            "committed canonical identity projection "
            "(default: registry identity_authority.projection_path)"
        ),
    )
    args = ap.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        sys.stderr.write(f"error: root not found: {root}\n")
        return 2
    projection_path = (args.projection or default_projection_path(root)).resolve()

    validator = Validator(root, projection_path)
    errors = validator.run()

    if errors:
        sys.stderr.write(f"FAIL — {len(errors)} violation(s):\n")
        for e in errors:
            sys.stderr.write(f"  {e}\n")
        return 1
    n = len(validator.registry.get("agents") or {})
    sys.stderr.write(
        f"PASS — agent-bindings/v2 valid, {n} binding(s) resolved against "
        f"{projection_path.name}, adapters consistent, no committed secrets\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
