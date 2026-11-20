# Cursor-Governance required-check cutover plan (proposed, not applied)

Lane CG-CUTOVER item 3, 2026-11-20. Rulesets belong to the CTO and the operator. This file changes
no ruleset, retires no check and removes no workflow. `L9-CI-CORE-004` forbids retiring a consumer
check before `CURSOR_CANARY_PASS`; every `retire_duplicate` row below is a candidate that waits for
that result and for its named parity receipt.

## Effective rules on `main` (read 2026-11-20 through `rules/branches/main`)

| Ruleset | Rule | Contexts | Strict |
|---|---|---|---|
| `20855699` main-protection (repository) | required_status_checks | Lint and Type Check, Test Suite, Root-file append-only gate, governance-self-check, repo-hygiene | yes |
| `21895545` (organization) | workflows | `l9-ci-core/.github/workflows/org-ci.yml@refs/heads/main` | n/a |
| `21895545` (organization) | required_status_checks | Analyze (central Core) | no |

Core `org-ci.yml` runs on `push`, `pull_request`, `merge_group` and `workflow_dispatch`
(l9-ci-core main `75a521f`).

## Reference receipt pair

PR #1088, head `4accb109c2e8d5a4421147cf69f60e33989b57dd`, both sides on the same head:

| Side | Job | Result |
|---|---|---|
| Core `Analyze (central Core)` | [run 44819081765 / job 136574965996](https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44819081765/job/136574965996) | `make setup validate check test`: `validate_rules_manifest` PASS, uv lock resolve, `ruff check .` all passed, `ruff format --check .` 2515 files, `run_pytest_suites.sh` 51 passed; Biome 2.5.8 blocking pass; SDK gate pass |
| Local `Lint and Type Check` | [run 44819082058 / job 136575004414](https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44819082058/job/136575004414) | ruff check, ruff format 2515 files, mypy, `uv lock --check`, conflict-marker scan |
| Local `Test Suite` | [run 44819082058 / job 136575004530](https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44819082058/job/136575004530) | `run_pytest_suites.sh` (PR scope) 51 passed, with coverage |

A green pair on one head is a positive witness only. Retirement also needs a negative witness: the
same defect, injected on a disposable branch, fails both sides with the same file and rule (Gate 3).

## Disposition per local required check

| Check | What it runs | Core equivalent today | Disposition | Parity receipt that must exist before retirement |
|---|---|---|---|---|
| Lint and Type Check | controller-manifest guard; ruff check; ruff format --check; mypy (**advisory**: `continue-on-error: true`, 328 pre-existing errors, `l9-lint-test.yml:159-164`); `uv lock --check`; conflict-marker scan | ruff check, ruff format --check and the lock check run in Core `make check` / `make validate` through the `Repo.mk` leaves. **The controller-manifest guard and the conflict-marker scan do not run in Core.** mypy gates nothing today on either side | `retire_duplicate` for the ruff, format and lock steps; the job stays required while it carries the two guards, which are `retain_domain`. mypy is not a blocking duplicate: it must not join the blocking `repo-check` leaf while its debt stands, because `Analyze (central Core)` would turn advisory errors into a merge blocker. It moves to Core only as an explicitly advisory step, or as a blocking one after the debt is cleared | (1) the green pair above; (2) a disposable-branch run where one ruff violation, one format violation and one stale `uv.lock` each fail `Analyze (central Core)` naming the same file and rule as `Lint and Type Check`; (3) the two guards running somewhere required, or the job kept for them |
| Test Suite | `run_python_test_suites.py --profile ci` (xdist with loadgroup, 300-second per-test timeout, root `coverage.xml`) on `push` and `merge_group`; PR-scoped selection on `pull_request` | Core `make test` reaches `run_pytest_suites.sh`, which calls the runner with `--profile local` on every event (`ops/scripts/run_pytest_suites.sh:38,75`). 51 = 51 on #1088 at PR scope. Core runs neither the CI profile's concurrency and timeout behavior nor, as far as is known, the coverage producer | `retire_duplicate` candidate, blocked on evidence and on a profile change | (0) Core's `make test` runs `--profile ci` on `push` and `merge_group` (or parity for xdist/loadgroup and the per-test timeout is proven separately); (1) a `merge_group` run and a `push` to `main` where Core's `make test` reports the same passed/failed/skipped counts as local `Test Suite` (full registry: 8317 passed, 2 failed, 15 skipped on `da1080b`, [job 136582497264](https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44821270157/job/136582497264)); (2) a disposable-branch failing test that fails both with the same node id; (3) the coverage file Sonar imports produced by the Core run, or Sonar coverage proven from one other run (T15, T35, T47) |
| Root-file append-only gate | `validate_root_file_protection.py` with `ops/config/root-file-protection.json`, PR body stamp, queued `merge_group` body | none | `retain_domain` | not applicable; repository-owned protection data |
| governance-self-check | ORG_INVARIANTS parse, SSOT presence, generated-artifact drift, rules budget, skills standard, skill projection, workflow action pins, MCP allowlist, tracked-secret guard, repo-docs obligations | none for governance content; Core does not check third-party action SHA pins here | `retain_domain` | not applicable. The action-pin step may later move to a Core or SDK provider as its own harvest row with good/bad witnesses |
| repo-hygiene | space paths, tracked runtime state, single env template, retired dirs, full hygiene check | none | `retain_domain` | not applicable |

Kept as domain checks, not required today: `Exact-head memory lifecycle proof`
(`memory-cross-repo.yml`), `L9 Projection Bundle Verify` and `Trusted Replay`, CodeQL (`codeql.yml`
PR default and `codeql-nightly.yml` security-extended; accepted owner, not relocated to the SDK).

## Proposed ruleset end state (operator applies, after `CURSOR_CANARY_PASS`)

1. Keep `Analyze (central Core)` required (organization ruleset 21895545).
2. Keep required: `Root-file append-only gate`, `governance-self-check`, `repo-hygiene`.
3. Keep `Lint and Type Check` required until the two guards run in a required check elsewhere; then drop it from
   ruleset 20855699 in the same change that deletes the job.
4. Keep `Test Suite` required until its three receipts exist; then drop it in the same change that
   deletes the job.

No step removes a check before its successor's negative witness is recorded.

## Next actions

| Item | Owner | Action |
|---|---|---|
| mypy debt | Cursor-Governance owners | Clear the 328 pre-existing errors, or give Core an explicitly advisory mypy step; never add the blocking `lint-mypy` target to `repo-check` first |
| Test profile in Core | Cursor-Governance `run_pytest_suites.sh` (Core reaches it through `Repo.mk` `repo-test`) | Select `--profile ci` on `push` and `merge_group` there, so Core and local Test Suite run the same profile; record both runs |
| Test Suite scope on `push` and `merge_group` | Cursor-Governance `run_pytest_suites.sh` scope, with Core `run-repository-verification` event plumbing | Record both counts; a mismatch is a CTO-QUESTION to the Core owner |
| Coverage from one run | Core lane L2b (T35) | Sonar import from the Core run, or keep local `Test Suite` as the coverage producer |
| Negative witnesses | lane CG-CUTOVER item 4 | Disposable-branch fixtures; run URLs in `CURSOR_CANARY_RESULT.md` |
