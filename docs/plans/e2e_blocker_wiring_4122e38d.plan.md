---
name: E2E Blocker Wiring
overview: Wire existing factory code (template, generate-spec, visual-qa, SEO checker) and republish LLM-Router 1.1.2 so local-proof emits canonical/OG/unique H1s on live OpenRouter. Do not weaken boot contracts. Perplexity is rotated. Vercel team role and SEO SERP vault stay human-blocked.
todos:
  - id: todo-00-preflight
    content: ""
    status: completed
  - id: todo-01-llm-dts
    content: Replace NodeJS.ProcessEnv with Record<string, string | undefined> in resolveOpenRouterBaseUrl; verify:declarations PASS
    status: completed
  - id: todo-02-llm-publish
    content: Bump llm-router to 1.1.2, verify:all PASS, publish GitHub Packages (never republish 1.1.1)
    status: completed
  - id: todo-03-layout-wire
    content: Port canonical + og:title/description/url from example BaseLayout into astro_template; raise verify-seo those checks from UNKNOWN to FAIL
    status: completed
  - id: todo-04-generate-spec-failclosed
    content: Add lead_form_action to generate-spec prompt; exit 1 on validateDomainSpec failure (no write-anyway); keep --write-invalid opt-in
    status: completed
  - id: todo-05-content-uniqueness
    content: Prompt first-line H1 ≤12 words then body ≥80; Hero uses line 1 as h1; reject duplicate slot bodies/H1s; finite retries then CONTENT_VALIDATION_FAILED
    status: completed
  - id: todo-06-visual-qa-script
    content: Point package.json verify:visual-qa at scripts/verify-visual-qa.mjs; keep VisualQAStage in end-to-end only
    status: completed
  - id: todo-07-seo-typecheck
    content: Fix SEO-Bot test types so npm run typecheck PASSes; retarget maintenance-readiness off missing website_factory_v2; do not exclude tests from tsc
    status: completed
  - id: todo-08-seo-yaml-doc
    content: Header on website_factory_integration.yaml — convenience copy; live contract is bot-interop v3
    status: completed
  - id: todo-09-consumer-bump
    content: "Website-Bot and SEO-Bot @quantum-l9/llm-router@1.1.2 from GitHub Packages; drop file: worktrees"
    status: completed
  - id: todo-10-gov-registry
    content: Commit Cursor-Governance openclaw-igorbot/openrouter registry enablement (refs only)
    status: completed
  - id: todo-11-perplexity
    content: ""
    status: completed
  - id: todo-12-vercel-role
    content: ""
    status: pending
  - id: todo-13-seo-vault
    content: ""
    status: pending
  - id: todo-14-regenerate
    content: Infisical-hydrated pipeline:local-proof on Safe Haven, no OPENROUTER_BASE_URL shim; assert canonical/OG/unique H1s in dist/
    status: in_progress
  - id: todo-15-pr-check
    content: make pr-check on each mutated product repo vs origin/main
    status: pending
isProject: true
---

# E2E constellation blocker plan (wire first)

Improved in place via `kernels/Improve.md` (plan artifact only; product repos unchanged).

**Kernel status:** PartiallySucceeded. Plan contracts, DAG, and unresolved forks are tightened. Product code is unmodified. Human ops remain Blocked.

**Depth:** deep. **Code in scope:** yes. **WB-001 OpenRouter:** already in AWS + Infisical — preflight confirms, does not redo.

**Evidence pack:** [`/Users/macm2/dev/website-bot-e2e/website_bot_full_e2e_run/E2E_HICCUP_LOG.md`](/Users/macm2/dev/website-bot-e2e/website_bot_full_e2e_run/E2E_HICCUP_LOG.md)

**Immutable baselines (full SHAs):**

- Website-Bot `c0ee7eacc4837ecd29fce379f69aa856f6259fce`
- SEO-Bot `90128380f449c61736a6335e51c67f66f6b3b58b`
- LLM-Router `37b142090c6f531bf70f487404d045e6bbe9053c`

Work from those SHAs (e2e clones or fresh branches). Revert local `file:../LLM-Router` before consumer bumps.

**Law:** do not invent parallel pipelines. If a stage/script/template already exists, wire it. Do not weaken `loadConfig()`, placeholder-scan, SEO-Bot Zod boot, or local-proof stage lists. Do not store `OPEN_ROUTER_MANAGEMENT_TOKEN` in AWS/Infisical. Never fabricate PASS.

## Secrets blocker status (probed 2026-08-13, values not logged)

Not all secret blockers are unblocked.

- **OPENROUTER_API_KEY — unblocked.** Governance `.env` `GET https://openrouter.ai/api/v1/key` HTTP 200. AWS `openclaw-igorbot/openrouter#apikey` `--check` OK. Infisical Website-Bot + SEO-Bot already created this session.
- **PERPLEXITY_API_KEY — unblocked (2026-08-13).** New `.env` key live-probed `POST https://api.perplexity.ai/chat/completions` model `sonar` HTTP **200**. AWS `openclaw-igorbot/perplexity#apikey` rotated (old sha256_12 `e5e690122684` → `2de70e44a033`, matches `.env`). Infisical: Website-Bot **patched**, SEO-Bot **created** `PERPLEXITY_API_KEY` (both match AWS). LLM-Router has no Infisical project; Website-Bot/SEO-Bot hydrate the key into `L9LLMRouter`. AWS-resolved key re-probed 200 after write.
- **OPEN_ROUTER_MANAGEMENT_TOKEN — not a mesh blocker.** Intentionally not in AWS/Infisical.
- **Vercel (X-001 / todo-12) — still blocked; wrong key type in the dashboard screenshots.** `Website_Bot_e2e_Test` is an **AI Gateway** key (`vck_…`, purpose `ai-gateway`). Website-Bot does not call AI Gateway. It needs a Vercel **account access token** as `VERCEL_TOKEN` for `POST /v11/projects` + `POST /v13/deployments`. Stored token still authenticates as `splitwisely704` / Northstar / `limited: true` / create-project **403**. Logged-in UI is a different identity: Hobby `igor-beylins-projects`. Workflow SDK (`workflow-sdk.dev`) is durable-workflow runtime, not this factory’s deploy path.
- **SEO-Bot SERP vault (todo-13) — partial.** PageSpeed live 200. `SEO_BOT_API_KEY` is minted in the editor (64-hex, correct shape) — **save `.env`**; it is not in Infisical yet. DataForSEO still `DATAFORSEO_API_KEY` (wrong). **Postgres/Redis are not Graphiti.** `Quantum-L9/l9-graphiti-memory` is SQLite canonical memory with optional Neo4j/Graphiti projections; it does not provide `DATABASE_URL` or `REDIS_URL`. SEO-Bot already ships [`docker-compose.validation.yml`](/Users/macm2/dev/website-bot-e2e/repos/SEO-Bot/docker-compose.validation.yml) (postgres:16 + redis:7). Full [`docker-compose.yml`](/Users/macm2/dev/website-bot-e2e/repos/SEO-Bot/docker-compose.yml) also pulls PostHog+ClickHouse — do not start that on this Mac. Nothing is listening on 5432/6379 right now. Test stack: publish loopback ports, `DATABASE_URL=postgres://l9bot:validation-only@127.0.0.1:5432/l9_seo_bot_validation`, `REDIS_URL=redis://127.0.0.1:6379`, then `npm run migrate`. Zod still also requires `POSTHOG_API_URL` + `POSTHOG_PERSONAL_API_KEY` (Infisical Website-Bot already has PostHog names).

```mermaid
flowchart TD
  P0[todo-00 preflight]
  Dts[todo-01 portable d.ts]
  Pub[todo-02 publish 1.1.2]
  Bump[todo-09 consumer bump]
  Tpl[todo-03 layout plus verify-seo FAIL]
  GS[todo-04 generate-spec fail-closed]
  Uniq[todo-05 H1 uniqueness]
  VQA[todo-06 visual-qa script]
  SeoT[todo-07 typecheck]
  SeoY[todo-08 yaml header]
  Gov[todo-10 registry commit]
  LP[todo-14 local-proof no shim]
  PRC[todo-15 pr-check]
  Pplx[todo-11 Perplexity human]
  Vcl[todo-12 Vercel human]
  Dfs[todo-13 SEO vault human]
  E2E[end-to-end after X-001]
  P0 --> Dts --> Pub --> Bump
  P0 --> Tpl
  P0 --> GS
  P0 --> Uniq
  P0 --> VQA
  P0 --> SeoT
  P0 --> SeoY
  P0 --> Gov
  Tpl --> LP
  GS --> LP
  Uniq --> LP
  Bump --> LP
  LP --> PRC
  SeoT --> PRC
  Gov --> PRC
  VQA --> E2E
  Vcl --> E2E
  Dfs --> E2E
  Pplx -.->|"fact path only"| E2E
```

## Improve kernel — what changed in this plan

Pass 1 inventory: plan duplicated todos, left three forks, gated local-proof on Perplexity (wrong layer), truncated SHAs, optional Hero split, “fix or exclude tests.”

Pass 2 contracts: resolved forks below. Entropy removed: duplicate numbered todo list, “optionally,” “fix or.”

Resolved forks (do not reopen):

1. **todo-07:** Fix test types / drop the missing `website_factory_v2` import. **Do not** exclude tests from `tsconfig.check.json`. Weakening typecheck is a validation bypass.
2. **todo-05:** Not optional. Prompt: line 1 = headline ≤12 words; blank line; body ≥80 words. [`Hero.astro`](/Users/macm2/dev/website-bot-e2e/repos/Website-Bot/astro_template/src/components/Hero.astro) uses line 1 as `<h1>`, remainder as body. Cross-slot uniqueness after retries. `MAX_RETRIES` stays finite (keep 1 or raise to 2). Exhaustion throws existing `CONTENT_VALIDATION_FAILED` — no infinite loop.
3. **todo-14 vs todo-11:** Content generation uses OpenRouter. Perplexity 401 does **not** gate local-proof. It gates live fact-verification / full mesh only.
4. **verify-seo:** After layout wire, raise canonical + og:title/description/url from UNKNOWN/low to **FAIL**. That wires the existing checker. Do not skip UNKNOWN checks. Do not invent a second SEO verifier.
5. **generate-spec write-anyway:** Default becomes exit 1. `--write-invalid` is the only escape. Preflight greps CI; if a workflow depends on write-anyway, update that workflow in the same PR — do not keep the silent write.

## Classification (missing vs unwired)

- **WB-001 OpenRouter — DONE.** AWS `openclaw-igorbot/openrouter#apikey` + Infisical Website-Bot/SEO-Bot `OPENROUTER_API_KEY`.
- **WB-002 / LLM-003 publish drift — EXISTS in git, not on Packages 1.1.1.** Patch-bump **1.1.2**. Do not republish 1.1.1. Preflight must prove the published tarball lacks `resolveOpenRouterBaseUrl`.
- **LLM-001 NodeJS namespace — EXISTS_TOO_WEAK.** Portable env type so declaration-consumer needs no `@types/node`.
- **LLM-002 Perplexity — OPS DONE.** New key live 200; AWS + Infisical Website-Bot/SEO-Bot rotated. Not a local-proof gate.
- **Both keys at construct — KEEP.** Do not make Perplexity optional (would hide LLM-002). Tests already DI dummy keys.
- **WB-003 lead_form_action — EXISTS_UNWIRED.** Pipeline + `LeadForm.astro` require it. [`generate-spec.ts`](/Users/macm2/dev/website-bot-e2e/repos/Website-Bot/scripts/generate-spec.ts) omits it from the prompt and writes invalid YAML anyway (lines 211–214).
- **WB-005 / WB-009 canonical + OG — EXISTS_UNWIRED.** Tags live in [`examples/supplemental-insurance-pros/astro_site/src/layouts/BaseLayout.astro`](/Users/macm2/dev/website-bot-e2e/repos/Website-Bot/examples/supplemental-insurance-pros/astro_site/src/layouts/BaseLayout.astro) (lines 27–30). [`astro_template/.../BaseLayout.astro`](/Users/macm2/dev/website-bot-e2e/repos/Website-Bot/astro_template/src/layouts/BaseLayout.astro) is what `SiteAssemblerStage` copies and lacks them (template only has conditional `og:image`).
- **WB-008 duplicate H1 — EXISTS_TOO_WEAK.** `MIN_WORDS=80` only; Hero dumps paragraph 0 into `<h1>`.
- **WB-007 visual QA — EXISTS_UNWIRED + GATED.** Real `scripts/verify-visual-qa.mjs` + `VisualQAStage`. npm script is echo stub. Stage stays end-to-end (needs public URL).
- **Images empty — EXISTS_GATED.** Out of this plan unless `--with-assets`. OG title/desc/url do not require images.
- **SEO-003 daemon — EXISTS_GATED.** Zod fail-closed in [`SEO-Bot/src/core/config.ts`](/Users/macm2/dev/website-bot-e2e/repos/SEO-Bot/src/core/config.ts) is correct. **No lite boot.**
- **SEO-004 YAML 2.0 — STALE CONVENIENCE.** Runtime is v3 `assertWebsiteFactoryHandoffV3`. `website_factory_v2.ts` is missing — do not recreate v2.
- **SEO-001 typecheck — EXISTS_TOO_WEAK.** CI src-only `tsc`; `npm run typecheck` includes tests. Align by fixing tests, not by dropping them.
- **X-001 / X-002 — OPS.** Chosen: create project in Hobby UI (skip Northstar 403). DNS only after that project exists. `VercelDeployStage` still requires `github_repo_id` because API deploy uses `gitSource`.
- **Handoff live — EXISTS_GATED.** `HandoffEmitterStage` requires end-to-end + deployTarget. Do not emit fake v3 from local-proof.

## Objective

Unblock a **second** Safe Haven e2e so that:

1. `pipeline:local-proof` uses live OpenRouter via Infisical (no `OPENROUTER_BASE_URL` shim, no `file:` llm-router).
2. Generated HTML has canonical + OG tags and unique H1s.
3. `generate-spec` cannot write a spec that fails `validateDomainSpec`.
4. `@quantum-l9/llm-router@1.1.2` on GitHub Packages matches git main (`OPENROUTER_BASE_URL` + portable d.ts).
5. Perplexity, Vercel, SEO SERP are green **or** explicitly human-blocked — never fabricated PASS.

**Falsifiable success**

- Regenerated `dist/**/*.html`: every indexable page has `rel=canonical`, `og:title`, `og:description`, `og:url`.
- No two indexable pages share the same H1 text (thank-you may omit H1).
- Each indexable H1 is ≤12 words.
- `generate-spec` against a live URL **exits non-zero** if `contact_form` is present without `lead_form_action`.
- LLM-Router `npm run verify:all` PASSes including `verify:declarations`.
- Website-Bot and SEO-Bot depend on `@quantum-l9/llm-router@1.1.2` from GitHub Packages.
- `pipeline:local-proof` with Infisical hydrate and **no** shim: content-generation checkpoint succeeded.
- `make pr-check` PASS on each mutated product repo vs `origin/main`.
- Vercel production URL READY only if X-001 is lifted; otherwise receipt stays `BLOCKED_TOKEN_SCOPE_OR_TEAM_ROLE`.

## Scope

**In**

- Wire `astro_template` BaseLayout from the example (canonical + og:title/description/url; keep json-ld and conditional og:image).
- Raise `verify-seo.mjs` canonical/OG checks to FAIL.
- Fail-closed `scripts/generate-spec.ts`.
- Content uniqueness + Hero H1 split as specified.
- Point `verify:visual-qa` at the existing mjs.
- LLM-Router portable type, 1.1.2 publish, consumer bumps.
- SEO-Bot test typecheck + YAML header.
- Cursor-Governance registry commit (refs only).
- Regenerated Safe Haven local-proof after wiring.

**Out**

- SEO-Bot lite boot / skip DataForSEO/PageSpeed.
- Making Perplexity optional on `L9LLMRouter`.
- GoDaddy DNS before a Vercel project exists.
- Force-push, republishing 1.1.1, storing management token.
- Pixel-clone of safehavenrr.com / Astro v6 source.
- GitHub MCP credential repair.
- `--with-assets` / image stages (gated, not required for this success set).
- Fake v3 handoff from local-proof.

## Execution envelope

- **Repos:** `Quantum-L9/LLM-Router`, `Quantum-L9/Website-Bot`, `Quantum-L9/SEO-Bot`, Cursor-Governance (registry only).
- **Worktrees:** `/Users/macm2/dev/website-bot-e2e/repos/{Website-Bot,SEO-Bot,LLM-Router}` or fresh clones at the locked SHAs. Revert dirty `file:` / shim edits first.
- **Order:** See DAG. Website-Bot template/spec/content **do not wait** for publish. Consumer dep bump **does**. local-proof waits for template + spec + uniqueness + consumer bump + OpenRouter preflight. It does **not** wait for Perplexity/Vercel/SERP.
- **Secrets:** `l9-aws-secrets` + Infisical names matching env vars. Never log values.
- **autonomous_merge:** false until this L4 plan-Build stack is green+mergeable, then merge bottom-up.
- **Network:** GitHub Packages publish; OpenRouter + Perplexity live probes green; Vercel only after human role fix.
- **Must not edit:** `CANONICAL_LAW.md`, session hooks, Infisical bootstrap IDs, token values in git.

## Todo contracts (side effects + regression)

**todo-00-preflight** — No product mutation. Must record: SHAs still match; `resolve_secret.py --ref 'openclaw-igorbot/openrouter#apikey' --check` OK; Infisical Website-Bot/SEO-Bot have `OPENROUTER_API_KEY`; published 1.1.1 tarball evidence; generate-spec CI grep result; worktree `git status` clean of `file:`.

**todo-01-llm-dts** — File: [`LLM-Router/src/providers/openrouter.ts`](/Users/macm2/dev/website-bot-e2e/repos/LLM-Router/src/providers/openrouter.ts). Regression: `npm run verify:declarations`. Risk: low.

**todo-02-llm-publish** — Files: `package.json`, built `dist/`. Side effect: GitHub Packages 1.1.2 is public-to-org. Rollback: consumers stay on 1.1.1; do not yank unless broken. Risk: high.

**todo-03-layout-wire** — Port from example BaseLayout; compute `canonicalUrl` from `siteConfig.siteUrl` + path. Files: `astro_template/src/layouts/BaseLayout.astro`, `scripts/verify-seo.mjs`. Regression: unit/fixture HTML without canonical fails verify-seo; with tags passes. Risk: low. Highest SEO leverage.

**todo-04-generate-spec-failclosed** — Files: `scripts/generate-spec.ts`, any CI that invoked write-anyway. Side effect: operator workflow breaking if they relied on invalid YAML. Regression: fixture missing `lead_form_action` exits 1 and does not write `--out` unless `--write-invalid`. Risk: medium.

**todo-05-content-uniqueness** — Files: `ContentGenerationStage.ts`, `Hero.astro`, `tests/unit/content-generation.test.ts`. Side effect: local-proof that previously passed with duplicated copy will FAIL (intended). Risk: medium.

**todo-06-visual-qa-script** — File: Website-Bot `package.json`. Do not add VisualQA to local-proof. Risk: low.

**todo-07-seo-typecheck** — Fix tests; retarget `maintenance-readiness.test.ts`. Files: failing tests / types only. Risk: low.

**todo-08-seo-yaml-doc** — Header only. Risk: low.

**todo-09-consumer-bump** — Depends on todo-02. Files: `package.json` / lock in both bots. Risk: medium (registry auth).

**todo-10-gov-registry** — [`ops/secrets/openclaw-igorbot.registry.yaml`](/Users/macm2/Cursor-Governance/Cursor-Governance/ops/secrets/openclaw-igorbot.registry.yaml). Refs only.

**todo-12** — Human UI + token (chosen 2026-08-13): Hobby `igor-beylins-projects`. Create GitHub-linked project `safehavenrr-e2e`, mint **account access token** scoped to that project ([access tokens](https://vercel.com/docs/accounts/access-tokens)). Do **not** use AI Gateway `vck_` keys ([AI Gateway API keys](https://vercel.com/docs/ai-gateway/authentication-and-byok/api-keys)). Agent then: AWS `openclaw-igorbot/vercel#token` + Infisical `VERCEL_TOKEN`; **unset** `VERCEL_TEAM_ID`. Probe `GET /v9/projects/{id}` 200 then existing `VercelDeployStage`. Workflow SDK ([API reference](https://workflow-sdk.dev/docs/api-reference)) is not this factory’s deploy path.

**todo-13** — Human SERP vault. Receipts: probe exit codes.

**todo-14-regenerate** — Depends: 00, 03, 04, 05, 09. Not 11/12/13. Command: Infisical-hydrated `npm run pipeline:local-proof -- --spec=<safehaven>`. Assert HTML. Unknown if OpenRouter Infisical key is revoked since last check — then stop and report, do not shim.

**todo-15-pr-check** — Each mutated repo `make pr-check`.

**Leverage:** todo-03 > todo-04 > todo-02 > todo-05 > todo-01 > rest.

**Critical path to local-proof:** `00 → (01→02→09 ∥ 03 ∥ 04 ∥ 05) → 14 → 15`.

## Property evidence

- P1 unique H1s — todo-05 + todo-14 HTML grep.
- P2 canonical+OG present — todo-03 verify-seo FAIL + todo-14 HTML.
- P3 generate-spec fail-closed — todo-04 fixture exit 1.
- P4 llm-router portable d.ts — todo-01 `verify:declarations`.
- P5 Packages 1.1.2 matches git — todo-02 tarball contains `resolveOpenRouterBaseUrl`; consumers on 1.1.2.
- P6 no shim local-proof — todo-14 env dump shows no `OPENROUTER_BASE_URL`; checkpoint succeeded.
- P7 typecheck honest — todo-07 `npm run typecheck` PASS without excluding tests.
- P8 no lite boot / no optional Perplexity — review diff; absence of skip flags.

## Stress / rollback

**Disconfirm before publish:** Packages 1.1.1 tarball really missing `resolveOpenRouterBaseUrl`. Uniqueness + 80-word min must not loop (finite retries). Example OG copy must not drop json-ld / PostHog inject. generate-spec CI must not require write-anyway (or is updated in-PR).

**Assumed false ifs:** Infisical OpenRouter still valid; example BaseLayout is intended factory UX; Vercel stage is correct once the token can create projects; DataForSEO required for real SEO-Bot.

**Blast radius:** Bad 1.1.2 breaks both bots’ LLM path. Fail-closed generate-spec breaks automation that parsed invalid YAML. Uniqueness gate fails previously “green” duplicated copy.

**Rollback:** revert PRs; leave consumers on 1.1.1; Infisical secret versions; do not revert OpenRouter AWS secret unless leaked.

## Doc / root surface

- Website-Bot `examples/README.md` if it still says pipeline does not materialize Astro.
- Website-Bot `package.json` visual-qa script.
- SEO-Bot YAML header / AGENTS.md if it still cites v2.
- Cursor-Governance registry (already enabled on disk).
- Root `AGENTS.md` / `CANONICAL_LAW.md` — N/A.

## GMP / PE handoff

- **May modify:** LLM-Router `src/providers/openrouter.ts`, `package.json`; Website-Bot `astro_template/**`, `scripts/generate-spec.ts`, `scripts/verify-seo.mjs`, `src/stages/ContentGenerationStage.ts`, `Hero.astro`, `package.json`; SEO-Bot tests/YAML header; Governance secrets registry.
- **Must not:** `CANONICAL_LAW.md`, session hooks, Infisical bootstrap IDs, Vercel/OpenRouter/Perplexity **values** in git, `OPEN_ROUTER_MANAGEMENT_TOKEN`.
- **Preserved:** bot-interop v3, Infisical fail-soft hydrate, SEO-Bot Zod fail-closed boot, local-proof vs end-to-end stage lists, both-keys-required at LLM construct.
- **Validate:** LLM-Router `npm run verify:all`; Website-Bot `npm run typecheck && npm run site:test:local && npm run pipeline:local-proof -- --spec=<safehaven>`; SEO-Bot `npm run typecheck && NODE_ENV=test npx vitest run`; each repo `make pr-check`.
- **Execute via:** `@environment/program-execution` then `/autonomy` under Program lease. Next skill: `l9-ynp` if still blocked on todo-11/12/13 after code wiring; else PE Controller.

## Convergence

**Status: NotConverged (plan improved; product untouched).**

Code wiring can proceed on Build. Live constellation remains blocked on U-02 Vercel team role and U-03 SEO SERP/DB. Those do not block todo-14. U-01 Perplexity is closed.

**Unknowns (accept_bounded unless human unblocks):** U-02 Vercel team; U-03 DataForSEO/PageSpeed; U-04 generate-spec CI write-anyway — **must be resolved in todo-00**, then either gone or in-PR.

**Do not claim Succeeded** until todo-14 HTML assertions pass and remaining human items are Passed or explicitly accepted as out-of-run.
