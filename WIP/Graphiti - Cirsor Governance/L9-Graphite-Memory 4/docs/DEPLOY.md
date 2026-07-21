<!-- L9_META
l9_schema: 1
parent: l9-graphite-memory
layer: docs
role: runbook
tags: [deploy, operations, infisical, zep-cloud]
owner: platform
status: active
version: 2.0.0
updated: 2026-07-05
/L9_META -->

# Deployment Guide

This document covers deploying L9 Graphite Memory in production environments.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Infisical Vault (secrets source of truth)              │
│    └─ Machine Identity → Universal Auth                 │
│         └─ ZEP_API_KEY, L9_OPENAI_API_KEY, etc.        │
└────────────────────────┬────────────────────────────────┘
                         │ load_secrets_sync()
                         ▼
┌─────────────────────────────────────────────────────────┐
│  L9 Graphite Memory MCP Server                          │
│    └─ Transport: ZepCloudTransport                      │
│         └─ Zep Cloud API (managed Neo4j + extraction)   │
└────────────────────────┬────────────────────────────────┘
                         │ stdio / SSE
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Any MCP-compatible Agent                               │
│    (Cursor, Claude, Windsurf, Manus, custom)            │
└─────────────────────────────────────────────────────────┘
```

## Deployment Modes

### Mode 1: Local stdio (Recommended for Development)

The MCP server runs as a child process of the agent. Agent spawns it via the config written by `write_cursor_config.py` or `write_claude_config.py`.

**Requirements:**
- Package installed: `pip install -e ".[all]"`
- 3 Infisical bootstrap env vars set in the agent's MCP server env block

**No separate deployment needed** — the agent manages the lifecycle.

### Mode 2: SSE/HTTP (Recommended for Shared/Team Use)

The MCP server runs as a standalone HTTP service. Multiple agents connect via SSE.

```bash
export INFISICAL_CLIENT_ID="..."
export INFISICAL_CLIENT_SECRET="..."
export INFISICAL_PROJECT_ID="..."
python -m l9_graphite_memory.server --transport sse --port 8200
```

Agents connect via:
```json
{
  "mcpServers": {
    "l9-graphite-memory": {
      "url": "http://your-host:8200/mcp/"
    }
  }
}
```

### Mode 3: Container (Recommended for Production)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install ".[all]"
EXPOSE 8200
CMD ["python", "-m", "l9_graphite_memory.server", "--transport", "sse", "--port", "8200"]
```

Inject Infisical vars via container orchestrator (K8s secrets, ECS task definition, etc.).

## Secrets Management

All secrets are managed via [Infisical](https://infisical.com) Universal Auth. See [ADR-001](adr/ADR-001-infisical-secrets-architecture.md) for the full architecture.

**Required secrets in Infisical vault:**

| Key | Description | Required |
|-----|-------------|----------|
| `ZEP_API_KEY` | Zep Cloud API key | Yes (for zep transport) |
| `L9_OPENAI_API_KEY` | OpenAI key for entity extraction | Optional (Zep handles it) |

**Bootstrap vars (set on machine/container, NOT in vault):**

| Variable | Description |
|----------|-------------|
| `INFISICAL_CLIENT_ID` | Machine identity client ID |
| `INFISICAL_CLIENT_SECRET` | Machine identity client secret |
| `INFISICAL_PROJECT_ID` | Infisical project ID |

## Secret Rotation

The secrets adapter supports zero-downtime rotation:

1. **SIGHUP reload**: Send SIGHUP to the server process to trigger `refresh_secrets()`
2. **Interval refresh**: Set `L9_SECRET_REFRESH_INTERVAL=900` for automatic 15-minute refresh
3. **Infisical rotation**: When Infisical rotates a secret, send SIGHUP to the server

## Health Monitoring

```bash
# CLI health check
l9-memory health

# HTTP health endpoint (SSE mode)
curl http://localhost:8200/healthcheck
```

## Upgrading

```bash
git pull
pip install -e ".[all]"
bash scripts/preflight.sh
# Restart agent or server
```

## Decommissioned (v1.0 Legacy)

The following are no longer used and have been archived to `_archived/`:

- `~/.cursor/graphiti.env` — replaced by Infisical vault
- `~/.cursor/secrets/graphiti.env` — replaced by Infisical vault
- `ensure_graphiti_tunnel.sh` — no SSH tunnel needed (Zep Cloud is HTTPS)
- `docker-compose.yml` (Neo4j + Graphiti self-hosted) — replaced by Zep Cloud managed service
- macOS Keychain storage — replaced by Infisical Universal Auth
- Hetzner VPS `46.62.243.82` — decommissioned
- See `_archived/DEPLOY-vps-legacy.md` for the old VPS runbook
