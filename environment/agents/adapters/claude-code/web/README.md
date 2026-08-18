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
| **Environment variables** | `environment.env.example` | surface/memory/autonomy posture only — **no credentials** |
| **Setup script** | `setup.bootstrap.sh` | normalize the environment, clone governance, then exec the canonical `setup.sh` from that clone |

## One adapter, thin surface callers

There is a single installer — `../install.sh` — and every surface reaches it:

```
Web / Mobile / --cloud   setup.bootstrap.sh ─→ web/setup.sh ─→ ../install.sh
CLI / Desktop            make claude-install ──────────────-─→ ../install.sh
```

`install.sh` owns the Claude-specific vendor wiring: the settings triad, skill
discovery, the `.claude/rules` LLM rules mount, the `.mcp.json` front door, and
excludes for the generated `.claude` mirrors. The shared bootstrap
(`ops/scripts/bootstrap_agent_environment.sh`) owns toolchain, checker binaries,
secrets, repo identity, and preflight. The surface callers own only what their
surface uniquely needs — for the cloud that is `gh`, credentials, cloning
governance, and the consumer repo's own language toolchain. **Add adapter
behaviour to `install.sh`, not to a caller**, or the surfaces drift apart again.

`make claude-install-check` reports drift read-only, writing nothing.

### Dependencies and tool versions

`uv.lock` in this repo is the only source of interpreter and dependency
versions. The shared bootstrap (`ops/scripts/bootstrap_agent_environment.sh`,
called by `install.sh`) applies it through the existing wrapper,
`ops/scripts/ensure_uv_environment.sh` (`uv sync --locked --extra dev`,
fingerprint-cached so a re-run is a no-op). It never installs a package by
name, and `validate_claude_env.py` fails any adapter script that tries.

That wrapper produces `$HOME/.cursor-governance/.venv/bin/python3` — the
interpreter `ops/graphiti`, `ops/autonomy`, and `memory/graphiti_bridge.py`
already resolve to. It matters that it exists: the sandbox's system `python3` is
3.11, while `.python-version` and `requires-python` pin ≥3.12, so without the
locked venv the memory gate cannot import its brain and governed writes are
denied.

### Secrets, and why this environment carries none

The account environment carries **no credentials at all**. Anthropic stores the
variables field in plaintext and everything in it is readable by the model, so a
token there is a token the model possesses — including `INFISICAL_CLIENT_SECRET`,
which would be a master key to the entire inventory.

Authenticated work resolves through the shared **capability plane** instead. The
session asks for a named capability; a trusted broker holds the credential and
returns only sanitized results. `ops/secrets` remains the SSOT.

```bash
# capability names and status only — there is no value-returning call here
python3 ops/secrets/bootstrap_agent_env.sh --check --surface claude-code \
  --require-capabilities sonar.read_issues,semgrep.appsec_scan,graphiti.query
```

Raw secret export is **denied** on this surface, and on every unregistered
surface. If a capability is unavailable, the fix is broker delivery — never
pasting a credential into the variables field to turn a check green.

Two things are deliberately **absent** from the variables field because they
name one repository while the environment is reused across many:

- `GRAPHITI_GROUP_ID` — `group_registry.yaml` resolves in the order
  `[explicit_env, git_remote_match, path_hint_match]`, so setting it here files
  every repo's memory under one group.
- `SONAR_PROJECT_KEY` / `SONAR_ORG_KEY` — `install.sh` derives them from the
  active `sonar-project.properties` and clears them when the workspace has none.

Breakglass keys (merge, push bypass, reset/revert/switch, broad-add, memory
enforcement) are listed in the template as documented-but-unset. Setting one in
the account environment makes the bypass permanent for every session.

> **The variables field is literal text — no shell expansion.** `FOO=$HOME/x` is
> stored as the characters `$HOME/x`. Never reference `$HOME` there; that is why
> `L9_GOVERNANCE_DIR` is deliberately absent from `environment.env.example` (the
> SSOT path is hard-pinned by `setup.sh` and the SessionStart hook instead).

## Steps

1. **Network access** — pick **Full** (simplest) or **Custom** + the allowlist in
   `network-policy.md`.
2. **Environment variables** — paste `environment.env.example` **as-is**. Do not
   replace anything with Infisical UA, Infisical password, a PAT, or
   `GRAPHITI_MCP_TOKEN`. `GH_TOKEN=proxy-injected` is a marker, not a secret.
   Authenticated work uses the capability broker (`L9_CAPABILITY_BROKER_URL`),
   which holds Infisical credentials on the trusted side.
3. **Setup script** — **paste `setup.bootstrap.sh` (recommended), not `setup.sh`.**
   The account field is a *copy*, not a live link to the repo, so pasting the full
   `setup.sh` drifts from the file on every edit until someone re-pastes it. The
   bootstrap is a stable stub: it clones/refreshes `Cursor-Governance` and then
   executes the canonical `setup.sh` from it, so edits to `setup.sh` on `main`
   propagate to every new session with **no re-paste**. (Pasting `setup.sh`
   directly still works — it's the same logic — but you own keeping it in sync.)
   Either way it is **machine-level provisioning only**: it installs `gh`,
   clones/refreshes governance at `$HOME/.cursor-governance`, establishes the
   locked governance venv (via the shared bootstrap inside `../install.sh`),
   and delegates all adapter wiring to `../install.sh` — the same installer CLI
   and Desktop use (see "One adapter" above). It does **not** install consumer
   repository dependencies and does **not** warm `pre-commit`: the account
   environment is cached (~7 days) and does not re-run per session, so that
   per-repository work lives in the committed SessionStart path
   (`hooks/session_deps_cloud.sh`, invoked by the SessionStart hook on every
   session and resume).
4. **Per-repo (git-tracked, REQUIRED)** — in each governed consumer repo commit
   the `.claude/` triad (`.claude/settings.json` + `.claude/hooks/`) so the
   SessionStart hook boots governance from the clone (see the parent `README.md`
   §4). Committed wiring is **required** for Web/Mobile, not optional: cloud
   SessionStart hooks come from project files or managed settings, and
   machine-level `~/.claude` hooks do not follow you into Anthropic cloud
   sessions. The account Setup script cannot reliably repair missing per-repo
   wiring because it is environment provisioning and may be cached for ~7 days
   without re-running. `install.sh` reconciliation remains as a repair fallback
   when a repo has not committed the triad — it preserves consumer-local keys
   and never clobbers what the repo already committed — but a governed repo
   should treat missing committed wiring as drift, not a supported posture.

## Verify (in a fresh session after saving)

```bash
ls "$HOME/.cursor-governance/CANONICAL_LAW.md"    # governance clone present
echo "$L9_GOVERNANCE_SURFACE"                     # must print exactly: claude-code
echo "$L9_GOVERNANCE_DIR"                         # must be an expanded path, not '$HOME/...'
"$HOME/.cursor-governance/.venv/bin/python3" -c 'import pydantic, yaml, jsonschema'  # locked env
# Same capability check every surface runs (names only — no secret values):
bash "$HOME/.cursor-governance/ops/secrets/bootstrap_agent_env.sh" --check \
  --surface claude-code --require-capabilities sonar.read_issues,semgrep.appsec_scan,graphiti.query
# SessionStart injects "L9 Governance — Claude Code session". DEGRADED hydrate
# with broker unset is the honest posture — do not paste GRAPHITI_MCP_TOKEN.
```

## Shared memory (required for governed Mobile/Web)

Cloud sessions reach the **same** Graphiti store as Cursor through the brokered
front door. `mcp.template.json` points `graphiti-memory` at
`${L9_CAPABILITY_BROKER_URL}/mcp/graphiti` — the L9 capability broker
(`graphiti.query`) — and carries **no bearer**: the broker resolves the
Graphiti credential on its trusted side and proxies to
`memory.quantumaipartners.com/graphiti/mcp`. This is **not** the retired
`L9_MEMORY_HTTP_*` side door (ADR-0006).

**Honest posture when the broker is unreachable or has no authenticated
identity for this session:** memory reports `DEGRADED` (broker identity
unavailable). Do **not** paste a Graphiti bearer into the variables field to
turn that green — the fix is broker delivery, never a static secret.

**Identity (shared graph, distinct author).** `group_id` is shared with Cursor.
Writing identity is not: `USER_ID=claude_code_agent` / `L9_MEMORY_AGENT_ID=claude-code`.

**Allowlist:** add `memory.quantumaipartners.com` (Custom) or use Full.

## Security

- Env vars are stored **in plaintext** and are readable by the model. This
  environment carries **no** Infisical password, UA secret, PAT, or Graphiti bearer.
- Never commit those names to a repo. `.mcp.json` carries only `${...}`
  references, never a token.
