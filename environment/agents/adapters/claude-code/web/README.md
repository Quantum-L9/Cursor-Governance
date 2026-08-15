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
| **Environment variables** | `environment.env.example` | credentials + surface/memory/autonomy posture (placeholders → real values in the UI) |
| **Setup script** | `setup.bootstrap.sh` | normalize the environment, clone governance, then exec the canonical `setup.sh` from that clone |

## One adapter, thin surface callers

There is a single installer — `../install.sh` — and every surface reaches it:

```
Web / Mobile / --cloud   setup.bootstrap.sh ─→ web/setup.sh ─→ ../install.sh
CLI / Desktop            make claude-install ──────────────-─→ ../install.sh
```

`install.sh` owns everything surface-neutral: the locked toolchain, the settings
triad, skill discovery, the MCP front door, local git excludes, and the
readiness preflight. The surface callers own only what their surface uniquely
needs — for the cloud that is `gh`, credentials, cloning governance, and the
consumer repo's own language toolchain. **Add adapter behaviour to
`install.sh`, not to a caller**, or the surfaces drift apart again.

`make claude-install-check` reports drift read-only, writing nothing.

### Dependencies and tool versions

`uv.lock` in this repo is the only source of interpreter and dependency
versions. `install.sh` applies it through the existing wrapper,
`ops/scripts/ensure_uv_environment.sh` (`uv sync --locked --extra dev`,
fingerprint-cached so a re-run is a no-op). It never installs a package by
name, and `validate_claude_env.py` fails any adapter script that tries.

That wrapper produces `$HOME/.cursor-governance/.venv/bin/python3` — the
interpreter `ops/graphiti`, `ops/autonomy`, and `memory/graphiti_bridge.py`
already resolve to. It matters that it exists: the sandbox's system `python3` is
3.11, while `.python-version` and `requires-python` pin ≥3.12, so without the
locked venv the memory gate cannot import its brain and governed writes are
denied.

> **The variables field is literal text — no shell expansion.** `FOO=$HOME/x` is
> stored as the characters `$HOME/x`. Never reference `$HOME` there; that is why
> `L9_GOVERNANCE_DIR` is deliberately absent from `environment.env.example` (the
> SSOT path is hard-pinned by `setup.sh` and the SessionStart hook instead).

## Steps

1. **Network access** — pick **Full** (simplest) or **Custom** + the allowlist in
   `network-policy.md`.
2. **Environment variables** — paste `environment.env.example`, then replace every
   `REPLACE_WITH_*` **in the UI, not in chat or a repo**. At minimum set `GH_TOKEN`
   and `GRAPHITI_MCP_TOKEN` (dedicated bot-user PAT + Graphiti bearer).
3. **Setup script** — **paste `setup.bootstrap.sh` (recommended), not `setup.sh`.**
   The account field is a *copy*, not a live link to the repo, so pasting the full
   `setup.sh` drifts from the file on every edit until someone re-pastes it. The
   bootstrap is a stable stub: it clones/refreshes `Cursor-Governance` and then
   executes the canonical `setup.sh` from it, so edits to `setup.sh` on `main`
   propagate to every new session with **no re-paste**. (Pasting `setup.sh`
   directly still works — it's the same logic — but you own keeping it in sync.)
   Either way it is idempotent, auto-detects Python vs Node, clones governance to
   `$HOME/.cursor-governance`, provisions `pre-commit` (the `make pr` gate,
   CANONICAL_LAW §12), and then delegates all adapter wiring to `../install.sh`
   — the same installer CLI and Desktop use (see "One adapter" above).
4. **Per-repo (git-tracked, recommended)** — in each consumer repo commit the
   `.claude/` triad so the SessionStart hook boots governance from the clone (see
   the parent `README.md` §4). Committing is preferred: it is explicit, reviewable,
   and identical on CLI. **Not strictly required for Mobile/Web**, though —
   `install.sh` reconciles the `.claude/` triad from the governance clone into the
   workspace when a repo has not committed it, so every mobile chat self-activates
   either way. Reconciliation preserves consumer-local keys and never clobbers
   what the repo already committed.

## Verify (in a fresh session after saving)

```bash
gh auth status                                    # Logged in as <bot-user>
ls "$HOME/.cursor-governance/CANONICAL_LAW.md"    # governance clone present
echo "$L9_GOVERNANCE_SURFACE"                     # must print exactly: claude-code
echo "$L9_GOVERNANCE_DIR"                         # must be an expanded path, not '$HOME/...'
"$HOME/.cursor-governance/.venv/bin/python3" -c 'import pydantic, yaml, jsonschema'  # locked env
[ -n "$GRAPHITI_MCP_TOKEN" ] && echo "memory bearer present"
# Memory = Cursor Graphiti front door only (ADR-0006). Proves the write path:
python3 "$HOME/.cursor-governance/environment/agents/adapters/claude-code/hooks/memory_lock.py" \
  acquire --namespace cursor-governance --task "env smoke"
# The SessionStart hook should have injected an "L9 Governance — Claude Code session"
# context block listing the governance clone and available skills. A hydrate line
# reading DEGRADED with facts_returned=0 almost always means GRAPHITI_MCP_TOKEN is
# unset, or that the locked .venv above is missing so the gates cannot import.
```

## Shared memory (required for governed Mobile/Web)

Cloud sessions use HTTPS Graphiti reachability to the **same** store as Cursor:

`GRAPHITI_MCP_URL=https://memory.quantumaipartners.com/graphiti/mcp`

(`mcp.template.json` expands `${GRAPHITI_MCP_URL}` / `${GRAPHITI_MCP_TOKEN}`).
This is **not** the retired `L9_MEMORY_HTTP_*` side door (ADR-0006).
CLI hosts may set `GRAPHITI_MCP_URL=http://127.0.0.1:8100/mcp` via the SSH tunnel.

**Identity (shared graph, distinct author).** `group_id` is shared with Cursor.
Writing identity is not: `USER_ID=claude_code_agent` / `L9_MEMORY_AGENT_ID=claude-code`.

**Allowlist:** add `memory.quantumaipartners.com` (Custom) or use Full.

## Security

- Env vars are stored **in plaintext** in the environment config. Use a
  least-privilege dedicated bot account; rotate any token ever pasted in chat.
- Never commit `GH_TOKEN` / `GRAPHITI_MCP_TOKEN` / `SONAR_TOKEN` to a repo. A
  committed `.env` is a leaked secret. `.mcp.json` carries only `${...}`
  references, never the token itself.
