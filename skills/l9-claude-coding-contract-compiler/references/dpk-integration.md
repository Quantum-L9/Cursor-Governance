<!-- L9META
parent: l9-claude-coding-contract-compiler
layer: reference
role: dpkintegration
version: 1.0.0
updated: 2026-07-12
sources: Developer-Pack-Kernel.md (DPK-1.0); L9_Alignment_Kernel.v3.yaml
-->

# DPK-1.0 Integration — Six-Layer Control Plane

DPK-1.0 turns a repo into an agent-operable control plane. This skill compiles contracts that
Claude executes; DPK defines the repo context those contracts must read, respect, and produce.
Integration binds each DPK layer to a contract section, so a compiled contract both CONSUMES
the DPK control plane (as authority) and PRODUCES DPK artifacts (as evidence).

## Six Layers → Contract Bindings
| DPK Layer | Artifact | Binds to contract section | Direction |
|---|---|---|---|
| 1 Identity & Capabilities | `.ai/manifest.yaml` | 1 Mandate + 3 Scope Lock | consume: owns/does_not_own bound scope |
| 2 Architectural Truth | verified drift map + `document_status` | 7 Context Normalization | consume: `verified_against.commit` anchors resume-from |
| 3 Change Control | `.ai/examples/task-contract.example.yaml` | 0 Resume-From + 3 Scope Lock | consume: task-contract `scope.allowed/prohibited` seeds scope-lock lists |
| 4 Verification & Evidence | 7 validation classes + `make` targets | 12 Evaluator + 18 Test + 23 Commands | produce: one-commit-per-contract evidence maps to classes |
| 5 Operational Ownership | alert→runbook 1:1 map | 19 Failure Evidence + 20 Documentation | produce: every alert pairs a runbook |
| 6 Transition State | debt & risk register | 25 Non-Goals + 28 Handoff | produce: inherited debt is declared, not treated greenfield |

## DPK Authority Order (folds into contract authority)
DPK's AGENTS.md cascade is adopted as the contract's conflict resolution, ABOVE the sibling's:
```
1. Security, safety, legal constraints
2. Explicit Task Contract definitions        # DPK Layer 3
3. System architecture invariants            # DPK Layer 2 / repository-map.yaml
4. Public interface schemas
5. Architecture Decision Records
6. Automated test assertions                  # DPK Layer 4
7. Local file stylistic conventions
```
This SUPERSEDES the prior contract-internal authority order for DPK-managed repos. When a repo
carries a DPK control plane, the compiled contract MUST cite `.ai/manifest.yaml` ownership as
the outer bound of `scope_lock.in_scope`.

## DPK Scope Derivation (hard)
- `scope_lock.in_scope` MUST be a subset of `.ai/manifest.yaml boundaries.owns`.
- `hard_out_of_scope` MUST include everything in `boundaries.does_not_own` plus the task
  contract's `scope.prohibited`.
- Touching a path outside `repository-map.yaml` domain ownership is a scope violation.

## DPK Prohibited Behaviors (adopted verbatim into every contract)
- DO NOT weaken, comment out, or delete tests to pass the pipeline.
- DO NOT inject unlogged values into telemetry loops.
- DO NOT edit `src/generated/`; edit the schema origin.
- DO NOT use ellipsis truncation markers (`...`) in code — matches the no-stub rule.

## DPK Verification Classes → Fail-Closed Evidence
Map each DPK validation class to the current contract's single checkpointed commit evidence (section 12):
static-analysis (`make lint`), unit (`make test-unit`), contract (`make test-contract`),
integration (`make test-integration`), evaluation (`make evaluate`), performance
(`make test-perf`), resilience (`make test-resilience`). AI features MUST carry an
evaluation suite or the readiness score is forced to zero (DPK red line).

## DPK Readiness Score (adopted as a release gate)
A compiled contract's `promotion_ready` cannot be true unless the DPK score >= 90.
```yaml
weights: {repo_clarity: 10, arch_mapping: 15, local_reproducibility: 10,
          test_eval_coverage: 15, security_boundaries: 10, observability_integrity: 15,
          deploy_rollback: 10, transition_clarity: 15}
bands: {independently_operable: "90-100", conditionally_clear: "80-89", rejected: "0-79"}
red_line_zero_if_any:
  - missing production operations owner in .ai/manifest.yaml
  - no machine-executable rollback target
  - AI feature without evaluation suite
  - broken alert→runbook reference link
```

## Multi-Agent Role Isolation (DPK §3) → Claude sessions
Claude must not validate its own mutations. The contract MUST assign isolated roles across
turns/sessions, never one persona doing all:
- Architect (plans, cannot write impl or approve)
- Implementer (writes minimal code, cannot judge own quality)
- Reviewer/Test (independent config + assertions, cannot write feature logic)
- Specialist Security/Perf (triggered on auth/prompt-schema/hot-loop changes)
For Claude Code this maps to separate sessions or explicit role-scoped turns with
tool restrictions per role.
