# Scheduler and Leases

A runtime task is eligible only when:

- the Program Lock and ledger validate;
- its definition is ready;
- predecessor tasks are passed locally or completed;
- required decisions are accepted;
- blocking Unknowns are resolved or explicitly accepted by program authority;
- wave entry gates pass;
- target state is reconciled and clean;
- Source Contract is exact and within the Blueprint ceiling;
- required approval is valid;
- no conflicting active lease exists.

One repository may have only one active writer lease. Lease expiry triggers evidence-preserving recovery, not deletion.
