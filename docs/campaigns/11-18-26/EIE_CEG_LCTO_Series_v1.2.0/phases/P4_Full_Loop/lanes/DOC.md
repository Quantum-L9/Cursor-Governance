```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/Enrichment.Inference.Engine
  read_only:
    - https://github.com/Quantum-L9/Cognitive.Engine.Graphs
    - https://github.com/Quantum-L9/Constellation.Gate
    - https://github.com/Quantum-L9/Cursor-Governance
  unlisted_repositories: no_access
```
# Lane DOC | EIE final as-built README, agent, invariant and ADR alignment

**Role:** writer lane; CTO is coordinator, integration/merge owner. This brief is **not** the child system prompt.

**Objective:** Prepare and publish accurate EIE docs/invariants/AGENTS before the combined Docker run using proved code/contract behavior; after G_RAIL, update the SAME DOC PR if real integration results require corrections. The operator has suspended the repo-local AGENT.md/AGENTS.md extra human-review protection for scoped campaign documentation changes only; the agent still honors global authorization and the repository/host enforced controls. No manual review pause for these files.

**Lane predecessor:** none. **Activation barrier gates:** G0.

## Reserved write surfaces

- https://github.com/Quantum-L9/Enrichment.Inference.Engine: README.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: AGENTS.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: docs/INVARIANTS.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: docs/ARCHITECTURE.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: docs/EXECUTION_FLOWS.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: docs/REPO_MAP.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: docs/contracts/README.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: docs/adr/*.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: docs/FILE_INDEX_FOR_AGENTS.md

## Required acceptance

- Publish accurate pre-Docker code and contract claims without claiming integrated graph+scoring proof; after G_RAIL update this same DOC PR to record actual verified evidence or remaining Unknowns.
- AGENTS.md reflects current runtime, gates, authority hierarchy and real source paths; ADR index/successors reflect all actual decisions.
- Local invariant enforcement status derived from executed tests, not optimistic labels.
- Publish any substantive code changes only through current governed make pr with verified explicit same-repository stack parent. Record exact PR URL, parent and head; own required CI and reviewer remediation until green.
- Do not run manual Docker/five-service integration before CTO verifies all campaign PRs are published and current-head green; use focused unit/contracts and existing mandated CI only.

## Explicit exclusions

- No raw Git push or unauthorized merge/deploy
- No global-law or unauthorized out-of-scope repo edits
- Makefile and Repo.mk are out of scope; no edits, generation, or workaround patches.
- No direct git push/gh pr create; no approvals requested solely for AGENT.md/AGENTS.md protected-doc changes in this campaign.
- No edits to Makefile or Repo.mk in any repository.

Mode and repo-access boundaries must be verified by current host. Coding workers do not call cross-session messaging tools; they report CTO-* lines in own transcript or Task result. Publication via current verified `make pr` only when this lane is writable and authorized. Each publisher owns its PR to ready-to-merge, then becomes idle and waits for CTO assignment. No lane merges or production mutation without separate authorization.
