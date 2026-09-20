# Graphiti VPS Deploy — C1 post-L9 (locked)

> **Retired 2026-09-06 (memory realignment C11, ADR-0030).** This document describes the direct Graphiti provider path that Cursor-Governance no longer has. Memory is the canonical `l9-graphite-memory` control plane (`ops/memory`, `python -m ops.memory.cli`); see `ops/memory/README.md` and `docs/MEMORY_PIPELINE_MAP.md`. Kept as an operator record of the projection deployment only.

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

The agent front door is **not** this tunnel. ADR-0031 sealed agent HTTP;
`graphiti_memory_client.py` is a tombstone. Use the locked venv:

```bash
GOV="${HOME}/.cursor-governance"
PY="${GOV}/.venv/bin/python"
WS="${CURSOR_PROJECT_DIR:-$(pwd)}"
(cd "$GOV" && PYTHONPATH="$GOV" "$PY" -m ops.memory.cli health --workspace "$WS")
(cd "$GOV" && PYTHONPATH="$GOV" "$PY" -m ops.memory.cli resolve --workspace "$WS")
```

Historical projection access only (retired as the live client — do not treat
`GRAPHITI_MCP_URL` / a bearer as memory):

```bash
# Terminal 1 — retired tunnel (projection host leftover)
ssh -N -L 8100:127.0.0.1:8100 -i ~/.ssh/Hetzner-C1-nopass root@46.62.243.82
```

## Verify

```bash
GOV="${HOME}/.cursor-governance"
PY="${GOV}/.venv/bin/python"
WS="${CURSOR_PROJECT_DIR:-$(pwd)}"
(cd "$GOV" && PYTHONPATH="$GOV" "$PY" -m ops.memory.cli readiness --workspace "$WS" --json)
(cd "$GOV" && PYTHONPATH="$GOV" "$PY" -m ops.memory.cli conflicts --workspace "$WS")
```

`graphiti_memory_client.py bootstrap|conflicts` is retired (tombstone). Do not
run it as a live health recipe.

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

Manual check (retired client — do not use as the live front door):
`python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py autoseed-check` is a tombstone invocation. Prefer `python -m ops.memory.cli readiness`.

## Warnings

- **No** C1 PacketStore / L9 MCP migration — bootstrap fresh per repo
- PlasticOS buyer-match Neo4j is separate (not this stack)
- Constellation Gate hub (ADR-002) is separate from Graphiti memory hooks
- Forbidden Graphiti groups: `main`, `default`, `test` (see `group_registry.yaml`)

## L9 decommission record

- **2026-06-07:** `/opt/l9` → `/opt/l9.archived-20260607`; all `l9-*` containers stopped
