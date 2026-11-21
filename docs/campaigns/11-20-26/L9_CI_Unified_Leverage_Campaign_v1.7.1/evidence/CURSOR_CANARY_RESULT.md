# CURSOR_CANARY result: `CURSOR_CANARY_BLOCKED` (one gate item open: 2.4, blocked on PIN-ADVANCE-3)

## Re-run on current `main`, 2026-11-21 (outranks every 2026-11-20 verdict below)

Lane CG-CANARY-PASS (X5), against `CURSOR_CANARY.md` Gates 0 to 4. A gate is PASS only where its
evidence holds on a promoted revision; otherwise the exact blocker is named.

### Bound revisions

| Item | Value |
|---|---|
| Cursor-Governance `main` | `991f2c18cefd9aba6f858f557cf9d24c9605f5b5` (after #1104, #1108 and the rest of the queue) |
| Core `main` | `56fe591` (#317); org-ci action pins `2ff05a03a1edb8a9a4602a915fb839dcadf21d56` (#321/#322), an ancestor of Core `main` |
| SDK provisioned by Core | `47ae3ac5bc8c1a14cc33e4985ce392996cd27ccc`, an ancestor of SDK `main` (`ad7727ec`) |
| Organization ruleset 21895545 | required workflow `l9-ci-core/.github/workflows/org-ci.yml@refs/heads/main`; required check `Analyze (central Core)` |
| Repository ruleset 20855699 | required: Lint and Type Check, Test Suite, Root-file append-only gate, governance-self-check, repo-hygiene |
| Canary scratch head | PR [#1096](https://github.com/Quantum-L9/Cursor-Governance/pull/1096) (DO NOT MERGE), merged with `main` `8a53c26c`: `73ad9c04` (Semgrep witnesses, Biome fixture removed for the run) and `fa1ec0e9` (Biome witness) |

### Verdict per gate

| Gate | Verdict | Evidence |
|---|---|---|
| 0. Prerequisites and permission | **PASS** | Core and SDK revisions above are promoted (on their `main`); no unmerged Core or SDK PR is claimed as installed. No merge, ruleset or permission change was made by this lane. |
| 1. Consumer baseline | **PASS** | Baseline of 2026-11-20 below (run 44819081765) plus current `main`: Lint and Type Check, Biome (SDK) and repo-hygiene green at `991f2c18`; last merged PR head #1108 `22710d5c` green on all six required checks including `Analyze (central Core)`. Issue #1106: `main` went from 29 blocking central findings to 0 (#1104, #1108). Custom-rule inventory: 4 rules in `.semgrep/l9-pr.yml`, enforced by `ops/scripts/run_pr_security.sh` in `make pr`. CodeQL: `codeql.yml` on push to `main` succeeded at `089214e4` (run 44870443753); `codeql-nightly.yml` security-extended last succeeded at `263216c1` (run 44731752123), reused per Gate 3. |
| 2.1 Ruleset selected org-ci and evaluated the exact head | **PASS** | `Analyze (central Core)` on #1096 `73ad9c04` ([run 44870986301](https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44870986301/job/136745236286)) and on #1108 `22710d5c` |
| 2.2 Every applicable language has an instance, a valid not-applicable reason, or a fail | **PASS** | Same run: `semgrep:language:python` planned and run; "not planned semgrep:language:typescript: no typescript or javascript file this target analyzes is inside the declared scan scope: 2 file(s) excluded by directory_names"; `javascript` and `shell` visible, unsupported, not planned |
| 2.3 Central config resolved from Core/SDK, not copied | **PASS** | SDK `47ae3ac5` provisioned by Core; Semgrep 1.171.0 and Biome 2.5.8 from Core locks; policy and identity maps under `.l9/runtime/org-governance/` |
| 2.4 Cursor-owned rules effective in a scoped execution | **BLOCKED on PIN-ADVANCE-3** | Same run: the report's rule ids are SDK baseline and registry rules only; none of the four `.semgrep/l9-pr.yml` rules ran in any CI job (only in local `make pr`). CTO decision (2026-11-21): bind them centrally; local `make pr` is not an accepted enforcement point. The mechanism is SDK [#136](https://github.com/Quantum-L9/l9-ci-sdk/pull/136) (ADR 0021, scoped consumer rulepack, SDK `d4bbdbd`), which is on SDK `main` but not in the SDK `47ae3ac5` that Core's org-ci provisions; it reaches org-ci with Core's next pin, PIN-ADVANCE-3 (lane N1e), together with the Core planner and `org-ci.yml` consumer step. The consumer side is [#1114](https://github.com/Quantum-L9/Cursor-Governance/pull/1114): `.l9/semgrep-consumer-rules.yaml` plus `canonical_rule_id` metadata, validated by SDK `main` `4a88739` `l9-ci semgrep consumer-run` (4 rules loaded, each fires on its known-bad file and stays inside its scope). PASS needs a central run id whose finding bundle shows the four rules in its coverage |
| 2.5 Native and repo-owned checks report correctly | **PASS** | All six required checks green on #1108 `22710d5c`; CodeQL and Sonar keep their own owners and are not described as SDK-executed |
| 3. Known-bad and known-good, central rule | **PASS** | `73ad9c04`: both `subprocess-shell-true` rules fire on `central_rule_bad.py:7`; `central_rule_good.py` scanned, no finding; `blocking_count: 6`, all on the canary's known-bad files |
| 3. Cursor-specific memory/transport rule | **BLOCKED on PIN-ADVANCE-3** (same cause as 2.4) | Fires locally, correctly scoped (2026-11-20 witness below), and fires in the SDK consumer execution on a scratch tree (#1114); not yet executed by org-ci |
| 3. Consumer override refused | **PASS** | `73ad9c04`: inline `# nosemgrep` (`override_nosemgrep.py:7`) and consumer `.semgrepignore` (`override_ignored_dir/`) no longer hide the finding; both rules fire on both. Version and severity override: consumer files cannot change Core's tool versions (Core installs from its own locks) |
| 3. Missing or failing required provider is FAIL or INCOMPLETE | **PASS** | 2026-11-20 runs 44825395263 and 44826737909: a required instance that could not complete ended `incomplete`, exit 6, job failure (never green); the same class is now an explicit not-planned reason (2.2) |
| 3. Biome known-bad | **PASS** | `fa1ec0e9`: [Core run 44870756504](https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44870756504/job/136744510501) `BIOME_STATUS: findings`, job failure; [SDK Biome run 44870757046](https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44870757046/job/136744512137) failure |
| 3. CodeQL PR default and nightly extended remain wired | **PASS** | Receipts reused, not forced: run 44870443753 (`codeql.yml`) and run 44731752123 (`codeql-nightly.yml`) |
| 3. Before/after comparison | **PASS** | `Analyze (central Core)`: 3 min 12 s on 2026-11-20 (`4accb109`, one instance) and 2 min 58 s now (`73ad9c04`). Findings on `main`: 29 blocking, now 0. 0 Semgrep errors (no timeouts) on `73ad9c04` |
| 4. Promotion and rollout decision | **BLOCKED** | One required item is open: 2.4, together with the matching Gate 3 memory-rule witness, both waiting on PIN-ADVANCE-3. Every consumer check stays in place (`L9-CI-CORE-004`) |

**Overall: `CURSOR_CANARY_BLOCKED`.** Exact blocker: the four Cursor-owned rules in
`.semgrep/l9-pr.yml` run in no CI job. The CTO chose central binding. The SDK binding (#136) is merged on SDK
`main` but not yet provisioned by org-ci; Core's PIN-ADVANCE-3 (lane N1e) carries it. Next action: when
PIN-ADVANCE-3 merges and #1114 is on `main`, re-run gate 2.4 and the Gate 3 memory-rule witness on a
Cursor-Governance head, and record the run id and the four rules in the central finding bundle's coverage here.
Also open but not gating: L1's proof that a Semgrep timeout counts as incomplete coverage (2026-11-20 B5;
not reproduced now).

## Verdict (2026-11-20, superseded by the re-run above)

`CURSOR_CANARY_BLOCKED`. The real Cursor-Governance evaluation runs Core's required workflow on the
exact head and fails closed on a central known-bad, a Biome known-bad and an incomplete required
instance. Five required properties are not met. Each is a central (SDK or Core) defect, not a
Cursor-Governance one, and no local waiver was added for any of them.

| # | Blocking item | Gate | Owner | Next action |
|---|---|---|---|---|
| B1 | A consumer inline `# nosemgrep` suppresses a central required finding (`override_nosemgrep.py` scanned, no finding) | 3 (override) | SDK, lane L1f (T44) | Run required rules with `--disable-nosem`; re-run the canary |
| B2 | A consumer `.semgrepignore` entry removes a file from central required coverage (`override_ignored_dir/` absent from `paths.scanned`) | 3 (override) | SDK, lane L1f (T44) | Ignore consumer `.semgrepignore` for required rules (declared scope); re-run the canary |
| B3 | The four Cursor-owned rules in `.semgrep/l9-pr.yml` run in no CI job; central Semgrep does not load them | 2.4, 4 | SDK/Core binding (scoped consumer rulepack) | Bind the consumer rulepack with its own path scope; until then local `make pr` enforcement stays (it fires, below) |
| B4 | `Analyze (central Core)` is red on every Cursor-Governance PR: the SDK marks `javascript` applicable from 2 test-fixture `.js` files, the plan maps it to `semgrep:language:typescript`, and that instance never completes (exit 6) | 2.2 | SDK inventory/instance, or Core plan (T32) | Make the instance execute those files or record an explicit not-applicable reason; never a local waiver |
| B5 | Semgrep rule timeouts (5 on 4 files in run 44819081765) are reported as a complete pass (`incomplete_provider_count: 0`) | 3 (partial coverage) | SDK normalization | Count a timed-out rule/file pair as incomplete coverage |

Open but not blocking the canary: `main` `Test Suite` fails `tests/ops/memory/test_egress_boundary.py`
since #1085 (owner: that lane); Sonar has no hosted apply run since #1062 (T15, `NOT_EXECUTED`).

## Gate 0: revisions and rules

| Item | Value |
|---|---|
| Cursor-Governance `main` | `da1080b91a554d27a0ffa9843289359a48b51393` |
| Core `main` | `8667d53` (#295); org-ci actions pinned at `8554ce964a3bbae2c21957208213d3c8ea63eb20` (#292, an ancestor of Core `main`) |
| SDK provisioned by Core | `dc783c648d42c5a6d9e197a533adc7d8f2841b06` (SDK_version 2.0.0) |
| Semgrep | 1.171.0 from Core `install-semgrep/locks/semgrep-1.171.0.txt` |
| Biome | 2.5.8 from Core `install-biome/locks/biome-2.5.8.json` (sha256 `17abac7e…`) |
| Ruleset 21895545 (organization) | workflow `l9-ci-core/.github/workflows/org-ci.yml@refs/heads/main`; required `Analyze (central Core)` (not strict) |
| Ruleset 20855699 (repository) | required Lint and Type Check, Test Suite, Root-file append-only gate, governance-self-check, repo-hygiene (strict) |

The pinned Core and SDK revisions are on their `main`; no unmerged Core or SDK pull request is
claimed as installed behavior.

## Gate 1: baseline

| Run | Head | Result |
|---|---|---|
| Core [44819081765 / 136574965996](https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44819081765/job/136574965996) (actions `ed10cb2d`, before the #292 re-pin) | PR #1088 `4accb109` | success, 3 min 12 s. Inventory `javascript, python`; one Semgrep instance (python), 876 files scanned, 38 results from 2 rule ids, 5 rule timeouts, gate pass; Biome blocking pass; `make setup validate check test` pass (51 tests) |
| Local Lint and Type Check [136575004414](https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44819082058/job/136575004414), Test Suite [136575004530](https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44819082058/job/136575004530) | `4accb109` | success; Test Suite 51 passed (PR scope) |
| Local Test Suite on `main` [136582497264](https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44821270157/job/136582497264) | `da1080b9` | failure: 8317 passed, 2 failed (`test_egress_boundary.py`), 15 skipped |

Custom rule dispositions (`.semgrep/l9-pr.yml`), all `retain_domain`, enforced only by
`ops/scripts/run_pr_security.sh` in `make pr`:

| Rule id | Path scope | Central | Local witness (semgrep 1.171.0, scratch tree) |
|---|---|---|---|
| `l9.no-semgrep-app-token-in-child-env` | all Python | not executed | not re-run here |
| `l9.memory-boundary-no-network-or-provider-transport` | `ops/memory/`, four hydration modules, `environment/agents/adapters/claude-code/memory/`; excludes tests and `hosted_hook_transport.py` | not executed | fires on `ops/memory/canary_transport_bad.py:3` (`import socket`); silent on a known-good `ops/memory` file and on `import socket` under `ops/lib/` (scope holds) |
| `l9.memory-boundary-spawn-only-through-the-binding` | memory path | not executed | not re-run here |
| `l9.memory-boundary-no-shell-string-spawn` | memory path | not executed | not re-run here |

CodeQL (`codeql.yml` PR default, `codeql-nightly.yml` security-extended) is the accepted native owner
and is unchanged; no scan was forced. `codeql / Analyze (python)` passed on every head above.

## Gate 2: real central invocation

| Requirement | Evidence | Result |
|---|---|---|
| Ruleset selected Core `org-ci.yml`; `Analyze (central Core)` evaluated the exact head | Canary PR [#1096](https://github.com/Quantum-L9/Cursor-Governance/pull/1096) (DO NOT MERGE), heads `fa243ccc` and `45df400b`; PR #1093 `860b7f72` | met |
| Every applicable language has an instance, a valid not-applicable reason, or a fail/incomplete status | `python` planned and run; `javascript` (2 files) planned as `semgrep:language:typescript`, incomplete; `shell` (187 files) visible, unsupported, not planned | fail-closed, but B4 |
| Central config resolved from Core/SDK, not copied | policy and identity maps under `.l9/runtime/org-governance/`, SDK `dc783c64`, Semgrep and Biome from Core locks | met |
| Cursor-owned rules effective in a scoped execution | not loaded centrally | B3 |
| Native and repo-owned checks report correctly | Lint and Type Check, Test Suite and CodeQL green on the canary heads; not described as SDK-executed | met |

## Gate 3: witnesses and failure injection

Canary PR [#1096](https://github.com/Quantum-L9/Cursor-Governance/pull/1096), branch
`agent/claude/cg-cutover-canary`, never merged. Fixtures under `canary/ci_ul/`, declared in
`ops/ci_parity/expect_fail_fixtures.json` (the class from #1090), so the local publish gate was not
relaxed.

| Witness | Head | Central result | Local gate |
|---|---|---|---|
| Central known-bad `central_rule_bad.py:7` (`shell=True`) | `fa243ccc`, [run 44826737909](https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44826737909/job/136601136875) | both `subprocess-shell-true` rules (SDK baseline and registry) fire; python instance fail, `blocking_count: 2`, job failure | semgrep-l9 `expected=2`; bandit B602 expected |
| Central known-good `central_rule_good.py` | same | scanned, no finding | no finding |
| Override: inline `# nosemgrep` (`override_nosemgrep.py:7`) | same | scanned, **no finding** (coverage lowered, B1) | no semgrep finding; bandit B602 still fires |
| Override: consumer `.semgrepignore` (`override_ignored_dir/`) | same | **not scanned** (coverage lowered, B2) | no semgrep finding; bandit B602 still fires |
| Required instance that cannot execute | `fa243ccc`, `860b7f72` | `semgrep:language:typescript` incomplete, aggregate fail/incomplete, job failure (never green) | n/a |
| Biome known-bad `biome_bad.json` | `45df400b`, [Core run 44827192217](https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44827192217/job/136602662377), [SDK run 44827193151](https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44827193151/job/136602664235) | Core `BIOME_STATUS: findings` ("File content differs from formatting output"), job failure; the SDK Biome job fails on the same file and rule | biome lane `expected` |
| Cursor memory rule known-bad | scratch tree only: a known-bad `ops/memory` file cannot be published through `make pr`, because the local rule and `test_transport_boundary.py` block it, as designed | not executed (B3) | fires, scoped |

Version and severity override attempts were not exercised on the canary. The consumer-controlled
version surfaces (`pyproject.toml`, `requirements.txt`, `.pre-commit-config.yaml`) are append-only
root files, and Core's Python tools for `make check` come from this repository's own `uv.lock`, so a
consumer ruff pin is effective there by design; Core's `check-toolchain-alignment` reports such drift
as advisory. Recorded as Unknown, not as a pass.

Runtime of `Analyze (central Core)`: 3 min 12 s on `4accb109` (one Semgrep instance), 2 min 57 s on
`fa243ccc` (two planned instances); the Biome-failed run on `45df400b` stopped after 26 s.

## Gate 4

`CURSOR_CANARY_BLOCKED` on B1 to B5. Every consumer check stays (`L9-CI-CORE-004`), including
`l9-lint-test-node.yml`, which now has a known-good (#1088) and a known-bad (`45df400b`) Biome
parity receipt. The required-check plan is `REQUIRED_CHECK_CUTOVER.md`. Re-run this canary on
#1096 after the B1 to B5 owners land their fixes; PASS needs every row above met on one head.
