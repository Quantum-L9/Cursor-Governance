# Analysis Notes — Multi-Agent L9 Environment (Phase 1)

## Repos cloned (shallow, HEAD)
- Cursor-Governance @ bda773b (2026-07-28) — governance SSOT
- l9-graphiti-memory @ 4aa86f2 (2026-07-28) — memory control plane v2.3.0

## Existing adapter model (CANONICAL_LAW §2)
- IDE-agnostic governance; adapters registered per surface:
  - Cursor: `.cursor-commands/` symlink (Active)
  - Claude Code: `environment/claude-code/` (Active)
  - Windsurf / VS Code: TBD (Planned)
  - CLI direct: Active
- Rule: no second activation path per agent; policy.json single authority; formatter ownership via agentdocs CLAUDE.md block.

## Memory identity model (the key contract to generalize)
- Two dimensions:
  - group_id = REPO namespace, SHARED across agents (group_registry.yaml; forbidden: main/default/""/test; workspace_group: igor-workspace)
  - Writing-agent identity = DISTINCT per agent: USER_ID / L9_MEMORY_AGENT_ID / L9_MEMORY_SOURCE + separate bearer token per agent principal
- Cursor identity: cursor_agent (config-docker-neo4j.yaml ${USER_ID:cursor_agent}); Claude Code: claude_code_agent / agent_id=claude-code, principal claude-code-memory-client
- l9-graphiti-memory server: bearer token -> MemoryPrincipal (principal_id, tenant, org, workspace, user_id, agent_id, roles tuple, read/write/promote namespaces globs, is_admin). auth_tokens.json maps token->principal. HTTP transport: `l9-memory-server --transport http` (also stdio/sse). http_auth_required default true.
- Roles field exists in principal ("memory-client") — roles are free-form strings; namespace grants are the enforcement (read/write/promote globs + is_admin).

## Env var contract (claude-code pack, to replicate per agent)
- GH_TOKEN (bot PAT), L9_GOVERNANCE_DIR, GRAPHITI_MCP_URL, GRAPHITI_MCP_TOKEN, USER_ID, L9_MEMORY_AGENT_ID, L9_MEMORY_SOURCE
- mcp.template.json: Graphiti MCP (`graphiti-memory`) with `Authorization: Bearer ${GRAPHITI_MCP_TOKEN}`, url `${GRAPHITI_MCP_URL}`
- Forbidden residue: `L9_MEMORY_HTTP_URL`, `L9_MEMORY_CLIENT_TOKEN`, `l9-shared-memory` (ADR-0006)
- SessionStart hook: fail-open bash, locates governance clone, emits additionalContext JSON. Authority order: CANONICAL_LAW.md -> AGENTS.md -> SKILL.md.

## Memory infra live state
- C1 VPS (Hetzner 46.62.243.82): graphiti-mcp container zepai/knowledge-graph-mcp:1.0.2, Neo4j; Cursor connects via SSH tunnel localhost:8100/mcp/
- Shared HTTP memory control plane: `https://memory.quantumaipartners.com` (Caddy → C1 `l9-memory-server`). Cloud adapters must default to that HTTPS URL, not loopback.

## Gaps for multi-agent replication (what user wants)
1. No central AGENT REGISTRY (peer of group_registry.yaml) declaring each agent: id, user_id, source, principal_id, role, surfaces, token env var name.
2. Adapters exist only for Cursor + Claude Code. Missing: Manus, generic/OpenAI-codex, Windsurf, Gemini CLI etc.
3. No role/division-of-work contract to prevent overlap/duplication (who writes what kind of episode; claim/lease convention).
4. auth_tokens.json server-side needs one principal per agent with roles + namespace grants — no generator script exists.
5. No validator that checks identity uniqueness across ALL agents (validate_claude_env.py only checks claude vs cursor).

## Duplication-prevention primitives already in l9-graphiti-memory
- Deterministic admission, idempotency, supersession, quarantine — server-side dedup exists. Overlap prevention at WORK level needs task-claim convention (episode kind) + role grants.

## User prefs to honor
- L9_META canonical header on all files (hard rule)
- Executable files preferred; ZIP with index for multi-file output; explicit confirmation before changing repo code; context window % after output.
