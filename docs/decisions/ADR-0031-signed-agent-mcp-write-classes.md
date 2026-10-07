# ADR-0031: Signed-agent MCP door + dual write classes

## Status

Accepted

## Date

2026-09-13

## Context

ADR-0030 made `MemoryService` (package-owned `l9-graphite-memory` stdio MCP)
the single front door and forbade agent HTTP / Graphiti provider entry. Two
gaps remained:

1. **Identity.** Surfaces still relied on ambient local principals or
   per-agent HTTPS bearers. That either collapsed all local agents into one
   principal or reintroduced a private door per agent.
2. **Cold writes.** Doctrine required `memory.phase_lock` →
   `memory.write_governed` for every model-authored fact, but cold agents
   could not write without SessionStart/phase-lock handoffs.

Operator law (2026-09-13): one shared agents door secret; per-agent **signed**
assertions select registry roles/grants; only the human gets a private
entrance; MCP is the only agent path; HTTP stays sealed; agents must write
ordinary episodic facts without a hook handoff.

## Decision

1. **Trust model 2 (agents).** All agent surfaces share one
   `L9_MEMORY_AGENTS_DOOR_SECRET`. Each surface presents a short-lived HMAC
   assertion binding `agent_id`. The server verifies the assertion with that
   agent's signing key and loads grants from the registry-rendered grant map.
   Spoofing `agent_id=cursor` without Cursor's signing key fails closed.
2. **Human private entrance.** Distinct `L9_MEMORY_HUMAN_DOOR_SECRET` /
   principal `human`. Never placed in agent env. Promote / `is_admin` paths
   require the human principal.
3. **MCP-only.** Agents reach memory only through package-owned
   `l9-graphite-memory` stdio MCP (and deterministic `ops/memory` CLI adapters
   over the same `MemoryService`). Agent HTTP URLs, `l9-shared-memory` HTTPS,
   and Graphiti provider clients remain forbidden side doors.
4. **Dual write classes.**
   - `memory.write_agent` — cold-safe model write. No SessionStart receipt. No
     `phase_lock`. Allowlisted classes (and aliases): `insight` (`lesson`),
     `decision`, `observation` (`note`), `episodic`, `meta` (`pickup`),
     `preference`, `semantic`, `constraint`.
   - `memory.write_governed` — conflict-sensitive model write. Requires a
     current `memory.phase_lock` + matching namespace snapshot digest.
   - `memory.ingest` — not a model bypass for either class.
5. **Repository mutation unchanged.** Governed repo edits still require
   session hydration only. Memory phase-lock never authorizes git.

## Consequences

- Amend ADR-0030 item 7 to recognize `memory.write_agent` alongside
  `write_governed`.
- Rewrite `agent_registry` / `render_principals` away from unique per-agent
  HTTPS bearers toward shared door + per-agent signing keys + human secret.
- Package `l9-graphite-memory` ≥ 2.4.0 implements assertion auth and both MCP
  write tools; Cursor-Governance binding pins that release.
- Skills/rules teach cold agents to call `memory.write_agent` first; use
  `phase_lock` → `write_governed` only when consistency against concurrent
  writers matters.

## Canonical identity assertion (2026-10-07)

The signed-agent credential and canonical identity evidence are different objects.

| Transport | What it proves | What it grants |
|---|---|---|
| `L9_MEMORY_AGENT_ASSERTION` (`agent_id.exp.nonce.hexsig`) | possession of the per-agent signing key | nothing by itself; the grant map supplies roles and namespaces |
| `L9_MEMORY_IDENTITY_ASSERTION_JSON` + `L9_MEMORY_IDENTITY_ASSERTION_HMAC` | `l9.identity-assertion/v1` ActorIdentity resolution | nothing |

Cursor-Governance produces the identity assertion. `ops/memory/print_agent_assertion_env.py` resolves the actor with the existing `agent_identity` resolver, reads `actor_ref` and `surface_refs` from `environment/agents/agent_registry.yaml`, and reads projection digests from `generated/governance/canonical_identity.yaml` and its receipt. It does not guess an actor or a surface. When actor identity resolves and surface evidence does not, `surface_identity` is `unknown` and `result` stays `resolved`, because SurfaceIdentity is non-material for this memory product. A resolved surface that is not in that actor's `surface_refs` is not minted.

Memory must verify the assertion, recompute the digest, check the HMAC with the authenticated agent's key, and require the actor-registry fragment to equal that `agent_id`. The identity assertion does not authorize namespaces.

### Local assertion digest

`.github` requires `assertion_digest` and does not define a global canonicalization algorithm. This repository and `l9-graphiti-memory` share one interop implementation rule. It is not global L9 semantic law:

1. copy the assertion object;
2. remove `assertion_digest`;
3. render UTF-8 JSON with `sort_keys=True`, `separators=(",", ":")`, and `ensure_ascii=False`;
4. SHA-256 that text and prefix `sha256:`.

`L9_MEMORY_IDENTITY_ASSERTION_HMAC` is HMAC-SHA256 of the ASCII digest under the same per-agent signing key used by the signed-agent door.

## Options Considered

1. Overload `L9_MEMORY_AGENT_ASSERTION` with the identity assertion. Rejected: that token is authentication, and its wire format stays `agent_id.exp.nonce.hexsig`.
2. Let memory re-resolve Cursor and Claude markers itself. Rejected: memory verifies the supplied assertion and does not inspect runtime markers or Cursor-Governance's registry.

## Supersedes

- Per-agent HTTPS bearer uniqueness as the agent identity door.
- ADR-0030 item 7's implication that **every** model-authored durable fact
  must take `phase_lock` → `write_governed` (high-stakes path remains; cold
  path is `write_agent`).
