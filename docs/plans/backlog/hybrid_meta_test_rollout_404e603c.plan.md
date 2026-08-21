---
name: Hybrid Meta Test Rollout
overview: "Roll out a YAML-driven, repo-wide meta-test using a hybrid policy: fail invalid literals immediately, capture unknown dynamic values as telemetry, then harden to proven dynamic-source enforcement after baseline stabilization."
todos:
  - id: catalog-schema
    content: Define YAML catalog schema for method/param pairs, scan globs, excludes, and dynamic policy flags.
    status: pending
  - id: engine-refactor
    content: Refactor test engine to load/validate YAML and drive AST checks from catalog entries.
    status: pending
  - id: hybrid-telemetry
    content: Implement hybrid warning telemetry for unknown dynamic values with stable CI-readable output.
    status: pending
  - id: repo-wide-scan
    content: Switch scan scope to repo-root *.py with strict noisy-dir exclusions and drift metrics.
    status: pending
  - id: promotion-path
    content: Add promotion mechanism from hybrid_warn to prove_dynamic per pair with explicit thresholds.
    status: pending
isProject: false
---

# Hybrid-to-Dynamic Meta-Test Revision Plan

## Objective

Build a frontier-grade, repo-wide contract enforcement system for method/param call validity using a staged policy:

- Stage 1 (Hybrid): fail invalid literals, warn/telemetry for unknown dynamic values.
- Stage 2 (Dynamic Enforcement): require provable dynamic source patterns for protected pairs.

## Scope

- Convert hardcoded pair definitions in `[/Users/ib-mac/Projects/L9/tests/ci/test_repository_contract_calls.py](/Users/ib-mac/Projects/L9/tests/ci/test_repository_contract_calls.py)` into a YAML contract catalog.
- Expand scan target to all Python files under repo root, with strict exclude rules.
- Preserve current passing behavior for literal validation while adding dynamic telemetry and migration gates.

## Design

- **Policy Catalog (YAML):** new catalog file (e.g. `[/Users/ib-mac/Projects/L9/config/contracts/repository_contract_pairs.yaml](/Users/ib-mac/Projects/L9/config/contracts/repository_contract_pairs.yaml)`) containing:
  - `scan.include_globs` / `scan.exclude_globs`
  - `pairs[]` with `method`, `param`, `allowed_literals`, `dynamic_policy`, `severity`
  - `dynamic_sources.allow_patterns` (for Phase 2 promotion)
- **Test Engine (Python):** loader + schema validator + AST scanner in `[/Users/ib-mac/Projects/L9/tests/ci/test_repository_contract_calls.py](/Users/ib-mac/Projects/L9/tests/ci/test_repository_contract_calls.py)`.
- **Hybrid Reporting:** emit structured warning output for unresolved dynamics (file, line, method, param, expression kind) without failing in Stage 1.

## Rollout Phases

1. **Baseline Hybrid (non-breaking):**
  - Fail only on literal values outside allowlist.
  - Record unknown dynamic expressions as warnings/telemetry.
  - Add snapshot metrics: total callsites, literal-valid, literal-invalid, dynamic-unknown.
2. **Stabilization Window:**
  - Review warning hotspots and classify accepted dynamic source patterns.
  - Add method-specific allow patterns (e.g., enum member, `ctx.scope`, `metadata.get("scope")`).
3. **Promotion to Dynamic Enforcement:**
  - Flip selected protected pairs from `hybrid_warn` to `prove_dynamic`.
  - Fail unknown dynamics for promoted pairs.
  - Keep less-critical pairs on hybrid until noise is near-zero.

## Validation Strategy

- **Unit-level:** schema validation for YAML and parser behavior.
- **Repo-wide meta-test:** all `*.py` under repo root with excludes (`.venv`, `.git`, `node_modules`, `__pycache__`, backup dirs).
- **Regression checks:**
  - no duplicate `(method,param)` in catalog,
  - non-empty allowlists for literal-checked pairs,
  - caller-count drift detection per pair (warn in Stage 1, fail when promoted).

## Deliverables

- YAML catalog for real method/param contracts.
- Refactored test engine loading catalog instead of hardcoded tuples.
- Hybrid warning report format suitable for CI logs.
- Promotion switches per pair for dynamic enforcement.
