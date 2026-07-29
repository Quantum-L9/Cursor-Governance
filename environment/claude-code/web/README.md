# Claude Code Web & Mobile — account environment install guide

Configure the account **environment** once in `claude.ai/code` (open your
environment → edit). The environment is **account-level**, so **Claude Code
Mobile uses the same config** — sessions started from the phone inherit it. There
is no separate mobile file.

> Environment changes apply to **new sessions only**. Start a fresh session after
> saving.

The environment has exactly three fields; this directory has one artifact per
field.

| Field (in the edit dialog) | Paste / set from | Purpose |
|---|---|---|
| **Network access** | `network-policy.md` | let the sandbox reach GitHub, registries, scanners |
| **Environment variables** | `environment.env.example` | credentials + governance/memory locations (placeholders → real values in the UI) |
| **Setup script** | `setup.sh` | install `gh`, toolchains, clone governance, provision memory |

## Steps

1. **Network access** — pick **Trusted** (recommended for a plain Python/TS repo;
   GitHub + package registries already allowlisted, no maintenance), **Full**
   (unrestricted), or **Custom** + the allowlist in `network-policy.md`. Four
   levels exist — `None / Trusted / Full / Custom`; see `network-policy.md`.
2. **Environment variables** — paste `environment.env.example`, then replace every
   `REPLACE_WITH_*` **in the UI, not in chat or a repo**. At minimum set `GH_TOKEN`
   (dedicated bot-user fine-grained PAT).
3. **Setup script** — paste `setup.sh`. It is idempotent and auto-detects Python
   vs Node, clones `Cursor-Governance` to `L9_GOVERNANCE_DIR`, and (optionally)
   installs the memory client.
4. **Per-repo (git-tracked, recommended)** — in each consumer repo commit the
   `.claude/` triad so the SessionStart hook boots governance from the clone (see
   the parent `README.md` §4). Committing is preferred: it is explicit, reviewable,
   and identical on CLI. **Not strictly required for Mobile/Web**, though —
   `setup.sh` step 3.5 installs the `.claude/` triad from the governance clone into
   the workspace when a repo has not committed it, so every mobile chat
   self-activates either way. It never overwrites files the repo already committed.

## Verify (in a fresh session after saving)

```bash
gh auth status                       # Logged in as <bot-user>
ls "$L9_GOVERNANCE_DIR/CANONICAL_LAW.md"   # governance clone present
# The SessionStart hook should have injected an "L9 Governance — Claude Code session"
# context block listing the governance clone and available skills.
```

## Shared memory (optional, cross-session)

`environment.env.example` sets `L9_MEMORY_HTTP_URL` / `L9_MEMORY_CLIENT_TOKEN`;
`../mcp.template.json` is the MCP block that consumes them. One long-running HTTP
server owns the canonical DB and all sessions share it.

**Identity (shared graph, distinct author).** The `group_id` (repo namespace) is
shared with Cursor — that is what makes memory shared. The writing-agent identity
is **not**: Claude Code uses `USER_ID=claude_code_agent` / `L9_MEMORY_AGENT_ID=claude-code`
and its **own** bearer token (a separate server principal), so it never writes
under Cursor's `cursor_agent`. Give Claude Code a token distinct from Cursor's.

**Container scope caveat:** `127.0.0.1:8200` shares memory only across sessions on
the **same host/container**. Separate ephemeral cloud containers each have their
own loopback and will **not** share via `127.0.0.1`. For cross-container sharing,
bind the memory server to a routable host, point `L9_MEMORY_HTTP_URL` at it, and
add that host to the Network-access allowlist. Authentication stays required; the
server refuses unauthenticated non-loopback binds.

## Security

- Env vars are stored **in plaintext** in the environment config. Use a
  least-privilege dedicated bot account; rotate any token ever pasted in chat.
- Never commit `GH_TOKEN` / `L9_MEMORY_CLIENT_TOKEN` / `SONAR_TOKEN` to a repo. A
  committed `.env` is a leaked secret. `.mcp.json` carries only `${...}`
  references, never the token itself.
