# Architecture Decision Records: exact placement and admission handoff

**Status:** Three **proposed** source-owner ADRs. They are fully authored candidate artifacts, not live owner decisions or global law. The execution agent may not select replacement architecture arbitrarily.

## The architecture that is being recorded

**Policy/control travels down:** organization required-workflow rulesets select eligible repositories and branches; Core owns workflow invocation, pins, modes, permissions and enforcement; SDK implements supported capability detection, provider execution, native-report import and technical evidence; consumers supply product-native facts, constraints, tests, and domain semantics, not weaker organization settings.

**Evidence travels up:** individual provider execution facts -> SDK canonical evidence, explicit unknowns and technical gate -> Core required check/controlled publication -> `l9-assurance` final organization policy verdict only where independently integrated and authorized. Native CodeQL and SaaS services can publish from separate least-privileged workflows without Core impersonating native execution. Rulepack packaging never transfers product semantic ownership.

## Frozen decision inventory

| Owner | Proposed exact path | Main decisions | Scoped invariants |
|---|---|---|---|
| `Quantum-L9/l9-ci-core` | `docs/adr/0001-top-down-ci-control-and-runtime-inheritance.md` | One central control plane, runtime-inherited scanner defaults, complete required provider/language accounting, no consumer override | Core 001/002/003/006 |
| `Quantum-L9/l9-ci-core` | `docs/adr/0002-governed-promotion-native-provider-boundaries-and-cost.md` | Pin/canary/parity promotion, preserve native CodeQL/SaaS privileges, justify tool cost/unique value, upstream rollback | Core 004/005/006 |
| `Quantum-L9/l9-ci-sdk` | `docs/adr/0020-all-applicable-capabilities-and-lossless-provider-evidence.md` | Deterministic all-capability discovery, separate applicability/coverage states, monotonic digest-locked rulepacks, no loss of specialty findings | SDK 001..005 |

Candidate source files are under `candidates/adr/<owner>/docs/adr/`. Core's minimal new `docs/adr/README.md` is included; SDK's **existing** `docs/adr/README.md` receives the exact additive `candidates/sdk-adr-index.patch`. All IDs and filenames are provisional until current target-head collision checks are completed; the decisions and owner scopes are not provisional preferences.

## Already accepted sources, do not supersede by accident

- `.github@c788b991f2ed5f670a2d5660a7faa4e1d52f64e3`: registered canonical `semantics/invariants.yaml` and existing `ADR-010-ownership-boundaries-no-recipes`. No CI implementation recipe is to be added as a second global semantic ledger merely to gain visibility.
- Core `.l9/architecture.yaml`, `.l9/ownership.yaml`, `.l9/governance-contract.yaml`, `.l9/release-plane.yaml` at `3579bdc19a7f36973e4f0fe516ea5aa6c5ab9437`: existing GitHub rulesets -> Core -> SDK boundary and Core-owned release; new Core ADRs *strengthen this*, not create a second owner.
- SDK existing ADR 0005, 0009, 0015, 0016, 0017, 0018, 0019 and `.l9/integration-contract.yaml` at `ab8a25543bf99de4c932f1930841a1e5f2ef2f27`: preserve the Provider SPI, source precision, centralized rollout and Core tool-version authority. A new provider requires separate SPI and validation; current Core-owned Biome is not automatically relocated.
- Cursor-Governance CodeQL PR #1067 is already merged. Protect default-suite PR and security-extended nightly behavior; do not redo it. Treat CodeQL's native workflow owner as existing source reality.

## Mandatory implementation and admission order

**v1.3.0 source-owner clarification:** Core ADR 0001 explicitly makes
Cursor-Governance the first mandatory real consumer acceptance, and SDK
ADR 0020 explicitly requires evidence-based *targeted* harvesting and
capability-scoped specialization. New supporting documents `HARVEST.md` and
`CURSOR_CANARY.md` are normative campaign acceptance requirements, not
independently admitted organization policy.

1. Re-resolve exact current `.github`, Core, SDK, consumer heads, existing ADR filenames and open PRs at execution time. Preserve any new accepted ADRs; renumber a proposal only if unavoidable due to a proven collision, with link reconciliation.
2. Publish the Core and SDK ADR candidates at the exact owner paths **alongside** the relevant domain-contract invariant candidate PRs, or explicitly staged predecessor PRs if required by the repository's merge process. Each PR must name what remains proposed versus admitted. Do not claim an ADR is accepted until the owning decision/PR gate does so.
3. Check every ADR decision against upstream existing law and its target-owned schema. Use `INVARIANTS.yaml` as frozen same-meaning wording. Resolve schema errors by the minimal authorized owner change, not by inventing a parallel global semantics system.
4. Implement detector, provider, governance, coverage and promotion changes using the existing SPI, runtime, toolchain lock, rulepack registry and ABI. Run known-bad/known-good tests. Check native CodeQL/Sonar/GitHub permissions and exact publisher identities.
5. Before shared config/rule migration, complete targeted cross-tool harvest
   per `HARVEST.md`, route each delta to its existing upstream owner and record
   delivery/effective config proof; do not deep-harvest all fleet repos.
6. After owner promotion, **first** perform the real `Cursor-Governance` canary
   per `CURSOR_CANARY.md`. Keep local checks until parity. A synthetic/SDK-only
   test cannot unlock rollout. **Then** run EIE, CEG and Odoo secondary
   canaries; only after both stages may the eligible fleet be rolled out.
   Record exact runs, stalled promotions, blocked entitlements and dispositions.

## Explicit rejects

No new `.github` global invariant or implementation ADR when existing global law covers the concern. No second CI control plane or distribution of copied Core/SDK required workflows/configs. No consumer-selected Core/SDK enforcement, versions, or requiredness. Preserve existing native thin callers, SHA pins, project bindings and governed CodeRabbit/Dependabot source generators; changing these contracts requires an explicitly admitted compatible successor. No all-at-once rollout. No secret promotion into untrusted PR execution. No blind CodeQL reimplementation. No paid feature purchases or billing changes without authorization. No removal of product tests or special rules without parity evidence.

## Source boundary

This is a bounded expression of decisions supported by the visible campaign discussion, supplied campaign v1.1.0, and inspected repository source files. It is **not** an independent full-transcript reconstruction, verified L9 AuthorityResolution receipt, admitted ADR set, or proof that any repository has changed.
