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
| T24 | Cursor-Governance has 11 open Dependabot vulnerabilities (3 high, 5 moderate, 3 low) and 3 open code-scanning alerts. | observed, operator-reported | lane N1b | Triage; fix or record an exception with owner and expiry. | OUT_OF_SCOPE: a finding, not a CI defect (operator decision 2026-11-20). Owner: the repository. |

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

| T32 | The SDK inventory reports JavaScript as `unsupported` in Cursor-Governance, so the central Semgrep path plans no JavaScript instance there. Visible, not hidden; CodeQL covers JavaScript separately. (Corrected: CodeQL on Cursor-Governance analyzes `python` only; JavaScript is not covered.) | observed (I1) | lane L1d | Decide whether the TypeScript pack is extended to JavaScript after fixture proof. | OPEN |
| T33 | CEG's and EIE's repository `.coderabbit.yaml` lack `inheritance: true`, so they override the organization policy. EIE's sets assertive, request changes, and a summary written into the PR description that `make pr` owns, and excludes docs. | observed | lanes C1 (CEG), C2 (EIE) | CEG: #516 merged by the operator. EIE: #368 open; CodeRabbit is reviewing it. (Corrected: #368 merged 2026-11-20T18:42:01Z, `4324e0df`.) | OPEN, EIE in progress |
| T34 | Stage 1 integration, 2026-11-20: Core #283's new `tests/governance/test_ci_runtime_invariants.py` failed to import under Core's full-suite discovery (`tests/tools` shadows top-level `tools`). | observed (I1) | lane L2 | Repaired on #283; re-verified: full suite 1165 OK. See `STAGE1_INTEGRATION.md`. | FIXED_PROVEN |

| T35 | Core uploads no coverage to Sonar, so every Core pull request that adds code fails SonarCloud with 0% coverage on new code (seen on #283, #286, #287). | observed | lane L2b | Feed coverage from an existing test run to the Sonar scan; no second test run. | OPEN, assigned |

| T36 | EIE workflows use mutable action tags in 85 places on main, and `perplexity-code-review.yml` interpolates dispatch inputs into `run:`. | observed (Semgrep) | lane F2b | Pin to SHAs, move inputs to `env:`. See `SEMGREP_REVIEW.md`. | OUT_OF_SCOPE: a finding, not a CI defect (operator decision 2026-11-20). Owner: the repository. |
| T37 | Hosted Semgrep false positives on main (SDK Python 3.7 compatibility rule, literal-identifier SQL, env-indirected script input, a logger line). | observed (Semgrep) | operator | Operator authorized; applied by the CTO session through the Semgrep API: rule disabled in the Code detection policy, 26 main-branch findings ignored (18 false positive, 8 acceptable risk; Semgrep also closed 22 copies on pull-request refs). Re-read: none of the 26 remain open. | FIXED_PROVEN |
| T38 | Consumers reference `Quantum-L9/l9-ci-core/...@v2` by a moving tag, and three `pyproject.toml` files have no uv dependency cooldown. | observed (Semgrep) | Core owner | One decision each, applied centrally. | OPEN |
| T39 | Reachable critical certifi advisory in four template repositories outside the campaign. | observed (Semgrep) | repository owners | Relock certifi. Out of campaign scope; recorded so it is not lost. | OUT_OF_SCOPE: a finding, not a CI defect (operator decision 2026-11-20). Owner: the repository. |

| T40 | Governance-seeder pull requests in l9-ci-sdk (#117) never run the two required checks, so they can never merge, and the SDK campaign stack (#118 to #121) is built on one. Main-based Dependabot PRs also fail `Analyze (central Core)`. | observed | lane L1e | Find the trigger or ruleset cause, fix it at the owner, or rebuild the SDK stack on main if it does not need #117. | OPEN, assigned |
| T41 | The secret-scanning service monitors only the operator's personal GitHub account; no Quantum-L9 repository is monitored, so its CI check sees nothing for the organization. | observed | operator | Connect the organization in the service's GitHub integration. | OPEN, operator |
| T42 | Codecov receives no usable report from any campaign repository; the one upload (CEG) is path-filtered, last ran 2026-03-11 and failed. | observed | cleanup wave | Retire in favour of Sonar coverage. See `CODECOV_REVIEW.md`. | OPEN, retire candidate |

| T43 | Core `org-ci.yml` pins its own actions to SHAs not on Core main (`043f50a`, `a0c7178`, orphaned by the #280 squash) and provisions SDK `d09d3963`; the merged #286 plan/aggregate and #287 inheritance do not run in the required job. | observed (EIE canary, CTO verified) | lane L2f | Re-pin to main, wire plan and aggregate, advance the SDK pin, add an ancestry guard test. See `CI_CONFIG_FINDINGS.md` rows 1–2. | OPEN, assigned |
| T44 | Central Semgrep scope is set by Semgrep's default ignore (drops `tests/` and `.semgrep/`), and consumer `# nosemgrep` and `.semgrepignore` can lower central coverage. | observed (canaries) | lane L1f | Declared scope; `--disable-nosem`; ignore consumer `.semgrepignore` for required rules. Rows 3–4. | OPEN, assigned |
| T45 | Core `Control plane attestation` fails on every push since at least 2026-11-18 (code-owner review rule missing, ruleset not strict, immutable-release setting unreadable); Core main Sonar new-code coverage 79.6% against 80%. | observed | lane L2g, operator for settings | Meet each expectation through the settings-as-code engine, or change it with a recorded operator decision; add tests for the uncovered lines. Row 8. | OPEN, assigned |
| T46 | `lint-autofix.yml` in Cursor-Governance and CEG opens pull requests with `GITHUB_TOKEN`, which starts no workflows, so those PRs never get their required checks (the class behind SDK #117, fixed for the SDK in #126). | observed | each repository | Use the organization App token, or stop opening PRs; add a verification check. Row 7. | OPEN |
| T47 | EIE Sonar on main fails its gate with no coverage imported; CEG sends no coverage to Sonar. | observed (canaries) | canary agents | One test run, `coverage.xml` reused by Sonar (the Core #289 pattern). Row 6. | OPEN, assigned |

| T48 | Lock-owned tools are pinned locally in several repositories off Core's toolchain lock (finding row 15). | observed | L2h, L1g, G2, then per owner | Report in Core; remove local pins. | OPEN, assigned |
| T49 | Core and SDK Dependabot configs do not ignore lock-owned tools; SDK #114 proposed lock-owned bumps; SDK #117 (rendered config restore) is blocked without required checks (finding row 16). | observed | operator (#114, #117), L2h | Close #114, re-run #117's checks, Core ignores lock-owned tools. | OPEN |

## Pending operator changes

| ID | Change | Where | When | Why |
|---|---|---|---|---|
| P1 | Turn off Codex automatic pull-request review on Cognitive.Engine.Graphs. | https://chatgpt.com/codex/cloud/settings/general | After CodeRabbit has reviewed its first pull request there. | Codex posted 117 comments and 7 usage-limit notices on 2026-11-20 across six repositories; CodeRabbit takes over routine review. |
| P2 | Keep Codex automatic review on Enrichment.Inference.Engine for the trial only. | same | Until the CodeRabbit decision. | Head-to-head comparison on the same pull requests. |
| P3 | Turn off Codex automatic review on .github. | same | With P1. | CodeRabbit is installed there. |
| P4 | Keep Codex for on-demand `@codex review` on pull requests that change CI workflows, permissions, or the Core and SDK contracts. Candidate lane: agents request it automatically only for those paths (change to Cursor-Governance publication rules; not started). | Cursor-Governance | After the trial. | Spend Codex credits where a second deep review pays. |
| P5 | Turn off Copilot automatic pull-request review. | GitHub organization or repository Copilot settings | Any time. | It fails on quota on every pull request and has produced no review since 2026-11-05. |
| P6 | Turn off "Automatically import new GitHub repositories" in the Sonar organization binding. | https://sonarcloud.io/organizations/quantum-l9/edit | Any time. | T19. |

## Close-out checklist

The campaign closes when every row is DONE with evidence. Side work (hosted hook memory, secret
registration, the Claude Code host default) does not block close-out.

| # | Item | Owner | Done when |
|---|---|---|---|
| X1 | Promotion is live: the required job runs current Core and SDK code | L2 (L2f step 1 merged as Core #292; step 2 open) | `Analyze (central Core)` on a consumer PR shows Core main and the advanced SDK pin |
| X2 | Core consumer gaps closed: security scans in org-ci, blocking toolchain alignment, conflict-marker step, Cursor-Governance deep entrypoint, supply-chain lane (HARVEST_LEDGER C1 to C5) | L2 | Each merged and observed on a Cursor-Governance PR |
| X3 | One source of tool versions reaches Cursor-Governance, Core, SDK, l9-graphiti-memory and IB-Odoo_19; Dependabot cannot bump a Core-owned tool | CG-CUTOVER, L1 (SDK #129), G2 (IB-Odoo_19 #560), L2 | Pins equal Core's lock and the blocking alignment check passes |
| X4 | Expensive checks run nightly only where code changed | L2 (planner merged; apply needs the operator's GitHub App) | The planner dispatches only changed repositories, including Cursor-Governance's Sonar; and nightly findings land somewhere owned (row 24): code-scanning alerts plus one rolling `Nightly findings` issue per repository, proven by one nightly run on Cursor-Governance |
| X5 | Cursor-Governance is cut over: dead and duplicate CI retired, required-check plan written, `CURSOR_CANARY_PASS` with evidence | CG-CUTOVER | `evidence/CURSOR_CANARY_RESULT.md` reports PASS against CURSOR_CANARY.md Gates 0-4 |
| X6 | Secondary canaries recorded (CEG, EIE) | C-CEG, C-EIE | Gate 2-3 verdicts with run ids; findings in CI_CONFIG_FINDINGS |
| X7 | Harvest ledgered with destinations | CTO, then each owner lane | Index in `evidence/HARVEST_LEDGER.md`; every row promoted during this campaign (at least C1 to C5) carries the full `HARVEST.md` fields and a delivery receipt. Rows not promoted stay as backlog for the rollout campaign |
| X8 | Merge queue on Cursor-Governance main, driven by `/l9-pr-remediation` (operator 2026-11-21: no separate merge script) | CTO; skill enqueue support assigned (X8-QUEUE) | All six required checks already run on `merge_group` (verified 02:30Z). Today `stack_safe_merge.py` only merges directly, which a queue refuses, and `merge_gate.py` denies `ccr/auto_merge`, the REST enqueue route. Done when the skill enqueues a granted, green head, the ruleset carries the queue, and the operator's `/l9-pr-remediation Quantum-L9/Cursor-Governance` lands at least two PRs through it with merge_group run ids recorded |
| X9 | Close-out evidence | CTO | PROOF.md filled from real runs; this register closed |
| X10 | CTO CI-run audit: bugs, duplicate and overlapping checks, misalignment with Core, and expensive per-PR checks that belong in nightly | CTO (operator directive 2026-11-21 02:30Z) | Each check on a green Cursor-Governance PR head and its merge-queue run is classified keep, retire (duplicate), fix (bug or misalignment) or move to nightly, with seconds measured from check runs; each retire or move is merged, or handed to the operator as a settings change with a click path; the measured per-PR delta goes in the receipt |

## Recorded operator decisions

- 2026-11-21, about 02:45Z: a pull request is judged only on the code it brings in; only the nightly run scans the whole repository. This applies to every tool. On a PR a check may read the whole tree when its analysis needs context (type checking, taint rules), but only findings the change introduces block. A finding already present at the merge-base is reported and does not block. Unknown (no base, failed or incomplete scan) still blocks. Exceptions: dependency and CVE audits run on a PR only when a manifest or lock file changes, and nightly for everything; affected-test selection falls back to the full suite when it cannot prove its scope. Pre-existing findings go to the nightly report with an owner, so debt stays visible. Local parity: lane PARITY-DIFF. Central org-ci: queued for the SDK and Core lanes. Recorded as CI_CONFIG_FINDINGS row 23.
- 2026-11-20, about 22:20Z: only checks that protect working or secure code may block a pull-request merge. Housekeeping checks (CODEOWNERS and file presence, docs and link checks, PR size, header conventions, toolchain-version drift and similar debt) report and never block. Recorded as CI_CONFIG_FINDINGS row 19.
- 2026-11-20, about 22:15Z: IB-Odoo_19 is proprietary to Quantum AI Partners, which clears its CI tooling for promotion into Quantum-L9 repositories (HARVEST_LEDGER S1a-S1f).

- 2026-11-20, about 21:50Z: close-out scope. The campaign includes cutting **Cursor-Governance** over to organization CI, debugging it and proving it works, so that the organization is ready to roll out. Rolling out to the other repositories is not part of this campaign; the harvest ledger's rows for EIE, CEG and IB-Odoo_19 are that campaign's starting backlog.
- 2026-11-20, about 21:40Z: harvest custom CI from Cursor-Governance, EIE, CEG and IB-Odoo_19 and move it upstream, so the organization benefits and consumers stop depending on their own copies. Ledger: `evidence/HARVEST_LEDGER.md`.

- 2026-11-20, about 20:35Z: one source of tool versions. Core's toolchain lock must fully reach every repository before the campaign is DONE, and Dependabot may never create drift for a locked tool. The organization is locked to Python 3.12 (Core lock 3.12.14).
- 2026-11-20, about 20:20Z: L2f authorized ("yes yes YES"): re-pin `org-ci.yml` to Core main, wire plan and aggregate into the required job, advance the SDK pin, add the ancestry guard. Rulesets and branch protection stay operator-only.
- 2026-11-20, about 20:15Z: the five-agent pool limit is overridden for lane G2 (l9-graphiti-memory).

- 2026-11-20, about 19:00Z: the campaign fixes CI so that it runs efficiently and correctly. It does not fix the findings CI tools uncover. A finding enters the campaign only as evidence of a CI defect: a gate that did not run, ran the wrong scope, reported a false outcome, wasted time or money, or is configured to produce noise. Lane F2b (EIE action pinning) and lane N1b (Cursor-Governance dependency floors, PR #1082) were withdrawn; #1082 is left for the operator outside the campaign.
- 2026-11-20, about 19:10Z: the CTO or the swarm merges Core, SDK and .github campaign pull requests once satisfied. Cursor-Governance, EIE and CEG are not merged by this campaign while another agent is merging there.
- 2026-11-20, about 18:55Z: merge the Core and SDK campaign pull requests once the CTO is satisfied. Core: #289, #283, #286, #287, #285. SDK: #118 to #121 after the governance-seeder PR #117 they are stacked on.

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

## Close-out status (2026-11-21 13:10Z)

Evidence for each row is in `CLOSEOUT_RECEIPT.md`.

| # | Status |
|---|---|
| X1 | DONE: org-ci pins SDK `4a887396` with CENTRAL-DIFF, the waiver ledger and B3 (Core #323, #324). |
| X2 | DONE: security scans in org-ci (Core #312), full-lock pip-audit (#330, #328, #335). |
| X3 | OPEN. Code merged; Cursor-Governance still pins Semgrep 1.171.0 (re-pin in progress), EIE #377 held for the App grant, l9-graphiti-memory and IB-Odoo_19 pins not re-verified. |
| X4 | OPEN. Code merged (Core #333, #337); the proof run is blocked on the nightly-App grant (click-path 7). |
| X5 | DONE: `CURSOR_CANARY_PASS` (Cursor-Governance #1112). |
| X6 | DONE (EIE canary #378, runs 1 and 2). |
| X7 | DONE (#1091, #1118). |
| X8 | OPEN. Skill support merged (#1109); the ruleset has no queue yet (click-path 1) and no PR has landed through it. |
| X9 | IN PROGRESS. `PROOF.md` filled from real runs (11 PASS, 34 BLOCKED, 14 NOT_PROVEN); register not closed. |
| X10 | OPEN. Findings done (rows 20-29); fixes not merged, operator settings not applied, measured delta not taken. |

### Corrections (REST, read 2026-11-21 13:10-13:20Z)

- EIE #368 is merged (`4324e0df`), not open.
- T32: CodeQL on Cursor-Governance analyzes `python` only, not JavaScript.
