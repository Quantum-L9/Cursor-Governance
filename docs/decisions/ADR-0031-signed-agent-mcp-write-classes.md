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

## Supersedes

- Per-agent HTTPS bearer uniqueness as the agent identity door.
- ADR-0030 item 7's implication that **every** model-authored durable fact
  must take `phase_lock` → `write_governed` (high-stakes path remains; cold
  path is `write_agent`).
