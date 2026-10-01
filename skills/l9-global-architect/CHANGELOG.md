# Changelog

This file is historical and non-authoritative. Machine-readable semantic owners declared by `runtime/MANIFEST.yaml` govern runtime behavior.

## 0.8.2 - 2026-09-27

### Validate & Repair hardening

- Applied `validate_repair_complete_align_and_harden` v1.0 against the complete v0.8.1 skill pack in full-readiness mode with modification explicitly authorized.
- Corrected release-version coupling in `validate_runtime_alignment.py`: the pack release version is now bound to `SKILL.md` and `runtime/MANIFEST.yaml`, while independently owned semantic artifacts keep their own versions unless their semantics change. Runtime compatibility is checked explicitly instead of forcing unrelated version churn.
- Made previously ad hoc readiness evidence reproducible in the shipped validator by checking state/action/transition integrity, required contract resolution, registered evaluator resolution, optional/historical manifest references, JSON Schema meta-validity, product-decision positive and negative behavior, and final-state hygiene.
- Fixed the ineffective unfinished-work marker regex, then hardened marker and residue detection without treating legitimate thin adapters, declarations, historical ADR text, or vendored reasoning source as defects.
- Added `ADR-L9-GAR-006.yaml` with finding-to-repair-to-validation traceability for this pass.
- Preserved all runtime architecture, L9 Architecture Profile, Reasoning Foursome source snapshots, intervention semantics, and product-decision schema v3 unchanged.

## 0.8.1 - 2026-09-27

### Recursive Alignment hardening

- Applied `recursive_architecture_alignment_auditor` v1.0 against the complete v0.8.0 skill pack with implementation explicitly authorized.
- Added first-class exact target binding to run state and intake: target identity, artifact type, material revision/version, inspection scope, correction scope, exclusions, inaccessible areas, ambiguity, and direct evidence must be explicit before whole-target claims or mutation.
- Added `TARGET_BINDING_UNRESOLVED`, target-bound convergence proof, and false-completion protection against similarly named target substitution or ambiguous scope.
- Separated inspection scope from correction scope so read authority cannot silently become mutation authority.
- Sharpened Signal Leverage versus Gate semantics: Signal Leverage owns semantic propagation eligibility/topology properties; Constellation.Gate retains concrete inter-node route selection, admission, routability, and routing-seam trust; Gate_SDK retains transport contract and client integration.
- Added conditional `CONTRACT_AND_CONFIGURATION` and `SECURITY` architecture lenses to cover canonical contract ownership, compatibility, configuration source-of-truth, trust boundaries, authn/authz, least privilege, unsafe execution surfaces, sensitive-data handling, and auditability when material; active material lens obligations now block STANDARD/DEEP plan promotion until evaluated and resolved or explicitly bounded.
- Expanded the system model to represent contracts, configuration authority, security boundaries, observability semantics, and validation ownership explicitly.
- Corrected stale reason-code wording that still referred to the retired GAR-owned First-Order architecture question.
- Added blocking evals `GAR-EVAL-057` through `GAR-EVAL-061` and deterministic runtime-alignment validation.
- Added `ADR-L9-GAR-005.yaml` documenting the root causes, rejected over-expansion, exact corrections, and validation evidence.

## 0.8.0 - 2026-09-26

### Added

- Promoted Signal Leverage to a first-class external reasoning primitive alongside First-Order, Second-Order, and Leverage.
- Vendored the complete `L9_REASONING_FOURSOME_PACK_v1.0.0` under `references/reasoning-foursome/`, including the standalone Signal Leverage kernel, foursome ownership matrix, validation gates, binding contract, and canonical leverage law.
- Added first-class run-state receipts for prediction propagation, observation propagation, signal write-back, topology observation, signal drag, validated shared gains, and unresolved propagation gaps.
- Added blocking evals `GAR-EVAL-052` through `GAR-EVAL-056` and signal-specific kill patterns for connectivity theater, authority laundering, runaway loops, and trapped shared gains.
- Added `decisions/ADR-L9-GAR-004.yaml` documenting the Triad-to-Foursome evolution and non-collision boundaries.

### Changed

- Replaced `REASONING_TRIAD_BINDING` with `REASONING_FOURSOME_BINDING`.
- Pre-architecture material reasoning now flows Second-Order BEFORE -> Signal Leverage propagation -> predicted Leverage before GAR may architect.
- Post-execution reasoning now flows Second-Order AFTER -> Signal Leverage observation propagation -> realized Leverage -> Signal Leverage evidence-bound write-back before convergence.
- Leverage no longer owns routing, signal topology, or write-back semantics; it owns systemic value, rank, score, fingerprint, compounding, and eligible shared-gain identification.
- Product Architecture Decision advances to schema v3 so material pre-architecture decisions project the Signal Leverage prediction-propagation receipt.
- The L9 Architecture Profile may constrain signal eligibility and boundaries when applicable but cannot choose topology, assert delivery, or promote returned evidence into authority.

### Preserved

- First-Order remains the sole intervention selector.
- Second-Order remains the sole consequence-model owner.
- GAR remains the architecture-realization owner and does not become a reasoning kernel.
- The L9 Architecture Profile remains architecture law and role hydration, not live inventory or signal runtime state.

## 0.7.0 - 2026-09-26

### Added

- Added `contracts/L9_ARCHITECTURE_PROFILE.yaml`, a conditional L9 constitution that hydrates GAR with eight hardened architecture invariants, an explicit semantic-collision map, canonical vocabulary, role semantics, and canonical flows without becoming a live asset inventory.
- Added profile-aware run state, First-Order handoff constraints, architecture-compliance gates, RAPID-mode hydration, and current-evidence role binding.
- Added `fixtures/l9-architecture-profile-hydration.json` and blocking behavior regressions `GAR-EVAL-042` through `GAR-EVAL-051`.
- Added high-signal kill patterns for profile-as-inventory, supporting-plane role collapse, participation-truth collapse, and participation control-plane leakage into steady-state execution.
- Added `decisions/ADR-L9-GAR-003.yaml` documenting the donor harvest, compression decision, rejected domain drift, runtime binding, and future repair map.

### Changed

- L9 architectural constraints now load before the Reasoning Triad so First-Order can reject architecturally illegal interventions before GAR realizes them.
- GAR now separates stable L9 role knowledge from current role-instance evidence, so it can understand Gate, Gate_SDK, Chassis, State, Evidence, Memory, Context, Research, Formal Reasoning, Reconciler, AgentOS, AgentProfile, communication, documentation, and semantic engines without inventing current topology.
- `AI-Q002` now evaluates the conditional L9 profile plus verified current constellation evidence rather than relying on stale prose-law sources.
- Participation and capability truth now remain explicitly multi-dimensional: implementation, ownership, advertisement, registration, routability, admission, and currentness cannot collapse into one boolean.
- The v0.7 harvest compressed broad donor material into existing semantic owners instead of expanding a large invariant catalog.

### Preserved

- The Reasoning Triad still owns intervention selection, consequences, and leverage. The L9 profile supplies hard feasibility constraints but never ranks interventions.
- Generic GAR epistemic discipline, convergence, and workflow routing remain their existing owners.
- L9 profile applicability remains independent from `L9_RUNTIME_BINDING` activation and orchestration-authority transfer.
- Current repository inventory, versions, provider availability, capability availability, Gate registration, routability, and runtime health still require current evidence.

## 0.6.0 - 2026-09-26

### Fixed

- Corrected the intervention-selection ownership defect that allowed GAR to perform excellent architectural work inside an unproven solution class.
- Prevented implicit `HARVEST_SEMANTICS` or `BUILD_NEW` routing before a current First-Order intervention decision is bound when the reasoning overlay is applicable.
- Prevented GAR from silently changing intervention classes when new evidence favors a materially different move.
- Closed the RAPID-mode escape where a required solution-surface census could otherwise be demanded without a state that produced it.
- Bound non-mutating architectural decisions to intervention fidelity instead of allowing decision-only work to bypass the overlay.
- Prevented execution success from being treated as proof of realized leverage when post-execution consequence/leverage closure is material.

### Added

- `integrations/REASONING_TRIAD_BINDING.yaml` as the non-owning boundary between GAR and the First-Order, Second-Order, and Leverage semantic owners.
- Pinned Reasoning Triad source snapshots under `references/reasoning-triad/` for provenance and stable binding.
- Bounded solution-surface census state for existing local owners, constellation owners, tools, packages, APIs, SDKs, CLIs, services, vendorable implementations, transplantable code, semantic-only donor value, and unresolved capability evidence.
- Intervention-fidelity state and explicit First-Order reconsideration handback.
- Post-execution Second-Order and realized-Leverage receipt tracking.
- Blocking behavior regressions through `GAR-EVAL-041`, including the canonical `excellent_wrong_work` failure.
- `fixtures/upstream-capability-vs-harvest.json` for direct-consumption-vs-harvest regression coverage.
- `decisions/ADR-L9-GAR-002.yaml` documenting the v0.6 problem, decision, rejected alternatives, validation, and future repair map.

### Changed

- GAR's former independent First-Order architecture question became an intervention-fidelity proof against the externally owned First-Order decision.
- Existing-mechanism search now produces evidence for intervention reasoning rather than silently owning the intervention class.
- Product architecture decisions now project a selected intervention instead of encoding `HARVEST_THEN_DECIDE` behavior.
- Convergence now distinguishes realized outcome correctness from predicted and realized systemic leverage where the overlay is material.

### Breaking

- `schemas/product-architecture-decision.schema.json` advances from `l9.gar.product-architecture-decision/v1` to `v2`.
- `HARVEST_THEN_DECIDE` is intentionally invalid under the v2 decision schema.
- Producers of product architecture decisions must emit the v2 intervention projection and supporting reasoning/currentness fields.

### Preserved

- `l9-intelligence-harvest` remains a narrow semantic-harvest capability rather than becoming a general intervention router.
- GAR remains the architectural realization owner beneath the Reasoning Triad rather than absorbing First-Order, Second-Order, or Leverage semantics.
- Reuse is not hard-coded as the winner. Upstream consumption, adaptation, vendoring, transplant, semantic harvest, local build, and no-action remain evidence-tested intervention candidates.

## 0.5.0 - 2026-08-26

- Established the machine-readable GAR runtime, guarded state-machine routing, explicit run state, evaluator registry, evidence discipline, architectural integrity, outcome accountability, convergence law, and host/runtime integration boundary.
- Made convergence the sole success definition and separated outcome accountability from execution capability.
- Established single-owner machine-readable runtime semantics with `SKILL.md` as a thin bootloader.
