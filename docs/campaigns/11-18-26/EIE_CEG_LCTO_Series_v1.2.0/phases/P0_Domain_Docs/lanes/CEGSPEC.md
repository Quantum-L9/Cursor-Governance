```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/Cognitive.Engine.Graphs
  read_only:
    - https://github.com/Quantum-L9/Enrichment.Inference.Engine
    - https://github.com/Quantum-L9/Constellation.Gate
  unlisted_repositories: no_access
```
# Lane CEGSPEC | CEG native admission correction when actually needed

**Role:** writer lane; CTO is coordinator, integration/merge owner. This brief is **not** the child system prompt.

**Objective:** Test and minimally repair existing CEG native pack admission or typed-sync validator only when a source-proven defect lies in CEG; do not create alternate tenant spec authority.

**Lane predecessor:** none. **Activation barrier gates:** G0.

## Reserved write surfaces

- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/config/loader.py
- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/config/tenant_mapping.py
- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/sync/row_contract.py
- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: tests/unit/test_domain_pack_loader.py
- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: tests/unit/test_native_domain_integrity.py

## Required acceptance

- CEG loads a source-proven, admitted tenant pack with correct identity and typed node/edge compatibility.
- If existing code already satisfies requirements, record proof and publish no cosmetic code PR.
- No new framework or fallback to archived PlasticOS YAML.
- Publish any substantive code changes only through current governed make pr with verified explicit same-repository stack parent. Record exact PR URL, parent and head; own required CI and reviewer remediation until green.
- Do not run manual Docker/five-service integration before CTO verifies all campaign PRs are published and current-head green; use focused unit/contracts and existing mandated CI only.

## Explicit exclusions

- No raw Git push or unauthorized merge/deploy
- No global-law or unauthorized out-of-scope repo edits
- Makefile and Repo.mk are out of scope; no edits, generation, or workaround patches.
- No direct git push/gh pr create; no approvals requested solely for AGENT.md/AGENTS.md protected-doc changes in this campaign.
- No edits to Makefile or Repo.mk in any repository.

Mode and repo-access boundaries must be verified by current host. Coding workers do not call cross-session messaging tools; they report CTO-* lines in own transcript or Task result. Publication via current verified `make pr` only when this lane is writable and authorized. Each publisher owns its PR to ready-to-merge, then becomes idle and waits for CTO assignment. No lane merges or production mutation without separate authorization.
