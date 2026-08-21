---
name: Plan
overview: Merge the two overlapping audit-findings documents into one deduplicated, correctly-prioritized backlog, and remediate it in dependency order — starting with a confirmed critical, live-traffic-breaking bug that only one of the two documents caught.
todos:
  - id: phase0-ledger
    content: "Phase 0: correct the finding ledger — close AUD-003 as false positive, record DWA split-verdict over PRD-001, collapse 3-way/2-way duplicates, file schema-enum and audit-pack-scope notes externally"
    status: completed
  - id: phase1-ci-tests
    content: "Phase 1: add eslint.config.js, minimal Vitest suite (BudgetTracker.evaluateTask, L9LLMRouter.route), wire npm test + npm run lint into ci.yml and publish.yml"
    status: completed
  - id: phase2-critical-bug
    content: "Phase 2: regression test + fix getDowngradedModel() family-branching and remove the as-any cast in execute()'s Perplexity branch (ICA-002/ICA-003)"
    status: completed
  - id: phase3-pricing
    content: "Phase 3: extract single canonical pricing table consumed by openrouter.ts and general-matrix.ts, add drift-guard test"
    status: completed
  - id: phase4-dead-wiring
    content: "Phase 4: implement disableSearch branch, add checkSurge/resetGlobalMonthly wrappers, implement real CircuitBreaker, remove RoutingResult, fix swallowed fallback errors"
    status: completed
  - id: phase5-security
    content: "Phase 5: vision URL allowlist (SEC-001), zod runtime validation (SEC-002), error-class redaction note (SEC-003), npm audit CI step (SEC-004)"
    status: completed
  - id: phase6-contract-docs
    content: "Phase 6: add ARCHITECTURE.md + ESLint no-restricted-imports rule for router-only-egress (RAA-003)"
    status: completed
  - id: phase7-rebaseline
    content: "Phase 7: re-run audits against new base_ref to establish first real prior-baseline"
    status: completed
isProject: false
---

# LLM-Router Unified Remediation Strategy

## Why a merge is needed first

`consolidated-findings-plan.md` (`PRD-*`, `ICA-*`) and `consolidated-findings-remediation-plan.md` (`AUD-*`, `SEC-*`, `RAA-*`, `DWA-*`) both audit the same commit (`87075d82...`) but were produced independently and never cross-referenced. Result: 25 raw finding IDs but only ~18 distinct defects, one critical false negative in doc2, and one confirmed false positive in doc2. Executing either document's phase plan in isolation is sub-optimal — doc1's plan never sees `SEC-*`/`DWA-002`/`DWA-003`/`AUD-005`, and doc2's plan never sees the release-blocking `ICA-002`/`ICA-003` bug at all.

All source claims below were verified directly against `src/*.ts`, `package.json`, and `.github/workflows/*.yml` — not just read from the audit docs.

## Unified, deduplicated backlog (severity-ranked)

- **CRITICAL — blocks release.** `ICA-002` + `ICA-003` combined: [src/index.ts](src/index.ts) `getDowngradedModel()` (lines 328-346) ignores model family and always returns a `GeneralModel`; the `Provider.PERPLEXITY` branch of `execute()` (line 137: `config.model = decision.model as any;`) then casts that wrong-family value into `PerplexityConfig.model`, which can send an invalid `model` string to Perplexity's live API on any hard-throttled search task. **Present only in doc1 — missing from doc2 entirely.**
- **HIGH — blocks release.** `PRD-002` = `AUD-001` = `RAA-001` (3-way duplicate): no `eslint.config.js` exists, no `tests/` directory exists, and neither `.github/workflows/ci.yml` nor `publish.yml` runs `npm test` or `npm run lint` — so a broken build or behavioral regression can merge and publish undetected.
- **MEDIUM.** `PRD-003` = `AUD-002` = `RAA-002` (3-way duplicate): [src/providers/openrouter.ts](src/providers/openrouter.ts) `COST_PER_1M` and [src/matrices/general-matrix.ts](src/matrices/general-matrix.ts) `MODEL_COST_PER_1K_OUTPUT` are independently-maintained pricing tables for the same `GeneralModel` enum — no shared source of truth, silent-drift risk corrupts budget enforcement.
- **MEDIUM.** `ICA-001` = `DWA-001` (2-way duplicate): [src/matrices/perplexity-matrix.ts](src/matrices/perplexity-matrix.ts) computes `disableSearch` correctly, but [src/providers/perplexity.ts](src/providers/perplexity.ts) (lines 65-68) has an empty `if (!config.disableSearch) { }` block — `web_search_options` is attached unconditionally, so non-search tasks still pay for and receive search grounding.
- **MEDIUM — candidate CWE-918.** `SEC-001`: `OpenRouterClient.completeWithVision()` forwards caller-supplied image URLs with no scheme/host allowlist (SSRF candidate).
- **LOW, split-verdict (adopting the more specific `DWA-*` verdicts over `PRD-001`'s bundled framing).**
  - `PRD-001` + `DWA-004`: remove `RoutingResult` from [src/types.ts](src/types.ts) (line 200) — confirmed zero producers/consumers, `RoutingDecision` already supersedes it.
  - `PRD-001` + `DWA-005`: implement a real `CircuitBreaker` class backing `CircuitBreakerState` (line 294) — confirmed zero producers/consumers today; high leverage because it also closes `AUD-005`'s gap (see below).
- **LOW.** `AUD-005`: [src/providers/openrouter.ts](src/providers/openrouter.ts) `completeWithFallback()` (line 206-208) swallows per-attempt errors (`catch { continue; }`) — only the final aggregated error surfaces.
- **LOW.** `DWA-002`: `BudgetTracker.checkSurgeAllowance()` is fully implemented but unreachable — `L9LLMRouter.budget` is private and no wrapper method exists, and nothing internal calls it either.
- **LOW.** `DWA-003`: `BudgetTracker.resetGlobalMonthly()` has no `L9LLMRouter` wrapper (unlike `resetDaily`/`resetWeekly`/`resetMonthly`), so the global hard ceiling can't be reset without a process restart.
- **LOW — CWE-20.** `SEC-002`: `zod` is a declared dependency but never imported anywhere in `src/` — `TaskDescriptor`/`RouterConfig` have zero runtime validation.
- **LOW — CWE-209.** `SEC-003`: `PerplexityError`/`OpenRouterError` attach the full config object as a public property — no secret today, but no guard against a future field addition leaking via generic error logging.
- **LOW.** `SEC-004`: no `npm audit`/SCA step in CI despite floating caret-range dependencies.
- **LOW, process/doc only.** `RAA-003`: no `ARCHITECTURE.md` or lint rule enforcing "only `index.ts` may import `providers/*`" — currently holds by accident, not by enforcement.
- **Close immediately, no remediation needed.**
  - `AUD-003`: **false positive** — `BudgetExhaustedError` is directly confirmed declared and exported at `src/index.ts:353-362`. Doc2's own unknowns section admits this was from a truncated read.
  - `SEC-005`: already resolved/positive (`persist-credentials: false`, scoped permissions) — preserve, do not regress.
  - `AUD-004` + `RAA-004`: audit-pack/preset scope-mismatch notes — no code action in this repo, forward to audit-pack maintainers.
  - Schema gap (`PRD_`/`RAA_` prefixes not in the canonical `audit_source` enum) — both docs flag this identically; it's a schema-registry decision outside this repo, log once and move on.

## Recommended execution sequence

1. **Phase 0 — Ledger correction (no code changes).** Close `AUD-003` as resolved/false-positive; record the `PRD-001`→`DWA-004`/`DWA-005` split-verdict decision; collapse the 3-way and 2-way duplicates into single tracked items; file the schema-enum gap and `AUD-004`/`RAA-004` notes as external/process items so they stop appearing in every future audit re-run.
2. **Phase 1 — Testing & CI safety net** (closes `PRD-002`/`AUD-001`/`RAA-001`). Add `eslint.config.js` (flat config, ESLint v9), stand up a minimal-but-real Vitest suite (`BudgetTracker.evaluateTask`, `L9LLMRouter.route`), and wire `npm test` + `npm run lint` into both `ci.yml` and `publish.yml`. This must land first because every fix below needs to be provably tested, not asserted.
3. **Phase 2 — Fix the critical live-traffic bug** (closes `ICA-002`+`ICA-003`). Write a failing regression test first (hard-throttled `SonarModel`-family task must downgrade within-family), then fix `getDowngradedModel()` to branch on provider/model-family, then remove the `as any` cast in the `Provider.PERPLEXITY` branch of `execute()`. Highest real-world risk item in the entire backlog — sequence immediately after the test gate exists, ahead of all medium/low items.
4. **Phase 3 — Pricing authority consolidation** (closes `PRD-003`/`AUD-002`/`RAA-002`). Extract one canonical `src/pricing.ts` (or `src/pricing/model-costs.ts`) pricing table; have both `openrouter.ts::calculateCost()` and `general-matrix.ts::estimateGeneralCost()` consume it; add a drift-guard test.
5. **Phase 4 — Dead-wiring activation & cleanup.** `ICA-001`/`DWA-001` (implement the `disableSearch` branch to omit `web_search_options`), `DWA-002` (add `L9LLMRouter.checkSurge()` wrapper), `DWA-003` (add `resetGlobalMonthly()` wrapper), `DWA-005` (implement a real `CircuitBreaker` class, wire into `execute()` before each provider call), `DWA-004` (remove `RoutingResult`), `AUD-005` (accumulate per-attempt fallback errors instead of discarding them).
6. **Phase 5 — Security hardening.** `SEC-001` (scheme/host allowlist for vision image URLs), `SEC-002` (zod schemas for `TaskDescriptor`/`RouterConfig`, validated at `execute()`/constructor entry), `SEC-003` (defensive comment or `toJSON()` redaction on error classes), `SEC-004` (`npm audit --audit-level=high` step in CI).
7. **Phase 6 — Contract documentation.** `RAA-003`: add `ARCHITECTURE.md` codifying router-only-egress plus an ESLint `no-restricted-imports` rule enforcing it.
8. **Phase 7 — Re-baseline.** Once Phases 1-6 land, capture the new commit SHA and re-run the audits against it to produce the first real prior-baseline for future follow-up audits — closing the process gap both original audit 05 and this consolidation identified (no real baseline existed before now).

## Sequencing rationale

Phase 1 must be first because Phases 2-6 are otherwise unverifiable. Phase 2 comes immediately after because it is the only `critical`/release-blocking defect and the only finding a live production incident could trace back to today. Phase 3 precedes Phase 4 because the circuit breaker and surge-allowance activations in Phase 4 both reason about cost/spend data that Phase 3 makes authoritative. Phase 5 is independent of Phases 2-4 and could run in parallel once Phase 1's scaffold exists. Phase 6 is pure documentation/lint-rule work with no functional dependency. Phase 7 requires Phases 1-6 complete to have a real baseline.
