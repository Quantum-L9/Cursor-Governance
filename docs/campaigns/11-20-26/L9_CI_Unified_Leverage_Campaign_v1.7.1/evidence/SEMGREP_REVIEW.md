# Semgrep AppSec Platform review (2026-11-20)

Sources: the operator's screenshots of `semgrep.dev/orgs/l9_ci_constellation` (operator-reported), and a read-only
Semgrep Web API read by the CTO session with the vault-bound `SEMGREP_APP_TOKEN` (observed). Nothing was changed.

## Account

| Fact | Value | Basis |
|---|---|---|
| Organization | `l9_ci_constellation`, deployment 103775 | observed |
| Plan | Free. 1 of 10 contributors used. No paid product selected. AI features shown as paused. | operator-reported |
| Free entitlement | Code and Supply Chain free for 10 or fewer contributors; 60 AI credits a month; no contributor limit on public projects | Semgrep usage docs (Context7 `/websites/semgrep_dev`) |
| Source control | GitHub private app for `Quantum-L9`, connected. Auto-scan of new repositories is off. | operator-reported |
| Projects | 41 via API. All six `Quantum-L9` campaign repositories are managed-scan projects, scanned on 2026-11-20. `cryptoxdog/IB-Odoo_19` is not in this organization. | observed |
| PR scans | Diff scans on every pull request, about 40 seconds, posted as `semgrep-cloud-platform/scan`. No ruleset lists that check as required, so it is advisory. Fail-open after 5 minutes. | observed (EIE job list), operator-reported |
| Custom rules, memories, workflows, integrations | none | operator-reported |
| Remediation policy | "Block malicious dependencies": block merge and comment. It cannot block a merge while the check is not required. | operator-reported |
| AI data flow | Multimodal on; providers AWS Bedrock, Cloudflare Workers AI, OpenAI, with zero data retention. Upgrade Guidance (forwards first-party code) off. | operator-reported |

Two Semgrep paths exist and are not duplicates in authority. Core's central `Analyze (central Core)` runs governed
rules and is the required gate. The hosted platform runs registry rules, Supply Chain and AI detection, and is advisory.

## Open findings on `main`, campaign repositories (observed)

| Repository | Code findings | High | Supply Chain |
|---|---|---|---|
| .github | 13 | 1 | 0 |
| Cognitive.Engine.Graphs | 9 | 4 | 0 |
| Cursor-Governance | 17 | 1 | 84 (7 critical, 47 high) |
| Enrichment.Inference.Engine | 111 | 12 | 0 |
| l9-ci-core | 0 | 0 | 0 |
| l9-ci-sdk | 5 | 4 | 0 |

## Disposition of the high and actionable findings

| Finding | Where | Verdict | Owner, action |
|---|---|---|---|
| `github-actions-mutable-action-tag`, 85 | EIE workflows | real | lane F2b: pin to full SHAs |
| `run-shell-injection` | EIE `perplexity-code-review.yml` 96, 135, 165 | real pattern; `workflow_dispatch` only, so not exploitable by outsiders | lane F2b: move to `env:` |
| `run-shell-injection` | CEG and EIE `k8s-deploy.yml` | pattern only: `workflow_dispatch`, values are repository metadata, `vars` and a dispatch input | no change to a deploy workflow; accepted, low |
| `python37-compatibility-importlib2`, 4 | SDK | false positive: `requires-python >=3.11` | operator: disable the rule in Policies |
| `sqlalchemy-execute-raw-query` | Cursor-Governance `host_bridge.py:128`, EIE migration 002 | false positive: identifiers are module literals | operator: triage as false positive |
| `github-script-injection` | .github `governance-pr.yml` | false positive: the input reaches the script through `env:` | operator: triage as false positive |
| `python-logger-credential-disclosure` | CEG `chassis/auth/auth.py:197` | false positive: logs method, path and client, not the token | operator: triage as false positive |
| `github-actions-mutable-action-tag` on `Quantum-L9/l9-ci-core/...@v2` | CEG, EIE | policy question, not a defect | Core owner: decide moving major tag versus SHA |
| `uv-missing-dependency-cooldown` | CEG, Cursor-Governance, EIE `pyproject.toml` | real hardening gap | Core owner: one uv cooldown policy for all consumers |
| Supply Chain: `pillow>=10.0.0`, `playwright>=1.41.0` floors; `virtualenv` 21.14.7 | Cursor-Governance | real | lane N1b (T24) |
| AI-detected AUTHZ and IDOR groups | EIE, Constellation.Gate | not triaged; AI features paused | UNKNOWN until triaged |
| certifi critical, reachable | l9-repo-template, l9-node-template, l9-dependency-template, l9-ci-debt-lsp | outside the campaign's seven repositories | repository owners |

Medium findings not listed above are not individually triaged here.
