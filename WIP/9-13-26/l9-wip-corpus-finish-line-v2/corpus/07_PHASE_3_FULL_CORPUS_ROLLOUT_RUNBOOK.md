# Phase 3 - Full Corpus Rollout Runbook

## Objective
Expand from one proven drawer to all selected WIP roots while retaining bounded failure domains and reversible rollout.

## Rollout sequence
1. Register roots with declared stable root keys.
2. Ingest one root at a time; record corpus snapshot and analysis identities.
3. Publish through the same topology/memory contracts; never bypass to Graphiti.
4. Run cross-root duplicate/project/dependency analysis only after every participating root has passed acquisition coverage checks.
5. Enable incremental runs with verified content hashes; cache may accelerate derivation but never establish identity.
6. Track missing/unmounted roots explicitly and prevent partial corpus state from masquerading as complete.
7. Recompute affected WorkUnits and build waves only when their supporting graph neighborhood changes.
8. Keep prior BuildWavePlans immutable as decision history; emit a new plan revision rather than editing history.

## Operational cadence
- source ingestion: event/scheduled based on Dropbox sync capability
- topology compile: after validated corpus generation
- memory publication: preflight then apply
- leverage replanning: when meaningful topology/readiness delta occurs, not on every timestamp change
