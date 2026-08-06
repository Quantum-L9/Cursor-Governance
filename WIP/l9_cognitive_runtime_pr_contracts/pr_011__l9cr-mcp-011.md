# PR-011 — Add OAuth authentication, scoped authorization, and audit middleware

```yaml
contract_version: "l9.pr-contract/1"
contract_id: "L9CR-MCP-011"
title: "Add OAuth authentication, scoped authorization, and audit middleware"
repository: "https://github.com/Quantum-L9/l9-cognitive-runtime"
base_branch: "main"
suggested_branch: "feat/mcp-011"
optional: false
depends_on:
  - "L9CR-MCP-010"
objective: >
  Protect hosted MCP with OAuth 2.1 resource-server behavior, per-invocation scopes, principal-bound runs, and redacted allow/deny audit events.
execution_policy:
  one_contract_per_pr: true
  preserve_scope: true
  fail_closed_on_unknowns: true
in_scope:
  - "protected-resource metadata"
  - "JWT validation"
  - "scope mapping"
  - "audit middleware"
  - "redaction"
  - "principal-bound run access"
  - "auth tests"
out_of_scope:
  - "GitHub team trust"
  - "mutating tools"
  - "GitHub App automation"
  - "admin UI"
  - "long-term warehouse"
acceptance_criteria:
  - "401 discovery works"
  - "scope enforcement works"
  - "wrong audience/expiry rejected"
  - "cross-principal isolation"
  - "allow and deny audit"
  - "no credential leakage"
evidence_required:
  - "protected-resource metadata"
  - "401 challenge"
  - "scoped success"
  - "insufficient scope"
  - "wrong audience"
  - "cross-principal isolation"
  - "redacted audit"
commit_message: "feat: secure hosted MCP with OAuth and audit"
pr_title: "feat: add MCP OAuth, authorization, and auditing"
pr_body:
  risk: "See source contract; preserve stated risk classification."
  rollback: "Revert this pull request."
```
