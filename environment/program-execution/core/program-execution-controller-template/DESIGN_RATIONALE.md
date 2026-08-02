# Design Rationale

The v2 Controller is a runtime projection engine, not a second planning authority.

It preserves the strongest laws from the source controller while deepening the seam with the Blueprint:

1. import intent instead of redefining it;
2. bind every task to a registered target and exact state;
3. enforce Blueprint authorization as a ceiling;
4. model decisions and Unknowns as runtime blockers without rewriting source;
5. separate worker attempt claims from independent verification;
6. require exact changed-file agreement;
7. record gate evaluations as receipts, not mutable Blueprint fields;
8. enforce explicit lifecycle transitions;
9. preserve evidence during recovery;
10. export runtime truth through a Handoff Receipt for program-owner acceptance.
