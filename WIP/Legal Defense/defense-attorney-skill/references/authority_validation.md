# Authority Validation

Before labeling a legal proposition `CONTROLLING`, validate all applicable gates.

## Case gate
- court has authority over the issue
- opinion is published/precedential where required
- disposition is known
- exact holding supports the proposition
- later history does not undermine the proposition
- quoted language comes from the opinion, not a headnote or secondary source
- material factual distinctions are disclosed

## Statute gate
- current enacted text checked
- subsection is correctly identified
- effective date covers the relevant event/proceeding
- later amendments do not change the proposition
- cross-referenced statute/rule checked when necessary

## Local-rule gate
- correct county/district/court
- order/rule currently operative or status explicitly verified
- statewide rule does not supersede it
- the proposition is actually contained in the order/rule

## Status values
- `VERIFIED_PRIMARY_CURRENT`
- `VERIFIED_PRIMARY_HISTORICAL`
- `SECONDARY_ONLY`
- `NEEDS_SUBSEQUENT_HISTORY_CHECK`
- `NEEDS_CURRENT_STATUTE_CHECK`
- `NEEDS_LOCAL_RULE_CHECK`
- `STATUS_UNKNOWN`

Fail closed. `STATUS_UNKNOWN` is preferable to a confident but stale legal claim.
