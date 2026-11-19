```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/Cognitive.Engine.Graphs
  read_only:
    - https://github.com/Quantum-L9/Enrichment.Inference.Engine
    - https://github.com/Quantum-L9/Constellation.Gate
  unlisted_repositories: no_access
```
# Lane DECISION | CEG graph-backed matching, readiness and evidence

**Role:** writer lane; CTO is coordinator, integration/merge owner. This brief is **not** the child system prompt.

**Objective:** At existing CEG owner prove actual persisted graph nodes/edges participate in one gate/dimension score or match with evidence, and provide next legitimate gap.

**Lane predecessor:** none. **Activation barrier gates:** G0.

## Reserved write surfaces

- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/health/api.py
- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/health/gap_prioritizer.py
- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/handlers.py
- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/scoring/graph_evidence.py
- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: tests/unit/test_handle_score.py

## Required acceptance

- Before/after CEG score/match/readiness reflects correctly admitted new data, not a fabricated scoring output.
- Unreviewed edge relevance and unobserved claims never counted as scored evidence.
- No unapproved remote_score_enabled activation; no worker score privilege.
- Publish any substantive code changes only through current governed make pr with verified explicit same-repository stack parent. Record exact PR URL, parent and head; own required CI and reviewer remediation until green.
- Do not run manual Docker/five-service integration before CTO verifies all campaign PRs are published and current-head green; use focused unit/contracts and existing mandated CI only.

## Explicit exclusions

- No raw Git push or unauthorized merge/deploy
- No global-law or unauthorized out-of-scope repo edits
- Makefile and Repo.mk are out of scope; no edits, generation, or workaround patches.
- No direct git push/gh pr create; no approvals requested solely for AGENT.md/AGENTS.md protected-doc changes in this campaign.
- No edits to Makefile or Repo.mk in any repository.

Mode and repo-access boundaries must be verified by current host. Coding workers do not call cross-session messaging tools; they report CTO-* lines in own transcript or Task result. Publication via current verified `make pr` only when this lane is writable and authorized. Each publisher owns its PR to ready-to-merge, then becomes idle and waits for CTO assignment. No lane merges or production mutation without separate authorization.
