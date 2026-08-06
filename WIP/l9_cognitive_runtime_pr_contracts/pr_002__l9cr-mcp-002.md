# PR-002 — Add canonical typed models for cognitive runtime artifacts

```yaml
contract_version: "l9.pr-contract/1"
contract_id: "L9CR-MCP-002"
title: "Add canonical typed models for cognitive runtime artifacts"
repository: "https://github.com/Quantum-L9/l9-cognitive-runtime"
base_branch: "main"
suggested_branch: "feat/mcp-002"
optional: false
depends_on:
  - "L9CR-MCP-001"
objective: >
  Define canonical typed Python models for runtime artifacts with deterministic canonical JSON, SHA-256 hashing, YAML serialization, and typed validation errors.
execution_policy:
  one_contract_per_pr: true
  preserve_scope: true
  fail_closed_on_unknowns: true
in_scope:
  - "typed models under src/l9_cognitive_runtime/models"
  - "canonical serialization and hashing"
  - "YAML serializer"
  - "typed errors"
  - "compatibility fixtures and tests"
out_of_scope:
  - "compiler refactor"
  - "schema changes"
  - "MCP"
  - "storage"
  - "authentication"
acceptance_criteria:
  - "all required models exported"
  - "invalid and unknown data rejected"
  - "canonical JSON and digest stable"
  - "YAML uses serializer"
  - "compatibility findings documented"
evidence_required:
  - "schema-model mapping"
  - "unresolved discrepancies"
  - "canonical fixture/digest"
  - "pytest"
  - "type-check"
commit_message: "feat: add canonical cognitive runtime models"
pr_title: "feat: add canonical typed runtime models"
pr_body:
  risk: "See source contract; preserve stated risk classification."
  rollback: "Revert this pull request."
```
