```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/Enrichment.Inference.Engine
  read_only:
    - https://github.com/Quantum-L9/Cognitive.Engine.Graphs
    - https://github.com/Quantum-L9/Constellation.Gate
    - https://github.com/Quantum-L9/Cursor-Governance
    - https://github.com/Quantum-L9/.github
  unlisted_repositories: no_access
```
# Lane DOC | EIE documentation and invariants single writer

**Role:** writer lane; CTO is coordinator, integration/merge owner. This brief is **not** the child system prompt.

**Objective:** Create actual root README and concise AGENTS; repair existing docs/INVARIANTS in place; reconcile ADRs, docs and documentation checks while respecting historical ADR decisions. The operator has suspended the repo-local AGENT.md/AGENTS.md extra human-review protection for scoped campaign documentation changes only; the agent still honors global authorization and the repository/host enforced controls. No manual review pause for these files.

**Lane predecessor:** none. **Activation barrier gates:** none.

## Reserved write surfaces

- https://github.com/Quantum-L9/Enrichment.Inference.Engine: README.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: AGENTS.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: docs/INVARIANTS.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: docs/ARCHITECTURE.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: docs/EXECUTION_FLOWS.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: docs/REPO_MAP.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: docs/FILE_INDEX_FOR_AGENTS.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: docs/contracts/README.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: docs/CLAUDE.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: CLAUDE.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: docs/adr/*.md
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: .github/workflows/docs-consistency.yml
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: local_pr_pipeline/docs_consistency_local.sh
- https://github.com/Quantum-L9/Enrichment.Inference.Engine: local_pr_pipeline/docs_link_check_local.py

## Required acceptance

- Root README explains 2D CRM -> domain graph -> CEG intelligence and marks as-built vs next phases explicitly.
- AGENTS.md shortened and accurate on upstream law, LCTO delegation, current eight Repo.mk checks, protected files, Gate/CEG boundaries, no duplicate operating policy.
- Existing docs/INVARIANTS.md keeps applicable identifiers and adds sharp EIE-only falsifiable product invariants with enforcement/missing enforcement truth.
- Preserve historical ADRs; disambiguate two ADR-011s in current index; successor ADRs only for genuinely revised decisions.
- Documentation and links/tests are correct without fake passes or weakening original mandatory checks.
- Publish any substantive code changes only through current governed make pr with verified explicit same-repository stack parent. Record exact PR URL, parent and head; own required CI and reviewer remediation until green.
- Do not run manual Docker/five-service integration before CTO verifies all campaign PRs are published and current-head green; use focused unit/contracts and existing mandated CI only.

## Explicit exclusions

- No raw Git push or unauthorized merge/deploy
- No global-law or unauthorized out-of-scope repo edits
- Makefile and Repo.mk are out of scope; no edits, generation, or workaround patches.
- No direct git push/gh pr create; no approvals requested solely for AGENT.md/AGENTS.md protected-doc changes in this campaign.
- No edits to Makefile or Repo.mk in any repository.

Mode and repo-access boundaries must be verified by current host. Coding workers do not call cross-session messaging tools; they report CTO-* lines in own transcript or Task result. Publication via current verified `make pr` only when this lane is writable and authorized. Each publisher owns its PR to ready-to-merge, then becomes idle and waits for CTO assignment. No lane merges or production mutation without separate authorization.
