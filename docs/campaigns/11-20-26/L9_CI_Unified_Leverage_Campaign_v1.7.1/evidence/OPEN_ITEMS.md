# Open items register

Campaign `L9-CI-UNIFIED-LEVERAGE-2026-11-20-v1.7.1`. Kept by the CTO session. It extends the findings
register in `09_EXECUTION_BINDING.md` (T01 to T16) with what the launch, the first swarm check-in and
the operator walkthrough (G0) found on 2026-11-20. Nothing here is closed by being listed.

Each row has one owner and one next action. Sources are marked `observed` (the CTO read it),
`operator-reported` (a screen the operator showed) or `lane` (a pool agent's report). This repository
is public, so rows about credentials carry counts and actions only, never locations or values.

## Security, do first

| ID | Item | Source | Owner | Next action | State |
|---|---|---|---|---|---|
| T17 | Cursor-Governance has 7 open secret-scanning alerts (4 provider-pattern, 3 generic), untriaged. The repository was made public on 2026-11-20, so history is readable. | operator-reported | operator, with the CTO | Triage each alert in the GitHub Security tab. Revoke and rotate every real credential and treat it as exposed. Dismiss false positives with a reason. The CTO session cannot read these alerts. | OPEN, P0 |
| T18 | Private repositories' source was readable on SonarCloud without login: 13 confirmed projects, 4 of unknown origin, and 2 stale snapshots in the old personal organization. | observed | CTO | Closed 2026-11-20: 17 projects set private, 2 stale projects deleted, anonymous re-check shows only projects whose GitHub repository is public. | FIXED_PROVEN |
| T19 | Sonar auto-import of new GitHub repositories is on, and automatic analysis is the default for new projects. That is how T18 happened. | operator-reported | operator | Turn off "Automatically import new GitHub repositories" in the Sonar organization binding. No documented API call was found. | OPEN |
| T20 | Push-protection bypass in Cursor-Governance is "anyone with write access", so any agent with write access can bypass a blocked secret. | operator-reported | operator | Decide whether to restrict bypass. Restricting adds an approval step. | OPEN, decision |
| T21 | Cursor-Governance is public. Its files include operational detail and campaign packs that describe unfixed weaknesses. | observed | operator | Decide whether any content is scrubbed or moved while the repository stays public. | OPEN, decision |
| T22 | CEG, EIE, Website-Bot and SEO-Bot were made public on 2026-11-20 (operator, about 17:50Z). Their secret-scanning alerts were not read first; full history is now public. Their Sonar projects were set public to match. | operator-reported, observed | operator | Triage each repository's secret-scanning alerts; rotate anything real. | OPEN, P0 |
| T23 | (Fixed in EIE #367, merged by the operator: eleven whole-path allowlist classes removed; the two findings they hid were exempted on their own rule only; Gitleaks binary pinned with checksum.) EIE `.gitleaks.toml` allowlists whole path classes (tests, docs, JSON, Markdown, requirements files), so a secret there passes on every event. EIE also installs an older Gitleaks binary without a checksum in two workflows, while Core pins a newer one. | lane (F2) | CTO to assign | Done. | FIXED_PROVEN |
| T24 | Cursor-Governance has 11 open Dependabot vulnerabilities (3 high, 5 moderate, 3 low) and 3 open code-scanning alerts. | observed, operator-reported | lane N1b | Triage; fix or record an exception with owner and expiry. | OPEN |

## Coverage that is not running

| ID | Item | Source | Owner | Next action | State |
|---|---|---|---|---|---|
| T15 | Sonar has not analyzed Cursor-Governance since #1062 merged. Zero dispatch runs exist. | lane (N1) | other CTO (Core scheduler) | Core's nightly dispatcher is plan-only and returns "apply closed" for `mode=apply`. Until it applies, Sonar coverage here is `NOT_EXECUTED`. | OPEN, reported |
| T25 | Sonar free plan allows 50k private lines. | observed | operator | Settled 2026-11-20: CEG, EIE, Website-Bot, SEO-Bot and Cursor-Governance are public on GitHub and in Sonar, so their lines are free. Revisit if any goes private again. | SETTLED |
| T26 | Copilot pull-request review fails on quota in Cursor-Governance and EIE; the last 15 EIE runs all failed. Codex posts usage-limit notices. | observed, lane (F2) | operator | Raise or reset the limit, or switch the reviewer off. Accepted as a known red check for merge on 2026-11-20. | OPEN, decision |
| T27 | CodeRabbit was never installed on Quantum-L9 (No Plan, no repositories), which is why it reviewed nothing. On 2026-11-20 the operator started the 2-week Advanced trial, installed the app on .github, CEG and EIE only, and saved an organization review policy (version 3: chill, no auto-approvals, summary in the walkthrough, exclusions only). | operator-reported | operator, CTO | Score the trial per pull request against Codex; operator decides near day 12 whether to buy Essentials. | OPEN, trial |
| T28 | EIE's Perplexity review workflow has not run since April 2026. | lane (F2) | operator | Retire candidate. Nothing was changed. | OPEN, decision |

## Spend

| ID | Item | Source | Owner | Next action | State |
|---|---|---|---|---|---|
| T29 | GitHub Code Quality "AI findings" scans are on in Cursor-Governance and the page says AI credits are billed per push. | operator-reported | operator | Turn off unless its findings are valued. It may share the credit pool behind T26; that is not confirmed. | OPEN, decision |
| T30 | GitHub Code Quality runs CodeQL a second time on every pull request and push, about 6 minutes each, beside the repository's own CodeQL workflow. It overlaps with Sonar's purpose. | observed, lane (N1) | CTO | Compare unique findings from Code Quality, CodeQL and Sonar in the tool matrix; then keep or drop. | OPEN |
| T31 | GitHub Secret Protection and Code Security are both enabled on private repositories and billed per active committer. The licence count and bill are unknown. | operator-reported | operator | Read the organization licensing page once. Public repositories are free. | UNKNOWN |

| T32 | The SDK inventory reports JavaScript as `unsupported` in Cursor-Governance, so the central Semgrep path plans no JavaScript instance there. Visible, not hidden; CodeQL covers JavaScript separately. | observed (I1) | lane L1d | Decide whether the TypeScript pack is extended to JavaScript after fixture proof. | OPEN |
| T33 | CEG's and EIE's repository `.coderabbit.yaml` lack `inheritance: true`, so they override the organization policy. EIE's sets assertive, request changes, and a summary written into the PR description that `make pr` owns, and excludes docs. | observed | lanes C1 (CEG), C2 (EIE) | CEG: #516 merged by the operator. EIE: #368 open; CodeRabbit is reviewing it. | OPEN, EIE in progress |
| T34 | Stage 1 integration, 2026-11-20: Core #283's new `tests/governance/test_ci_runtime_invariants.py` failed to import under Core's full-suite discovery (`tests/tools` shadows top-level `tools`). | observed (I1) | lane L2 | Repaired on #283; re-verified: full suite 1165 OK. See `STAGE1_INTEGRATION.md`. | FIXED_PROVEN |

| T35 | Core uploads no coverage to Sonar, so every Core pull request that adds code fails SonarCloud with 0% coverage on new code (seen on #283, #286, #287). | observed | lane L2b | Feed coverage from an existing test run to the Sonar scan; no second test run. | OPEN, assigned |

## Pending operator changes

| ID | Change | Where | When | Why |
|---|---|---|---|---|
| P1 | Turn off Codex automatic pull-request review on Cognitive.Engine.Graphs. | https://chatgpt.com/codex/cloud/settings/general | After CodeRabbit has reviewed its first pull request there. | Codex posted 117 comments and 7 usage-limit notices on 2026-11-20 across six repositories; CodeRabbit takes over routine review. |
| P2 | Keep Codex automatic review on Enrichment.Inference.Engine for the trial only. | same | Until the CodeRabbit decision. | Head-to-head comparison on the same pull requests. |
| P3 | Turn off Codex automatic review on .github. | same | With P1. | CodeRabbit is installed there. |
| P4 | Keep Codex for on-demand `@codex review` on pull requests that change CI workflows, permissions, or the Core and SDK contracts. Candidate lane: agents request it automatically only for those paths (change to Cursor-Governance publication rules; not started). | Cursor-Governance | After the trial. | Spend Codex credits where a second deep review pays. |
| P5 | Turn off Copilot automatic pull-request review. | GitHub organization or repository Copilot settings | Any time. | It fails on quota on every pull request and has produced no review since 2026-11-05. |
| P6 | Turn off "Automatically import new GitHub repositories" in the Sonar organization binding. | https://sonarcloud.io/organizations/quantum-l9/edit | Any time. | T19. |

## Recorded operator decisions

- 2026-11-20: merging is last. No campaign pull request is merged until the campaign has fully converged; agents never merge.
- 2026-11-20: Cursor-Governance stays public; its open items are fixed inside the campaign.
- 2026-11-20: the Copilot quota failure is accepted as a known red check.

## Held for the operator

| ID | Item | Owner | Next action |
|---|---|---|---|
| H1 | Lane N1's CodeQL language-detection fix is committed locally and unpublished. | operator | Say whether it may be published as a pull request. It needs a second pull request to advance the caller pins. |
| H2 | G0 Screen 3: the Cursor-Governance Sonar project's analysis method, quality gate, new-code definition and imported coverage. | operator | Optional while T15 is open; nothing is analyzing it. |
| H3 | Organization-level custom secret patterns on GitHub. | CTO, then operator | The CTO supplies patterns and test strings after the harvest lists internal token formats; the operator creates them once at organization level. |

## Recorded and settled

- CodeQL in Cursor-Governance is in Advanced setup; default setup is not configured. `operator-reported`, `observed`.
- CodeQL overlay cache hits on sampled pull requests: analysis 1m16s against 4m41s on the base. `lane (N1)`.
- Sonar "Mask detected secret values" is on for the organization. `observed`.
- The Cursor-Governance Sonar project is public again, matching the public repository, so its lines do not count against the private allowance. `observed`.
- EIE #366 is ready to merge; T05, T06 and the EIE half of T10 are dispositioned. `lane (F2)`.
