<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: reference
role: adversarial-red-team
version: 2.0.0
status: active
-->

# Deterministic Red-Team Contract

## Contents

- Purpose
- Machine-owned input
- Changed-symbol ledger
- Claim-validation matrix
- Falsification ledger
- LLM judgment boundary
- Convergence
- Deterministic closure complement

## Purpose

Turn adversarial review from reviewer temperament into a bounded closure system. Machines enumerate the semantic change surface and mandatory attacks. The LLM may judge meaning only where deterministic evidence cannot settle the question. It may add attacks, claims, or symbols, but it may not delete machine-seeded ones.

## Machine-owned input

Run `scripts/build_change_ledger.py` for every audited PR against its exact source head. Bundle construction requires the resulting ledger for every PR and binds its canonical SHA-256 in `deterministic_census_binding`.

The generated ledger owns four pre-judgment inventories:

1. changed artifacts and deterministic audit obligations;
2. `changed_symbols`;
3. `claim_seeds`;
4. `falsification_seeds`.

The bundle contains a canonical `change-ledger.json` set so later verification can prove the audit did not silently drop machine census material.

## Changed-symbol ledger

`changed_symbol_ledger` is the canonical semantic change inventory.

Detection order:

- Python before/after contents available: compare AST class/function/method nodes as `EXACT_STATIC`;
- otherwise: detect named changed symbols from diff lines as `HEURISTIC`;
- when a semantic source/config/schema/workflow file changes but no named symbol can be extracted: emit a `FILE_SCOPE` fallback symbol.

Machine rows use `source: MACHINE`. Auditor-added semantic rows use `source: AUDITOR` and may not masquerade as machine output.

Every machine symbol must:

- appear exactly once;
- remain bound to the PR head that produced it;
- receive scope disposition;
- link active objectives where applicable;
- link canonical evidence;
- link at least one `CHANGED_SYMBOL` claim;
- receive a `CHANGED_SYMBOL` audit obligation;
- link findings when the change is defective or unauthorized.

`SCOPE_EXTENSION` requires a finding. `UNKNOWN` blocks convergence. Machine symbols may not be omitted because the reviewer considers them unimportant.

## Claim-validation matrix

`claim_validation_matrix` is the single claim-to-proof surface for material positive and negative audit conclusions.

Machine seeds cover at minimum:

- each active objective;
- each canonical audit domain for each PR;
- each machine-detected changed symbol;
- each PR readiness conclusion;
- audit convergence for each PR.

The auditor may add material claims discovered during semantic review.

Statuses:

- `SUPPORTED`: the claim has confirmed evidence, claim-specific validation, and all applicable falsification probes survived;
- `REFUTED`: evidence or at least one falsification probe proves the claim false;
- `NOT_APPLICABLE`: the claim genuinely does not apply and its probes are likewise not applicable;
- `UNKNOWN`: available evidence cannot safely decide the claim.

Material claims require evidence that discriminates `claim:<claim_id>`. Supported claims additionally require validation evidence for every declared `validation_properties` item.

The matrix does not become a competing verdict store. Objective claims mirror `objective_closure`; domain claims mirror `domain_assessments`; readiness claims mirror per-PR readiness; convergence claims mirror the executive convergence state; changed-symbol claims mirror the symbol's scope/finding disposition.

## Falsification ledger

`falsification_ledger` records explicit attempts to disprove claims.

Machine-seeded attacks include:

- negative requirement search for objectives;
- counterexample search for audit domains and changed symbols;
- stale-evidence/blocker search for readiness;
- omission search for audit convergence.

The auditor may add stronger probes such as bypass search, mutation testing, failure injection, alternate-owner search, baseline comparison, or cross-PR conflict search.

Results:

- `SURVIVED`: the attack was executed and did not defeat the claim;
- `FALSIFIED`: the attack produced evidence that defeats the claim;
- `INCONCLUSIVE`: the attack could not resolve the hypothesis;
- `NOT_APPLICABLE`: the attack is legitimately irrelevant to the claim.

`SURVIVED` and `FALSIFIED` require confirmed evidence discriminating `falsification:<claim_id>`.

For material claims:

- `SUPPORTED` requires every applicable probe to `SURVIVE`;
- `REFUTED` requires at least one `FALSIFIED` probe;
- `UNKNOWN` requires unresolved/inconclusive evidence and cannot be promoted to PASS;
- `NOT_APPLICABLE` requires all attached probes to be `NOT_APPLICABLE`.

One friendly probe cannot cancel a falsified or inconclusive material attack.

## LLM judgment boundary

Use deterministic/static/executable proof whenever available. Set `judgment_required: true` only when semantic interpretation is genuinely necessary, such as:

- whether an abstraction is justified by the requirement and existing owner;
- whether two apparently separate owners represent the same semantic authority;
- whether a discovered counterexample is materially relevant to the governed behavior;
- whether a direct coupling is necessary rather than accidental scope growth.

Judgment-required probes must use `LLM_JUDGMENT` or `HYBRID`, cite direct evidence, and explain why deterministic closure is insufficient. Static/command/check probes may not claim LLM judgment is necessary.

The model never receives authority to erase a machine seed, weaken a failed attack, or turn `INCONCLUSIVE` into `SURVIVED` by prose.

## Convergence

The final `VERIFICATION` pass must re-observe every retained finding, every audit obligation, every claim, and every falsification probe. `CONVERGED` additionally requires:

- zero new material information in final verification;
- no material `UNKNOWN` claim;
- no material inconclusive probe supporting a positive conclusion;
- exact machine-ledger binding for every audited PR;
- no omitted machine symbol, claim seed, or falsification seed.

Adversarial closure discovers whether the audit's positive conclusions survive attack. It does not create mutation or merge authority.

## Deterministic closure complement

The red-team claim/falsification layer answers whether positive claims survive attack. The v2.0 deterministic-closure layer answers whether enumerable structural obligations were omitted. Use both: falsification does not replace hunk/edge/SSOT/config/dependency/generated closure, and deterministic closure does not replace semantic counterexample judgment.
