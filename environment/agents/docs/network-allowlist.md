<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/docs/network-allowlist.md
layer: doc
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-07-31
/L9_META -->

# Network allowlist — multi-agent cloud surfaces

Peer of `environment/agents/adapters/claude-code/web/network-policy.md`. Apply the same hosts
on Manus / Codex cloud / Gemini / any Custom-network sandbox that must reach
shared memory and GitHub.

## Required for shared memory + governance

| Host | Why |
|---|---|
| `memory.quantumaipartners.com` | Graphiti HTTPS MCP (`GRAPHITI_MCP_URL` …/graphiti/mcp) |
| `broker.quantumaipartners.com` | **nobody** — capability-broker experiment retired; never shipped. Do not allowlist a host no adapter calls |
| `github.com`, `*.githubusercontent.com` | clone governance + consumer repos |
| `api.github.com` | `gh` / GitHub API |
| `pypi.org`, `files.pythonhosted.org` | Python toolchains when the surface installs packages |
| `registry.npmjs.org` | Node toolchains when applicable |
| `npm.pkg.github.com` | GitHub Packages for `@quantum-l9/*` (`ops/secrets/gh_npm.sh` + `gh auth token` on hosted; Infisical `authed_npm.sh` for trusted operators). Do not paste `NODE_AUTH_TOKEN` |

## Production memory

```text
https://memory.quantumaipartners.com/graphiti/mcp
```

TLS terminates at Caddy on C1 → `l9-memory-server` (loopback on the host).
Unauthenticated MCP calls must receive **401**. Cloud adapters use the
HTTPS hostname above — never a loopback URL as the default.

## Surface notes

| Surface | Where to set allowlist |
|---|---|
| Claude Code Web/Mobile | Account environment → Network access (see claude-code pack) |
| Manus | Manus project / connector network settings |
| Codex cloud | Codex environment network / egress settings |
| Gemini CLI | Host machine firewall / corporate proxy (CLI is local) |
| Generic | Whatever the surface uses for egress |
