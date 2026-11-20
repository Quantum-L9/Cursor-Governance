# CodeRabbit activation and paid-value closure (mandatory bounded lane)

> **v1.7.1 (2026-11-20):** the SHAs and pull-request states in this file are the 2026-11-19 snapshot. `09_EXECUTION_BINDING.md` holds the live recheck and outranks any conflicting sentence here.

Status: campaign execution input, NOT proof of a subscription, live installation, paid entitlement, or executed review. Source snapshot: 2026-11-19. Vendor behavior must be rechecked against live settings at execution.

## Why this lane exists

CodeRabbit is a hosted PR-review application, NOT a Core/SDK scanner provider to be moved into the unprivileged required CI job. Core/SDK may consume verified review observations through existing evidence routes if an authorized integration exists. CodeRabbit native app installation, licensing, per-repo activation and AI review settings belong to CodeRabbit and the applicable GitHub organization/account. The centrally rendered CodeRabbit YAML is already governed by `Quantum-L9/.github` ADR-0020; do not add a second central policy owner, or try to implement CodeRabbit reviews inside SDK.

## Verified repository findings (read-only snapshot)

| Target | Observation | Exact source or PR |
| --- | --- | --- |
| Quantum-L9/.github | Central `.coderabbit.yaml`, `ops/render-coderabbit.js`, and accepted ADR-0020 exist. ADR prescribes `Quantum-L9/coderabbit` as org-level vendor config and says creation/installation are operator tasks. | `.github@c788b991f2ed5f670a2d5660a7faa4e1d52f64e3`, `.coderabbit.yaml`, `docs/adr/0020-coderabbit-central-config-seeded.md` |
| Quantum-L9/coderabbit | Not retrievable through current GitHub connection; absence vs private/inaccessible is UNKNOWN. | GitHub repository/file lookup (2026-11-19) |
| Quantum-L9/Cursor-Governance | No `.coderabbit.yaml` in main tree. CodeRabbit comment was not seen on sampled PRs #1062 or #1067; two PRs do not prove fleet-wide absence. | `Cursor-Governance@263216c13b5b4cac07f627675fb4f231e08317c8`, PR #1062/#1067 reviews/comments |
| Quantum-L9/Enrichment.Inference.Engine | `.coderabbit.yaml` exists, auto review enabled, no `inheritance: true`, and `reviews.path_filters` explicitly excludes `docs/**`; PR #364 sampled without CodeRabbit actor. | `EIE@29d4eb54942e446a9ac917d2ebe2d9733a4e7aec` root config |
| Quantum-L9/Cognitive.Engine.Graphs | `.coderabbit.yaml` exists with custom instructions but no inheritance; live activation UNKNOWN. | `CEG@90a9863709537e4087646abf13d50830956df276` root config |
| Quantum-L9/l9-repo-template | `.coderabbit.yaml` exists with no inheritance; template-born repos can skip central defaults. | `l9-repo-template@093ed4e9150fd47d3ba5c33b123dd77407cd2d66` root config |
| cryptoxdog/IB-Odoo_19 | Substantial config exists on Staging, no inheritance. Auto-review enabled in YAML, but bot on PR #556 says automatic reviews withheld because repository has fewer than 10 stars; manual trigger is offered. `enable_free_tier: true` is present. | `IB-Odoo_19@0626d9493c877e5785ed7610c52d224fd7b738e6` `.coderabbit.yaml`, PR #556 issuecomment 7027149995 |

The `cryptoxdog` GitHub owner is separate from Quantum-L9. Neither a Quantum-L9 subscription nor Quantum-L9/coderabbit defaults can be assumed to cover it. Do not infer that `enable_free_tier: true` overrides a paid entitlement or proves one.

## Preflight and trust boundaries

1. Login to https://app.coderabbit.ai and select the exact intended organization. Inspect Subscription and Billing: current plan, active status, paying entity, assigned seats, seat cap, included PR reviews, pay-as-you-go setting, and any overage cap. If CodeRabbit is paid, identify which GitHub owner and PR authors actually receive that entitlement. No purchase or automatic usage-billing change.
2. Inspect the GitHub App installation for `Quantum-L9` and separately `cryptoxdog` as needed: installed owner, accessible repositories, repository-scoped permissions, webhook health and CodeRabbit dashboard enabled toggle. Record evidence without tokens or private account data. If missing, report the precise operator authorization needed. GitHub source read access DOES NOT imply GitHub App admin access.
3. Inspect dashboard organization defaults, repository settings, auto-review triggers, default and nondefault base branches, skipped review reasons, plan-specific features, relevant integrations and learned rules. Determine which settings are overridden by repository YAML. Do not claim UI changes were made without a saved-settings receipt.
4. Verify whether `Quantum-L9/coderabbit` actually exists and CodeRabbit is installed on it. If missing, propose or create only with the correct organization owner's authorization. Its central `.coderabbit.yaml` should come from the existing `Quantum-L9/.github` renderer/ADR-0020, not from a new independently invented config. Do not replace existing product instructions wholesale.
5. Choose a safe effective configuration hierarchy: central defaults; product-level exceptions with `inheritance: true` where needed; no routine per-repo file for projects that have no specialty. The known local YAML files for EIE, CEG, Odoo and repo-template presently lack inheritance; fix by source-owned PR only when the actual central parent exists and the effective merge is proven. Reconcile EIE's `docs/**` exclusion with review requirements and ADR-0020. Avoid blanket policy that forces CodeRabbit to duplicate Semgrep or excludes tests/docs.
6. Ask the vendor for any unverified entitlement, review auto-trigger restriction, or access issue only when local authenticated evidence cannot resolve it. Odoo #556 and the vendor FAQ both establish the less-than-10-stars automatic review limitation for the observed path; do not guess that YAML can override it. Manual `Trigger review` / `@coderabbitai review` is a fallback, not successful automated coverage.

## Actual acceptance, not config theater

A. **Organization setup:** authenticated billing/plan and app installation evidence, identity and settings context (Quantum-L9 vs cryptoxdog), no accidental new paid feature, effective central YAML source, inherited settings resolved.

B. **Cursor canary:** on a safe eligible Cursor-Governance PR at its exact head, CodeRabbit must perform a real review, or return an explicit vendor entitlement/access blocker with recorded evidence. Use official `@coderabbitai configuration` on a PR to report the effective source. Preserve CodeQL and Core required-workflow checks. Do NOT count CodeRabbit as a required Core provider until a separate authority-backed gate is admitted.

C. **Specialized consumer:** on one EIE or CEG PR, verify local domain instructions and inherited central exclusions both take effect. Prove docs/tests remain reviewable. Do not flatten product-specific knowledge into a general global prompt.

D. **Odoo:** reconcile free/paid review restriction, GitHub owner, PR base branch and manual/automatic triggers on Staging. A status comment stating auto-review skipped is a failure of automatic-review coverage, not a completed code review. Do not assume `cryptoxdog` is bound to Quantum-L9 organization config.

E. **Value:** measure PRs eligible, PRs actually reviewed, code files reviewed, accepted unique correctness/security findings, false positives, ignored comments, time-to-review, seats/credits consumed, and actual cost. Distinguish human-readable summary from substantive review. Compare to CodeQL/Semgrep/Sonar overlaps, and reject extra spend without incremental value.

F. **Delivery:** published source-owner PRs for validated YAML and renderer/seed correction, precise vendor UI steps or evidence where this runtime cannot access the dashboard, and one closure table per owner with outcomes `verified_active`, `config_corrected_pending_live_review`, `blocked_external_account`, `not_applicable`, `declined`, or `unknown`. No false 'installed means used' conclusion.

## Relevant official references

- https://docs.coderabbit.ai/configuration/central
- https://docs.coderabbit.ai/configuration/inheritance-and-merging
- https://docs.coderabbit.ai/reference/configuration
- https://kb.coderabbit.ai/articles/1442026547-troubleshoot-why-coderabbit-reviews-might-not-trigger
- https://kb.coderabbit.ai/articles/8856795235-how-do-i-activate-coderabbit-pro-for-my-open-source-project
- https://www.coderabbit.ai/pricing
- https://github.com/Quantum-L9/.github/blob/main/docs/adr/0020-coderabbit-central-config-seeded.md
- https://github.com/cryptoxdog/IB-Odoo_19/pull/556#issuecomment-7027149995

## Explicit exclusions

No new CodeRabbit subscription, Enterprise-only org-wide override, seat purchase, webhook secret disclosure, vendor credentials embedded in repo, auto-commit from AI reviewer, independent governance authority, or blanket review-required branch protection merely to prove integration. Any future normative CodeRabbit gate must be separately justified against cost, failure semantics and true service reliability.
