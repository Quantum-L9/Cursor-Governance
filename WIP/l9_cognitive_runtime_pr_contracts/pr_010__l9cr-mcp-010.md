# PR-010 — Add hosted MCP Streamable HTTP transport

```yaml
contract_version: "l9.pr-contract/1"
contract_id: "L9CR-MCP-010"
title: "Add hosted MCP Streamable HTTP transport"
repository: "https://github.com/Quantum-L9/l9-cognitive-runtime"
base_branch: "main"
suggested_branch: "feat/mcp-010"
optional: false
depends_on:
  - "L9CR-MCP-009"
objective: >
  Expose the read-only MCP server through Streamable HTTP at /v1/mcp while preserving a separate stdio entry point.
execution_policy:
  one_contract_per_pr: true
  preserve_scope: true
  fail_closed_on_unknowns: true
in_scope:
  - "HTTP app and settings"
  - "/v1/mcp"
  - "/healthz"
  - "/readyz"
  - "origin/request-size/concurrency/timeout controls"
  - "HTTP tests"
out_of_scope:
  - "OAuth"
  - "public production deployment"
  - "GitHub identity"
  - "distributed RunStore"
  - "mutating tools"
acceptance_criteria:
  - "MCP initializes over /v1/mcp"
  - "tool parity with stdio"
  - "oversize/origin/time/concurrency enforcement"
  - "stdio opens no socket"
evidence_required:
  - "HTTP initialize/tool call"
  - "origin/size/concurrency tests"
  - "health/readiness"
commit_message: "feat: add MCP Streamable HTTP transport"
pr_title: "feat: expose cognitive runtime over Streamable HTTP"
pr_body:
  risk: "See source contract; preserve stated risk classification."
  rollback: "Revert this pull request."
```
