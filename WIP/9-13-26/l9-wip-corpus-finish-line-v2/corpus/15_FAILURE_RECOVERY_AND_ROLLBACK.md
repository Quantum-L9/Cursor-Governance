# Failure Recovery and Rollback

## Source acquisition failure
No downstream compile. Preserve previous current generation. Report partial/missing roots explicitly.

## Topology validation failure
Do not build/apply publication plan. Fix observation/contract/evidence issue first.

## Publication preflight mismatch
Stop. No apply.

## Memory admission partial failure
Canonical receipts decide truth. Retry by preserved idempotency identity; never invent a replacement plan to hide failed candidates.

## Graphiti projection failure
Canonical Memory remains authoritative. Drain/retry outbox; rebuild projection from canonical state if necessary.

## Bad planning output
No effect on canonical graph. Reject BuildWavePlan revision and re-run planner with preserved evidence/inputs.

## Corpus rollback
Do not rewrite history. Restore previous source corpus only if source owner chooses; otherwise use temporal validity/retraction so current graph state reflects new truth while history remains queryable.
