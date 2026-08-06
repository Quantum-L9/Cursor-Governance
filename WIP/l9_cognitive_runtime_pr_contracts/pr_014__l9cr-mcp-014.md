# PR-014 — Add cross-client MCP conformance tests and production release gates

```yaml
contract_version: "l9.pr-contract/1"
contract_id: "L9CR-MCP-014"
title: "Add cross-client MCP conformance tests and production release gates"
repository: "https://github.com/Quantum-L9/l9-cognitive-runtime"
base_branch: "main"
suggested_branch: "test/mcp-014"
optional: false
depends_on:
  - "L9CR-MCP-013"
objective: >
  Add automated protocol/OAuth/isolation/provenance conformance tests, manual client certification procedures, and blocking production release gates.
execution_policy:
  one_contract_per_pr: true
  preserve_scope: true
  fail_closed_on_unknowns: true
in_scope:
  - "protocol conformance tests"
  - "OAuth and audience tests"
  - "cross-principal isolation"
  - "client certification"
  - "release checklist and gates"
out_of_scope:
  - "new tools"
  - "graph execution"
  - "mutating operations"
  - "adapter rendering"
  - "all-client support"
acceptance_criteria:
  - "CI conformance runs"
  - "release blocks on failed gate"
  - "both certifications recorded"
  - "release metadata complete"
  - "only read-only tools registered"
evidence_required:
  - "CI conformance"
  - "client certifications"
  - "release metadata"
  - "tool registry diff"
  - "rollback identifier"
commit_message: "test: add MCP conformance and release gates"
pr_title: "test: gate releases on MCP client conformance"
pr_body:
  risk: "See source contract; preserve stated risk classification."
  rollback: "Revert this pull request."
```
