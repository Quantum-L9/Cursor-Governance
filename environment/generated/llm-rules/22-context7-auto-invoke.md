---
description: Auto-invoke Context7 MCP before coding on external libraries —FastAPI, Neo4j, pytest, GitHub Actions, new platforms/tools, APIs, MCP, install, Docker.
---

# Context7 Auto-Invoke (External Docs)

**MCP servers:** `context7` (Claude Code plugin, and the governed vault bridge
in `mcp.template.json`) **and** `user-Context7` (Cursor).
**Skill:** `@.cursor-commands/skills/l9-context7-docs/`

Hosted Web/Mobile runs with `SKIP_PLUGIN_MARKETPLACE=true`, so the marketplace
plugin never installs there. The governed server closes that gap without a
pasted key (2026-09-24): `mcp.template.json` declares `context7` as a local
stdio bridge (`ops/secrets/run_vault_mcp_bridge.sh context7`) that binds
`CONTEXT7_API_KEY` from Infisical in-process, as this surface's machine
identity, and forwards to `https://mcp.context7.com/mcp`. The key is never in
the environment, argv, `.mcp.json` or a file, and no header references it.

The server renders **unconditionally** (never `_requires_env`-gated: that turned
a missing secret into a silently absent server). When the key cannot be bound
the bridge refuses to start and names the fix — the surface's Infisical machine
identity (`L9_INFISICAL_CLIENT_ID` + `L9_INFISICAL_CLIENT_SECRET`, set once in
the environment settings). That is a failure to **fix**, never to skip or
remove, and SessionStart reports the bind by name and source.

Until it does, and only until then, the obligation when `mcp__context7__*`
tools are **absent or failing** is unchanged: skill `l9-context7-docs` or an
official docs GET. Never treat a missing MCP tool as permission to skip docs,
never close the gap by pasting `CONTEXT7_API_KEY` into the account variables
field, `mcp.template.json` or `.mcp.json`, and never close it by gating the
server out of `.mcp.json` again.

Call whichever server this surface exposes. Do not treat a missing allow-list
entry as permission to skip.

## Mandatory — call Context7 before first implementation

When the task touches any item below, **read MCP tool schemas** if those tools
exist, then call `resolve-library-id` → `query-docs`. If those MCP tools are
not on this session, invoke skill `l9-context7-docs` (or GET official docs)
**before writing or editing code**. Do not wait for the user to say "use context7".

| Trigger | Examples | Seed library names |
|---------|----------|-------------------|
| **FastAPI / ASGI** | routes, middleware, deps, Pydantic v2, lifespan | `FastAPI`, `Starlette`, `Pydantic` |
| **Neo4j** | Cypher, Python driver, graph sync/scoring | `Neo4j Python Driver`, `Neo4j` |
| **pytest** | fixtures, markers, parametrize, asyncio, plugins | `pytest`, `pytest-asyncio` |
| **GitHub Actions / gh** | workflow syntax, actions, expressions, `gh` CLI | `GitHub Actions`, `actions/checkout` |
| **API / MCP / install / Docker** | vendor payloads, MCP tools, package install, Compose | official product name |
| **New software** | unfamiliar SDK, platform, plugin, MCP server, CLI tool | official product name |
| **Dev tooling** | Docker Compose, pre-commit, ruff, semgrep, MCP SDK | tool's official name |

Also invoke when: version-specific API, migration syntax, deprecated patterns, or errors suggesting stale/wrong API shape.

Upstream API field names, MCP tool schemas, install commands, and Docker
images are **not** "local repo code". A payload such as `language_name: "en"`
is an upstream contract and requires Context7 (then official docs GET).

## Verify before codegen

- Before calling a third-party library function, verify the symbol exists in the project's installed version (`package.json`, `pyproject.toml`, `go.mod`, etc.).
- If Context7 misses, GET the official docs page. If that also misses, stop (Unknown). Do not invent fields.
- Never invent function signatures, parameter names, or return types — propose adding the dependency (with version) before writing code that depends on it.

## Skip Context7

- Secrets, credentials, proprietary payloads must never go in Context7 queries.
- Do **not** skip because the edit is "just config" or "purely local" when an API, MCP tool, install, or Docker image is involved.

## MCP flow (max 3 calls each)

1. `resolve-library-id` — `{ "libraryName": "...", "query": "specific task, no secrets" }`
2. `query-docs` — `{ "libraryId": "/org/project", "query": "..." }`

If user gives a library ID (`/org/project`), skip step 1.

## Output

```markdown
Context7 checked: `/org/project`
Key constraints:
- …
Applied in: …
```

<!-- generated-from: rules/22-context7-auto-invoke.mdc; do-not-edit -->
