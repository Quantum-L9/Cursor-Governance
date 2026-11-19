```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/Enrichment.Inference.Engine
  read_only:
    - https://github.com/Quantum-L9/Cognitive.Engine.Graphs
    - https://github.com/Quantum-L9/Constellation.Gate
  unlisted_repositories: no_access
```
# Lane OUT | EIE persisted result to CEG durable outbox

**Role:** writer lane; CTO is coordinator, integration/merge owner. This brief is **not** the child system prompt.

**Objective:** At existing side-effect owner persist and replay graph-pending payload/operation id; ensure same evidence and no extra research call on recovery.

**Lane predecessor:** none. **Activation barrier gates:** G0.

## Current-state corrections (pack v1.3.0)

- `tests/unit/test_score_invalidation.py` does NOT exist at the pinned baseline — it is a NEW regression file in this lane. EIE #359 (merged 2026-11-18; the pinned baseline head) already stopped the false `score-invalidate` emission and the unbound staging ingress, and Gate canonically routes no `score-invalidate` action. Write the regression suite around the merged fix; never re-implement or revert it.
- All other reserved surfaces exist at the pin; migrations under `migrations/versions/*` are deliberately added by this lane.

## Reserved write surfaces

- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/side_effect_coordinator.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/pg_models.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: migrations/versions/*
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/engines/handlers.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/engines/packet_router.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: tests/unit/test_side_effect_coordinator.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: tests/unit/test_converge_graph_sync.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: tests/unit/test_score_invalidation.py

## Required acceptance

- Persist pending graph work with actual existing store or minimal proven migration.
- Use injected durable-store restart simulator and original pinned outbox payload with idempotent ACK test now; actual process kill plus CEG Neo4j readback is P4 G_RAIL.
- No completed-graph claim without CEG ACK and no paid replay.
- Publish any substantive code changes only through current governed make pr with verified explicit same-repository stack parent. Record exact PR URL, parent and head; own required CI and reviewer remediation until green.
- Do not run manual Docker/five-service integration before CTO verifies all campaign PRs are published and current-head green; use focused unit/contracts and existing mandated CI only.

## Explicit exclusions

- No raw Git push or unauthorized merge/deploy
- No global-law or unauthorized out-of-scope repo edits
- Makefile and Repo.mk are out of scope; no edits, generation, or workaround patches.
- No direct git push/gh pr create; no approvals requested solely for AGENT.md/AGENTS.md protected-doc changes in this campaign.
- No edits to Makefile or Repo.mk in any repository.

Mode and repo-access boundaries must be verified by current host. Coding workers do not call cross-session messaging tools; they report CTO-* lines in own transcript or Task result. Publication via current verified `make pr` only when this lane is writable and authorized. Each publisher owns its PR to ready-to-merge, then becomes idle and waits for CTO assignment. No lane merges or production mutation without separate authorization.
