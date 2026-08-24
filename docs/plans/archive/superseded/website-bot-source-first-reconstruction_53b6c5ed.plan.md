---
name: Website-Bot source-first reconstruction
overview: "Make reconstruction the only path when a live source site exists. Keep working campaign extract/design/chrome patches. Close remaining invention paths: generate-spec extra routes, content home-copy fallback, empty-crawl LLM, FAQ schema LLM, and seo_contract.site_url pointing at igorbeylin.com. Land on Quantum-L9/Website-Bot. Gate is make verify-all."
todos:
  - id: T1
    content: Lock Website-Bot baseline SHA and reuse the existing campaign dirty tree; list uncommitted reconstruction files versus origin/main; do not clone a new campaign directory
    status: completed
  - id: T2
    content: "Keep crawled page bodyText, tel: phones, and header nav on IngestedPage; refuse incomplete cache reuse; prove with existing unit tests rather than rewriting extract from origin/main"
    status: completed
  - id: T3
    content: Keep source-copy port when pages exist; when sourceSite.enabled and pages are empty, throw CONTENT_VALIDATION_FAILED; when reconstructing, do not fall back to home bodyText for an unmatched slug
    status: completed
  - id: T4
    content: Keep crawled CSS palette as design tokens and DESIGN_REASONING_FAILED when sourceSite.enabled and palette missing
    status: completed
  - id: T5
    content: Keep compact depth-1 nav plus crawled phone, sticky header, blue phone pill, inherit link color, ProseSection H2 from first crawled paragraph, CTA inspection headline
    status: completed
  - id: T6
    content: Keep unique source-photo assignment, /logo.* preference for global:logo, no tiny-wordmark penalty, gallery-first leftover photos
    status: completed
  - id: T7
    content: "When crawled pages exist, build DomainSpec identity from the crawl before any LLM: routes from crawled slugs, phone from tel:, palette from CSS, site_url set to https://safehavenrr-site.vercel.app; LLM may fill only vertical and keywords"
    status: completed
  - id: T8
    content: When reconstructing, skip generateFaqs; port FAQ pairs from the crawled FAQ page body or omit FAQPage; leave Organization and LocalBusiness as the existing CODE emitters
    status: completed
  - id: T9
    content: Add or keep unit tests for extract, skip LLM, empty-crawl fail-closed, unmatched-slug no home fallback, design fail-closed, logo versus OG, generate-spec crawl routes and site_url, schema FAQ skip
    status: completed
  - id: T10
    content: Rebuild Safe Haven from https://www.safehavenrr.com/ using the campaign clone; publish to cryptoxdog/safehavenrr-site; prove https://safehavenrr-site.vercel.app after hard refresh
    status: completed
  - id: T11
    content: Open a scoped PR on Quantum-L9/Website-Bot with the factory patches; run make verify-all; merge only via L4 plan Build after green
    status: completed
isProject: false
---

# PLAN: Website-Bot source-first reconstruction

> **Improved by** `kernels/Improve.md` from PLAN_DOCUMENT `WIP/website_bot_source_first_reconstruction.plan.json` (validator PASS).
> **Supersedes:** `website-bot-source-first-reconstruction_a1c5ccca.plan.md`
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** `@environment/program-execution` → Program Lock/Controller → `@autonomy` (subordinate).
> **Law:** status remains `draft` until PE Lock + capability probes at execute start. Do not free-form mutate from this markdown.

## Execute via @environment/program-execution + autonomy (required)

**Authority order (fail-closed — see `environment/agents/PEER_EXECUTION.md`):**

```text
this .plan.md  (intent / envelope / DAG / success properties)
        │ project
        ▼
@environment/program-execution   HOW work executes (authoritative)
  Blueprint → Program Lock → Controller admit/claim/render/verify/handoff
        │ lease (narrow-never-widen)
        ▼
root autonomy/  +  @autonomy (/autonomy → l9-bounded-autonomy)
  MAY the leased agent act?  (packet, lanes, PR poll) — owns_program_state: false
        │
        ▼
PE adapter (Cursor: cursor-foreground | cursor-background)
```

Program leases are authoritative. Autonomy leases are subordinate and **must not outlive** the Program lease.

### Pipeline steps

1. **Attach** [@environment/program-execution](environment/program-execution/) + [@autonomy](commands/autonomy.md).
2. **Project this plan → Blueprint artifacts** under `$HOME/.l9/programs/pes-website-bot-source-first/`.
3. **Validate + bootstrap Controller** (`pec.py bootstrap` / `reconcile` / `status` / `next`).
4. **Admit exact task scope** — Source Contract ⊂ Task Card ceiling; `claim` → `prepare` → `render-contract`.
5. **Map Program task → autonomy campaign.** `autonomy_action_id` = `pes.<wave>.<task>`.
6. **Orchestrate under [@autonomy](commands/autonomy.md)** — Protocols A–D. Spawn ready `work` Tasks; background `poll` after T11 PR. Main continues (no `AwaitShell` on poll).
7. **L4 local autonomy** inside the Program lease: local commits only until `ops/autonomy/l4_local.py authorize-release` → scoped push/PR → `l9-pr-remediation`. Launching this plan through PE+`/autonomy` **or** clicking Build **is** merge authorization for this stack after green+mergeable.
8. **Record + verify + handoff.** Graphiti PICKUP on close is observability only.

### Adapter routing

| Work class | Prefer |
|------------|--------|
| this Cursor plan default | `cursor-foreground` |
| Website-Bot implementation | `cursor-foreground` |
| verification | `ci-generic-shell` (`make verify-all`) |
| remote PR | `github-remote-actions` after L4 release |

### Campaign authorization packet (fill at execute — subordinate to Program Lock)

```yaml
packet_id: autonomy-2026-08-13-website-bot-source-first
authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
profile: pr-convergence
authority_profile: program_controller_bound
autonomous_merge: false
plan_ref: ~/.cursor/plans/website-bot-source-first-reconstruction_53b6c5ed.plan.md
plan_id: plan.website-bot.source-first-reconstruction.v1
schema_ref: canonical.schema.plan_document.v1
program_execution:
  root: environment/program-execution
  program_id: pes-website-bot-source-first
  adapter_id: cursor-foreground
  autonomy_provider_id: root-autonomy-control-plane
declared_prs: []
declared_branches: [feat/source-first-reconstruction]
allowed_inside_packet:
  - execute_rendered_contract_only
  - execute_plan_todos_inside_envelope
  - remediate_until_green
  - commit_scoped_on_declared_branch
  - push_non_force_declared_branch
  - inspect_ci_and_comments
forbidden_inside_packet:
  - widen_blueprint_or_task_card_ceiling
  - mutate_without_program_lease
  - outlive_program_lease
  - merge_outside_l4_plan_build_stack
  - force_push
  - admin_merge
  - expand_scope
  - commit_secrets
  - weaken_tests_for_green
  - direct_graphiti_task_claim
  - recreate_campaign_directory
  - godaddy_dns_cutover
  - invent_website_bot_pr_check_target
created_by: "/autonomy+program-execution"
```

### Phase-0 action table ↔ PE Task Cards

| id | pe_task_id | wave | depends_on | mutation | lock_keys | isolation_key | autonomy_action_id | kind | adapter_hint |
|----|------------|------|------------|----------|-----------|---------------|--------------------|------|--------------|
| T1 | TASK-001 | W0 | [] | false | `repo:HEAD` | `preflight` | `pes.w0.t1` | `work` | `cursor-foreground` |
| T2 | TASK-002 | W1 | [T1] | false | `path:src/ingestion` | `prove` | `pes.w1.t2` | `work` | `cursor-foreground` |
| T3 | TASK-003 | W1 | [T2] | true | `path:src/stages/Content` | `mutate` | `pes.w1.t3` | `work` | `cursor-foreground` |
| T4 | TASK-004 | W1 | [T2] | false | `path:src/stages/Design` | `prove` | `pes.w1.t4` | `work` | `cursor-foreground` |
| T5 | TASK-005 | W1 | [T3] | false | `path:astro_template` | `prove` | `pes.w1.t5` | `work` | `cursor-foreground` |
| T6 | TASK-006 | W1 | [T2] | false | `path:src/services/images` | `prove` | `pes.w1.t6` | `work` | `cursor-foreground` |
| T7 | TASK-007 | W2 | [T2] | true | `path:scripts/generate-spec.ts` | `mutate` | `pes.w2.t7` | `work` | `cursor-foreground` |
| T8 | TASK-008 | W2 | [T3] | true | `path:src/stages/Schema` | `mutate` | `pes.w2.t8` | `work` | `cursor-foreground` |
| T9 | TASK-009 | W3 | [T2, T3, T4, T6, T7, T8] | true | `evidence:unit` | `validate` | `pes.w3.t9` | `work` | `ci-generic-shell` |
| T10 | TASK-010 | W3 | [T5, T7, T9] | true | `vercel:safehavenrr-site` | `validate` | `pes.w3.t10` | `work` | `cursor-foreground` |
| T11 | TASK-011 | W4 | [T10] | true | `pr:Website-Bot` | `converge` | `pes.w4.t11` | `work` | `github-remote-actions` |

**Stop / do not execute when:** plan status is not `executable` after PE Lock; Website-Bot HEAD ≠ locked SHA; request includes GoDaddy cutover; request recreates the campaign directory; request adds a Website-Bot `pr-check` Makefile target.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.website-bot.source-first-reconstruction.v1` |
| name | Website-Bot source-first reconstruction |
| schema_version | `1.0.0` |
| status | `draft` |
| is_project | `false` |
| created_at | `2026-08-13` |
| updated_at | `2026-08-13` |
| depth | `standard` |
| improve_pass | `kernels/Improve.md` on plan artifacts (not Website-Bot product code) |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | Website-Bot SourceSiteManifest + DomainSpec; campaign source inspected 2026-08-13 |
| plan_class | `bounded_execution_contract` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Wrap/prove T2 T4 T5 T6. Mutate only remaining holes T3 T7 T8. Execute via PE + subordinate @autonomy. |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-08-13T16:12:00-04:00` |
| repository | `Quantum-L9/Website-Bot` |
| workspace | `/Users/macm2/dev/website-bot-e2e-full-feature-20260813/repos/Website-Bot` |
| ssot_clone | `/Users/macm2/Cursor-Governance/Cursor-Governance` (planning only) |
| campaign | `/Users/macm2/dev/website-bot-e2e-full-feature-20260813/` — reuse; do not recreate |
| branch | `e2e-full-feature-20260813` |
| commit_sha | `c0ee7eacc4837ecd29fce379f69aa856f6259fce` |
| dirty | `true` |
| allowed_local_dirt | extract/design/assembler/template/image-planner patches (T2 T4 T5 T6). Content still has home-copy fallback. generate-spec still calls designReasoning. Schema FAQ still calls generateSchema. |
| overlap_policy | `explicitly_allow_listed_paths` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` if origin/main SHA moved or campaign dir missing |

## Objective

### Mission

Kyle's live roofing site is professional (black / `#1ca0e0` / white, job photos, `(704) 648-7252`). The factory's first deploy was unshowable because crawl discarded evidence and LLM stages invented a green brochure. **Keep** the campaign patches that already port extract/design/chrome/photos. **Delete** the remaining invention paths named in T3 T7 T8. Prove the Vercel alias. PR Quantum-L9/Website-Bot. Website-Bot gate is `make verify-all`.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Reconstructing with pages does not call generateContent; matching slug only | runtime_behavior | `tests/unit/content-generation.test.ts` prompts.length === 0 | true |
| SP-02 | sourceSite.enabled and empty pages throws CONTENT_VALIDATION_FAILED | runtime_behavior | content-generation empty-crawl test | true |
| SP-03 | Unmatched reconstructing slug does not receive home bodyText | runtime_behavior | content-generation unmatched-slug test | true |
| SP-04 | sourceSite.enabled without palette throws DESIGN_REASONING_FAILED | runtime_behavior | `tests/unit/source-palette.test.ts` | true |
| SP-05 | Phones + nav persisted; incomplete cache refused | structural | `tests/unit/page-extractor.test.ts` | true |
| SP-06 | global:logo is /logo.webp not OG | structural | `tests/unit/image-asset-planning-source.test.ts` | true |
| SP-07 | Compact nav ≤ 8, crawled phone, tokens #1ca0e0 on black | filesystem | siteConfig.ts + tokens.css | true |
| SP-08 | generate-spec routes ⊆ crawled slugs; site_url is Vercel alias | structural | generate-spec overlay + `generated-spec/safehavenrr.yaml` | true |
| SP-09 | Reconstructing schema does not call generateFaqs | structural | `tests/unit/schema-generator.test.ts` | true |
| SP-10 | Production alias hard-refresh matches source look; no repeated home essay | network_observation | https://safehavenrr-site.vercel.app | true |
| SP-11 | PR exists; `make verify-all` PASS | quality_gate | Website-Bot `make verify-all` | true |

## Capability preflight

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.website-bot.source-first-reconstruction.v1` |
| blocking | `true` |

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `branch_and_HEAD_resolution` | `git -C .../Website-Bot rev-parse HEAD` | equals `c0ee7eacc4837ecd29fce379f69aa856f6259fce` | true |
| CP-02 | `campaign_reuse` | campaign Website-Bot `node_modules` present | campaign exists; do not clone | true |
| CP-03 | `command_available` | `node --version` and `gh --version` | node + gh present | true |
| CP-04 | `filesystem_write` | Website-Bot `src/` `astro_template/` `tests/unit/` `scripts/generate-spec.ts` writable | write probe | true |
| CP-05 | `dns_out_of_envelope` | GoDaddy remains out | Vercel alias is the showable URL | true |
| CP-06 | `website_bot_gate` | `grep pr-check Makefile` in Website-Bot | no target; use `make verify-all` | true |

## Execution envelope

### Filesystem

- **write_allow:** Website-Bot `src/`, `astro_template/`, `scripts/generate-spec.ts`, `tests/unit/`; campaign `generated-spec/safehavenrr.yaml`; Cursor-Governance `skills/l9-e2e-blocker-resolution/references/campaign-reuse.md`
- **write_deny:** `CANONICAL_LAW.md`, `AGENTS.md`, `ORG_INVARIANTS.yaml`, `pyproject.toml`, campaign `.env`, Website-Bot `.env`, Docker compose for seo-bot-data, Website-Bot Makefile (do not add pr-check)
- **delete_allow:** none

### Commands

- **allow:** `node --import tsx --test …`, `make verify-all`, `npm run pipeline:end-to-end -- --spec=…`, `gh pr create`, `l4_local.py` after kernels
- **deny:** force-push, history rewrite, Docker kill of postgres/redis, GoDaddy API, copying campaign `.env`, inventing `make pr-check` on Website-Bot

### Network

| Field | Value |
|-------|-------|
| mode | `bounded_external_write` |
| allowed_services | `https://www.safehavenrr.com/` (crawl), GitHub `cryptoxdog/safehavenrr-site` + `Quantum-L9/Website-Bot`, Vercel `safehavenrr-site`, OpenRouter only for unresolved OG gap slots |

### Secrets

| Field | Value |
|-------|-------|
| access | `read_only_named` (`openclaw-igorbot/github#token`, existing campaign Vercel/OpenRouter env — never print values) |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false`

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_read` | `safe_to_repeat` | `none` | null | false |
| T2 | `filesystem_read` | `safe_to_repeat` | `none` | null | false |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore scoped paths | false |
| T4 | `filesystem_read` | `safe_to_repeat` | `none` | null | false |
| T5 | `filesystem_read` | `safe_to_repeat` | `none` | null | false |
| T6 | `filesystem_read` | `safe_to_repeat` | `none` | null | false |
| T7 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore generate-spec.ts and yaml | false |
| T8 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore SchemaGeneratorStage | false |
| T9 | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | restore tests | false |
| T10 | `network_write` | `safe_with_dedupe` | `manual_only` | leave last good Vercel production SHA | false |
| T11 | `network_write` | `safe_with_dedupe` | `manual_only` | close or abandon PR | false |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T3 | content reconstruction | `runtime` | ContentGenerationStage | home-copy fallback; LLM when enabled+empty |
| T7 | spec identity | `runtime` | generate-spec.ts | LLM-first DomainSpec; site_url igorbeylin.com |
| T8 | schema reconstruction | `runtime` | SchemaGeneratorStage.generateFaqs | rewriting Organization/LocalBusiness CODE path |
| T10 | Safe Haven publish | `external_system` | Vercel alias | GoDaddy; stale dpl cards as proof |
| T11 | Quantum-L9/Website-Bot | `control_plane` | GitHub PR | force-push / admin-merge / fake pr-check target |

## Rollback

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.website-bot.source-first-reconstruction.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Website-Bot write_allow only; close PR if opened |
| data | `none` | |
| external_state | `manual_recovery` | leave last good Vercel production SHA; do not touch GoDaddy |
| local_state | `git_restore_scoped_paths` | keep campaign clone and image cache |

Irreversible operations: none in envelope.

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` |
| uncertainty | `medium` |
| blast_radius | `high` |
| architectural_boundaries_crossed | `1` |
| external_systems_touched | `3` |
| migration_required | `false` |
| unknown_dependency_count | `2` |

## Execution DAG

| id | owner | layer | depends_on | outputs |
|----|-------|-------|------------|---------|
| T1 | agent | assurance | [] | baseline receipt |
| T2 | agent | runtime | [T1] | extract keep-and-prove |
| T7 | agent | runtime | [T2] | crawl-first spec + Vercel site_url |
| T3 | agent | runtime | [T2] | fail-closed content; no home fallback |
| T4 | agent | runtime | [T2] | design keep-and-prove |
| T5 | agent | runtime | [T3] | chrome keep-and-prove |
| T6 | agent | runtime | [T2] | photos keep-and-prove |
| T8 | agent | runtime | [T3] | FAQ LLM skip |
| T9 | agent | assurance | [T2, T3, T4, T6, T7, T8] | unit tests PASS |
| T10 | agent | external_system | [T5, T7, T9] | Vercel alias proof |
| T11 | agent | control_plane | [T10] | Quantum-L9/Website-Bot PR |

**Critical path:** T1 → T2 → T7 → T3 → T5 → T9 → T10 → T11

**Forbidden edges:** T10 before T9; T11 before T10; GoDaddy node; clone-new-campaign; add-pr-check-target.

## Property evidence matrix

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `runtime_behavior_evidence` | unit test | content-generation reconstructing | prompts.length === 0 | `not_run` |
| EV-SP-02 | SP-02 | `runtime_behavior_evidence` | unit test | content-generation empty crawl | CONTENT_VALIDATION_FAILED | `not_run` |
| EV-SP-03 | SP-03 | `runtime_behavior_evidence` | unit test | unmatched slug | body ≠ home body | `not_run` |
| EV-SP-04 | SP-04 | `runtime_behavior_evidence` | unit test | source-palette | DESIGN_REASONING_FAILED | `not_run` |
| EV-SP-05 | SP-05 | `structural_evidence` | unit test | page-extractor | phones + nav | `not_run` |
| EV-SP-06 | SP-06 | `structural_evidence` | unit test | image-asset-planning-source | logo.webp | `not_run` |
| EV-SP-07 | SP-07 | `filesystem_evidence` | inspect | siteConfig.ts | phone + nav ≤ 8 | `not_run` |
| EV-SP-08 | SP-08 | `structural_evidence` | overlay | generate-spec + safehavenrr.yaml | routes from crawl; site_url alias | `not_run` |
| EV-SP-09 | SP-09 | `structural_evidence` | unit test | schema-generator reconstructing | generateSchema not called | `not_run` |
| EV-SP-10 | SP-10 | `network_observation_evidence` | hard-refresh | https://safehavenrr-site.vercel.app | look match | `not_run` |
| EV-SP-11 | SP-11 | `quality_gate_evidence` | verify-all | `make verify-all` | PASS | `not_run` |
| EV-BASE | baseline | `repository_state_evidence` | rev-parse | Website-Bot HEAD | `c0ee7eacc4837ecd29fce379f69aa856f6259fce` | `not_run` |

## Stress and disconfirm

- If generate-spec still LLM-first, do invented `/services/*` slugs still receive home bodyText?
- If sourceSite.enabled and crawl is empty, does content still invent a brochure?
- If site_url stays `https://igorbeylin.com`, do receipts claim a parked domain?
- If execute runs `make pr-check` inside Website-Bot, does the gate fail because the target does not exist?
- If origin/main never receives the PR, does the next campaign rebuild the invented-green path?

Assumptions that must remain true: campaign clone exists; safehavenrr.com crawlable; Vercel alias is the showable URL; no GoDaddy secret; greenfield LLM paths stay; Website-Bot gate is `make verify-all`.

Rollback: restore scoped Website-Bot paths; close PR; leave last good Vercel SHA; do not touch GoDaddy; do not delete the campaign clone.

## Out of scope

- GoDaddy DNS cutover for igorbeylin.com
- SEO / Search Console
- Recreating the campaign dir or copying campaign `.env`
- Killing Docker seo-bot-data postgres/redis
- Cursor-Governance root protected files
- Force-push, history rewrite, admin-merge
- Hand-editing site-output HTML
- Gemini except OG gap slots
- Palette redesign
- Adding a Website-Bot `make pr-check` target
- Rewriting Organization/LocalBusiness JSON-LD (already CODE)

## Follow-on milestone

| priority | change | why |
|----------|--------|-----|
| P1 | GoDaddy DNS cutover | no vault secret; Vercel alias is the showable URL |
| P2 | SEO / Search Console | user deferred; eyes first |
| P3 | Greenfield LLM path quality | reconstruction must not wait on brochure-from-scratch |

## Convergence

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.website-bot.source-first-reconstruction.v1` |
| current_state | `partial` |
| implementation_ready | `false` until PE Lock + CP-01..CP-06 |

- **executable_when:** PE Blueprint accepted; HEAD still locked SHA; campaign clone present
- **complete_when:** EV-SP-01..11 passed; alias visual match; PR open; `make verify-all` PASS
- **blocking_conditions:** LLM still called when source pages exist; home-copy fallback remains; site_url still igorbeylin.com

| kind | id | note | resolution |
|------|----|------|------------|
| unknown | U1 | generate-spec residual LLM for vertical/keywords | accept_bounded |
| unknown | U2 | CODEOWNERS / greenfield tests after fail-closed reconstruction | probe |

| Field | Value |
|-------|-------|
| minimum_safe_next_action | attach @environment/program-execution + /autonomy — do not free-form execute |
| execute_via | `@environment/program-execution` → Program Lock/Controller → `@autonomy` (`/autonomy` → `l9-bounded-autonomy`) |
| next_skill | `/autonomy` |

## Scope (from PLAN_DOCUMENT)

**In:** reuse campaign Website-Bot clone; Wrap/prove T2 T4 T5 T6; mutate T3 T7 T8; tests; Safe Haven alias proof; PR.

**Out:** listed under Out of scope.
