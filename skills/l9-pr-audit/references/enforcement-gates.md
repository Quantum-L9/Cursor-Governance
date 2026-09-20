<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: reference
role: enforcement-gates
version: 2.0.0
status: active
-->

# Enforcement Gates

## Contents

- G1-G6: target, authority, PR evidence, census, evidence, findings
- G7-G16: remediation surfaces, mutation, architecture, preservation, readiness, output/package integrity
- G17-G24: objective/scope/change discipline and remediation convergence
- G25-G30: inspection, recursive convergence, boundary alignment, provenance, control adequacy, hygiene
- G31-G35: changed symbols, claims, falsification, LLM judgment, deterministic closure

## G1 Target and coverage lock

Pass only when repository identity, frozen PR set, inspection scope, exclusions/inaccessible surfaces, applicable audit domains, exact default-branch/source-head revisions, and exact changed-file inventory are explicit. `COMPLETE` cannot hide Unknown domains or convergence-blocking exclusions.

## G2 Authority and intent resolution

Pass only when material governing sources have authority IDs, scope, precedence, and evidence, and `intent_contract` identifies active objectives plus original PR-prompt availability. Pointer/index artifacts must be followed to canonical owners when resolvable. Historical task intent never overrides current repository authority.

## G3 PR evidence bindings

Pass only when required-check resolution, review-thread discovered/classified/remaining counts, changed-file inventory, and mandatory validation evidence are explicit. `RESOLVED`, `NONE`, and `COMPLETE` require confirmed claim-specific evidence. Source head is never silently substituted for tested revision.

## G4 Deterministic audit census

Pass only when every audited PR has an exact bound `build_change_ledger.py` census, its head/schema/generator/hash agree with `deterministic_census_binding`, and every changed surface, machine changed symbol, CI failure, review thread, claim seed, falsification seed, and deterministic obligation is accounted for before semantic grading. The model may add semantic rows but may not omit or rewrite machine-owned rows.

## G5 Evidence closure

Pass only when every retained finding has direct canonical evidence, exact locator, epistemic state, and claim/evidence fit. TEST/CI/RUNTIME/MEASUREMENT pass/fail claims require exact tested revision and properties discriminated.

## G6 Finding and authority closure

Pass only when each finding references a known authority ID, exact current PR heads, owner axes, root-cause state, behavioral closure condition, and closing validation. Confirmed claims require confirmed evidence.

## G7 Remediation surface proof

Pass only when every finding has exactly one surface record and every implementation path has confirmed `IMPLEMENTATION` surface evidence that discriminates `implementation_surface`. Unsafe or host-specific write paths fail closed.

## G8 Mutation eligibility

Pass only when generated mutation authority is restricted to Confirmed CODEBASE findings with CONFIRMED root cause, resolved mutation guard, resolvable dependency order, and claim-specifically confirmed implementation paths. All other work has empty `write_surfaces`.

## G9 Architecture and reachability

Pass only when touched ownership/boundary/source-of-truth relationships are resolved. File existence does not prove discovery, registration, routing, enforcement, or execution.

## G10 Negative closure

Pass only when each PR covers every anti-bypass class exactly once with evidence that discriminates that class, and no material test/gate weakening, skip/ignore growth, suppression/exclusion growth, generator/owner bypass, or unexplained dependency movement is hidden behind green status.

## G11 Preservation closure

Pass only when affected public APIs, data contracts, externally consumed behavior, and release surfaces have evidence-backed preservation/migration status.

## G12 Dependency and constellation closure

`depends_on_findings` is the sole dependency SSOT. Cycles/order-blocked findings receive no mutation authority. Multi-PR combined readiness requires complete cross-PR relationships and exact merge order.

## G13 Readiness consistency

Pass only when per-PR blocking finding IDs and blocking Unknown IDs exactly match canonical records. READY requires open non-draft state, MERGEABLE state, sufficient claim-specific mandatory validation, PASS evidence for every resolved required check, complete review coverage with zero unresolved remaining threads, no blocking finding/Unknown, no unresolved preservation/bypass condition, complete change discipline, and complete required cross-PR evidence.

## G14 Audit convergence

Pass only when audit coverage is complete, authority is resolved, dependency order is reconciled, applicable domains are disposed, change-discipline Unknowns are eliminated or represented/resolved, the obligation ledger is fully dispositioned, every material claim has validation/falsification closure, and cross-PR evidence is complete when relevant. Audit convergence is separate from code readiness.

## G15 Canonical output contracts

Pass only when `audit.json` validates against `schemas/audit-output.schema.json` plus cross-field semantic gates, and derived `remediation-handoff.json` validates against `schemas/remediation-handoff.schema.json`. Derived Markdown/contract text never becomes authority.

## G16 Package integrity

Pass only when `MANIFEST.json` validates against its schema, binds builder version plus builder-byte/schema digests and `change_ledger_set_sha256`, records `autoremediate`, every packaged file hash matches, the exact file set includes `change-ledger.json`, deterministic projections re-derive byte-identically, bound census rows still match canonical audit machine rows, secret-safe scanning passes, and the outer ZIP filename carries non-colliding save tags.

## G17 Objective closure

Pass audit coverage only when every active objective has exactly one closure record. READY requires every active objective `SATISFIED`. `UNPROVEN`, `NOT_IMPLEMENTED`, or `CONFLICTED` must remain visible as findings/Unknowns as appropriate.

## G18 Scope fidelity

Pass only when `change_discipline.scope_fidelity.changed_surfaces` matches each PR's exact changed-file inventory one-for-one. Every surface receives `REQUIRED`, `DIRECTLY_COUPLED`, `VALIDATION_REQUIRED`, `GENERATED_CONSEQUENCE`, `SCOPE_EXTENSION`, or `UNKNOWN`. `SCOPE_EXTENSION` requires a finding.

## G19 Complexity delta

Pass only when per-PR file-add/delete/modify counts reconcile to exact changed-file inventory and structural growth is recorded where observable. Complexity delta is evidence, not an automatic defect score.

## G20 Architectural economy

Pass only when every detected architecture-growth candidate is dispositioned. `JUSTIFIED` requires active-objective linkage plus evidence the existing owner/capability was considered. `UNJUSTIFIED` requires a finding. Do not equate new abstraction with failure.

## G21 Supersession closure

Pass only when material replacements of paths/owners/entrypoints/config/dependencies/subsystems are dispositioned. `RESIDUAL` duplicate live authority/path requires a finding. `UNKNOWN` blocks audit convergence.

## G22 Failure-path and test discrimination

Pass only when material changed failure behavior is `TESTED`, `STRUCTURALLY_PROVEN`, or explicitly `NOT_APPLICABLE`, and materially changed production behavior has a discriminating validation disposition. `WEAK` or `ABSENT` test discrimination requires a finding; Unknowns block audit convergence.

## G23 Audit obligation ledger

Pass only when the ledger covers every active objective, every changed surface, every machine changed symbol, every architecture-growth candidate, every material supersession/failure/test obligation, every in-scope CI failure, and every unresolved review thread discovered. Every obligation ends `PASS`, `FINDING`, `NOT_APPLICABLE`, or `UNKNOWN` with canonical evidence. A converged audit may contain known findings, but never silently missing obligations.

## G24 Remediation convergence contract

Pass only when the generated PR Remediation Contract makes audit-finding closure the primary mission and additionally requires current CI convergence plus all-current-code-review-thread convergence on affected PRs. It must set `MERGE=False`, publish only through the canonical SSOT Makefile `make pr` path, and forbid target-repository Makefile fallback, raw `gh pr` substitution, replacement PRs, gate weakening, scope expansion, and merge.

## G25 Inspection inventory closure

Pass only when every changed file appears exactly once as `CHANGED` at its exact PR-head revision and every authoritative, implementation, and coupled remediation surface used by a material conclusion appears in `audit_coverage.artifact_inventory`. `COMPLETE` may not retain unknown artifact revisions.

## G26 Recursive verification convergence

Pass only when `audit_passes` starts with `DISCOVERY`, ends with `VERIFICATION`, and the final verification pass re-observes every retained finding, every audit obligation, every material claim, and every falsification probe. `CONVERGED` additionally requires final `new_information_count == 0`, no next-pass objective, no material `UNKNOWN` claim, and no unresolved applicable `INCONCLUSIVE` probe.

## G27 Domain, adapter, and boundary alignment

Pass only when every canonical audit domain has exactly one canonical assessment; architecture-policy adapter applicability is resolved or explicitly `NOT_APPLICABLE`; the boundary map is complete for whole-scope coverage; each finding semantic owner resolves to the boundary map; and no project-specific adapter was imported without verified authority and scope.

## G28 Finding provenance and blocking policy

Pass only when every finding records evidence-backed PR/baseline provenance and every `merge_blocking=true` finding has authority-backed, confirmed evidence that discriminates `merge_blocking_basis`. Non-Unknown origin requires `finding_origin` evidence. Pre-existing debt additionally requires `pre_existing_blocking_relevance` evidence to block merge and never receives default mutation authority.

## G29 Underbuilt-control closure

Pass only when every material required control audited in `change_discipline.control_adequacy` is dispositioned. Every mapped security, policy-enforcement, validation, and source-of-truth boundary is covered by a control-adequacy record. `UNDERBUILT` requires a finding and obligation; `UNKNOWN` blocks convergence.

## G30 Adversarial regression and package hygiene

Before packaging the skill itself, `scripts/self_test.py` must prove at minimum: unknown-field rejection, changed-file/scope exact coverage, machine changed-symbol binding, machine claim/falsification seed preservation, inspection-inventory closure, recursive-verification saturation across findings/obligations/claims/probes, objective coverage, obligation-ledger coverage, material-claim falsification enforcement, LLM-judgment boundary enforcement, evidence-backed readiness inputs, surface-evidence enforcement, unconfirmed finding mutation denial, dependency-cycle mutation denial, strict scope-extension behavior, CI/review/MERGE=False remediation contract projection, secret rejection, bound change-ledger manifest integrity, unique ZIP naming, and a positive end-to-end bundle build. The packaging workflow must remove stale bytecode first, run validation with bytecode writes disabled, verify that validation created no `__pycache__`/`.pyc`, and reject any final skill archive containing such residue.


## G31 Changed-symbol closure

Pass only when every machine changed symbol from the bound ledger appears exactly in `changed_symbol_ledger`, retains machine-owned identity/detection fields, links a `CHANGED_SYMBOL` obligation, and links at least one `CHANGED_SYMBOL` claim. Semantic auditor-added symbols may extend the ledger but may not replace machine rows.

## G32 Claim-validation closure

Pass only when all machine claim seeds exist unchanged, material claim evidence discriminates `claim:<claim_id>` or declared validation properties, and claim status reconciles with canonical objective/domain/symbol/readiness/convergence state. A material `SUPPORTED` claim requires all declared validation properties proven and no unresolved attack.

## G33 Adversarial falsification closure

Pass only when all machine falsification seeds exist unchanged and every material claim has applicable attacks. `SUPPORTED` requires every applicable probe `SURVIVED`; any `FALSIFIED` probe refutes the claim; any applicable `INCONCLUSIVE` prevents positive closure. `SURVIVED`/`FALSIFIED` require confirmed evidence that discriminates `falsification:<claim_id>`.

## G34 LLM judgment boundary

Pass only when `LLM_JUDGMENT` or `HYBRID` is used for a falsification probe whose deterministic static/command/check evidence is insufficient, `judgment_required=true`, and `judgment_rationale` plus evidence explain the unresolved semantics. Deterministic probes may not be relabeled as LLM judgment to bypass missing machine evidence.

## G35 Deterministic closure completion

Pass only when every machine closure seed from `change-ledger.v1.4` is preserved in `deterministic_closure_ledger`, every v2.0 closure kind is semantically dispositioned under `references/deterministic-closure.md`, post-judgment root-cause/severity/validation coverage is exact, repository-wide conclusions are withheld without complete-corpus evidence, and final recursive verification re-observes every closure ID.

### v2.0 deterministic-closure gate

Fail closure when a changed public contract lacks complete producer/consumer disposition, an applicable mutation candidate is unexecuted/survives while test discrimination is claimed strong, any current review thread lacks semantic disposition, or any newly added non-test artifact lacks proven reachability/registration/authorized future contract. Repository-wide producer/consumer and reachability absence claims require a complete repository corpus. Mutation probes must execute only in isolated temporary copies and prove the original audited source hash is unchanged.
