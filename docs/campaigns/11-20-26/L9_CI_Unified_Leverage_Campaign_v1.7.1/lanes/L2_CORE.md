# Lane L2: Core control plane, runtime inheritance and truthful requiredness

## MANIFEST

- Campaign `L9-CI-UNIFIED-LEVERAGE-2026-11-20-v1.7.1`, lane `L2`, pool slot 2.
- Write: `Quantum-L9/l9-ci-core` only. Base: fetched `origin/main` (`3579bdc1` on 2026-11-20).
- Read-only: `Quantum-L9/l9-ci-sdk`.
- Absorbs v1.7.0 Lane 2 and finding T04.

## OBJECTIVE

Propose Core ADRs 0001 and 0002 and invariants `L9-CI-CORE-001` to `006` at their owner with running
witnesses, then make the required job account for every SDK-selected language and provider instance
and never report a skipped required instance as passed.

## NON-GOALS

- No second workflow distributed to consumers. No consumer repository edited.
- No CodeQL or SaaS credential moved into the read-only required job.
- No scanner promoted to blocking. No ruleset, branch-protection or pin-advance change.
- No consumer check retired. Do not mark an ADR Accepted.
- Do not edit a file that open pull request #281 changes for its purpose (test-expense logic).

## ASSETS USED

- This pack: `ADRS.md`, `INVARIANTS.yaml`, `INVARIANTS.md`, `PROOF.md` P0, P2, P7, P8, P9;
  `candidates/adr/l9-ci-core/docs/adr/` (three files), `candidates/core-governance-contract.patch`;
  `OTHER_TOOLS_EVIDENCE.md` T04; `09_EXECUTION_BINDING.md` B12, B13, B14, Stacking.
- Core: `AGENTS.md` (§3, §5, §6, §11, §14, §16, §24), `.l9/governance-contract.yaml`,
  `.l9/architecture.yaml`, `.l9/ownership.yaml`, `.l9/release-plane.yaml`, `.l9/sdk-compatibility.yaml`,
  `.github/workflows/org-ci.yml`, `.github/workflows/security.yml`,
  `.github/actions/install-consumer-ci/toolchain-lock.json`, `docs/ACTIVATION.md`.

## WORKFLOW

1. **PR 2a, decisions.** Create `docs/adr/` with the three candidate files unchanged. Apply the
   contract patch (applies cleanly at `3579bdc1`). Append one dated `AGENTS.md` section that points at
   the two ADRs and repeats none of their text. Add one positive and one negative witness test per
   invariant, named by ID; a witness that needs step 2 fails closed with the exact missing capability.
   Publish against `main`.
2. **PR 2b, all applicable instances**, stacked on 2a. Consume the SDK inventory at the head lane L1
   reports in `interface-freeze`. Schedule every required language and provider instance, record each
   terminal status, and fail or mark incomplete when one is missing, skipped, timed out or untrusted.
   Fixture: Python plus TypeScript, then the same with one instance killed. If `org-ci.yml` conflicts
   with #281, stack on `agent/fleet-b2/pr-expense-guard` as the binding describes. Publish.
3. **PR 2c, inherited configuration**, stacked on 2b. Let the stamp and `l9.repo-execution/v2`
   contracts accept centrally resolved configuration with a content digest, without a self-triggered
   drift failure. Prove a consumer override of version, mode or ignore scope is refused or ignored with
   evidence. Publish.
4. **T04, report first.** Establish whether any consumer still calls `security.yml` after §15. State
   per profile whether Bandit and npm audit are required, advisory or not run. Change labels so an
   advisory or skipped scan cannot read as executed. Promote nothing.

## CONSTRAINTS

- `Makefile` is the generated facade and is never edited. Recipes live in `Repo.mk`.
- Gates before publishing: `make setup validate check test`.
- Publish with `PR_REMEDIATE=0 OPEN_PR=1 make -C "$HOME/.cursor-governance" pr WS="$PWD"`.
- `AGENTS.md` is append-only.
- An interface change that the SDK must match is a `CTO-QUESTION`, not a local decision.

## DONE-CRITERIA

- PR 2a, 2b, 2c each `ready-to-merge`.
- Each of `L9-CI-CORE-001` to `006` has a named failing known-bad and passing known-good test. For
  `004` and `006` the test proves the gate logic only; live proof belongs to lane I1 and is stated as
  not yet made.
- The mixed-language fixture shows two completed executions and one aggregate, and goes red when one
  instance is removed.
- T04 has a disposition with evidence.

## ACTIVATION

Begin after role registration and `/coding-agent` mode reports ACTIVE. First status line carries the
mode JSON, the base SHA you fetched and the current head of #281.
