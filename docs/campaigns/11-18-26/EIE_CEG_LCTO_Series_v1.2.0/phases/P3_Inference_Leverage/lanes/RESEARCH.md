```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/Enrichment.Inference.Engine
  read_only:
    - https://github.com/Quantum-L9/.github
  unlisted_repositories: no_access
```
# Lane RESEARCH | DeepSeek + Perplexity bounded research

**Role:** writer lane; CTO is coordinator, integration/merge owner. This brief is **not** the child system prompt.

**Objective:** Implement cheapest extraction, targeted sourced research and Perplexity escalation inside existing clients/orchestrator; no duplicated requests or false no-search completion.

**Lane predecessor:** none. **Activation barrier gates:** G0.

## Current-state corrections (pack v1.3.0)

- `app/services/deepseek_client.py` and `tests/unit/test_enrichment_orchestrator.py` do NOT exist at the pinned baseline — both are NEW files. The DeepSeek client is a NEW provider surface: the pinned AGENTS.md declares the stack `Perplexity LLM` only. DeepSeek is authorized by the operator for this campaign (activation session, 2026-11-18); the DOC owner updates the AGENTS.md stack claim in the same wave. Provider credentials come only from the governed secret binding.

## Reserved write surfaces

- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/engines/enrichment_orchestrator.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/engines/search_optimizer.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/perplexity_client.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/prompt_builder.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/deepseek_client.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/core/config.py
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: tests/unit/test_enrichment_orchestrator.py

## Required acceptance

- No identical fanout for same acquisition; max budget and deadline honored.
- Real per-field retrieval provenance carried; web-required unsupported claims withheld.
- DeepSeek no-web with supplied document makes a real extraction attempt; no empty completed false green.
- Publish any substantive code changes only through current governed make pr with verified explicit same-repository stack parent. Record exact PR URL, parent and head; own required CI and reviewer remediation until green.
- Do not run manual Docker/five-service integration before CTO verifies all campaign PRs are published and current-head green; use focused unit/contracts and existing mandated CI only.

## Explicit exclusions

- No raw Git push or unauthorized merge/deploy
- No global-law or unauthorized out-of-scope repo edits
- Makefile and Repo.mk are out of scope; no edits, generation, or workaround patches.
- No direct git push/gh pr create; no approvals requested solely for AGENT.md/AGENTS.md protected-doc changes in this campaign.
- No edits to Makefile or Repo.mk in any repository.

Mode and repo-access boundaries must be verified by current host. Coding workers do not call cross-session messaging tools; they report CTO-* lines in own transcript or Task result. Publication via current verified `make pr` only when this lane is writable and authorized. Each publisher owns its PR to ready-to-merge, then becomes idle and waits for CTO assignment. No lane merges or production mutation without separate authorization.
