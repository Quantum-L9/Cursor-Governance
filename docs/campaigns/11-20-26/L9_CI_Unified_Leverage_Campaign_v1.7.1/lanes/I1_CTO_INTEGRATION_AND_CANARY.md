# Lane I1: integration, live canary and closeout (CTO session)

## MANIFEST

- Campaign `L9-CI-UNIFIED-LEVERAGE-2026-11-20-v1.7.1`, lane `I1`. Executor: the CTO session, in
  disposable worktrees. It is not delegated to a pool agent or a subagent.
- Write: evidence files in this pack only.
- Absorbs v1.7.0 Stage 1, Stage 2A, Stage 2B and Stage 4.

## OBJECTIVE

Prove the exact combined Core and SDK revision before anything is called integrated, run the real
Cursor-Governance canary once that revision is promoted, and close the campaign with a verdict that
matches the evidence.

## NON-GOALS

- No merge. No ruleset or pin change. No consumer check retired.
- No fix applied to a lane branch; a defect goes back as `CTO REMEDIATE <pr>`.
- No canary result from an unmerged pull request, an SDK-only fixture or a static workflow diff.
- No fleet rollout in this campaign pass before `CURSOR_CANARY_PASS`.

## ASSETS USED

- This pack: `CURSOR_CANARY.md`, `PROOF.md` P0 to P14, `INVARIANTS.md` admission order, `ADRS.md`
  admission order, `CAMPAIGN.md` Stage 1 to Stage 4, `09_EXECUTION_BINDING.md` B21.
- Core `AGENTS.md` §6 and §16 (SDK pin and pin advance), `.l9/sdk-compatibility.yaml`.

## WORKFLOW

1. **Stage 1.** When L1 and L2 report `ready-to-merge`, check out both exact heads in disposable
   worktrees, point Core at the SDK head the way its compatibility contract allows, and run Core's and
   the SDK's suites together plus the mixed-language fixture. Record both SHAs. A failure names the
   owning lane and goes back to it.
2. **Wave 1 report.** One report to the operator: pull requests with heads, the Stage 1 result, the
   findings register, what merges are needed in what order, and `CURSOR_CANARY_BLOCKED` with reason
   `BLOCKED_ON_PROMOTION`.
3. **Stage 2A, after promotion.** Run `CURSOR_CANARY.md` Gates 0 to 4 against the real
   `Quantum-L9/Cursor-Governance` head: the ruleset selected `org-ci.yml`, `Analyze (central Core)`
   evaluated that exact head, every applicable language and provider ran or reported truthfully,
   inherited configuration with digests, the four Cursor rules still effective in scope, known-bad and
   known-good fixtures on a disposable branch, one refused consumer override, one missing-scanner
   failure, CodeQL and product tests unchanged. Compare against lane N1's baseline.
4. **Stage 2B.** EIE, CEG and Odoo with their own harvested rules and fixtures, Odoo under its own
   owner's enforcement.
5. **Closeout.** `evidence/CLOSEOUT.md`: accepted decisions, pull-request links and head SHAs,
   rulesets and revisions, canary ledger, rule tests, tool matrix, spend Unknowns, and every finding
   T01 to T16 as fixed, already satisfied, invalid, or blocked with owner and next action.

## CONSTRAINTS

- `integration_responsibility`: the claim is about the exact combined revision, and component receipts
  do not prove it.
- A row is `PASS`, `BLOCKED` or `NOT_PROVEN`. The campaign is `PASS`, `PARTIAL` or `BLOCKED`.
  `PARTIAL` applies only when a mandatory row is not `PASS`.
- A canary failure is fixed at the earliest source owner. No local waiver hides a broken rollout.

## DONE-CRITERIA

- Stage 1 result recorded with both SHAs.
- `CURSOR_CANARY_PASS`, or `CURSOR_CANARY_BLOCKED` with the exact failed item, owner and next action.
- `evidence/CLOSEOUT.md` covers `PROOF.md` P0 to P14 by number with no blank row.

## ACTIVATION

Stage 1 starts on the two `ready-to-merge` statuses. Stage 2A starts only after the operator's merges
and Core's pin advance are observed on `main`.
