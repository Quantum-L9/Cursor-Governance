---
name: LLM-Router capability-integrity hardening (next 1.1.x patch)
overview: "Make it impossible for LLM-Router callers to request capabilities the selected execution path silently drops. Land one canonical capability resolver plus one validation authority, refactor resolveRoute and dispatch to consume a single capability decision, fail closed on vision+search, vision-without-images, images-on-non-vision, search-modifiers-without-search, and consensus-without-search, rem..."
todos:
  - id: T00
    content: "Create branch campaign/7-router-capability-integrity from origin/main c47c0248f603786fea2e14ce4a9dcc7ea1c5ea40 in LLM-Router. Bind the full SHA. Do not base on campaign/7-router-search-policy (PR #55 is CONFLICTING and superseded). Do not rebase, do not merge PR #55 content in, and do not mutate product files until the branch is bound."
    status: pending
    phase: execute
    depends_on: []
  - id: T01
    content: "Fix 1 — canonical capability resolver. Add ResolvedCapabilities { searchRequired, searchPolicySource, visionRequired, imagesProvided } and resolveCapabilities(task) to src/matrices/search-policy.ts; move VISION_TASKS there from src/index.ts; keep requiresSearchProvider and isSearchTask semantics unchanged. Export resolveCapabilities and ResolvedCapabilities from src/index.ts. Do not change requiresSearch precedence (explicit boolean wins, undefined falls back to TaskType default)."
    status: pending
    phase: execute
    depends_on: [T00]
  - id: T02
    content: "Fix 2 — fail-closed validation authority. Add validateCapabilities(capabilities) throwing UnsupportedCapabilityCombinationError for: searchRequired+visionRequired (SEARCH_VISION_COMBINATION_UNSUPPORTED, keep the existing main code name), visionRequired without imagesProvided (VISION_INPUT_REQUIRED), imagesProvided without visionRequired (IMAGES_NOT_SUPPORTED_FOR_TASK). Extend the existing error class code union additively and keep its current constructor signature working; fold assertSearchVisionCompatible into validateCapabilities and keep the exported shim delegating for compatibility. Call validateCapabilities inside resolveRoute before any provider/model resolution."
    status: pending
    phase: execute
    depends_on: [T01]
  - id: T03
    content: "Fix 3 + Fix 7 — one decision consumed by routing and dispatch, with capability evidence on the public resolution. Add visionRequired to RoutingResolution (additive; imagesProvided stays internal to the capabilities module and is not spread onto the public contract). resolveRoute returns capabilities on every branch. dispatchProvider branches on decision.searchRequired and decision.visionRequired with asserts: searchRequired implies provider PERPLEXITY, visionRequired implies provider OPENROUTER and non-empty images. Delete the second task reinterpretation (VISION_TASKS.has(task.type) && images?.length) and the now-unreachable images?.length ?? 1 fallback."
    status: pending
    phase: execute
    depends_on: [T01, T02]
  - id: T04
    content: "Fix 4 — impossible-state guard. Add a guard at the top of resolvePerplexityConfig: throw when requiresSearchProvider(task) is false, so provider config and routing authority agree. disableSearch: false already landed on main (perplexity-matrix.ts line 64); keep it and its comment. Do not remove the field from PerplexityConfig (public contract, direct-provider compatibility)."
    status: pending
    phase: execute
    depends_on: [T01]
  - id: T05
    content: "Fix 5 — search-modifier validation. After capability resolution, throw SEARCH_MODIFIER_WITHOUT_SEARCH when recency or a non-empty domainFilter is present but searchRequired is false. The schema stays permissive; this is runtime contract enforcement. RequiresSearch=false plus domainFilter becomes an explicit contract error."
    status: pending
    phase: execute
    depends_on: [T02]
  - id: T06
    content: "Fix 6 — consensus requires a search-backed route. In execute(), after route resolution and before budget reservation, throw CONSENSUS_REQUIRES_SEARCH when options.consensus is true and decision.searchRequired is false. Consensus stays a search execution modifier, never hidden routing authority. Do not change the existing variations>1 dispatch condition inside the Perplexity branch."
    status: pending
    phase: execute
    depends_on: [T03]
  - id: T07
    content: "Fix 8 — failed routed calls are auditable. Add optional outcome ('SUCCESS'|'FAILED'), failureKind (reuse ProviderFailureKind union from src/types.ts), and errorCode to RoutingDecision (additive). On success keep the existing push with outcome SUCCESS. In the execute() catch path after route resolution, set outcome FAILED plus classified failureKind/errorCode and push before rethrowing; budget/circuit pre-provider failures map to failureKind local/unknown with the error name as errorCode. Never log prompt, API key, authorization header, or image contents."
    status: pending
    phase: execute
    depends_on: [T03]
  - id: T08
    content: "Proof wave — extend tests/routing-matrix.test.ts to the full 14-row contract matrix (8 route rows, 6 fail rows) and add capability-integrity coverage: validation throws occur before budget reservation and before any provider call (assert via injected fake clients), dispatch asserts, modifier and consensus throws, FAILED callLog entries with classified kinds, and no prompt data in call log entries. Run npm run verify:all and fix any real regression without weakening existing budget/circuit/fallback/image-safety assertions. Do not touch src/budget, src/circuit-breaker.ts, transports, src/pricing.ts, or vision internals."
    status: pending
    phase: execute
    depends_on: [T02, T03, T04, T05, T06, T07]
  - id: T09
    content: "Release wave — run npm run verify:all and npm pack; check the npm registry for the highest published 1.1.x (npm view, network read; fail closed on error — never assume the next number); bump package.json to the next unused patch; human checkpoint before npm publish (NPM_TOKEN via l9-aws-secrets, never printed); ephemeral install of the packed tarball into Website-Bot and SEO-Bot with consumer compile/test PASS; pin the exact published version in both bots' package.json and package-lock.json. Final invariant: Website-Bot installed Router == SEO-Bot installed Router == new verified patch."
    status: pending
    phase: execute
    depends_on: [T08]
  - id: T10
    content: "Docs — update ARCHITECTURE.md and README.md routing sections to the single authority chain (TaskDescriptor → resolve capabilities → validate → resolve provider/model → reserve budget → dispatch EXACT resolved capability), document the fail-closed error codes and the RoutingDecision audit fields, and note the patch-release behavior change (invalid capability combinations now throw instead of silently degrading). Do not rewrite unrelated architecture prose."
    status: pending
    phase: execute
    depends_on: [T09]
isProject: false
---

# PLAN: LLM-Router capability-integrity hardening (next 1.1.x patch)

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** `@environment/program-execution` → Program Lock/Controller → `@autonomy` (subordinate).
> **Suggested filename:** `llm-router-capability-integrity-hardening-next-1-1-x-patch_98afbbbf.plan.md`

## Objective (from PLAN_DOCUMENT)

Make it impossible for LLM-Router callers to request capabilities the selected execution path silently drops. Land one canonical capability resolver plus one validation authority, refactor resolveRoute and dispatch to consume a single capability decision, fail closed on vision+search, vision-without-images, images-on-non-vision, search-modifiers-without-search, and consensus-without-search, remove the impossible Perplexity disableSearch state, add capability evidence and failure outcomes to RoutingDecision, keep every mature piece (budget, circuit, fallback, transport, pricing, taxonomy, provider inventory) untouched, then publish the next unused 1.1.x patch and pin the exact same version in Website-Bot and SEO-Bot.

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | resolveCapabilities(task) is the single internal capability authority; resolveRoute and dispatchProvider consume one RoutingDecision and never re-derive search/vision from the raw task (grep evidence: VISION_TASKS referenced only inside src/matrices/search-policy.ts) | quality_gate | observe during PE verify / make pr-check | true |
| SP-02 | Every route resolution carries searchRequired, searchPolicySource (EXPLICIT|TASK_DEFAULT), and visionRequired on RoutingResolution; RoutingDecision exposes outcome plus failureKind/errorCode on post-route-resolution failures | quality_gate | observe during PE verify / make pr-check | true |
| SP-03 | All five unsupported-combination codes throw before budget reservation and before provider dispatch: SEARCH_VISION_COMBINATION_UNSUPPORTED, VISION_INPUT_REQUIRED, IMAGES_NOT_SUPPORTED_FOR_TASK, SEARCH_MODIFIER_WITHOUT_SEARCH, CONSENSUS_REQUIRES_SEARCH | quality_gate | observe during PE verify / make pr-check | true |
| SP-04 | The full 14-row routing matrix from the contract passes: 8 route rows (3 STRATEGIC_REASONING, 3 COMPETITOR_RESEARCH, 2 SCREENSHOT_ANALYSIS, 1 consensus-on-search) and 6 fail rows (SEARCH_VISION, VISION_INPUT_REQUIRED, IMAGES_NOT_SUPPORTED, SEARCH_MODIFIER, CONSENSUS_REQUIRES_SEARCH plus SEARCH+CONSENSUS success) | quality_gate | observe during PE verify / make pr-check | true |
| SP-05 | resolvePerplexityConfig throws for any non-search task and disableSearch stays false on every router-built PerplexityConfig | quality_gate | observe during PE verify / make pr-check | true |
| SP-06 | getCallLog() records FAILED entries (outcome, failureKind, errorCode) for failures after route resolution without logging prompt, API key, authorization header, or image contents | quality_gate | observe during PE verify / make pr-check | true |
| SP-07 | npm run verify:all PASS on the capability-integrity branch (build, strict types, declaration-consumer compile, lint, lint:boundary, tests, audit, package verify) | quality_gate | observe during PE verify / make pr-check | true |
| SP-08 | npm pack produces the tarball; ephemeral install in Website-Bot and SEO-Bot compiles and passes tests against the packed artifact | quality_gate | observe during PE verify / make pr-check | true |
| SP-09 | The next unused 1.1.x patch is published after a human checkpoint and registry-version verification (never assumed), then pinned as the exact same version in both bots | quality_gate | observe during PE verify / make pr-check | true |
| SP-10 | Budget, circuit, fallback, image-safety regression suites stay green with no changes to src/budget, src/circuit-breaker.ts, provider transports, src/pricing.ts, or src/vision internals | quality_gate | observe during PE verify / make pr-check | true |

## Scope (from PLAN_DOCUMENT)

**In:** Quantum-L9/LLM-Router: new branch campaign/7-router-capability-integrity from origin/main c47c0248f603786fea2e14ce4a9dcc7ea1c5ea40 (package version 1.1.3 baseline), src/matrices/search-policy.ts (Replace+Create): resolveCapabilities, ResolvedCapabilities, validateCapabilities, VISION_TASKS canonical home, UnsupportedCapabilityCombinationError code-union extension, src/index.ts (Replace): resolveRoute consumes validated capabilities and returns them; dispatchProvider branches on decision.searchRequired/decision.visionRequired with provider and images asserts; execute() consensus check before budget reservation; failure audit logging in the catch path, src/types.ts (Replace, additive only): RoutingResolution.visionRequired; RoutingDecision outcome/failureKind/errorCode optional fields, src/matrices/perplexity-matrix.ts (Replace): throw when resolvePerplexityConfig is called for a non-search task, tests/routing-matrix.test.ts (extend to full 14 rows), tests/search-policy.test.ts (extend), tests/capability-integrity.test.ts (Create), package.json version bump to the registry-verified next unused 1.1.x patch, ARCHITECTURE.md and README.md routing authority-chain documentation, Website-Bot package.json + package-lock.json and SEO-Bot package.json + package-lock.json: pin the exact published patch (release wave only, after publish)

**Out:**
- src/budget/** and any budget semantics (reservation, reconciliation, throttling, surge)
- src/circuit-breaker.ts behavior
- src/providers/openrouter.ts and src/providers/perplexity.ts transport internals
- src/pricing.ts, src/matrices/general-matrix.ts and perplexity-matrix.ts pricing/selection tables
- src/vision/index.ts resolveVisionConfig logic
- src/control-plane/**
- src/schemas.ts (schema stays permissive; runtime validation is the new authority)
- TaskType taxonomy, provider inventory, SonarModel/GeneralModel enums
- Direct provider subpath exports (deprecated, kept for 1.x compatibility)
- campaign/7-router-search-policy branch and PR #55 content (conflicting with main, superseded by this plan; disposition via l9-pr-remediation, never stacked onto or rebased)
- npm major/minor release, public API removal, or re-export of the deprecated direct provider subpaths
- WIP/Llm Router Contract.md (intent source document, not a product surface)

## Critical path (seed)

T00 → T01 → T02 → T03 → T06 → T08 → T09 → T10

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: Router capability resolution, dispatch, the public RoutingResolution/RoutingDecision contracts, the call log, and consumer package pins. A wrong throw code rejects valid consumer traffic; a wrong dispatch assert crashes at runtime instead of degrading. Budget/circuit/fallback/transport code is untouched, so their regression surface is bounded to call-log length assertions.
- Rollback: Drop the branch — no revert of main. If the patch is already published: re-pin both bots back to 1.1.3 and deprecate the patch on npm (deprecate, never unpublish). No force-push, no rebase, no admin-merge.

## Convergence (seed)

- status: partial
- next_skill: l9-ynp
- stop_reason: PLAN_DOCUMENT validates and the PE+autonomy blueprint projects. Pre-validation P5 and all final validations remain pending until execute. PR #55 disposition and npm publish are human-gated. Do not implement from this markdown alone; execution flows through @environment/program-execution + @autonomy under a Program lease.
- execute_via: @environment/program-execution → @autonomy

---

## Template body (complete every required section before status=executable)

# PLAN: LLM-Router capability-integrity hardening (next 1.1.x patch)

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Execute:** when status is `executable`, run through **[@environment/program-execution](environment/program-execution/)** with autonomy as the subordinate orchestration plane — **[@autonomy](commands/autonomy.md)** / `l9-bounded-autonomy` under a Program lease. Do **not** free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to PE Task Cards + Phase-0 autonomy actions. Body is the binding contract.
> **Rename to:** `snake_case_name_<8hex>.plan.md` before execute.
> **Law:** executable only when baseline matches, capability probes pass, invariants match, and envelope is respected. Markdown completeness alone is insufficient.

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
Peer Execution Core -> thin provider
  (Cursor: cursor-foreground | cursor-background;
   Claude: claude-code-direct)
```

Program leases are authoritative. Autonomy leases are subordinate and **must not outlive** the Program lease (`COMPATIBILITY.yaml` / autonomy-control-plane bridge). Never invent a second scheduler; never widen Blueprint ceilings via the campaign packet.

### Pipeline steps

Live execution is one command. Do not hand-run pec, L4, or inner compile
scripts from this template.

```bash
make -C "$HOME/.cursor-governance" campaign INTENT=<brief.md|activate.yaml>
```

`run_campaign.py` projects the plan into Blueprint artifacts under
`$HOME/.l9/programs/<id>/`, admits the lock, executes every task, stacks
PRs, and closes into `campaigns/COMPLETED/<id>/`. Never mutate sealed
`environment/program-execution/core/` templates in place.

| Plan section | Runner-owned Blueprint / Controller artifact |
|--------------|-------------------------------------|
| metadata / objective | `PROGRAM.yaml` / program identity |
| immutable_baseline | `CURRENT_STATE_DELTA` + reconcile exact SHA |
| execution_envelope + architecture_impact | Task Card `authorization_ceiling` + Source/Rendered Contract paths |
| execution_DAG / todos | `DEPENDENCY_GRAPH.yaml` + `TASK_CARDS.yaml` + `EXECUTION_WAVES.yaml` |
| capability_preflight | Controller reconcile + gate probes before claim |
| property_evidence_matrix | Task Card `validation` / evidence catalog refs |
| rollback | Task Card `rollback` + recovery receipts |
| convergence | `CONVERGENCE_GATES.yaml` + Handoff Receipt (owner accepts verdict) |

If the runner exits nonzero, stop and report. Do not continue with
`pec.py bootstrap`, `claim`, `record-attempt`, or a second scheduler.

### Adapter routing (from `registry/EXECUTION_ROUTING_POLICY.yaml`)

| Work class | Prefer |
|------------|--------|
| interactive local repair (this Cursor plan default) | `cursor-foreground` → `claude-code-direct` |
| repository implementation | `claude-code-direct` → `cursor-background` → `cursor-foreground` |
| verification | `ci-github-actions` / `ci-generic-shell` |
| remote PR/merge actions | `github-remote-actions` only with exact approval |

### Campaign authorization packet (fill at execute — subordinate to Program Lock)

```yaml
packet_id: autonomy-<YYYY-MM-DD>-<n>
authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
profile: pr-convergence            # or program_deploy_max_autonomy when PES Phase-0 selects it
authority_profile: program_controller_bound
autonomous_merge: false            # COMPATIBILITY forbidden; L4 plan/PE stack merge after green+mergeable
plan_ref: <this .plan.md path>
plan_id: plan.<domain>.<slug>.v1
schema_ref: canonical.schema.plan_document.v1
program_execution:
  root: environment/program-execution
  program_id: pes-<slug>
  program_lock_digest: <sha256 from Controller>
  blueprint_ref: $HOME/.l9/programs/<program_id>/blueprint
  runtime_ref: $HOME/.l9/programs/<program_id>/runtime
  provider_ref: cursor-foreground  # or routed thin provider
  execution_profile_ref: worker-default
  autonomy_provider_id: root-autonomy-control-plane
declared_prs: []
declared_branches: [<feature-branch>]
allowed_inside_packet:
  - execute_rendered_contract_only
  - execute_plan_todos_inside_envelope
  - remediate_until_green
  - commit_scoped_on_declared_branch
  - push_non_force_declared_branch   # only after L4 release_authorized
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
created_by: "/autonomy+program-execution"
```

### Phase-0 action table ↔ PE Task Cards

Derive from frontmatter todos + `execution_DAG`. Each row is both an autonomy action and a PE Task Card projection.

| id  | pe_task_id | wave | depends_on | mutation | lock_keys   | isolation_key | autonomy_action_id      | kind | adapter_hint    |
|-----|------------|------|------------|----------|-------------|---------------|-------------------------|------|-----------------|
| T00 | PES/T00    | W0   | []         | bind     | router      | branch:new    | act-00-bind             | work | foreground      |
| T01 | PES/T01    | W1   | [T00]      | mutate   | router      | path:policy   | act-01-resolver         | work | claude-code     |
| T02 | PES/T02    | W1   | [T01]      | mutate   | router      | path:policy   | act-02-validate         | work | claude-code     |
| T03 | PES/T03    | W2   | [T01,T02]  | mutate   | router      | path:index    | act-03-single-decision  | work | claude-code     |
| T04 | PES/T04    | W2   | [T01]      | mutate   | router      | path:perplex  | act-04-perplexity-guard | work | claude-code     |
| T05 | PES/T05    | W2   | [T02]      | mutate   | router      | path:index    | act-05-modifiers        | work | claude-code     |
| T06 | PES/T06    | W2   | [T03]      | mutate   | router      | path:index    | act-06-consensus        | work | claude-code     |
| T07 | PES/T07    | W2   | [T03]      | mutate   | router      | path:index    | act-07-audit            | work | claude-code     |
| T08 | PES/T08    | W3   | [T02-T07]  | prove    | router      | path:tests    | act-08-proof            | work | ci-shell        |
| T09 | PES/T09    | W4   | [T08]      | release  | router,bots | path:pkgs     | act-09-release          | work | remote-approval |
| T10 | PES/T10    | W4   | [T09]      | docs     | router      | path:docs     | act-10-docs             | work | claude-code     |

PES/Tnn projects to PE task id `pes-llm-router-cap-integrity/Tnn`; `remote-approval` = github-remote-actions only with exact approval (T09 publish).

**Spawn rules:** PE `claim`/`render` first for mutation rows; then @autonomy Protocol A (ready `work` Tasks in one message) / B (`poll` + `run_in_background: true`) / C (join) / D (PICKUP). Autonomy must not bypass wave order or Program Lock drift checks (`program_lock_stale_or_invalid` → stop).

**Stop / do not execute when:** plan status ≠ `executable`; PE Blueprint not accepted / Controller not bootstrapped; Program Lock drift; capability preflight blocked; DAG cyclic; envelope or Task Card ceiling incomplete; blocking unknowns remain; autonomy revoke / lease expired.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.llm-router.capability-integrity.v1` |
| name | *(same as frontmatter `name`)* |
| overview | *(same as frontmatter `overview`)* |
| schema_version | `1.0.0` |
| status | `draft` |
| is_project | `false` *(frontmatter `isProject`)* |
| owner | campaign 7-ROUTER |
| created_at | `2026-08-17` |
| updated_at | `2026-08-17` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | `ARCHITECTURE.md` routing sections in Quantum-L9/LLM-Router (updated in T10) |
| plan_class | `remediation_plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via @environment/program-execution + subordinate @autonomy; capability-integrity hardening only — budget, circuit, fallback, transport, pricing, taxonomy, provider inventory stay untouched (contract Fix 9) |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-08-17T23:05:00Z` (plan compile time) |
| repository | `Quantum-L9/LLM-Router` |
| workspace | `/Users/macm2/LLM-Router` |
| ssot_clone | n/a (target repo is its own clone) |
| branch | `campaign/7-router-capability-integrity` (created at T00 from origin/main) |
| commit_sha | `c47c0248f603786fea2e14ce4a9dcc7ea1c5ea40` (PLAN-SCHEMA-001) |
| dirty | `false` (baseline is clean origin/main; the dirty campaign/7-router-search-policy working tree is never touched) |
| artifact_hashes | `{ "package.json": "version 1.1.3 (baseline, unhashed at plan time)" }` |
| allowed_local_dirt | none on the new branch |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

LLM-Router (v1.1.3) can silently drop capabilities a caller explicitly requested: a search+vision combination loses vision on the Perplexity branch, a vision task without images degrades to text-only completion, images on non-vision tasks are ignored, search-only modifiers and consensus are silently discarded off the search branch, and failed routed calls leave no audit trace. Make it impossible to express what the execution plane cannot honor: one canonical capability resolver plus one validation authority, a single decision consumed by both resolveRoute and dispatch, fail-closed throws for every unsupported combination, capability evidence and failure outcomes on RoutingDecision, and a registry-verified 1.1.x patch pinned identically in Website-Bot and SEO-Bot. Non-negotiable preserved contracts: requiresSearch explicit-boolean precedence, budget reservation before dispatch and reconciliation after, provider circuit breaking, bounded fallback, hidden SDK retries disabled, direct provider subpath exports kept for 1.x, budget tracker process-local — no redesign of budget, circuit, fallback, transport, pricing, taxonomy, or provider inventory (contract Fix 9).

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Baseline still matches locked SHA at start | `repository_state` | `git rev-parse HEAD` == `c47c0248f603786fea2e14ce4a9dcc7ea1c5ea40` | true |
| SP-02 | resolveCapabilities is the single capability authority; dispatch never re-derives search/vision from the raw task | `structural` | grep: `VISION_TASKS` appears only in `src/matrices/search-policy.ts`; `dispatchProvider` contains no task-type vision re-check | true |
| SP-03 | All five unsupported-combination codes throw before budget reservation and provider dispatch | `runtime_behavior` | 14-row routing matrix (8 route + 6 fail rows) passes in `tests/routing-matrix.test.ts` + `tests/capability-integrity.test.ts` | true |
| SP-04 | RoutingResolution carries searchRequired, searchPolicySource, visionRequired; RoutingDecision carries outcome/failureKind/errorCode | `structural` | `npm run verify:types` + declaration-consumer compile PASS | true |
| SP-05 | FAILED entries appear in getCallLog() with no prompt/key/image data | `runtime_behavior` | capability-integrity test asserts FAILED entry fields and absence of prompt material | true |
| SP-06 | resolvePerplexityConfig throws for non-search tasks; disableSearch stays false | `runtime_behavior` | search-policy + perplexity-matrix tests PASS | true |
| SP-07 | Quality gate PASS on changed files | `quality_gate` | `npm run verify:all` → PASS (build, strict types, declarations, lint, boundary, tests, audit, package verify) | true |
| SP-08 | Packed tarball is clean and consumers compile/test against it | `filesystem` + `quality_gate` | `npm pack` contains only expected files; Website-Bot and SEO-Bot ephemeral-install compile/test PASS | true |
| SP-09 | Published patch is registry-verified (never assumed) and pinned identically in both bots | `network_observation` + `filesystem` | `npm view` evidence; both pins equal the published version | true |
| SP-10 | Budget/circuit/fallback/image-safety regression suites stay green with zero changes to mature modules | `quality_gate` | regression suites PASS; `src/budget`, `src/circuit-breaker.ts`, transports, `src/pricing.ts`, vision internals untouched in the diff | true |
| SP-11 | Publish happened only after a human checkpoint | `human_confirmation` | checkpoint receipt recorded before `npm publish` | true |

`evidence_type` ∈ `filesystem` \| `runtime_behavior` \| `structural` \| `quality_gate` \| `repository_state` \| `network_observation` \| `proof_receipt` \| `human_confirmation`

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`  
`instance_binding:` `capability_preflight_ref` → fill path or inline id below.

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.llm-router.capability-integrity.v1` |
| source_ref | this plan_id |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | Immutable baseline section |
| baseline_verified | `false` (reverified at execution start — plan mode ran no probes) |
| drift_detected | `false` at plan time |

### Probes (min 1; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `branch_and_HEAD_resolution` | `git -C /Users/macm2/LLM-Router rev-parse origin/main && git rev-parse HEAD` (after T00) | equals locked commit_sha `c47c0248f603786fea2e14ce4a9dcc7ea1c5ea40` | true |
| CP-02 | `command_available` | `node --version && npm --version && npx tsc --version` | node 20+ / npm present / tsc present | true |
| CP-03 | `filesystem_write` | write probe inside `src/` and `tests/` on the new branch | may_modify paths writable | true |
| CP-04 | `registry_read` | `npm view @quantum-l9/llm-router versions --json` (T09 wave) | registry read succeeds; next unused patch identified | true |
| CP-05 | `PR_55_disposition` | `/l9-pr-remediation` diagnose of PR #55 | disposition recorded before any edit on the new branch | true |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** LLM-Router `src/matrices/search-policy.ts`, `src/matrices/perplexity-matrix.ts`, `src/index.ts`, `src/types.ts`, `src/provider-errors.ts`, `tests/**`, `scripts/test-inventory.mjs`, `package.json`, `package-lock.json`, `ARCHITECTURE.md`, `README.md`; release wave only: `Website-Bot/package.json`, `Website-Bot/package-lock.json`, `SEO-Bot/package.json`, `SEO-Bot/package-lock.json` (pin lines)
- **write_deny:** `src/budget/**`, `src/circuit-breaker.ts`, `src/providers/**`, `src/pricing.ts`, `src/matrices/general-matrix.ts` (pricing/selection tables), `src/vision/index.ts`, `src/control-plane/**`, `src/schemas.ts`, `src/memory.ts`, `WIP/**`, `campaign/7-router-search-policy` branch, secrets, `.env*`
- **delete_allow:** none (no deletions in scope)

### Commands

- **allow:** `git checkout -b campaign/7-router-capability-integrity origin/main` (T00), `npm run verify:all`, `npm test`, `npm run build`, `npm run lint`, `npm pack`, `npm view @quantum-l9/llm-router versions --json`, scoped `git add` + `git commit` on the declared branch only, `npm publish` (human checkpoint only, T09)
- **deny:** force-push, hard-reset, rebase, admin-merge, `git push` outside the L4 release path, `npm publish` without the human checkpoint receipt, secret exfil, out-of-scope installs, edits to campaign/7-router-search-policy

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | npm registry: read (`npm view`) any time in T09; write (`npm publish`) only as `bounded_external_write` after the human checkpoint |

### Secrets

| Field | Value |
|-------|-------|
| access | `read_only_named` — `NPM_TOKEN` resolved via `l9-aws-secrets` at publish time, never printed |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always in packet + PE `COMPATIBILITY.yaml` (forbidden).  
**Merge for this plan** only after PE verify/handoff path + [@autonomy](commands/autonomy.md) join on this L4 plan/PE stack, green+mergeable (see Execute section). Outside that stack → denied.

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005).

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T00 | `filesystem_mutation` (new branch) | `safe_to_repeat` | `retry_once` | delete the branch | false |
| T01 | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | restore scoped paths / drop branch | false |
| T02 | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | restore scoped paths / drop branch | false |
| T03 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore scoped paths / drop branch | false |
| T04 | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | restore scoped paths / drop branch | false |
| T05 | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | restore scoped paths / drop branch | false |
| T06 | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | restore scoped paths / drop branch | false |
| T07 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore scoped paths / drop branch | false |
| T08 | `filesystem_read` + test runs | `safe_to_repeat` | `retry_once` | null | false |
| T09 | `external_state_mutation` (npm publish) + `filesystem_mutation` (version + pins) + `network_read` | `unsafe_blind_repeat` for publish; `safe_with_dedupe` for pins | `manual_only` for publish | deprecate the published version; re-pin both bots to 1.1.3 | true (publish) |
| T10 | `filesystem_mutation` (docs only) | `safe_to_repeat` | `retry_once` | restore scoped paths / drop branch | false |

`side_effects` ∈ `none` \| `filesystem_read` \| `filesystem_mutation` \| `destructive_filesystem_mutation` \| `network_read` \| `network_write` \| `database_read` \| `database_write` \| `external_state_mutation` \| `human_approval`

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T01 | router capability policy | `policy` | `src/matrices/search-policy.ts` (requiresSearch semantics, #45/#46 contracts) | change requiresSearch precedence; touch TaskType taxonomy |
| T02 | router capability validation | `policy` | `UnsupportedCapabilityCombinationError` public class (main #46 shape) | rename existing code SEARCH_VISION_COMBINATION_UNSUPPORTED; break constructor compat |
| T03 | routing + dispatch authority | `control_plane` | `RoutingResolution` / `RoutingDecision` public contracts in `src/types.ts` | redesign budget, circuit, fallback, pricing; spread imagesProvided onto the public contract |
| T04 | perplexity provider config | `data_plane` | `PerplexityConfig` public contract (disableSearch stays a field) | remove disableSearch; change pricing/selection tables |
| T05 | search modifier policy | `policy` | `TaskDescriptor` fields recency/domainFilter (schema stays permissive) | mutate `src/schemas.ts` |
| T06 | execution options policy | `control_plane` | `execute()` options.consensus semantics | change variations>1 dispatch condition |
| T07 | call audit | `assurance` | `RoutingDecision` + `ProviderFailureKind`/`ProviderErrorMetadata` | log prompt/keys/images; weaken existing budget/circuit assertions |
| T08 | proof wave | `assurance` | `tests/routing-matrix.test.ts` (main #46 baseline) + verify:all | weaken or delete legitimate tests (95-test-fix-policy) |
| T09 | release + consumer pins | `external_system` | package.json version; Website-Bot/SEO-Bot package locks | publish without human checkpoint; guess the next version; drift between the two pins |
| T10 | documentation | `docs` | ARCHITECTURE.md / README.md routing sections | rewrite unrelated architecture prose |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`  
`instance_binding:` `rollback_contract_ref`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.llm-router.capability-integrity.v1` |
| source_execution_ref | this plan_id |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | baseline drift; blocking property fail; envelope breach; human checkpoint refused at publish |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | scoped to write_allow; whole-plan abort = drop the branch, never revert main |
| data | `none` | no data-plane stores in scope |
| external_state | `manual_recovery` | npm publish is irreversible: compensate with `npm deprecate` + re-pin both bots to 1.1.3; never unpublish |
| local_state | `git_restore_scoped_paths` | consumer package.json pins restored to 1.1.3 |

### Irreversible operations

- (PLAN-SCHEMA-010) `npm publish` in T09 — the single irreversible operation; gated by the human checkpoint, registry verification, and C3 evidence. Compensation is deprecation, not removal.

### Rollback verification

- `npm run verify:all` PASS after path restore; `git diff --name-only` restricted to write_allow paths; `npm view` shows the published version deprecated (only if the publish compensation path was taken)

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` |
| uncertainty | `medium` |
| blast_radius | `medium` |
| architectural_boundaries_crossed | `1` (LLM-Router → Website-Bot/SEO-Bot pins at T09) |
| external_systems_touched | `1` (npm registry: read + human-gated publish) |
| migration_required | `false` |
| unknown_dependency_count | `5` (UNK-001..005, all accept_bounded) |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

| Field | Value |
|-------|-------|
| receipt_path | n/a |
| categories | not activated — no retire/migrate/replace in scope (contract Fix 9 preserves all mature modules) |
| checksum_required | `true` |
| destructive_gate_required_for | `migrate_then_delete` |

## Gated write pipeline *(optional — irreversible or external writes)*

Activated for the single irreversible external write in scope: `npm publish` (T09).

- **gates (ordered):** C3 evidence (`npm run verify:all` PASS) → registry read (`npm view`) identifies the next unused patch → human checkpoint receipt → `npm publish` → consumer proof (F3) → pin both bots (same wave, same version)
- **dedupe_before_non_idempotent_write:** `true` — publish exactly once; re-publish attempt requires a fresh checkpoint
- **bounded_write_count:** `1` (one publish per campaign)
- **receipt_required:** `true` — checkpoint receipt recorded before and after publish

## Regeneration extinguishment *(optional — retirement/deprecation)*

not activated — no regenerator artifacts or deprecations in scope.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`  
`instance_binding:` `dependency_topology_ref` / `execution_DAG_ref`  
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.<plan_id>` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | owner | layer | depends_on | outputs |
|----|-------|-------|------------|---------|
| T00 | agent | assurance | [] | bound branch receipt, baseline_receipt, PR #55 disposition |
| T01 | agent | policy | [T00] | resolveCapabilities + ResolvedCapabilities in src/matrices/search-policy.ts |
| T02 | agent | policy | [T01] | validateCapabilities; 3 fail-closed codes; extended error class; tests |
| T03 | agent | control_plane | [T01, T02] | single-decision resolveRoute + dispatchProvider; RoutingResolution.visionRequired |
| T04 | agent | data_plane | [T01] | non-search guard in resolvePerplexityConfig |
| T05 | agent | policy | [T02] | SEARCH_MODIFIER_WITHOUT_SEARCH throw |
| T06 | agent | control_plane | [T03] | CONSENSUS_REQUIRES_SEARCH throw before budget reservation |
| T07 | agent | assurance | [T03] | FAILED audit entries with outcome/failureKind/errorCode |
| T08 | agent | assurance | [T02, T03, T04, T05, T06, T07] | full 14-row matrix + capability-integrity suite; verify:all PASS |
| T09 | agent | external_system | [T08] | published patch + identical pins in Website-Bot and SEO-Bot |
| T10 | agent | docs | [T09] | updated ARCHITECTURE.md / README.md authority chain |

**Critical path:** `T00` → `T01` → `T02` → `T03` → `T06` → `T08` → `T09` → `T10`

**Forbidden edges:** any edge into `src/budget`, `src/circuit-breaker.ts`, `src/providers`, `src/pricing.ts`, `src/vision/index.ts`, `src/control-plane`, `src/schemas.ts`; T09 publish before human checkpoint; edges from the campaign/7-router-search-policy branch. Graph is acyclic (validated by `validate_plan_document.py`).

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`  
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`  
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `repository_state_evidence` | rev-parse compare | `git rev-parse HEAD` | locked SHA c47c0248f603786fea2e14ce4a9dcc7ea1c5ea40 | `not_run` |
| EV-SP-02 | SP-02 | `structural_evidence` | grep structural scan | `grep -rn "VISION_TASKS" src` | hits only in src/matrices/search-policy.ts | `not_run` |
| EV-SP-03 | SP-03 | `runtime_behavior_evidence` | 14-row matrix suite | `npm test -- routing-matrix capability-integrity` | 8 route rows + 6 fail rows PASS | `not_run` |
| EV-SP-04 | SP-04 | `structural_evidence` | strict type + declaration consumer | `npm run verify:types && npm run verify:declarations` | PASS | `not_run` |
| EV-SP-05 | SP-05 | `runtime_behavior_evidence` | capability-integrity call-log tests | `npm test -- capability-integrity` | FAILED entries present; no prompt material | `not_run` |
| EV-SP-06 | SP-06 | `runtime_behavior_evidence` | search-policy tests | `npm test -- search-policy` | perplexity guard throws; disableSearch false | `not_run` |
| EV-SP-07 | SP-07 | `quality_gate_evidence` | canonical quality gate | `npm run verify:all` | PASS | `not_run` |
| EV-SP-08 | SP-08 | `filesystem_evidence` | tarball content scan + consumer proof | `npm pack` then consumer compile/test | clean tarball; both consumers PASS | `not_run` |
| EV-SP-09 | SP-09 | `network_observation_evidence` | registry state read | `npm view @quantum-l9/llm-router versions --json` | next unused patch identified; pins equal it | `not_run` |
| EV-SP-10 | SP-10 | `quality_gate_evidence` | regression suites + diff scope | `npm test` + `git diff --name-only` | regressions green; mature modules absent from diff | `not_run` |
| EV-SP-11 | SP-11 | `proof_receipt` | human checkpoint receipt | checkpoint before `npm publish` | receipt recorded | `not_run` |
| EV-F4 | F4 | `quality_gate_evidence` | pr-check availability | `make pr-check` | N/A (no Makefile in LLM-Router, P0); if added before execute, must PASS | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Assumption A false → …
- Probe/environment differs from baseline capture → …

### Assumption failure conditions

- Dirty tree overlaps `write_allow` under `stop_if_dirty_overlaps_may_modify`
- Blocking success property fails after mutation
- Unknown dependency discovered mid-flight (PLAN-SCHEMA-013)

### Blast radius notes

- …

### Rollback constraints

- No force-push / history rewrite
- External append-only systems → compensating record only

## Out of scope

- Adjacent features / refactors not listed in envelope
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution (see below)

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

| Field | Value |
|-------|-------|
| separate_plan_required | `true` |

| priority | change | why |
|----------|--------|-----|
| P1 | … | … |

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`  
`instance_binding:` `convergence_contract_ref`  
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.<plan_id>` |
| source_ref | this plan_id |
| current_state | `draft` \| `preflight_blocked` \| `execution_ready` \| `executing` \| `validation_failed` \| `partial` \| `converged` |
| implementation_ready | `false` until preflight + DAG + envelope filled |

### Gates

- **executable_when:**
  - baseline locked + reverified
  - blocking capability probes pass
  - DAG acyclic
  - envelope + side-effect matrix complete for mutate todos
  - no blocking unknowns
- **complete_when:**
  - all blocking SP-* evidence `passed`
  - rollback contract still valid / unused-or-verified
  - out_of_scope respected (diff hygiene)
- **blocking_conditions:**
  - `preflight_blocked`
  - envelope breach
  - baseline drift
  - failed blocking property

### Evidence

- **required_evidence_refs:** `EV-SP-01`, `EV-SP-02`, `EV-SP-03`
- **observed_evidence_refs:** *(fill during execution)*
- **missing_evidence:** *(fill)*

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| open_blocker | | | |
| unknown | U1 | | ask / measure / lock — do not infer away |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `execution_ready` → `executing` → `converged` |
| minimum_safe_next_action | When law holds and status=`executable`, attach [@environment/program-execution](environment/program-execution/) + [@autonomy](commands/autonomy.md); project→Lock→claim→render→autonomy lanes — do not free-form execute |
| execute_via | `@environment/program-execution` → Program Lock/Controller → `@autonomy` (`/autonomy` → `l9-bounded-autonomy`) under Program lease → PE adapter |
| broader_work_requires_separate_contract | `true` |

---

## Machine stub (optional YAML instance seed)

Copy out and fill when promoting to a validated plan_document artifact; keep in sync with sections above.

```yaml
schema_id: canonical.schema.plan_document.v1
schema_version: 1.0.0
metadata:
  plan_id: plan.domain.slug.v1
  name: Short plan title
  overview: "…"
  status: draft
  is_project: false
  created_at: YYYY-MM-DD
architect_framing:
  planning_ssot: …
  plan_class: bounded_execution_contract
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: org/repo
  commit_sha: REPLACE_WITH_FULL_SHA
  dirty: false
  artifact_hashes: {}
  overlap_policy: stop_if_dirty_overlaps_may_modify
  verification_rule: reverify_at_execution_start
  on_drift: stop_and_replan
objective:
  mission: …
  success_properties:
    - id: SP-01
      property: …
      evidence_type: repository_state
      proof: …
      blocking: true
capability_preflight_ref: preflight.plan.domain.slug.v1
execution_envelope:
  filesystem:
    write_allow: []
    write_deny: []
  commands:
    allow: []
    deny: []
  network:
    mode: none
  secrets:
    access: none
    redaction_required: true
  autonomous_merge: false
side_effects_and_idempotency: []
architecture_impact: []
rollback_contract_ref: rollback.plan.domain.slug.v1
complexity_and_uncertainty:
  complexity: low
  uncertainty: low
  blast_radius: low
  architectural_boundaries_crossed: 0
  external_systems_touched: 0
  migration_required: false
  unknown_dependency_count: 0
dependency_topology_ref: dag.plan.domain.slug.v1
validation_evidence_refs: []
stress_and_disconfirm:
  disconfirming_cases: []
  assumption_failure_conditions: []
out_of_scope: []
convergence_contract_ref: conv.plan.domain.slug.v1
execute_via:
  pipeline: environment/program-execution
  mention_program: "@environment/program-execution"
  controller: environment/program-execution/core/program-execution-controller-template
  blueprint: environment/program-execution/core/program-execution-blueprint-template
  autonomy_provider: root-autonomy-control-plane
  autonomy_integration: environment/program-execution/integrations/autonomy-control-plane
  adapter_default: cursor-foreground
  command_ref: commands/autonomy.md
  slash: /autonomy
  skill: l9-bounded-autonomy
  mention_autonomy: "@autonomy"
  authority_order:
    - plan_document
    - program_lock_and_controller
    - autonomy_packet_subordinate
    - pe_adapter_worker
todos:
  - id: todo-01-baseline-preflight
    content: …
    status: pending
```

