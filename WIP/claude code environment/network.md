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
app.infisical.com
sonarcloud.io
*.sonarcloud.io
semgrep.dev
*.semgrep.dev
```

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
| `memory.quantumaipartners.com` | Graphiti front door (`/graphiti/mcp`) — SessionStart hydrate, phase-lock, governed writes |
| `app.infisical.com` | canonical secret provider (`ops/secrets/hydrate_infisical.py`) — Universal Auth login + secret read |
| `sonarcloud.io`, `*.sonarcloud.io` | Sonar issue fetch in `l9-pr-remediation` (`sonar_fetch.py`) |
| `semgrep.dev`, `*.semgrep.dev` | Semgrep registry rulesets (`p/python`, `p/secrets`) and **authenticated** Semgrep AppSec when `SEMGREP_APP_TOKEN` is resolved. Local CE scanning of already-cached rules does not need it |

### Deliberately absent

- **AWS Secrets Manager endpoints** — the cloud surface bootstraps through
  Infisical Universal Auth, not the AWS CLI. `hydrate_infisical.py` still falls
  back to AWS where an operator has it configured; add
  `secretsmanager.us-east-1.amazonaws.com` only if you use that path.
- Any host not tied to a capability above. Do not widen this list to make a
  test pass — a capability that cannot reach its host must report DEGRADED.

`memory.quantumaipartners.com` is required for HTTPS Graphiti (`/graphiti/mcp`).
MCP connectors routed through Anthropic may not need allowlisting; keep the host
for setup probes and `.mcp.json` HTTP clients.
