# Case-State Update Protocol

## Objective
Keep the portable case brain current under `../cases/26CR294791-170/case_state_contract.yaml` without rewriting history or silently overwriting source material.

## Immutable source rule
Files under `../cases/26CR294791-170/compiled/` are immutable compiled snapshots. Do not rewrite a historical source proposition to match later information. Add the new source, preserve provenance, emit a delta, and recompile affected modules.

## Update events
A case-state update may be proposed when a new reliable source establishes or changes:
- docket posture;
- court division;
- indictment status;
- hearing date/time;
- charge language;
- testimony;
- admitted evidence;
- filing acceptance/service;
- court order;
- authority status;
- deadline;
- contradiction resolution.

## Delta fields
Return a concise `CASE_STATE_DELTA` containing:
- target file/field;
- previous status/value;
- proposed new status/value;
- source;
- source date/time if known;
- confidence/status label;
- downstream files or analyses affected.

## Merge law
- add provenance;
- preserve prior versions when historically relevant;
- never upgrade a fact status without a qualifying source;
- never erase a contradiction merely because one version is inconvenient;
- update phase only from a verified triggering event;
- do not modify private facts unless the new private value is needed and supplied by Mr. Beylin.

## User-facing behavior
When the new information materially changes strategy, state the delta before relying on the changed state. Do not bury a phase change inside later analysis.
