---
name: optimize-cli-pr-pack
description: Identify underutilized, verified repository-owned capabilities and enable their full utilization — activating dormant or miswired code, off-by-default features, unread config, and unused signals — then package the exact change as a deployable PR commit bundle (changed files, binary-safe patch, revision synthesis, adaptive route, evidence and decision ledger, before-and-after performance evidence, deploy and rollback playbooks, successor-agent handoff). Removing a verified CLI throughput bottleneck is one branch of the same mission. Use when a repository or CLI audit, benchmark, dead-wiring finding, capability brief, patch, or prior sandbox artifact must become production code that safely raises utilization of latent capability the repository already owns. Do not use for audit-only output, non-repository targets, manufacturing capability that does not already exist, new throttling systems, or bypassing provider quotas, billing limits, licensing, authorization, abuse controls, or external service limits.
---

# Optimize CLI PR Pack

## Terminal Objective

Produce a deployable code change that enables an underutilized, verified repository-owned capability — or removes or relaxes a verified repository-owned CLI bottleneck — and package the exact change as a PR-ready commit bundle. Enabling latent capability the repository already owns is the primary mission; throughput is one branch of it.

Audits, plans, benchmarks, and specifications are evidence inputs. They are never substitutes for working code, validation, deployment instructions, rollback, and handoff.

## Identity Lock

Keep these invariants active:

1. Enable a proven, underutilized repository-owned capability, or remove or relax a proven repository-owned CLI bottleneck. Never manufacture capability the repository does not already own, and never activate anything `dormant_by_design`.
2. Preserve correctness, compatibility, safety, truthful documentation, and external contracts.
3. Never implement a new throttle, uncontrolled concurrency spike, or external quota bypass.
4. Produce a deployable PR commit pack, not an audit-only report.
5. Synthesize all material findings before selecting implementation options.
6. Apply leverage after synthesis and before freezing the revision plan.
7. Treat unproven reachability, ownership, or intended behavior as `UNKNOWN`.
8. Preserve unresolved out-of-scope documentation-code divergence as an explicit finding.
9. Route only the proof obligations required by evidence, risk, ownership, and active adapters.
10. Run at most three implementation-validation cycles. A fourth cycle is prohibited.
11. Require comparable performance proof before claiming improvement.

Run `scripts/validate_identity_lock.py` before packaging the Skill or accepting generated output doctrine.

## Authority Order

1. Current user instruction and platform safety rules.
2. Verified target-repository state and executable behavior.
3. Newest validated sandbox or conversation artifact.
4. Repository contracts, tests, packaging, and release configuration.
5. Bundled optimize product, reasoning, synthesis, pack, deployment, and handoff contracts.
6. Targeted external evidence required to close a named gap.
7. `UNKNOWN`.

Higher authority wins. Do not silently merge incompatible versions or let documentation override runtime evidence without reconciliation.

## Activation and Rejection

Activate on strong signals:

- optimize a repo by enabling an underutilized capability it already owns, or remove a verified CLI throughput bottleneck;
- activate proven dormant or miswired capability: inactive components, off-by-default features, unread config, unused signals, or broken producer→consumer wiring;
- convert a repository or CLI audit or benchmark into deployable code, before-and-after performance evidence, and a PR pack;
- repair fixed delay, unnecessary serialization, low local cap, blocking I/O, repeated startup, duplicate work, buffering, lock contention, or local retry drag;
- continue a prior patch or plan into a commit-ready deployment bundle.

Reject or reroute when:

- the objective is a new rate limiter, pacing system, or throttle;
- the request seeks to bypass provider quotas, billing limits, licensing, authorization, or abuse controls;
- the target is not a repository-owned execution path, or has no reachable entrypoint;
- the capability does not already exist and would have to be built from scratch (that is a feature request, not utilization);
- only an audit or explanation is requested;
- ownership is external and circumvention is requested.

## Required Inputs and Operating Modes

Resolve from available context before asking:

- repository or materialized Git worktree;
- bottleneck evidence and expected workload;
- correctness invariants and resource ceilings;
- base ref, branch, deployment path, and release mechanism;
- prior plans, patches, benchmarks, and validation evidence.

Modes:

- `PACK_ONLY`: edit the supplied sandbox worktree and produce a pack without remote mutation.
- `WRITE_AUTHORIZED` by default when a write connector exists: commit, push, or update a PR autonomously.
- `BLOCKED_PACK`: preserve completed work and emit one issue artifact per independent blocker.

Repository-owned targets only. External ownership or a request to bypass provider quotas, billing, licensing, authorization, or abuse controls is still rejected — that boundary is not a write-approval step.

## Context-First Gate

Before external research or rebuilding:

1. Inspect relevant conversation context.
2. Inventory relevant sandbox artifacts by metadata first.
3. Select the newest validated canonical artifact.
4. Reuse, patch, or extend it.
5. Name the exact remaining evidence gap.
6. Perform the smallest authoritative inspection that can resolve it.
7. Stop research when the material gap closes.

Load `references/context-first-reuse.yaml` when prior work exists.

### Diagnosis (repository scan)

When the target is a real repository and no prior finding exists, run `scripts/scan_capabilities.py <repo>` to surface CANDIDATE utilization gaps (inactive components, off-by-default flags) and the repository's entrypoints. Candidates are advisory only — verify each against the latent-capability reachability law (bidirectional evidence, dynamic dispatch, registries, `dormant_by_design`) before authoring a finding. Absence of any reachable entrypoint is a `blocked_pack` signal for the router (`target_reachable`). Use `scripts/measure.py --before <cmd> --after <cmd>` to produce the comparable before/after proof block: median wall-clock by default, or a functional utilization metric with `--capture` (e.g. consumer invocations `0 -> N`).

## Adaptive Execution Router

Load `references/adaptive-optimize-router.yaml` before planning or mutation. Use `scripts/route_optimize.py` when deterministic routing is useful.

Classify independently:

```yaml
task_kind: optimize_cli_revision
utilization_gap_class: repository class | external_limit | unknown
ownership: repository_owned | external | unknown
evidence_state: sufficient | partial | conflicting | absent
risk_class: reversible | guarded | irreversible
docs_code_divergence: none | non_blocking | release_blocking | unknown
latent_capability: true | false
output_mode: pack_only | write_authorized
```

The router returns:

- reasoning depth;
- initial action: `proceed`, `proceed_with_validation`, `bounded_probe`, or `blocked_pack`;
- required adapters;
- active proof obligations;
- write boundary;
- stop condition;
- maximum of three cycles.

Do not execute every gate at maximum depth. Activate only proof obligations that can change readiness, safety, implementation selection, or handoff.

## Evidence and Decision Ledger

Load `references/evidence-decision-ledger-contract.yaml`. Maintain `decision_ledger` throughout the run.

Record:

- material claims with `verified`, `inferred`, or `unknown` grade;
- supporting and disconfirming evidence;
- implementation options and trade-offs;
- selected revision option IDs;
- bounded probes and discriminating results;
- unknowns with `resolved`, `probe`, `constraint`, `handoff`, or `block` disposition;
- every routed proof obligation and its status;
- final action, rollback or containment, authorization state, convergence, and stop reason.

The ledger exposes claims and decisions, not private chain-of-thought. Run `scripts/validate_decision_ledger.py` before building the final pack.

## Product and Adapter Gates

### Optimize Product Gate

Load `references/optimize-cli-product-contract.md`. Classify the bottleneck before editing:

- artificial delay or pacing;
- unnecessary serialization;
- undersized local worker, queue, batch, chunk, or connection cap;
- blocking I/O or sync/async mismatch;
- repeated initialization, startup, parsing, validation, or connection setup;
- duplicate work or missing safe reuse;
- avoidable buffering or non-streaming execution;
- repository-owned retry, polling, debounce, or backoff drag;
- lock contention or coarse synchronization;
- latent capability wiring;
- external limit or unknown ownership.

External or unknown ownership cannot become `PR_READY`. Diagnose and package a blocker instead of bypassing the limit.

### Latent-Capability Reachability Adapter

Load `references/latent-capability-activation.md` when dormant code, registries, feature flags, unused signals, or producer-consumer edges may explain the bottleneck.

Require:

- real CLI entrypoints;
- dynamic dispatch and registry resolution;
- bidirectional evidence: definition evidence and missing-consumer evidence;
- feature-flag and rollout intent;
- verdict `activate`;
- repository ownership;
- no material reachability unknown.

`dormant_by_design: true` or `UNKNOWN` reachability blocks activation.

### Documentation-Code Divergence Adapter

Load `references/docs-code-capability-divergence.md` when help text, README, examples, defaults, entrypoints, generated docs, release claims, and runtime behavior disagree.

Reconcile only when authority, intended behavior, and scope are proven. Otherwise record a `docs_code_divergence` finding in:

- `evidence/CLI_REVISION_SYNTHESIS.json`;
- `evidence/DOCS_CODE_DIVERGENCE_FINDINGS.md`;
- the PR body.

Release-blocking or unknown divergence prevents `PR_READY`. Non-blocking out-of-scope divergence must retain an owner and next action.

### Revision Synthesis and Leverage Adapter

After all findings are collected, load `references/revision-synthesis-leverage-adapter.md`.

1. Normalize each material finding as `CLI-FND-NNN`.
2. Map every finding to one or more `CLI-TGT-NNN` targets.
3. Generate viable `CLI-OPT-NNN` options.
4. Recalculate leverage using canonical weights.
5. Preserve rejected and deferred options.
6. Select only in-scope options scoring at least `3.5` with no material unknowns.
7. Freeze `selected_option_ids` before implementation.
8. Emit `evidence/CLI_REVISION_SYNTHESIS.json`.

Every finding must map to a target and every target to an option.

### Ecosystem Adapter

Load `references/ecosystem-adapters.md` to preserve repository-native Python, Node.js/TypeScript, Go, or Rust packaging, entrypoints, tests, build, install, and release conventions.

## Adaptive Convergence Workflow

Load `references/adaptive-convergence.md`.

For each cycle:

1. Reconcile the current worktree, prior ledger, and remote facts when available.
2. Re-run the router only if evidence, risk, ownership, capabilities, or authority changed.
3. Select the highest-value unresolved proof obligation.
4. Run one bounded implementation, probe, or validation action.
5. Update claims, options, unknowns, proof status, and stop reason.
6. Check regressions and readiness.
7. Stop immediately when all obligations are satisfied or a material blocker is proven.

Cycle three is terminal. Package `PR_READY` or `BLOCKED`. Never start cycle four.

## Scope Lock

Before editing, freeze:

- allowed files and additions;
- stable public interfaces and correctness invariants;
- baseline and target metrics;
- selected revision options;
- active proof obligations;
- resource ceilings and protective limits;
- entrypoints, registries, flags, and consumers when wiring is active;
- deployment, rollback, and validation surfaces;
- excluded work.

Do not broaden the allowlist without a concrete blocker and an updated ledger. Preserve unrelated working-tree changes.

## PR-Ready Gates

`PR_READY` requires all applicable gates:

1. Route matches ownership, evidence state, risk, adapters, and write boundary.
2. Every routed proof obligation is `satisfied` with evidence.
3. Decision ledger converged with no material unknowns.
4. Every finding maps to a target and every target has options.
5. Selected options pass scope, leverage, and unknown gates.
6. Documentation-code conflicts are reconciled or non-blockingly disclosed.
7. Bottleneck is repository-owned.
8. Comparable baseline and candidate evidence show positive improvement.
9. Correctness, ordering, cancellation, signals, durability, and exit codes remain valid.
10. CPU, memory, queues, workers, processes, descriptors, and connections remain bounded.
11. Compatibility is preserved or migration is explicit.
12. Native quality, tests, package build, install, and CLI execution pass.
13. Deployment, abort thresholds, rollback, and handoff are executable.
14. Patch, copied files, manifest, commit message, PR body, route, ledger, and synthesis agree.

Never weaken checks, alter CI, lower thresholds, remove safety limits, or cherry-pick flattering measurements to manufacture readiness.

## Commit Pack Contract

Load `references/pr-commit-pack-contract.md`. The final pack must contain:

```text
<pack-name>/
  MANIFEST.json
  README.md
  change/
    files/<repository-relative changed files>
    commit.patch
    OPTIMIZATION_PLAN.json
  pr/
    COMMIT_MESSAGE.txt
    PR_BODY.md
    PR_CHECKLIST.md
  evidence/
    EXECUTION_ROUTE.json
    DECISION_LEDGER.json
    DECISION_RECORD.md
    CLI_REVISION_SYNTHESIS.json
    CLI_REVISION_PLAN.md
    DOCS_CODE_DIVERGENCE_FINDINGS.md
    VALIDATION.md
    PERFORMANCE.md
    WIRING_MAP.md                    # when latent-capability adapter is active
    LATENT_CAPABILITY_FINDINGS.json # when latent-capability adapter is active
    commands.jsonl
    checksums.sha256
  deploy/
    DEPLOY_PLAYBOOK.md
    ROLLBACK_PLAYBOOK.md
    RELEASE_CHECKLIST.md
  handoff/
    AGENT_HANDOFF.md
    NEXT_AGENT_TASK.json
  issues/                            # only when blocked
    ISSUE-<fingerprint>.md
```

Use `scripts/build_commit_pack.py` for deterministic generation and `scripts/validate_commit_pack.py` before delivery.

## Deployment and Handoff

Load `references/deploy-playbook-contract.md` and `references/agent-handoff-contract.md`.

The deploy playbook must use real repository commands and include prerequisites, staged rollout, success thresholds, abort thresholds, monitoring, rollback triggers, and exact rollback actions. Never invent credentials, hosts, registries, quotas, or release IDs.

The handoff must preserve completed work, repository identity, route, ledger, selected options, performance delta, validation evidence, deployment state, blockers, unknowns, prohibited moves, and the next executable action.

## Failure Handling

Fail closed when:

- the repository or source is unavailable;
- the bottleneck cannot be reproduced or supported by equivalent trace evidence;
- ownership is external or materially unknown;
- a safe resource envelope cannot be established;
- unrelated changes cannot be separated;
- required validation cannot be executed or bounded honestly;
- deployment requires invented environment facts;
- the patch is empty, unsafe, or unrelated;
- cycle three ends with a material blocker.

For each independent blocker, create one issue artifact with evidence, impact, reproduction, attempted work, acceptance criteria, owner, and exact next action. Preserve completed code and evidence in the blocked pack.

## After-Use Improvement

Capture an observation only when the user reports a bad run or requests iteration:

```yaml
missed_trigger: null
false_trigger: null
recurring_correction: null
manual_rework: null
proposed_behavior_change: null
```

Update the smallest behavior-changing rule, route condition, proof obligation, or validator. Do not invent telemetry.

## Validation

`scripts/self_test.py` is the single aggregate gate: it runs every standalone
validator below, then builds and validates a pack from the shipped example
against an inline fixture repository. Run it before delivery:

```bash
python3 scripts/self_test.py
```

It invokes exactly these, so run any individually while iterating:

```bash
python3 scripts/validate_identity_lock.py
python3 scripts/validate_activation_model.py
python3 scripts/validate_latent_capability_integration.py
python3 scripts/validate_revision_synthesis.py
python3 scripts/validate_decision_ledger.py     # accepts the combined spec, a pack dir, or DECISION_LEDGER.json
python3 scripts/validate_adaptive_reasoning.py
python3 scripts/validate_exemplary_skill.py .
python3 scripts/build_commit_pack.py --spec <spec> --repo-root <repo> --output <dir>
python3 scripts/validate_commit_pack.py <pack-dir>
python3 scripts/scan_capabilities.py <repo>          # advisory diagnosis scan
python3 scripts/measure.py --before <cmd> --after <cmd>  # before/after proof
```

`self_test.py` asserts this list stays in parity with what it actually runs, so the
two can never drift (defect fix). JSON Schemas are enforced for real:
`build_commit_pack.py` validates the spec against `schemas/pack-spec.schema.json` and
the emitted manifest against `schemas/pack-manifest.schema.json` via `jsonschema` (a
required dependency). Structural success does not prove utilization improved; the
generated pack must carry comparable before/after evidence — a throughput
measurement, or a capability-activation functional proof.

## Exemplary Build Evidence

This evolution uses `extract_expertise -> compress_expertise -> adaptive_route -> evidence_ledger -> exemplary_gate -> package`.

See `expertise_model.yaml` and `skill_intelligence_report.yaml`. Do not claim exemplary tier unless deterministic gates pass.

## Resource Map

- `references/adaptive-optimize-router.yaml`: proportional route and proof-obligation law.
- `references/evidence-decision-ledger-contract.yaml`: auditable claim, option, unknown, probe, decision, and convergence contract.
- `references/adaptive-convergence.md`: proof-obligation-driven three-cycle loop.
- `references/optimize-cli-product-contract.md`: utilization-gap taxonomy and safety boundary.
- `references/latent-capability-activation.md`: reachability and activation law.
- `references/docs-code-capability-divergence.md`: divergence evidence and disclosure law.
- `references/revision-synthesis-leverage-adapter.md`: finding-target-option synthesis and leverage selection.
- `references/pr-commit-pack-contract.md`: portable pack structure.
- `references/deploy-playbook-contract.md`: staged deployment and rollback.
- `references/agent-handoff-contract.md`: successor-agent state transfer.
- `references/ecosystem-adapters.md`: native language and packaging adapters.
- `scripts/scan_capabilities.py`: advisory repository scan for candidate utilization gaps and entrypoints.
- `scripts/measure.py`: comparable before/after measurement producing a proof block.
- `scripts/route_optimize.py`: deterministic adaptive router.
- `scripts/validate_decision_ledger.py`: route and ledger validator.
- `scripts/build_commit_pack.py`: deterministic pack builder.
- `scripts/validate_commit_pack.py`: generated-pack validator.
- `scripts/self_test.py`: end-to-end, deterministic, and negative tests.
