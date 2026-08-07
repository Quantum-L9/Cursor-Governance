# ADR-0005: Interactive `l9-shared-memory` MCP registration (surface carriers)

## Status

Accepted

## Date

2026-08-04

## Context

ADR-0003 kept two memory entry points and named RC2 (registering the interactive
`l9-shared-memory` MCP server) as **out of scope / open**. #68 fixed the hook path
(RC1) but left the interactive path unregistered: on the managed (CCR) surface the
MCP set is sourced from the launch `--mcp-config` (account connectors) plus
user-scope config, and never from a home-dir `.mcp.json`. So `setup.sh`'s
`.mcp.json` copy — the only MCP wiring it performed — reached no interactive
surface there, `claude mcp list` was empty, and the model had no
`mcp__l9-shared-memory__*` tools.

`render.claude.json` already documents the intended carriers: **CLI = user-scope
`claude mcp add-json`**, **web/mobile = git-tracked `.mcp.json`**. Setup implemented
only the second. This ADR records the decision to implement the first, and the
per-surface carrier behavior — nothing more.

Empirical findings that bound the decision (verified 2026-08-04, CLI 2.1.221):

- The session launcher does **not** pass `--strict-mcp-config`, so a user-scope
  `~/.claude.json` MCP server is merged with the managed `--mcp-config` set.
- `claude mcp add-json --scope user` stores the server object **verbatim**,
  preserving `${...}` env-references; a sentinel token never landed on disk, and
  `claude mcp get` prints the `${...}` reference, not a resolved secret.
- `claude mcp get` / `list` health-check user-scope servers; `.mcp.json` servers
  show as pending-approval and are not connected.

## Decision

Register `l9-shared-memory` through the correct **surface-specific carrier**, and
verify readiness at runtime:

1. **CLI / managed surfaces** — `web/setup.sh` registers the server object from
   `mcp.template.json` via `claude mcp add-json --scope user l9-shared-memory`,
   only when the `claude` CLI and the memory env (`L9_MEMORY_HTTP_URL` +
   `L9_MEMORY_CLIENT_TOKEN`) are present. It is **idempotent** (skip when already
   registered with the same URL; warn — never overwrite — on a conflicting URL)
   and **secret-safe** (only `${...}` env-refs are stored; the token resolves at
   runtime). Registration failure is a visible WARN and never aborts setup.
2. **Web / mobile surfaces** — the git-tracked `.mcp.json` carrier is retained
   unchanged for surfaces that read a repo-local config.
3. **Account-managed fallback** — where neither carrier is honored, an operator
   registers `l9-shared-memory` as a managed-environment account connector. This
   is a documented **operator action** requiring exact approval, not automated
   here.
4. **Runtime readiness** — `validate_claude_env.py` fails when the interactive
   server is expected (CLI + memory env present) but absent, malformed, or not an
   `${...}` env-ref; it is advisory where the CLI is absent (CI / pre-clone web).
   Connectivity is reported but advisory, so a transient dial failure cannot turn
   a correctly-registered surface red.

The existing hook path (SessionStart prefetch, gate, lock, writeback) is
**unchanged** by this decision; the interactive and hook paths coexist.

## Consequences

- A fresh CLI/managed session that ran setup exposes `mcp__l9-shared-memory__*`
  tools for on-demand read/write.
- No bearer token is written to disk (env-ref carrier + a validator assertion).
- Re-running setup does not duplicate or churn the registration.
- Readiness is proven, not assumed; a surface that silently lacks the tools fails
  validation instead of passing green.
- The live carrier must still be confirmed per surface (the fresh-session test is
  authoritative); where a surface ignores user-scope, the account-connector
  fallback applies.

## Scope boundary (explicit)

This decision defines **only** interactive MCP registration and readiness. It does
**not** define the canonical future lifecycle memory architecture. The
**shared-mcp-memory-adapter-foundation** Program Execution campaign owns lifecycle
convergence, the shared adapter runtime, `l9-memory-mcp` lifecycle invocation,
`capabilities.yaml`, shared CLI enforcement, conformance, shadow migration, canary
cutover, and legacy-pipeline removal. RC2 is a transitional prerequisite and must
not pre-empt or duplicate that work.

This ADR does **not** supersede ADR-0002 (memory enforcement contract).

## Alternatives considered

- **Rely on `.mcp.json` alone.** Rejected: the managed/CLI launcher does not read a
  home-dir `.mcp.json`, so it registers nothing on that surface.
- **Expand the token into the stored MCP config.** Rejected (fail-closed): would
  persist a secret on disk. The `${...}` env-ref carrier is required; if a CLI ever
  expanded it at add-time, that path would not ship.
- **Build the campaign's shared adapter runtime now.** Rejected: out of scope; owned
  by the Program Execution campaign.

## References

- ADR-0002 — memory enforcement contract
- ADR-0003 — memory architecture: two entry points, one contract (RC2 open note)
- ADR-0004 — hook memory client is a contract-pinned stdlib mirror
- `environment/claude-code/mcp.template.json`, `web/setup.sh`, `validate_claude_env.py`,
  `render.claude.json`
- `reports/graphiti-memory-audit-2026-08-04/` — MEM-003 / RC2 origin
