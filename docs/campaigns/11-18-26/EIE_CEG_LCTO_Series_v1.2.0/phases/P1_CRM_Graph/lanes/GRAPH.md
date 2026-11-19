```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/Cognitive.Engine.Graphs
  read_only:
    - https://github.com/Quantum-L9/Enrichment.Inference.Engine
  unlisted_repositories: no_access
```
# Lane GRAPH | CEG tenant node, child and relationship materialization

**Role:** writer lane; CTO is coordinator, integration/merge owner. This brief is **not** the child system prompt.

**Objective:** Use CEG native graph sync generator and tenant intake owner to materialize mapped entities/relations, enforcing tenant namespace and approved edge identities.

**Lane predecessor:** none. **Activation barrier gates:** G0.

## Reserved write surfaces

- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/intake/crm_field_scanner.py
- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/intake/intake_compiler.py
- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/intake/impact_reporter.py
- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/sync/generator.py
- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/sync/row_contract.py
- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/handlers.py
- https://github.com/Quantum-L9/Cognitive.Engine.Graphs: tests/unit/test_domain_neutrality_acceptance.py

## Required acceptance

- Graph sync creates declared node and child/edge structures only; no missing edge invented.
- Same source ID replays idempotently; other tenant/resource does not alias.
- Typed CEG mock/injected-driver operations match expected node, child and edge contracts in unit tests; actual Neo4j readback is P4 G_RAIL.
- Publish any substantive code changes only through current governed make pr with verified explicit same-repository stack parent. Record exact PR URL, parent and head; own required CI and reviewer remediation until green.
- Do not run manual Docker/five-service integration before CTO verifies all campaign PRs are published and current-head green; use focused unit/contracts and existing mandated CI only.

## Explicit exclusions

- No raw Git push or unauthorized merge/deploy
- No global-law or unauthorized out-of-scope repo edits
- Makefile and Repo.mk are out of scope; no edits, generation, or workaround patches.
- No direct git push/gh pr create; no approvals requested solely for AGENT.md/AGENTS.md protected-doc changes in this campaign.
- No edits to Makefile or Repo.mk in any repository.

Mode and repo-access boundaries must be verified by current host. Coding workers do not call cross-session messaging tools; they report CTO-* lines in own transcript or Task result. Publication via current verified `make pr` only when this lane is writable and authorized. Each publisher owns its PR to ready-to-merge, then becomes idle and waits for CTO assignment. No lane merges or production mutation without separate authorization.
