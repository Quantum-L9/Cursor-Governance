# PR-005 — Harden compiler parsing and remove silent fallback behavior

```yaml
contract_version: "l9.pr-contract/1"
contract_id: "L9CR-MCP-005"
title: "Harden compiler parsing and remove silent fallback behavior"
repository: "https://github.com/Quantum-L9/l9-cognitive-runtime"
base_branch: "main"
suggested_branch: "fix/mcp-005"
optional: false
depends_on:
  - "L9CR-MCP-004"
objective: >
  Remove silent parser fallbacks, guessed values, and authority-bearing defaults. Malformed or ambiguous inputs must fail with typed deterministic errors.
execution_policy:
  one_contract_per_pr: true
  preserve_scope: true
  fail_closed_on_unknowns: true
in_scope:
  - "typed error envelopes"
  - "strict YAML/JSON/schema handling"
  - "explicit kernel activation"
  - "unknown preservation"
  - "fallback-removal tests"
out_of_scope:
  - "kernel policy changes"
  - "graph changes"
  - "MCP"
  - "authentication"
acceptance_criteria:
  - "malformed inputs cannot succeed"
  - "unknown kernels never substitute"
  - "empty plans gain no authority"
  - "typed deterministic error codes"
  - "valid fixtures still compile"
evidence_required:
  - "removed fallback inventory"
  - "before/after malformed behavior"
  - "error examples"
  - "pytest"
  - "type-check"
commit_message: "fix: enforce strict cognitive runtime parsing"
pr_title: "fix: remove silent compiler fallbacks"
pr_body:
  risk: "See source contract; preserve stated risk classification."
  rollback: "Revert this pull request."
```
