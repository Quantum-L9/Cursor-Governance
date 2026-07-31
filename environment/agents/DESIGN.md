<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/DESIGN.md
layer: design
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-07-28
/L9_META -->

# L9 Multi-Agent Environment — Design

One work environment, N agents, one shared memory graph, zero identity collisions, zero duplicated work.

## 1. Problem

The L9 governance environment activates today on exactly two surfaces (Cursor via `.cursor-commands`, Claude Code via `environment/claude-code/`). Each surface hand-declares its memory identity in its own env file. There is no single place that answers: **which agents exist, what is each agent's unique ID, what role does it hold, which token maps to it on the memory server, and what work is it allowed to claim?** Adding a third agent (Manus, Codex, Gemini, Windsurf) today means copying a directory and hand-editing identities — the exact drift pattern CANONICAL_LAW forbids.

## 2. Design axis

Everything derives from **one registry file**: `environment/agents/agent_registry.yaml`. It is the peer of `ops/graphiti/group_registry.yaml` and completes the identity matrix:

| Dimension | Registry | Shared or distinct |
|---|---|---|
| `group_id` (WHAT repo the memory is about) | `ops/graphiti/group_registry.yaml` | **Shared** across all agents |
| Agent identity (WHO wrote the memory) | `environment/agents/agent_registry.yaml` | **Distinct** per agent |
| Role (WHAT KIND of work the agent claims) | same registry, `role` field | Assigned per agent |

Renderers turn the registry into per-surface artifacts (env blocks, MCP configs, server principals). No adapter ever declares an identity literal; it references the registry. One authority, N renderings — the same pattern `policy.json` already uses for formatter ownership.

## 3. Agent identity contract (binding)

Every agent entry declares, and every derived artifact must agree on:

| Field | Rule | Example (Manus) |
|---|---|---|
| `agent_id` | unique, kebab-case, immutable | `manus` |
| `user_id` | unique, snake_case, `${agent_id}_agent` | `manus_agent` |
| `source` | equals `agent_id` | `manus` |
| `principal_id` | `${agent_id}-memory-client` | `manus-memory-client` |
| `token_env` | `L9_MEMORY_TOKEN__<AGENT_ID>` upper snake | `L9_MEMORY_TOKEN__MANUS` |
| `role` | one of the role catalog below | `researcher-builder` |
| `surfaces` | where this agent runs | `[manus-cloud]` |

Uniqueness is enforced three ways: (a) the validator fails on any duplicate `agent_id`/`user_id`/`principal_id`; (b) the principal generator refuses to emit two principals with the same claims; (c) the memory server itself authenticates each bearer token to exactly one principal (constant-time compare, `authz/authenticator.py`).

## 4. Role catalog and overlap prevention

Roles are enforced at two levels — **namespace grants** (hard, server-side) and **work-claim protocol** (soft, convention encoded in the adapter + session hook):

| Role | write_namespaces | promote | Typical agent |
|---|---|---|---|
| `orchestrator` | `*` | yes | the human-directed lead session (Cursor) |
| `implementer` | repo groups it is assigned | no | Claude Code |
| `researcher-builder` | repo groups it is assigned | no | Manus |
| `reviewer` | `<group>.reviews` only | no | CI/PR bots |
| `observer` | none (read-only) | no | dashboards, analytics |

**Work-claim protocol (duplication guard):** before starting a unit of work, an agent writes a `task-claim` episode (`kind=procedure`, deterministic `claim_key = sha256(group_id + normalized task title)`) and searches for open claims first. The memory server's idempotency layer makes duplicate claims a no-op with a `duplicate` outcome — the second agent sees the claim is taken and moves on. Claims carry `agent_id`, `role`, `status` (`claimed → in_progress → done | released`), and a TTL; stale claims are reclaimable. This uses only existing server primitives (deterministic admission, idempotency, supersession) — no server change required.

## 5. Per-surface adapters (rendered, not authored)

| Surface | Adapter artifact | Identity carrier |
|---|---|---|
| Cursor | existing `.cursor-commands` + `ops/graphiti` (unchanged) | `USER_ID=cursor_agent` machine env |
| Claude Code | existing `environment/claude-code/` (env example now rendered from registry) | account environment |
| Manus | `environment/agents/adapters/manus/` — Manus skill + connector spec | Manus session env / custom MCP connector |
| Codex / OpenAI | `environment/agents/adapters/codex/` — AGENTS.md block + setup script | account env |
| Gemini CLI | `environment/agents/adapters/gemini/` — settings + setup script | `~/.gemini/settings.json` env refs |
| Generic CLI | `environment/agents/adapters/generic/` — env block + `.mcp.json` | shell profile |

Every adapter does the same three things, per the claude-code precedent: discover skills (governance clone), boot context (session-start hook or equivalent), reach shared memory (HTTP MCP with the agent's own bearer token and identity env block).

## 6. Server-side wiring

`tools/render_principals.py` reads the registry plus a local token file (`agent_tokens.local.json`, never committed) and emits the l9-graphiti-memory `auth_tokens.json` — one principal per agent with role-appropriate namespace grants. The memory server must be reachable by cloud agents: bind to a routable host (or keep the C1 pattern — server on VPS, each surface reaches it directly over HTTPS with auth required). Loopback-only deployments cannot serve Manus/Claude-Web; this is a stated constraint, not a fabricated capability.

**Two memory planes, one workspace-group contract.** This pack's renderer targets the *planned* `l9-graphiti-memory` control-plane server (its `MemoryPrincipal`/`auth_tokens.json` model). The memory stack *deployed today* is the `zepai/knowledge-graph-mcp` MCP server driven by `ops/graphiti/graphiti_memory_client.py` — a different code path with its own hardened gate: an explicit `group_id` override that contradicts the resolved repo match fails closed, path hints match whole path segments only, and direct `write` to the shared workspace group (`igor-workspace`, per `ops/graphiti/group_registry.yaml`) is rejected unconditionally — only bootstrap's integration-edge mirror writes there. The `workspace_group` in `agent_registry.yaml` MUST stay equal to the one in `group_registry.yaml`, and any server-side grant of that namespace (researcher-builder role) is a grant on the *control-plane* server, not a license to bypass the CLI gate on the deployed stack.

## 7. Validator

`validate_agents.py` (peer of `validate_claude_env.py`) checks: registry parses; all identity fields unique across N agents; naming rules hold; no secrets committed; every adapter directory references only registry identities; role values are in the catalog; rendered examples agree with the registry. Exit non-zero on any violation; wired as `make agents-env`.

## 8. What this does NOT do

No second activation path for Cursor or Claude Code (their adapters stay authoritative; the registry only becomes the source their identity examples are rendered from). No fork of `group_id` per agent. No duplicate of `policy.json`. No plaintext token ever enters the repo.
