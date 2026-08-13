---
name: l9-repository-renovation
description: audit, reconcile, and renovate a real software repository from fragmented manifests, duplicated automation, stale configuration, dead wiring, ignored tests, documentation drift, and ambiguous ownership into a coherent, validated implementation delivered through a governed pull request. use when the user asks to fix a messy repo end to end, align pyproject/package manifests with actual capabilities, collapse competing dependency or test authorities, turn an audit into full production files, modernize repository control planes, or continue remediation until the pr is green. do not use for audit-only commentary, isolated feature development, cosmetic refactors, or repositories the user has not authorized for modification.
disable-model-invocation: true
---

# L9 Repository Renovation

## Terminal objective

Transform the repository's actual current state into one coherent operating contract, implement the complete files required by that contract, validate the renovated system from cold start, and deliver exactly one reviewable pull request. A report or plan is an intermediate artifact, never the terminal output.

Preserve working product behavior unless verified evidence requires a behavior change. Renovate the control plane before rewriting the product plane.

## Identity lock

Keep these invariants active throughout execution:

1. Inspect the live repository before trusting prior reviews, copied templates, comments, or plans.
2. Collapse competing authorities instead of adding another wrapper, manifest, runner, or registry.
3. Implement complete production files. Do not leave TODOs, placeholders, pseudo-code, commented-out future wiring, or choices for a later coding agent.
4. Preserve externally consumed behavior, public APIs, data contracts, and release compatibility unless the contract explicitly authorizes a migration.
5. Treat ignored tests, ad hoc CI installs, stale manifests, dead executables, duplicate registries, and undocumented package boundaries as system defects until proven intentional.
6. Validate local and CI paths through the same canonical entrypoints.
7. Keep every checkpoint green. Never stack unrelated failures into a final rescue commit.
8. Stop after three implementation-validation cycles for the same failure class. Escalate the exact blocker rather than normalizing failure.
9. Open at most one pull request. Never merge unless the user separately authorizes merge.

## Authority order

Resolve conflicts in this order:

1. Current user instruction and platform safety rules.
2. Live repository state at the resolved base commit.
3. Executable tests, schemas, lockfiles, CI, and runtime behavior.
4. Repository invariants, ADRs, ownership rules, and release contracts.
5. Newest validated audit, contract, or implementation artifact.
6. Comments, prose documentation, copied templates, and historical plans.
7. Model inference, labeled `UNKNOWN` until verified.

Higher authority wins. A comment never overrides executable behavior without an explicit reconciliation decision.

## Reject and reroute

Do not activate this skill when the user wants only an explanation, a narrow feature, a cosmetic cleanup, an ungrounded rewrite, or a repository-independent template. Do not use it to bypass required reviews, branch protections, licensing, security controls, provider quotas, or organizational policy.

When the repository is inaccessible, produce no fictional renovation. State the missing access or materialization step.

## Operating modes

Default to `RENOVATE_TO_PR` when the user asks for implementation or a PR.

- `AUDIT_ONLY`: stop after evidence-backed findings only when explicitly requested.
- `CONTRACT_ONLY`: emit the renovation contract and implementation wave, without edits, only when explicitly requested.
- `PACK_ONLY`: renovate a supplied worktree and produce a PR-ready pack without remote mutation.
- `RENOVATE_TO_PR`: audit, contract, implement, validate, commit, push, open one draft PR, inspect checks, and remediate authorized failures until green.
- `BLOCKED_PACK`: preserve completed work and emit a blocker record when access, policy, or an external dependency prevents completion.

GitHub publishing has separate authorization gates. Stage, commit, push, PR creation, and subsequent remediation pushes each require explicit authorization. If the user has not already named every requested action, ask once for a bundled authorization listing each action. Never infer merge authorization.

## Workflow

### 0. Resolve the live baseline

Before editing:

1. Resolve repository owner/name, default branch, base commit, current branch, worktree cleanliness, open related PRs, and write permissions.
2. Read repository-level instructions, invariants, ownership files, ADRs, package manifests, lockfiles, CI, Makefiles/task runners, test configuration, and release wiring.
3. Re-read files that changed since any prior audit. Prior findings are hypotheses until reconfirmed against the live base.
4. Record the immutable base commit in the renovation contract.
5. If the worktree contains unrelated changes, do not stage or overwrite them. Isolate the renovation on a new branch or worktree.

Load `references/authority-and-scope.md` for base selection, scope ownership, and authorization rules.

### 1. Run forensic discovery

For a materialized repository, run:

```bash
python scripts/audit_repository.py /path/to/repo --output repository-audit.before.json
```

Use the script as a deterministic floor, not a substitute for architectural inspection. Manually verify findings across these classes:

- dependency and package-authority drift;
- test discovery, ignored suites, shadowed packages, and orphaned validators;
- local gate versus CI divergence;
- ad hoc installs outside lockfiles;
- duplicate registries, runners, manifests, and ownership claims;
- dead or partially wired executables;
- config and documentation references to deleted or archived paths;
- release, consumer, and upstream/downstream compatibility;
- security permissions, secret exposure, and unsafe mutation surfaces;
- stale comments that materially misdescribe active behavior.

Load `references/findings-taxonomy.md` for classification and proof requirements. Load the matching stack adapter from `references/stack-adapters.md` only after the stack is verified.

### 2. Synthesize one target operating contract

Do not repair findings independently. First identify the smallest canonical authorities the renovated repository should have, typically:

- one dependency declaration and lock authority per package boundary;
- one test-suite registry or intentionally simple discovery contract;
- one local runner consumed by CI;
- one ownership source for generated registries and mirrors;
- one release and consumer compatibility path;
- one evidence record for validation and rollback.

Compile the audit into an execution contract:

```bash
python scripts/compile_contract.py \
  repository-audit.before.json \
  --repo /path/to/repo \
  --base-ref origin/main \
  --output renovation-contract.json \
  --plan RENOVATION_PLAN.md
python scripts/validate_contract.py renovation-contract.json
```

Then refine the generated contract with verified repository evidence. Freeze:

- exact allowed and forbidden paths;
- preserved behavior and public contracts;
- files to create, replace, rename, or delete;
- authority decisions and superseded mechanisms;
- implementation checkpoints;
- cold-start validation commands;
- rollback method;
- PR and remediation policy;
- explicit blockers and unknowns.

Unknowns that affect safety, scope, or architecture block implementation. Minor unknowns may remain only when the contract names the verification step and prevents speculative edits.

### 3. Implement in leverage order

Use this default sequence unless evidence requires another dependency order:

1. Dependency and package authority.
2. Canonical registry or configuration model.
3. Canonical runner and compatibility entrypoints.
4. Drift validators and negative tests.
5. Local gates and CI rewiring.
6. Documentation and operator handoff.
7. Removal of superseded paths only after replacements prove green.

Write full files. Prefer deleting duplicate authority over synchronizing it forever. Preserve thin compatibility shims only when a real consumer still uses them, and make the shim delegate without owning policy.

Apply the expert heuristics in `references/renovation-method.md` during design and review.

### 4. Validate every checkpoint

Each commit-sized checkpoint must pass its scoped tests and the contract's baseline gates before the next checkpoint begins. Capture command, exit code, duration, and relevant output.

Run the contract matrix with:

```bash
python scripts/run_validation_matrix.py \
  renovation-contract.json \
  --repo /path/to/repo \
  --output validation-evidence.json
```

After implementation, rerun discovery and compare:

```bash
python scripts/audit_repository.py /path/to/repo --output repository-audit.after.json
python scripts/compare_audits.py \
  repository-audit.before.json \
  repository-audit.after.json \
  --json renovation-delta.json \
  --markdown RENOVATION_DELTA.md
```

Do not claim success because finding counts decreased. Require all contract acceptance criteria, no new high-severity finding, no weakened gate, no hidden suite, and no unexplained dependency movement.

When the contract preserves a public API, prove it structurally rather than by assertion. Snapshot the public surface at the base ref and at the renovated head, then classify the compatibility delta:

```bash
python scripts/api_surface.py extract /path/to/repo@base --output api-surface.before.json
python scripts/api_surface.py extract /path/to/repo --output api-surface.after.json
python scripts/api_surface.py diff \
  --before api-surface.before.json \
  --after api-surface.after.json \
  --output api-surface.delta.json \
  --fail-on-break
```

A breaking delta that the contract did not authorize is a stop condition, and the required semver bump must match any version change the renovation declares.

### 5. Build the PR pack

Before staging, run:

```bash
python scripts/validate_pr_pack.py \
  --repo /path/to/repo \
  --contract renovation-contract.json \
  --evidence validation-evidence.json \
  --before repository-audit.before.json \
  --after repository-audit.after.json \
  --output pr-pack-validation.json
```

Generate the PR body:

```bash
python scripts/render_pr_body.py \
  --contract renovation-contract.json \
  --evidence validation-evidence.json \
  --delta renovation-delta.json \
  --output PR_BODY.md
```

The PR must explain:

- the operational defect, not merely the files changed;
- the authority model before and after;
- exact scope and preserved behavior;
- validation evidence and cold-start reproduction;
- dependency or lockfile movement;
- risks, rollback, and remaining debt;
- upstream and downstream implications.

Load `references/pr-lifecycle.md` before any GitHub write.

### 6. Publish and converge

With explicit authorization for each action:

1. Inspect status and diff.
2. Stage only contract-approved paths using explicit path arguments.
3. Create green, reviewable commits in dependency order.
4. Push the feature branch.
5. Reuse an existing matching PR or open exactly one draft PR.
6. Inspect all available checks and review threads.
7. Remediate failures that are caused by this change and within contract scope.
8. Re-run local validation before every remediation push.
9. Stop when required checks are green and no unresolved in-scope review thread remains.
10. Hand off for human review. Do not merge without separate authorization.

A green PR with hidden bypasses, removed tests, floating installs, ignored failures, or unexplained exclusions is not converged.

## Expert review rules

Use these rules as condition, judgment, and action pairs:

1. **A tool or dependency is installed in CI but absent from the lock contract.** Judge that CI owns a second environment. Move the dependency into the canonical declaration and remove the fallback install.
2. **A test path is globally ignored.** Judge it ungoverned until an explicit canonical runner proves execution. Register and run it, or document and test why it is non-test content.
3. **Local and CI commands duplicate orchestration.** Judge that topology will drift. Make CI invoke the repository-owned runner rather than copying its logic.
4. **A non-installable repository still carries packaging metadata.** Judge by actual bootstrap behavior, not aesthetics. Remove or retain build metadata only after proving what the package manager does.
5. **Two source roots expose the same import/package name.** Judge broad discovery unsafe. Isolate suites or package boundaries explicitly instead of adding larger ignore lists.
6. **Documentation claims a capability is active but no executable wiring reaches it.** Judge the capability dead or dormant-by-design. Wire it with tests, or mark the intentional dormancy in the canonical registry.
7. **A global strict gate cannot pass because of inherited debt.** Judge a fake blocking gate worse than an explicit ratchet. Scope the gate, publish debt, and tighten monotonically without hiding failures.

## Failure boundaries

- **Scope explosion:** split the work only when findings cross independent package, release, or ownership boundaries. Do not split tightly coupled authority repair into decorative PRs.
- **Broken baseline:** distinguish pre-existing failure from renovation regression with a recorded baseline. Do not silently fix unrelated failures.
- **Resolver churn:** halt when lockfile movement exceeds what declared changes explain.
- **External check unavailable:** report the exact external check and preserve local evidence; do not claim green.
- **Repeated failure:** after three cycles for the same failure class, stop with the smallest reproducible blocker and completed artifacts.

Load `references/convergence-and-failure.md` for detailed stop conditions.

## After-use improvement

Only when the user reports a bad run or requests iteration, capture:

- a missed or false activation signal;
- a recurring finding the audit script failed to detect;
- a contract ambiguity that caused rework;
- a validation or PR failure that escaped the gates.

Update the smallest rule, adapter, or deterministic script that would prevent recurrence. Do not invent telemetry or grow the skill from hypothetical edge cases.

## Validation

Before distributing this skill, run:

```bash
python scripts/self_test.py
python scripts/validate_exemplary_skill.py .
```

When using the skill on a repository, require contract validation, before/after audits, validation evidence, PR-pack validation, and one PR or an explicit blocked-pack result.

## Resource map

- `references/authority-and-scope.md`: live-baseline, ownership, change authority, and branch safety.
- `references/findings-taxonomy.md`: finding classes, evidence burden, severity, and renovation decisions.
- `references/renovation-method.md`: synthesis model, expert heuristics, leverage sequence, and anti-patterns.
- `references/stack-adapters.md`: conditional Python, Node/TypeScript, and polyglot/monorepo rules.
- `references/pr-lifecycle.md`: authorization ladder, commit discipline, PR creation, check remediation, and handoff.
- `references/convergence-and-failure.md`: validation cycles, rollback, blocker handling, and stop conditions.
- `references/output-contract.md`: required audit, contract, evidence, delta, PR, and blocked-pack structures.
- `scripts/audit_repository.py`: deterministic repository inventory and baseline findings.
- `scripts/compile_contract.py`: convert audit evidence into a bounded renovation contract and plan.
- `scripts/validate_contract.py`: fail-closed structural and semantic contract validation.
- `scripts/run_validation_matrix.py`: execute contract-declared validation and capture evidence.
- `scripts/compare_audits.py`: produce before/after delta evidence.
- `scripts/validate_pr_pack.py`: enforce changed-file scope, evidence, and zero-stub gates.
- `scripts/render_pr_body.py`: render a reviewable PR description from verified artifacts.
- `scripts/api_surface.py`: extract the public API surface by AST and classify the before/after compatibility delta into a fail-closed semver verdict.
- `scripts/self_test.py`: exercise the deterministic workflow against a synthetic messy repository.
- `schemas/`: machine-readable artifact contracts.
