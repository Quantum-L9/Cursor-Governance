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

### CI-parity scanners

The Setup script also installs the scanners CI runs, at CI's versions, from the
one pin manifest `ops/ci_parity/tools.yaml` (sha256-verified): CodeQL, Semgrep
(incl. the Pro policy via `semgrep ci --dry-run`), Biome, pip-audit, plus
actionlint, zizmor, shellcheck, osv-scanner and yamllint. SessionStart reinstalls
a missing or off-pin tool in the background. Nothing to paste: they run on their own.

| When | What runs | Blocks? |
|---|---|---|
| After each Edit/Write | fast lanes on that file (findings returned to the agent) | no |
| After each commit | every lane, in the background, in a snapshot clone | no — writes a receipt |
| Before a push (`git push`, `make pr`) | reuses the commit's receipt | only a NEW CI-blocking finding on a changed line |
| After a push | SonarCloud PR quality gate + issues, read-only | no |

`L9_CI_PARITY=0` disables all of it for a session. Details and the parity proof:
`ops/ci_parity/README.md`; doctrine: `AGENTS.md` CI_PARITY_HOSTED_CLAUDE_V1.

### Secrets: one machine identity, everything else bound from Infisical

Infisical project `cursor-governance` is the secret vault, and this surface
reaches it with no AWS (2026-09-24; Cursor keeps its own AWS login seed). The account environment carries exactly **one**
credential: this surface's Infisical machine identity,
`L9_INFISICAL_CLIENT_SECRET`, beside the non-secret `L9_INFISICAL_CLIENT_ID`.
Anthropic stores the variables field in plaintext and the model can read it, so
that identity is dedicated to this surface, least-privilege, and revocable in
Infisical without touching any other surface. It is never an operator's or
another agent's identity.

Every other secret is bound in-process by `ops/secrets/capability_bind.py` as
that identity and never exported. A remote MCP server that needs a key is a
local vault bridge (`ops/secrets/vault_mcp_bridge.py`), so Context7 needs no
header and no pasted key.

```bash
# names and sources only — never a value
"$HOME/.cursor-governance/.venv/bin/python" \
  "$HOME/.cursor-governance/ops/secrets/capability_bind.py" --check CONTEXT7_API_KEY SONAR_TOKEN
```

Raw secret export (`hydrate --export`) is **denied** on this surface. An
unbound name is fixed in Infisical (or by setting this surface's identity) —
never by pasting that secret into the variables field to turn a check green.

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
   Authenticated Sonar/Semgrep stay operator-side. The capability broker
   (`L9_CAPABILITY_BROKER_URL`) never shipped — do not set it. Memory is the
   bound stdio control plane (`L9_MEMORY_INTERPRETER`). Do not set
   `GRAPHITI_MCP_URL`.
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
# Memory readiness is layered (R0..R9); there is no provider URL and no bearer.
"$HOME/.cursor-governance/.venv/bin/python3" -m ops.memory.diagnostics --workspace "$PWD"
```

## Shared memory (required for governed Mobile/Web)

Cloud sessions reach the **same** canonical memory as Cursor: the
`l9-graphite-memory` control plane (`MemoryService`, `memory-control-plane/v1`),
bound per checkout by `ops/config/memory-binding.json` and proven by
`ops/memory/runtime_binding.py`. The session hooks (`memory_prefetch.py`,
`memory_writeback.py`) hydrate and close through `ops/memory`; the only MCP
memory server `mcp.template.json` declares is the package-owned stdio entry,
rendered when `L9_MEMORY_INTERPRETER` names a Python carrying the pinned
package. The direct-provider front door (`graphiti-memory` over a provider URL)
was retired at realignment stage C8; the capability broker never shipped; the
`L9_MEMORY_HTTP_*` side door is retired (ADR-0006).

**Honest posture:** there is no memory credential to paste. A memory bearer in
the variables field is a contract violation, not a configuration.

**Identity (shared namespace, distinct author).** The repository namespace is
shared with Cursor. Writing identity is not: `USER_ID=claude_code_agent` /
`L9_MEMORY_AGENT_ID=claude-code`.

**Allowlist:** the memory package is installed from GitHub
(`Quantum-L9/l9-graphiti-memory`); allow `github.com` or use Full.

## Security

- Env vars are stored **in plaintext** and are readable by the model. This
  environment carries **no** Infisical password, UA secret, PAT, or Graphiti bearer.
- Never commit those names to a repo. `.mcp.json` carries only `${...}`
  references, never a token.
