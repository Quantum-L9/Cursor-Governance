# Network access — L9 Claude Code cloud environment (Web · Mobile)

Paste guidance for claude.ai/code → environment → Network access.
Same environment is used by Web, Mobile, Desktop cloud, and `claude --cloud`.

## Option A — Full (fastest proof)

Network access → **Full**.

## Option B — Custom (least privilege)

Network access → **Custom**, include default package-manager list, plus:

```
github.com
*.githubusercontent.com
api.github.com
cli.github.com
pypi.org
files.pythonhosted.org
registry.npmjs.org
memory.quantumaipartners.com
sonarcloud.io
*.sonarcloud.io
```

`memory.quantumaipartners.com` is required for HTTPS Graphiti (`/graphiti/mcp`).
MCP connectors routed through Anthropic may not need allowlisting; keep the host
for setup probes and `.mcp.json` HTTP clients.

