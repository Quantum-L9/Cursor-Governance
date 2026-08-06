# PR-008 — Expose the cognitive runtime as a read-only MCP server over stdio

```yaml
contract_version: "l9.pr-contract/1"
contract_id: "L9CR-MCP-008"
title: "Expose the cognitive runtime as a read-only MCP server over stdio"
repository: "https://github.com/Quantum-L9/l9-cognitive-runtime"
base_branch: "main"
suggested_branch: "feat/mcp-008"
optional: false
depends_on:
  - "L9CR-MCP-007"
objective: >
  Expose the deterministic compiler as a read-only local MCP stdio server for Claude Code, Cursor, and compatible hosts. No execution or repository mutation.
execution_policy:
  one_contract_per_pr: true
  preserve_scope: true
  fail_closed_on_unknowns: true
in_scope:
  - "MCP server package"
  - "five read-only tools"
  - "runtime/pack resources"
  - "stdio entry point"
  - "MCP integration tests"
  - "local client docs"
out_of_scope:
  - "HTTP"
  - "OAuth"
  - "persistent storage"
  - "graph execution"
  - "repository writes"
  - "adapter rendering"
  - "sampling"
acceptance_criteria:
  - "Claude Code and Cursor start stdio server"
  - "five tools listed"
  - "compile_runtime succeeds"
  - "no execution or writes"
  - "non-stdio refused"
evidence_required:
  - "initialize response"
  - "tool listing"
  - "compile example"
  - "invalid-input error"
  - "Claude/Cursor configs"
commit_message: "feat: expose cognitive runtime over MCP stdio"
pr_title: "feat: add read-only MCP stdio server"
pr_body:
  risk: "See source contract; preserve stated risk classification."
  rollback: "Revert this pull request."
```
