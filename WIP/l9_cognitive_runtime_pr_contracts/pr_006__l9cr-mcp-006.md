# PR-006 — Derive execution graphs from execution contracts

```yaml
contract_version: "l9.pr-contract/1"
contract_id: "L9CR-MCP-006"
title: "Derive execution graphs from execution contracts"
repository: "https://github.com/Quantum-L9/l9-cognitive-runtime"
base_branch: "main"
suggested_branch: "feat/mcp-006"
optional: false
depends_on:
  - "L9CR-MCP-005"
objective: >
  Generate execution graphs from validated execution contracts, including explicit nodes, edges, evidence, validation gates, and terminal conditions.
execution_policy:
  one_contract_per_pr: true
  preserve_scope: true
  fail_closed_on_unknowns: true
in_scope:
  - "contract-derived nodes and edges"
  - "dependency resolution"
  - "acyclicity"
  - "deterministic topological ordering"
  - "golden/property tests"
out_of_scope:
  - "node execution"
  - "shell access"
  - "repository mutation"
  - "remote agents"
  - "MCP"
acceptance_criteria:
  - "contract changes alter graph"
  - "cycles and missing dependencies rejected"
  - "identical contracts produce identical graphs"
  - "scheduler honors dependencies"
evidence_required:
  - "contract-graph mapping"
  - "golden graphs"
  - "cycle/missing dependency tests"
  - "determinism results"
commit_message: "feat: derive execution graphs from contracts"
pr_title: "feat: make execution graphs contract-driven"
pr_body:
  risk: "See source contract; preserve stated risk classification."
  rollback: "Revert this pull request."
```
