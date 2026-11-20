# Lane S0: preflight, harvest ledger and G0 (CTO session)

## MANIFEST

- Campaign `L9-CI-UNIFIED-LEVERAGE-2026-11-20-v1.7.1`, lane `S0`. Executor: the CTO session.
- Write: `docs/campaigns/11-20-26/L9_CI_Unified_Leverage_Campaign_v1.7.1/**` in Cursor-Governance.
- Read-only: all seven campaign repositories.
- Absorbs v1.7.0 Stage 0, the Stage 0H ledger, and G0.

## OBJECTIVE

Hold the campaign's facts current: the launch recheck, the single harvest ledger, the tool inventory,
and the operator's read-only account answers.

## NON-GOALS

- No lane remediation. No push to a lane branch.
- No scan, test or workflow dispatched. No setting changed on any vendor screen.
- No credential, card detail, invoice or token requested from the operator.
- No Unknown filled in from public repository metadata.

## ASSETS USED

- This pack: `09_EXECUTION_BINDING.md`, `CAMPAIGN.yaml`, `BASELINE.md`, `HARVEST.md`,
  `OPERATOR_VERIFY_FIRST.md`, `G0_OTHER_VENDOR_CHECK.md`, `OTHER_TOOLS_EXECUTION.md` Phase A,
  `TOOL_VALUE.md`, `PROOF.md` P5, P10.
- Cursor-Governance: `governance/cto-mode/MODE.yaml`, `ops/autonomy/cto_mode.py`,
  `docs/DEGRADED_MODE_CONTRACT.md`.

## WORKFLOW

1. **Bootstrap recheck.** Run `cto_mode.py on` again. Re-read the seven heads and every open pull
   request. Update the binding's live recheck if anything moved, and say so in each task prompt.
2. **Launch.** With P1, P2 and P3 holding, build five launches with `cto_mode.py launch-spec` and
   create the children. The task prompt is the lane brief plus the recorded operator decisions and the
   pack head to read from. Schedule the 20-minute check-in while any lane is open.
3. **G0, if P4 says now.** Say the opening words in `OPERATOR_VERIFY_FIRST.md`. Do the self-service
   source check first. Then one screen at a time, each as a link and one navigation step; after each
   answer write one sentence of observed state and mark it `OPERATOR_REPORTED` or `UNKNOWN`. Then the
   `G0_OTHER_VENDOR_CHECK.md` follow-up for the single most consequential missing fact. Write the
   stop/go table to `evidence/G0_SUMMARY.md`.
4. **Release gated items.** For each G0-gated lane item, send that lane a `CTO ANSWER` naming the
   exact action the operator authorized. G0 complete authorizes nothing by itself.
5. **Harvest ledger.** Fold each lane's reported rows into `evidence/HARVEST_LEDGER.md`, one row per
   rule or configuration delta, grouped by true owner, with the `HARVEST.md` fields. A row with a
   missing field stays Unknown with its owner and next proof.
6. **Tool inventory.** Keep `evidence/TOOL_MATRIX.md` with the ten `OTHER_TOOLS_EXECUTION.md` Phase A
   dimensions per tool. Workflow conclusion and native outcome are separate columns.
7. **Check-ins.** Follow `operating_protocol.check_in`. Answer every `CTO-QUESTION` under the decision
   classes. Escalate one exact authority-reserved question at a time.

## CONSTRAINTS

- Operator contact only for the cases in `operating_protocol.invariants.minimal_operator_pings`, plus
  the G0 conversation.
- Every evidence file marks each fact `observed`, `operator-reported` or `inferred`.
- Publish pack updates with `PR_REMEDIATE=0 make pr`.

## DONE-CRITERIA

- Five children report coding-agent mode ACTIVE, or each failure is reported with its session id.
- `evidence/G0_SUMMARY.md` exists with every field `OBSERVED`, `OPERATOR_REPORTED` or `UNKNOWN`, or G0
  is recorded as deferred by the operator.
- The ledger has a row for every donor rule (59) and every configuration delta a lane reported.
- The tool matrix has a row for every tool `OTHER_TOOLS_EXECUTION.md` Phase A names.

## ACTIVATION

Starts at the bootstrap sitting. It does not start before P1, P2 and P3.
