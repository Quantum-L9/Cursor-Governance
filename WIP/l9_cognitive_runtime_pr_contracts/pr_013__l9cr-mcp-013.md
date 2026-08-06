# PR-013 — Add reviewable Claude Code and Cursor MCP project configurations

```yaml
contract_version: "l9.pr-contract/1"
contract_id: "L9CR-MCP-013"
title: "Add reviewable Claude Code and Cursor MCP project configurations"
repository: "https://github.com/Quantum-L9/l9-cognitive-runtime"
base_branch: "main"
suggested_branch: "docs/mcp-013"
optional: false
depends_on:
  - "L9CR-MCP-012"
objective: >
  Add reviewable project-scoped Claude Code and Cursor MCP configurations with OAuth discovery and no static credentials.
execution_policy:
  one_contract_per_pr: true
  preserve_scope: true
  fail_closed_on_unknowns: true
in_scope:
  - ".mcp.json"
  - ".cursor/mcp.json"
  - "client setup docs"
  - "secret scanner"
  - "README/CI updates"
out_of_scope:
  - "user-global config"
  - "static auth headers"
  - "PATs"
  - "org-wide install"
  - "ChatGPT admin"
acceptance_criteria:
  - "both clients recognize server and complete OAuth"
  - "no credentials in config"
  - "runtime_capabilities works"
  - "secret scanner proves fail/pass"
evidence_required:
  - "Claude/Cursor listings"
  - "sanitized OAuth transcript"
  - "capabilities calls"
  - "scanner fail/pass"
commit_message: "docs: add Claude Code and Cursor MCP configuration"
pr_title: "docs: enable project-scoped MCP access for Claude Code and Cursor"
pr_body:
  risk: "See source contract; preserve stated risk classification."
  rollback: "Revert this pull request."
```
