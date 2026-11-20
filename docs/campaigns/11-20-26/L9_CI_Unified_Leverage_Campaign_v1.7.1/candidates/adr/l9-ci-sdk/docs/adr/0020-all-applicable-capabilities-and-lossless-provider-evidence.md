# ADR 0020: All-applicable capability detection and lossless provider evidence

## Status
Proposed. Campaign admission candidate; it is not a production provider or an automatic promotion of existing Semgrep rules.

**Decision owner:** `Quantum-L9/l9-ci-sdk` for factual repository capability detection, provider SPI, scanner rulepack composition, report import, canonical evidence and technical evaluation. **Related:** SDK ADR 0005 (Provider SPI), ADR 0009 (packaged Semgrep rules), ADR 0015/0018/0019 (precision), ADR 0016 (organization-managed CI), ADR 0017 (tool-version selection), `.l9/integration-contract.yaml`; `L9-CI-SDK-001..005`; Core ADRs 0001/0002.

## Context

SDK already exposes multi-language repository facts and one active in-tree Semgrep provider. Core's currently integrated central invocation nevertheless chooses one language, and locally authored framework/product Semgrep packs do not automatically join the central scan. A provider registry without an explicit, complete applicability inventory cannot prove that all relevant analysis ran. Moving rules upstream by name alone can lose unique taint, Odoo XML and product security behavior.

## Decision

1. **Detect facts comprehensively:** for one exact repository snapshot, enumerate every supported applicable language, framework and provider prerequisite using examined source, manifests, lockfiles and recognized framework markers. Do not collapse mixed-language repositories into a primary language. Unsupported or ambiguous signals remain explicit; the SDK does not invent repository class or organization requiredness.
2. **Separate states:** represent capability detection, eligibility, planned execution, invocation, analyzed file scope, exclusions, execution result, parsed findings, and coverage independently. `not_applicable` needs positive evidence of nonapplicability. Missing executables, invalid manifests, parser faults, unsupported language, unscanned required source and skipped execution cannot silently convert to a completed passing scan. SDK emits a factual/technical result, not final `l9-assurance` policy authority.
3. **Compose exact, monotonic rulepacks:** effective config is pinned/versioned SDK global baseline plus applicable language/framework packs and authorized product-specific rules or constrained extensions, bound to executable revision and exact content digests. Product-specific meaning remains with its domain owner; SDK packaging/distribution does not transfer that semantic ownership. A consumer-local ignore or remote registry update must not silently weaken the centrally required baseline. Mutable registry names require independent content pinning/snapshot or explicit unreproducibility status.
4. **Prove safe consolidation:** every specialized rule retired or migrated needs positive known-bad and negative known-good fixtures preserving its intended scope. A rule with the same identifier or similar syntax is not proof of equivalence. Use existing Semgrep rule fixture capabilities, preserve source file/line identities and resolve duplicate IDs deliberately. EIE/CEG shared generic rules and Odoo SQL/taint/XML rules are the first parity test cases.
5. **Normalize without laundering evidence:** preserve native provider/rule identifiers, original source provenance, configuration/ruleset digest, revision, file scope, and failures. Correlating Semgrep/CodeQL/Sonar findings may group evidence but may not erase distinct provider observations or unproven severities. For native tools that require a separate privileged workflow, import/observe their validated native results without claiming SDK initiated the action. SDK's technical gate is not an Assurance verdict.
6. **No opportunistic provider proliferation:** extend the existing SPI only when the provider adds required unique evidence or removes proven duplication, with its own compatibility/proof decision. Existing Core-managed Biome behavior remains the current authority until a separately validated SDK provider is intentionally adopted; this ADR is not an exception to ADR 0017 or authorization to move CodeQL or SaaS credentials into Core's read-only workflow.

## Alternatives considered and rejected

- **One primary repository language:** silently drops scans for mixed applications.
- **Treat no matching findings or process skip as PASS:** confuses unscanned code with safe code.
- **Aggregate arbitrary local `.semgrep` config from consumers:** permits unreviewed changes and baseline weakening.
- **Flatten all rule IDs into one organization pack without provenance and fixtures:** loses product ownership and useful specialized findings.
- **Treat all native vendor results as SDK-executed:** creates false execution and permission claims.

## Consequences and follow-through

- Good: central execution can account for every detected required capability with reproducible rulepacks and truthful coverage.
- Trade-off: some frameworks require an explicit validated detector; unsupported capability remains visible instead of receiving a fake green result. Additional providers require bounded contracts and validation.
- Required realization: update existing SDK `.l9/integration-contract.yaml` and public contracts if changed; implement facts/selection/normalization under the current module boundaries; test source-tree and installed-wheel resource resolution; run SDK public API/compatibility tests and CodeQL/Sonar native provenance fixtures. Core chooses requiredness and enforcement using these facts.
- This **amends in scope**, but does not rewrite, ADR 0005/0016/0017 and the Semgrep precision ADRs; historical accepted decisions remain authoritative where not explicitly superseded.

## Acceptance conditions

**Targeted harvest and scope gate:** Use evidence-bound donor rule inventories
starting with EIE, CEG, Odoo and Cursor. General-purpose, language, framework
and domain rules are separately classified; only genuine reusable rules are
promoted to their applicable SDK pack and selected by verified capability.
Product/path-specific rules retain original domain authority, even when a
versioned derivative is transported to SDK. A filename match or duplicate
rule ID does not establish equivalence or justify fleet-wide application.
Prove Odoo and Cursor memory restrictions do not fire in non-applicable repos.
See campaign `HARVEST.md` for the bounded source-disposition contract.

- Python-only, TypeScript-only, mixed, Odoo Python+XML, unsupported-language and malformed-manifest fixtures produce complete, stable capability inventories and truthful statuses.
- Odoo indirect SQL/taint and EIE/CEG specialized known-bad/known-good witnesses survive versioned pack composition; local weak exclusions cannot silence mandatory baseline checks.
- Hash/config mismatch, network/registry fault, no analyzed source or provider parser failure cannot produce passing required-provider facts.
- Finding correlation preserves each native source ID and report lineage, while no SDK artifact asserts an organization Assurance verdict.
