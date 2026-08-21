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
memory.quantumaipartners.com
semgrep.dev
*.semgrep.dev
broker.quantumaipartners.com
```

`broker.quantumaipartners.com` is this deployment's capability broker — the host
behind `L9_CAPABILITY_BROKER_URL` and therefore behind every authenticated
capability. It belonged in the table below from the start but not in this block,
so pasting Option B verbatim silently disabled the entire capability plane while
the table said the host was required. Substitute your own broker hostname if
your deployment uses a different one; do not delete the line.

**`app.infisical.com` and `sonarcloud.io` are deliberately NOT in this list.**
See "Egress the agent must not need" below — an agent container that can reach
a secret backend is one bad line away from using it.

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
| `memory.quantumaipartners.com` | Graphiti front door. Needed only where the broker is not yet fronting `/graphiti/mcp`; once `L9_CAPABILITY_BROKER_URL` is set, the broker reaches it and the agent does not |
| `semgrep.dev`, `*.semgrep.dev` | Semgrep **registry rulesets** (`p/python`, `p/secrets`) for local CE only. Authenticated AppSec runs in the trusted worker, not here |
| `broker.quantumaipartners.com` (or your deployment's broker hostname) | every authenticated capability (`sonar.read_issues`, `semgrep.appsec_scan`, `graphiti.*`). Present in the Option B block above — keep the two in step |

### Egress the agent must not need (contract §16)

Least privilege is a second, independent line of defence behind the capability
architecture. Even with no credential in the environment, an agent container
that can reach a secret backend is one mistake away from using one.

| Host | Who reaches it | Why not the agent |
|---|---|---|
| `app.infisical.com` | **broker only** | The secret backend. The agent holds no Infisical credential and has no reason to speak to it; blocking egress makes that structural rather than conventional |
| `sonarcloud.io`, `*.sonarcloud.io` | **broker only** | Authenticated Sonar reads are brokered. Unauthenticated public reads still work if you choose to allow the host; the token never leaves the broker either way |
| `semgrep.dev` authenticated API | **trusted worker only** | CE rule downloads are fine from the agent; authenticated AppSec is not |
| AWS Secrets Manager endpoints | **nobody** | The AWS bootstrap path is removed entirely (contract S1). Do not re-add it |

Broker egress allow-list (applied to the broker's own network policy, not this
one): `app.infisical.com`, `memory.quantumaipartners.com`, `sonarcloud.io`,
`semgrep.dev`, plus any host a newly registered capability declares.

### Deliberately absent

- **AWS Secrets Manager endpoints** — the AWS credential bootstrap is removed,
  not merely unused. Agent surfaces must never obtain Universal Auth credentials
  from an instance profile (contract S1).
- Any host not tied to a capability above. Do not widen this list to make a
  test pass — a capability that cannot reach its host must report DEGRADED.

`memory.quantumaipartners.com` is required for HTTPS Graphiti (`/graphiti/mcp`).
MCP connectors routed through Anthropic may not need allowlisting; keep the host
for setup probes and `.mcp.json` HTTP clients.
