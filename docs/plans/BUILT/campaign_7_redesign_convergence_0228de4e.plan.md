---
name: Campaign 7 Redesign Convergence
overview: Convert the Campaign 7 execution contract into a bounded, machine-validatable plan that wires the full REDESIGN_IMPROVE runtime graph in Website-Bot (13 blocking outcomes), then proves it with exactly one real Safe Haven seam run and a RedesignExecutionIntegrityReceipt.
todos:
  - id: todo-00-baseline-preflight
    content: "W0: reverify baseline SHA 3eb3536; probe SEO-Bot endpoints/identity, DataForSEO, secrets resolve, Playwright; record identities for receipt"
    status: completed
  - id: todo-01-intent-binding
    content: "R1/R2: recursive-cli sets build_intent=REDESIGN_IMPROVE; requireBuildIntent() fail-closed (BUILD_INTENT_REQUIRED) on redesign surfaces"
    status: completed
  - id: todo-02-intent-tests
    content: "Intent test matrix A: recursive emits REDESIGN_IMPROVE; undefined cannot become COPY on redesign surfaces; explicit accepted"
    status: completed
  - id: todo-03-mandatory-competitive
    content: "R3: competitive-intelligence added to mandatory stage set under REDESIGN_IMPROVE; COMPETITIVE_INTELLIGENCE_REQUIRED fail-closed"
    status: completed
  - id: todo-04-donor-10-invariant
    content: "R4: hard qualified_donor_count==10 with bounded replacement; COMPETITIVE_EVIDENCE_INCOMPLETE otherwise"
    status: completed
  - id: todo-05-donor-ingestion
    content: "R5: real bounded donor crawl + screenshots per donor (reuse SourceCrawler/ScreenshotCapturer); manifests, digests, DONOR_REFERENCE_ONLY"
    status: completed
  - id: todo-06-donor-tests
    content: "Donor test matrix C: 3/9 fail, 10 pass, excluded replaced, missing crawl/screenshot fail"
    status: completed
  - id: todo-07-seo-blueprint-wiring
    content: "R6: wire real createSEOContentBlueprint with exact CompetitiveLandscape lineage validation"
    status: completed
  - id: todo-08-pcc-wiring
    content: "R7: wire compilePageContentContract on runtime path; page_content_contract_llm_calls==0 instrumentation"
    status: completed
  - id: todo-09-scp-wiring
    content: "R8: wire real createStructuredContent; exact PCC digest lineage; SCP is final prose authority"
    status: completed
  - id: todo-10-legacy-content-bypass
    content: "R9: replace ContentGenerationStage with SCP projection stage under REDESIGN_IMPROVE; legacy_content_generation_calls==0"
    status: completed
  - id: todo-11-deterministic-schema
    content: "R10: RedesignSchemaSerializerStage, zero LLM, determinism proof; redesign_schema_llm_calls==0"
    status: completed
  - id: todo-12-content-chain-tests
    content: "Test matrices D/E/F/G: lineage accept/reject, determinism repeats, bypass counters"
    status: completed
  - id: todo-13-blueprint-visual-requirements
    content: "R11: add visual_requirements surface to WebsiteBuildBlueprintV1 (bot-interop) + lock update + production"
    status: completed
  - id: todo-14-planner-consumes-blueprint
    content: "R11: ImageAssetPlanningStage derives slots from blueprint under REDESIGN_IMPROVE; required_visual_slots_filled==100% gate"
    status: completed
  - id: todo-15-source-asset-corpus
    content: "R12: SourceAssetCorpus + client_owned_authorized reuse policy + SELECTED/REJECTED-with-reason ledger; precedence rules"
    status: completed
  - id: todo-16-visual-asset-tests
    content: "Test matrices H/I: slots resolve, source photo preferred, rejection reasons, donor images excluded"
    status: completed
  - id: todo-17-integrity-receipt
    content: "§16: RedesignExecutionIntegrityReceipt emitter with all identity/intent/donor/lineage/counter/asset/QA fields; missing evidence=FAIL"
    status: completed
  - id: todo-18-fail-closed-tests
    content: §17 impossibility matrix + receipt validation tests (matrix J)
    status: completed
  - id: todo-19-full-validation
    content: "§20 ordered validation: all targeted tests, typecheck, lint, build, verify:all — earlier failure blocks later claims"
    status: completed
  - id: todo-20-safehaven-seam-proof
    content: "R13: exactly ONE real Safe Haven seam run (no mocks/fixtures/seeding); emit + validate receipt"
    status: completed
  - id: todo-21-converge-report
    content: 17-section final report; ship via make pr; final line READY_FOR_REAL_GOLDEN_E2E or DO_NOT_RUN_GOLDEN_E2E
    status: completed
isProject: false
---

# PLAN: Campaign 7 — REDESIGN_IMPROVE Runtime Convergence

> plan_id: `plan.website-bot.campaign7-redesign-convergence.v1` · schema `canonical.schema.plan_document.v1` · depth **deep** · plan_class `bounded_execution_contract` · status **draft** (becomes `executable` after baseline reverify + preflight)
>
> Execute via `@environment/program-execution` + `@autonomy` under a Program lease. Ship via `make pr` (never bare `git push`). No sister-repo mutation (SEO-Bot, LLM-Router → `CROSS_REPOSITORY_BLOCKER` instead).

## Immutable baseline

- Repository: `Quantum-L9/Website-Bot`, branch `main`
- Locked SHA: `3eb3536f2bf3f7aad4500748bf028ccc3038f7c2` (reverify at execution start; on drift → stop_and_replan)
- Tracked tree clean; allowed local dirt: untracked tooling (`.claude/`, `.cursor/`, `.vscode/`, `.biomeignore`, `.editorconfig`, `scripts/claude-deepseek.sh`)
- Identities: `@quantum-l9/llm-router@1.1.2`, `@quantum-l9/bot-interop` = `file:packages/bot-interop`; SEO-Bot bound at runtime via `SEO_BOT_URL`/`SEO_BOT_API_KEY` (no local clone — record endpoint contract version during preflight)
- Work happens on a new feature branch from `origin/main` (e.g. `feat/campaign7-redesign-convergence`)

## Objective

Make REDESIGN_IMPROVE the real product path: `recursive:improve` → REDESIGN_IMPROVE → mandatory competitive intelligence → exactly 10 crawled+screenshotted donors → PatternPortfolio → WebsiteBuildBlueprint → real SEOContentBlueprint → deterministic zero-LLM PageContentContract → real StructuredContentPackage → blueprint-driven visual slots + authorized Safe Haven asset reuse → deterministic schema → rendered visual QA — fail-closed at every edge, with COPY/legacy unreachable from this path. Prove it with one real Safe Haven seam run emitting a `RedesignExecutionIntegrityReceipt`. Do NOT run full Golden E2E.

### Success properties (all blocking)

| id | property | proof |
|----|----------|-------|
| SP-01 | Baseline matches locked SHA at start | `git rev-parse HEAD` |
| SP-02 | `recursive:improve` emits `build_intent: REDESIGN_IMPROVE` before plan construction; undefined redesign intent fails closed (`BUILD_INTENT_REQUIRED`), never COPY | intent tests + run spec evidence |
| SP-03 | Donor invariant: qualified usable donors == 10, each with crawl manifest + screenshot set; 3/9/excluded/no-evidence → `COMPETITIVE_EVIDENCE_INCOMPLETE` | donor test matrix + runtime counts |
| SP-04 | SEOContentBlueprint / PageContentContract / StructuredContentPackage wired with exact lineage; PCC deterministic, `page_content_contract_llm_calls == 0` | lineage + determinism tests, LLM counters |
| SP-05 | Under REDESIGN_IMPROVE: `legacy_content_generation_calls == 0` and `redesign_schema_llm_calls == 0` | instrumentation counters + tests |
| SP-06 | Blueprint visual requirements drive ImageAssetPlanning; `required_visual_slots_filled == 100%`; every reusable Safe Haven asset SELECTED or REJECTED with reason | receipt asset section + tests |
| SP-07 | One real Safe Haven seam run completes; `RedesignExecutionIntegrityReceipt` validates; `REDESIGN_EXECUTION_INTEGRITY = PASS` | receipt artifact |
| SP-08 | Quality gates: tests, typecheck, build, `npm run verify:all`, `make pr` PASS | command output |

## Ground truth (compliance review already completed)

Current main has classes/ports but not the graph. Key bound facts:

- `scripts/recursive/recursive-cli.ts` `writeSourceSpec` copies `fixtures/ci-test-spec.yaml` and never sets `build_intent`
- `src/pipeline/BuildIntent.ts` `parseBuildIntent(undefined) → COPY`; locked in by `tests/unit/build-intent.test.ts`
- `src/pipeline/FactoryExecutionPlan.ts` inserts `CompetitiveIntelligenceStage` only when caller passes the intent; always runs `ContentGenerationStage` + `SchemaGeneratorStage`; competitive stage not in `MANDATORY[mode]`
- `src/stages/CompetitiveIntelligenceStage.ts` accepts any `selected_donors.length > 0` (`slice(0,10)`); no donor crawl/screenshots (LLM nugget extraction only)
- `src/intelligence/compile-page-content-contract.ts`, `SeoBuildIntelligenceHttpClient.createSEOContentBlueprint/createStructuredContent` exist but have zero production callers
- `packages/bot-interop/src/website-intelligence.ts` `WebsiteBuildBlueprintV1` has no visual-requirement surface; `ImageAssetPlanningStage` reads spec `imageSlots`
- Donor crawl machinery is reusable: `src/ingestion/SourceCrawler.ts` + `ScreenshotCapturer.ts`
- No `RedesignExecutionIntegrityReceipt`, no SourceAssetCorpus reuse ledger

## Scope

**In:** Website-Bot runtime, contracts (`packages/bot-interop` — Website-Bot-owned), stages, intelligence layer, recursive CLI intent binding, tests, receipt emitter, one seam run.

**Out (forbidden):** SEO-Bot / LLM-Router mutation; full Golden E2E / three recursive waves / portfolio runs; manual Safe Haven redesign or output patching; competitor prose/imagery reuse; weakening donor count or fail-closed refusals; restoring COPY as recursive default; breaking the separately-explicit legacy COPY compatibility path; unrelated cleanup; `.github/workflows/**` edits.

## Execution DAG / TODOs

Waves ordered per contract §20 validation order. Each todo classifies its paths (REQUIRED_RUNTIME / REQUIRED_CONTRACT / REQUIRED_TEST / REQUIRED_EVIDENCE).

### W0 — Preflight

- **todo-00 baseline+preflight** — reverify SHA; probe: SEO-Bot endpoint reachability + contract version, DataForSEO-backed landscape availability, `SEO_BOT_URL`/`SEO_BOT_API_KEY` via Infisical/AWS resolve (never printed), Playwright screenshot capability, `npm test` green at baseline. Record SEO-Bot/bot-interop identities for the receipt. Blocked probe → `preflight_blocked`.

### W1 — Intent authority (R1, R2)

- **todo-01 intent binding** — `scripts/recursive/recursive-cli.ts`: `writeSourceSpec` sets `spec.build_intent = "REDESIGN_IMPROVE"` explicitly. `src/pipeline/BuildIntent.ts`: add `requireBuildIntent()` (typed `BUILD_INTENT_REQUIRED`) for redesign/recursive surfaces; keep `parseBuildIntent` COPY default only for the explicit legacy path. Callers (`scripts/run-pipeline.ts`, `scripts/validate-site-factory.ts`, `src/inngest/website-pipeline.ts`) route redesign surfaces through the fail-closed parser.
- **todo-02 intent tests** — update `tests/unit/build-intent.test.ts` (undefined on redesign surface → fail closed; recursive fixture-without-intent → REDESIGN_IMPROVE; explicit REDESIGN_IMPROVE accepted); regression test that `recursive:improve` spec output contains `build_intent: REDESIGN_IMPROVE`.

### W2 — Mandatory competitive stage + donors (R3, R4, R5)

- **todo-03 mandatory stage** — `src/pipeline/FactoryExecutionPlan.ts`: under REDESIGN_IMPROVE add `competitive-intelligence` (and new redesign stages) to the mandatory set per mode; absence of credentials → `COMPETITIVE_INTELLIGENCE_REQUIRED` (map from existing `INTELLIGENCE_UNAVAILABLE` taxonomy).
- **todo-04 donor == 10 invariant** — `src/stages/CompetitiveIntelligenceStage.ts`: bounded replacement selection from `landscape.payload.domains` beyond `selected_donors` when a candidate is excluded/unusable; hard fail `COMPETITIVE_EVIDENCE_INCOMPLETE` unless exactly 10 qualified usable donors.
- **todo-05 real donor ingestion** — new `src/stages/DonorIngestionStage.ts` (or module inside competitive stage) reusing `SourceCrawler`/`ScreenshotCapturer` for bounded per-donor crawl (ranked URLs + bounded discovery), per-donor crawl manifest + screenshot set + evidence digest, disposition `DONOR_REFERENCE_ONLY`; donors without evidence dropped and replaced (bounded), else fail. PatternPortfolio synthesis consumes this real evidence.
- **todo-06 donor test matrix** — 3→FAIL, 9→FAIL, 10→PASS, excluded-in-10→FAIL/replace, missing crawl→FAIL, missing screenshot→FAIL (`tests/unit/` new donor suite; port fakes only in tests).

### W3 — Content authority chain (R6, R7, R8, R9, R10)

- **todo-07 SEOContentBlueprint wiring** — new stage/step after blueprint sealing calls `SeoBuildIntelligenceHttpClient.createSEOContentBlueprint` with exact `competitive_landscape_ref`, routes, VerifiedBusinessFacts; validate lineage equality (`COMPETITIVE_LANDSCAPE_MISMATCH`, `SEO_CONTENT_BLUEPRINT_INVALID`, `ROUTE_SET_MISMATCH`). No fixture fallback.
- **todo-08 PCC wiring** — call `compilePageContentContract` (already deterministic, tested) on the runtime path; instrument `page_content_contract_llm_calls` counter == 0; existing failure codes (`CONTENT_REQUIREMENT_UNPLACED`) already present.
- **todo-09 StructuredContentPackage wiring** — send sealed PCC via `createStructuredContent`; validate `page_content_contract_ref` digest equality, route-set compatibility (`STRUCTURED_CONTENT_LINEAGE_MISMATCH`); store as sole prose authority in `BuildContext`.
- **todo-10 legacy content bypass** — `FactoryExecutionPlan`: under REDESIGN_IMPROVE replace `ContentGenerationStage` with a structured-content projection stage that maps StructuredContentPackage routes/sections into `ctx.generatedContent` verbatim (no rewriting); instrument `legacy_content_generation_calls == 0`; legacy stage remains only on the explicit COPY path.
- **todo-11 deterministic schema** — new `RedesignSchemaSerializerStage` (deterministic JSON-LD from VerifiedBusinessFacts + StructuredContentPackage + routes; zero LLM, no FAQ generation call) substituted for `SchemaGeneratorStage` under REDESIGN_IMPROVE; instrument `redesign_schema_llm_calls == 0`; determinism test (same inputs twice → identical digest).
- **todo-12 chain tests** — lineage accept/reject, stale/mismatched digest, route mismatch, malformed artifact, determinism repeats, bypass counters (test matrix D/E/F/G).

### W4 — Visual authority (R11, R12)

- **todo-13 blueprint visual requirements** — `packages/bot-interop/src/website-intelligence.ts`: add `visual_requirements` to `WebsiteBuildBlueprintV1` (route, section, slot_id, required, role enum [hero, project_proof, gallery, service, team, trust, process, material, background, logo, badge, decorative], min count, preferred provenance, device suitability, composition guidance); produce it in `CompetitiveIntelligenceStage` blueprint sealing with deterministic route re-assertion; update `contracts/WEBSITE_INTELLIGENCE_LOCK.json` accordingly (Website-Bot-owned contract, not a sister repo).
- **todo-14 planner consumes blueprint** — `src/stages/ImageAssetPlanningStage.ts`: under REDESIGN_IMPROVE derive slots from blueprint `visual_requirements` (not spec `imageSlots`); gate `required_visual_slots_filled == 100%` (`VISUAL_ASSET_REQUIREMENT_UNSATISFIED`).
- **todo-15 SourceAssetCorpus + reuse ledger** — bind `source_assets: {harvest: true, reuse_policy: client_owned_authorized}` spec surface; extend source ingestion/asset planning so every discovered reusable source image is SELECTED or REJECTED with machine-readable reason (`SOURCE_ASSET_REUSE_UNEXPLAINED` if any unexplained loss); precedence authorized-source > licensed > generated > none; donor images excluded by construction.
- **todo-16 visual/asset tests** — matrix H/I: requirements reach planner; required slot missing → fail; authorized source photo preferred over generation; rejection carries reason; donor image cannot become candidate asset.

### W5 — Receipt + gates (R13 prep, §16, §17)

- **todo-17 RedesignExecutionIntegrityReceipt** — new emitter (`src/pipeline/evidence/RedesignExecutionIntegrityReceipt.ts` + finalizer hook) collecting all §16 fields (identities, intent proof, donor counts, lineage refs, LLM counters, asset ledger counts, schema path, rendered QA refs) → `REDESIGN_EXECUTION_INTEGRITY: PASS|FAIL`; missing evidence → FAIL. Rendered visual QA required for convergence on this path (`VISUAL_QA_REQUIRED`).
- **todo-18 fail-closed invariant tests** — §17 impossibility matrix + receipt validation test (matrix J).

### W6 — Validation + seam proof (R13)

- **todo-19 full targeted validation** — contract §20 order: intent → plan → donor → crawl/screenshot → SEO adapter → blueprint → lineage → PCC determinism → SCP lineage → bypass → schema → source-asset → visual-slot → QA-gate → integration → `npm run typecheck` → lint → build → `npm run verify:all`. Any earlier failure blocks later claims.
- **todo-20 ONE Safe Haven seam proof** — `https://www.safehavenrr.com`, real SEO-Bot + DataForSEO, real donors/crawl/screenshots, real SCP, authorized asset reuse, rendered QA. No mocks, no seeded landscape, no manual patching. Emit + validate receipt. NOT a recursive 3-wave run, NOT Golden E2E.
- **todo-21 converge** — required 17-section final report; ship branch via `make pr`; final line `READY_FOR_REAL_GOLDEN_E2E` only if every blocking property passed, else `DO_NOT_RUN_GOLDEN_E2E`.

**Critical path:** todo-00 → 01 → 03 → 04 → 05 → 07 → 08 → 09 → 10 → 11 → 13 → 14 → 15 → 17 → 19 → 20 → 21

## Checkpoints (no-go → stop, report, do not weaken)

| after | evidence required | no-go action |
|---|---|---|
| W0 | SEO-Bot live probes pass; identities recorded | `preflight_blocked` — report exact probe failure |
| W2 | donor matrix green incl. ==10 hard fail cases | stop; if SEO-Bot cannot supply enough qualified candidates by contract → `CROSS_REPOSITORY_BLOCKER` with evidence |
| W3 | lineage + zero-LLM counters green | stop; never LLM-repair or fixture-substitute |
| W5 | receipt emitter validates on synthetic full-evidence fixture | stop before seam run |
| W6 seam | receipt `PASS` with all §16 fields | report FAIL honestly; final line `DO_NOT_RUN_GOLDEN_E2E` |

## Stress test / disconfirming cases

- **SEO-Bot returns < 10 qualified donors even after bounded replacement** (Aug 15 live run returned 3): this is the highest-probability blocker. Bounded discovery from `domains[]` beyond `selected_donors` is the in-repo mitigation; if the endpoint contract itself cannot yield 10 → `CROSS_REPOSITORY_BLOCKER`, not a weakened invariant.
- **SEO-Bot has no `structured-content` endpoint or different shape than `SeoBuildIntelligencePort` assumes** → probe in W0; mismatch → `CROSS_REPOSITORY_BLOCKER`.
- **Provider JSON compliance flake (residual F-18)** recurs during pattern synthesis → bounded retries already exist in router; persistent failure fails the seam honestly.
- **`bot-interop` blueprint schema change breaks `WEBSITE_INTELLIGENCE_LOCK.json` parity** → run `npm run evidence:contract-parity` inside W4.
- **Donor crawl blocked by robots/bot-protection** → bounded replacement into next qualified candidate; below 10 → fail.
- **Blast radius:** high (pipeline topology, contract package, stages). Legacy COPY path must keep passing its existing suite untouched.
- **Rollback:** code = revert branch commits (`git_restore_scoped_paths` pre-PR); external = seam run writes only evidence artifacts + preview-tier deploys (no production promotion); no force-push.

## Unknowns (fail-closed)

| id | question | resolution |
|---|---|---|
| U1 | Can real SEO-Bot landscape yield 10 qualified operating-company donors for Safe Haven's market? | probe at W0/W2; below 10 → CROSS_REPOSITORY_BLOCKER |
| U2 | Exact live SEO-Bot structured-content endpoint contract/version | probe at W0 |
| U3 | Does seam run require end-to-end mode (Vercel deploy) to reach rendered QA, or can VisualQAStage be admitted to a bounded redesign-proof mode? | probe repo; decide in W5 — QA is mandatory either way |

## GMP handoff / envelope

- **may_modify:** `scripts/recursive/recursive-cli.ts`, `src/pipeline/**`, `src/stages/**`, `src/intelligence/**`, `src/ingestion/**` (reuse), `packages/bot-interop/src/website-intelligence.ts`, `contracts/WEBSITE_INTELLIGENCE_LOCK.json`, `tests/unit/**`, new evidence emitters, `fixtures/` additions (new redesign fixture only)
- **must_not_modify:** `.github/workflows/**`, `.env*`, SEO-Bot/LLM-Router (external), existing legacy COPY test semantics except where the contract explicitly requires the redesign-surface change, docs/reports history
- **preserved_contracts:** explicit legacy COPY path continues to work when explicitly requested; Astro/npm/Vercel locked decisions; evidence-backed readiness only; secrets via Infisical only
- **validation_commands:** `npm test`, `npm run typecheck`, `npm run build`, `npm run evidence:contract-parity`, `npm run verify:all`, `make pr`

## Convergence

- `executable_when`: baseline reverified, W0 probes pass, DAG acyclic (it is), no blocking unknowns open beyond U1–U3 probe plan
- `complete_when`: SP-01..SP-08 all passed, receipt PASS, report emitted, `make pr` green
- Final line is earned, never asserted: `READY_FOR_REAL_GOLDEN_E2E` iff all blocking properties pass; otherwise `DO_NOT_RUN_GOLDEN_E2E`
- next_skill: `l9-gmp-protocol` or `@environment/program-execution` + `/autonomy` for execution; this plan grants no mutation authority by itself
