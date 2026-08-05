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
# Optional: curl -sS -o /dev/null -w "%{http_code}\n" "$L9_MEMORY_HTTP_URL/healthz"
# The SessionStart hook should have injected an "L9 Governance — Claude Code session"
# context block listing the governance clone and available skills.
```

## Shared memory (optional, cross-session)

`environment.env.example` sets `L9_MEMORY_HTTP_URL` / `L9_MEMORY_CLIENT_TOKEN`;
`../mcp.template.json` is the MCP block that consumes them (URL expands to
`${L9_MEMORY_HTTP_URL}/mcp`). One long-running HTTP control plane owns the
canonical DB; all sessions share it. Production endpoint:
`https://memory.quantumaipartners.com` (Caddy TLS → C1 `l9-memory-server` on
`:8200`). `setup.sh` only wires the client (`.mcp.json`); it never starts a
local memory server.

**Identity (shared graph, distinct author).** The `group_id` (repo namespace) is
shared with Cursor — that is what makes memory shared. The writing-agent identity
is **not**: Claude Code uses `USER_ID=claude_code_agent` / `L9_MEMORY_AGENT_ID=claude-code`
and its **own** bearer token (a separate server principal), so it never writes
under Cursor's `cursor_agent`. Give Claude Code a token distinct from Cursor's.

**Allowlist:** Add `memory.quantumaipartners.com` to the Claude environment
Network-access allowlist (or use Full). Authentication is required on the
server; bearer tokens never go in `.mcp.json`.

### Two memory entry points

Memory reaches a session two ways (see `docs/decisions/ADR-0003`), both on the same
server and contract:

- **Lifecycle (hook) path** — the SessionStart prefetch injects context and the Stop
  hook writes back, via the stdlib client. Always on; unchanged by RC2.
- **Interactive (MCP tool) path** — `mcp__l9-shared-memory__*` tools the model calls
  on demand. This needs the MCP server *registered* with Claude Code.

### How the interactive server is registered (carriers)

Registration depends on the surface (`render.claude.json` is the map):

| Surface | Carrier | Installed by |
|---|---|---|
| CLI / managed (CCR) | **user scope** — `claude mcp add-json --scope user l9-shared-memory …` | `setup.sh` (step 5a), idempotent |
| Web / mobile (repo-local) | git-tracked **`.mcp.json`** | `setup.sh` step 3.5 (copied from `mcp.template.json`) |
| Any surface that honors neither | **account connector** (operator adds it in the managed-environment MCP settings) | manual, operator action |

`setup.sh` registers user-scope only when the `claude` CLI and `L9_MEMORY_*` are
present; it is idempotent (skips when already registered, warns — never overwrites —
on a conflicting URL) and secret-safe (stores only `${...}` env-refs; the token
resolves at runtime and is never written to disk). If registration cannot be
performed on a surface, setup emits a WARN and continues — the hook path is
unaffected — and readiness validation surfaces the gap rather than a false green.

### Verify the interactive path (fresh session)

```bash
claude mcp list                     # l9-shared-memory should be listed
claude mcp get l9-shared-memory     # Status: connected (env-ref auth, not a literal token)
python3 environment/claude-code/validate_claude_env.py   # includes interactive-MCP readiness
```

`validate_claude_env.py` treats readiness as **blocking** where the CLI + memory env
are present (the surface should expose tools) and **advisory** where the CLI is
absent (CI / pre-clone web). A missing or malformed registration fails; a transient
connectivity error is reported but does not fail.

> RC2/MEM-003 covers interactive registration only. Convergence of the lifecycle
> path onto the shared adapter runtime is owned by the shared-mcp-memory-adapter
> foundation campaign, not this change.

## Security

- Env vars are stored **in plaintext** in the environment config. Use a
  least-privilege dedicated bot account; rotate any token ever pasted in chat.
- Never commit `GH_TOKEN` / `L9_MEMORY_CLIENT_TOKEN` / `SONAR_TOKEN` to a repo. A
  committed `.env` is a leaked secret. `.mcp.json` carries only `${...}`
  references, never the token itself.
