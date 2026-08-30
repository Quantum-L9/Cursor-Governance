# Degraded-mode contract — what still works with the capability broker retired

**Findings:** mobile bootstrap audit B-09, B-10; capability-broker retirement 2026-08-29
**Status:** in force on every model-controlled surface

The capability-broker experiment **never shipped**. `capability_client.py`
reports every registered capability `UNAVAILABLE`. That is not a
misconfiguration and not an outage, and no environment field will change it.
This document says exactly what remains valid.

## <a id="hosted-surface-identity"></a>Why: the broker is gone, not waiting

The former architecture needed a platform-issued session identity the broker
could verify (`ccpool_*` JWT or a projected workload identity). An
Anthropic-hosted `cloud_default` environment issues neither. Independently,
`broker.quantumaipartners.com` was never deployed.

Retirement closes both questions: do not set `L9_CAPABILITY_BROKER_URL`, do not
probe a never-shipped host, and do not paste a reusable secret into a
model-controlled sandbox to "enable" Sonar / Semgrep / Context7.

Graphiti memory uses `${GRAPHITI_MCP_URL}` (default
`https://memory.quantumaipartners.com/graphiti/mcp`) with **no bearer**. Cursor
on this machine may still use the SSH tunnel at `127.0.0.1:8100`.

Archived implementation: `ops/secrets/_archived/capability-broker/RETIRED.md`.

## What IS valid

This is the supported operating envelope, not a list of things that happen to
work today.

| Works | Notes |
|---|---|
| `git` fetch/push | Anthropic's git proxy authenticates; no PAT anywhere |
| `gh api` (REST) | Proxy-injected. `gh auth status` reports a false negative — use `gh api user` |
| `uv`, `uv sync --locked` | The locked toolchain is the SSOT and needs no broker |
| `pre-commit` | The CANONICAL_LAW §12 gate |
| `node`, `npm` | Public registry always. `@quantum-l9/*` on GitHub Packages uses `gh auth token` (`ops/secrets/gh_npm.sh`); do not paste `NODE_AUTH_TOKEN` |
| Local `semgrep` CE, `bandit`, `pip-audit` | Credential-free rulesets |
| `gitleaks` | Once provisioned; the security gate fails closed without it |
| Every `l9-*` skill that does not call a capability | |
| Graphiti MCP at `GRAPHITI_MCP_URL` | No bearer; session may be memory-blind |

| Does not work | Consequence |
|---|---|
| `gh pr view/list/checks/merge` (GraphQL) | Session gateway returns 403 — use `gh api` REST |
| Autonomous merge | `gh pr merge` is GraphQL, so it 403s here anyway; and there is no autonomous-merge env boolean — merge needs the scoped `/l9-pr-remediation` receipt (or human `L9_MERGE_AUTHORIZED`) |
| `sonar.read_issues` | No authenticated Sonar; public reads only |
| `semgrep.appsec_scan`, `semgrep.mcp` | No authenticated AppSec; CE unaffected |
| `context7.mcp` | No library docs retrieval via the retired broker |
| `gitguardian.mcp` | No brokered secret scanning; `gitleaks` still runs locally |
| `github.mcp`, `github.packages_read` | Platform GitHub MCP (where connected) covers most of this |

## The rule that does not bend

A capability reporting `UNAVAILABLE`, `DEGRADED`, or `BLOCKED_BY_PLATFORM` is
**never** a reason to paste a credential into this surface. Not `SONAR_TOKEN`,
not `SEMGREP_APP_TOKEN`, not `INFISICAL_CLIENT_SECRET`, not a Graphiti bearer.
Everything an LLM can execute can read that LLM's environment. An unavailable
capability is a delivery problem; a pasted secret is a permanent compromise on
this surface.
