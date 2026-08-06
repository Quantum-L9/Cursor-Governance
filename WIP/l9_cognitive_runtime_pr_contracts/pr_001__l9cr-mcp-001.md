# PR-001 — Establish installable Python package and build baseline

```yaml
contract_version: "l9.pr-contract/1"
contract_id: "L9CR-MCP-001"
title: "Establish installable Python package and build baseline"
repository: "https://github.com/Quantum-L9/l9-cognitive-runtime"
base_branch: "main"
suggested_branch: "feat/mcp-001"
optional: false
depends_on:
  []
objective: >
  Convert the repository into an installable Python project without changing cognitive-runtime semantics. Preserve existing runtime, contracts, kernels, manifests, and roadmap while adding a src-based package, tests, linting, typing, and build metadata.
execution_policy:
  one_contract_per_pr: true
  preserve_scope: true
  fail_closed_on_unknowns: true
in_scope:
  - "pyproject.toml"
  - "src/l9_cognitive_runtime/__init__.py"
  - "tests/test_package_import.py"
  - "pytest/Ruff/type-check/build configuration"
  - "README development setup"
out_of_scope:
  - "runtime move"
  - "compiler changes"
  - "MCP"
  - "auth"
  - "deployment"
  - "PyPI publication"
acceptance_criteria:
  - "isolated install succeeds"
  - "import succeeds"
  - "existing behavior unchanged"
  - "pytest and Ruff pass"
  - "wheel and sdist build"
  - "no build/cache artifacts committed"
evidence_required:
  - "before/after tree"
  - "install output"
  - "pytest"
  - "Ruff"
  - "build output"
  - "deferred migration list"
commit_message: "build: establish installable cognitive runtime package"
pr_title: "build: establish Python package baseline"
pr_body:
  risk: "See source contract; preserve stated risk classification."
  rollback: "Revert this pull request."
```
