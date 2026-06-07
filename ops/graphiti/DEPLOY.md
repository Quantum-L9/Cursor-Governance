# Graphiti VPS Deploy — Human Steps (Phase 0)

## Prerequisites

- VPS with Docker; Neo4j 5.26 + Graphiti MCP
- Tailscale on VPS and Mac
- OpenAI API key (extraction only)

## Deploy

```bash
cd GlobalCommands/ops/graphiti
cp graphiti.env.example graphiti.env   # on VPS — fill secrets
docker compose up -d
curl -sf -H "Authorization: Bearer $GRAPHITI_MCP_TOKEN" http://127.0.0.1:8100/healthcheck
cypher-shell -a bolt://127.0.0.1:7687 "RETURN 1"
```

Confirm default namespace: Graphiti MCP may use `"default"` or `"main"` — both are **forbidden** in production (`group_registry.yaml`).

## Mac client

```bash
cp graphiti.env.example ~/.cursor/graphiti.env   # fill Tailscale IP + token
# Merge mcp.json.example into ~/.cursor/mcp.json
bash GlobalCommands/ops/scripts/setup_workspace_symlinks.sh "$(pwd)"
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py health
```

## Verify namespace

```bash
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py resolve
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py bootstrap --dry-run --group-id sandbox-test
```
