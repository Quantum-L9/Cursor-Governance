```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/l9-ci-sdk
    - https://github.com/Quantum-L9/l9-ci-core
    - https://github.com/Quantum-L9/Cognitive.Engine.Graphs
    - https://github.com/Quantum-L9/Enrichment.Inference.Engine
    - https://github.com/Quantum-L9/Cursor-Governance
    - https://github.com/cryptoxdog/IB-Odoo_19
    - https://github.com/Quantum-L9/.github   # CTO session only
  read_only: []
  unlisted_repositories: no_access
```

# CTO-mode campaign launch: unified CI governance and tool leverage

**Campaign:** `L9-CI-UNIFIED-LEVERAGE-2026-11-20-v1.7.1`
**Executor:** `/lcto` CTO mode on Claude Code cloud, under current Cursor-Governance law
**Authorization:** implement the bounded work, open reviewable pull requests, verify and integrate.
This is not an ADR or invariant admission, a merge grant, a vendor or billing authorization, or a
completed G0.
**Status:** corrected handoff, not executed. The pool is not launched.

## Mission

Unchanged from `README.md`: one central CI control plane (organization rulesets, then Core, then SDK),
native providers kept as governed adapters at their own owners, and the most defensible value from every
scanner and paid integration already in use, with no purchase.

## Reading order

1. `09_EXECUTION_BINDING.md`. It is the resolved launch binding and outranks any sentence in this pack
   that it names. Its live recheck replaces every 2026-11-19 SHA and pull-request state.
2. `CAMPAIGN.yaml` for the lane, repository and dependency index.
3. `README.md`, `CAMPAIGN.md`, `ADRS.md`, `INVARIANTS.yaml`, `INVARIANTS.md`: frozen intent.
4. The acceptance contracts a lane cites: `PROOF.md`, `HARVEST.md`, `CURSOR_CANARY.md`,
   `OTHER_TOOLS_EVIDENCE.md`, `OTHER_TOOLS_EXECUTION.md`, `CODEQL_SONAR_LEVERAGE.md`,
   `CODERABBIT_ACTIVATION.md`, `TOOL_VALUE.md`, `OPERATOR_VERIFY_FIRST.md`,
   `G0_OTHER_VENDOR_CHECK.md`.
5. The lane brief in `lanes/`. A pool agent reads its own brief and the files that brief names.

## Execution order

1. **Preconditions.** The operator answers the one batched set in `09_EXECUTION_BINDING.md` (P1 to
   P5). No child is created before P1, P2 and P3 hold.
2. **Bootstrap sitting.** The CTO re-runs `cto_mode.py on`, rechecks the seven heads and the open-PR
   table, launches five children with `cto_mode.py launch-spec`, and hands each its lane brief: L1, L2,
   F1, F2, N1. The CTO opens G0 with the operator in the same sitting if P4 says now.
3. **Wave 1.** L1 and L2 publish the ADR and invariant pull requests first. F1, F2 and N1 run their
   ungated steps. H1 goes to the first idle slot by `CTO ASSIGN`. The CTO runs S0 and G1 itself and
   keeps the harvest ledger.
4. **Stage 1 integration.** When L1 and L2 report `ready-to-merge`, the CTO tests the exact combined
   Core and SDK heads in a disposable worktree (lane I1). Component green is not integrated green.
5. **Wave 1 exit.** Ready-to-merge pull requests, the findings register with a disposition per ID, and
   `CURSOR_CANARY_BLOCKED` with reason `BLOCKED_ON_PROMOTION`. The CTO reports once and stops asking.
6. **Wave 2.** After the operator merges and Core advances its SDK pin, the CTO runs
   `CURSOR_CANARY.md` on the real Cursor-Governance consumer, then EIE, CEG and Odoo. Only
   `CURSOR_CANARY_PASS` opens consumer cleanup and fleet work.
7. **Closeout.** `PROOF.md` P0 to P14 by number, each row `PASS`, `BLOCKED` with owner and next action,
   or `NOT_PROVEN`. No false green.

## CTO ownership and swarm discipline

- The CTO owns integration, decisions inside the frozen architecture, the harvest ledger, G0, every
  `.github` write and the final receipt. It reviews every lane diff against its brief. It never pushes
  to a lane's branch and never remediates a lane's pull request; a defect goes back as
  `CTO REMEDIATE <pr>`.
- Fixed pool of five, launched once, reused by `CTO ASSIGN`. One mutating agent per repository.
- Pool agents report only in their own transcript with `CTO-STATUS:`, `CTO-QUESTION:` and
  `CTO-BLOCKER:` lines. They never message the operator or another session.
- Publishing is part of done and is never put to the operator. Merging is the operator's.
- A foreign open pull request is read, never edited. See the Stacking section of the binding.
- A failing test is evidence. It is classified and repaired at its cause, never skipped or weakened.

## Stop condition

Finish when every mandatory `PROOF.md` criterion has evidence. If an owner decision, a merge or a
vendor account blocks one, record `BLOCKED` with the single action needed and keep every independent
lane moving. Do not weaken a control, widen scope, or report the campaign as shipped.
