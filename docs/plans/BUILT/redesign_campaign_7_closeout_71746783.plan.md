---
name: Redesign Campaign 7 Closeout
overview: Finish Campaign 7 (REDESIGN_IMPROVE) by pointing the pipeline at the fixed local SEO-Bot, hardening donor qualification and cache/revert guards, then re-running the Safe Haven seam proof to a PASS integrity receipt and final verdict.
todos:
  - id: seo-bot-up
    content: Start fixed SEO-Bot from /Users/macm2/SEO-Bot and smoke-test the seo-content-blueprint endpoint
    status: completed
  - id: infisical-url
    content: Persist SEO_BOT_URL in Website-Bot Infisical and export for seam shell
    status: completed
  - id: donor-tighten
    content: Add manufacturer/franchise exclusions to donorQualification.ts + must-reject tests
    status: completed
  - id: seam-guards
    content: "Seam script: purge source-site cache, preflight stage-version assertions"
    status: completed
  - id: receipt-provenance
    content: Add source_crawl_provenance and stage versions to integrity receipt; fail on cache
    status: completed
  - id: seam-run
    content: Run targeted tests, then one real Safe Haven seam proof to receipt PASS
    status: completed
  - id: final-report
    content: Emit 17-section report with READY/DO_NOT_RUN verdict backed by receipt evidence
    status: completed
isProject: false
---

# Campaign 7 Closeout — REDESIGN_IMPROVE Seam PASS

## Context

All 13 requirements are code-complete in Website-Bot. The last seam proof died at `redesign-content-authority` with a 500 from the old SEO-Bot producer ("LLM did not return valid JSON"). The fixed producer lives at `/Users/macm2/SEO-Bot` (branch `claude/campaign-7-seo-build-intelligence-producer`) but is not the process serving 127.0.0.1:3100. Remaining risks from the last run: `SEO_BOT_URL` absent from Infisical, three national/manufacturer donors accepted, source crawl reused the client cache, and silent file reverts went undetected mid-session.

## Phase 1 — SEO-Bot producer online (no sister-repo code changes)

- Start the fixed SEO-Bot from `/Users/macm2/SEO-Bot` (confirm branch/SHA, `npm run` its server) on a local port; smoke-test `POST /api/build-intelligence/seo-content-blueprint` with a multi-route payload before touching Website-Bot.
- Persist `SEO_BOT_URL` into the Website-Bot Infisical project (prod, path `/`) via the Infisical API using the `l9-aws-secrets` bootstrap, and export it in the seam shell for this run. No secrets committed; only the env var name is referenced in code.

## Phase 2 — Donor qualification tightening

- In [src/pipeline/redesign/donorQualification.ts](src/pipeline/redesign/donorQualification.ts), add exclusion patterns for manufacturers (`owenscorning`, `gaf`, `certainteed`, `tamko`, `iko`, `malarkey`) and national franchise/network properties (`servpro`, `servicemaster`, `contractorconnection`, `pauldavis`, `belfor`), plus a structural rule rejecting hosts whose accepted page evidence lacks a local-operator footprint. Extend `DonorExclusionReason` accordingly.
- Update [tests/unit/donor-qualification.test.ts](tests/unit/donor-qualification.test.ts) with the three previously-accepted offenders as must-reject cases.

## Phase 3 — Seam-run integrity guards

- [scripts/run-redesign-seam-proof.ts](scripts/run-redesign-seam-proof.ts):
  - Delete the Safe Haven client source-site cache (`build/assets/safehavenrr/_cache/source-site`) before the run so `SourceSiteIngestionStage` performs a live crawl.
  - Preflight assert `CompetitiveIntelligenceStage.version === "2.0.0"` (and versions of the other redesign stages) and abort with a clear error if any file was reverted.
- [src/pipeline/redesign/integrityReceipt.ts](src/pipeline/redesign/integrityReceipt.ts) + [src/stages/RedesignIntegrityReceiptStage.ts](src/stages/RedesignIntegrityReceiptStage.ts): record `source_crawl_provenance: "live" | "cache"` and per-stage versions in the receipt; fail evaluation when provenance is `cache` on a seam run.

## Phase 4 — Validate and re-run the seam proof

- Targeted unit tests: donor qualification, integrity receipt, blueprint compile; then `npm run verify:all` gate as feasible.
- One real Safe Haven seam run (`npm run redesign:seam-proof`) with Infisical hydration + `SEO_BOT_URL` exported. Expected: exactly 10 qualified operating-company donors with live crawls/screenshots, sealed SEOContentBlueprint from the real producer, deterministic PCC (0 LLM calls), real StructuredContentPackage, legacy content/schema bypassed, 100% visual slot fill, live source crawl, receipt `REDESIGN_EXECUTION_INTEGRITY: PASS`.

## Phase 5 — Final report and verdict

- Produce the 17-section campaign report with receipt evidence, and conclude `READY_FOR_REAL_GOLDEN_E2E` only if the receipt is PASS; otherwise `DO_NOT_RUN_GOLDEN_E2E` with the exact blocking evidence.

## Failure handling

- If the fixed producer still 500s on the 29-route blueprint, this remains a cross-repo blocker: stop, record it in the receipt/report as `DO_NOT_RUN_GOLDEN_E2E`, and do not substitute a local blueprint or mutate SEO-Bot.
