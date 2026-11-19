```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/Enrichment.Inference.Engine
  read_only:
    - https://github.com/Quantum-L9/Cognitive.Engine.Graphs
    - https://github.com/Quantum-L9/Constellation.Gate
  unlisted_repositories: no_access
```
# Lane IN | EIE durable CEG inference feedback intake

**Role:** writer lane; CTO is coordinator, integration/merge owner. This brief is **not** the child system prompt.

**Objective:** Use existing GraphReturnChannel handler as logical ingress, add proven recoverable acceptance/consume/dedupe; queue is performance optimization only. Build against the OUT-owned established persistence interface after early G_SCHEMA rather than waiting for outbound crash tests; never edit schema/migrations.

**Lane predecessor:** none. **Activation barrier gates:** G_SCHEMA.

## Reserved write surfaces

- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/graph_return_channel.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/chassis_handlers.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: tests/services/test_graph_return_channel.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: tests/services/test_chassis_handlers.py

## Required acceptance

- Accepted feedback is persisted and consumed once across injected-store reload in focused tests; live process restart is P4 G_RAIL.
- QueueFull or store failure returns truthful refusal/pending; no silent loss.
- No provenance inflation: graph-inferred value remains sourced and unadmitted if contract requires.
- Publish any substantive code changes only through current governed make pr with verified explicit same-repository stack parent. Record exact PR URL, parent and head; own required CI and reviewer remediation until green.
- Do not run manual Docker/five-service integration before CTO verifies all campaign PRs are published and current-head green; use focused unit/contracts and existing mandated CI only.

## Explicit exclusions

- No raw Git push or unauthorized merge/deploy
- No global-law or unauthorized out-of-scope repo edits
- Makefile and Repo.mk are out of scope; no edits, generation, or workaround patches.
- No direct git push/gh pr create; no approvals requested solely for AGENT.md/AGENTS.md protected-doc changes in this campaign.
- No edits to Makefile or Repo.mk in any repository.

Mode and repo-access boundaries must be verified by current host. Coding workers do not call cross-session messaging tools; they report CTO-* lines in own transcript or Task result. Publication via current verified `make pr` only when this lane is writable and authorized. Each publisher owns its PR to ready-to-merge, then becomes idle and waits for CTO assignment. No lane merges or production mutation without separate authorization.
