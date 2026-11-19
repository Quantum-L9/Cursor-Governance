```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/Enrichment.Inference.Engine
  read_only:
    - https://github.com/Quantum-L9/Cognitive.Engine.Graphs
  unlisted_repositories: no_access
```
# Lane CRM | EIE CRM field and entity projection

**Role:** writer lane; CTO is coordinator, integration/merge owner. This brief is **not** the child system prompt.

**Objective:** Connect native CRM adapters to generic spec-driven mapping and graph seed intake, preserving original source_system/resource/record id.

**Lane predecessor:** none. **Activation barrier gates:** G0.

## Reserved write surfaces

- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/crm/base.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/crm/hubspot_client.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/crm/odoo_client.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/crm/salesforce_client.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/crm_field_scanner.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/domain_spec_workflow.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/api/v1/converge.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: tests/test_crm_field_scanner.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: tests/contracts/test_crm_provider_parity.py

## Required acceptance

- Two distinct source resources become unambiguous domain-aligned identity projections.
- Unknown/unmapped fields retained visibly without inventing approved ontology properties.
- Connector failures fail explicitly; empty RPC error result not reported as real no data.
- Publish any substantive code changes only through current governed make pr with verified explicit same-repository stack parent. Record exact PR URL, parent and head; own required CI and reviewer remediation until green.
- Do not run manual Docker/five-service integration before CTO verifies all campaign PRs are published and current-head green; use focused unit/contracts and existing mandated CI only.

## Explicit exclusions

- No raw Git push or unauthorized merge/deploy
- No global-law or unauthorized out-of-scope repo edits
- Makefile and Repo.mk are out of scope; no edits, generation, or workaround patches.
- No direct git push/gh pr create; no approvals requested solely for AGENT.md/AGENTS.md protected-doc changes in this campaign.
- No edits to Makefile or Repo.mk in any repository.

Mode and repo-access boundaries must be verified by current host. Coding workers do not call cross-session messaging tools; they report CTO-* lines in own transcript or Task result. Publication via current verified `make pr` only when this lane is writable and authorized. Each publisher owns its PR to ready-to-merge, then becomes idle and waits for CTO assignment. No lane merges or production mutation without separate authorization.
