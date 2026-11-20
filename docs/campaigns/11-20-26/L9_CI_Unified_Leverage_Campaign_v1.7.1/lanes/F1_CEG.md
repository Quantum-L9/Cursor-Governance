# Lane F1: CEG scanner honesty (GitGuardian, Codecov, aggregate)

## MANIFEST

- Campaign `L9-CI-UNIFIED-LEVERAGE-2026-11-20-v1.7.1`, lane `F1`, pool slot 3.
- Write: `Quantum-L9/Cognitive.Engine.Graphs` only. Base: fetched `origin/main` (`b2150980`).
- Read-only: `Quantum-L9/l9-ci-core`.
- Findings: T01, T02 with T14, T07, T08, and verification of T03.

## OBJECTIVE

Make CEG's secrets scan, coverage upload and aggregate gate report what actually happened, so a scan
that did not run or an upload the vendor rejected can no longer finish green.

## NON-GOALS

- No change to the required-or-advisory policy of any job. Preserve it and label it.
- No edit to test selection or pull-request test expense: open pull request #514 owns that.
- No `CODECOV_TOKEN` value invented, no vendor setting changed, no paid tier enabled.
- T03 is not rebuilt. No test is skipped or weakened to get green.
- No CodeQL migration, no CodeRabbit YAML change, no local check retired.

## ASSETS USED

- This pack: `OTHER_TOOLS_EVIDENCE.md` T01, T02, T03, T07, T08, T14 and the hosted anchors;
  `OTHER_TOOLS_EXECUTION.md` lane F1; `PROOF.md` P14; `09_EXECUTION_BINDING.md` B03, B09, B11, G0,
  Stacking.
- CEG: `AGENTS.md`, `CLAUDE.md`, `.github/workflows/ci-quality.yml` (GitGuardian step near lines 151
  to 186, Codecov near 237 to 244, the `quality-gate` aggregate), `.github/workflows/supply-chain.yml`,
  `.l9/external-checkout.json`, `docs/CI_PIPELINE.md`.

## WORKFLOW

1. Re-read the three warn-and-skip branches of the GitGuardian step at your base and record them.
2. **T01.** Make each outcome distinct and visible: scanned clean, secret detected, key absent, token
   lacks scope, container failed to start, container started and scanner failed. Honor the job's
   existing requiredness. Witnesses: clean scan, missing CI context, unavailable scanner, pull succeeds
   then scanner fails, synthetic test secret detected. Put the classification where a test can run it.
3. **T07.** The aggregate must not count a not-executed or rejected native result as an executed
   control. Add a fixture that proves it.
4. **T02 with T14, ungated part.** Make a failed or unauthenticated upload a distinct, visible outcome
   that is never reported as accepted coverage. Do not flip `fail_ci_if_error` if that changes
   requiredness; state the policy and label the result.
5. **T02, gated part.** Changing how the upload authenticates waits for G0. Write
   `CTO-BLOCKER: G0 codecov-auth` and move on.
6. **T08.** Report dependency-graph availability and review execution separately. A skipped review
   must not read as clean.
7. **T03.** Record the latest `Analyze (central Core)` run on CEG `main`. Close `ALREADY_SATISFIED`
   with that run, or reopen with it.
8. Publish one pull request. If `make pr` reports a textual conflict with #514 on `ci-quality.yml`,
   stack on `agent/fleet-d/ceg-pilot`.

## CONSTRAINTS

- CEG `AGENTS.md` boundaries hold. `Makefile` is never edited. New tracked files follow
  `docs/contracts/L9_META_HEADERS.md`.
- Gates before publishing: `make validate check test`.
- Publish with `PR_REMEDIATE=0 OPEN_PR=1 make -C "$HOME/.cursor-governance" pr WS="$PWD"`.
- No vendor token in a fork-reachable context.

## DONE-CRITERIA

- One pull request `ready-to-merge`.
- All five T01 witnesses and the T07 fixture exist and are cited.
- T01, T02, T03, T07, T08, T14 each have a disposition: `FIXED_PROVEN`, `ALREADY_SATISFIED` with a
  fresh run, `INVALID` with the contradiction, or `BLOCKED` with owner and dependency.
- A native receipt is cited for anything called executed; otherwise the row says not yet observed.

## ACTIVATION

Begin after role registration and `/coding-agent` mode reports ACTIVE. First status line carries the
mode JSON, the base SHA you fetched and the current head of #514.
