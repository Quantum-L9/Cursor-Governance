# Lane N1: Cursor-Governance native baseline, CodeQL detect and Sonar successor

## MANIFEST

- Campaign `L9-CI-UNIFIED-LEVERAGE-2026-11-20-v1.7.1`, lane `N1`, pool slot 5.
- Write: `Quantum-L9/Cursor-Governance` only, and only the paths named in Workflow step 4. Base:
  fetched `origin/main` (`a95562c9`).
- Read-only: `Quantum-L9/l9-ci-core`.
- Findings: T15. Absorbs `CODEQL_SONAR_LEVERAGE.md` A.1 and `CURSOR_CANARY.md` Gate 1.
- The CTO owns `docs/campaigns/11-20-26/**`. Do not write there.

## OBJECTIVE

Capture the real consumer baseline the canary will be judged against, prove or disprove that Sonar
still analyzes this repository after #1062, and prepare the one narrow CodeQL fix: a failed language
lookup must not read as "nothing to analyze".

## NON-GOALS

- No CodeQL redesign, no suite change, no default setup, no new required check.
- No Sonar scan, test suite or workflow dispatched. The 8175-test suite is not re-run.
- No rule moved out of `.semgrep/l9-pr.yml`. No local check retired.
- No fix to Core's scheduler from here.

## ASSETS USED

- This pack: `CURSOR_CANARY.md`, `CODEQL_SONAR_LEVERAGE.md`, `OPERATOR_VERIFY_FIRST.md`, `HARVEST.md`,
  `PROOF.md` P11, P13; `09_EXECUTION_BINDING.md` B01, B02, T15, G0.
- Cursor-Governance: `CANONICAL_LAW.md`, `AGENTS.md`, `.github/workflows/codeql.yml`,
  `codeql-nightly.yml`, `codeql-reusable.yml`, `.github/codeql/codeql-config.yml`,
  `.github/workflows/sonarcloud.yml`, `sonar-project.properties`, `.semgrep/l9-pr.yml`,
  `ops/scripts/run_pr_security.sh`, `docs/handoffs/CODEQL_ROLLOUT_HANDOFF.md`.
- Core: `.github/workflows/org-nightly-dispatch.yml`, `nightly-deep.yml`, `org-ci.yml`.

## WORKFLOW

1. **Baseline, read-only.** Record default-branch head, required checks, and the latest real runs with
   run ID and `head_sha` for: `Analyze (central Core)`, CodeQL pull-request, CodeQL nightly, Sonar,
   the test suite. List the four `.semgrep/l9-pr.yml` rule IDs with path scope and expected finding.
2. **T15, read-only.** Find a hosted Core `mode=apply` dispatch for this repository on `a95562c9` or
   later and the native Sonar gate it produced. Report `EXECUTED_VERIFIED` with the run, or
   `NOT_EXECUTED` with what is missing and which Core file would schedule it. Do not dispatch one.
3. **CodeQL nightly and overlay, read-only.** Record the last scheduled `security-extended` run and
   whether a pull request since `24f0c4db` logged an overlay-base cache hit.
4. **CodeQL detect, gated by G0.** In `codeql-reusable.yml`, a `/languages` API failure must fail or
   report unknown, not fall back to an empty set and succeed. Add a negative test. Until G0 clears,
   write `CTO-BLOCKER: G0 codeql-detect`, keep the change local and unpublished, and do not edit any
   other CodeQL or Sonar file.
5. **Rule dispositions.** For each of the four rules give a `HARVEST.md` disposition. Three memory
   transport and spawn rules stay Cursor-owned; the process-token rule is a conditional candidate.
   Report the rows for the CTO ledger.
6. Publish step 4 once G0 clears. If it never clears, report the lane done with that item `BLOCKED`.

## CONSTRAINTS

- This repository's law applies in full: no local commit hook, no bypass flags, root files append-only.
- Thin consumer callers pin the reusable workflow by SHA. A reusable change needs the documented
  caller pin update; say so in the pull request rather than promising none.
- Publish with `PR_REMEDIATE=0 make pr`.
- A cache miss is an optimization finding, not a security failure. Keep the two apart.

## DONE-CRITERIA

- Baseline table with run IDs and SHAs, in the transcript.
- T15 has a disposition backed by a run or by a named absence.
- Four rule rows delivered.
- The CodeQL detect pull request is `ready-to-merge`, or the item is `BLOCKED` on G0 with the diff
  described.

## ACTIVATION

Begin after role registration and `/coding-agent` mode reports ACTIVE. Cursor-Governance is your
primary repository, so attach it with push. First status line carries the mode JSON and the base SHA.
