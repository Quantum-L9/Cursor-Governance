# CI Unified Leverage v1.7.1 — close-out receipt

**Status: DRAFT (07:40Z 2026-11-21).** Rows marked OPEN are not met. This file is final only when every X row says DONE with evidence.

Campaign scope (operator, 2026-11-20 21:50Z): cut **Cursor-Governance** over to organization CI, debug it and prove it works, so the
organization is ready to roll out. Rolling out to other repositories is a separate campaign.

## Close-out checklist

| # | Item | Status | Evidence |
|---|---|---|---|
| X1 | Promotion live: the required job runs current Core and SDK code | DONE | org-ci pins SDK `4a887396` with CENTRAL-DIFF, the waiver ledger and B3 (Core [#323](https://github.com/Quantum-L9/l9-ci-core/pull/323) + [#324](https://github.com/Quantum-L9/l9-ci-core/pull/324), merged 06:36Z). Verified on real Cursor-Governance PRs #1112, #1113, #1115 (Analyze green). |
| X2 | Core consumer gaps C1-C5 | DONE | Security scans in org-ci: Core [#312](https://github.com/Quantum-L9/l9-ci-core/pull/312) merged 08:16Z (the required job enforces Core's security scan); pip-audit audits the consumer's full resolved lock, [#330](https://github.com/Quantum-L9/l9-ci-core/pull/330) merged 09:07Z. Supply chain #304/#309, toolchain drift #302, conflict markers #300, housekeeping classification #310 merged. |
| X3 | One toolchain-lock source reaches every repository; Dependabot can't bump Core-owned tools | PARTIAL | Core #295 merged. CEG [#524](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/524) merged. Core [#328](https://github.com/Quantum-L9/l9-ci-core/pull/328) merged 10:2xZ at `03028b6a` (org-ci activates push semantics + full-lock pip-audit; canary run 44891625020: CG pass: improved, 4 repos kept green). Core [#334](https://github.com/Quantum-L9/l9-ci-core/pull/334) (pip-audit prints its export and package count) merged at `802ffda7`, activation pending. EIE [#377](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/377) under re-verification. Full-lock evidence at #328 head `27b80948`: EIE security leg job 136808505872 took the `uv.lock` export path (`--no-deps`), `PIP_AUDIT_OUTCOME: executed_pass`, 106 locked packages. |
| X4 | Expensive checks run nightly, only where code changed; nightly findings land somewhere owned | IN PROGRESS | Planner + App-token apply merged (Core #290, #299; app `l9-nightly-dispatch`). Nightly findings sink (row 24) merged: Core [#333](https://github.com/Quantum-L9/l9-ci-core/pull/333) at `12f92e7f` (SARIF to code scanning, one rolling "Nightly findings" issue, ratchet). Proof run [44891263316](https://github.com/Quantum-L9/l9-ci-core/actions/runs/44891263316): the full nightly scan of Cursor-Governance ran through SARIF projection (python + typescript), then the token mint failed: `The permissions requested are not granted to this installation` (app 5854787 asks for contents:read, security-events:write, issues:write). **Blocked on the operator** granting the App those permissions; then two re-runs prove upload + in-place issue edit. Ownership: the nightly issue is the automated inventory; CG #1106 stays the hand-curated checklist for its 29 sites and links to it. |
| X5 | Cursor-Governance cut over, `CURSOR_CANARY_PASS` | DONE | [#1112](https://github.com/Quantum-L9/Cursor-Governance/pull/1112) merged 07:37Z: Gates 0-4 PASS on the PIN-ADVANCE-3 pins; gate 2.4 witnessed centrally (the four `.semgrep/l9-pr.yml` rules fire in the central bundle). |
| X6 | Secondary canaries recorded | DONE (EIE) | EIE [#378](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/378): run 1 (central run 44874376220) and run 2 (44878546690, job 136768547018) Gates 2-3 PASS; in run 2 only the 3 canary findings block and 33 pre-existing do not. CEG canary #517: earlier run recorded; not re-run on PIN-ADVANCE-3. |
| X7 | Harvest ledgered with destinations | DONE | `HARVEST_LEDGER.md` index merged (#1091); full `HARVEST.md` fields for promoted rows C1-C5 merged ([#1118](https://github.com/Quantum-L9/Cursor-Governance/pull/1118)). |
| X8 | Merge queue on Cursor-Governance main, driven by `/l9-pr-remediation` | OPEN (operator) | Skill support merged ([#1109](https://github.com/Quantum-L9/Cursor-Governance/pull/1109)); throwaway proof PR #1113 ready. Waiting on the operator's ruleset change (20855699). |
| X9 | Close-out evidence | IN PROGRESS | This file. |
| X10 | CTO CI-run audit | DONE (findings), OPEN (applied) | See "CI-run audit" below. |

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

## Findings rows added this session

Rows 17-27 in `CI_CONFIG_FINDINGS.md`. Row 27 (new): canary consumer legs inherited the Core PR's `pull_request` event, so Cursor-Governance's
`make test` refused ("HEAD is not a two-parent merge commit") at both pins and masked any CG regression. Fix: Core #328 (push semantics for consumer legs).
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

## Rollout backlog (next campaign)

CEG and EIE cutover using HARVEST_LEDGER rows; IB-Odoo_19 framework checks (S1a-S1f); `l9-semantic-compiler-engine` SHA-1 sites (fixed upstream by SDK #145, needs a pin past CENTRAL-DIFF there); Core ADR 0023 amendment; Analyze-check rename (operator ruleset edit).

## Merged pull requests (2026-11-20 16:00Z to close-out)

### l9-ci-core (37)

| PR | Merged (UTC) | Title |
|---|---|---|
| [#308](https://github.com/Quantum-L9/l9-ci-core/pull/308) | 00:16 | ci(org-ci): activate SDK fbe14fec — advance Core pins to eba72ac3 (P0 step two) |
| [#309](https://github.com/Quantum-L9/l9-ci-core/pull/309) | 00:29 | feat(supply-chain): Core-owned per-repository licence exemptions |
| [#310](https://github.com/Quantum-L9/l9-ci-core/pull/310) | 01:35 | L2-closeout housekeeping audit: classify every Analyze (central Core) step; housekeeping never  |
| [#302](https://github.com/Quantum-L9/l9-ci-core/pull/302) | 01:35 | L2-closeout item 2: report toolchain drift in Analyze (central Core), advisory |
| [#300](https://github.com/Quantum-L9/l9-ci-core/pull/300) | 01:35 | L2-closeout item 3: repository verification fails an unresolved merge conflict |
| [#311](https://github.com/Quantum-L9/l9-ci-core/pull/311) | 02:04 | ci(canary): blocking promotion canary for changes to Analyze (central Core) |
| [#313](https://github.com/Quantum-L9/l9-ci-core/pull/313) | 03:04 | fix(canary): run the base pins inline; repair main's stale canary render |
| [#315](https://github.com/Quantum-L9/l9-ci-core/pull/315) | 03:35 | fix(sdk): promote SDK 2796d7a4 (#141 framework-scoped Semgrep rules) (PIN-ADVANCE-1 step one) |
| [#316](https://github.com/Quantum-L9/l9-ci-core/pull/316) | 03:48 | ci(org-ci): activate SDK 2796d7a4 — advance Core pins to df3b2eaf (PIN-ADVANCE-1 step two) |
| [#318](https://github.com/Quantum-L9/l9-ci-core/pull/318) | 04:10 | fix(sdk): promote SDK 1d632037 (#140 credentials, #142 _archived, #134 scope) (PIN-ADVANCE-2 st |
| [#320](https://github.com/Quantum-L9/l9-ci-core/pull/320) | 04:21 | test(provisioning): use a non-secret-shaped read-token fixture (unblocks PIN-ADVANCE-2) |
| [#321](https://github.com/Quantum-L9/l9-ci-core/pull/321) | 04:42 | fix(sdk): make SDK 47ae3ac5 the default, not 1d632037 (PIN-ADVANCE-2 redirect, step one) |
| [#322](https://github.com/Quantum-L9/l9-ci-core/pull/322) | 04:54 | ci(org-ci): activate SDK 47ae3ac5 — advance Core pins to 2ff05a03 (PIN-ADVANCE-2c step two) |
| [#317](https://github.com/Quantum-L9/l9-ci-core/pull/317) | 05:34 | feat(canary): run the SDK revision an admission-only pull request admits (row 25) |
| [#323](https://github.com/Quantum-L9/l9-ci-core/pull/323) | 06:23 | feat(sdk): admit SDK 4a887396 and the action inputs CENTRAL-DIFF needs (PIN-ADVANCE-3 step one) |
| [#324](https://github.com/Quantum-L9/l9-ci-core/pull/324) | 06:36 | ci(org-ci): activate SDK 4a887396 with CENTRAL-DIFF, the waiver ledger and B3 (PIN-ADVANCE-3 st |
| [#325](https://github.com/Quantum-L9/l9-ci-core/pull/325) | 06:49 | ci(org-ci): upload every instance bundle beside the central set (SDK ADR 0021 Core change 2) |
| [#289](https://github.com/Quantum-L9/l9-ci-core/pull/289) | 19:03 | ci(sonar): import coverage from Core's existing test runs into its Sonar analysis (L2b) |
| [#283](https://github.com/Quantum-L9/l9-ci-core/pull/283) | 19:03 | docs(adr): propose Core ADRs 0001 and 0002 with witnessed ci_runtime_invariants (L2 PR 2a) |
| [#285](https://github.com/Quantum-L9/l9-ci-core/pull/285) | 19:04 | fix(security): report each scan's real outcome in security.yml (L2 T04) |
| [#286](https://github.com/Quantum-L9/l9-ci-core/pull/286) | 19:05 | feat(actions): plan and aggregate every required provider/target instance (L2 PR 2b, stacked on |
| [#287](https://github.com/Quantum-L9/l9-ci-core/pull/287) | 19:07 | feat(stamp): inherit tool configuration from Core at runtime (L2 PR 2c, stacked on #286) |
| [#288](https://github.com/Quantum-L9/l9-ci-core/pull/288) | 19:08 | fix(tools): authenticate the registry fetch from private Quantum-L9/.github |
| [#284](https://github.com/Quantum-L9/l9-ci-core/pull/284) | 19:12 | feat(settings): GitHub settings-as-code engine and reusable runner |
| [#290](https://github.com/Quantum-L9/l9-ci-core/pull/290) | 19:48 | Nightly scheduling: plan from the registry projection, change-gate Core's deep suite, closed ap |
| [#291](https://github.com/Quantum-L9/l9-ci-core/pull/291) | 20:12 | Regenerate the required-repositories projection from .github@08b2d07 (adds CEG, EIE and 25 more |
| [#292](https://github.com/Quantum-L9/l9-ci-core/pull/292) | 21:19 | L2f step 1: re-pin org-ci to main, guard self-pin ancestry, promote SDK dc783c64 |
| [#293](https://github.com/Quantum-L9/l9-ci-core/pull/293) | 21:20 | L2g: attest the operator's Core main protection, run required checks on the merge queue, declar |
| [#294](https://github.com/Quantum-L9/l9-ci-core/pull/294) | 21:52 | L2f step 2: activate SDK dc783c64 and make Analyze (central Core) the every-instance verdict |
| [#295](https://github.com/Quantum-L9/l9-ci-core/pull/295) | 22:09 | L2h: toolchain alignment across every declaration surface; Core on its own lock; Dependabot ign |
| [#299](https://github.com/Quantum-L9/l9-ci-core/pull/299) | 22:44 | L2-closeout item 4: open nightly apply with an App-minted token; admit Cursor-Governance |
| [#305](https://github.com/Quantum-L9/l9-ci-core/pull/305) | 22:58 | P0 step one: promote SDK 9af1a202 (scan-scope planning fixes the Cursor-Governance TypeScript-i |
| [#301](https://github.com/Quantum-L9/l9-ci-core/pull/301) | 22:58 | feat(run-sonar): one reusable Core Sonar step that reuses the consumer's coverage |
| [#298](https://github.com/Quantum-L9/l9-ci-core/pull/298) | 23:24 | L2-closeout item 1 (step one): security.yml scans a consumer on what it changes, with the Core  |
| [#306](https://github.com/Quantum-L9/l9-ci-core/pull/306) | 23:37 | Item 8 (a): publish the required check name once in the runtime contract (current value) |
| [#304](https://github.com/Quantum-L9/l9-ci-core/pull/304) | 23:50 | L2-closeout item 5 (step one): one Core supply-chain lane with per-repository policy data |
| [#307](https://github.com/Quantum-L9/l9-ci-core/pull/307) | 23:50 | fix(sdk): promote SDK fbe14fec (#133 declared analysis budget) (P0 step one) |

### l9-ci-sdk (25)

| PR | Merged (UTC) | Title |
|---|---|---|
| [#137](https://github.com/Quantum-L9/l9-ci-sdk/pull/137) | 00:16 | test(semgrep): witness the Cursor-Governance canary timeouts as incomplete coverage (B5 REMEDIA |
| [#141](https://github.com/Quantum-L9/l9-ci-sdk/pull/141) | 03:04 | fix(semgrep): Django rules apply only where Django is detected |
| [#140](https://github.com/Quantum-L9/l9-ci-sdk/pull/140) | 03:57 | fix(semgrep): hardcoded-credential requires a secret-shaped value, not a name |
| [#142](https://github.com/Quantum-L9/l9-ci-sdk/pull/142) | 03:58 | fix(semgrep): declare archived code (**/_archived/**) out of required scope, with its reason |
| [#134](https://github.com/Quantum-L9/l9-ci-sdk/pull/134) | 03:58 | fix(semgrep): tests in required scope; scope evidence in the finding bundle (B1+B2) |
| [#135](https://github.com/Quantum-L9/l9-ci-sdk/pull/135) | 03:59 | docs(capabilities): record the inventory's required-scope choice (#130 Codex gap, option 3) |
| [#143](https://github.com/Quantum-L9/l9-ci-sdk/pull/143) | 04:09 | fix(semgrep): report a shell=True site once; the L9 rule supersedes the registry duplicate |
| [#136](https://github.com/Quantum-L9/l9-ci-sdk/pull/136) | 04:20 | feat(semgrep): scoped consumer rulepack binding (ADR 0021 Accepted, B3) |
| [#138](https://github.com/Quantum-L9/l9-ci-sdk/pull/138) | 04:32 | feat(policy): central finding-waiver ledger l9.finding-waivers/v1 (CTO decision) |
| [#139](https://github.com/Quantum-L9/l9-ci-sdk/pull/139) | 04:42 | fix(semgrep): harden the provider argv; drop the inert nosemgrep (CTO REMEDIATE, P0) |
| [#144](https://github.com/Quantum-L9/l9-ci-sdk/pull/144) | 05:56 | feat(semgrep): classify findings new or pre-existing against a baseline commit (CENTRAL-DIFF, A |
| [#145](https://github.com/Quantum-L9/l9-ci-sdk/pull/145) | 06:09 | fix(semgrep): honour usedforsecurity=False for the registry SHA-1 rule (ADR 0024) |
| [#122](https://github.com/Quantum-L9/l9-ci-sdk/pull/122) | 19:26 | docs(adr): propose SDK ADR 0020 and ci_provider_invariants with witnesses (main-based; replaces |
| [#123](https://github.com/Quantum-L9/l9-ci-sdk/pull/123) | 19:29 | feat(capabilities): complete capability inventory for one snapshot (main-based; replaces #119) |
| [#124](https://github.com/Quantum-L9/l9-ci-sdk/pull/124) | 19:31 | feat(rulesets): digest-locked rulepack composition and the donor harvest ledger (main-based; re |
| [#125](https://github.com/Quantum-L9/l9-ci-sdk/pull/125) | 19:36 | feat(capabilities): serve JavaScript through the TypeScript Semgrep pack (main-based; replaces  |
| [#126](https://github.com/Quantum-L9/l9-ci-sdk/pull/126) | 19:48 | fix(ci): manifest reconcile detects drift and never pushes with GITHUB_TOKEN |
| [#127](https://github.com/Quantum-L9/l9-ci-sdk/pull/127) | 19:48 | refactor(capabilities): drop unused _ODOO_MANIFEST_NAMES (follow-up to #123) |
| [#128](https://github.com/Quantum-L9/l9-ci-sdk/pull/128) | 20:57 | feat(semgrep): required central runs disable nosem and scan a declared scope |
| [#117](https://github.com/Quantum-L9/l9-ci-sdk/pull/117) | 21:18 | ci(governance): restore drifted governance files |
| [#129](https://github.com/Quantum-L9/l9-ci-sdk/pull/129) | 21:52 | chore(toolchain): align every Core lock-owned tool pin with Core's toolchain lock |
| [#130](https://github.com/Quantum-L9/l9-ci-sdk/pull/130) | 22:19 | fix(capabilities): plan a Semgrep target only on files its scan reaches (P0: Cursor-Governance  |
| [#131](https://github.com/Quantum-L9/l9-ci-sdk/pull/131) | 22:44 | fix(semgrep): count unfinished rule/file analysis as incomplete coverage (canary B5) |
| [#132](https://github.com/Quantum-L9/l9-ci-sdk/pull/132) | 22:58 | docs(adr): propose 0021, scoped consumer rulepack binding (canary B3; design for review) |
| [#133](https://github.com/Quantum-L9/l9-ci-sdk/pull/133) | 23:37 | fix(semgrep): give required runs a declared analysis budget (B5) |

### Cursor-Governance (44)

| PR | Merged (UTC) | Title |
|---|---|---|
| [#1105](https://github.com/Quantum-L9/Cursor-Governance/pull/1105) | 01:04 | ci(authority): detect .github drift on main without bot publication |
| [#1104](https://github.com/Quantum-L9/Cursor-Governance/pull/1104) | 05:05 | fix(security): no environment, argv or document value chooses or becomes the code these scripts |
| [#1091](https://github.com/Quantum-L9/Cursor-Governance/pull/1091) | 05:09 | docs(ci-ul): harvest ledger and Cursor-Governance close-out checklist |
| [#1102](https://github.com/Quantum-L9/Cursor-Governance/pull/1102) | 05:09 | fix(projection): regenerate identity-attribution bundle at .github 08b2d07 (unblocks /lcto) |
| [#1098](https://github.com/Quantum-L9/Cursor-Governance/pull/1098) | 05:18 | fix(memory): allowlist the retired-provider unset in setup.bootstrap_steps.sh (CG-CUTOVER item  |
| [#1093](https://github.com/Quantum-L9/Cursor-Governance/pull/1093) | 05:19 | ci: Core-locked toolchain pins and dead-workflow retirement (CG-CUTOVER items 1 and 2) |
| [#1095](https://github.com/Quantum-L9/Cursor-Governance/pull/1095) | 05:19 | docs(ci-ul): Cursor-Governance required-check cutover plan (CG-CUTOVER item 3) |
| [#1090](https://github.com/Quantum-L9/Cursor-Governance/pull/1090) | 05:19 | feat(ci-parity): declared expect-fail fixture class for canary witnesses |
| [#1092](https://github.com/Quantum-L9/Cursor-Governance/pull/1092) | 05:19 | memory: hosted hook carrier calls the hook-principal tools (memory.ingest, not write_agent) |
| [#1108](https://github.com/Quantum-L9/Cursor-Governance/pull/1108) | 05:20 | chore(archive): delete the archived workflow executors (#1106 section 3) |
| [#1100](https://github.com/Quantum-L9/Cursor-Governance/pull/1100) | 05:20 | ci(sonarcloud): scan through Core's reusable Sonar step |
| [#1097](https://github.com/Quantum-L9/Cursor-Governance/pull/1097) | 05:20 | docs(ci-ul): CURSOR_CANARY result — CURSOR_CANARY_BLOCKED (CG-CUTOVER item 5) |
| [#1107](https://github.com/Quantum-L9/Cursor-Governance/pull/1107) | 05:33 | ci-parity: block only on findings the change introduces; unknown never passes |
| [#1099](https://github.com/Quantum-L9/Cursor-Governance/pull/1099) | 05:34 | fix(excludes): every writer into a clone applies that clone's session excludes |
| [#1109](https://github.com/Quantum-L9/Cursor-Governance/pull/1109) | 05:44 | feat(merge): hand a green, authorized PR stack to GitHub's merge queue |
| [#1111](https://github.com/Quantum-L9/Cursor-Governance/pull/1111) | 05:57 | fix(ci-parity): declare the central Semgrep rules on the EIE nosemgrep canary |
| [#1110](https://github.com/Quantum-L9/Cursor-Governance/pull/1110) | 06:23 | chore(deps): bump the python-minor-patch group with 4 updates |
| [#1114](https://github.com/Quantum-L9/Cursor-Governance/pull/1114) | 06:23 | feat(semgrep): declare the Cursor rulepack for central binding (SDK ADR 0021, canary B3) |
| [#1115](https://github.com/Quantum-L9/Cursor-Governance/pull/1115) | 06:49 | secrets: register the memory credentials; SessionStart reports them by name, source and hook ca |
| [#1116](https://github.com/Quantum-L9/Cursor-Governance/pull/1116) | 07:01 | fix(ci-parity): EIE canary expectations for central semgrep at SDK 4a887396 |
| [#1117](https://github.com/Quantum-L9/Cursor-Governance/pull/1117) | 07:02 | secrets: governed provisioning script for the l9-memory-hooks principal (dry run by default) |
| [#1112](https://github.com/Quantum-L9/Cursor-Governance/pull/1112) | 07:37 | docs(ci-ul): CURSOR_CANARY_PASS on the PIN-ADVANCE-3 pins |
| [#1062](https://github.com/Quantum-L9/Cursor-Governance/pull/1062) | 16:23 | fix(ci): refuse a pull-request full suite and wait on Core to apply Sonar |
| [#1073](https://github.com/Quantum-L9/Cursor-Governance/pull/1073) | 16:46 | fix(setup): start swarm children DEGRADED and let them materialize governance |
| [#1075](https://github.com/Quantum-L9/Cursor-Governance/pull/1075) | 17:01 | fix(modes): keep the mode state file out of git status in lane checkouts |
| [#1065](https://github.com/Quantum-L9/Cursor-Governance/pull/1065) | 17:22 | fix(skills): Claude's skill projection is the skill register |
| [#1064](https://github.com/Quantum-L9/Cursor-Governance/pull/1064) | 17:37 | fix(repo-sync): leave docs/plans in place during fast-forward |
| [#1079](https://github.com/Quantum-L9/Cursor-Governance/pull/1079) | 17:40 | fix(identity): Claude Code surfaces are web and cli; per-repo memory namespaces in multi-repo w |
| [#1074](https://github.com/Quantum-L9/Cursor-Governance/pull/1074) | 17:59 | test(ci-parity): make Cursor posttool tests hermetic against Claude runtime markers |
| [#1066](https://github.com/Quantum-L9/Cursor-Governance/pull/1066) | 18:26 | feat(rules): load one speech contract on every governed reply |
| [#1068](https://github.com/Quantum-L9/Cursor-Governance/pull/1068) | 18:31 | fix(l9-plan): stamp-or-refuse campaign renders and route campaign latch repair |
| [#1071](https://github.com/Quantum-L9/Cursor-Governance/pull/1071) | 18:37 | fix(program-execution): bind admission evidence before a rendered plan claims |
| [#1072](https://github.com/Quantum-L9/Cursor-Governance/pull/1072) | 18:41 | test(program-execution): cover rendered-plan admission evidence binding |
| [#1080](https://github.com/Quantum-L9/Cursor-Governance/pull/1080) | 19:16 | feat(memory): memory works in every repository a Claude Code session works in |
| [#1081](https://github.com/Quantum-L9/Cursor-Governance/pull/1081) | 19:21 | fix(codeql): a failed language lookup is unknown, not nothing to analyze |
| [#1082](https://github.com/Quantum-L9/Cursor-Governance/pull/1082) | 19:29 | fix(deps): clear Dependabot and Semgrep Supply Chain advisories (virtualenv, Pillow, playwright |
| [#1083](https://github.com/Quantum-L9/Cursor-Governance/pull/1083) | 19:33 | fix(cto-mode): one bootstrap path for swarm children |
| [#1076](https://github.com/Quantum-L9/Cursor-Governance/pull/1076) | 19:47 | docs(campaigns): CI Unified Leverage v1.7.1 pack: launch corrections and live campaign evidence |
| [#1084](https://github.com/Quantum-L9/Cursor-Governance/pull/1084) | 20:02 | docs(campaigns): CI configuration findings from the CI Unified Leverage canaries |
| [#1085](https://github.com/Quantum-L9/Cursor-Governance/pull/1085) | 20:56 | cto-mode: launch swarm children from Cursor-Governance; stub preflight; renderable Setup field |
| [#1086](https://github.com/Quantum-L9/Cursor-Governance/pull/1086) | 20:56 | docs(campaigns): toolchain lock reach and Dependabot drift findings |
| [#1088](https://github.com/Quantum-L9/Cursor-Governance/pull/1088) | 21:32 | ci: report every required check on merge_group so main can run a merge queue |
| [#1089](https://github.com/Quantum-L9/Cursor-Governance/pull/1089) | 22:09 | feat(host-binding): Claude Code binds the coding-agent execution projection by default |
| [#1094](https://github.com/Quantum-L9/Cursor-Governance/pull/1094) | 22:44 | ci: retire lint-autofix and on-org-update; keep the Biome workflow until a known-bad witness (C |

### Cognitive.Engine.Graphs (10)

| PR | Merged (UTC) | Title |
|---|---|---|
| [#508](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/508) | 16:18 | fix(match): lift the candidate fields the Odoo mapper reads |
| [#514](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/514) | 16:42 | ci: keep one pull-request pytest owner and one deep plan |
| [#515](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/515) | 17:42 | fix(ci): report what the secrets scan, dependency review and coverage upload did |
| [#516](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/516) | 18:27 | ci(coderabbit): inherit the organization review policy |
| [#519](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/519) | 20:34 | ci(contracts): run on push to main only, so PR commits are not scanned twice |
| [#518](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/518) | 20:34 | ci(coverage): retire the dead Codecov upload in dev-layer-gmp (T42) |
| [#520](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/520) | 21:33 | ci: retire dev-layer-gmp.yml, which never ran a test |
| [#523](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/523) | 21:52 | ci(docs-code-sync): drop path filters for directories that do not exist |
| [#521](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/521) | 22:09 | ci(sonar): CI-based SonarQube Cloud analysis, replacing Automatic Analysis |
| [#522](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/522) | 22:44 | ci: one owner per lint and contract check; central Core covers PRs |

### Enrichment.Inference.Engine (16)

| PR | Merged (UTC) | Title |
|---|---|---|
| [#363](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/363) | 16:18 | chore(deps): bump actions/checkout from 4.3.1 to 4.4.0 in the actions-minor-patch group |
| [#361](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/361) | 16:18 | chore(deps): bump fastapi from 0.162.2 to 0.162.4 in the python-minor-patch group |
| [#362](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/362) | 16:18 | chore(deps): bump types-pyyaml from 6.0.12.20261103 to 6.0.12.20261111 |
| [#364](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/364) | 16:19 | fix(ci): pin current CEG and Gate peers to the design-pack specimen |
| [#365](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/365) | 16:42 | ci: keep pull-request pytest on the contract selection |
| [#328](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/328) | 16:55 | refactor(crm): make the writeback layer provider-agnostic |
| [#366](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/366) | 17:23 | fix(ci): secret-scan jobs report NOT_EXECUTED instead of ending green |
| [#367](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/367) | 18:09 | fix(security): scan every path with Gitleaks and verify the binary's checksum |
| [#368](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/368) | 18:42 | ci(coderabbit): inherit the organization review policy |
| [#369](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/369) | 19:34 | ci(actions): pin every third-party action to a commit SHA |
| [#371](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/371) | 20:56 | ci(sonar): import coverage from the PR-fast test run into SonarCloud |
| [#372](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/372) | 21:20 | ci(sonar): send the deep plan's full-catalog coverage to main's analysis |
| [#373](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/373) | 22:09 | ci: never let a push to main cancel a deep workflow_dispatch run |
| [#374](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/374) | 22:44 | ci(toolchain): align uv and the gitleaks hook to Core's toolchain lock |
| [#375](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/375) | 22:58 | ci: make docs-sync and docs-consistency able to fail; PR-size says advisory |
| [#370](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/370) | 23:24 | fix(ci): grant the release analysis job contents: read only |

