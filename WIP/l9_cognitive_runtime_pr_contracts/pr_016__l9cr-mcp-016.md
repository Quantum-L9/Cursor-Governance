# PR-016 Optional — Add validated agent adapter rendering

```yaml
contract_version: "l9.pr-contract/1"
contract_id: "L9CR-MCP-016"
title: "Add validated agent adapter rendering"
repository: "https://github.com/Quantum-L9/l9-cognitive-runtime"
base_branch: "main"
suggested_branch: "feat/mcp-016"
optional: true
depends_on:
  - "L9CR-MCP-014"
objective: >
  Optionally add deterministic render-only agent adapters that preserve bundle, graph, kernel, constraints, unknowns, and authority exactly.
execution_policy:
  one_contract_per_pr: true
  preserve_scope: true
  fail_closed_on_unknowns: true
in_scope:
  - "renderer interface"
  - "generic MCP renderer"
  - "optional Claude/Cursor renderers"
  - "runtime:render tool"
  - "semantic-equivalence golden tests"
out_of_scope:
  - "execution"
  - "automatic config writes"
  - "repository mutation"
  - "new planning"
  - "graph reordering"
acceptance_criteria:
  - "semantic-equivalence passes"
  - "source bundle digest included"
  - "no planning or side effects"
  - "runtime:render required"
  - "golden tests pass"
evidence_required:
  - "stability evidence"
  - "bundle/render examples"
  - "semantic equivalence"
  - "scope enforcement"
commit_message: "feat: add governed agent adapter rendering"
pr_title: "feat: add deterministic runtime adapter renderers"
pr_body:
  risk: "See source contract; preserve stated risk classification."
  rollback: "Revert this pull request."
```
