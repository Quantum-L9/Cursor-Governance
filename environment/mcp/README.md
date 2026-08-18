# L9 Master MCP Configuration — Capability Broker Architecture

**Authority**: `~/.cursor-governance/environment/mcp/master.mcp.json`  
**Architecture**: Zero-secret capability broker (credentials never on agent surface)

**Wired to**:
- Cursor: `~/.cursor/mcp.json` (symlink)
- Claude Code CLI: `~/.claude/mcp.json` (symlink)
- Claude Code Web/Mobile: `mcp.template.json` (env-var refs)

This is the single source of truth for MCP server configuration across all L9 surfaces.

## Architecture: MCP Through Broker

```
Agent Surface (Cursor / Claude Code)
  ↓ POST /mcp
  ↓ X-Capability-Id: github.mcp
  ↓ NO credentials in headers or env
L9 Capability Broker (localhost:8787 or K8s)
  ↓ Authenticates caller (workload JWT)
  ↓ Fetches secret from Infisical (workload identity)
  ↓ Calls upstream API with credential
  ↓ Sanitizes response
Upstream API (api.github.com, api.context7.io, etc.)
```

**Key security property**: Agent surface never holds a credential. It asks the broker to perform a named capability. The broker resolves the secret, calls upstream, and returns a sanitized result.

## Setup

### For CLI (Cursor / Claude Code CLI)

1. **Start the broker locally**:
   ```bash
   cd ~/.cursor-governance
   make broker-serve
   ```
   
   Keep this running in a dedicated terminal.

2. **Set broker URL** in `~/.zshrc`:
   ```bash
   # L9 Capability Broker
   export L9_CAPABILITY_BROKER_URL=http://localhost:8787
   ```

3. **Reload shell**:
   ```bash
   source ~/.zshrc
   ```

4. **Restart Cursor/Claude Code** — MCPs should be green.

### For Web/Mobile (Claude Code Cloud)

1. **Deploy broker to K8s**:
   ```bash
   kubectl apply -f ops/secrets/k8s/broker-deployment.yaml
   ```

2. **Set broker URL** in cloud environment variables:
   ```
   L9_CAPABILITY_BROKER_URL=https://broker.quantumaipartners.com/l9/capability
   ```

3. **New sessions** will have green MCPs (no secret pasting required).

## How It Works

1. **Master config** (`master.mcp.json`) defines MCP servers
2. **Credential-bearing MCPs** point to `${L9_CAPABILITY_BROKER_URL}/mcp` with a capability ID
3. **No-credential MCPs** (Playwright, public repos) run locally as before
4. **Broker** holds secrets, agent surfaces hold only capability IDs
5. **Symlinks** are auto-created by `ops/scripts/setup_workspace_symlinks.sh`

## MCP Server Types

### Brokered (credential-bearing)

These reach upstream APIs through the broker:
- **GitHub**: `github.mcp` capability
- **Context7**: `context7.mcp` capability
- **Semgrep**: `semgrep.mcp` capability
- **GitGuardian**: `gitguardian.mcp` capability

Config format:
```json
{
  "GitHub": {
    "url": "${L9_CAPABILITY_BROKER_URL}/mcp",
    "headers": {
      "X-Capability-Id": "github.mcp"
    }
  }
}
```

### Local (no credential)

These run as local processes (no broker needed):
- **Playwright**: browser automation (no API key)
- **n8n-workflows**: public repo reader
- **Tavily Expert**: separate service (own URL)

Config format:
```json
{
  "Playwright": {
    "command": "npx",
    "args": ["@playwright/mcp@latest"]
  }
}
```

### Direct (separate bearer)

- **graphiti-memory**: Uses `${GRAPHITI_MCP_URL}` + `${GRAPHITI_MCP_TOKEN}` directly (Caddy proxy, not brokered)

## Adding a New MCP Server

### If it needs a credential

1. Add capability to `ops/secrets/capabilities.yaml`:
   ```yaml
   - id: myservice.mcp
     summary: My Service MCP proxy
     secret_refs: [MY_SERVICE_TOKEN]
     upstream_host: api.myservice.com
     methods: [GET, POST]
     paths:
       - /v1/resource
     params:
       query: {source: caller, validate: text, max_bytes: 500}
     sanitizer: passthrough
     failure_semantics: degrade
   ```

2. Add secret to Infisical (project: Cursor-Governance, env: prod)

3. Add to `master.mcp.json`:
   ```json
   {
     "MyService": {
       "url": "${L9_CAPABILITY_BROKER_URL}/mcp",
       "headers": {
         "X-Capability-Id": "myservice.mcp"
       }
     }
   }
   ```

4. Restart broker (CLI) or deploy new broker image (cloud)

### If it doesn't need a credential

Just add to `master.mcp.json`:
```json
{
  "MyService": {
    "command": "npx",
    "args": ["-y", "my-service-mcp"]
  }
}
```

## Wiring Check

```bash
cd ~/.cursor-governance
make wiring-check
```

This verifies:
- Symlinks exist and point to the master config
- No broken links
- No duplicate MCP configs

## Troubleshooting

### MCPs red in Cursor

1. **Check broker is running**:
   ```bash
   curl http://localhost:8787/healthz
   # Should return: {"status":"ok","capabilities":...}
   ```

2. **Check broker URL is set**:
   ```bash
   echo $L9_CAPABILITY_BROKER_URL
   # Should print: http://localhost:8787
   ```

3. **Check symlink**:
   ```bash
   ls -l ~/.cursor/mcp.json
   # Should point to: ~/.cursor-governance/environment/mcp/master.mcp.json
   ```

4. **Restart Cursor**

### Broker won't start

```bash
cd ~/.cursor-governance
python3 ops/secrets/capability_broker.py preflight
```

This reports:
- Boundary isolation (must NOT run in model-controlled env)
- Workload identity (AWS credentials for CLI)
- Capabilities registered

If preflight fails:
- Check AWS credentials: `aws sts get-caller-identity`
- Check Python deps: `make venv`
- Check Infisical bootstrap in AWS

### MCPs red in Claude Code Web/Mobile

1. **Check broker is deployed**:
   ```bash
   kubectl get pods -n claude-code -l app=l9-capability-broker
   ```

2. **Check broker URL in environment**:
   - Go to claude.ai/code → Settings → Environment
   - Verify `L9_CAPABILITY_BROKER_URL` is set

3. **Start a new session** (env vars only apply to new sessions)

## Migration from Old Architecture

If you were using `load_secrets_auto.sh` (RETIRED):

1. **Remove from `~/.zshrc`**:
   ```bash
   # Remove this block:
   if [ -f "${HOME}/.cursor-governance/environment/mcp/load_secrets_auto.sh" ]; then
       source "${HOME}/.cursor-governance/environment/mcp/load_secrets_auto.sh" 2>/dev/null || true
   fi
   ```

2. **Add broker URL** to `~/.zshrc`:
   ```bash
   export L9_CAPABILITY_BROKER_URL=http://localhost:8787
   ```

3. **Start broker**:
   ```bash
   make broker-serve
   ```

See `MIGRATION_TO_BROKER.md` for full migration guide.

## Files

- `master.mcp.json` — single source of truth
- `MIGRATION_TO_BROKER.md` — migration guide from old architecture
- `README.md` — this file
- `ops/secrets/capability_broker.py` — broker implementation
- `ops/secrets/capabilities.yaml` — capability registry
- `ops/secrets/k8s/broker-deployment.yaml` — K8s deployment
- `ops/scripts/setup_workspace_symlinks.sh` — auto-wiring
