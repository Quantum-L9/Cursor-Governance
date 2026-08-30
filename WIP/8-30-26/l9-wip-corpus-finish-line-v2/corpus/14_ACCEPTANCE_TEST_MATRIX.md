# Acceptance Test Matrix

## Seam tests
- meta -> RMP contract
- meta -> Corpus Intelligence contract
- corpus edge coverage
- topology validation
- candidate/canonical non-leakage
- publication integrity forgery rejection
- publication preflight/apply parity
- temporal retraction
- edge property/direction fidelity
- source locator fidelity
- memory replay idempotency
- projection rebuild

## Retrieval tests
- exact named artifact resolution
- dependency expansion
- blocker inclusion
- supersession collapse
- conflict inclusion
- candidate relation labeling
- budget overflow fail-closed
- irrelevant connected artifact exclusion

## Planning tests
- two independent prerequisites are parallelized
- downstream unit waits for prerequisites
- foundational unlock outranks isolated ready work when objective supports it
- high-risk/low-confidence candidate does not outrank proven foundational work by a single opaque score
- retraction removes stale prerequisite from current plan
- counterfactual unlock computation is explainable from graph changes

## End-to-end killer test
Hide Dropbox browsing from the planning agent. Give it only the objective and governed Memory/Graph retrieval. It must recover the correct authoritative files, dependencies, blockers, supersession state, WorkUnits, and build waves closely enough to match expert judgment.
