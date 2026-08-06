# PR-004 — Add immutable runtime pack loading, manifest verification, and provenance

```yaml
contract_version: "l9.pr-contract/1"
contract_id: "L9CR-MCP-004"
title: "Add immutable runtime pack loading, manifest verification, and provenance"
repository: "https://github.com/Quantum-L9/l9-cognitive-runtime"
base_branch: "main"
suggested_branch: "feat/mcp-004"
optional: false
depends_on:
  - "L9CR-MCP-003"
objective: >
  Add deterministic immutable pack loading, manifest verification, safe path resolution, and provenance on every runtime bundle.
execution_policy:
  one_contract_per_pr: true
  preserve_scope: true
  fail_closed_on_unknowns: true
in_scope:
  - "RuntimePack and PackLoader"
  - "manifest validation"
  - "path traversal protection"
  - "hash verification"
  - "PackProvenance"
  - "tamper tests"
out_of_scope:
  - "remote downloads"
  - "publishing"
  - "signing infrastructure"
  - "mutable aliases"
  - "MCP"
  - "authentication"
acceptance_criteria:
  - "explicit pack_ref required"
  - "path escape rejected"
  - "missing/tampered manifest rejected"
  - "RuntimeBundle contains provenance"
  - "pack remains immutable"
evidence_required:
  - "manifest interpretation"
  - "pack example"
  - "traversal and tamper tests"
  - "bundle provenance"
commit_message: "feat: add immutable runtime pack loader"
pr_title: "feat: add pack loading and provenance verification"
pr_body:
  risk: "See source contract; preserve stated risk classification."
  rollback: "Revert this pull request."
```
