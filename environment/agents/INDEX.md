<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/INDEX.md
layer: index
owner: governance-control-plane
status: active
version: 2.1.0
updated: 2026-07-31
/L9_META -->

# INDEX — l9-multi-agent-pack (deploy-ready, 2026-07-31)

**2026-07-31:** Adapters thickened to Claude Code contract; live memory
`https://memory.quantumaipartners.com`; codex+gemini `active`. See
`docs/DEPLOY.md`, `adapters/ADAPTER_CONTRACT.md`. Claude Code remains at
`environment/claude-code/`.

Read order: `README.md` → `HANDOFF.md` → `DESIGN.md` → `agent_registry.yaml`.
Intended repo destination: `Quantum-L9/Cursor-Governance` at `environment/agents/`.

## Core (delivered in handoff v1, unchanged)

| # | File | Description |
|---|---|---|
| 1 | `HANDOFF.md` | Master handoff: mission, verified repo ground truth (pinned SHAs), decisions, remaining work, resume instructions. |
| 2 | `DESIGN.md` | Architecture: registry-driven identity, binding naming law, role catalog, adapter map, server wiring, validator spec. |
| 3 | `agent_registry.yaml` | SSOT for agent identity + role: 5 agents (cursor, claude-code, manus active; codex, gemini planned), role grants, memory endpoint contract. No secrets. |
| 4 | `docs/WORK_CLAIM_PROTOCOL.md` | Anti-duplication protocol: deterministic claim keys, race-safe duplicate outcome, status machine, role-based work routing. |
| 5 | `docs/MEMORY_TOPOLOGY.md` | One shared memory server for all surfaces: topology options, C1 routable-HTTPS wiring, security non-negotiables. |
| 6 | `tools/render_principals.py` | Registry + gitignored token map → memory server `auth_tokens.json`. **Now runtime-tested.** |
| 7 | `analysis_notes.md` | Raw Phase-1 repo analysis findings. |

## New in this build (the "intending to push" work)

| # | File | Description |
|---|---|---|
| 8 | `README.md` | Pack landing page: layout, operator quick start, add-an-agent flow, PR integration notes (CANONICAL_LAW §2 rows, `make agents-env`). |
| 9 | `adapters/manus/README.md` | Manus adapter: carrier mapping (skills / project instructions / custom MCP connector), 4-step setup, role limits. |
| 10 | `adapters/manus/environment.env.example` | Manus identity env block rendered from the registry (`manus_agent` / `manus` / researcher-builder). |
| 11 | `adapters/manus/mcp-connector.json` | Manus Custom MCP connector template (HTTP `/mcp`, bearer auth, identity headers). |
| 12 | `adapters/manus/session_bootstrap.md` | Session bootstrap for Manus project instructions/skill: authority order, 7 binding memory rules incl. claim protocol. |
| 13 | `adapters/codex/README.md` | Codex adapter (planned): `~/.codex/config.toml` MCP wiring, cloud env settings, setup, implementer role limits. |
| 14 | `adapters/codex/environment.env.example` | Codex identity env block (`codex_agent` / implementer). |
| 15 | `adapters/codex/agents-block.md` | Drop-in AGENTS.md block giving Codex its identity + claim rules in every governed repo. |
| 16 | `adapters/gemini/README.md` | Gemini adapter (planned): `~/.gemini/settings.json` wiring, reviewer role (server-enforced `<group>.reviews` writes only). |
| 17 | `adapters/gemini/environment.env.example` | Gemini identity env block (`gemini_agent` / reviewer). |
| 18 | `adapters/gemini/settings.template.json` | Gemini CLI `mcpServers` entry (httpUrl + bearer header via env expansion). |
| 19 | `adapters/gemini/gemini-block.md` | Drop-in GEMINI.md block: reviewer identity, review-namespace limits, claim rules. |
| 20 | `adapters/generic/README.md` | Onboarding recipe for ANY future surface: 1 registry entry → 1 token → 1 env block → 1 bootstrap. |
| 21 | `adapters/generic/mcp.template.json` | Generic MCP client template (HTTP, bearer, identity headers, `${AGENT_ID}` placeholders). |
| 22 | `adapters/generic/bootstrap.template.md` | Generic session bootstrap with `{{AGENT_ID}}` / `{{ROLE}}` placeholders. |
| 23 | `tools/validate_agents.py` | N-agent validator: registry parse, naming law, uniqueness, role catalog, adapter-registry consistency, committed-secret scan. Exit 0/1/2. |
| 24 | `tools/test_validators.py` | Self-test suite: 2 positive + 5 negative cases — **7/7 passing** (see VALIDATION.md). |
| 25 | `VALIDATION.md` | Evidence log: validator PASS output, rendered principal grants for all 5 agents, test-suite results. |
| 26 | `INDEX.md` | This file. |
