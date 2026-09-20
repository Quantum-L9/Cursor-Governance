<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/docs/network-allowlist.md
layer: doc
owner: governance-control-plane
status: active
version: 1.2.0
updated: 2026-09-14
/L9_META -->

# Network allowlist — multi-agent cloud surfaces

Peer of `environment/agents/adapters/claude-code/web/network-policy.md`. Apply the same hosts
on Manus / Codex cloud / Gemini / any Custom-network sandbox that must reach
GitHub. Agent memory is stdio MCP (ADR-0031) and does **not** require an HTTPS host.

## Required for governance

Every row here is a host an adapter actually calls. Memory is not among them:
agent memory is stdio MCP and opens no HTTPS egress (ADR-0031).

| Host | Why |
|---|---|
| `github.com`, `*.githubusercontent.com` | clone governance + consumer repos |
| `api.github.com` | `gh` / GitHub API |
| `pypi.org`, `files.pythonhosted.org` | Python toolchains when the surface installs packages |
| `registry.npmjs.org` | Node toolchains when applicable |
| `npm.pkg.github.com` | GitHub Packages for `@quantum-l9/*` (`ops/secrets/gh_npm.sh` + `gh auth token` on hosted; Infisical `authed_npm.sh` for trusted operators). Do not paste `NODE_AUTH_TOKEN` |

## Historical — not required, do not allowlist

Hosts that once appeared in agent allowlists and no longer belong there. Keep
them out of the copyable list of every surface.

| Host | Status |
|---|---|
| `memory.quantumaipartners.com` | **Retired** as the agent memory front door (the former Graphiti HTTPS MCP at `/graphiti/mcp`). Not required for agent memory — ADR-0031: stdio MCP only, agent HTTP sealed. What remains behind that name is operator infrastructure (TLS still terminates at Caddy on C1), never an adapter target |
| `broker.quantumaipartners.com` | **Never shipped** — capability-broker experiment retired. No adapter calls it |

## Agent memory (no HTTPS host)

Agent memory is package-owned `l9-graphite-memory` stdio MCP. There is no
required HTTPS host and no `GRAPHITI_MCP_URL` on the agent surface. Do not
teach cloud adapters to hold the retired URL above or any memory bearer.

## Surface notes

| Surface | Where to set allowlist |
|---|---|
| Claude Code Web/Mobile | Account environment → Network access (see claude-code pack) |
| Manus | Manus project / connector network settings |
| Codex cloud | Codex environment network / egress settings |
| Gemini CLI | Host machine firewall / corporate proxy (CLI is local) |
| Generic | Whatever the surface uses for egress |
