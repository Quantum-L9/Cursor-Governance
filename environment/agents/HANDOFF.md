<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/HANDOFF.md
layer: handoff
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-07-28
/L9_META -->

# HANDOFF — L9 Multi-Agent Environment Pack (Session 2026-07-28)

Portable load-pack of this session's operational state. Treat as **session
context below current user instructions**, per `adapters/claude-code.md`
invocation order (CANONICAL_LAW.md → AGENTS.md → SKILL.md → this handoff).

## 1. Mission (user's words, normalized)

> Replicate the same work environment in all LLMs and have all write to the
> same memory, so work is organized without overlap or duplication, with each
> agent using their unique ID with the correct role set.

Interpreted as: extend the L9 governance adapter model (CANONICAL_LAW §2) from
2 surfaces (Cursor, Claude Code) to N agents (adding Manus, Codex, Gemini),
all writing to one shared l9-graphiti-memory plane, with a single registry
governing identity + role, and a claim protocol preventing duplicated work.

## 2. Ground truth established (Phase 1 — COMPLETE)

Verified live on 2026-07-28 (EDT), shallow clones at these SHAs:

| Repo | SHA | Fact base |
|---|---|---|
| Quantum-L9/Cursor-Governance | `bda773b` | Adapter model in CANONICAL_LAW §2 (Cursor + Claude Code active; Windsurf/VS Code planned). Memory layer §8: Graphiti/Neo4j on C1 VPS (Hetzner 46.62.243.82), container `zepai/knowledge-graph-mcp:1.0.2-graphiti-0.28.2-standalone`, Cursor reaches it via SSH tunnel `localhost:8100/mcp/`. Group registry: `ops/graphiti/group_registry.yaml` (schema 2, workspace_group `igor-workspace`, forbidden groups `main/default/""/test`, repos: ib-odoo-19, cursor-governance, cognitive-engine-graphs, l9-node-template, igorbot). Cursor identity `${USER_ID:cursor_agent}` in `ops/graphiti/config-docker-neo4j.yaml`. Claude Code env pack at `environment/agents/adapters/claude-code/` (same content as the user's uploaded `l9-claude-code-env-pack.zip`; the repo wins on disagreement). |
| Quantum-L9/l9-graphiti-memory | `4aa86f2` | v2.3.0 memory control plane. `MemoryPrincipal` contract (`contracts/identity.py`): principal_id, tenant, org, workspace, user_id, agent_id, roles tuple, read/write/promote namespace globs, is_admin. Bearer-token auth (`authz/authenticator.py`, constant-time), namespace policy (`authz/policy.py`, fnmatch globs). `auth_tokens.json` maps token → principal. Server: `l9-memory-server --transport stdio|http|sse`; `http_auth_required` defaults true; refuses unauthenticated non-loopback bind. Guarantees used by our design: deterministic admission, idempotency (duplicate outcome), supersession, bi-temporal lineage. |

GitHub access: Manus's `gh` is authenticated as `cryptoxdog` with **admin/push
on both repos** — no adapter needed for repo access (answered in this session).

## 3. Decisions made (Phase 2 — COMPLETE, user informed, not yet user-ratified)

1. **One registry file** `environment/agents/agent_registry.yaml` is the SSOT
   for WHO (identity + role). Peer of `group_registry.yaml` (WHAT repo).
   `group_id` stays shared across agents; identity stays distinct per agent.
2. **Identity naming law:** `agent_id` kebab-case unique; `user_id` =
   `<agent_id>_agent`; `source` = agent_id; `principal_id` =
   `<agent_id>-memory-client`; `token_env` = `L9_MEMORY_TOKEN__<AGENT>`;
   `legacy_token_env` honors already-deployed names (`GRAPHITI_MCP_TOKEN` for
   Cursor, `L9_MEMORY_CLIENT_TOKEN` for Claude Code).
3. **Role catalog:** orchestrator (Cursor), implementer (Claude Code, Codex),
   researcher-builder (Manus), reviewer (Gemini), observer. Hard enforcement =
   server-side namespace grants rendered per role; soft enforcement =
   work-claim protocol.
4. **Work-claim protocol** (anti-duplication): deterministic
   `claim_key = sha256(group_id + "\n" + normalized_title)` written as a
   `procedure` episode; the server's idempotency `duplicate` outcome is the
   race-safe loser signal; status transitions via supersession; TTL 4h/24h;
   orchestrator arbitrates. Uses only existing server primitives.
5. **Topology:** the only topology satisfying "all LLMs, same memory" is a
   routable HTTPS memory endpoint (Option A: l9-memory-server on C1 behind
   TLS). Loopback/tunnel patterns stay valid for single-machine but cannot be
   the shared plane. Auth stays required.
6. **No second activation path** for existing adapters; registry becomes the
   render source for their identity examples. No `policy.json` duplicate. No
   tokens in the repo, ever.

## 4. Artifacts built so far (Phase 3 — IN PROGRESS)

| File (in this pack) | Status | Purpose |
|---|---|---|
| `DESIGN.md` | done | Full architecture: problem, identity contract, role catalog, adapters table, server wiring, validator spec |
| `agent_registry.yaml` | done | The registry itself — 5 agents (cursor, claude-code, manus active; codex, gemini planned), role catalog with grants, memory endpoint contract |
| `docs/WORK_CLAIM_PROTOCOL.md` | done | Claim episode schema, status machine, mandatory pre-work search rule, role-based work routing, attribution invariants |
| `docs/MEMORY_TOPOLOGY.md` | done | Options A/B/C comparison, C1 wiring commands, non-negotiables, stated unknowns |
| `tools/render_principals.py` | done, **not yet executed/tested** | Registry + gitignored token map → `auth_tokens.json` (one principal per agent; fails on duplicate identity/token, unknown role, empty grants) |
| `analysis_notes.md` | done | Raw Phase-1 findings (repo facts, gaps, user prefs) |

## 5. Remaining work

### Done (2026-07-31) — thicken agents to Claude Code contract

1. **Adapters deploy-ready** — manus / codex / gemini / generic now carry
   env (production URL), MCP carrier, bootstrap, README, `setup.md`;
   `ADAPTER_CONTRACT.md` + `docs/DEPLOY.md` + `docs/network-allowlist.md`.
   Codex + Gemini flipped to `status: active`. Claude Code **unchanged** at
   `environment/agents/adapters/claude-code/`.
2. **`validate_agents.py` A3** — adapter contract enforced; production_url
   must match env examples. `make agents-env` + self-tests green.
3. **Memory Option A LIVE** — `https://memory.quantumaipartners.com` documented
   in registry `memory.production_url` and MEMORY_TOPOLOGY.

### Still operator / human

4. **Sync expanded `auth_tokens.json` to C1** when codex/gemini tokens are
   issued locally — requires explicit VPS approval (`docs/DEPLOY.md` §3).
5. **Paste surface configs** — Manus connector, Codex/Gemini env+MCP,
   AGENTS.md / GEMINI.md blocks in consumer repos.
6. **Optional:** CANONICAL_LAW §2 table rows for Manus/Codex/Gemini;
   commit/PR when user asks.

## 6. Constraints and user preferences in force (locked)

L9_META canonical header on every generated file (hard rule). Explicit user
confirmation before modifying repo code. Multi-file outputs delivered as one
ZIP with an index file. Decisive, deterministic responses; unknowns labelled
"Unknown", never fabricated. Executable deliverables preferred. Graph-database
(Neo4j/Graphiti) architecture preferred for agent memory. No tokens/secrets in
any repo file; account-environment or gitignored local files only.

## 7. Resume instructions for the next session (any agent)

Read this file, then `DESIGN.md`, then `agent_registry.yaml`. Confirm the two
repo SHAs are still HEAD (`git ls-remote`); if moved, re-verify §2 facts before
building. Continue at §5 item 1 (adapters), honoring §6. The authority order
is CANONICAL_LAW.md → AGENTS.md → this pack; where this pack disagrees with
the repos at HEAD, the repos win and this pack must be updated, not the
reverse.

## 8. Session verification log

`gh api` confirmed admin on both repos (2026-07-28). Shallow clones taken same
day. `render_principals.py` compiles conceptually against
`config/auth_tokens.json.example` fields — **runtime test still pending**
(§5.4). No writes have been made to any GitHub repo in this session.
