# Claude Code Web & Mobile — account environment install guide

Configure the account **environment** once in `claude.ai/code` (open your
environment → edit). Sessions run in Anthropic's **Linux** sandbox; Web and
Mobile share the same account environment (there is no separate mobile file).

> Environment changes apply to **new sessions only**. Start a fresh session after
> saving.

The environment has exactly three fields; this directory has one artifact per
field.

| Field (in the edit dialog) | Paste / set from | Purpose |
|---|---|---|
| **Network access** | `network-policy.md` | let the sandbox reach GitHub, registries, scanners |
| **Environment variables** | `environment.env.example` | credentials + governance/memory locations (placeholders → real values in the UI) |
| **Setup script** | `setup.sh` | install `gh`, toolchains, `pre-commit` (the `make pr` gate, CANONICAL_LAW §12), clone governance, provision memory |

## Steps

1. **Network access** — pick **Full** (simplest) or **Custom** + the allowlist in
   `network-policy.md`.
2. **Environment variables** — paste `environment.env.example`, then replace every
   `REPLACE_WITH_*` **in the UI, not in chat or a repo**. At minimum set `GH_TOKEN`
   (dedicated bot-user fine-grained PAT).
3. **Setup script** — **paste `setup.bootstrap.sh` (recommended), not `setup.sh`.**
   The account field is a *copy*, not a live link to the repo, so pasting the full
   `setup.sh` drifts from the file on every edit until someone re-pastes it. The
   bootstrap is a stable stub: it clones/refreshes `Cursor-Governance` and then
   executes the canonical `setup.sh` from it, so edits to `setup.sh` on `main`
   propagate to every new session with **no re-paste**. (Pasting `setup.sh`
   directly still works — it's the same logic — but you own keeping it in sync.)
   Either way it is idempotent, auto-detects Python vs Node, clones governance to
   `$HOME/.cursor-governance`, provisions `pre-commit` (the `make pr` gate,
   CANONICAL_LAW §12), and optionally wires the shared-memory MCP client (`.mcp.json`).
4. **Per-repo (git-tracked, recommended)** — in each consumer repo commit the
   `.claude/` triad so the SessionStart hook boots governance from the clone (see
   the parent `README.md` §4). Committing is preferred: it is explicit, reviewable,
   and identical on CLI. **Not strictly required for Mobile/Web**, though —
   `setup.sh` step 3.5 installs the `.claude/` triad from the governance clone into
   the workspace when a repo has not committed it, so every mobile chat
   self-activates either way. It never overwrites files the repo already committed.

## Verify (in a fresh session after saving)

```bash
gh auth status                              # Logged in as <bot-user>
ls "$HOME/.cursor-governance/CANONICAL_LAW.md"   # governance clone present
# Memory = Cursor Graphiti front door only (ADR-0006).
# Optional: curl -sS -o /dev/null -w "%{http_code}\n" "$GRAPHITI_FRONT_DOOR/healthz"
# The SessionStart hook should have injected an "L9 Governance — Claude Code session"
# context block listing the governance clone and available skills.
```

## Shared memory (optional, cross-session)

`environment.env.example` sets `GRAPHITI_FRONT_DOOR` / `GRAPHITI_MCP_TOKEN`;
`../mcp.template.json` is the MCP block that consumes them (URL expands to
`${GRAPHITI_FRONT_DOOR}/mcp`). One long-running HTTP control plane owns the
canonical DB; all sessions share it. Production endpoint:
`http://127.0.0.1:8100` (Caddy TLS → C1 `l9-memory-server` on
`:8200`). `setup.sh` only wires the client (`.mcp.json`); it never starts a
local memory server.

**Identity (shared graph, distinct author).** The `group_id` (repo namespace) is
shared with Cursor — that is what makes memory shared. The writing-agent identity
is **not**: Claude Code uses `USER_ID=claude_code_agent` / `L9_MEMORY_AGENT_ID=claude-code`
and its **own** bearer token (a separate server principal), so it never writes
under Cursor's `cursor_agent`. Give Claude Code a token distinct from Cursor's.

**Allowlist:** Add `127.0.0.1:8100` to the Claude environment
Network-access allowlist (or use Full). Authentication is required on the
server; bearer tokens never go in `.mcp.json`.

## Security

- Env vars are stored **in plaintext** in the environment config. Use a
  least-privilege dedicated bot account; rotate any token ever pasted in chat.
- Never commit `GH_TOKEN` / `GRAPHITI_MCP_TOKEN` / `SONAR_TOKEN` to a repo. A
  committed `.env` is a leaked secret. `.mcp.json` carries only `${...}`
  references, never the token itself.
