# Selective consumer configuration and rule harvest

> **v1.7.1 (2026-11-20):** the SHAs and pull-request states in this file are the 2026-11-19 snapshot. `09_EXECUTION_BINDING.md` holds the live recheck and outranks any conflicting sentence here.

**Decision:** Harvest reusable CI configuration and rule deltas from known customized consumers, then deliver approved deltas to their existing upstream owners. Begin with a lightweight census; deep-inspect genuine customizations, not every repository. A donor inventory or SDK-only rule list does not complete this work.

**Scope:** Customer/consumer configs here means CI, scanner, review and coverage configuration in authorized in-scope repositories. Product behavior, customer production settings and business data are outside this harvest. Promote reusable semantics and sanitized configuration, never credentials, tokens, secret values or customer data. Keep project/account identities and justified local exceptions at their owner. No new global law, repository, configuration language or provider is created by this harvest.

## Source census and initial donors

Observed at the 2026-11-19 source snapshot; rebind exact heads, source paths and open PRs before execution. These are initial donors, not approved promotions or proof that other repos are uncustomized.

| Donor | Known rule inventory | Proposed inspection | Preservation constraint |
|---|---|---|---|
| `Quantum-L9/Enrichment.Inference.Engine` | `.semgrep/semgrep-rules.yaml`: 8 Python IDs | Compare each with CEG and SDK; inspect other configured tools using the owner table | No blind copy of broad exclusions, severity or fragile patterns; preserve justified product settings and good/bad fixtures |
| `Quantum-L9/Cognitive.Engine.Graphs` | Same 8 IDs; `.semgrep/fixtures/` | Compare behavior and precision; include native scanner/coverage deltas and T01/T02/T07 | Same ID is not semantic equivalence; preserve domain tests and distinguish native execution from job success |
| `cryptoxdog/IB-Odoo_19` `Staging` | `.semgrep/odoo-patterns.yml`: 36 rules; PR #553 SQL/taint candidates | Separate generic Python, Odoo 19 and PlasticOS rules; reconcile Sonar #552 and native review config | Prove Odoo applicability; retain PlasticOS bans, naming/migration rules, product identities and separate-owner governance |
| `Quantum-L9/Cursor-Governance` | `.semgrep/l9-pr.yml`: 4 rules; `ops/scripts/run_pr_security.sh` | Evaluate credential-leak candidate; inspect native CodeQL/Sonar and Core/SDK inheritance | Keep memory transport/spawn semantics Cursor-owned; preserve accepted CodeQL owner and PR/nightly split |

## Bounded discovery

1. **Cheap census:** index eligible accessible repositories, custom paths, workflow references and existing central/native config sources. Include Semgrep, Gitleaks/GitGuardian, CodeQL, Sonar, CodeRabbit, Codecov, lint/type tools, Dependabot and observed supply-chain scripts. Record repo, branch, head, path and source/derived relationship. Use the existing G0/account route for missing native settings.
2. **Inspect deltas:** distinguish generated defaults, genuine customization, stale copies and missing/unknown configuration. Deep-inspect the four initial donors and additional material hits. Compare the current upstream baseline before proposing another rule or source. Repeated use does not establish universal applicability.
3. **Bind scope:** identify affected languages, frameworks, products, events, branches and trust contexts. Unresolved behavior, owner, license or sharing right means `defer_unknown`; preserve the working check.
4. **Separate rollout:** a census is not fleet enforcement proof. Core/SDK integration, the real Cursor canary, secondary canaries and per-consumer parity precede rollout or cleanup.

## Existing upstream owners and delivery routes

Resolve the exact live path or native setting key during Stage 0H. Named paths are recorded owner surfaces, not permission to write an uninspected target.

| Configuration family | Authoritative source / upstream destination | Effective consumer and proof |
|---|---|---|
| Semgrep and portable CLI rule/config behavior | Existing SDK rulepack/provider mechanisms, including `l9_ci/rulesets/semgrep`; Core owns selection and requiredness | Pinned config in Core-governed execution; good/bad and non-target witnesses |
| Versions, invocation, schedules, profiles, permissions and enforcement | Existing Core governance, workflows, runtime config and toolchain | Actual required workflow uses admitted revisions/digests; no consumer override |
| Ruff, Biome, Mypy and lint/type defaults | Core versions/orchestration; SDK portable execution only after provider admission. Preserve current Core/repo execution until proven successor | Effective config, file scope and real outcomes; product build/type targets and justified exceptions stay scoped |
| CodeQL suites, shared config and reusable workflow | Existing Cursor-Governance CodeQL owner and caller templates; GitHub native security settings/alerts | Default PR / extended nightly, thin caller SHA pins, native upload and language/suite parity; no SDK relocation |
| Sonar properties, profiles/gates and exclusions | Native Sonar settings retain their owner; property files retain their source owner unless a reusable delta is admitted. Core schedules; product owns source/tests/coverage | Correct project/revision, analysis mode, indexed source, imported coverage and native gate. Project keys and local source roots are not global defaults |
| CodeRabbit defaults and instructions | Existing `Quantum-L9/.github` source and `ops/render-coderabbit.js` under ADR-0020 → derived vendor-facing `Quantum-L9/coderabbit`; product instructions stay local | Source/rendered revision, effective inheritance and real review. Vendor config repo existence/access remains Unknown until verified |
| Gitleaks/GitGuardian rules, allowlists and invocation | Resolve CLI/config owner separately from native account/app owner. Portable rules enter SDK only through admitted mechanisms; Core governs requiredness | Real scans and good/bad execution witnesses; every allowlist has a scoped reason/owner. Auth/incident settings and secret values remain native |
| Codecov flags, upload config and coverage | Product owns tests/artifacts; existing native upload/project owner owns auth/acceptance; Core schedules; SDK may consume supported verified observations | Accepted exact-revision upload, intended flags/file set and digest; no test rerun solely to upload or token harvest |
| Dependabot defaults and managed files | Existing `Quantum-L9/.github` source and `ops/render-dependabot.js` | Regenerate from source; verify ecosystems/ignores/major-version behavior; no competing hand-edited copies or second generator |
| SCA, SBOM, license and other observed checks | Existing semantic policy and implementation owners; admitted SDK providers; Core event/requiredness policy | Actual lockfile/image/source scope, native results and provenance; no blanket promotion or new scanner solely for breadth |

Required native files and thin callers remain where the platform contract requires them. No-routine-copy/no-repin applies to the promoted **Core/SDK required runtime**, not an unimplemented successor to every native integration.

## One evidence row per distinct rule or configuration delta

Use one compact ledger grouped by true source owner; no new runtime schema is required. Each row records:

- **Donor:** repo, branch, head, path/blob SHA or native setting key, observation time and evidence. Keep PR head, evaluated checkout and reusable-workflow revision distinct.
- **Behavior:** rule ID/config selector, old/proposed effective value or behavior, event/trust lane, languages/frameworks/products, scanned paths, exclusions and exceptions.
- **Ownership:** semantic owner, canonical source/generator, derived consumer, exact upstream target repo/path or native key and baseline revision. Unknown destination blocks promotion.
- **Evidence:** upstream comparison; good/bad fixtures for executable behavior; precision/false-positive history when available; non-target witness; effective-config/native receipt for service-owned settings. Do not invent a code fixture for an entitlement.
- **Disposition:** one value below, rationale, affected consumers, dependencies and preservation requirement.
- **Delivery:** owner PR/change reference, admission, promoted release/revision, effective inherited config and native/run receipt, or explicit pending/blocker. Proposed, published, admitted, deployed and observed execution are distinct.
- **Retirement/recovery:** eligible local removals, parity receipt, preceding known-good owner revision/config, rollback scope and rollback validation. A disposition label alone cannot approve deletion.

Missing evidence is `Unknown` with owner and minimum next proof. Never fill pending PRs, canaries or vendor observations with pretend values.

## Classification and admission dispositions

Retain the existing seven reporting dispositions. Applicability is independent of destination; use the owner table.

- `already_satisfied`: current upstream behavior, scope and precision are equivalent; demonstrate effective execution, not matching text.
- `promote_global`: justified organization-wide config/rule behavior at its existing owner. SDK receives suitable rule/provider data, not all native settings. This is not a new global law or automatic blocking promotion.
- `promote_language`: language-general, evidence-backed behavior; SDK language pack where applicable, otherwise correct native source.
- `promote_framework`: framework-scoped behavior with reliable applicability; never a fleet default; preserve semantic ownership.
- `retain_domain`: product/path/account/contract-specific meaning stays at its owner. A centrally invoked versioned derivative requires source lineage and a scoped binding.
- `retire_duplicate`: only after promoted effective successor, Cursor and relevant secondary/per-consumer gates, and good/bad, scope and exclusion parity.
- `defer_unknown`: behavior, owner, precision, license, authorization, effective config or applicability remains unproved. Preserve the working check and record the dependency.

Framework/domain selection requires verified facts or an authorized identity-bound binding. Consumer settings may strengthen but never weaken Core baseline. Do not spread Odoo/PlasticOS/memory restrictions, project IDs, tenant allowlists or broad exclusions across unrelated consumers.

## Upstream delivery and closure

1. Bind donor/upstream revisions, compare effective behavior and dispose each candidate.
2. Deliver to the **existing source owner**: SDK/Lane 1, Core/Lane 2, native owner/Lane 3, or retained product owner. `.github` writes use its already governed sources/generators. Coordinate one writer per repo/file set across these and F1/F2/F3 lanes.
3. Implement and validate an authorized owner change. Publish repository PRs only through that target's verified `make pr`; native settings follow G0 and applicable explicit authorization. Publication neither admits an ADR nor changes an account.
4. Record actual owner admission/promotion and effective merged/runtime config with source identity. Regenerate derived files from their source.
5. Prove promoted Core/SDK on real Cursor first, then EIE/CEG/Odoo as applicable; native changes also need their own receipts. Independent false-green repairs may precede canary without authorizing fleet cleanup.
6. Retire only proven duplicate behavior; retain product source, project bindings, accepted native callers and justified exceptions.
7. Close each row with actual delivery/proof or an owner-bound blocker. Report harvest preparation separately from upstream execution. Required blocked delivery, inheritance or parity keeps the campaign open.

**Required output:** cross-tool disposition/delivery ledger, correctly owned PRs or authorized native change receipts, effective config/run evidence, behavioral witnesses where applicable, and retirement/rollback mapping. Zero routine consumer CI configuration does not mean zero product-owned source or zero native project identity.
