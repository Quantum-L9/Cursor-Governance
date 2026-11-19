```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/Enrichment.Inference.Engine
  read_only:
    - https://github.com/Quantum-L9/Cognitive.Engine.Graphs
  unlisted_repositories: no_access
```
# Lane INFER | Inference graph, first-pass closure and value-directed planner

**Role:** writer lane; CTO is coordinator, integration/merge owner. This brief is **not** the child system prompt.

**Objective:** Repair existing rule metadata representation and run cheap inference closure before acquisition, then rank distinct downstream prerequisites by justified marginal value/cost.

**Lane predecessor:** none. **Activation barrier gates:** G0.

## Current-state corrections (pack v1.3.0)

- `tests/unit/test_inference_bridge_v2.py` does NOT exist at the pinned baseline — it is a NEW file. All other reserved surfaces exist at the pin.

## Reserved write surfaces

- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/engines/convergence_controller.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/engines/meta_prompt_planner.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/engines/inference/rule_loader.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/engines/inference_bridge_v2.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/engines/inference_bridge_adapter.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/engines/convergence/field_evidence.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: tests/unit/test_inference_bridge_v2.py

## Required acceptance

- Inference-only fixture uses zero provider calls and preserves versioned provenance.
- One acquired prerequisite produces multi-hop derivations; duplicate converging output counted once, no invented business weights.
- No results outside the requested response schema even when internal graph state expands.
- Publish any substantive code changes only through current governed make pr with verified explicit same-repository stack parent. Record exact PR URL, parent and head; own required CI and reviewer remediation until green.
- Do not run manual Docker/five-service integration before CTO verifies all campaign PRs are published and current-head green; use focused unit/contracts and existing mandated CI only.

## Explicit exclusions

- No raw Git push or unauthorized merge/deploy
- No global-law or unauthorized out-of-scope repo edits
- Makefile and Repo.mk are out of scope; no edits, generation, or workaround patches.
- No direct git push/gh pr create; no approvals requested solely for AGENT.md/AGENTS.md protected-doc changes in this campaign.
- No edits to Makefile or Repo.mk in any repository.

Mode and repo-access boundaries must be verified by current host. Coding workers do not call cross-session messaging tools; they report CTO-* lines in own transcript or Task result. Publication via current verified `make pr` only when this lane is writable and authorized. Each publisher owns its PR to ready-to-merge, then becomes idle and waits for CTO assignment. No lane merges or production mutation without separate authorization.
