# Degraded-mode contract — what still works with zero brokered capabilities

**Findings:** mobile bootstrap audit B-09, B-10
**Status:** in force on every Anthropic-hosted (`cloud_default`) session

Every brokered capability on this surface currently reports
`BLOCKED_BY_PLATFORM`. That is not a misconfiguration and not an outage, and no
environment field will change it. This document says exactly what remains valid,
so the answer is written down rather than rediscovered by trial.

## <a id="hosted-surface-identity"></a>Why: the hosted surface issues no session identity

`ops/secrets/capability_client.py` accepts two proofs of identity:

1. a `ccpool_*` session JWT — self-hosted Claude Code Remote pools only
2. a projected workload identity (Kubernetes SA, SPIFFE JWT-SVID)

An Anthropic-hosted `cloud_default` environment issues **neither**. The broker
therefore has nothing to verify, and the only way to give it something would be
to place a reusable secret in a model-controlled sandbox — which is the exact
posture the capability architecture exists to remove.

So the block is structural. It holds regardless of `L9_CAPABILITY_BROKER_URL`,
regardless of whether the broker is deployed, and regardless of network policy.
It is reported as `BLOCKED_BY_PLATFORM` (exit 4) and never as "no broker
configured" (exit 3), because those call for different actions and only one of
them is achievable.

**Tracking:** this needs a platform-side session-identity mechanism, or an L9
self-hosted `ccpool_*` environment. Both are outside this repository.

## Compounding: the broker host is not deployed

`broker.quantumaipartners.com` has **no DNS record**. Verified by contrast:
`sonarcloud.io`, `semgrep.dev`, `context7.com` and `memory.quantumaipartners.com`
all resolve from the same runtime; the broker host raises `gaierror` locally and
`502 CONNECT` through the egress gateway.

This is a second, independent blocker. Fixing it alone would not enable a single
capability, because the identity gap above still applies.

```bash
python3 ops/secrets/probe_broker.py        # tells the two apart
```

## What IS valid in degraded mode

This is the supported operating envelope, not a list of things that happen to
work today.

| Works | Notes |
|---|---|
| `git` fetch/push | Anthropic's git proxy authenticates; no PAT anywhere |
| `gh api` (REST) | Proxy-injected. `gh auth status` reports a false negative — use `gh api user` |
| `uv`, `uv sync --locked` | The locked toolchain is the SSOT and needs no broker |
| `pre-commit` | The CANONICAL_LAW §12 gate |
| `node`, `npm` | Public registry only |
| Local `semgrep` CE, `bandit`, `pip-audit` | Credential-free rulesets |
| `gitleaks` | Once provisioned; the security gate fails closed without it |
| Every `l9-*` skill that does not call a capability | |

| Does not work | Consequence |
|---|---|
| `gh pr view/list/checks/merge` (GraphQL) | Session gateway returns 403 — use `gh api` REST |
| Autonomous merge | `gh pr merge` is GraphQL, so it 403s here anyway; and there is no autonomous-merge env boolean — merge needs the scoped `/l9-pr-remediation` receipt (or human `L9_MERGE_AUTHORIZED`) |
| `sonar.read_issues` | No authenticated Sonar; public reads only |
| `semgrep.appsec_scan`, `semgrep.mcp` | No authenticated AppSec; CE unaffected |
| `context7.mcp` | No library docs retrieval |
| `gitguardian.mcp` | No brokered secret scanning; `gitleaks` still runs locally |
| `github.mcp`, `github.packages_read` | Platform GitHub MCP is connected and covers most of this |

## The rule that does not bend

A capability reporting `DEGRADED` or `BLOCKED_BY_PLATFORM` is **never** a reason
to paste a credential into this surface. Not `SONAR_TOKEN`, not
`SEMGREP_APP_TOKEN`, not `INFISICAL_CLIENT_SECRET`, not a Graphiti bearer.
Everything an LLM can execute can read that LLM's environment. A degraded
capability is a delivery problem on the trusted side; a pasted secret is a
permanent compromise on this one.
