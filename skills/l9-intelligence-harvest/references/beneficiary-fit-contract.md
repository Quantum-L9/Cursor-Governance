# Beneficiary Fit Contract

Compare donor semantics against the beneficiary without implementing beneficiary changes.

## Rules

- Treat the donor as evidence, never authority.
- If the beneficiary already owns stronger semantics, preserve beneficiary ownership and use MERGE_WITH_EXISTING, KEEP_LOCAL, REJECT, or UNKNOWN as appropriate.
- Never weaken beneficiary safety, validation, authority, or ownership boundaries to make a donor concept fit.
- If beneficiary is `none`, target standalone reusable placement rather than inventing a beneficiary implementation.
- Derive acceptance tests that express behavior, not donor-specific code shape.
- Never create, edit, delete, wire, commit, push, or deploy beneficiary artifacts.

## Retained runtime dependency

A concept may depend on donor runtime only when that dependency is intentionally retained and explicitly declares:

- target;
- probe proving availability;
- failure behavior when unavailable.

Without those three fields, portability closure fails and the concept cannot qualify as a nugget.
