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
| `sonar.read_issues` | No brokered Sonar. `sonar_fetch.py` authenticates only with a `SONAR_TOKEN` the operator environment already supplies (2026-09-04 directive: resolve Sonar fully, never merge-blocking); otherwise public reads |
| `semgrep.appsec_scan`, `semgrep.mcp` | No authenticated AppSec; CE unaffected |
| `context7.mcp` | No library docs retrieval via the retired broker |
| `gitguardian.mcp` | No brokered secret scanning; `gitleaks` still runs locally |
| `github.mcp`, `github.packages_read` | Platform GitHub MCP (where connected) covers most of this |

## Observed GitHub transports

Rows are **dated and per-container measurements**, not a standing claim. A container
that contradicts a row is new evidence: add a dated row, do not silently rewrite an
old one. The contract these measure against lives in `ops/autonomy/surface_profile.yaml`
under `surface_capabilities.github`, and in rule 62's surface-transport section.

### 2026-08-29, re-verified 2026-08-30 — Claude Code cloud container, `Quantum-L9/Cursor-Governance`

First measured at `a2f78b5`; every row below re-probed unchanged at `450b7d0`.

| Probe | Result |
|---|---|
| `gh` binary | **present**, `/usr/bin/gh` v2.98.0 |
| `gh api user` | **works** — resolves `cryptoxdog` |
| `gh api repos/Quantum-L9/Cursor-Governance` | **works** |
| `mcp__github__*` tools | **work** |
| `gh auth status` | reports `The token in GH_TOKEN is invalid` — **and exits 0** |
| `gitleaks` | present, `/root/.local/bin/gitleaks` |
| `pre-commit` | present, `/root/.local/bin/pre-commit` |
| `uv` | present, `/root/.local/bin/uv` |
| `semgrep` | **absent** |

Two consequences worth stating plainly.

**`gh auth status` is a misleading detector.** It reports failure and exits 0. A script
branching on its exit code takes the success path while its own output says the
opposite, and a human reading only the text concludes GitHub is unreachable when the
REST route works. Probe the endpoint you need instead.

**The session prompt on this surface asserts there is no `gh` CLI.** That assertion is
false here, as the first row shows. It is harness-owned and there is no in-repo lever
for it (P307 CI-001 R1), so it is recorded rather than fixed: trust the probe, not the
prompt.

### 2026-08-31 — Claude Code cloud container, `Quantum-L9/Cursor-Governance` @ `a221142`

Re-probed while integrating this change. Every row above reproduces **except one**.

| Probe | Result | vs. the row above |
|---|---|---|
| `gh` binary | **present**, `/usr/bin/gh` v2.98.0 | same |
| `gh api user` | **works** — resolves `cryptoxdog`, exit 0 | same |
| `gh api repos/Quantum-L9/Cursor-Governance` | **works**, exit 0 | same |
| `gh auth status` | reports `The token in GH_TOKEN is invalid` — **and exits 1** | **contradicts** |
| `gitleaks` | present, `/root/.local/bin/gitleaks` | same |
| `pre-commit` | present, `/root/.local/bin/pre-commit` | same |
| `uv` | present, `/root/.local/bin/uv` | same |
| `semgrep` | **absent** | same |

The contradicting row is recorded, not merged into the earlier one, per the rule at the
top of this section. It does not weaken the conclusion drawn from it — it hardens it.
The earlier row supported "never gate on `gh auth status`" because the exit code
disagreed with the message. Two containers of the same surface class now return
**different** exit codes for the same message and the same working `gh api`, so the
exit code is not a stable signal in either direction, and a script gating on it fails
unpredictably rather than consistently.

What must not be read into this: the 2026-08-29/30 row is not retracted, and neither
row licenses asserting a mechanism. `gh api` succeeding while the session's own
`GH_TOKEN` is an invalid sentinel remains the only claim either row supports.

### 2026-09-04 — Claude Code cloud container, `Quantum-L9/Cursor-Governance` @ `a4a311e`

Probed during a `/l9-pr-remediation` Converge run over PRs #488 and #489.

| Probe | Result |
|---|---|
| `gh api user` | **works** — resolves `cryptoxdog` |
| `gh api graphql` (any query) | **403** — "only the pinned set of PR-review operations is served" |
| `gh pr list` / `gh pr view` | **403** — both are GraphQL clients |
| `gh api repos/{owner}/{repo}/pulls/{n}` | **works** |
| `gh api repos/{owner}/{repo}/rules/branches/main` | **works** — returns the org ruleset |
| `gh api repos/{owner}/{repo}/branches/main/protection` | **403** "Resource not accessible by integration" |
| `gh api repos/{owner}/{repo}/commits/{sha}/check-runs` | **works** |

**The consequence was a board that could never answer.** `ops/autonomy/pr_board.py`
is the merge authority, and two of its inputs were reachable only by routes this
container refuses: `_pr_view` called `gh pr view` (GraphQL), and
`protection_required` treated the 403 on classic protection as lost telemetry.
Either one alone degraded every verdict to `wait / telemetry unavailable`, so no
PR in the repo could ever be merged by the sanctioned path — an unclearable gate,
which teaches bypassing rather than safety.

Both are now fixed in the helper rather than worked around at the call site: the
view falls back to a REST reconstruction of the same nine fields, and an
unreadable classic-protection source is treated as naming nothing (rulesets still
answer, and GitHub's own `mergeStateStatus` still refuses BLOCKED). The fail-closed
property is unchanged — when *no* transport answers, the verdict is still
`BoardError` → `wait`, never `merge`.

What must not be read into this row: GraphQL being refused here is not a claim
that it is refused everywhere, and the REST fallback is not a licence to prefer
REST where GraphQL answers. The board tries GraphQL first and uses REST only when
that call fails.

### 2026-09-05 — Claude Code cloud container, `Quantum-L9/Cursor-Governance` @ `91daac4`

Probed during the mobile environment audit (`docs/CLAUDE_CODE_MOBILE_ENVIRONMENT_AUDIT.md`),
on a **12-repository container** rooted at `/home/user` rather than a single checkout.

| Probe | Result | vs. the rows above |
|---|---|---|
| `gh api user` | **works** — resolves `cryptoxdog`, exit 0 | same |
| `gh api repos/Quantum-L9/Cursor-Governance` | **works** — `default=main` | same |
| `git ls-remote origin main` | **works** — returns `91daac4…` | new probe |
| `gh auth status` | reports `The token in GH_TOKEN is invalid` — **and exits 1** | matches 2026-08-31, contradicts 2026-08-29/30 |
| `gitleaks` | present, `/root/.local/bin/gitleaks` | same |
| `pre-commit` | present, `/root/.local/bin/pre-commit` | same |
| `uv` | present, `/root/.local/bin/uv` v0.8.17 | same |
| `semgrep` | **absent** | same |

The exit code lands on `1` for the second time out of three measurements. That does not
resolve the split — it confirms the conclusion the 2026-08-31 row already drew: two
values have now been observed for the same message and the same working `gh api`, so the
exit code is unusable in either direction. Nothing here retracts the 2026-08-29/30 row.

**New in this row: the sentinel is measurably one value across five names.**
`GH_TOKEN`, `GITHUB_TOKEN`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and
`CLOUDSDK_AUTH_ACCESS_TOKEN` all hold a 14-character value with the identical SHA-256
prefix `f07d7417`. Five unrelated providers cannot share one credential, so this is a
placeholder occupying five credential-shaped names — not five degraded credentials. It
strengthens "`gh api` succeeds while the session's own `GH_TOKEN` is an invalid
sentinel" without asserting any mechanism for why.

The Graphiti row in the capability table above ("No bearer; session may be memory-blind")
also reproduces here: `GRAPHITI_MCP_TOKEN` is absent, the CLI adds `Authorization` only
when it is set, and the rendered `.mcp.json` carries `url` with no `headers` — which is
what `mcp.template.json` intends via `_optional_headers`. The audit's F-01 is therefore
scoped to the readiness receipt **labelling** that plane
`Graphiti_authenticated_health: READY`, not to the posture this row already
records. That label is now fixed: the dimension is `Graphiti_reachability`, and
a separate `graphiti_transport_auth` observation reports `UNAUTHENTICATED` here
from the presence of `GRAPHITI_MCP_TOKEN` — the same signal the client and
`mcp.template.json` already branch on. This row's posture is unchanged.

### Relationship to the P307 pack

`WIP/8-26-26/environment_experience_improvement_pack_p307_revised` records **CR-105**
("GH_TOKEN and GITHUB_TOKEN are set, but no gh CLI exists to consume them") and
**CR-124** ("Core CLI tooling absent; GitHub work rerouted — gh, gitleaks, semgrep,
pre-commit not installed"). Both carry `status: OBSERVED_CONTEXT_SPECIFIC`, and both
stand: they describe containers that were measured. The table above is a **dated
counter-observation for a different container**, not a correction of theirs. In this
one, `gh`, `gitleaks` and `pre-commit` are present and only `semgrep` is absent.

## The rule that does not bend

A capability reporting `UNAVAILABLE`, `DEGRADED`, or `BLOCKED_BY_PLATFORM` is
**never** a reason to paste a credential into this surface. Not `SONAR_TOKEN`,
not `SEMGREP_APP_TOKEN`, not `INFISICAL_CLIENT_SECRET`, not a Graphiti bearer.
Everything an LLM can execute can read that LLM's environment. An unavailable
capability is a delivery problem; a pasted secret is a permanent compromise on
this surface.
