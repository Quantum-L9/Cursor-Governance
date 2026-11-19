```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/Enrichment.Inference.Engine
  read_only:
    - https://github.com/Quantum-L9/Cognitive.Engine.Graphs
    - https://github.com/Quantum-L9/Constellation.Gate
  unlisted_repositories: no_access
```
# Lane E2E | Real signed integration test and crash replay

**Role:** writer lane; CTO is coordinator, integration/merge owner. This brief is **not** the child system prompt.

**Objective:** Implement minimum combined test rail assertions under existing EIE e2e/integration test owners, do not create a second infrastructure orchestrator.

**Lane predecessor:** none. **Activation barrier gates:** G0.

## Reserved write surfaces

- https://github.com/Quantum-L9/Enrichment.Inference.Engine: tests/e2e/*
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: tests/integration/test_eie_ceg_mesh.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: scripts/eie_ceg_mesh_verify.sh

## Required acceptance

- Real Gate+EIE+CEG+Postgres+Neo4j test with exact tenant/domain pins and before/after graph readback.
- Two process-kill windows, duplicate packet, second minimal non-PlasticOS cartridge and actual scoring delta.
- Correct accepted/persisted/applied/consumed distinctions in receipts.
- Publish any substantive code changes only through current governed make pr with verified explicit same-repository stack parent. Record exact PR URL, parent and head; own required CI and reviewer remediation until green.
- Do not run manual Docker/five-service integration before CTO verifies all campaign PRs are published and current-head green; use focused unit/contracts and existing mandated CI only.

## Explicit exclusions

- No raw Git push or unauthorized merge/deploy
- No global-law or unauthorized out-of-scope repo edits
- Makefile and Repo.mk are out of scope; no edits, generation, or workaround patches.
- No direct git push/gh pr create; no approvals requested solely for AGENT.md/AGENTS.md protected-doc changes in this campaign.
- No edits to Makefile or Repo.mk in any repository.

Mode and repo-access boundaries must be verified by current host. Coding workers do not call cross-session messaging tools; they report CTO-* lines in own transcript or Task result. Publication via current verified `make pr` only when this lane is writable and authorized. Each publisher owns its PR to ready-to-merge, then becomes idle and waits for CTO assignment. No lane merges or production mutation without separate authorization.
