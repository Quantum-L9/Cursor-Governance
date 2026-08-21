---
name: Graphiti REST client cutover
overview: Make Graphiti the live primary memory by fixing the C1 server's OpenAI key (gating) and porting graphiti_memory_client.py from MCP JSON-RPC (/mcp/) to the deployed graph_service REST API, then verifying end-to-end and scrubbing the SSH key from the repo.
todos:
  - id: phase0
    content: Obtain valid sk-proj OpenAI key (gpt-4o-mini + text-embedding-3-small access); rotate leaked admin key
    status: pending
  - id: phase1
    content: "C1 (approval-gated): replace OPENAI_API_KEY in /opt/graphiti-cursor/graphiti.env, recreate graphiti-mcp, verify /search 200"
    status: pending
  - id: phase2-transport
    content: Add rest_call helper + replace mcp_call/call_tool in graphiti_memory_client.py
    status: pending
  - id: phase2-search
    content: Port search/_search_group to POST /search (SearchResults.facts)
    status: pending
  - id: phase2-write
    content: Port writes (cmd_write/_write_episode/bootstrap) to POST /messages; add EpisodeContract.to_rest_messages()
    status: pending
  - id: phase2-stats-health
    content: Port get_episodes to GET /episodes/{group}; rewrite health_check/_probe_tool_plane to REST
    status: pending
  - id: phase3-config
    content: Set GRAPHITI_API_BASE + token in ~/.cursor/graphiti.env (token in Keychain); scrub C1_SSH from .env.local
    status: pending
  - id: phase4-verify
    content: Verify health green, bootstrap seed, inject prefetch>0, search/stats, session-start hook healthy
    status: pending
  - id: phase5-docs
    content: Update DEPLOY.md + 03-graphiti-memory.mdc to REST transport; sync repo .cursor-commands client
    status: pending
isProject: false
---

# Get Graphiti Live: Server Key Fix + Client REST Cutover

## Why
The Mac client speaks MCP JSON-RPC at `/mcp/`, but C1 runs Graphiti's REST API (`uvicorn graph_service.main:app`) with routes `/search`, `/messages`, `/get-memory`, `/episodes/{group}`. There is no `/mcp/`, so `health` is degraded and prefetch returns 0. Separately, the server's OpenAI key is an `sk-admin-` key that cannot embed, causing `/search` 500. Both must be fixed; the client is fully cut over to REST (MCP support removed).

## Current state (already done)
- C1 SSH key stored in macOS Keychain (`graphiti-c1-ssh-key`); round-trip verified.
- `~/.cursor/graphiti.env` created with `GRAPHITI_SSH_KEYCHAIN_SERVICE` reference.
- Tunnel is up on `127.0.0.1:8100`; liveness `/healthcheck` green; `GET /episodes/igor-workspace` returns `200 []`.
- Tunnel/bootstrap wiring (`ensure_graphiti_tunnel.sh`, `session_start_bootstrap.sh`) reads the Keychain entry.

## Phase 0 - Prereq (you)
- Create a valid `sk-proj-...` OpenAI key with access to `gpt-4o-mini` + `text-embedding-3-small`; verify with `curl https://api.openai.com/v1/models`.
- Rotate the leaked `sk-admin-` key.

## Phase 1 - Server OpenAI key fix (C1, REQUIRES YOUR EXPLICIT APPROVAL per rule 93)
- Edit `OPENAI_API_KEY` in C1 `/opt/graphiti-cursor/graphiti.env` (protected Docker `.env`).
- Recreate only the app container: `docker compose --env-file graphiti.env up -d --force-recreate graphiti-mcp`.
- Verify: `POST /search {"query":"x","group_ids":["igor-workspace"],"max_facts":3}` returns `200` (not 500).
- No image swap, no port/compose changes.

## Phase 2 - Client REST cutover (no infra; canonical file in GlobalCommands)
Target: `/Users/macm2/Dropbox/cursor governance/GlobalCommands/ops/graphiti/graphiti_memory_client.py`

- Add `rest_call(method, path, body=None)` using `GRAPHITI_API_BASE` (derive from `GRAPHITI_MCP_URL` by stripping `/mcp/`) with `Authorization: Bearer $GRAPHITI_MCP_TOKEN`. Keep `CircuitBreaker`/`RateLimiter`.
- Replace `mcp_call` / `call_tool` (lines ~55-93) with REST equivalents.
- `_search_group` / search: `POST /search` -> parse `SearchResults.facts` (each `FactResult{uuid,name,fact,...}`). Schema: `{query, group_ids:[gid], max_facts:int}`.
- Writes (`cmd_write`, `_write_episode`, `bootstrap`, `cmd_inject` were `add_episode`): `POST /messages` with `{group_id, messages:[{content, role_type:"system", role:"cursor", name, timestamp, source_description}]}` (202 accepted). Map `EpisodeContract` body -> single `Message.content` in [episode_contract.py](/Users/macm2/Dropbox/cursor governance/GlobalCommands/ops/graphiti/episode_contract.py) via a new `to_rest_messages()`.
- `cmd_stats` (`get_episodes`): `GET /episodes/{group_id}?last_n=N` (required param).
- `health_check` + `_probe_tool_plane`: liveness `GET /healthcheck` plus functional probe `GET /episodes/{gid}?last_n=1`; `healthy = liveness_ok and probe_ok`. Remove `tools/list`.
- `_find_supersedes_uuid` / `_is_already_seeded`: keep, backed by `/search`.
- Keep group resolution and `resolve_read_groups` unchanged.

## Phase 3 - Config + secret wiring
- Update [~/.cursor/graphiti.env](/Users/macm2/.cursor/graphiti.env): set `GRAPHITI_API_BASE=http://127.0.0.1:8100` and `GRAPHITI_MCP_TOKEN` (server token). Prefer storing the token in Keychain (`graphiti-mcp-token`) and referencing it, mirroring the SSH-key pattern.
- Scrub the raw `C1_SSH` private key from [.env.local](/Users/macm2/Library/CloudStorage/Dropbox/Repo_Dropbox_IB/Enrichment.Inference.Engine/.env.local) (Keychain is now primary; other secrets in that file stay).

## Phase 4 - End-to-end verification
- `graphiti_memory_client.py health` -> `healthy: true`.
- `bootstrap --dry-run` then real `bootstrap` seeds the repo manifest (writes via `/messages`).
- `inject "session start"` -> `prefetch_chars > 0` after seed.
- `search "..."` returns facts; `stats` lists episodes.
- Re-run session-start hook -> reports `graphiti: healthy` (not degraded).

## Phase 5 - Doc coherence (prevent re-drift)
- Update [DEPLOY.md](/Users/macm2/Dropbox/cursor governance/GlobalCommands/ops/graphiti/DEPLOY.md) and [03-graphiti-memory.mdc](/Users/macm2/Dropbox/cursor governance/GlobalCommands/rules/03-graphiti-memory.mdc) to state REST transport (`/search`,`/messages`,...) and `GRAPHITI_API_BASE`, removing `/mcp/` assumptions.
- Note: repo `.cursor-commands/ops/graphiti/` must reflect the edited client (re-run `setup_workspace_symlinks.sh` if it is a copy rather than a symlink).

## Risk / sequencing notes
- Phase 1 is gating for search/ingest (embeddings); Phase 2 read path (`/episodes`) works without it.
- Phase 1 is the only step touching protected C1 infra and will not proceed without your explicit "APPROVED".
- All Phase 2-5 edits are in GlobalCommands / home dotfiles - no repo or C1 risk.
