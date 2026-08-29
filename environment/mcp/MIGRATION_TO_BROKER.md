> **RETIRED 2026-08-29.** The capability broker never shipped. Do not follow
> these steps. Live MCP: `environment/mcp/README.md` and `ops/secrets/RETIRED.md`.

# Migration to Capability Broker Architecture

**Date**: 2026-08-17  
**Status**: Completed

## What Changed

MCP servers (GitHub, Context7, Semgrep, GitGuardian) now reach upstream APIs through the L9 capability broker instead of holding credentials directly.

### Before

```bash
# Old: Direct secret loading (RETIRED)
export GITHUB_TOKEN="$(python3 ops/secrets/resolve_secret.py ...)"
export CONTEXT7_API_KEY="$(python3 ops/secrets/resolve_secret.py ...)"
# ... loaded in ~/.zshrc via load_secrets_auto.sh

# MCPs connected directly to upstream APIs with these env vars
```

### After

```bash
# New: Broker-mediated access (NO credentials on agent surface)
export L9_CAPABILITY_BROKER_URL=http://localhost:8787

# MCPs connect to broker with capability IDs, broker holds secrets
```

## Migration Steps

### 1. Remove Old Secret Loading from ~/.zshrc

**Remove these lines** from `~/.zshrc`:

```bash
# L9 MCP Secrets (auto-load) — REMOVE THIS BLOCK
if [ -f "${HOME}/.cursor-governance/environment/mcp/load_secrets_auto.sh" ]; then
    source "${HOME}/.cursor-governance/environment/mcp/load_secrets_auto.sh" 2>/dev/null || true
fi
```

Then reload:
```bash
source ~/.zshrc
```

### 2. Start the Broker Locally (CLI Surfaces)

In a dedicated terminal (keep it running):

```bash
cd ~/.cursor-governance
make broker-serve
```

This starts the broker on `http://localhost:8787`.

### 3. Set Broker URL

Add to `~/.zshrc`:

```bash
# L9 Capability Broker
export L9_CAPABILITY_BROKER_URL=http://localhost:8787
```

Then reload:
```bash
source ~/.zshrc
```

### 4. Verify MCPs

Restart Cursor/Claude Code and check that MCPs are green:
- GitHub ✅
- Context7 ✅
- Semgrep ✅
- GitGuardian ✅
- Playwright ✅
- graphiti-memory ✅

## For Web/Mobile (Claude Code Cloud)

No migration needed — Web/Mobile MCPs were degraded before and will be enabled once the broker is deployed to K8s:

1. Deploy broker to C1:
   ```bash
   kubectl apply -f ops/secrets/k8s/broker-deployment.yaml
   ```

2. Set `L9_CAPABILITY_BROKER_URL` in cloud environment variables:
   ```
   L9_CAPABILITY_BROKER_URL=https://broker.quantumaipartners.com/l9/capability
   ```

3. MCPs will be green on next session start.

## Architecture

```
Agent Surface (Cursor / Claude Code)
  ↓ POST /mcp with X-Capability-Id header
L9 Capability Broker (localhost:8787 or K8s)
  ↓ Fetches secret from Infisical (workload auth)
Upstream API (api.github.com, api.context7.io, etc.)
```

**Key security property**: Agent surface never holds a credential. It asks the broker to perform a named capability. The broker resolves the secret, calls upstream, and returns a sanitized result.

## Troubleshooting

### MCPs still red after migration

1. Check broker is running:
   ```bash
   curl http://localhost:8787/healthz
   # Should return: {"status":"ok","capabilities":...}
   ```

2. Check `L9_CAPABILITY_BROKER_URL` is set:
   ```bash
   echo $L9_CAPABILITY_BROKER_URL
   # Should print: http://localhost:8787
   ```

3. Check MCP config points at broker:
   ```bash
   cat ~/.cursor/mcp.json | grep L9_CAPABILITY_BROKER_URL
   ```

4. Restart Cursor/Claude Code

### Broker won't start

```bash
cd ~/.cursor-governance
python3 ops/secrets/capability_broker.py preflight
```

This reports:
- Boundary isolation (broker must NOT run in model-controlled env)
- Workload identity method (AWS credentials for CLI)
- Capabilities registered

If preflight fails, check:
- AWS credentials configured (`aws sts get-caller-identity`)
- Infisical bootstrap secrets in AWS Secrets Manager
- Python dependencies installed (`make venv`)

## Rollback (if needed)

If you need to revert temporarily:

1. Restore old `load_secrets_auto.sh` from git history
2. Re-add to `~/.zshrc`
3. Update `master.mcp.json` to use env vars instead of broker URLs

But this is NOT recommended — the broker is the correct architecture.

## References

- ADR-0024: MCP Capability Broker Integration
- `ops/secrets/capability_broker.py` — broker implementation
- `ops/secrets/capabilities.yaml` — capability registry
- `environment/mcp/master.mcp.json` — CLI MCP config
- `environment/agents/adapters/claude-code/mcp.template.json` — Web/Mobile config
