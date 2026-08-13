---
name: l9-cli-optimization
description: Identify underutilized, verified repository-owned capabilities and enable their full utilization — activating dormant or miswired code, off-by-default features, unread config, and unused signals — then package the exact change as a deployable PR commit bundle (changed files, binary-safe patch, revision synthesis, adaptive route, evidence and decision ledger, before-and-after performance evidence, deploy and rollback playbooks, successor-agent handoff). Removing a verified CLI throughput bottleneck is one branch of the same mission. Use when a repository or CLI audit, benchmark, dead-wiring finding, capability brief, patch, or prior sandbox artifact must become production code that safely raises utilization of latent capability the repository already owns. Do not use for audit-only output, non-repository targets, manufacturing capability that does not already exist, new throttling systems, or bypassing provider quotas, billing limits, licensing, authorization, abuse controls, or external service limits.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  future_home: https://github.com/Quantum-L9/l9-tools
  status: active
---

# Optimize CLI PR Pack

## Future home

Marked for relocation to [`Quantum-L9/l9-tools`](https://github.com/Quantum-L9/l9-tools). **Do not move yet.** Remains an explicit-only L9 skill in Cursor-Governance until extracted.

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
- `FULL_THROTTLE`: enable off-by-default feature flags at scale and prove them with the repo's own tests — a separate, bounded mode with its own gate. See **Full-Throttle Activation Mode** below.

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

When the target is a real repository and no prior finding exists, run `scripts/scan_capabilities.py <repo>` for a COMPREHENSIVE sweep, not just a symbol scan. It classifies candidates into:

- `inactive_component` — a top-level def/class or JS export referenced nowhere.
- `broken_partial_wiring` — an **unwired executable**: a `__main__` module or shell script that no wiring surface (Makefile, CI, pre-commit, hook, `package.json`, or any non-doc file) invokes. This is the dead-end-wiring case. Each carries `suggested_wiring` (a ready-to-paste Makefile target) and a `doc_only` flag (declared-active-in-docs but unwired). Read the top-level `unwired_executables` list.
- `dangling_reference` — a **broken/phantom/archived import**: `import X` or `python -m X` whose root is not stdlib, not a declared dependency, and not resolvable in-repo (phantom), or resolves ONLY under `_archived/` (archived-module reference). Read the top-level `dangling_references` list.
- `miswired_file` — a `.py` that fails to parse (cracked; cannot import/run). Read `syntax_errors`.
- `dormant_capability` — a named off-by-default feature flag.

Candidates are advisory only — verify each against the latent-capability reachability law (bidirectional evidence, dynamic dispatch, registries, `dormant_by_design`) before authoring a finding. Anything under `_archived/`/scratch is excluded from reactivation; `intent=staged_rollout` / `recommended_verdict=do_not_activate` is dormant_by_design (Identity-Lock #1 — do NOT activate). `candidate_counts_by_class` summarizes the sweep.

The scanner deliberately does NOT cover two gap classes — run these **manual diffs** to be exhaustive:

1. **Registry / inventory drift.** Diff every on-disk plugin/skill/command/DAG inventory against the manifest or registry that is supposed to list it (e.g. `skills/*/SKILL.md` folders vs the entries in a skills manifest; slash commands documented in a rule vs the backing files/skills that exist). An entry present on disk but absent from its registry is a dormant capability the tool never surfaces; an entry in the registry with nothing on disk is a dangling reference.
2. **Config/doc path references to deleted files.** Grep manifest/config/rule/doc files for repository-relative paths and flag those that no longer exist or now live only under `_archived/`.

**When a finding is an unwired executable (`broken_partial_wiring`) or dead-end wiring, the reactivation edge is a wiring change — a Makefile/CI/hook/`package.json` target — and the pack's `change/files` MUST include that Makefile/CLI diff.** Use the candidate's `suggested_wiring` as the starting target. If the executable mutates files, wire it read-only or opt-in (a `-check`/`--no-repair` target), never as an unattended auto-fix; expose a separate deliberate target for the mutating mode.

Absence of any reachable entrypoint is a `blocked_pack` signal for the router (`target_reachable`). Use `scripts/measure.py --before <cmd> --after <cmd>` to produce the comparable before/after proof block: median wall-clock by default, or a functional utilization metric with `--capture` (e.g. consumer invocations `0 -> N`). When the `before` state is the unpatched code, pass `--repo <path> --before-ref <base-ref>` so `measure.py` runs the `before` command in a throwaway git worktree at that ref and cleans it up — the sanctioned way to produce the unpatched baseline without hand-building a worktree.

## Full-Throttle Activation Mode

A separate, self-contained mode for testing a repository "full throttle": enable
its off-by-default feature flags, prove them against the repository's own tests,
and package the flip as a review-required PR. Load
`references/full-throttle-activation.md` before running it.

This mode consciously relaxes **Identity-Lock #1's `dormant_by_design` clause for
testing only**. The core scan → PR-pack pipeline and its `dormant_by_design`
refusal (`build_commit_pack.py` still exits 2 on `dormant_by_design:true`) are
**untouched**. The relaxation is paid for with hard compensating controls that
keep #2 (safety) and #3 (no quota/backpressure bypass) intact:

- **Polarity-aware danger block-list.** A flag is NEVER flipped when turning it on
  either *enables a dangerous action* (delete/purge/deploy/publish/charge/billing/
  live/prod/send/external/migrate) or *disables a safety control* (auth/tls/ssl/
  verify/validation/sandbox/permission via `disable_*`/`skip_*`/`bypass_*`). Both
  polarities of danger are held — `enable_delete=False→True` and
  `disable_auth=False→True` are each danger. `.optimize-scan.json` `full_throttle.{never_flip,always_flip,danger_tokens}` extends the list.
- **Staged / `dormant_by_design` flags are held.** A flag marked staged rollout
  (`wave N`, `dormant_by_design`, system-state intent) is classified `staged` and
  never flipped, honoring Identity-Lock #1.
- **Consumer reachability (`consumer_evidence`, `needs_wiring`).** A flag is only a
  real flip candidate if code actually *reads* it. `flag_inventory` builds a
  repo-wide reader corpus (Load-context Names, attribute accesses, string keys —
  declarations and assignment targets excluded) and marks each flag `found` /
  `none` / `unknown`. A safe flag with `consumer_evidence=none` is **declared but
  unconsumed** — flipping is a no-op — so it is held with `needs_wiring: true`
  ("needs a wiring change, not a flip"). This is the flag-level form of the
  never-fake-an-activation law (the CEG `temporal_decay_enabled` case). `unknown`
  is a generic config leaf (`enabled` under a block) the static check cannot
  disambiguate; decision unchanged, verify the parent/registry manually.
- **Non-runtime / infra held (`scope`).** Config under `docs/`, `infra/`, `deploy/`,
  `helm/`, `monitoring/` (and `values*.yaml` / `Chart.yaml`) is `scope=non_runtime`;
  a generic `enabled` under a k8s/Helm deploy block (`ingress`/`autoscaling`/`pdb`/…)
  is `scope=infra`. Both are surfaced but never flipped — docs/deploy toggles, not
  application capability.
- **Empirical back-out.** Every non-danger flip is validated by execution in a
  throwaway `git worktree` at HEAD: run the baseline (flags off), flip all
  candidates, run the repo's own tests, and back out — by bounded bisection — any
  flag whose activation regresses tests, reclassifying it `empirically_unsafe`.
  "All except a danger block-list" is thus proven by tests, never assumed.
- **Isolation + human gate.** All flip+test happens in the worktree; the real
  working tree is never mutated. The pack is labeled **REVIEW REQUIRED — do not
  auto-merge**; a full-throttle pack is **never auto-merged** by the skill. Deploy/
  publish test commands are themselves danger-classified and refused.
- **Honesty.** The pack's `FULL_THROTTLE_REPORT.md` carries the real captured
  flags-off → flags-on test delta; no activation is ever claimed without it.

Scripts (each stdlib-only, read-only except the pack output):

```bash
python3 scripts/flag_inventory.py <repo>                 # inventory + polarity-aware danger classification
python3 scripts/full_throttle.py <repo> --mode plan      # plan: inventory + would-flip set, nothing mutated
python3 scripts/full_throttle.py <repo> --mode apply --test-cmd "<cmd>"   # worktree flip + test + back-out
python3 scripts/full_throttle.py <repoA> <repoB> --mode plan              # multi-repo matrix
python3 scripts/build_flag_activation_pack.py --report <ft.json> --repo-root <repo> --output <dir>
```

`MODE=plan` is the default and mutates nothing; run it first and review the danger
exclusions before `MODE=apply`. A run where every candidate is danger-excluded or
regresses tests flips nothing and emits a BLOCKED pack — that is a valid outcome,
not a failure to force.

## Adaptive Execution Router

Load `references/adaptive-optimize-router.yaml` before planning or mutation. Use `scripts/route_optimize.py` when deterministic routing is useful.

Classify independently. This block is the router **input**, not the persisted route:

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

The persisted `evidence/EXECUTION_ROUTE.json` is the router **output**, whose shape is fixed by `schemas/pack-spec.schema.json#/$defs/execution_route`. Emit it with `scripts/route_optimize.py` (its output validates as-is) rather than hand-copying this input block. The route carries `docs_code_divergence`, `latent_capability`, and `output_mode` as recorded classification, but `execution_route` sets `additionalProperties: false` — never add other classifier-only keys to it.

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
8. Comparable baseline and candidate evidence, on the accept path bound to `execution_route.utilization_gap_class`:
   - **8a — throughput class** (delay, serialization, low cap, blocking I/O, repeated startup, duplicate work, buffering, retry/backoff drag, lock contention): a comparable positive wall-clock delta.
   - **8b — latent-capability / functional class** (inactive component, miswired file, dormant capability, unused signal, orphaned config, broken partial wiring, latent-capability wiring): a comparable positive functional delta — consumer invocations, reads eliminated, or a signal now consumed (a `0 -> N` activation) — carrying an explicit "no throughput claim" note. A pure activation is never failed for lacking a wall-clock number; `improvement_percent` may be `null` when the metric is `higher_is_better` from a zero baseline.
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

Use `scripts/build_commit_pack.py` for deterministic generation and `scripts/validate_commit_pack.py` before delivery. Two validator gates catch authors out: the commit-message first line must be **≤ 72 characters**, and `deploy/DEPLOY_PLAYBOOK.md` must express **verify**, **abort**, and **rollback** intent (each satisfied by a synonym — e.g. validate/confirm, halt/stop, revert/restore).

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

### Recorded observations (2026-07-30 activation run)

```yaml
- recurring_correction: hand-authored EXECUTION_ROUTE.json carried classifier-only fields (docs_code_divergence, latent_capability, output_mode); additionalProperties:false rejected the build.
  proposed_behavior_change: relabel the classify block as router input; route_optimize now persists those three fields and the schema admits them as optional route properties.
- manual_rework: built a second git worktree by hand to produce the unpatched 0->N baseline; measure.py had no git-state helper.
  proposed_behavior_change: measure.py gained --repo/--before-ref worktree scaffolding, documented in the Diagnosis section.
- recurring_correction: build failed on the undocumented 72-char commit-subject limit and the required literal deploy word "verify".
  proposed_behavior_change: both gates documented in the commit-pack and deploy-playbook contracts and in SKILL.md.
- false_trigger: scan_capabilities flagged Alembic upgrade/downgrade, a setuptools entry_points target, and same-name twins as inactive_component.
  proposed_behavior_change: added framework-aware reference sources, migration/pytest skips, candidate ranking, and twin visibility.
```

### Recorded observations (second run — Cognitive.Engine.Graphs)

```yaml
- manual_rework: Gate #8 read as "positive improvement" and gave no rule for whether a functional-only (flat wall-clock) activation passes.
  proposed_behavior_change: split Gate #8 into 8a throughput (wall-clock delta) and 8b latent/functional (functional delta, no-throughput note), bound to execution_route.utilization_gap_class.
- false_trigger: scan_capabilities surfaced intentional staged-rollout flags (kge/gds/compliance) as dormant_capability opportunities — the Identity-Lock #1 trap.
  proposed_behavior_change: added an intent pass (system-state / dormant_by_design / "wave N" markers) that emits intent=staged_rollout + recommended_verdict=do_not_activate.
- recurring_correction: undiscoverable spec enums (optimization.strategy, findings[].kind, divergence_type) forced sequential build failures.
  proposed_behavior_change: shipped assets/pack-spec.minimal.json, an enum quick-reference in the commit-pack contract, and collect-and-report of ALL schema violations per build.
- recurring_correction: leverage_score / decision were re-derived by hand though they are pure functions of the seven dimensions.
  proposed_behavior_change: documented both as DERIVED in the leverage adapter (validator already prints the expected value).
- manual_rework: mapped one bottleneck across the fine utilization_gap_class enum and the coarse findings[].kind enum with no guide.
  proposed_behavior_change: added a utilization_gap_class -> findings[].kind mapping table to the leverage adapter.
- manual_rework: the canonical example's wiring block, copied into a throughput change, failed on additionalProperties.
  proposed_behavior_change: shipped a non-latent minimal example without wiring and documented that wiring is latent-capability only.
- recurring_correction: a semantically-complete deploy playbook was rewritten only to inject the literal words verify/rollback.
  proposed_behavior_change: the deploy gate now accepts synonyms (validate/confirm/smoke, revert/restore, halt/stop).
```

### Recorded observations (third run — Cursor-Governance, comprehensive sweep)

```yaml
- missed_trigger: scan_capabilities only found unreferenced symbols and off-by-default flags; the real dormancy (an unwired validation harness, phantom `l9_ops_mcp`/`tools.validation` imports, an archived-module import, and skills present on disk but missing from the registry) was found only by a hand audit.
  proposed_behavior_change: added detectors for broken_partial_wiring (unwired executables, with suggested_wiring Makefile targets), dangling_reference (phantom / undeclared / archived-only imports and `python -m` targets), and miswired_file (syntax-broken); added candidate_counts_by_class and the unwired_executables/dangling_references/syntax_errors lists.
- false_trigger: sibling modules imported via a runtime sys.path.insert (e.g. ops/graphiti/*.py, generate_rules_manifest) first scanned as phantom.
  proposed_behavior_change: module resolution treats any non-archived in-repo match as local; added ALWAYS_AVAILABLE (pip/setuptools/...) and IMPORT_ALIAS (yaml->pyyaml, ...) allowlists; excluded scratch dirs (wip/scratch/...) from candidates and deduped the finding lists.
- recurring_correction: the reactivation edge for an unwired script is a Makefile/CI target, but that wiring was not treated as part of the pack change.
  proposed_behavior_change: Diagnosis now requires the Makefile/CLI diff in change/files for broken_partial_wiring findings, and warns to wire mutating tools read-only/opt-in (never as an unattended auto-fix).
- missed_trigger: registry/inventory drift (skill folder on disk absent from its manifest) and config/doc references to deleted files are real dormancy classes the static scan cannot see.
  proposed_behavior_change: documented both as mandatory MANUAL diffs in the Diagnosis section.
```

### Recorded observations (fourth run — full-throttle activation)

```yaml
- missed_trigger: the skill diagnosed off-by-default flags but had no path to ENABLE them at scale and prove them — "test all repos full throttle" had no mode.
  proposed_behavior_change: added a separate, self-contained Full-Throttle Activation Mode (flag_inventory / full_throttle / build_flag_activation_pack) that flips non-danger flags, proves them in an isolated worktree, and packages a review-required PR; the core scan/PR-pack pipeline and its dormant_by_design refusal are untouched.
- recurring_correction: "enable everything" is unsafe by default — a flat flip would turn on delete/deploy/auth-disable flags.
  proposed_behavior_change: polarity-aware danger classifier (enabling a dangerous action OR disabling a safety control are both held), staged/dormant_by_design flags held, and empirical back-out reverts any flag that regresses the repo's own tests; the PR is never auto-merged.
```

### Recorded observations (fifth run — CEG wiring PR + EIE handoff)

```yaml
- missed_trigger: flag_inventory flagged CEG causal.temporal_decay_enabled as safe->flip, but the flag had NO consumer — flipping was a no-op; it needed a wiring change (shipped as CEG PR #155). The scanner detected the default, never whether anything reads the flag.
  proposed_behavior_change: added a context-aware repo-wide reader corpus (Load-only Names, attribute accesses, string keys — declarations/assignment targets excluded) and a consumer_evidence signal; a safe flag with consumer_evidence=none is held with needs_wiring=true ("needs a wiring change, not a flip"). Generic config leaves resolve to consumer_evidence=unknown (decision unchanged; verify parent/registry manually).
- false_trigger: on EIE, flag_inventory surfaced docs/contracts/dependencies/*.yaml and infra/k8s/helm values*.yaml `enabled` keys as flip candidates — documentation/contract specs and Helm deploy manifests, not application runtime config.
  proposed_behavior_change: added _NONRUNTIME_PATH (docs/, infra/, deploy/, helm/, monitoring/, values*.yaml, Chart.yaml) -> scope=non_runtime hold, and INFRA_BLOCKS (ingress/autoscaling/pdb/...) -> scope=infra hold. Both surfaced but never flipped.
```

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
python3 scripts/flag_inventory.py <repo>             # full-throttle: off-by-default flag inventory + danger classification
python3 scripts/full_throttle.py <repo> --mode plan  # full-throttle: plan (apply proves + backs out breakers in a worktree)
python3 scripts/build_flag_activation_pack.py --report <ft.json> --repo-root <repo> --output <dir>  # review-required flag-activation pack
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
- `scripts/scan_capabilities.py`: comprehensive advisory scan — inactive components, unwired executables (with suggested Makefile wiring), broken/phantom/archived imports, syntax-broken files, off-by-default flags, entrypoints.
- `scripts/measure.py`: comparable before/after measurement producing a proof block.
- `references/full-throttle-activation.md`: full-throttle activation mode sub-contract (danger classifier, empirical back-out, pack shape, invariants).
- `assets/full-throttle.example.json`: example `full_throttle.py --mode apply` report consumed by the flag-activation pack builder.
- `scripts/flag_inventory.py`: off-by-default flag inventory + polarity-aware danger classifier + consumer-reachability signal (`consumer_evidence`/`needs_wiring` via a repo-wide reader corpus) + non-runtime/infra `scope` holds + single-line flip transform.
- `scripts/full_throttle.py`: worktree-isolated flip → test → empirical back-out harness; multi-repo driver.
- `scripts/build_flag_activation_pack.py`: standalone deterministic review-required flag-activation pack builder (core pipeline untouched).
- `scripts/route_optimize.py`: deterministic adaptive router.
- `scripts/validate_decision_ledger.py`: route and ledger validator.
- `scripts/build_commit_pack.py`: deterministic pack builder.
- `scripts/validate_commit_pack.py`: generated-pack validator.
- `scripts/self_test.py`: end-to-end, deterministic, and negative tests.
