# Graphiti VPS Deploy — C1 post-L9 (locked)

**Host:** `46.62.243.82` (Hetzner C1)  
**Install path:** `/opt/graphiti-cursor`  
**Prerequisite:** L9 stack decommissioned (`/opt/l9` archived; no `l9-*` containers)  
**Mac access:** SSH tunnel (Tailscale **out of scope**)

## Ports (loopback on VPS)

| Service | Bind | Notes |
|---------|------|-------|
| Graphiti MCP | `127.0.0.1:8100` | Maps container 8000 |
| Neo4j bolt | `127.0.0.1:7687` | Default `neo4j` DB (dedicated instance) |
| Neo4j browser | `127.0.0.1:7474` | Optional admin |

## Deploy on C1

```bash
ssh -i ~/.ssh/Hetzner-C1-nopass root@46.62.243.82
mkdir -p /opt/graphiti-cursor
cd /opt/graphiti-cursor
# Copy docker-compose.yml AND config-docker-neo4j.yaml from GlobalCommands/ops/graphiti/
# — the config file is required (mounted read-only, CONFIG_PATH env points at it).
cp graphiti.env.example graphiti.env   # fill OPENAI_API_KEY, tokens — NEVER commit
source graphiti.env && docker compose up -d
curl -sf http://127.0.0.1:8100/health
```

**OPENAI_API_KEY** must be a live `sk-...` / `sk-proj-...` **secret key with inference
permissions** — not an `sk-admin-...` org-management key (401s on every call).
Source of truth: AWS Secrets Manager `l9/OPENAI_API_KEY` (see `graphiti.env.example`).

## Mac client

```bash
# Terminal 1 — tunnel
ssh -N -L 8100:127.0.0.1:8100 -i ~/.ssh/Hetzner-C1-nopass root@46.62.243.82

# Terminal 2 — env
cp GlobalCommands/ops/graphiti/graphiti.env.example ~/.cursor/graphiti.env
# GRAPHITI_MCP_URL=http://127.0.0.1:8100/mcp/
# GRAPHITI_MCP_TOKEN=<same as VPS>
# GRAPHITI_MEMORY_ENABLED=1
# GRAPHITI_WRITE_GATES=0

bash GlobalCommands/ops/scripts/setup_workspace_symlinks.sh "$(pwd)"
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py health
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py resolve
```

## Verify

```bash
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py bootstrap --dry-run --group-id sandbox-test
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py conflicts
bash .cursor-commands/ops/graphiti/test_gate_e2e_full.sh
```

## Custom ontology

Entity types are configured natively in `config-docker-neo4j.yaml` (`graphiti.entity_types`),
mounted into the container at `/app/mcp/config/config.yaml` — no CLI flag needed on this image.
Edit that file and `docker compose up -d --force-recreate graphiti-mcp` to apply.
`ontology_coding.py` is reference material only; it is not wired into this image.

## Autoseed on workspace wire

In `~/.cursor/graphiti.env`:

```bash
GRAPHITI_AUTOSEED=1   # default off — runs bootstrap via setup_workspace_symlinks.sh (memory-bank scaffold retired)
```

Manual check: `python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py autoseed-check` (exit 2 = not seeded).

## Warnings

- **No** C1 PacketStore / L9 MCP migration — bootstrap fresh per repo
- PlasticOS buyer-match Neo4j is separate (not this stack)
- Constellation Gate hub (ADR-002) is separate from Graphiti memory hooks
- Forbidden Graphiti groups: `main`, `default`, `test` (see `group_registry.yaml`)

## L9 decommission record

- **2026-06-07:** `/opt/l9` → `/opt/l9.archived-20260607`; all `l9-*` containers stopped
