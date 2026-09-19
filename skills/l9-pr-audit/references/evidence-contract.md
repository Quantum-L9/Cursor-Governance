<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: reference
role: evidence-contract
version: 2.0.0
status: active
-->

# Evidence and Remediation Handoff Contract

## Contents

- Canonical structure and deterministic census binding
- Changed symbols, claims, falsification, inspection inventory, domains, adapters, boundaries
- Finding provenance, recursive passes, coverage, intent, PR inventory, change discipline, obligations
- Evidence states, revision identity, bidirectional integrity, check/review evidence, secret safety
- Remediation surfaces, mutation probe/result gate, regression/preservation/anti-bypass proof
- Cross-PR proof, residual Unknowns, remediation convergence, handoff quality, deterministic closure evidence

## Prime directive

Make the audit directly consumable by remediation without forcing downstream rediscovery. Evidence strength must match the claim, and every readiness-relevant claim must trace to canonical evidence.

## Canonical structural owner

`schemas/audit-output.schema.json` owns `audit.json`. `scripts/build_audit_bundle.py` loads that schema with Draft 2020-12 validation, then applies cross-field semantic gates. Unknown fields are rejected. Do not create a second structural validator.

## Deterministic census binding

`deterministic_census_binding` binds each audited PR to the exact machine change ledger by ledger schema, generator version, source head, and canonical SHA-256. The builder receives those ledger files explicitly and rejects missing PRs, moved heads, hash mismatches, or machine-owned rows that diverge from the bound census. The bundled `change-ledger.json` is provenance input; `audit.json` remains canonical semantic truth.

## Changed-symbol ledger

`changed_symbol_ledger` records every machine-enumerated semantic change plus any auditor-added semantic symbol. Machine rows preserve path/name/kind/change-type/detection method/confidence/source from the deterministic ledger. Every machine symbol has a `CHANGED_SYMBOL` audit obligation and at least one linked `CHANGED_SYMBOL` claim. Heuristic detection remains labeled `HEURISTIC`; file fallback remains `FILE_SCOPE`; only exact static evidence may claim exactness.

## Claim-validation matrix

`claim_validation_matrix` is the canonical claim ledger for objectives, domains, changed symbols, readiness, convergence, preservation, findings, and auditor-added material assertions. Machine-seeded claims may be supplemented but not deleted or rewritten. Material claims are `SUPPORTED`, `REFUTED`, `NOT_APPLICABLE`, or `UNKNOWN`; status must reconcile with the existing canonical objective/domain/symbol/readiness/convergence state. Claim evidence must discriminate `claim:<claim_id>` or an explicitly declared validation property.

## Falsification ledger

`falsification_ledger` is the deterministic red-team surface. Every material positive claim receives one or more counterexample attacks such as negative-requirement search, alternate-owner/bypass search, mutation test, failure injection, stale-evidence check, baseline comparison, cross-PR conflict search, or omission search. `SUPPORTED` requires every applicable probe to `SURVIVE`; any `FALSIFIED` probe refutes the claim; `INCONCLUSIVE` blocks positive closure. Probe-closing evidence must discriminate `falsification:<claim_id>`. `LLM_JUDGMENT`/`HYBRID` is allowed only when static/command/check evidence cannot decide the attack and must include rationale plus evidence.

## Inspection inventory

`audit_coverage.artifact_inventory` records the exact inspected artifact universe: path, revision, affected PRs, artifact class, audit roles, responsibility, and canonical evidence. Every changed file must appear exactly once as `CHANGED` for its PR head. Every authoritative, implementation, and coupled remediation surface must be represented. A `COMPLETE` audit may not hide unknown artifact revisions.

This closes a model-variance gap: two auditors may reason differently, but neither may support a whole-audit conclusion with an invisible browsing trail.

## Canonical domain assessments

`audit_coverage.domain_assessments` is the single source of truth for audit-domain disposition. Every canonical domain appears exactly once with `PASS`, `FAIL`, `NOT_APPLICABLE`, or `UNKNOWN`, evidence IDs, related finding IDs, and closing-validation text when needed. There is no separate completed/skipped domain ledger. `FAIL` means the audit conclusively found a domain defect; it does not mean the audit itself failed to converge.

## Architecture policy adapters

`architecture_policy_adapters` records project-, platform-, regulatory-, organizational-, or domain-specific architecture law separately from ChatGPT/Fable execution adapters. Applied adapters require exact governing authority, scope, rule domains, validation methods, and confirmed evidence. `NOT_APPLICABLE` is explicit. Do not import an adapter from unrelated repositories by naming similarity.

## Boundary map

`boundary_map` records component responsibilities and material architecture boundaries. Findings must resolve their `semantic_owner` to a component in this map. A complete audit cannot rely on an implicit prose-only ownership model.

## Finding provenance and blocking basis

Every finding records whether it was `PR_INTRODUCED`, `PR_EXPOSED`, `PRE_EXISTING`, or `UNKNOWN`, plus `origin_evidence_ids`. Any non-Unknown origin requires confirmed evidence that discriminates `finding_origin`. `merge_blocking` is never self-justifying: the paired `merge_blocking_basis` must identify blocking/non-blocking status, governing authority when blocking, rationale, and evidence. Blocking evidence must be confirmed and discriminate `merge_blocking_basis`. This prevents an auditor from turning severity rhetoric or unrelated baseline debt into arbitrary PR blockage. A `PRE_EXISTING` finding additionally requires confirmed `pre_existing_blocking_relevance` evidence before it may block merge, and remains non-mutation-eligible without separately authorized scope.

## Recursive audit pass evidence

`audit_passes` records the bounded recursive review sequence. Pass 1 is `DISCOVERY`; the final pass is `VERIFICATION`; intermediate `RECONCILIATION` passes exist only when a concrete evidence-backed objective remains. Each pass records evidence, findings, obligations, claims, and falsification probes re-observed, new-information count, measurable result, and next-pass objective.

A `CONVERGED` audit requires final verification to re-observe every retained finding, every obligation, every material claim, and every falsification probe, discover zero new material information, and have no next-pass objective. It may not retain a material `UNKNOWN` claim or an unresolved applicable `INCONCLUSIVE` falsification probe. This is search-saturation evidence, not proof that the PR itself is defect-free.

## Target coverage

`audit_coverage` records explicit inspection scope, exclusions/inaccessibility and impact, applicable domains, completed domains, and skipped domains. `CHANGE_DISCIPLINE` is mandatory.

`COMPLETE` is illegal when an applicable domain has no disposition, an `UNKNOWN` skipped domain remains, or an excluded surface blocks convergence.

## Intent contract

`intent_contract` separates requested intent provenance from repository architecture authority.

- `sources` records current user instruction, original PR prompt, PR body/issue, repository law, or other provenance.
- `objectives` records active/superseded/conflicted objectives with explicit scope, non-goals, and acceptance criteria.
- `original_pr_prompt` records whether the prompt was provided/recovered/unavailable/unknown and what audit questions used it.

The original prompt is strong evidence for historical requested objective and scope but never overrides newer user authority or current repository law.

## Exact PR inventory

Every `pr_binding` includes exact base/head identity plus exact `changed_files` inventory. `change_discipline.scope_fidelity.changed_surfaces` must cover that inventory exactly once. This converts "did the model notice every changed file?" into a deterministic gate.

## Change discipline

`change_discipline` owns eight required review surfaces:

1. `objective_closure`
2. `scope_fidelity`
3. `complexity_delta`
4. `architectural_economy`
5. `supersession_closure`
6. `failure_path_coverage`
7. `test_discrimination`
8. `control_adequacy`

Structural growth is evidence, not automatic failure. `UNJUSTIFIED`, `SCOPE_EXTENSION`, `RESIDUAL`, `WEAK`, and `ABSENT` require explicit findings where defined by the schema/semantic gates. Unknowns block affected audit convergence until represented in `residual_unknowns`.

## Audit obligation ledger

`audit_obligation_ledger` is the coverage governor. Each obligation records ID, PR, kind, subject, disposition, evidence IDs, and related finding IDs.

Required kinds cover active objectives, every changed surface, every machine changed symbol, architecture-growth candidates, material supersession, material failure paths, test-discrimination obligations, in-scope CI failures, and every unresolved review thread discovered at the audited head.

The model may add obligations but may not remove deterministic obligations. Audit convergence requires complete disposition as `PASS`, `FINDING`, `NOT_APPLICABLE`, or `UNKNOWN`. A `FINDING` is compatible with a converged audit; an unrepresented Unknown is not.

## Every remediation-relevant finding

Include stable ID/class/severity/confidence/merge-blocking state, affected PRs and exact heads, governing authority, ownership axes, canonical evidence IDs, observed/expected behavior, mismatch, impact, root cause/state, behavioral closure condition, and typed closing validation.

Finding classes include `COMPLETENESS`, `CORRECTNESS`, `ARCHITECTURE`, `INVARIANT`, `CONTRACT`, `SOURCE_OF_TRUTH`, `SECURITY`, `RELIABILITY`, `PERFORMANCE`, `TEST_QUALITY`, `CI`, `REVIEW`, `CROSS_PR`, `PRESERVATION`, `SCOPE`, `PROPORTIONALITY`, and `SUPERSESSION`.

## Evidence states and types

Every material evidence entry carries `epistemic_state`: `CONFIRMED`, `INFERENCE`, or `UNKNOWN`.

Evidence types: `SOURCE`, `CONTRACT`, `INVARIANT`, `DIFF`, `TEST`, `CI`, `RUNTIME`, `MEASUREMENT`, `REVIEW_THREAD`, `GENERATED_ARTIFACT`, `CONFIGURATION`, `DEPENDENCY_GRAPH`, `CROSS_PR_INTERACTION`.

Validation result vocabulary: `PASS`, `FAIL`, `BLOCKED`, `NOT_EXECUTED`, `UNKNOWN`, `NOT_APPLICABLE`.

`properties_discriminated` names what the evidence actually proves. A green check is never global correctness evidence merely because it is green.

## Revision identity

For `TEST`, `CI`, `RUNTIME`, and `MEASUREMENT` evidence preserve separately `source_head_sha`, exact `tested_revision_sha`, and validation result. Observed `PASS`/`FAIL` with unknown tested revision is invalid.

## Bidirectional evidence integrity

If a finding references evidence ID `E`, evidence `E.findings_using_this_evidence` must reference that finding, and vice versa. Evidence used only for authority, scope, obligations, reviews, required-check resolution, anti-bypass, preservation, regression, or cross-PR proof may have no finding reference.

## Required-check and review evidence

Every PR binding carries evidence IDs for required-check resolution and review-thread coverage. Resolved/none/complete claims require confirmed claim-specific evidence. READY requires zero unresolved review threads.

The audit obligation ledger also carries one `REVIEW_THREAD` obligation per unresolved thread discovered. This prevents aggregate counts from hiding an uninspected thread.

## Secret-safe evidence

Never preserve a secret value to prove exposure. Keep repository/path/line/symbol/check identifiers, a redacted excerpt when needed, and the fact proven. The packager rejects common high-confidence secret shapes.

## Remediation surface evidence

For every finding record authoritative read surfaces, implementation surfaces, coupled read surfaces, excluded false leads when useful, and `surface_evidence` linking paths/roles to canonical evidence IDs.

Every implementation path must have confirmed `IMPLEMENTATION` surface evidence whose discriminated properties include `implementation_surface`.

## Mutation probe result contract

`schemas/mutation-probe-result.schema.json` owns the machine-readable output of `scripts/execute_mutation_probe.py`. The runner validates its result before emission. Default command execution is `ARGV_NO_SHELL`; `SHELL_EXPLICIT` is permitted only when the caller supplied `--allow-shell`. The result records hashes rather than raw stdout/stderr, binds the audited source hash before/after, and uses truthful process exit semantics: `0=KILLED`, `1=SURVIVED`, `2=BASELINE_FAILED/EXECUTION_ERROR`, `3=audited-source integrity failure`. The temporary copy is filesystem isolation only, not a security sandbox.

## Mutation gate

A finding becomes default mutation work only when all are true:

1. `remediation_owner_class == CODEBASE`;
2. `confidence == Confirmed`;
3. `root_cause_state == CONFIRMED`;
4. mutation guard is `NOT_APPLICABLE` or an admitted `MUTATION_GUARD` authority;
5. dependency order is resolvable;
6. at least one implementation path has confirmed implementation-surface evidence.

Anything else remains evidence-bearing but non-authorizing. An unlisted required write path yields `SCOPE_EXTENSION_REQUIRED`.

## Regression, preservation, anti-bypass, failure, and test proof

Correctness findings should record reproduction and regression evidence when applicable. Public/data/release changes create preservation obligations. Every selected PR must contain every anti-bypass class exactly once.

Failure-path coverage and test-discrimination are distinct from generic green CI. Changed failure behavior may be structurally proven or tested. A test is discriminating only when evidence shows it can distinguish the governed behavior from a wrong implementation; selective mutation testing is strong evidence when safe/available.

## Cross-PR proof

Single-PR audits use `NOT_APPLICABLE`. Multi-PR audits classify material relationships and carry evidence-backed exact merge order before combined READY.

## Residual Unknowns

Every residual Unknown records ID, description, affected PRs/conclusion, readiness/convergence impact, evidence needed, and owner class. Unknown change-discipline obligations prevent audit convergence unless represented and reconciled.

## Remediation contract convergence

The remediation contract's **primary** mission is closing audit findings. In addition, it requires current CI convergence and all-current-review-thread convergence on affected PRs.

- repair codebase-owned CI failures within authorized write scope;
- report external CI pipeline/environment/human blockers rather than weakening gates;
- inspect, reply to, and resolve every current unresolved review thread regardless of author, re-querying after publication;
- publish only through the canonical SSOT Makefile `make pr` surface;
- `MERGE=False`: stop at merge-ready, never merge.

## Handoff quality gate

Pass only when bound change-ledger validation, schema validation, semantic validation, derived handoff schema validation, and manifest verification all succeed. Fail when machine symbol/claim/falsification seeds are missing or rewritten, a material positive claim lacks adversarial closure, or remediation would need to rediscover basic bug location, governing authority, ownership class, changed-file/symbol scope, unresolved audit obligations, already-triaged CI failure, write-surface proof, or exact closure target. The handoff carries an adversarial-assurance summary; detailed red-team ledgers remain canonical in `audit.json`.

## Deterministic closure evidence

A deterministic closure row must cite evidence that discriminates its specific disposition. Repository-wide uniqueness/absence/precedence conclusions additionally require a bound complete repository corpus. CI `PRE_EXISTING` attribution requires `ci_baseline` evidence; severity overrides require `severity_override` evidence; generated `MATCHED` requires generator/source/command provenance plus equal audited and regenerated hashes.
