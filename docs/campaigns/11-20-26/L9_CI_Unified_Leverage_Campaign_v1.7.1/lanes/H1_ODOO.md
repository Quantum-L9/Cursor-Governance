# Lane H1: Odoo rule harvest and native-scope verification

## MANIFEST

- Campaign `L9-CI-UNIFIED-LEVERAGE-2026-11-20-v1.7.1`, lane `H1`. Assigned by `CTO ASSIGN` to the
  first idle pool slot.
- Write: `cryptoxdog/IB-Odoo_19` only, base `Staging` (`341e45f4` on 2026-11-20). Expect little or no
  write.
- Read-only: `Quantum-L9/l9-ci-sdk`.
- Findings: T10 (Odoo half). `cryptoxdog` is a separate GitHub owner from `Quantum-L9`.

## OBJECTIVE

Classify the 39 Odoo Semgrep rules so lane L1 can take only what is portable, and establish what Sonar
and CodeRabbit actually cover on this repository now that #552, #553 and #556 are merged.

## NON-GOALS

- No rule removed, moved or weakened here. `.semgrep/odoo-patterns.yml` stays the owner's file.
- No Sonar scan dispatched, no vendor setting changed.
- No claim that a `Quantum-L9` ruleset or subscription covers this owner.
- No Docker runtime test run ad hoc (`AGENTS.md` 2026-11-06). No module code touched.

## ASSETS USED

- This pack: `HARVEST.md`, `CODEQL_SONAR_LEVERAGE.md` §B, `CODERABBIT_ACTIVATION.md` item D,
  `PROOF.md` P10, P12, P13; `09_EXECUTION_BINDING.md` B01, B04, T10.
- IB-Odoo_19: `AGENTS.md` with its dated corrections, `CLAUDE.md`, `INVARIANTS.md`,
  `.semgrep/odoo-patterns.yml`, `.semgrep/tests/`, `sonar-project.properties`,
  `.sonarcloud.properties`, `tests/test_sonar_scope.py`, `.coderabbit.yaml`,
  `.github/workflows/ci.yml`, `l9-analysis.yml`.

## WORKFLOW

1. **Rule classification, read-only.** For each of the 39 rule IDs: generic Python, Odoo 19 framework,
   or PlasticOS-specific. One `HARVEST.md` disposition per rule with head, blob, fixture path in
   `.semgrep/tests/` where one exists, and the scope that makes it applicable. A rule with no known-bad
   and known-good fixture is `defer_unknown`. Report rows for the CTO ledger and for lane L1.
2. **Sonar scope, read-only.** From the merged #552 state, list which modules and script roots are now
   in analysis scope and which are excluded with a reason. State whether any hosted Sonar analysis of
   `Staging` at or after `341e45f4` is observable. A properties file is not an analysis.
3. **CodeRabbit, read-only.** Find the most recent pull request where the bot reviewed or declined.
   Record automatic review, manual review, or skipped with the bot's stated reason.
4. **Enforcement boundary, read-only.** Record which required checks protect `Staging` as far as the
   repository API shows. Do not infer the rest.
5. Write only if a step exposes a defect inside this repository that the pack's scope covers. Publish
   it with `make pr` into `Staging`.

## CONSTRAINTS

- This repository's `make pr` is its own ceremony and targets `Staging`. Never `Production`, never
  `main`. `make push` is retired.
- In a cloud session the install-smoke is skipped by default and the pull request says so.
- `AGENTS.md` and `CLAUDE.md` are append-only.

## DONE-CRITERIA

- 39 rule rows, none blank.
- T10 (Odoo) has a disposition: live scope proven, or `NOT_PROVEN` with the missing observation named.
- CodeRabbit state recorded as one of the `CODERABBIT_ACTIVATION.md` item F outcomes.
- Any pull request opened is `ready-to-merge`; if none was needed, say so.

## ACTIVATION

Begin when a `CTO ASSIGN H1` arrives while you are idle. Re-run `/coding-agent` mode for this
repository first. First status line carries the mode JSON and the `Staging` SHA you fetched.
