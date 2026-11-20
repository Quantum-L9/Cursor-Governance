# Lane F2: EIE secrets-scan truthfulness and reviewer audit

## MANIFEST

- Campaign `L9-CI-UNIFIED-LEVERAGE-2026-11-20-v1.7.1`, lane `F2`, pool slot 4.
- Write: `Quantum-L9/Enrichment.Inference.Engine` only. Base: fetched `origin/main` (`e1a61f78`).
- Read-only: `Quantum-L9/l9-ci-core`.
- Findings: T05, T06, T10 (EIE half, observe only), T13.

## OBJECTIVE

Make EIE's Gitleaks and GitGuardian jobs state plainly when they did not scan, close or record the
Dependabot pre-merge gap, and produce the evidence needed to decide whether the Perplexity review
workflow earns its cost.

## NON-GOALS

- No edit to `.github/workflows/sonarcloud.yml`, `ci.yml`, `pr-pipeline.yml` or `Repo.mk`: open pull
  request #365 changes them.
- No workflow disabled or retired, including `perplexity-code-review.yml`.
- No license purchased, no vendor setting changed, no secret added.
- No CodeQL migration, no CodeRabbit YAML change, no transport or runtime file touched (C-13, C-21).

## ASSETS USED

- This pack: `OTHER_TOOLS_EVIDENCE.md` T05, T06, T10, T13; `OTHER_TOOLS_EXECUTION.md` lanes F2 and F3;
  `PROOF.md` P14; `CODERABBIT_ACTIVATION.md`; `09_EXECUTION_BINDING.md` B09, B10, B19.
- EIE: `AGENTS.md`, `CLAUDE.md`, `.github/workflows/gitleaks.yml`, `gitguardian.yml`,
  `perplexity-code-review.yml`, `coderabbit-notify.yml`, `.coderabbit.yaml`,
  `sonar-project.properties`.

## WORKFLOW

1. **T05.** Read the trigger, job and actor predicates that skip Gitleaks for `dependabot[bot]`. Find
   a hosted Dependabot pull request and record what ran. If a pre-merge scan can run without a new
   license or secret, implement it with a witness. If it cannot, leave the skip, make it report
   `SKIPPED_BY_POLICY` with its reason, and record the residual gap with its owner. Post-merge scanning
   does not close the pre-merge gap.
2. **T06.** Make a missing or expired GitGuardian token and an API failure report as not executed.
   Witnesses for both. Keep the successful path intact.
3. **T10, observe.** State whether #365 removes `--cov=engine` at `sonarcloud.yml:85`. If it does not,
   write a `CTO-QUESTION`. Do not edit the file.
4. **T13, read-only.** For Perplexity, CodeRabbit and Copilot review on EIE: runs that actually
   executed, permissions, overlap, and cost where visible. End with `KEEP`, `RETIRE_CANDIDATE` or
   `BLOCKED`. A retirement is a recommendation for the operator, not a change.
5. **CodeRabbit, read-only.** Record that `.coderabbit.yaml` lacks `inheritance: true` and excludes
   `docs/**`. Change nothing while the central parent is unconfirmed (B19).
6. Publish one pull request for steps 1 and 2.

## CONSTRAINTS

- EIE `CLAUDE.md` holds: cite the contract, no vague language, no inline `# noqa` for globally ignored
  rules. `Makefile` is never edited.
- Gates before publishing: `make validate check test`.
- Publish with `PR_REMEDIATE=0 OPEN_PR=1 make -C "$HOME/.cursor-governance" pr WS="$PWD"`.
- No vendor token in a fork-reachable context.

## DONE-CRITERIA

- One pull request `ready-to-merge` for T05 and T06, with the named witnesses.
- T05, T06, T10 (EIE), T13 each have a disposition with evidence.
- The reviewer audit table exists in the transcript with a row per reviewer.

## ACTIVATION

Begin after role registration and `/coding-agent` mode reports ACTIVE. First status line carries the
mode JSON, the base SHA you fetched and the current head of #365.
