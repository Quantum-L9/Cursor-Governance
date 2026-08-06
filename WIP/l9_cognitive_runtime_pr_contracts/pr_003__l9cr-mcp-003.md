# PR-003 — Introduce an in-memory CognitiveRuntimeService facade

```yaml
contract_version: "l9.pr-contract/1"
contract_id: "L9CR-MCP-003"
title: "Introduce an in-memory CognitiveRuntimeService facade"
repository: "https://github.com/Quantum-L9/l9-cognitive-runtime"
base_branch: "main"
suggested_branch: "feat/mcp-003"
optional: false
depends_on:
  - "L9CR-MCP-002"
objective: >
  Add one typed in-memory application-service boundary for CLI, tests, and future MCP adapters without fixed repository-root output files.
execution_policy:
  one_contract_per_pr: true
  preserve_scope: true
  fail_closed_on_unknowns: true
in_scope:
  - "CognitiveRuntimeService"
  - "interfaces and dependency injection"
  - "compile_runtime orchestration"
  - "CLI compatibility wrappers"
  - "facade tests"
out_of_scope:
  - "semantic changes"
  - "script removal"
  - "MCP"
  - "persistent storage"
  - "hosted HTTP"
acceptance_criteria:
  - "representative bundle compiles in memory"
  - "equivalent to prior pipeline"
  - "no fixed output files"
  - "CLI preserved"
  - "typed signatures"
  - "no MCP imports"
evidence_required:
  - "before/after call graph"
  - "service example"
  - "golden comparison"
  - "pytest"
  - "type-check"
commit_message: "refactor: add cognitive runtime service facade"
pr_title: "refactor: introduce in-memory runtime service"
pr_body:
  risk: "See source contract; preserve stated risk classification."
  rollback: "Revert this pull request."
```
