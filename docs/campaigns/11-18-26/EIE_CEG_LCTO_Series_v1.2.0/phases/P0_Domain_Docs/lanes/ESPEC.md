```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/Enrichment.Inference.Engine
  read_only:
    - https://github.com/Quantum-L9/Cognitive.Engine.Graphs
    - https://github.com/Quantum-L9/Constellation.Gate
  unlisted_repositories: no_access
```
# Lane ESPEC | EIE native spec and typed compatibility

**Role:** writer lane; CTO is coordinator, integration/merge owner. This brief is **not** the child system prompt.

**Objective:** Inspect and minimally correct the existing native spec compatibility/typed projection owners against actual CEG admitted source; no model of CEG scoring in EIE.

**Lane predecessor:** none. **Activation barrier gates:** G0.

## Reserved write surfaces

- https://github.com/Quantum-L9/Enrichment.Inference.Engine: domains/plasticos/spec.yaml
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/engines/domain_spec_compatibility.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/engines/domain_yaml_reader.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: tests/fixtures/ceg/plasticos.spec.yaml
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: tests/contracts/test_native_domain_spec.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: tests/unit/test_effective_domain_reader.py

## Required acceptance

- Exact EIE vs CEG native revisions and compatibility proof linked to the actually approved CEG pack, or BLOCKED with source owner.
- Wrong tenant, missing endpoint, type/refnamespace discrepancy and stale spec pin reject before sync.
- No PlasticOS-specific branch in shared inference/transport or a second executable CEG spec invented.
- Publish any substantive code changes only through current governed make pr with verified explicit same-repository stack parent. Record exact PR URL, parent and head; own required CI and reviewer remediation until green.
- Do not run manual Docker/five-service integration before CTO verifies all campaign PRs are published and current-head green; use focused unit/contracts and existing mandated CI only.

## Explicit exclusions

- No raw Git push or unauthorized merge/deploy
- No global-law or unauthorized out-of-scope repo edits
- Makefile and Repo.mk are out of scope; no edits, generation, or workaround patches.
- No direct git push/gh pr create; no approvals requested solely for AGENT.md/AGENTS.md protected-doc changes in this campaign.
- No edits to Makefile or Repo.mk in any repository.

Mode and repo-access boundaries must be verified by current host. Coding workers do not call cross-session messaging tools; they report CTO-* lines in own transcript or Task result. Publication via current verified `make pr` only when this lane is writable and authorized. Each publisher owns its PR to ready-to-merge, then becomes idle and waits for CTO assignment. No lane merges or production mutation without separate authorization.
