# CI Unified Leverage v1.7.1 — close-out receipt

**Status: FINAL FOR THE CODE WORK (13:10Z 2026-11-21).** Every code item is merged and verified. Three items wait only on operator settings (X3, X4, X8); each names its click-path below and closes on one proof run.

Campaign scope (operator, 2026-11-20 21:50Z): cut **Cursor-Governance** over to organization CI, debug it and prove it works, so the
organization is ready to roll out. Rolling out to other repositories is a separate campaign.

## Close-out checklist

| # | Item | Status | Evidence |
|---|---|---|---|
| X1 | Promotion live: the required job runs current Core and SDK code | DONE | org-ci pins SDK `4a887396` with CENTRAL-DIFF, the waiver ledger and B3 (Core [#323](https://github.com/Quantum-L9/l9-ci-core/pull/323) + [#324](https://github.com/Quantum-L9/l9-ci-core/pull/324), merged 06:36Z). Verified on real Cursor-Governance PRs #1112, #1113, #1115 (Analyze green). |
| X2 | Core consumer gaps C1-C5 | DONE | Security scans in org-ci: Core [#312](https://github.com/Quantum-L9/l9-ci-core/pull/312) merged 08:16Z (the required job enforces Core's security scan); pip-audit audits the consumer's full resolved lock, [#330](https://github.com/Quantum-L9/l9-ci-core/pull/330) merged 09:07Z. Supply chain #304/#309, toolchain drift #302, conflict markers #300, housekeeping classification #310 merged. |
| X3 | One toolchain-lock source reaches every repository; Dependabot can't bump Core-owned tools | DONE (code); EIE #377 waits on the operator | Core #295, CEG [#524](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/524) merged. Core [#328](https://github.com/Quantum-L9/l9-ci-core/pull/328) `03028b6a` (push semantics + full-lock pip-audit active in org-ci; canary 44891625020: CG pass: improved, 4 kept green), [#334](https://github.com/Quantum-L9/l9-ci-core/pull/334)/[#335](https://github.com/Quantum-L9/l9-ci-core/pull/335) `94a3da0b` (pip-audit prints its export and count: EIE 106, CG 119, CEG 80, SDK 25, Core 2). Core's own toolchain audited by [#336](https://github.com/Quantum-L9/l9-ci-core/pull/336). EIE [#377](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/377) (drop EIE's local bandit/pip-audit) is held at `2f88e4a7` until the nightly full-lock audit reaches an owned destination (row 24), which needs the App grant (click-path 7). |
| X4 | Expensive checks run nightly, only where code changed; nightly findings land somewhere owned | DONE (code); proof waits on the operator | Planner + App-token apply (Core #290, #299). Nightly findings sink [#333](https://github.com/Quantum-L9/l9-ci-core/pull/333) `12f92e7f` (SARIF to code scanning, one rolling "Nightly findings" issue, ratchet on the single waiver ledger) plus full-lock pip-audit [#337](https://github.com/Quantum-L9/l9-ci-core/pull/337) `a226d0a6`. Proof run [44891263316](https://github.com/Quantum-L9/l9-ci-core/actions/runs/44891263316) and dry run 44896873853 ran the full scans (pip-audit CG 119, SDK 25, Core 2, CEG 80, EIE 106, no known vulnerabilities) and stopped at the token mint: `The permissions requested are not granted to this installation`. After click-path 7: two dispatches prove the upload and the in-place issue edit. CG #1106 stays the hand-curated checklist for its 29 sites. |
| X5 | Cursor-Governance cut over, `CURSOR_CANARY_PASS` | DONE | [#1112](https://github.com/Quantum-L9/Cursor-Governance/pull/1112) merged 07:37Z: Gates 0-4 PASS on the PIN-ADVANCE-3 pins; gate 2.4 witnessed centrally (the four `.semgrep/l9-pr.yml` rules fire in the central bundle). |
| X6 | Secondary canaries recorded | DONE (EIE) | EIE [#378](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/378): run 1 (central run 44874376220) and run 2 (44878546690, job 136768547018) Gates 2-3 PASS; in run 2 only the 3 canary findings block and 33 pre-existing do not. CEG canary #517: earlier run recorded; not re-run on PIN-ADVANCE-3. |
| X7 | Harvest ledgered with destinations | DONE | `HARVEST_LEDGER.md` index merged (#1091); full `HARVEST.md` fields for promoted rows C1-C5 merged ([#1118](https://github.com/Quantum-L9/Cursor-Governance/pull/1118)). |
| X8 | Merge queue on Cursor-Governance main, driven by `/l9-pr-remediation` | DONE (code); waits on the operator | Skill support merged ([#1109](https://github.com/Quantum-L9/Cursor-Governance/pull/1109)); throwaway proof PR #1113 ready (G2). `main` still has no `merge_queue` rule (checked 13:05Z). After click-path 1, G2 proves (iii) REST membership observable, (i) dequeue on push, (ii) REST DELETE dequeues; then `/l9-pr-remediation Quantum-L9/Cursor-Governance`. |
| X9 | Close-out evidence | DONE | This file, published through `make pr`. |
| X10 | CTO CI-run audit | DONE (findings); applying is operator settings + backlog | See "CI-run audit" below; rows 20-29 in `CI_CONFIG_FINDINGS.md`. |

## What changed for every PR

- **PRs are judged only on the code they bring in** (operator decision, row 23). Pre-existing findings are reported as warnings and do not block; unknown (no base, failed or incomplete scan) blocks. Baselines: PR = merge-base, merge queue = base, push = first parent, nightly = whole tree.
- **Waivers are central only** (Core ledger, l9-ci-sdk #138), owned and expiring; consumers cannot self-waive and `nosemgrep`/consumer ignores do not reduce required coverage.
- **Every Core change to what Analyze runs passes a differential promotion canary** on five repositories first (Core #311, #313, #317).

## Canary verdicts (promotion canary, Core)

| Core PR | Change | Verdict | Note |
|---|---|---|---|
| #311 | canary introduced | pass | differential |
| #319 | activate SDK 1d632037 | **FAIL** (run 44864948490) | caught tests/ scope widening: SDK 104, CEG 91, EIE 19, Core 1 new blockers; not merged (row 26) |
| #322 | activate SDK 47ae3ac5 | pass | l9-ci-sdk improved |
| #324 | activate SDK 4a887396 + CENTRAL-DIFF | pass (run 44875640013) | CG: 79 findings, all advisory |
| #328 | consumer legs verify as a push; full-lock pip-audit active | pass (run 44891625020) | CG pass: improved (row 27 fixed); 4 kept green |
| #335 | org-ci on #334's pip-audit (prints export + count) | pass | all 5 kept green |
| #336 | Core toolchain audit | pass | all 5 kept green; audit 104 audited, 26 excepted, 0 open |
| #338 | admit Semgrep 1.186.0 | pass | all 5 kept green |
| #339 | activate Semgrep 1.186.0 | pass (run 44903350118) | all 5 kept green; zero finding drift (below) |

## Findings rows added this session

Rows 17-27 in `CI_CONFIG_FINDINGS.md`. Row 27 (new): canary consumer legs inherited the Core PR's `pull_request` event, so Cursor-Governance's
`make test` refused ("HEAD is not a two-parent merge commit") at both pins and masked any CG regression. Fix: Core #328 (push semantics for consumer legs).
Row 28 (new, security): nobody audited Core's pinned CI toolchain (consumer lock exports exclude it; Core's own leg audited 2 packages). The new toolchain audit (Core [#336](https://github.com/Quantum-L9/l9-ci-core/pull/336)) resolved 109 pins from 9 tools and found 30 known vulnerabilities in 6 packages, all in Semgrep 1.171.0's locked closure (urllib3, certifi, pyjwt, mcp, opentelemetry-api, wcmatch), installed by every repository's CI. Decision: re-lock 1.171.0 now (fixes urllib3, certifi), dated owned exceptions for the rest with a reachability reason and expiry ≤ 2026-12-05, then promote Semgrep 1.186.0 through the canary and drop the exceptions it clears. The audit stays blocking. Merged: Core [#336](https://github.com/Quantum-L9/l9-ci-core/pull/336) at `c4a66e12` (104 audited, 26 excepted, 0 open; the wcmatch ReDoS GHSA-53pm-wgxf-c6qf exception is bounded by proven `timeout-minutes` on every Semgrep job, a 300 s SDK kill, and a timeout that fails closed) and [#338](https://github.com/Quantum-L9/l9-ci-core/pull/338) at `2ee1720b` (Semgrep 1.186.0 admitted), activated by [#339](https://github.com/Quantum-L9/l9-ci-core/pull/339) at `acb73463`: canary kept all 5 repositories green; audit now 105 audited, 8 excepted, 0 open (18 exceptions pruned as stale).
Semgrep 1.171.0 → 1.186.0 finding drift (canary run 44903350118, head versus base legs): no new and no fixed findings anywhere. Blocking 0 → 0 in all five; non-blocking CG 80 → 80, CEG 139 → 139, EIE 36 → 36, SDK 154 → 154, Core 1 → 1.

Remaining toolchain exceptions (`.github/actions/install-semgrep/audit-exceptions.yaml`, owner `l9-ci-core`, created 2026-11-21, all expire 2026-12-05; the audit fails on expiry):

| Advisory | Package@version | Removal trigger |
|---|---|---|
| GHSA-5h93-6whr-6q8j, GHSA-84m7-p3x7-pcfv, GHSA-qx49-fqc8-xw99, GHSA-rwrf-2pqf-9j8j, GHSA-w4fh-qvv9-3v23 | mcp@1.29.0 | a Semgrep release allowing mcp >= 1.30.0 |
| GHSA-mf5v-w3w3-f6cg, GHSA-xcq7-p3pf-p88h | opentelemetry-api@1.37.0 | a Semgrep release allowing opentelemetry-api >= 1.45.2 |
| GHSA-53pm-wgxf-c6qf | wcmatch@8.5.2 | a Semgrep release allowing wcmatch >= 11.2 (bounded-impact: ReDoS on attacker file names; availability only; timeout fails closed) |

Row 29 (new, governance): Core's `Control plane attestation` (`attest`) has failed on every main push, 99 failures and 0 passes. It reports three operator settings, correctly: Core `main` has no `pull_request` rule (active: required_status_checks, workflows); immutable releases cannot be read because `L9_CONTROL_PLANE_TOKEN` is not provisioned; and ruleset 21895545 has `strict_required_status_checks_policy=false` with no merge queue. Click-paths 4-6.

Row 22: a double-triggered canary posted a cancelled FAIL verdict on the same head (hit #328, #330); fixed by Core [#332](https://github.com/Quantum-L9/l9-ci-core/pull/332) (one verdict per pushed head; a text edit posts no verdict). Row 27 fix: Core [#326](https://github.com/Quantum-L9/l9-ci-core/pull/326) (action, merged 08:30Z) and #328 (org-ci activation). A follow-on conflict between push semantics and CG's `sonarcloud.yml` allowlist test was fixed in Cursor-Governance [#1119](https://github.com/Quantum-L9/Cursor-Governance/pull/1119).

## CI-run audit (X10)

Measured on a green Cursor-Governance PR (head of #1107): about **1001 runner-seconds per push**.

| Check | s | Verdict | Action |
|---|---|---|---|
| Analyze (python) — CodeQL default setup | 234 | retire (duplicate) | operator: turn CodeQL default setup off, keep the `codeql` workflow (or the reverse) |
| semgrep-cloud-platform/scan | 163 | retire from PRs | operator: Semgrep app — stop PR scans; the central SDK Semgrep is the required one |
| Exact-head memory lifecycle proof | 89 | path-scope | run only when memory code changes |
| SBOM / License / Dependency Review | 32 | path-scope | only when manifests or locks change; nightly for all |
| `pr / gates`, `pr / body`, `issue` | small | fix | each fires twice (duplicate triggers) |
| merge_group | — | fix | Cursor-Governance runs its full suite on merge_group; scope it to the group's base |

Projected saving if all applied: about **520 s per push (~52%)**. Measured delta after applying: NOT MEASURED (not yet applied).

## Operator click-paths

1. **Merge queue (X8):** https://github.com/Quantum-L9/Cursor-Governance/settings/rules/20855699 → tick *Require merge queue* → Squash, build concurrency 5, group size 1-5, wait 5 min, only merge non-failing, timeout 60 min → *Save changes*. Then `/l9-pr-remediation Quantum-L9/Cursor-Governance`.
2. **CodeQL duplicate:** Settings → Code security → Code scanning → CodeQL analysis → switch *Default setup* off (the `codeql` workflow stays).
3. **Semgrep app PR scan:** Semgrep AppSec Platform → Projects → Cursor-Governance → turn off diff-aware PR scans (keep scheduled full scans if wanted).
4. **Core main protection (row 29):** https://github.com/Quantum-L9/l9-ci-core/settings/rules → the `main` ruleset → add *Require a pull request before merging* (0 approvals, code-owner review off) → *Save changes*.
5. **Attestation token (row 29):** Core → Settings → Environments → `control-plane-attestation` → add secret `L9_CONTROL_PLANE_TOKEN` (a fine-grained token or App with repository Administration: read only).
6. **Required-check freshness (row 29):** organization ruleset 21895545 → *Require branches to be up to date before merging* on, or bind a merge queue (click-path 1 does that for Cursor-Governance).
7. **Nightly App (X3, X4):** organization Settings → Developer settings → GitHub Apps → `l9-nightly-dispatch` (5854787) → Permissions → Repository: Code scanning alerts *Read and write*, Issues *Read and write* → save; then accept the new permissions on the organization installation, with repository access covering Cursor-Governance, CEG, EIE, l9-ci-sdk, l9-ci-core.

## Rollout backlog (next campaign)

CEG and EIE cutover using HARVEST_LEDGER rows; IB-Odoo_19 framework checks (S1a-S1f); `l9-semantic-compiler-engine` SHA-1 sites (fixed upstream by SDK #145, needs a pin past CENTRAL-DIFF there); Core ADR 0023 amendment; Analyze-check rename (operator ruleset edit).

## Merged pull requests (2026-11-20 16:00Z to 2026-11-21 13:10Z, 149 across five repositories)

Sorted by merge time. Dependabot and operator merges are included.

### l9-ci-core (51)

| PR | Merged (UTC) | Title |
|---|---|---|
| [#289](https://github.com/Quantum-L9/l9-ci-core/pull/289) | 11-20 19:03 | ci(sonar): import coverage from Core's existing test runs into its Sonar analysis (L2b) |
| [#283](https://github.com/Quantum-L9/l9-ci-core/pull/283) | 11-20 19:03 | docs(adr): propose Core ADRs 0001 and 0002 with witnessed ci_runtime_invariants (L2 PR 2a) |
| [#285](https://github.com/Quantum-L9/l9-ci-core/pull/285) | 11-20 19:04 | fix(security): report each scan's real outcome in security.yml (L2 T04) |
| [#286](https://github.com/Quantum-L9/l9-ci-core/pull/286) | 11-20 19:05 | feat(actions): plan and aggregate every required provider/target instance (L2 PR 2b, stacked on #283) |
| [#287](https://github.com/Quantum-L9/l9-ci-core/pull/287) | 11-20 19:07 | feat(stamp): inherit tool configuration from Core at runtime (L2 PR 2c, stacked on #286) |
| [#288](https://github.com/Quantum-L9/l9-ci-core/pull/288) | 11-20 19:08 | fix(tools): authenticate the registry fetch from private Quantum-L9/.github |
| [#284](https://github.com/Quantum-L9/l9-ci-core/pull/284) | 11-20 19:12 | feat(settings): GitHub settings-as-code engine and reusable runner |
| [#290](https://github.com/Quantum-L9/l9-ci-core/pull/290) | 11-20 19:48 | Nightly scheduling: plan from the registry projection, change-gate Core's deep suite, closed apply path |
| [#291](https://github.com/Quantum-L9/l9-ci-core/pull/291) | 11-20 20:12 | Regenerate the required-repositories projection from .github@08b2d07 (adds CEG, EIE and 25 more) |
| [#292](https://github.com/Quantum-L9/l9-ci-core/pull/292) | 11-20 21:19 | L2f step 1: re-pin org-ci to main, guard self-pin ancestry, promote SDK dc783c64 |
| [#293](https://github.com/Quantum-L9/l9-ci-core/pull/293) | 11-20 21:20 | L2g: attest the operator's Core main protection, run required checks on the merge queue, declare immutable rel |
| [#294](https://github.com/Quantum-L9/l9-ci-core/pull/294) | 11-20 21:52 | L2f step 2: activate SDK dc783c64 and make Analyze (central Core) the every-instance verdict |
| [#295](https://github.com/Quantum-L9/l9-ci-core/pull/295) | 11-20 22:09 | L2h: toolchain alignment across every declaration surface; Core on its own lock; Dependabot ignores lock-owned |
| [#299](https://github.com/Quantum-L9/l9-ci-core/pull/299) | 11-20 22:44 | L2-closeout item 4: open nightly apply with an App-minted token; admit Cursor-Governance |
| [#305](https://github.com/Quantum-L9/l9-ci-core/pull/305) | 11-20 22:58 | P0 step one: promote SDK 9af1a202 (scan-scope planning fixes the Cursor-Governance TypeScript-incomplete failu |
| [#301](https://github.com/Quantum-L9/l9-ci-core/pull/301) | 11-20 22:58 | feat(run-sonar): one reusable Core Sonar step that reuses the consumer's coverage |
| [#298](https://github.com/Quantum-L9/l9-ci-core/pull/298) | 11-20 23:24 | L2-closeout item 1 (step one): security.yml scans a consumer on what it changes, with the Core rules |
| [#306](https://github.com/Quantum-L9/l9-ci-core/pull/306) | 11-20 23:37 | Item 8 (a): publish the required check name once in the runtime contract (current value) |
| [#307](https://github.com/Quantum-L9/l9-ci-core/pull/307) | 11-20 23:50 | fix(sdk): promote SDK fbe14fec (#133 declared analysis budget) (P0 step one) |
| [#304](https://github.com/Quantum-L9/l9-ci-core/pull/304) | 11-20 23:50 | L2-closeout item 5 (step one): one Core supply-chain lane with per-repository policy data |
| [#308](https://github.com/Quantum-L9/l9-ci-core/pull/308) | 11-21 00:16 | ci(org-ci): activate SDK fbe14fec — advance Core pins to eba72ac3 (P0 step two) |
| [#309](https://github.com/Quantum-L9/l9-ci-core/pull/309) | 11-21 00:29 | feat(supply-chain): Core-owned per-repository licence exemptions |
| [#302](https://github.com/Quantum-L9/l9-ci-core/pull/302) | 11-21 01:35 | L2-closeout item 2: report toolchain drift in Analyze (central Core), advisory |
| [#310](https://github.com/Quantum-L9/l9-ci-core/pull/310) | 11-21 01:35 | L2-closeout housekeeping audit: classify every Analyze (central Core) step; housekeeping never blocks |
| [#300](https://github.com/Quantum-L9/l9-ci-core/pull/300) | 11-21 01:35 | L2-closeout item 3: repository verification fails an unresolved merge conflict |
| [#311](https://github.com/Quantum-L9/l9-ci-core/pull/311) | 11-21 02:04 | ci(canary): blocking promotion canary for changes to Analyze (central Core) |
| [#313](https://github.com/Quantum-L9/l9-ci-core/pull/313) | 11-21 03:04 | fix(canary): run the base pins inline; repair main's stale canary render |
| [#315](https://github.com/Quantum-L9/l9-ci-core/pull/315) | 11-21 03:35 | fix(sdk): promote SDK 2796d7a4 (#141 framework-scoped Semgrep rules) (PIN-ADVANCE-1 step one) |
| [#316](https://github.com/Quantum-L9/l9-ci-core/pull/316) | 11-21 03:48 | ci(org-ci): activate SDK 2796d7a4 — advance Core pins to df3b2eaf (PIN-ADVANCE-1 step two) |
| [#318](https://github.com/Quantum-L9/l9-ci-core/pull/318) | 11-21 04:10 | fix(sdk): promote SDK 1d632037 (#140 credentials, #142 _archived, #134 scope) (PIN-ADVANCE-2 step one) |
| [#320](https://github.com/Quantum-L9/l9-ci-core/pull/320) | 11-21 04:21 | test(provisioning): use a non-secret-shaped read-token fixture (unblocks PIN-ADVANCE-2) |
| [#321](https://github.com/Quantum-L9/l9-ci-core/pull/321) | 11-21 04:42 | fix(sdk): make SDK 47ae3ac5 the default, not 1d632037 (PIN-ADVANCE-2 redirect, step one) |
| [#322](https://github.com/Quantum-L9/l9-ci-core/pull/322) | 11-21 04:54 | ci(org-ci): activate SDK 47ae3ac5 — advance Core pins to 2ff05a03 (PIN-ADVANCE-2c step two) |
| [#317](https://github.com/Quantum-L9/l9-ci-core/pull/317) | 11-21 05:34 | feat(canary): run the SDK revision an admission-only pull request admits (row 25) |
| [#323](https://github.com/Quantum-L9/l9-ci-core/pull/323) | 11-21 06:23 | feat(sdk): admit SDK 4a887396 and the action inputs CENTRAL-DIFF needs (PIN-ADVANCE-3 step one) |
| [#324](https://github.com/Quantum-L9/l9-ci-core/pull/324) | 11-21 06:36 | ci(org-ci): activate SDK 4a887396 with CENTRAL-DIFF, the waiver ledger and B3 (PIN-ADVANCE-3 step two) |
| [#325](https://github.com/Quantum-L9/l9-ci-core/pull/325) | 11-21 06:49 | ci(org-ci): upload every instance bundle beside the central set (SDK ADR 0021 Core change 2) |
| [#327](https://github.com/Quantum-L9/l9-ci-core/pull/327) | 11-21 07:51 | ci(canary): reusable org-ci jobs as sibling jobs, no continue-on-error, verdict is the only gate |
| [#329](https://github.com/Quantum-L9/l9-ci-core/pull/329) | 11-21 08:16 | fix(security): HTTPS-only gitleaks download; name the report helper's arguments (#312 step one) |
| [#312](https://github.com/Quantum-L9/l9-ci-core/pull/312) | 11-21 08:16 | L2-closeout item 1 (step two): org-ci runs Core's security scan; the required job enforces it |
| [#326](https://github.com/Quantum-L9/l9-ci-core/pull/326) | 11-21 08:30 | feat(verification): push semantics for consumer verification on request (row 27 step one) + CENTRAL-DIFF basel |
| [#330](https://github.com/Quantum-L9/l9-ci-core/pull/330) | 11-21 09:07 | SEC-LOCKSET: Core's pip-audit audits the consumer's full resolved lock |
| [#332](https://github.com/Quantum-L9/l9-ci-core/pull/332) | 11-21 09:32 | ci(canary): one verdict per pushed head; a text edit posts no verdict (row 22) |
| [#333](https://github.com/Quantum-L9/l9-ci-core/pull/333) | 11-21 09:47 | NIGHTLY-SINK (X4): nightly central scan to code scanning, a rolling findings issue and a ratchet |
| [#328](https://github.com/Quantum-L9/l9-ci-core/pull/328) | 11-21 10:20 | ci(org-ci): consumer legs verify as a push; merge-group baseline is base_sha (row 27 step two) |
| [#334](https://github.com/Quantum-L9/l9-ci-core/pull/334) | 11-21 10:20 | fix(security): pip-audit names its uv export and the audited package count |
| [#335](https://github.com/Quantum-L9/l9-ci-core/pull/335) | 11-21 10:45 | ci(org-ci): pin security.yml at #334's merge (step two) |
| [#337](https://github.com/Quantum-L9/l9-ci-core/pull/337) | 11-21 11:23 | NIGHTLY-SINK: full-lock pip-audit in the nightly sink, on the same issue and ratchet |
| [#336](https://github.com/Quantum-L9/l9-ci-core/pull/336) | 11-21 12:11 | feat(security): audit Core's pinned toolchain with pip-audit (TOOLCHAIN-AUDIT) |
| [#338](https://github.com/Quantum-L9/l9-ci-core/pull/338) | 11-21 12:12 | feat(semgrep): admit Semgrep 1.186.0 with a hash-locked closure (step one) |
| [#339](https://github.com/Quantum-L9/l9-ci-core/pull/339) | 11-21 12:49 | ci(semgrep): activate Semgrep 1.186.0; prune audit exceptions it makes stale (step two) |

### l9-ci-sdk (25)

| PR | Merged (UTC) | Title |
|---|---|---|
| [#122](https://github.com/Quantum-L9/l9-ci-sdk/pull/122) | 11-20 19:26 | docs(adr): propose SDK ADR 0020 and ci_provider_invariants with witnesses (main-based; replaces #118) |
| [#123](https://github.com/Quantum-L9/l9-ci-sdk/pull/123) | 11-20 19:29 | feat(capabilities): complete capability inventory for one snapshot (main-based; replaces #119) |
| [#124](https://github.com/Quantum-L9/l9-ci-sdk/pull/124) | 11-20 19:31 | feat(rulesets): digest-locked rulepack composition and the donor harvest ledger (main-based; replaces #120) |
| [#125](https://github.com/Quantum-L9/l9-ci-sdk/pull/125) | 11-20 19:36 | feat(capabilities): serve JavaScript through the TypeScript Semgrep pack (main-based; replaces #121) |
| [#126](https://github.com/Quantum-L9/l9-ci-sdk/pull/126) | 11-20 19:48 | fix(ci): manifest reconcile detects drift and never pushes with GITHUB_TOKEN |
| [#127](https://github.com/Quantum-L9/l9-ci-sdk/pull/127) | 11-20 19:48 | refactor(capabilities): drop unused _ODOO_MANIFEST_NAMES (follow-up to #123) |
| [#128](https://github.com/Quantum-L9/l9-ci-sdk/pull/128) | 11-20 20:57 | feat(semgrep): required central runs disable nosem and scan a declared scope |
| [#117](https://github.com/Quantum-L9/l9-ci-sdk/pull/117) | 11-20 21:18 | ci(governance): restore drifted governance files |
| [#129](https://github.com/Quantum-L9/l9-ci-sdk/pull/129) | 11-20 21:52 | chore(toolchain): align every Core lock-owned tool pin with Core's toolchain lock |
| [#130](https://github.com/Quantum-L9/l9-ci-sdk/pull/130) | 11-20 22:19 | fix(capabilities): plan a Semgrep target only on files its scan reaches (P0: Cursor-Governance TS instance inc |
| [#131](https://github.com/Quantum-L9/l9-ci-sdk/pull/131) | 11-20 22:44 | fix(semgrep): count unfinished rule/file analysis as incomplete coverage (canary B5) |
| [#132](https://github.com/Quantum-L9/l9-ci-sdk/pull/132) | 11-20 22:58 | docs(adr): propose 0021, scoped consumer rulepack binding (canary B3; design for review) |
| [#133](https://github.com/Quantum-L9/l9-ci-sdk/pull/133) | 11-20 23:37 | fix(semgrep): give required runs a declared analysis budget (B5) |
| [#137](https://github.com/Quantum-L9/l9-ci-sdk/pull/137) | 11-21 00:16 | test(semgrep): witness the Cursor-Governance canary timeouts as incomplete coverage (B5 REMEDIATE) |
| [#141](https://github.com/Quantum-L9/l9-ci-sdk/pull/141) | 11-21 03:04 | fix(semgrep): Django rules apply only where Django is detected |
| [#140](https://github.com/Quantum-L9/l9-ci-sdk/pull/140) | 11-21 03:57 | fix(semgrep): hardcoded-credential requires a secret-shaped value, not a name |
| [#142](https://github.com/Quantum-L9/l9-ci-sdk/pull/142) | 11-21 03:58 | fix(semgrep): declare archived code (**/_archived/**) out of required scope, with its reason |
| [#134](https://github.com/Quantum-L9/l9-ci-sdk/pull/134) | 11-21 03:58 | fix(semgrep): tests in required scope; scope evidence in the finding bundle (B1+B2) |
| [#135](https://github.com/Quantum-L9/l9-ci-sdk/pull/135) | 11-21 03:59 | docs(capabilities): record the inventory's required-scope choice (#130 Codex gap, option 3) |
| [#143](https://github.com/Quantum-L9/l9-ci-sdk/pull/143) | 11-21 04:09 | fix(semgrep): report a shell=True site once; the L9 rule supersedes the registry duplicate |
| [#136](https://github.com/Quantum-L9/l9-ci-sdk/pull/136) | 11-21 04:20 | feat(semgrep): scoped consumer rulepack binding (ADR 0021 Accepted, B3) |
| [#138](https://github.com/Quantum-L9/l9-ci-sdk/pull/138) | 11-21 04:32 | feat(policy): central finding-waiver ledger l9.finding-waivers/v1 (CTO decision) |
| [#139](https://github.com/Quantum-L9/l9-ci-sdk/pull/139) | 11-21 04:42 | fix(semgrep): harden the provider argv; drop the inert nosemgrep (CTO REMEDIATE, P0) |
| [#144](https://github.com/Quantum-L9/l9-ci-sdk/pull/144) | 11-21 05:56 | feat(semgrep): classify findings new or pre-existing against a baseline commit (CENTRAL-DIFF, ADR 0023) |
| [#145](https://github.com/Quantum-L9/l9-ci-sdk/pull/145) | 11-21 06:09 | fix(semgrep): honour usedforsecurity=False for the registry SHA-1 rule (ADR 0024) |

### Cursor-Governance (46)

| PR | Merged (UTC) | Title |
|---|---|---|
| [#1062](https://github.com/Quantum-L9/Cursor-Governance/pull/1062) | 11-20 16:23 | fix(ci): refuse a pull-request full suite and wait on Core to apply Sonar |
| [#1073](https://github.com/Quantum-L9/Cursor-Governance/pull/1073) | 11-20 16:46 | fix(setup): start swarm children DEGRADED and let them materialize governance |
| [#1075](https://github.com/Quantum-L9/Cursor-Governance/pull/1075) | 11-20 17:01 | fix(modes): keep the mode state file out of git status in lane checkouts |
| [#1065](https://github.com/Quantum-L9/Cursor-Governance/pull/1065) | 11-20 17:22 | fix(skills): Claude's skill projection is the skill register |
| [#1064](https://github.com/Quantum-L9/Cursor-Governance/pull/1064) | 11-20 17:37 | fix(repo-sync): leave docs/plans in place during fast-forward |
| [#1079](https://github.com/Quantum-L9/Cursor-Governance/pull/1079) | 11-20 17:40 | fix(identity): Claude Code surfaces are web and cli; per-repo memory namespaces in multi-repo workspaces |
| [#1074](https://github.com/Quantum-L9/Cursor-Governance/pull/1074) | 11-20 17:59 | test(ci-parity): make Cursor posttool tests hermetic against Claude runtime markers |
| [#1066](https://github.com/Quantum-L9/Cursor-Governance/pull/1066) | 11-20 18:26 | feat(rules): load one speech contract on every governed reply |
| [#1068](https://github.com/Quantum-L9/Cursor-Governance/pull/1068) | 11-20 18:31 | fix(l9-plan): stamp-or-refuse campaign renders and route campaign latch repair |
| [#1071](https://github.com/Quantum-L9/Cursor-Governance/pull/1071) | 11-20 18:37 | fix(program-execution): bind admission evidence before a rendered plan claims |
| [#1072](https://github.com/Quantum-L9/Cursor-Governance/pull/1072) | 11-20 18:41 | test(program-execution): cover rendered-plan admission evidence binding |
| [#1080](https://github.com/Quantum-L9/Cursor-Governance/pull/1080) | 11-20 19:16 | feat(memory): memory works in every repository a Claude Code session works in |
| [#1081](https://github.com/Quantum-L9/Cursor-Governance/pull/1081) | 11-20 19:21 | fix(codeql): a failed language lookup is unknown, not nothing to analyze |
| [#1082](https://github.com/Quantum-L9/Cursor-Governance/pull/1082) | 11-20 19:29 | fix(deps): clear Dependabot and Semgrep Supply Chain advisories (virtualenv, Pillow, playwright) |
| [#1083](https://github.com/Quantum-L9/Cursor-Governance/pull/1083) | 11-20 19:33 | fix(cto-mode): one bootstrap path for swarm children |
| [#1076](https://github.com/Quantum-L9/Cursor-Governance/pull/1076) | 11-20 19:47 | docs(campaigns): CI Unified Leverage v1.7.1 pack: launch corrections and live campaign evidence |
| [#1084](https://github.com/Quantum-L9/Cursor-Governance/pull/1084) | 11-20 20:02 | docs(campaigns): CI configuration findings from the CI Unified Leverage canaries |
| [#1086](https://github.com/Quantum-L9/Cursor-Governance/pull/1086) | 11-20 20:56 | docs(campaigns): toolchain lock reach and Dependabot drift findings |
| [#1085](https://github.com/Quantum-L9/Cursor-Governance/pull/1085) | 11-20 20:56 | cto-mode: launch swarm children from Cursor-Governance; stub preflight; renderable Setup field |
| [#1088](https://github.com/Quantum-L9/Cursor-Governance/pull/1088) | 11-20 21:32 | ci: report every required check on merge_group so main can run a merge queue |
| [#1089](https://github.com/Quantum-L9/Cursor-Governance/pull/1089) | 11-20 22:09 | feat(host-binding): Claude Code binds the coding-agent execution projection by default |
| [#1094](https://github.com/Quantum-L9/Cursor-Governance/pull/1094) | 11-20 22:44 | ci: retire lint-autofix and on-org-update; keep the Biome workflow until a known-bad witness (CG-CUTOVER item  |
| [#1105](https://github.com/Quantum-L9/Cursor-Governance/pull/1105) | 11-21 01:04 | ci(authority): detect .github drift on main without bot publication |
| [#1104](https://github.com/Quantum-L9/Cursor-Governance/pull/1104) | 11-21 05:05 | fix(security): no environment, argv or document value chooses or becomes the code these scripts run (CG-CUTOVE |
| [#1091](https://github.com/Quantum-L9/Cursor-Governance/pull/1091) | 11-21 05:09 | docs(ci-ul): harvest ledger and Cursor-Governance close-out checklist |
| [#1102](https://github.com/Quantum-L9/Cursor-Governance/pull/1102) | 11-21 05:09 | fix(projection): regenerate identity-attribution bundle at .github 08b2d07 (unblocks /lcto) |
| [#1098](https://github.com/Quantum-L9/Cursor-Governance/pull/1098) | 11-21 05:18 | fix(memory): allowlist the retired-provider unset in setup.bootstrap_steps.sh (CG-CUTOVER item 6) |
| [#1090](https://github.com/Quantum-L9/Cursor-Governance/pull/1090) | 11-21 05:19 | feat(ci-parity): declared expect-fail fixture class for canary witnesses |
| [#1092](https://github.com/Quantum-L9/Cursor-Governance/pull/1092) | 11-21 05:19 | memory: hosted hook carrier calls the hook-principal tools (memory.ingest, not write_agent) |
| [#1093](https://github.com/Quantum-L9/Cursor-Governance/pull/1093) | 11-21 05:19 | ci: Core-locked toolchain pins and dead-workflow retirement (CG-CUTOVER items 1 and 2) |
| [#1095](https://github.com/Quantum-L9/Cursor-Governance/pull/1095) | 11-21 05:19 | docs(ci-ul): Cursor-Governance required-check cutover plan (CG-CUTOVER item 3) |
| [#1097](https://github.com/Quantum-L9/Cursor-Governance/pull/1097) | 11-21 05:20 | docs(ci-ul): CURSOR_CANARY result — CURSOR_CANARY_BLOCKED (CG-CUTOVER item 5) |
| [#1100](https://github.com/Quantum-L9/Cursor-Governance/pull/1100) | 11-21 05:20 | ci(sonarcloud): scan through Core's reusable Sonar step |
| [#1108](https://github.com/Quantum-L9/Cursor-Governance/pull/1108) | 11-21 05:20 | chore(archive): delete the archived workflow executors (#1106 section 3) |
| [#1107](https://github.com/Quantum-L9/Cursor-Governance/pull/1107) | 11-21 05:33 | ci-parity: block only on findings the change introduces; unknown never passes |
| [#1099](https://github.com/Quantum-L9/Cursor-Governance/pull/1099) | 11-21 05:34 | fix(excludes): every writer into a clone applies that clone's session excludes |
| [#1109](https://github.com/Quantum-L9/Cursor-Governance/pull/1109) | 11-21 05:44 | feat(merge): hand a green, authorized PR stack to GitHub's merge queue |
| [#1111](https://github.com/Quantum-L9/Cursor-Governance/pull/1111) | 11-21 05:57 | fix(ci-parity): declare the central Semgrep rules on the EIE nosemgrep canary |
| [#1110](https://github.com/Quantum-L9/Cursor-Governance/pull/1110) | 11-21 06:23 | chore(deps): bump the python-minor-patch group with 4 updates |
| [#1114](https://github.com/Quantum-L9/Cursor-Governance/pull/1114) | 11-21 06:23 | feat(semgrep): declare the Cursor rulepack for central binding (SDK ADR 0021, canary B3) |
| [#1115](https://github.com/Quantum-L9/Cursor-Governance/pull/1115) | 11-21 06:49 | secrets: register the memory credentials; SessionStart reports them by name, source and hook carrier |
| [#1116](https://github.com/Quantum-L9/Cursor-Governance/pull/1116) | 11-21 07:01 | fix(ci-parity): EIE canary expectations for central semgrep at SDK 4a887396 |
| [#1117](https://github.com/Quantum-L9/Cursor-Governance/pull/1117) | 11-21 07:02 | secrets: governed provisioning script for the l9-memory-hooks principal (dry run by default) |
| [#1112](https://github.com/Quantum-L9/Cursor-Governance/pull/1112) | 11-21 07:37 | docs(ci-ul): CURSOR_CANARY_PASS on the PIN-ADVANCE-3 pins |
| [#1118](https://github.com/Quantum-L9/Cursor-Governance/pull/1118) | 11-21 08:04 | docs(ci-ul): full harvest fields and delivery receipts for C1 to C5 |
| [#1119](https://github.com/Quantum-L9/Cursor-Governance/pull/1119) | 11-21 08:16 | fix(tests): allow exactly Core's reusable Sonar step in the Core-caller guard (CG-SONAR-CONFLICT) |

### Enrichment.Inference.Engine (16)

| PR | Merged (UTC) | Title |
|---|---|---|
| [#361](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/361) | 11-20 16:18 | chore(deps): bump fastapi from 0.162.2 to 0.162.4 in the python-minor-patch group |
| [#362](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/362) | 11-20 16:18 | chore(deps): bump types-pyyaml from 6.0.12.20261103 to 6.0.12.20261111 |
| [#363](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/363) | 11-20 16:18 | chore(deps): bump actions/checkout from 4.3.1 to 4.4.0 in the actions-minor-patch group |
| [#364](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/364) | 11-20 16:19 | fix(ci): pin current CEG and Gate peers to the design-pack specimen |
| [#365](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/365) | 11-20 16:42 | ci: keep pull-request pytest on the contract selection |
| [#328](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/328) | 11-20 16:55 | refactor(crm): make the writeback layer provider-agnostic |
| [#366](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/366) | 11-20 17:23 | fix(ci): secret-scan jobs report NOT_EXECUTED instead of ending green |
| [#367](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/367) | 11-20 18:09 | fix(security): scan every path with Gitleaks and verify the binary's checksum |
| [#368](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/368) | 11-20 18:42 | ci(coderabbit): inherit the organization review policy |
| [#369](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/369) | 11-20 19:34 | ci(actions): pin every third-party action to a commit SHA |
| [#371](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/371) | 11-20 20:56 | ci(sonar): import coverage from the PR-fast test run into SonarCloud |
| [#372](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/372) | 11-20 21:20 | ci(sonar): send the deep plan's full-catalog coverage to main's analysis |
| [#373](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/373) | 11-20 22:09 | ci: never let a push to main cancel a deep workflow_dispatch run |
| [#374](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/374) | 11-20 22:44 | ci(toolchain): align uv and the gitleaks hook to Core's toolchain lock |
| [#375](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/375) | 11-20 22:58 | ci: make docs-sync and docs-consistency able to fail; PR-size says advisory |
| [#370](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/370) | 11-20 23:24 | fix(ci): grant the release analysis job contents: read only |

### Cognitive.Engine.Graphs (11)

| PR | Merged (UTC) | Title |
|---|---|---|
| [#508](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/508) | 11-20 16:18 | fix(match): lift the candidate fields the Odoo mapper reads |
| [#514](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/514) | 11-20 16:42 | ci: keep one pull-request pytest owner and one deep plan |
| [#515](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/515) | 11-20 17:42 | fix(ci): report what the secrets scan, dependency review and coverage upload did |
| [#516](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/516) | 11-20 18:27 | ci(coderabbit): inherit the organization review policy |
| [#518](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/518) | 11-20 20:34 | ci(coverage): retire the dead Codecov upload in dev-layer-gmp (T42) |
| [#519](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/519) | 11-20 20:34 | ci(contracts): run on push to main only, so PR commits are not scanned twice |
| [#520](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/520) | 11-20 21:33 | ci: retire dev-layer-gmp.yml, which never ran a test |
| [#523](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/523) | 11-20 21:52 | ci(docs-code-sync): drop path filters for directories that do not exist |
| [#521](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/521) | 11-20 22:09 | ci(sonar): CI-based SonarQube Cloud analysis, replacing Automatic Analysis |
| [#522](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/522) | 11-20 22:44 | ci: one owner per lint and contract check; central Core covers PRs |
| [#524](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/524) | 11-21 08:04 | ci(deps): align CEG's Core-owned tool pins with Core's toolchain lock |
