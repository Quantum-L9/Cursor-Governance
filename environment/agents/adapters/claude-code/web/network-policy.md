# Network access — L9 Claude Code cloud environment (Web · Mobile)

Paste guidance for claude.ai/code → environment → Network access.
Same environment is used by Web, Mobile, Desktop cloud, and `claude --cloud`.

## Option A — Full (fastest proof)

Network access → **Full**.

## Option B — Custom (least privilege)

Network access → **Custom**, include the default package-manager list, plus the
hosts below. Every entry is justified by a capability the adapter actually
invokes — nothing is listed speculatively. Drop a host and you disable exactly
the capability named beside it.

```
github.com
*.githubusercontent.com
api.github.com
codeload.github.com
cli.github.com
objects.githubusercontent.com
pypi.org
files.pythonhosted.org
registry.npmjs.org
astral.sh
*.astral.sh
semgrep.dev
*.semgrep.dev
app.infisical.com
mcp.context7.com
sonarcloud.io
api.osv.dev
```

Amended 2026-09-24 (`AGENTS.md` INFISICAL_MACHINE_IDENTITY_V1 and
CI_PARITY_HOSTED_CLAUDE_V1): the hosted surface binds its secrets from Infisical
as its own least-privilege machine identity, so `app.infisical.com` is required;
the CI-parity scanners add `sonarcloud.io` (read-only) and `api.osv.dev`.

### Host → owning capability

| Host | Capability that requires it |
|---|---|
| `github.com`, `codeload.github.com`, `*.githubusercontent.com` | governance clone/fetch; `pre-commit` hook repos; **gitleaks release download** (`install.sh` pins 8.24.3) |
| `api.github.com` | `gh` auth, PR/CI reads, `l9-pr-remediation` |
| `cli.github.com` | `gh` apt package install |
| `objects.githubusercontent.com` | GitHub release asset redirects (gitleaks tarball) |
| `pypi.org`, `files.pythonhosted.org` | `uv sync --locked` (governance `uv.lock`), `uvx` for bandit / semgrep / pip-audit, `pre-commit`, `uv` itself |
| `astral.sh`, `*.astral.sh` | `uv`-managed CPython download when the sandbox lacks the pinned interpreter (`.python-version` = 3.12). Not needed when a system 3.12 is already present |
| `registry.npmjs.org` | consumer workspaces with `package.json` |
| _(none for memory)_ | Since realignment stage C9/C11 memory is the canonical `l9-graphite-memory` control plane over **stdio** to the bound runtime (`ops/memory`); the session opens no memory HTTPS egress and holds no memory bearer. `memory.quantumaipartners.com` is no longer required (ADR-0030) |
| `semgrep.dev`, `*.semgrep.dev` | Semgrep registry rulesets (`p/python`, `p/secrets`) for CE, and the org policy for the Semgrep Pro `semgrep ci --dry-run` lane (`ops/secrets/capability_exec.py`; no scan is created) |
| `app.infisical.com` | Machine-identity login + in-process secret binds (`capability_bind.py`, `vault_mcp_bridge.py`) |
| `mcp.context7.com` | Context7 docs through the vault-bound stdio bridge |
| `sonarcloud.io` | Read-only PR quality gate / issues (`ops/ci_parity/sonar_status.py`); never a scanner run |
| `api.osv.dev` | `osv-scanner` vulnerability lookups for changed lockfiles (`ops/ci_parity`) |
| `github.com` release assets (via `*.githubusercontent.com`) | CI-parity tool downloads pinned by sha256 in `ops/ci_parity/tools.yaml` (CodeQL bundle, actionlint, shellcheck, osv-scanner, Biome) |

### Egress the agent must not need (contract §16)

Least privilege is a second, independent line of defence behind the capability
architecture. Even with no credential in the environment, an agent container
that can reach a secret backend is one mistake away from using one.

| Host | Who reaches it | Why not the agent |
|---|---|---|
| AWS Secrets Manager endpoints | **nobody** | The AWS bootstrap path is removed entirely (contract S1). Do not re-add it |

Broker egress allow-list (if a broker is ever deployed — it is **not** the
Graphiti health plane): `app.infisical.com`, `sonarcloud.io`, `semgrep.dev`,
plus any host a newly registered capability declares. The retired Graphiti
host is not on it. Native Memory Streamable HTTP is the selected transport,
but its issuer and resource host are UNKNOWN until verified and must not be
invented onto this list.

### Deliberately absent

- **AWS Secrets Manager endpoints** — the AWS credential bootstrap is removed,
  not merely unused. Agent surfaces must never obtain Universal Auth credentials
  from an instance profile (contract S1).
- Any host not tied to a capability above. Do not widen this list to make a
  test pass — a capability that cannot reach its host must report DEGRADED.

### Historical — not required, do not allowlist

- `memory.quantumaipartners.com` — the retired HTTPS Graphiti projection
  (`/graphiti/mcp`). Keep this host out of every agent allowlist. It is not
  the Memory 3.0 native MCP endpoint. Native Streamable HTTP's host is
  UNKNOWN until verified (CANONICAL_LAW §8.10). Absence of a host here is
  not proof that a stdio server needs no egress, and it is not a reason to
  put stdio back. Raw provider HTTP stays forbidden.
