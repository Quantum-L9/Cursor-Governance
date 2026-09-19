---
name: l9-pr-audit
description: deep-audit one or more GitHub pull requests against current repository architecture, invariants, contracts, ownership, CI, reviews, change proportionality, and cross-PR interactions, using a deterministic evidence census plus recursive verification to produce a revision-bound audit and PR Remediation Contract without mutating the target repository. use when auditing PR correctness, completeness, architecture alignment, merge readiness, or downstream remediation evidence.
disable-model-invocation: true
---

# L9 PR Audit

## Purpose

Deep-audit the exact current heads of one or more pull requests against the target repository's actual architecture and operational law. Use a deterministic adversarial census plus bounded LLM judgment to actively falsify material positive conclusions. Produce an evidence-complete, revision-bound audit that a downstream remediation agent can act on without repeating basic discovery.

The audited repository is read-only. This skill may create local audit artifacts and the requested ZIP, but it never edits, pushes, comments on, closes, or merges audited PRs.

## Ownership boundary

- `l9-pr-audit` owns the read-only PR evidence census, changed-symbol census, claim-validation matrix, adversarial falsification ledger, producer/consumer closure, isolated mutation discrimination, semantic review-thread closure, orphan-artifact reachability, objective/scope reconstruction, deep correctness/completeness/architecture review, change-discipline audit, invariant/contract/CI/review/preservation/anti-bypass/cross-PR audit, obligation closure, and evidence-rich remediation handoff.
- `l9-pr-digest` is donor intelligence only. Its useful scope/expansion/proportionality detectors are harvested into this pack; runtime audit execution must not depend on `l9-pr-digest` being installed or invoked.
- `l9-pr-remediation` or another explicitly authorized coding agent owns mutation and convergence of repository code. Audit-only mutation discrimination is limited to disposable temporary copies and never grants mutation authority over the audited repository. Its deterministic signal-census and review/CI convergence patterns may be harvested, but `l9-pr-audit` does not become a second remediation engine. The audit phase remains read-only.
- Repository domain owners retain semantic authority. This skill cites their law; it does not become a competing source of truth.
- The remediation adapter changes downstream work shape only. `autoremediate=0` is the default, so bundle generation never silently launches repair. When a remediation executor is explicitly invoked, the generated PR Remediation Contract is the downstream execution contract and remains subordinate to current user authority and repository law.
- `schemas/audit-output.schema.json` owns structural audit shape. `scripts/build_audit_bundle.py` owns cross-field semantic validation and deterministic projections. Do not duplicate either contract in another validator.

## Required inputs

- Target GitHub repository, as URL or `owner/repo`.
- PR scope. If specific PRs are supplied, audit exactly those. If the user requests all open PRs, or supplies only a repository in an audit request, freeze all PRs open at audit start.
- Current repository and PR evidence sufficient to bind exact default-branch, base, and source-head revisions.
- The original prompt/task contract used to generate the PR when available. This is preferred intent evidence for objective closure, scope/non-goals, proportionality, failure-path expectations, and expected tests, but the audit must continue when it cannot be recovered.

Do not ask for inputs already recoverable from the repository or current conversation. If a material binding cannot be resolved, record `UNKNOWN` and fail the affected completeness, readiness, or convergence claim closed.

## Authority order

1. Latest explicit user scope and constraints.
2. Current repository architecture law, semantic owners, and scoped instructions.
3. Authoritative invariants, contracts, schemas, ADRs, policy, generators, mutation guards, and enforcement owners.
4. Original PR-generation prompt/task contract for historical requested objective, explicit scope, non-goals, and acceptance criteria only; it never overrides current repository law, current contracts, or newer user authority.
5. Reproducible runtime, CI, measurement, and validation evidence bound to the revision actually tested.
6. Current implementation and tests as evidence, not automatic authority.
7. PR description, commits, reviews, and review threads after reconfirmation against the current head.
8. Current documentation and historical plans.
9. Labeled inference.
10. `UNKNOWN`.

Higher authority wins. An index or pointer is navigation evidence, not a replacement for the semantic owner it cites. Never let a green check prove architecture, a PR description redefine repository law, or an inference masquerade as observed state.

## Runtime laws

1. **Target and inspection scope are explicit.** Record what was inspected, what was excluded or inaccessible, and whether each exclusion blocks a finding, readiness, or convergence. Never claim whole-target coverage from partial inspection.
2. **Authority is resolved, not implied.** Record each material authority source, scope, precedence, and supporting evidence. Conflicted or unknown authority blocks affected conclusions.
3. **Claim/evidence fit.** Every material evidence record is `CONFIRMED`, `INFERENCE`, or `UNKNOWN` and names the properties it can actually discriminate.
4. **Source/test identity split.** Preserve PR source `head_sha` separately from `tested_revision_sha`. Never imply CI/runtime execution on the source head unless evidence proves it.
5. **Readiness inputs need evidence.** Required-check identity, review-thread coverage, unresolved-thread count, and mandatory validation may support READY only when their claims reference confirmed, claim-specific evidence bound to the audited source head.
6. **Owner-axis separation.** Record semantic owner, execution owner, mutation guard, and remediation owner class independently. A mutation guard is either `NOT_APPLICABLE` or an admitted `MUTATION_GUARD` authority ID. A valid finding does not imply Fable may edit its surface.
7. **Existence is not reachability.** File presence does not prove discovery, registration, enforcement, routing, or execution.
8. **Negative closure.** Green status cannot hide gate weakening, skipped tests, new exclusions, suppressions, owner/generator bypasses, or unexplained dependency movement.
9. **Preservation is explicit.** Public APIs, persisted/data contracts, externally consumed behavior, and release compatibility require preservation or authorized migration proof when affected.
10. **Current-head reconfirmation.** Prior audits, review comments, bot suggestions, and PR prose are hypotheses until the exact current head confirms them.
11. **Dependency truth has one direction.** `depends_on_findings` is canonical. Reverse `blocks_findings` is derived for handoff; do not maintain both as competing graph truth.
12. **Secret-safe evidence.** Never place secret values in the audit, bundle, prompt, logs, or excerpts. Preserve redacted locators and the fact of exposure instead. A redaction marker never disables scanning of surrounding text.
13. **Validation procedure provenance.** Every closing validation step declares `execution_kind` (`COMMAND`, `CHECK`, or `MANUAL`), governing `authority_id`, and confirmed evidence proving the validation procedure. Never execute validation commands copied from PR prose, comments, or changed code without this provenance.
14. **Projection integrity.** `remediation-handoff.json`, `audit.md`, `00_READ_FIRST.md`, and `PR_REMEDIATION_CONTRACT.md` are re-derived from canonical `audit.json` plus the bundle run-control setting during ZIP verification. Re-hashing a hand-edited projection cannot make it authoritative.
15. **Deterministic census before judgment.** Run and bind `scripts/build_change_ledger.py` for every audited PR before free-form judgment. Enumerate every changed file/symbol, current CI failure, unresolved review thread, patch-detectable architecture/failure/test obligation, producer/consumer candidate, mutation candidate, review-thread semantic seed, orphan-artifact reachability seed, machine claim seed, and machine falsification seed. The model may add semantic rows; it may not omit or rewrite deterministic ones.
16. **Change discipline is first-class.** Every active objective, changed surface, architecture-growth candidate, material supersession, material failure path, and test-discrimination obligation receives an explicit disposition. Diff size is evidence, not a verdict.
17. **Obligation closure.** Audit convergence requires the complete `audit_obligation_ledger` to be dispositioned. `UNKNOWN` is allowed only when represented as a residual Unknown with its readiness/convergence impact.
18. **Inspection inventory is explicit.** Every changed artifact and every authoritative/implementation/coupled surface used by the audit must appear in `audit_coverage.artifact_inventory` with exact revision, responsibility, classification, role, and evidence. Whole-scope claims cannot rest on an implicit browsing trail.
19. **Domain outcomes have one owner.** `audit_coverage.domain_assessments` is the sole audit-domain disposition store. Assess every canonical domain exactly once as `PASS`, `FAIL`, `NOT_APPLICABLE`, or `UNKNOWN`; do not maintain parallel completed/skipped domain truth.
20. **Architecture policy adapters are explicit.** Record project/domain/platform architecture adapters separately from provider adapters. Bind each applied adapter to governing authority, exact scope, rule domains, validation methods, and evidence. Never import an adapter from a neighboring project by similarity.
21. **Boundary ownership is canonical data.** Record component responsibilities plus material communication/routing/orchestration/data/config/security/policy/validation/source-of-truth boundaries in `boundary_map`. A finding's semantic owner must resolve to that map rather than exist only in prose.
22. **Blocking decisions require proof.** Distinguish whether a finding was `PR_INTRODUCED`, `PR_EXPOSED`, `PRE_EXISTING`, or `UNKNOWN`. A merge-blocking finding requires an authority-backed `merge_blocking_basis` with confirmed evidence that discriminates the blocking decision.
23. **Underbuilt controls are audited explicitly.** `change_discipline.control_adequacy` records whether required contract, boundary, security, reliability, observability, validation, ownership, and source-of-truth controls are adequate, underbuilt, not applicable, or unknown. Underbuilt controls require findings.
24. **Red-team surfaces are machine-owned.** Bind one deterministic change ledger per audited PR. `changed_symbol_ledger`, machine-seeded `claim_validation_matrix` rows, and machine-seeded `falsification_ledger` rows must preserve that census exactly; the model may add semantic rows but may not delete, rename, or rewrite machine seeds.
25. **Positive claims must survive attack.** Every material `SUPPORTED` claim requires claim-specific validation and all applicable falsification probes to `SURVIVE`. A `FALSIFIED` probe refutes the claim; an `INCONCLUSIVE` probe prevents positive closure. Use LLM judgment only when the probe declares why deterministic closure is insufficient.
26. **Recursive verification proves saturation.** Run at least one discovery pass and one final verification pass. A `CONVERGED` audit requires the final verification pass to re-observe every retained finding, audit obligation, material claim, and falsification probe and discover zero new material information; if verification finds something new or any applicable attack remains inconclusive, perform another bounded reconciliation/verification pass instead of stopping.
27. **Deterministic closure owns enumerable audit completeness.** Load [references/deterministic-closure.md](references/deterministic-closure.md). Public-contract deltas, SSOT candidates, bypass paths, supersession liveness, changed failure edges, config precedence, dependency causality/pairing, diff hunks, root-cause dominance, severity bounds, reverse validation coverage, CI causality, generated provenance, and architecture-economy proof must use their canonical machine/semantic closure rows. Do not substitute reviewer prose for a required disposition.

## Run control

- Default `autoremediate=0`. Audit, validate, build, and return the remediation bundle only. Do not automatically invoke a remediation executor.
- `autoremediate=1` is valid only when the latest explicit user instruction enables it for that run. The audit phase itself remains read-only; execution must be handed to a separately authorized remediation executor.
- The bundle records the `autoremediate` value in `remediation-handoff.json` and `MANIFEST.json` so verification cannot silently change the run mode.
- Publication authority in the remediation contract is limited to validated fixes on the existing affected PR branches through the canonical SSOT Makefile `make pr` surface. The target repository Makefile is never the publication authority.

## Mutation eligibility for Fable

A work unit receives `mutation_eligible: true` only when all are true:

- owner class is `CODEBASE`;
- finding confidence is `Confirmed`;
- root cause state is `CONFIRMED`;
- mutation guard is `NOT_APPLICABLE` or resolves to an admitted `MUTATION_GUARD` authority;
- dependency order is resolvable and not `UNKNOWN`;
- finding origin is neither `PRE_EXISTING` nor `UNKNOWN`;
- at least one exact implementation path has confirmed evidence that specifically discriminates `implementation_surface`.

`write_surfaces` is a strict allowlist. If Fable proves that an unlisted path is required, it must stop that unit as `SCOPE_EXTENSION_REQUIRED` and request a refreshed handoff or separate authority. It may not self-authorize scope expansion.

## Progressive load map

Load only what the current stage needs:

- Audit method: [references/audit-protocol.md](references/audit-protocol.md)
- Change discipline, proportionality, scope, failure/test obligations: [references/change-discipline.md](references/change-discipline.md)
- Evidence and finding contract: [references/evidence-contract.md](references/evidence-contract.md)
- Output ZIP contract: [references/output-bundle.md](references/output-bundle.md)
- Deterministic gates: [references/enforcement-gates.md](references/enforcement-gates.md)
- ChatGPT execution binding: [adapters/chatgpt.md](adapters/chatgpt.md)
- Fable downstream binding: [adapters/claude-code-fable.md](adapters/claude-code-fable.md)
- Canonical audit schema: [schemas/audit-output.schema.json](schemas/audit-output.schema.json)
- Derived handoff schema: [schemas/remediation-handoff.schema.json](schemas/remediation-handoff.schema.json)
- Bundle manifest schema: [schemas/bundle-manifest.schema.json](schemas/bundle-manifest.schema.json)
- Deterministic change census: [scripts/build_change_ledger.py](scripts/build_change_ledger.py)
- Deterministic adversarial red-team contract: [references/adversarial-red-team.md](references/adversarial-red-team.md)
- Deterministic closure contract: [references/deterministic-closure.md](references/deterministic-closure.md)
- Harvest provenance: [references/harvested-invariants.md](references/harvested-invariants.md), maintenance only

`jsonschema>=4` is required by the deterministic builder. Missing schema validation is a blocker, never a reason to fall back to prose-only validation.

## Audit workflow

1. **Bind target and audit coverage.** Resolve exact repository/default branch/default-branch SHA, frozen PR set, inspection scope, excluded/inaccessible surfaces, applicable audit domains, and exact changed-file inventory per PR. `CHANGE_DISCIPLINE` is always applicable.
2. **Resolve authority and intent provenance.** Discover repository law, semantic owners, invariants, contracts, schemas, ADRs, generators, mutation guards, and merge/validation enforcement. Recover the original PR-generation prompt/task contract when available and record its provenance; do not block solely because it is unavailable.
3. **Bind PRs.** For each PR bind exact base SHA, source head SHA, branches, commits, changed files, draft/state, mergeability, required-check resolution, review-thread discovered/classified/remaining counts, and canonical evidence IDs supporting mandatory validation.
4. **Run and bind the deterministic census.** For every audited PR, run `scripts/build_change_ledger.py` against normalized exact-head evidence. Preserve the canonical ledger hash in `deterministic_census_binding`; bundle construction requires the ledger bytes. Enumerate every changed surface, changed symbol, current CI failure, unresolved review thread, patch-detectable architecture-growth candidate, material failure-path candidate, test-discrimination obligation, machine claim seed, and machine falsification seed before semantic grading.
5. **Materialize the deterministic red team.** Populate `changed_symbol_ledger` from the machine census, seed `claim_validation_matrix` and `falsification_ledger`, then add only evidence-backed auditor-discovered rows. Every material positive claim must be paired with explicit counterexample/falsification work before it can close as supported. Load [references/adversarial-red-team.md](references/adversarial-red-team.md).
   Materialize `deterministic_closure_ledger` from the same bound census and close every applicable row under [references/deterministic-closure.md](references/deterministic-closure.md). Treat `repository_files_complete: true` as the only machine signal that a supplied repository corpus is complete; file presence alone never upgrades a partial corpus.
6. **Materialize the inspection inventory.** Record every changed file plus each authoritative, validation, implementation, and directly coupled artifact actually inspected, with its exact revision, responsibility, classification, roles, and evidence. Do not let an unrecorded browsing path support a whole-audit conclusion.
7. **Reconstruct the objective contract.** Resolve active objectives, explicit scope, non-goals, acceptance criteria, and intended post-PR behavior from current user authority + repository law + original PR prompt when available. Keep superseded/conflicted objectives explicit.
8. **Build the audit obligation ledger.** Seed it with the deterministic census, then add semantic obligations discovered from architecture, coupling, contracts, supersession, or cross-PR analysis. Every obligation must end `PASS`, `FINDING`, `NOT_APPLICABLE`, or `UNKNOWN` with evidence.
9. **Collect complete in-scope evidence.** Inspect the full diff, every changed file, every unresolved review thread, material check results, and directly coupled surfaces needed to falsify a material conclusion. The diff boundary is not automatically the audit boundary.
10. **Build the boundary/surface model.** Map calls, imports, reads, writes, produces, consumes, transforms, generates, validates, routes, authorizes, persists, publishes, registers, discovers, and enforces where material.
11. **Audit each PR.** Evaluate completeness, correctness, architecture alignment, invariant preservation, contracts/schemas, source-of-truth relationships, security/authority, reliability/observability, measured performance when material, test quality, CI, review status, preservation, anti-bypass checks, and the full change-discipline contract from [references/change-discipline.md](references/change-discipline.md).
12. **Audit proportionality and economy.** Record the structural complexity delta. For every new architecture candidate, decide whether existing ownership/capability can absorb the requirement before accepting new machinery. Never fail solely because a PR is large or adds an abstraction.
13. **Audit scope fidelity.** Every changed file must map to `REQUIRED`, `DIRECTLY_COUPLED`, `VALIDATION_REQUIRED`, `GENERATED_CONSEQUENCE`, `SCOPE_EXTENSION`, or `UNKNOWN`. `SCOPE_EXTENSION` is a finding; `UNKNOWN` blocks affected convergence/readiness until represented and resolved.
14. **Audit supersession, failure paths, and test discrimination.** When behavior/path/owner is replaced, inspect residual live references. For material changed failure behavior, require test or structural proof. For materially changed production behavior, determine whether the validating test/check actually discriminates the property.
15. **Audit the constellation.** With multiple PRs, analyze overlap, stacked bases, hidden dependencies, duplicate authority, generated collisions, supersession, combined behavior, and proven merge order. `cross_pr_evidence_pack` is `NOT_APPLICABLE` only for a single-PR audit.
16. **Run available read-only validation.** Prefer repository-native checks that discriminate the property under review. Record source head, exact tested revision, command/check, result, and properties discriminated. `NOT_EXECUTED` is never `PASS`.
17. **Reconcile and consolidate.** Reconfirm prior findings against current heads, remove false positives/already-fixed signals, split mixed CI failures by owner, and consolidate symptoms under evidence-backed root causes.
18. **Gate findings and repair surfaces.** Retain no correctness/architecture/scope/proportionality finding without governing authority plus direct evidence. Bind each finding to exact heads, owner axes, root-cause state, closure condition, and evidence-backed implementation/coupled surfaces.
19. **Assess preservation and bypass.** Require explicit proof when public/data/release behavior or validation surfaces move. Every selected PR must cover every anti-bypass class exactly once.
20. **Close the obligation ledger.** The audit cannot converge while any deterministic or semantic obligation lacks a disposition. Known defects may remain as `FINDING`; uncertainty remains explicit as `UNKNOWN` and must flow to `residual_unknowns`.
21. **Assess readiness and convergence separately.** Merge readiness concerns the proposed code state. Audit convergence concerns whether the audit itself has complete scope/authority/evidence/change-discipline/obligation reconciliation. A NotReady PR may still have a Converged audit.
22. **Run recursive audit verification.** Record `audit_passes`. The first pass is `DISCOVERY`; the final pass is `VERIFICATION`. Recheck every retained finding, every obligation, every material claim, and every falsification probe against exact current evidence. If verification discovers any new material finding, obligation, contradiction, or Unknown, do not declare convergence: reconcile it and run another verification pass.
23. **Write canonical audit.** Create `audit.json` exactly to [schemas/audit-output.schema.json](schemas/audit-output.schema.json). Do not add ad hoc fields.
24. **Validate and build.** Run `python scripts/build_audit_bundle.py --audit <audit.json> --change-ledger <pr-ledger.json> [--change-ledger <next-pr-ledger.json> ...] --validate-only`, then build the ZIP with the same bound ledgers. Derived handoff and manifest must pass their own schemas.

## Finding doctrine

Every retained finding must answer with evidence:

- What governing rule/expected behavior applies, which `authority_id` owns it, and what enforces it?
- What does the exact audited source head do and what should it do?
- Which evidence IDs prove the mismatch, and what properties do those records discriminate?
- Is the root cause `CONFIRMED`, `INFERENCE`, or `UNKNOWN`?
- Who owns semantics, execution, mutation admissibility, and remediation class, and which admitted authority resolves the mutation guard?
- Which exact surfaces are authoritative, implementation candidates, coupled reads, or false leads?
- What behavior closes the finding, which validation discriminates closure, whether it is `COMMAND`/`CHECK`/`MANUAL`, and what authority/evidence proves that validation procedure is legitimate?

Severity is consequence-based: `Critical`, `High`, `Medium`, `Low`. Confidence is evidence-based: `Confirmed`, `Probable`, `Possible`, `Unknown`. Merge-blocking is independent from rhetorical severity.

A performance finding is not `Confirmed` or `Probable` without measurement evidence when executable measurement exists. A generated/registered surface is not proven active from file existence alone. A touched file is not proof of improvement.

## Evidence economy

Prefer exact locators over source dumps. Preserve repository, source head, tested revision, path, line range, symbol, check, command, result, properties discriminated, and concise fact proven when available. Store shared evidence once and reference it by ID.

The builder enforces bidirectional finding/evidence references for evidence used by findings. Required-check/review claims, authority records, anti-bypass checks, surface evidence, regression proof, and cross-PR relationships must reference the canonical evidence index rather than become parallel evidence stores.

Do not make remediation reopen whole CI logs, rediscover governing invariants, remap basic coupled surfaces, or rediscover whether a finding is editable.

## PR remediation handoff

When Claude Code Fable or another authorized remediation executor will remediate, load [adapters/claude-code-fable.md](adapters/claude-code-fable.md). The deterministic builder derives `remediation-handoff.json` and `PR_REMEDIATION_CONTRACT.md` from the validated canonical audit.

The remediation contract has one primary mission and two mandatory convergence addenda. **Primary:** resolve every freshness-valid mutation-eligible audit finding at its root cause. **Additionally:** resolve current codebase-owned CI failures on the affected PRs and disposition/resolve every current unresolved code-review thread regardless of author. Re-query both after publication because new CI failures or review threads may appear on the repaired head. The contract sets `MERGE=False`: converge the PRs to audit-closed, CI-resolved, review-resolved, merge-ready state and stop before merge.

The handoff must also require exact-head freshness, dependency order, strict write allowlists, preservation obligations, provenance-bound validation, and SSOT publication. After required validation passes, publication to the existing affected PR branch must use the canonical SSOT Makefile `make pr` path; if that SSOT path cannot be proven, publication is blocked. Never substitute target-repository Makefiles, raw `gh pr`, replacement PRs, merge, deployment, or scope expansion.

## Completion

The audit is handoff-complete only when:

- target/inspection coverage and excluded surfaces are explicit;
- material authority sources and conflicts are resolved or explicitly Unknown;
- every selected PR is bound to its exact audited source head and exact changed-file inventory;
- every changed artifact plus every authoritative/implementation/coupled surface supporting a material conclusion is recorded in the exact-revision inspection inventory;
- intent provenance is explicit, including original PR prompt availability and use when available;
- every active objective has objective-closure disposition;
- every changed surface has scope-fidelity disposition;
- every machine changed symbol is preserved from the bound deterministic ledger and linked to a `CHANGED_SYMBOL` obligation and claim;
- every machine-seeded material claim and falsification probe is present unchanged, and every material `SUPPORTED` claim survives all applicable attacks;
- complexity delta, architectural economy, supersession closure, failure-path coverage, and test discrimination are explicitly disposed;
- every deterministic-closure seed is preserved from the bound ledger and semantically closed: public-contract preservation, per-candidate SSOT uniqueness, graph-backed bypass paths, per-reference supersession liveness, changed failure edges, config precedence, dependency causal/pair closure, every material diff hunk, generated provenance, CI causality, root-cause dominance, severity consistency, reverse validation-to-claim coverage, and architecture-economy proof;
- the audit obligation ledger covers every changed surface, every machine changed symbol, active objective, detected architecture-growth candidate, material supersession/failure/test obligation, producer/consumer candidate, executable mutation candidate, every current review thread, orphan-artifact reachability candidate, in-scope CI failure, and unresolved review thread;
- the recursive pass ledger contains a discovery pass and final verification pass; final verification re-observes every retained finding, obligation, material claim, and falsification probe and discovers zero new material information before `CONVERGED`;
- required-check identity, mandatory validation, review-thread coverage, and unresolved-thread count carry claim-specific evidence and fail readiness closed when unresolved;
- every remediation-relevant finding has authority, evidence, owner axes, a resolved mutation guard, root-cause state, exact closure target, provenance-bound validation, and evidence-backed surfaces;
- executed validation identifies the revision actually tested and the property discriminated;
- preservation and anti-bypass obligations are explicit;
- cross-PR relationships and merge order are complete when multiple PRs are selected;
- residual Unknowns identify what they block and the evidence needed to resolve them;
- dependency ordering is acyclic/resolvable for mutation-enabled work;
- `executive_verdict` distinguishes audit status, readiness, convergence, and exactly one minimum safe next action;
- canonical `audit.json` passes schema plus semantic validation;
- derived handoff and manifest pass their schemas;
- ZIP manifest hashes bind the canonical audit, bound change-ledger set, schemas, builder bytes, and packaged bytes; deterministic projections and machine census bindings are re-derived/rechecked during verification.

If a PR head moves before completion, that PR audit is stale. Rebind and re-audit it rather than quietly carrying findings forward.

## Hard prohibitions

- Never modify the audited repository or PRs during the audit phase. `autoremediate=0` is the default and stops after bundle generation.
- Never fabricate repository, CI, test, measurement, review, runtime, or mergeability evidence.
- Never claim whole-target coverage without explicit `audit_coverage` proof.
- Never treat a pointer/index as semantic authority when it names a stronger resolvable owner.
- Never collapse source head and tested revision unless evidence proves identity.
- Never retain a conclusion-only finding.
- Never mark required checks/review coverage complete without evidence.
- Never use a green check as proof for properties it did not discriminate.
- Never treat file existence as proof of discovery, registration, enforcement, or runtime reachability.
- Never hide gate weakening, skipped tests, exclusions, suppressions, or dependency drift behind a green verdict.
- Never copy secret values into audit evidence or downstream prompts.
- Never expose a Fable write path without confirmed evidence that discriminates `implementation_surface` and a resolved mutation guard.
- Never expose mutation authority for Probable/Possible/Unknown findings, inferred/unknown root causes, dependency-order blockers, or non-CODEBASE owner classes.
- Never let Fable self-expand `write_surfaces`.
- Never execute or instruct Fable to execute a closing validation command without its declared execution kind, authority ID, and confirmed `validation_procedure` evidence.
- Never omit or rewrite a machine-seeded changed symbol, claim, or falsification probe.
- Never mark a material claim `SUPPORTED` when any applicable falsification probe is `FALSIFIED` or `INCONCLUSIVE`.
- Never use LLM judgment as a substitute for available deterministic/static/executable proof; judgment-required probes must explain why semantic interpretation is necessary.
- Never prescribe one implementation when multiple valid implementations satisfy the same closure condition.
- Never depend on `l9-pr-digest` or `l9-pr-remediation` at runtime to make this audit complete; donor intelligence must be compiled into this pack.
- Never declare audit convergence while the obligation ledger contains undisposed or unrepresented `UNKNOWN` work.
- Never use diff size, file count, or the mere presence of a new abstraction as proof of overengineering; require objective/owner evidence.
- Never claim a repository-wide uniqueness/bypass/supersession/config result from `repository_files` unless `repository_files_complete: true` is bound in the normalized census input.
- Never mark generated output `PROVEN` without generator/source/command/owner provenance plus byte-identical regeneration against the audited generated bytes.
- Never mark unpaired manifest/lock movement aligned without explicit pair disposition; intentional unpaired movement requires discriminating evidence.

## Exemplary validation

The exemplary intelligence pipeline is `parse_source -> extract_expertise -> compress_expertise -> design_skill -> run_exemplary_gate -> package`. Its artifacts are `expertise_model.yaml` and `skill_intelligence_report.yaml`.

Before packaging this skill, run:

```bash
find <skill-root> -type d -name __pycache__ -prune -exec rm -rf {} +
find <skill-root> -type f -name '*.pyc' -delete
PYTHONDONTWRITEBYTECODE=1 python scripts/self_test.py
PYTHONDONTWRITEBYTECODE=1 python <l9-skill-compiler>/scripts/validate_exemplary_skill.py <skill-root>
test -z "$(find <skill-root> \( -type d -name __pycache__ -o -type f -name '*.pyc' \) -print -quit)"
```

The pack is subject to [references/enforcement-gates.md](references/enforcement-gates.md). Do not claim exemplary when deterministic validation is unavailable or failing.

## After-use improvement

Only when the user reports a bad run or requests iteration, capture: missed trigger, false trigger, stale evidence escape, ownership misclassification, unresolved review signal, unproven readiness input, scope-expansion attempt, closure validation that failed to discriminate, or manual bundle repair. Update the smallest rule, schema, adapter, or deterministic validator that would prevent recurrence. Do not invent telemetry or grow the skill from hypothetical edge cases.

### v2.0 deterministic closures

- For every changed public contract, require complete producer/consumer census when repository coverage is complete; every discovered consumer receives an explicit compatibility/migration disposition.
- For exact Python mutation candidates, run `scripts/execute_mutation_probe.py` only against its disposable temporary copy using an authorized project test command. Default execution is argv-based with no shell; shell operators require explicit `--allow-shell` authorization. The runner is filesystem isolation, not a process sandbox. Its output must validate against `schemas/mutation-probe-result.schema.json`; exit `0` means `KILLED`, `1` means `SURVIVED`, `2` means baseline/execution failure, and `3` means audited-source integrity failure. Never edit the audited repository in place. A strong `DISCRIMINATING` test claim cannot survive an applicable surviving/unexecuted mutation.
- Enumerate every current code-review thread and require semantic closure; UI resolved state is evidence, not semantic disposition.
- Enumerate every newly added non-test executable/config/schema/workflow artifact and prove reachability, registration, or explicitly authorized future contract; otherwise emit an orphan finding.
- Treat incomplete repository corpus, failed mutation baseline, mutation execution error, unresolved semantic review disposition, or unproven artifact reachability as `UNKNOWN`; do not convert absence of evidence into closure.
