# PR-012 — Add containerization and production deployment baseline

```yaml
contract_version: "l9.pr-contract/1"
contract_id: "L9CR-MCP-012"
title: "Add containerization and production deployment baseline"
repository: "https://github.com/Quantum-L9/l9-cognitive-runtime"
base_branch: "main"
suggested_branch: "feat/mcp-012"
optional: false
depends_on:
  - "L9CR-MCP-011"
objective: >
  Package the authenticated read-only MCP service as an immutable non-root container and add deployment, scanning, rollback, and operations baselines.
execution_policy:
  one_contract_per_pr: true
  preserve_scope: true
  fail_closed_on_unknowns: true
in_scope:
  - "multi-stage Dockerfile"
  - "non-root/read-only runtime"
  - "container health checks"
  - "image scan workflow"
  - "digest deployment"
  - "rollback and operations docs"
out_of_scope:
  - "cloud-provider selection"
  - "mutating tools"
  - "GitHub App"
  - "multi-region"
  - "autoscaling"
acceptance_criteria:
  - "container builds and runs non-root"
  - "required endpoints work"
  - "no secrets"
  - "pack provenance matches"
  - "scan policy satisfied"
  - "digest deployment"
  - "rollback verified"
evidence_required:
  - "container build/user"
  - "endpoint smoke"
  - "secret and vulnerability scans"
  - "image digest"
  - "deploy/rollback transcript"
commit_message: "build: add production MCP container baseline"
pr_title: "build: containerize the hosted cognitive runtime MCP"
pr_body:
  risk: "See source contract; preserve stated risk classification."
  rollback: "Revert this pull request."
```
