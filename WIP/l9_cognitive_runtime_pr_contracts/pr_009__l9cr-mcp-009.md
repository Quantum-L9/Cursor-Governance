# PR-009 — Add isolated MCP run resources and bounded result storage

```yaml
contract_version: "l9.pr-contract/1"
contract_id: "L9CR-MCP-009"
title: "Add isolated MCP run resources and bounded result storage"
repository: "https://github.com/Quantum-L9/l9-cognitive-runtime"
base_branch: "main"
suggested_branch: "feat/mcp-009"
optional: false
depends_on:
  - "L9CR-MCP-008"
objective: >
  Add bounded isolated per-run MCP result storage and resources with TTL, eviction, collision-resistant IDs, and no cross-run leakage.
execution_policy:
  one_contract_per_pr: true
  preserve_scope: true
  fail_closed_on_unknowns: true
in_scope:
  - "RunStore interface"
  - "bounded in-memory store"
  - "run resources"
  - "TTL and LRU/expiry eviction"
  - "isolation tests"
out_of_scope:
  - "persistent DB"
  - "multi-node storage"
  - "OAuth binding"
  - "hosted HTTP"
  - "execution"
acceptance_criteria:
  - "compile_runtime returns run_id"
  - "all resources retrievable"
  - "expiry and unknown IDs return typed not-found"
  - "concurrent isolation"
  - "bounded memory"
  - "no fixed files"
evidence_required:
  - "run lifecycle"
  - "expiry"
  - "eviction"
  - "concurrent isolation"
  - "memory-bound config"
commit_message: "feat: add isolated MCP runtime resources"
pr_title: "feat: add bounded per-run MCP resources"
pr_body:
  risk: "See source contract; preserve stated risk classification."
  rollback: "Revert this pull request."
```
