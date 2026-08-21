---
name: Repair Graphiti MCP Memory
overview: Replace the wrong Graphiti Docker image on C1 (46.62.243.82) with the official MCP-capable image, reconcile tool-name mismatches in graphiti_memory_client.py, verify end-to-end memory read/write for the newly-registered igorbot group, and document any credential changes in a gitignored .env file using this repo's existing AWS Secrets Manager annotation convention.
todos:
  - id: phase0-baseline
    content: "Phase 0: SSH read-only baseline capture of current C1 compose file, env, image digest, container status"
    status: pending
  - id: phase1-artifacts
    content: "Phase 1: Author new docker-compose.yml graphiti-mcp service block + config.yaml locally in governance repo"
    status: pending
  - id: phase2-credential-check
    content: "Phase 2: Determine if new image supports token auth; decide on GRAPHITI_MCP_TOKEN change and document in .env if so"
    status: pending
  - id: phase3-deploy
    content: "Phase 3: Deploy new image to C1 with per-step approval (copy files, pull, recreate graphiti-mcp container only)"
    status: pending
  - id: phase4-verify
    content: "Phase 4: Run health/resolve/bootstrap/search verification; introspect live tools/list and patch graphiti_memory_client.py tool names if they differ from add_memory/search_memory_facts"
    status: pending
  - id: phase5-rollback-ready
    content: "Phase 5: Confirm rollback path is intact (old compose backup, cached old image, untouched Neo4j volume)"
    status: pending
  - id: phase6-report
    content: "Phase 6: Write GMP evidence report and update .env/.env.template with any credential changes"
    status: pending
isProject: false
---


# Repair Graphiti MCP Memory (C1 — 46.62.243.82)

## Confirmed root cause (from prior diagnosis)

`/opt/graphiti-cursor/docker-compose.yml` on C1 runs `zepai/graphiti:latest` — this is Graphiti's plain REST API (`graphiti-core`), which has never implemented an MCP transport. It only exposes `/healthcheck, /search, /messages, /entity-node, /entity-edge/{uuid}, /episode/{uuid}, /episodes/{group_id}, /get-memory, /group/{group_id}, /clear`. There is no `/mcp` route. `graphiti_memory_client.py` (used by all Cursor sessions across all repos) POSTs JSON-RPC to `/mcp/` expecting `tools/list` / `tools/call` — every one of those calls has 404'd for the full 6 weeks the container has been up. Only `/healthcheck` ever succeeded, which is why the outage went unnoticed.

The correct image is the official `zepai/knowledge-graph-mcp` (from `getzep/graphiti`), which serves MCP HTTP transport at `/mcp/` — exactly the endpoint already configured in `~/.cursor/graphiti.env` (`GRAPHITI_MCP_URL=http://127.0.0.1:8100/mcp/`). No client-side URL change needed.

## Second defect found during planning: tool-name mismatch

Even after the image is fixed, `graphiti_memory_client.py` will still fail some calls because it uses tool names that don't match the official server's tool schema:

| Client calls (wrong) | Call sites | Official tool name | Payload shape |
|---|---|---|---|
| `add_episode` | [graphiti_memory_client.py:251](/Users/macm2/.cursor-governance/ops/graphiti/graphiti_memory_client.py), :255, :349 | `add_memory` | Compatible — `EpisodeContract.to_mcp_payload()` in [episode_contract.py:98-106](/Users/macm2/.cursor-governance/ops/graphiti/episode_contract.py) already emits `name, episode_body, source, source_description, reference_time, group_id`, which matches `add_memory`'s standard episode schema |
| `search_facts` | [graphiti_memory_client.py:110](/Users/macm2/.cursor-governance/ops/graphiti/graphiti_memory_client.py), :283 | `search_memory_facts` | Arg key names (`max_facts` etc.) must be re-verified against the live `tools/list` schema — do not assume |
| `search_nodes` | :110, :470 | `search_nodes` | Already correct, no change |
| `get_episodes` | :467 | `get_episodes` | Already correct, no change |

This will be verified live against the deployed server (not guessed) before patching.

## Scope confirmation: only the Cursor-governance deployment is affected

`igorbot/graphiti/docker-compose.yml` in this repo has the identical `zepai/graphiti:latest` image bug (same port 8100, same pattern), but [memory_tool.py:35,41-43](/Users/macm2/igorbot-07-19-2026/igorbot/graphiti/memory_tool.py) talks to Neo4j directly via `graphiti_core`/bolt, never through that container's HTTP API — so IgorBot's own memory is unaffected. This plan is scoped to the C1 Cursor-memory box only. The identical latent bug in `igorbot/graphiti/docker-compose.yml` is noted but out of scope (informational only, no action taken here).

## Phase 0 — Baseline capture (read-only, no VPS changes)

1. SSH to C1 (read-only): copy current `/opt/graphiti-cursor/docker-compose.yml`, `graphiti.env` (values redacted in the copy kept locally), and record the exact running image digest (`docker inspect graphiti-mcp-cursor --format '{{.Image}}'`) and `docker compose ps` output.
2. Save these as a timestamped backup under a new local-only path (not committed) so the current (broken) state can be restored in under a minute if the new image fails.
3. Record current Neo4j data volume path (`/opt/graphiti-cursor/neo4j-data`) — this volume is never touched by this plan.

## Phase 1 — Author new artifacts locally (governance repo, no VPS changes yet)

Files to change in `$HOME/.cursor-governance/ops/graphiti/`:

1. **[docker-compose.yml](/Users/macm2/.cursor-governance/ops/graphiti/docker-compose.yml)** — `graphiti-mcp` service only (neo4j service block untouched):
   - `image: zepai/graphiti:latest` -> `image: zepai/knowledge-graph-mcp:standalone` (exact tag confirmed against Docker Hub before use — verify tag exists at execution time, do not assume `:standalone` is current)
   - Add volume mount for the new `config.yaml` (see below), read-only
   - Update environment block to the new image's variable names: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`, `OPENAI_API_KEY`, `GRAPHITI_TELEMETRY_ENABLED`, `SEMAPHORE_LIMIT` (new — concurrency control, default `10`), `CONFIG_PATH=/app/mcp/config/config.yaml`
   - Keep `ports: "127.0.0.1:8100:8000"` unchanged — no port/network change
   - Remove the now-obsolete commented custom-ontology block (or re-verify against the new image's `--help` output if still wanted)

2. **New file `config.yaml`** (or `config-docker-neo4j.yaml`) in `ops/graphiti/`:
   ```yaml
   server:
     transport: "http"
   llm:
     provider: "openai"
     model: "${MODEL_NAME:-gpt-4o-mini}"
   embedder:
     provider: "openai"
     model: "${EMBEDDER_NAME:-text-embedding-3-small}"
   database:
     provider: "neo4j"
     providers:
       neo4j:
         uri: "${NEO4J_URI}"
         username: "${NEO4J_USER}"
         password: "${NEO4J_PASSWORD}"
         database: "neo4j"
   ```
   Exact keys to be cross-checked against the installed image's `--help`/schema before mounting (the README excerpt gives the shape but not an exhaustive schema).

3. **graphiti.env** on C1 — reuse existing `NEO4J_PASSWORD` and `OPENAI_API_KEY` values as-is (no rotation needed; same Neo4j instance, same data, same OpenAI account). Add `SEMAPHORE_LIMIT=10` as a new non-secret tuning var.

## Phase 2 — Credential decision point (conditional — only if applicable)

- Check whether `zepai/knowledge-graph-mcp` supports a built-in bearer-token/API-key auth mechanism (not confirmed in the README excerpt reviewed).
  - If yes: generate a new random `GRAPHITI_MCP_TOKEN` and enable it — this is the one credential that may actually change.
  - If no: leave `GRAPHITI_MCP_TOKEN` unset/deprecated and continue relying on the existing security boundary (loopback bind + SSH-tunnel-only access, no direct internet exposure) — no credential change.
- **Any credential that does change** will be documented in a new gitignored `.env` entry at the repo root, following the existing convention in [.env.template](/Users/macm2/igorbot-07-19-2026/igorbot/.env.template) (e.g. `# aws: openclaw-igorbot/<name> field: token`) plus the actual value in local `.env`, so it can later be pushed into AWS Secrets Manager via `credentials/aws-secrets-setup.sh` conventions. Since `NEO4J_PASSWORD` and `OPENAI_API_KEY` are not changing, no update to those existing `.env.template` entries is expected — only a new token entry would be added, conditionally.

## Phase 3 — Deploy to VPS (each step requires your explicit approval before execution, per VPS/Docker protection rules)

1. Copy updated `docker-compose.yml` + `config.yaml` to `/opt/graphiti-cursor/` on C1 (scp, not manual VPS editing)
2. `docker compose --env-file graphiti.env pull graphiti-mcp`
3. `docker compose --env-file graphiti.env up -d --force-recreate graphiti-mcp` (Neo4j service untouched, not recreated)
4. Confirm container health: `docker compose ps`, `docker compose logs --tail=40 graphiti-mcp`

## Phase 4 — Verification (from Mac, through existing SSH tunnel)

1. `python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py health` — expect `"healthy": true`, `tools.reachable: true`
2. Introspect live schema: raw `tools/list` call, diff tool names/arg keys against Phase-2 assumptions in the compatibility table above
3. Patch `graphiti_memory_client.py` call sites only if the live schema differs from assumptions (rename `add_episode`->`add_memory`, `search_facts`->`search_memory_facts`, adjust arg keys if needed)
4. `python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py resolve` — confirm `group_id: "igorbot"`, `readonly: false` (registry entry already added)
5. `bootstrap --dry-run` for `igorbot` group, then a real write + `search` round-trip to prove read/write both work
6. `bash .cursor-commands/ops/graphiti/test_gate_e2e_full.sh` — full existing self-test suite
7. Re-run `check_governance_wiring.sh` / `validate_governance_symlinks.sh` to confirm nothing else regressed

## Phase 5 — Rollback plan

- Old `zepai/graphiti:latest` container config is fully preserved in the Phase 0 backup; rollback is `docker compose up -d --force-recreate graphiti-mcp` against the restored old compose file (image already cached locally on C1, no re-pull needed)
- Neo4j container and its data volume are never recreated or modified in this plan, so rollback carries zero data-loss risk
- If the new image's config.yaml schema doesn't match assumptions, this is caught in Phase 4 step 1 (health check) before any client code is patched — the deploy step is fully reversible at that point

## Phase 6 — Documentation

- Per repo convention (rules `80-gmp-execution.mdc`, `81-gmp-audit.mdc`, `83-gmp-contracts.mdc`), execution of this plan will be tracked as a GMP run with a signed evidence report in `/reports/GMP-Report-<next-id>-Graphiti-MCP-Repair.md` covering exactly what changed, all verification command output, and the before/after `health` JSON.
- Any new/changed secret gets a corresponding annotated entry added to `.env.template` (comment only, no value) and the real value written to local gitignored `.env`, ready for `credentials/aws-secrets-setup.sh`-style provisioning into AWS Secrets Manager.

## What requires your approval at execution time (not now)

- Exact Docker image tag confirmation (verify `zepai/knowledge-graph-mcp:standalone` or equivalent tag actually exists before pulling)
- Each VPS command in Phase 3 (copy files, pull, recreate container) — per `01-vps-rules.mdc` / `93-c1-server-protection.mdc`, shown and approved one at a time
- The Phase 2 credential decision (generate new `GRAPHITI_MCP_TOKEN` or not) once the new image's auth support is confirmed
