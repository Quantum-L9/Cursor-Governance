# PR-015 Optional — Add GitHub organization and team-derived trust mapping

```yaml
contract_version: "l9.pr-contract/1"
contract_id: "L9CR-MCP-015"
title: "Add GitHub organization and team-derived trust mapping"
repository: "https://github.com/Quantum-L9/l9-cognitive-runtime"
base_branch: "main"
suggested_branch: "feat/mcp-015"
optional: true
depends_on:
  - "L9CR-MCP-014"
objective: >
  Optionally add GitHub organization and immutable team-ID trust mapping with fail-closed membership resolution, bounded caches, webhooks, and revocation tests.
execution_policy:
  one_contract_per_pr: true
  preserve_scope: true
  fail_closed_on_unknowns: true
in_scope:
  - "membership resolver"
  - "numeric org/team policy"
  - "positive/negative cache"
  - "single-flight refresh"
  - "signed webhook revocation"
  - "trust tests"
out_of_scope:
  - "repository mutation"
  - "GitHub App installation tokens"
  - "token passthrough"
  - "mutable production policy"
acceptance_criteria:
  - "unmapped/inactive users denied"
  - "numeric IDs govern"
  - "GitHub failure fails closed"
  - "revocation SLO met"
  - "all trust decisions audited"
  - "GitHub token not accepted as MCP bearer"
evidence_required:
  - "numeric-ID policy"
  - "membership transcript"
  - "offboarding/team-removal/webhook tests"
  - "audit examples"
commit_message: "feat: add GitHub-derived MCP trust policy"
pr_title: "feat: add GitHub organization trust enforcement"
pr_body:
  risk: "See source contract; preserve stated risk classification."
  rollback: "Revert this pull request."
```
