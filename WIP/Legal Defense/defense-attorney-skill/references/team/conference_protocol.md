# Council Conference Protocol

## Objective
Produce independent concern-specific findings before synthesis, while keeping the user-facing answer concise and preventing hidden assumptions from propagating across seats.

## Step 1 - State lock
Chief Synthesis identifies the current case, phase, court, next material event, dynamic unknowns, and the exact decision being considered. If posture is material and stale, route verification before strategy.

## Step 2 - Independent bounded passes
Each activated cognition reviews the shared sources and returns only:
- `CONCLUSION`
- `BASIS` - source-backed facts, record item, or authority it owns or may properly rely on
- `RISK`
- `UNKNOWN`
- `RECOMMENDATION` within its concern

Do not output private chain-of-thought. Concise rationale is sufficient.

## Step 3 - Cross-concern flags
If a seat encounters an issue outside its concern, it emits `ROUTE_TO: <owning_cognition>` rather than deciding the issue itself.

## Step 4 - State Red Team
For material decisions, build the strongest realistic State response from the same record and current law. Include:
- strongest prosecution framing;
- harmful fact or inference;
- likely rehabilitation or procedural answer;
- what defense action would help the State;
- what a skeptical judge may focus on.

## Step 5 - Preservation review
When later phases may be affected, identify:
- waiver risk;
- disclosure cost;
- testimony rehearsal risk;
- record-preservation value;
- suppression/discovery/appellate effect;
- whether the move is reversible.

## Step 6 - Dissent resolution
Chief Synthesis applies `disagreement_protocol.md`. Do not erase material dissent.

## Step 7 - Decision ranking
Chief Synthesis ranks materially distinct options under the canonical order in `decision_contract.yaml`. Do not create a competing local ranking. Do not create fake numeric precision unless the user requests scoring.


## Step 8 - Operator handoff
For an action recommendation, collapse the council into one executable handoff for Mr. Beylin:
- decision;
- objective;
- exact next act;
- exact words or document only if requested;
- stop condition;
- danger branch;
- new information that triggers re-conference.

## Conference visibility
Default output is integrated. Show seat-by-seat positions only when:
- there is material dissent;
- the user asks to see the council;
- comparing options benefits from distinct expert views;
- the reason for the recommendation would otherwise be unclear.
