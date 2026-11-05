---
name: Manus adapter bootstrap alignment
overview: "Fully align the Manus adapter with current shared bootstrap, identity, secrets and native Memory contracts without inventing authority. Planning is an artifact-only subtask; downstream implementation remains the user's requested outcome. Use the existing shared owners for observational check, locked-Python preflight, independent source-revision readiness and hosted Manus no-AWS/no-operator-prof..."
todos:
  - id: T1
    content: "Repair the shared bootstrap owner, not a Manus copy: branch check/apply before UV provisioning, secrets removal/login/mkdir, receipt writes and other mutation; count check-mode UV mismatch as DEGRADED. Verify the locked venv version and required pydantic/yaml imports immediately after toolchain resolution before every gate/secrets/identity consumer; missing/wrong/import-failing locked Python is exit 1 with no system-python governance fallback. Preserve exit 0/6/1, stderr diagnostics and stdout machine payload. Make ensure_uv check architecture mismatch observational and prevent fingerprint/lock-state mutation while retaining apply concurrency behavior. Independent review follow-up: apply selects only the verified governance secrets owner, never an older workspace copy. Source revision requires the exact repository root and tracked script ownership, so nested copied code cannot borrow an enclosing HEAD. Broad release-gate peer fixtures are isolated against the same real locked-prefix/version/tracked-source helper; no peer installer runtime changes. Present preflight failure retains actionable declared-pin and locked-sync/pypi.org/astral.sh diagnostics. Local topology keeps canonical SSOT clean on main and execution on the feature checkout; no protected source is modified for freshness."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Select Manus validator interpreter only after shared bootstrap returns and fail closed if a locked interpreter is absent. Resolve runtime_script_revision from the actual executing script source root independently of --governance; explicit provenance overrides remain truthful inputs and UNKNOWN remains represented. Add two-clone/copied-script/missing-Git tests, retain mismatch and digest semantics and do not rewrite runtime receipt schema. Default writer source provenance requires exact root and tracked ownership of the executing writer. Explicit overrides and UNKNOWN/omit behavior remain truthful inputs."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Use canonical shared surface detection for explicit hosted Manus classification. In the shared secrets identity owner, Manus takes only sanctioned runtime machine identity inputs and never imports/probes AWS, seeds credentials or falls back to an operator's Infisical profile, including missing/refused/partial identities. Preserve Cursor/operator authorized bootstrap and self-hosted pool precedence; retain names-only failure/status and no credential exposure. Main executor owns this shared change. Complete the shared identity context through capability_bind: optional explicit environment propagated without os.environ writes; identity/value/source/token/failed-login caches invalidated on context changes before cache hits. Real binder tests prepopulate an operator context and prove explicit/ambient-transition Manus cannot reuse it."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T4
    content: "Consolidate complete canonical identity assurance at the existing shared owner and invoke it from adapter validation/materialization. Require v2 operating bindings, exact actor_ref/surface_refs and active binding/current projected identities; reject legacy agent_id/status fields, foreign identity, missing scope and tampered/stale/unverifiable projection before any materialized file. Do not edit canonical registries or treat registered identities as OAuth admission. Preserve projector provenance-equivalence semantics rather than forcing source-revision churn. Guard the legacy shared assertion exporter so a nonzero mint cannot source a pre-existing output path; failed/refused fresh exports cannot leave stale assertions accepted by a launcher. A skipped legacy mint preserves its existing scoped pre-launch handoff without claiming a fresh mint; native Manus launchers independently refuse and strip every legacy assertion, so this is not a Manus transport fallback. Trusted canonical checker keeps its code ROOT at the source checkout; only artifact paths are rebound. A fresh-process hostile caller-root ops package must never execute."
    status: pending
    phase: execute
    depends_on: []
  - id: T5
    content: "Replace the historical Manus memory stdio/HMAC carrier, renderer and launcher contract with native authenticated MCP Streamable HTTP consumption or explicit UPSTREAM_BLOCKED. The installed owner package is 2.6.0; owner main ae6e2c0d0c29dfe2a3de3fdf5293e4d996164620 leaves hosted OAuth actor admission issue 108 open. Consume only owner-supplied package/client capabilities and a proven host-managed client binding; do not invent an SDK method, issuer, callback, public client id or credential. A candidate descriptor may cite the existing published resource identifier only as owner contract, never a live endpoint admission. Renderer must refuse an executable connector when required native package/client proof is missing and must not render or start stdio/HMAC/legacy maps as fallback. Materializer remains legacy rejection assurance only, not a production Memory 3.0 credential path. Validator must validate the blocked contract without advertising Memory ready."
    status: pending
    phase: execute
    depends_on: [T4]
  - id: T6
    content: "Make explicit Manus startup health-only and on-demand retrieval separate from startup and repository mutation, using the existing shared health/envelope and canonical close semantics only if a native owner client is available. Otherwise lifecycle tools report UPSTREAM_BLOCKED with names-only evidence and do not invoke historical signed local/operator CLI as an agent transport. Remove launcher minting for the hosted memory lifecycle path; leave unrelated governance bearer protection and apply authorization unchanged. Align the existing manus-session-start envelope to resolve/health/capabilities only and prohibit admin distill emulation. No custom lifecycle authority or fake public Manus hook."
    status: pending
    phase: execute
    depends_on: [T5]
  - id: T7
    content: "Separate Infisical configuration shape from observed Universal Auth state in native MCP status; a configured descriptor is not live authentication. Keep status observational, record unverified/observed auth without accidental login, emit stage-specific sanitized 401 errors, clear refused/expired cached tokens and enforce truthful bounded expiresIn semantics including absent, invalid, very short and expired lifetime. Tests use offline fake APIs and confirm no request credential, echoed resolved value or auth response reaches output. Do not expand capabilities or add credentials. Main executor owns this change. Anchor token expiry before login so round-trip time cannot extend it, reject already-expired responses, and recursively inspect original decoded response strings/keys so JSON escaping cannot hide credential echoes."
    status: pending
    phase: execute
    depends_on: [T3]
  - id: T8
    content: "Update Manus README/setup/session-bootstrap/env comments and shared SURFACE_BOOTSTRAP_CONTRACT to current owner law with matched validator/tests: canonical .github identity versus operating binding; check is observational; locked missing Python blocks; Manus no AWS/profile fallback; native Memory-only/UPSTREAM_BLOCKED; startup health-only, hydration on demand and no memory precondition on coding; Infisical configured/auth separation. Remove active stdio/HMAC/cross-chat secret-map and must-start-before-writes instructions. Keep secret-plane runtime identity distinct from connector-only native Infisical credentials, explicit project instruction versus enforced hook, dormant manus-cloud PE provider and parent-owned stacked PR contract. Do not modify protected root docs or skills. Replace shared SessionStart hydrate/prefetch table and active Claude startup compile_and_format prose with health-only startup and explicitly on-demand retrieval. Documentation correction grants no peer runtime hook."
    status: pending
    phase: execute
    depends_on: [T2, T3, T4, T5, T6, T7]
  - id: T9
    content: "Run all scoped proofs, broader applicable shared regressions and the unchanged .pre-commit-config.yaml catalog; distinguish structural admission, unit-fixture results and live Unknowns. Inspect diff against 334faa6957e0c2f67eeea4b397019f6a141a30b8, preserve inherited paths and leave failure evidence honest. Re-run the tool-owned plan pipeline/section admission after any plan change; parent then executes only its authorized scoped commit/L4/stacked PR route and displays the PR URL. No planner-side publication or runtime claim. User explicitly selected PR #826 on 2026-11-05 after sibling #827 appeared. Retain PR_STACK=auto with explicit PR_BASE=origin/feat/fail-closed-plan-pipeline; never reinterpret this as permission to merge, bypass gates, or rebase onto #827."
    status: pending
    phase: execute
    depends_on: [T8]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Manus adapter bootstrap alignment

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `manus_adapter_bootstrap_alignment_1a51d89b.plan.md`
> **Law:** executable only when baseline matches, capability probes pass, invariants match, and envelope is respected. Markdown completeness alone is insufficient.

## Execute via Cursor Build

Press **Build**. Plan on the current workspace. Execute on the unique open-PR chain tip.

- If any open PR exists: **never** branch from `origin/main`. Start from the unique chain tip (`PR_STACK=auto`). Use `agent_worktree_start.sh` when this checkout is not already that tip. Sibling open-PR chains fail closed.
- If the board is empty: `origin/main` is allowed.
- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a **planning** requirement.
- After Build todos complete: scoped-commit (pathspecs), `l4_local.py authorize-release`, then `PR_STACK=auto PR_REMEDIATE=0 make pr`. Do not skip `make pr`.
- The finish reply **must** display the opened PR URL as proof. Without that URL the Build is incomplete.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.simple.manus_adapter_bootstrap_alignment.v1` |
| name | Manus adapter bootstrap alignment |
| overview | Fully align the Manus adapter with current shared bootstrap, identity, secrets and native Memory contracts without inventing authority. Planning is an artifact-only subtask; downstream implementation remains the user's requested outcome. Use the existing shared owners for observational check, locked-Python preflight, independent source-revision readiness and hosted Manus no-AWS/no-operator-profile classification. Replace the historical Manus Memory stdio/HMAC carrier with a fail-closed native Memory 3.0 carrier/render/readiness interface that explicitly reports UPSTREAM_BLOCKED while the owner package/client and OAuth actor admission are unavailable. Keep ordinary coding usable memory-blind. Baseline is Quantum-L9/Cursor-Governance branch fix/manus-bootstrap-alignment at 334faa6957e0c2f67eeea4b397019f6a141a30b8, advanced by the parent before any source edit onto the unique PR chain #824 -> #825 -> #826 (feat/fail-closed-plan-pipeline). Preserve all 32 inherited paths and every existing owner contract. GAR decision and reasoning-owner receipts are docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-decision.json; the tool-owned GAR run and plan pipeline own structural admission only, never runtime or live-auth admission. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial`; remaining unknowns: U1, U2, U3 |
| is_project | `false` |
| owner | l9.actor-registry/global@1#manus |
| created_at | 2026-11-05T18:45:42+00:00 |
| updated_at | 2026-11-05T18:45:42+00:00 |
| depth | `deep` |
| estimate | One bounded implementation and regression-validation pass; native hosted Memory admission is an upstream dependency, not an implementation estimate. |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | validated PLAN_DOCUMENT JSON (`validate_plan_document.py`) |
| plan_class | `bounded_execution_contract` — PLAN_DOCUMENT mode `plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via Cursor Build; stacked make pr if any open PR exists; no redesign unless plan_class requires it |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-11-05T18:45:42+00:00` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/home/ubuntu/Cursor-Governance` |
| branch | `fix/manus-bootstrap-alignment` |
| commit_sha | `8e035cb36bee164adfa74c3354f61a8763561c92` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Fully align the Manus adapter with current shared bootstrap, identity, secrets and native Memory contracts without inventing authority. Planning is an artifact-only subtask; downstream implementation remains the user's requested outcome. Use the existing shared owners for observational check, locked-Python preflight, independent source-revision readiness and hosted Manus no-AWS/no-operator-profile classification. Replace the historical Manus Memory stdio/HMAC carrier with a fail-closed native Memory 3.0 carrier/render/readiness interface that explicitly reports UPSTREAM_BLOCKED while the owner package/client and OAuth actor admission are unavailable. Keep ordinary coding usable memory-blind. Baseline is Quantum-L9/Cursor-Governance branch fix/manus-bootstrap-alignment at 334faa6957e0c2f67eeea4b397019f6a141a30b8, advanced by the parent before any source edit onto the unique PR chain #824 -> #825 -> #826 (feat/fail-closed-plan-pipeline). Preserve all 32 inherited paths and every existing owner contract. GAR decision and reasoning-owner receipts are docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-decision.json; the tool-owned GAR run and plan pipeline own structural admission only, never runtime or live-auth admission.

### Scope in

- Shared bootstrap ordering and strictly observational --check in ops/scripts/bootstrap_agent_environment.sh, including honest 0/6/1 status, machine stdout hygiene and optional component accounting.
- ensure_uv_environment.sh check safety, especially architecture mismatch fingerprint deletion and any read-only lock probe side effects; preserve exclusive apply/shared reader concurrency and pinned apply behavior.
- Independent runtime source provenance in write_runtime_readiness_receipt.py with corresponding tests and no new receipt authority.
- Shared hosted Manus surface classification, no AWS or operator profile fallback in session_start_secrets.py/infisical_cli_login.py, using existing surface_detect instead of private host marker lists.
- Shared canonical identity assurance through tools/assurance/check_canonical_identity_projection.py and ops/memory/identity_projection.py; materializer rejects legacy bypasses and failed-mint exporter guard is fail-closed.
- Manus Memory carrier/render/launch/readiness interface consumes native owner contract only or reports UPSTREAM_BLOCKED; no package upgrade, registration churn or auth fabrication.
- Explicit health-only/on-demand Manus lifecycle adapter behavior, matching memory-hook envelope and shared bootstrap surface documentation; keep the sole canonical close owner and no hosted admin emulation.
- Native Infisical status/configuration/auth distinction, bounded credential-redacted stage errors and cache-expiry safety; preserve the separate encrypted connector credential boundary.
- Manus README/setup/session bootstrap/env comments, structural validator, owner contracts and focused regression tests; plan artifacts generated through the current mandatory run_plan_pipeline.py.

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1 proves shared bootstrap --check performs no installation, secrets login/profile mutation, receipt removal/write, Git exclude/prune/ref mutation or scratch restoration; it leaves fixture filesystem snapshots unchanged and reports unsynchronized/missing optional components as exit 6 rather than READY. | `quality_gate` | V1: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q tests/ops/scripts/test_agent_bootstrap_readiness.py ops/scripts/tests/test_bootstrap_diagnostic_contract.py ops/scripts/tests/test_bootstrap_invariants.py` → Exit/status/stdout contracts and new fixture snapshots pass; no check-mode mutation or unlocked policy consumer. Tests must isolate HOME/state and never apply against the active shared .venv. The unchanged UV shell-count fixture fails identically at baseline because its stub counts sync --help; retain its independent baseline failure evidence, not a fabricated PASS. | `true` |
| SP-02 | V1 and V2 prove locked .venv absence, wrong pinned version or required import failure exits 1 before any policy/secrets/namespace/readiness consumer and never executes system Python for governance work; Manus install selects the locked validator interpreter after bootstrap. | `quality_gate` | V1: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q tests/ops/scripts/test_agent_bootstrap_readiness.py ops/scripts/tests/test_bootstrap_diagnostic_contract.py ops/scripts/tests/test_bootstrap_invariants.py` → Exit/status/stdout contracts and new fixture snapshots pass; no check-mode mutation or unlocked policy consumer. Tests must isolate HOME/state and never apply against the active shared .venv. The unchanged UV shell-count fixture fails identically at baseline because its stub counts sync --help; retain its independent baseline failure evidence, not a fabricated PASS.; V2: `bash -n ops/scripts/bootstrap_agent_environment.sh ops/scripts/ensure_uv_environment.sh environment/agents/adapters/manus/install.sh; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_manus_adapter.py` → Syntax and updated contract tests pass; late locked validator selection, missing/wrong/import-failing locked Python and thin installer failure behavior are proved without real bootstrap apply. | `true` |
| SP-03 | V3 proves runtime_script_revision is independently resolved from the executing script owner, not copied from --governance; mismatched two-clone revisions yield NOT_READY/REVISION_MISMATCH and missing provenance remains UNKNOWN. | `quality_gate` | V3: `.venv/bin/python -B -m pytest -q ops/scripts/tests/test_runtime_readiness_receipt.py tests/ops/scripts/test_claude_bootstrap_receipt_revision.py tests/ops/scripts/test_agent_bootstrap_readiness.py` → Independent executing-source revision, UNKNOWN provenance, two-clone mismatch and existing receipt reader/digest regressions pass. | `true` |
| SP-04 | V4 proves explicit hosted Manus classification uses the shared surface detector, performs no AWS import/probe/seed or operator profile fallback whether the machine identity is present, absent or refused, never exposes values, and preserves authorized Cursor/operator behavior. | `quality_gate` | V4: `.venv/bin/python -B -m pytest -q ops/secrets/test_session_start_secrets.py tests/ops/secrets/test_manus_identity_plane.py` → Hosted Manus absent/partial/refused/present identity cases never import/probe AWS or use operator profile; existing Cursor/operator/self-hosted cases and names-only receipts pass. | `true` |
| SP-05 | V5 proves canonical identity assurance is owned by the shared verifier; Manus materialization rejects legacy agent_id/status shortcuts, foreign/unknown/non-current actor or surface, inactive binding and stale/tampered projection before producing files; failed mint paths never source or reuse an existing assertion file. | `quality_gate` | V5: `.venv/bin/python -B tools/assurance/check_canonical_identity_projection.py; .venv/bin/python -B tools/authority/project_canonical_identity.py --authority-root /home/ubuntu/L9-Org-Authority --check; .venv/bin/python -B -m pytest -q tests/test_canonical_identity_projection.py environment/agents/adapters/manus/tests/test_memory_authority.py environment/agents/adapters/manus/tests/test_manus_adapter.py tests/ops/memory/test_assertion_export_fail_closed.py` → Shared canonical binding/projection/receipt and currentness pass; legacy identity/status/tamper/non-current and failed-mint file/stale-env negative cases fail closed with no authority production. | `true` |
| SP-06 | V6 proves the committed Memory carrier is native authenticated Streamable HTTP, contains no fabricated issuer/client/callback/credential or stdio/HMAC/provider fallback, and renderer/readiness refuse the installed 2.6.0 package as UPSTREAM_BLOCKED without starting it or changing the lockfile. Canonical actor manus and surface manus-cloud remain registration only, not auth proof. | `quality_gate` | V6: `.venv/bin/python -B environment/agents/adapters/manus/validate_manus_adapter.py --repo-root .; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_manus_adapter.py environment/agents/adapters/manus/tests/test_memory_authority.py; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_native_memory_boundary.py` → Native carrier structurally valid while renderer/readiness reports installed2.6.0 UPSTREAM_BLOCKED; no stdio/HMAC/provider fallback, fabricated OAuth input, executable legacy credential carrier, release or auth claim. | `true` |
| SP-07 | V7 proves lifecycle startup is bounded health-only, retrieval is explicit/on-demand and not a repository-write precondition; native-client absence or unproved OAuth actor admission is fail-closed for memory while governance remains usable. No lifecycle wrapper emulates admin distill or a local operator agent door. | `quality_gate` | V7: `.venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_memory_lifecycle.py environment/agents/adapters/manus/tests/test_mcp_server.py; .venv/bin/python -B ops/scripts/validate_memory_egress_boundary.py --enforce --root .; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_native_memory_boundary.py` → Updated lifecycle health-only/on-demand/no-write-precondition and blocked-native-client tests pass; no startup hydration, local operator agent fallback, admin distill emulation or provider egress introduced. Governance protection unchanged. | `true` |
| SP-08 | V8 proves Infisical configured shape is separate from observed auth state, 401 outcomes name the failing stage without leaking request/response credentials, token expiry/invalid expiry never overstates usable lifetime, and offline fixtures cannot be described as live Universal Auth proof. | `quality_gate` | V8: `.venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_infisical_mcp_server.py environment/agents/adapters/manus/tests/test_render_infisical_mcp_connector.py` → Configured/auth-unverified and observed auth states are distinct, status does not authenticate, staged401 errors redact all credentials, short/invalid/expired cache lifetime is truthful and response values remain withheld; only offline proof claimed. | `true` |
| SP-09 | V9 and V10 prove matching docs/contracts/tests contain no active legacy memory instructions, preserve unrelated governance/Infisical MCP safety, pass scoped quality gates and contain only this plan's allowlisted changes; root protected files, inherited planning owners, upstream .github/Memory and secrets remain untouched. | `quality_gate` | V9: `.venv/bin/python -B skills/l9-plan-simple/scripts/run_plan_pipeline.py --plan-json docs/plans/manus-adapter-bootstrap-alignment.plan.json --execute-via cursor-build --workspace . --gar-run docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-run.json --out-md docs/plans/manus_adapter_bootstrap_alignment_a15b0001.plan.md; .venv/bin/python -B skills/l9-plan-simple/scripts/admit_plan.py --all docs/plans/manus_adapter_bootstrap_alignment_a15b0001.plan.md; git diff --check` → Current pipeline validates JSON, verifies real GAR load-order run, fills canonical projection and validates bound section receipt; admission --all PASS without unbound/undeclared/parameter markers. This is plan-structure admission only. Matching adapter/shared docs no longer teach retired behavior.; V10: `PATH="$PWD/.venv/bin:$PATH" L9_GOVERNANCE_SURFACE=manus PYTHONDONTWRITEBYTECODE=1 make precommit-repo; git diff --check; scoped unchanged .pre-commit-config.yaml hook catalog on all repair/new test paths` → Only approved task paths change; no protected root/inherited/skill/upstream/credential mutation, whitespace defect or weakened gate. Applicable unchanged catalog passes and failures remain evidence. Parent alone authorizes release and publishes its scoped stacked PR after all mandatory implementation proofs pass. | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.manus_adapter_bootstrap_alignment.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.manus_adapter_bootstrap_alignment.v1` |
| source_ref | `plan.simple.manus_adapter_bootstrap_alignment.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.manus_adapter_bootstrap_alignment.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P1 | pre-validation (status `passed`) | `git status --short; git rev-parse HEAD; git branch --show-current; git diff --name-only 061fae50dbc1c1e57280b8f94f0a4df783f746d9..HEAD` | Observed clean at 334faa6957e0c2f67eeea4b397019f6a141a30b8 on fix/manus-bootstrap-alignment before plan artifacts; inherited 32 files are not this task's changes. Reverify at execution start; do not overwrite parent or inherited work. | `true` |
| P2 | pre-validation (status `passed`) | `.venv/bin/python -B tools/authority/project_canonical_identity.py --authority-root /home/ubuntu/L9-Org-Authority --check` | Existing projector reports historical 9b27869dd893fcd28f76f99c9184a90435542c76 provenance-equivalent through .github 93dbaa13e5062c243a6bc47e9b63af0a808808c1; actor manus/surface manus-cloud already registered. Source revision alone does not demand regenerated bytes. | `true` |
| P3 | pre-validation (status `passed`) | `PYTHONDONTWRITEBYTECODE=1 L9_MEMORY_ENV_HEAL=0 .venv/bin/python -B ops/hooks/plan_memory_prefetch.py --workspace . --task 'Manus adapter bootstrap alignment'` | Bounded prefetch attempted without environment healing. Observed NO_HIT, zero records/conflicts, snapshot_digest 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 at original 061fae50 baseline; record as historical planning evidence only, native auth UNKNOWN. CANONICAL_LAW 8.9/8.10 makes memory nonblocking; changed-source task context must not be invented. | `true` |
| P4 | pre-validation (status `passed`) | `Read /home/ubuntu/manus-fix-baseline.log and parent-provided scoped regression baseline; inspect .pre-commit-config.yaml as the hook catalog without editing it` | Log records 204 passed in 38.76s before implementation; not a final implementation verdict. Parent reports locked UV check cached and current BOUND canonical binding; these observations grant no new authority. | `true` |
| P5 | pre-validation (status `passed`) | `.venv/bin/python -B skills/l9-plan/scripts/route_plan.py --risk high --evidence partial --json; load skills/l9-global-architect/runtime/MANIFEST.yaml load_order and pinned Reasoning Foursome snapshots` | Observed deep with omit_gates []; all 14 GAR owner artifacts resolve and are loaded in order; GAR decision is selected before PLAN_DOCUMENT. No integrated runtime activation or unimplemented product extract substitution. | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `ops/scripts/bootstrap_agent_environment.sh`, `ops/scripts/ensure_uv_environment.sh`, `ops/scripts/write_runtime_readiness_receipt.py`, `ops/scripts/tests/test_bootstrap_diagnostic_contract.py`, `ops/scripts/tests/test_bootstrap_invariants.py`, `ops/scripts/tests/test_uv_environment_fingerprint.sh`, `ops/scripts/tests/test_runtime_readiness_receipt.py`, `ops/secrets/session_start_secrets.py`, `ops/secrets/infisical_cli_login.py`, `ops/secrets/test_session_start_secrets.py`, `tools/assurance/check_canonical_identity_projection.py`, `ops/memory/identity_projection.py`, `ops/memory/export_agent_assertion_env.sh`, `ops/config/memory-hook-envelopes.json`, `tests/test_canonical_identity_projection.py`, `environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md`, `environment/agents/adapters/manus/install.sh`, `environment/agents/adapters/manus/validate_manus_adapter.py`, `environment/agents/adapters/manus/materialize_memory_authority.py`, `environment/agents/adapters/manus/memory-mcp-connector.json`, `environment/agents/adapters/manus/render_memory_mcp_connector.py`, `environment/agents/adapters/manus/serve_memory_mcp.sh`, `environment/agents/adapters/manus/memory_lifecycle.py`, `environment/agents/adapters/manus/mcp_server.py`, `environment/agents/adapters/manus/serve_mcp.sh`, `environment/agents/adapters/manus/mcp-connector.json`, `environment/agents/adapters/manus/infisical_mcp_server.py`, `environment/agents/adapters/manus/README.md`, `environment/agents/adapters/manus/setup.md`, `environment/agents/adapters/manus/session_bootstrap.md`, `environment/agents/adapters/manus/environment.env.example`, `environment/agents/adapters/manus/tests/test_manus_adapter.py`, `environment/agents/adapters/manus/tests/test_memory_authority.py`, `environment/agents/adapters/manus/tests/test_memory_lifecycle.py`, `environment/agents/adapters/manus/tests/test_mcp_server.py`, `environment/agents/adapters/manus/tests/test_infisical_mcp_server.py`, `environment/agents/adapters/manus/tests/test_render_infisical_mcp_connector.py`, `docs/plans/manus-adapter-bootstrap-alignment.plan.json`, `docs/plans/manus_adapter_bootstrap_alignment_a15b0001.plan.md`, `docs/plans/manus_adapter_bootstrap_alignment_a15b0001.section-receipt.json`, `docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-decision.json`, `docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-run.json`, `tests/ops/scripts/test_agent_bootstrap_readiness.py`, `tests/ops/secrets/test_manus_identity_plane.py`, `tests/ops/memory/test_assertion_export_fail_closed.py`, `environment/agents/adapters/manus/tests/test_native_memory_boundary.py`, `ops/secrets/capability_bind.py`, `ops/scripts/tests/test_session_start_runtime_report.py`, `environment/agents/adapters/claude-code/tests/test_install_mounts.py`, `ops/scripts/tests/test_capability_plane_counts_degraded.py`
- **write_deny:** `CANONICAL_LAW.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `Makefile`, `.pre-commit-config.yaml`, `skills/`, `commands/`, `rules/`, `pyproject.toml`, `uv.lock`, `generated/governance/canonical_identity.yaml`, `generated/governance/canonical_identity.receipt.yaml`, `environment/agents/agent_registry.yaml`, `governance/authority-bindings/canonical-agent-identity.yaml`, `all inherited 061fae50..334faa69 paths`, `/home/ubuntu/L9-Org-Authority`, `/home/ubuntu/L9-Memory-Owner`, `credential/secret stores, deployed services, account configuration and shared live .venv`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `Run V1-V10 from /home/ubuntu/Cursor-Governance using .venv/bin/python -B and isolated fixtures; no bootstrap apply or live login against the active shared environment.`, `After all proofs pass parent may use its own scoped commit and authorize-release, then PR_STACK=auto PR_REMEDIATE=0 make pr, and must display the opened PR URL. Planning subagent performs none of these external effects.`, `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q tests/ops/scripts/test_agent_bootstrap_readiness.py ops/scripts/tests/test_bootstrap_diagnostic_contract.py ops/scripts/tests/test_bootstrap_invariants.py`, `bash -n ops/scripts/bootstrap_agent_environment.sh ops/scripts/ensure_uv_environment.sh environment/agents/adapters/manus/install.sh; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_manus_adapter.py`, `.venv/bin/python -B -m pytest -q ops/scripts/tests/test_runtime_readiness_receipt.py tests/ops/scripts/test_claude_bootstrap_receipt_revision.py tests/ops/scripts/test_agent_bootstrap_readiness.py`, `.venv/bin/python -B -m pytest -q ops/secrets/test_session_start_secrets.py tests/ops/secrets/test_manus_identity_plane.py`, `.venv/bin/python -B tools/assurance/check_canonical_identity_projection.py; .venv/bin/python -B tools/authority/project_canonical_identity.py --authority-root /home/ubuntu/L9-Org-Authority --check; .venv/bin/python -B -m pytest -q tests/test_canonical_identity_projection.py environment/agents/adapters/manus/tests/test_memory_authority.py environment/agents/adapters/manus/tests/test_manus_adapter.py tests/ops/memory/test_assertion_export_fail_closed.py`, `.venv/bin/python -B environment/agents/adapters/manus/validate_manus_adapter.py --repo-root .; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_manus_adapter.py environment/agents/adapters/manus/tests/test_memory_authority.py; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_native_memory_boundary.py`, `.venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_memory_lifecycle.py environment/agents/adapters/manus/tests/test_mcp_server.py; .venv/bin/python -B ops/scripts/validate_memory_egress_boundary.py --enforce --root .; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_native_memory_boundary.py`, `.venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_infisical_mcp_server.py environment/agents/adapters/manus/tests/test_render_infisical_mcp_connector.py`, `.venv/bin/python -B skills/l9-plan-simple/scripts/run_plan_pipeline.py --plan-json docs/plans/manus-adapter-bootstrap-alignment.plan.json --execute-via cursor-build --workspace . --gar-run docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-run.json --out-md docs/plans/manus_adapter_bootstrap_alignment_a15b0001.plan.md; .venv/bin/python -B skills/l9-plan-simple/scripts/admit_plan.py --all docs/plans/manus_adapter_bootstrap_alignment_a15b0001.plan.md; git diff --check`, `PATH="$PWD/.venv/bin:$PATH" L9_GOVERNANCE_SURFACE=manus PYTHONDONTWRITEBYTECODE=1 make precommit-repo; git diff --check; scoped unchanged .pre-commit-config.yaml hook catalog on all repair/new test paths`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `bounded_external_write` |
| allowed_services | `GitHub Quantum-L9/Cursor-Governance only for the downstream executor's existing stacked PR publication path; offline fixtures for Auth0, Infisical and Memory; no live service configuration, authentication or deployment` |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- CANONICAL_LAW.md 8.9 health-only/on-demand/no-memory-write-precondition and 8.10 native Memory3 OAuth/client/identity separation; 14.1 Infisical secret authority.
- environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md existing shared detector precedence; adapters wrap and do not redefine meaning.
- ops/scripts/bootstrap_agent_environment.sh 0 satisfied / 6 usable degraded / 1 locked-interpreter blocked, machine stdout versus stderr diagnostics.
- tools/authority/project_canonical_identity.py provenance-equivalence, ops/memory/identity_projection.py digest/current-identity verification, canonical .github actor/surface ownership versus operating bindings.
- Memory owner ADR-100/REMOTE_MCP_CONTRACT.md at ae6e2c0d: OAuth native hosted door only, unknown client/actor admission remains blocked; legacy package presence is not hosted suitability.
- Governance wrapper no arbitrary shell/file/write tools and explicit bearer/apply guard; native Infisical fixed capability manifest, viewSecretValue=false and response-secret withholding.
- Current l9-plan-simple pipeline owner at 334faa6957: tool-owned write_plan_run, pipeline projection/section receipt and admit_plan; structural admission is not runtime admission.
- Parent-owned stacked PR/L4 path, inherited unique #824->825->826 chain tip; no Program Execution, Controller, deployment or autonomous merge.

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/scripts/bootstrap_agent_environment.sh ops/scripts/ensure_uv_environment.sh ops/scripts/tests/test_bootstrap_diagnostic_contract.py ops/scripts/tests/test_bootstrap_invariants.py ops/scripts/tests/test_uv_environment_fingerprint.sh tests/ops/scripts/test_agent_bootstrap_readiness.py ops/scripts/tests/test_session_start_runtime_report.py environment/agents/adapters/claude-code/tests/test_install_mounts.py ops/scripts/tests/test_capability_plane_counts_degraded.py` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- environment/agents/adapters/manus/install.sh ops/scripts/write_runtime_readiness_receipt.py ops/scripts/tests/test_runtime_readiness_receipt.py environment/agents/adapters/manus/tests/test_manus_adapter.py tests/ops/scripts/test_agent_bootstrap_readiness.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/secrets/session_start_secrets.py ops/secrets/infisical_cli_login.py ops/secrets/test_session_start_secrets.py tests/ops/secrets/test_manus_identity_plane.py ops/secrets/capability_bind.py` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tools/assurance/check_canonical_identity_projection.py ops/memory/identity_projection.py ops/memory/export_agent_assertion_env.sh environment/agents/adapters/manus/materialize_memory_authority.py environment/agents/adapters/manus/validate_manus_adapter.py environment/agents/adapters/manus/tests/test_memory_authority.py tests/test_canonical_identity_projection.py environment/agents/adapters/manus/tests/test_manus_adapter.py tests/ops/memory/test_assertion_export_fail_closed.py` | `false` |
| T5 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- environment/agents/adapters/manus/memory-mcp-connector.json environment/agents/adapters/manus/render_memory_mcp_connector.py environment/agents/adapters/manus/serve_memory_mcp.sh environment/agents/adapters/manus/validate_manus_adapter.py environment/agents/adapters/manus/tests/test_manus_adapter.py environment/agents/adapters/manus/tests/test_memory_authority.py environment/agents/adapters/manus/tests/test_native_memory_boundary.py` | `false` |
| T6 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- environment/agents/adapters/manus/memory_lifecycle.py environment/agents/adapters/manus/mcp_server.py environment/agents/adapters/manus/serve_mcp.sh environment/agents/adapters/manus/mcp-connector.json ops/config/memory-hook-envelopes.json environment/agents/adapters/manus/tests/test_memory_lifecycle.py environment/agents/adapters/manus/tests/test_mcp_server.py environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md environment/agents/adapters/manus/tests/test_native_memory_boundary.py` | `false` |
| T7 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- environment/agents/adapters/manus/infisical_mcp_server.py environment/agents/adapters/manus/tests/test_infisical_mcp_server.py environment/agents/adapters/manus/tests/test_render_infisical_mcp_connector.py` | `false` |
| T8 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- environment/agents/adapters/manus/README.md environment/agents/adapters/manus/setup.md environment/agents/adapters/manus/session_bootstrap.md environment/agents/adapters/manus/environment.env.example environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md environment/agents/adapters/manus/validate_manus_adapter.py environment/agents/adapters/manus/tests/test_manus_adapter.py` | `false` |
| T9 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- docs/plans/manus-adapter-bootstrap-alignment.plan.json docs/plans/manus_adapter_bootstrap_alignment_a15b0001.plan.md docs/plans/manus_adapter_bootstrap_alignment_a15b0001.section-receipt.json docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-decision.json docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-run.json` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `repository root` | `ops` | `CANONICAL_LAW.md 8.9 health-only/on-demand/no-memory-write-precondition and 8.10 native Memory3 OAuth/client/identity separation; 14.1 Infisical secret authority.`, `environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md existing shared detector precedence; adapters wrap and do not redefine meaning.`, `ops/scripts/bootstrap_agent_environment.sh 0 satisfied / 6 usable degraded / 1 locked-interpreter blocked, machine stdout versus stderr diagnostics.`, `tools/authority/project_canonical_identity.py provenance-equivalence, ops/memory/identity_projection.py digest/current-identity verification, canonical .github actor/surface ownership versus operating bindings.`, `Memory owner ADR-100/REMOTE_MCP_CONTRACT.md at ae6e2c0d: OAuth native hosted door only, unknown client/actor admission remains blocked; legacy package presence is not hosted suitability.`, `Governance wrapper no arbitrary shell/file/write tools and explicit bearer/apply guard; native Infisical fixed capability manifest, viewSecretValue=false and response-secret withholding.`, `Current l9-plan-simple pipeline owner at 334faa6957: tool-owned write_plan_run, pipeline projection/section receipt and admit_plan; structural admission is not runtime admission.`, `Parent-owned stacked PR/L4 path, inherited unique #824->825->826 chain tip; no Program Execution, Controller, deployment or autonomous merge.` | `CANONICAL_LAW.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `Makefile`, `.pre-commit-config.yaml`, `skills/`, `commands/`, `rules/`, `pyproject.toml`, `uv.lock`, `generated/governance/canonical_identity.yaml`, `generated/governance/canonical_identity.receipt.yaml`, `environment/agents/agent_registry.yaml`, `governance/authority-bindings/canonical-agent-identity.yaml`, `all inherited 061fae50..334faa69 paths`, `/home/ubuntu/L9-Org-Authority`, `/home/ubuntu/L9-Memory-Owner`, `credential/secret stores, deployed services, account configuration and shared live .venv` |
| T2 | `repository root` | `assurance` | `CANONICAL_LAW.md 8.9 health-only/on-demand/no-memory-write-precondition and 8.10 native Memory3 OAuth/client/identity separation; 14.1 Infisical secret authority.`, `environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md existing shared detector precedence; adapters wrap and do not redefine meaning.`, `ops/scripts/bootstrap_agent_environment.sh 0 satisfied / 6 usable degraded / 1 locked-interpreter blocked, machine stdout versus stderr diagnostics.`, `tools/authority/project_canonical_identity.py provenance-equivalence, ops/memory/identity_projection.py digest/current-identity verification, canonical .github actor/surface ownership versus operating bindings.`, `Memory owner ADR-100/REMOTE_MCP_CONTRACT.md at ae6e2c0d: OAuth native hosted door only, unknown client/actor admission remains blocked; legacy package presence is not hosted suitability.`, `Governance wrapper no arbitrary shell/file/write tools and explicit bearer/apply guard; native Infisical fixed capability manifest, viewSecretValue=false and response-secret withholding.`, `Current l9-plan-simple pipeline owner at 334faa6957: tool-owned write_plan_run, pipeline projection/section receipt and admit_plan; structural admission is not runtime admission.`, `Parent-owned stacked PR/L4 path, inherited unique #824->825->826 chain tip; no Program Execution, Controller, deployment or autonomous merge.` | `CANONICAL_LAW.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `Makefile`, `.pre-commit-config.yaml`, `skills/`, `commands/`, `rules/`, `pyproject.toml`, `uv.lock`, `generated/governance/canonical_identity.yaml`, `generated/governance/canonical_identity.receipt.yaml`, `environment/agents/agent_registry.yaml`, `governance/authority-bindings/canonical-agent-identity.yaml`, `all inherited 061fae50..334faa69 paths`, `/home/ubuntu/L9-Org-Authority`, `/home/ubuntu/L9-Memory-Owner`, `credential/secret stores, deployed services, account configuration and shared live .venv` |
| T3 | `repository root` | `ops` | `CANONICAL_LAW.md 8.9 health-only/on-demand/no-memory-write-precondition and 8.10 native Memory3 OAuth/client/identity separation; 14.1 Infisical secret authority.`, `environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md existing shared detector precedence; adapters wrap and do not redefine meaning.`, `ops/scripts/bootstrap_agent_environment.sh 0 satisfied / 6 usable degraded / 1 locked-interpreter blocked, machine stdout versus stderr diagnostics.`, `tools/authority/project_canonical_identity.py provenance-equivalence, ops/memory/identity_projection.py digest/current-identity verification, canonical .github actor/surface ownership versus operating bindings.`, `Memory owner ADR-100/REMOTE_MCP_CONTRACT.md at ae6e2c0d: OAuth native hosted door only, unknown client/actor admission remains blocked; legacy package presence is not hosted suitability.`, `Governance wrapper no arbitrary shell/file/write tools and explicit bearer/apply guard; native Infisical fixed capability manifest, viewSecretValue=false and response-secret withholding.`, `Current l9-plan-simple pipeline owner at 334faa6957: tool-owned write_plan_run, pipeline projection/section receipt and admit_plan; structural admission is not runtime admission.`, `Parent-owned stacked PR/L4 path, inherited unique #824->825->826 chain tip; no Program Execution, Controller, deployment or autonomous merge.` | `CANONICAL_LAW.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `Makefile`, `.pre-commit-config.yaml`, `skills/`, `commands/`, `rules/`, `pyproject.toml`, `uv.lock`, `generated/governance/canonical_identity.yaml`, `generated/governance/canonical_identity.receipt.yaml`, `environment/agents/agent_registry.yaml`, `governance/authority-bindings/canonical-agent-identity.yaml`, `all inherited 061fae50..334faa69 paths`, `/home/ubuntu/L9-Org-Authority`, `/home/ubuntu/L9-Memory-Owner`, `credential/secret stores, deployed services, account configuration and shared live .venv` |
| T4 | `repository root` | `assurance` | `CANONICAL_LAW.md 8.9 health-only/on-demand/no-memory-write-precondition and 8.10 native Memory3 OAuth/client/identity separation; 14.1 Infisical secret authority.`, `environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md existing shared detector precedence; adapters wrap and do not redefine meaning.`, `ops/scripts/bootstrap_agent_environment.sh 0 satisfied / 6 usable degraded / 1 locked-interpreter blocked, machine stdout versus stderr diagnostics.`, `tools/authority/project_canonical_identity.py provenance-equivalence, ops/memory/identity_projection.py digest/current-identity verification, canonical .github actor/surface ownership versus operating bindings.`, `Memory owner ADR-100/REMOTE_MCP_CONTRACT.md at ae6e2c0d: OAuth native hosted door only, unknown client/actor admission remains blocked; legacy package presence is not hosted suitability.`, `Governance wrapper no arbitrary shell/file/write tools and explicit bearer/apply guard; native Infisical fixed capability manifest, viewSecretValue=false and response-secret withholding.`, `Current l9-plan-simple pipeline owner at 334faa6957: tool-owned write_plan_run, pipeline projection/section receipt and admit_plan; structural admission is not runtime admission.`, `Parent-owned stacked PR/L4 path, inherited unique #824->825->826 chain tip; no Program Execution, Controller, deployment or autonomous merge.` | `CANONICAL_LAW.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `Makefile`, `.pre-commit-config.yaml`, `skills/`, `commands/`, `rules/`, `pyproject.toml`, `uv.lock`, `generated/governance/canonical_identity.yaml`, `generated/governance/canonical_identity.receipt.yaml`, `environment/agents/agent_registry.yaml`, `governance/authority-bindings/canonical-agent-identity.yaml`, `all inherited 061fae50..334faa69 paths`, `/home/ubuntu/L9-Org-Authority`, `/home/ubuntu/L9-Memory-Owner`, `credential/secret stores, deployed services, account configuration and shared live .venv` |
| T5 | `environment/agents/adapters/manus` | `memory` | `CANONICAL_LAW.md 8.9 health-only/on-demand/no-memory-write-precondition and 8.10 native Memory3 OAuth/client/identity separation; 14.1 Infisical secret authority.`, `environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md existing shared detector precedence; adapters wrap and do not redefine meaning.`, `ops/scripts/bootstrap_agent_environment.sh 0 satisfied / 6 usable degraded / 1 locked-interpreter blocked, machine stdout versus stderr diagnostics.`, `tools/authority/project_canonical_identity.py provenance-equivalence, ops/memory/identity_projection.py digest/current-identity verification, canonical .github actor/surface ownership versus operating bindings.`, `Memory owner ADR-100/REMOTE_MCP_CONTRACT.md at ae6e2c0d: OAuth native hosted door only, unknown client/actor admission remains blocked; legacy package presence is not hosted suitability.`, `Governance wrapper no arbitrary shell/file/write tools and explicit bearer/apply guard; native Infisical fixed capability manifest, viewSecretValue=false and response-secret withholding.`, `Current l9-plan-simple pipeline owner at 334faa6957: tool-owned write_plan_run, pipeline projection/section receipt and admit_plan; structural admission is not runtime admission.`, `Parent-owned stacked PR/L4 path, inherited unique #824->825->826 chain tip; no Program Execution, Controller, deployment or autonomous merge.` | `CANONICAL_LAW.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `Makefile`, `.pre-commit-config.yaml`, `skills/`, `commands/`, `rules/`, `pyproject.toml`, `uv.lock`, `generated/governance/canonical_identity.yaml`, `generated/governance/canonical_identity.receipt.yaml`, `environment/agents/agent_registry.yaml`, `governance/authority-bindings/canonical-agent-identity.yaml`, `all inherited 061fae50..334faa69 paths`, `/home/ubuntu/L9-Org-Authority`, `/home/ubuntu/L9-Memory-Owner`, `credential/secret stores, deployed services, account configuration and shared live .venv` |
| T6 | `repository root` | `memory` | `CANONICAL_LAW.md 8.9 health-only/on-demand/no-memory-write-precondition and 8.10 native Memory3 OAuth/client/identity separation; 14.1 Infisical secret authority.`, `environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md existing shared detector precedence; adapters wrap and do not redefine meaning.`, `ops/scripts/bootstrap_agent_environment.sh 0 satisfied / 6 usable degraded / 1 locked-interpreter blocked, machine stdout versus stderr diagnostics.`, `tools/authority/project_canonical_identity.py provenance-equivalence, ops/memory/identity_projection.py digest/current-identity verification, canonical .github actor/surface ownership versus operating bindings.`, `Memory owner ADR-100/REMOTE_MCP_CONTRACT.md at ae6e2c0d: OAuth native hosted door only, unknown client/actor admission remains blocked; legacy package presence is not hosted suitability.`, `Governance wrapper no arbitrary shell/file/write tools and explicit bearer/apply guard; native Infisical fixed capability manifest, viewSecretValue=false and response-secret withholding.`, `Current l9-plan-simple pipeline owner at 334faa6957: tool-owned write_plan_run, pipeline projection/section receipt and admit_plan; structural admission is not runtime admission.`, `Parent-owned stacked PR/L4 path, inherited unique #824->825->826 chain tip; no Program Execution, Controller, deployment or autonomous merge.` | `CANONICAL_LAW.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `Makefile`, `.pre-commit-config.yaml`, `skills/`, `commands/`, `rules/`, `pyproject.toml`, `uv.lock`, `generated/governance/canonical_identity.yaml`, `generated/governance/canonical_identity.receipt.yaml`, `environment/agents/agent_registry.yaml`, `governance/authority-bindings/canonical-agent-identity.yaml`, `all inherited 061fae50..334faa69 paths`, `/home/ubuntu/L9-Org-Authority`, `/home/ubuntu/L9-Memory-Owner`, `credential/secret stores, deployed services, account configuration and shared live .venv` |
| T7 | `environment/agents/adapters/manus` | `assurance` | `CANONICAL_LAW.md 8.9 health-only/on-demand/no-memory-write-precondition and 8.10 native Memory3 OAuth/client/identity separation; 14.1 Infisical secret authority.`, `environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md existing shared detector precedence; adapters wrap and do not redefine meaning.`, `ops/scripts/bootstrap_agent_environment.sh 0 satisfied / 6 usable degraded / 1 locked-interpreter blocked, machine stdout versus stderr diagnostics.`, `tools/authority/project_canonical_identity.py provenance-equivalence, ops/memory/identity_projection.py digest/current-identity verification, canonical .github actor/surface ownership versus operating bindings.`, `Memory owner ADR-100/REMOTE_MCP_CONTRACT.md at ae6e2c0d: OAuth native hosted door only, unknown client/actor admission remains blocked; legacy package presence is not hosted suitability.`, `Governance wrapper no arbitrary shell/file/write tools and explicit bearer/apply guard; native Infisical fixed capability manifest, viewSecretValue=false and response-secret withholding.`, `Current l9-plan-simple pipeline owner at 334faa6957: tool-owned write_plan_run, pipeline projection/section receipt and admit_plan; structural admission is not runtime admission.`, `Parent-owned stacked PR/L4 path, inherited unique #824->825->826 chain tip; no Program Execution, Controller, deployment or autonomous merge.` | `CANONICAL_LAW.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `Makefile`, `.pre-commit-config.yaml`, `skills/`, `commands/`, `rules/`, `pyproject.toml`, `uv.lock`, `generated/governance/canonical_identity.yaml`, `generated/governance/canonical_identity.receipt.yaml`, `environment/agents/agent_registry.yaml`, `governance/authority-bindings/canonical-agent-identity.yaml`, `all inherited 061fae50..334faa69 paths`, `/home/ubuntu/L9-Org-Authority`, `/home/ubuntu/L9-Memory-Owner`, `credential/secret stores, deployed services, account configuration and shared live .venv` |
| T8 | `environment/agents` | `docs` | `CANONICAL_LAW.md 8.9 health-only/on-demand/no-memory-write-precondition and 8.10 native Memory3 OAuth/client/identity separation; 14.1 Infisical secret authority.`, `environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md existing shared detector precedence; adapters wrap and do not redefine meaning.`, `ops/scripts/bootstrap_agent_environment.sh 0 satisfied / 6 usable degraded / 1 locked-interpreter blocked, machine stdout versus stderr diagnostics.`, `tools/authority/project_canonical_identity.py provenance-equivalence, ops/memory/identity_projection.py digest/current-identity verification, canonical .github actor/surface ownership versus operating bindings.`, `Memory owner ADR-100/REMOTE_MCP_CONTRACT.md at ae6e2c0d: OAuth native hosted door only, unknown client/actor admission remains blocked; legacy package presence is not hosted suitability.`, `Governance wrapper no arbitrary shell/file/write tools and explicit bearer/apply guard; native Infisical fixed capability manifest, viewSecretValue=false and response-secret withholding.`, `Current l9-plan-simple pipeline owner at 334faa6957: tool-owned write_plan_run, pipeline projection/section receipt and admit_plan; structural admission is not runtime admission.`, `Parent-owned stacked PR/L4 path, inherited unique #824->825->826 chain tip; no Program Execution, Controller, deployment or autonomous merge.` | `CANONICAL_LAW.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `Makefile`, `.pre-commit-config.yaml`, `skills/`, `commands/`, `rules/`, `pyproject.toml`, `uv.lock`, `generated/governance/canonical_identity.yaml`, `generated/governance/canonical_identity.receipt.yaml`, `environment/agents/agent_registry.yaml`, `governance/authority-bindings/canonical-agent-identity.yaml`, `all inherited 061fae50..334faa69 paths`, `/home/ubuntu/L9-Org-Authority`, `/home/ubuntu/L9-Memory-Owner`, `credential/secret stores, deployed services, account configuration and shared live .venv` |
| T9 | `docs/plans` | `assurance` | `CANONICAL_LAW.md 8.9 health-only/on-demand/no-memory-write-precondition and 8.10 native Memory3 OAuth/client/identity separation; 14.1 Infisical secret authority.`, `environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md existing shared detector precedence; adapters wrap and do not redefine meaning.`, `ops/scripts/bootstrap_agent_environment.sh 0 satisfied / 6 usable degraded / 1 locked-interpreter blocked, machine stdout versus stderr diagnostics.`, `tools/authority/project_canonical_identity.py provenance-equivalence, ops/memory/identity_projection.py digest/current-identity verification, canonical .github actor/surface ownership versus operating bindings.`, `Memory owner ADR-100/REMOTE_MCP_CONTRACT.md at ae6e2c0d: OAuth native hosted door only, unknown client/actor admission remains blocked; legacy package presence is not hosted suitability.`, `Governance wrapper no arbitrary shell/file/write tools and explicit bearer/apply guard; native Infisical fixed capability manifest, viewSecretValue=false and response-secret withholding.`, `Current l9-plan-simple pipeline owner at 334faa6957: tool-owned write_plan_run, pipeline projection/section receipt and admit_plan; structural admission is not runtime admission.`, `Parent-owned stacked PR/L4 path, inherited unique #824->825->826 chain tip; no Program Execution, Controller, deployment or autonomous merge.` | `CANONICAL_LAW.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `Makefile`, `.pre-commit-config.yaml`, `skills/`, `commands/`, `rules/`, `pyproject.toml`, `uv.lock`, `generated/governance/canonical_identity.yaml`, `generated/governance/canonical_identity.receipt.yaml`, `environment/agents/agent_registry.yaml`, `governance/authority-bindings/canonical-agent-identity.yaml`, `all inherited 061fae50..334faa69 paths`, `/home/ubuntu/L9-Org-Authority`, `/home/ubuntu/L9-Memory-Owner`, `credential/secret stores, deployed services, account configuration and shared live .venv` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.manus_adapter_bootstrap_alignment.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.manus_adapter_bootstrap_alignment.v1` |
| source_execution_ref | `plan.simple.manus_adapter_bootstrap_alignment.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (V1 fixture no-side-effect snapshots and locked-Python failure matrix.) → Stop shared bootstrap changes if check mutates or a policy consumer runs on fallback Python; repair at the shared owner.; C2 fails (V5 canonical projection/legacy materialization/failed-mint negative cases.) → Do not produce credential/grant files or launch any memory process after failed identity assurance.; C3 fails (V6/V7 prove UPSTREAM_BLOCKED without stdio/HMAC/provider fallback and health-only startup.) → Keep memory fail-closed and coding usable; never invent upstream APIs, client registration, credentials or a deployment to clear the blocker.; C4 fails (V1-V10 scoped checks and diff hygiene, current plan/section admission; parent must separately prove publication gates.) → Stop publication on failure, overlapping parent changes or sibling PR chains. No force push, merge or silent embedded-mode switch. |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Use scoped forward repair or a separately authorized scoped revert of this task's exact changed paths; preserve parent edits and the 32 inherited files. Do not use hard reset, force push, blanket git restore or resurrect retired hosted Memory stdio/HMAC as rollback. Before publication compare source/diff to baseline, rerun affected tests and confirm check leaves fixture state unchanged. No data, credential or deployed external state is changed, so no data rollback is required. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `Run V1-V10 from /home/ubuntu/Cursor-Governance using .venv/bin/python -B and isolated fixtures; no bootstrap apply or live login against the active shared environment.`
- re-run `After all proofs pass parent may use its own scoped commit and authorize-release, then PR_STACK=auto PR_REMEDIATE=0 make pr, and must display the opened PR URL. Planning subagent performs none of these external effects.`
- re-run `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q tests/ops/scripts/test_agent_bootstrap_readiness.py ops/scripts/tests/test_bootstrap_diagnostic_contract.py ops/scripts/tests/test_bootstrap_invariants.py`
- re-run `bash -n ops/scripts/bootstrap_agent_environment.sh ops/scripts/ensure_uv_environment.sh environment/agents/adapters/manus/install.sh; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_manus_adapter.py`
- re-run `.venv/bin/python -B -m pytest -q ops/scripts/tests/test_runtime_readiness_receipt.py tests/ops/scripts/test_claude_bootstrap_receipt_revision.py tests/ops/scripts/test_agent_bootstrap_readiness.py`
- re-run `.venv/bin/python -B -m pytest -q ops/secrets/test_session_start_secrets.py tests/ops/secrets/test_manus_identity_plane.py`
- re-run `.venv/bin/python -B tools/assurance/check_canonical_identity_projection.py; .venv/bin/python -B tools/authority/project_canonical_identity.py --authority-root /home/ubuntu/L9-Org-Authority --check; .venv/bin/python -B -m pytest -q tests/test_canonical_identity_projection.py environment/agents/adapters/manus/tests/test_memory_authority.py environment/agents/adapters/manus/tests/test_manus_adapter.py tests/ops/memory/test_assertion_export_fail_closed.py`
- re-run `.venv/bin/python -B environment/agents/adapters/manus/validate_manus_adapter.py --repo-root .; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_manus_adapter.py environment/agents/adapters/manus/tests/test_memory_authority.py; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_native_memory_boundary.py`
- re-run `.venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_memory_lifecycle.py environment/agents/adapters/manus/tests/test_mcp_server.py; .venv/bin/python -B ops/scripts/validate_memory_egress_boundary.py --enforce --root .; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_native_memory_boundary.py`
- re-run `.venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_infisical_mcp_server.py environment/agents/adapters/manus/tests/test_render_infisical_mcp_connector.py`
- re-run `.venv/bin/python -B skills/l9-plan-simple/scripts/run_plan_pipeline.py --plan-json docs/plans/manus-adapter-bootstrap-alignment.plan.json --execute-via cursor-build --workspace . --gar-run docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-run.json --out-md docs/plans/manus_adapter_bootstrap_alignment_a15b0001.plan.md; .venv/bin/python -B skills/l9-plan-simple/scripts/admit_plan.py --all docs/plans/manus_adapter_bootstrap_alignment_a15b0001.plan.md; git diff --check`
- re-run `PATH="$PWD/.venv/bin:$PATH" L9_GOVERNANCE_SURFACE=manus PYTHONDONTWRITEBYTECODE=1 make precommit-repo; git diff --check; scoped unchanged .pre-commit-config.yaml hook catalog on all repair/new test paths`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `high` — highest todo risk across 9 todo(s) |
| uncertainty | `medium` — 4 unknown(s), 0 blocking |
| blast_radius | `high` — Shared bootstrap, secrets classification and identity assurance serve every adapter; incorrect edits can allow check-mode mutation, operator credential borrowing or false READY/identity/auth claims across surfaces. Memory transport containment is Manus-local and must not disturb unrelated governance/Infisical servers. No database/deployment migration or credential mutation is in scope. |
| architectural_boundaries_crossed | `shared bootstrap versus adapter wrapping`, `canonical identity provenance versus operating binding`, `hosted secrets versus operator bootstrap`, `native Memory package authority versus host-managed OAuth client`, `configuration structure versus observed runtime admission` |
| external_systems_touched | `Quantum-L9/.github pinned source read only`, `Quantum-L9/l9-graphiti-memory pinned source read only`, `GitHub downstream stacked PR publication only; parent-owned` |
| migration_required | `false` |
| unknown_dependency_count | `4` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.manus_adapter_bootstrap_alignment.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.manus_adapter_bootstrap_alignment.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Repair the shared bootstrap owner, not a Manus copy: branch check/apply before UV provisioning, secrets removal/login/mkdir, receipt writes and other mutation; count check-mode UV mismatch as DEGRADED. Verify the locked venv version and required pydantic/yaml imports immediately after toolchain resolution before every gate/secrets/identity consumer; missing/wrong/import-failing locked Python is exit 1 with no system-python governance fallback. Preserve exit 0/6/1, stderr diagnostics and stdout machine payload. Make ensure_uv check architecture mismatch observational and prevent fingerprint/lock-state mutation while retaining apply concurrency behavior. Independent review follow-up: apply selects only the verified governance secrets owner, never an older workspace copy. Source revision requires the exact repository root and tracked script ownership, so nested copied code cannot borrow an enclosing HEAD. Broad release-gate peer fixtures are isolated against the same real locked-prefix/version/tracked-source helper; no peer installer runtime changes. Present preflight failure retains actionable declared-pin and locked-sync/pypi.org/astral.sh diagnostics. Local topology keeps canonical SSOT clean on main and execution on the feature checkout; no protected source is modified for freshness. | Cursor Build agent | `high` | medium | `[]` | `ops/scripts/bootstrap_agent_environment.sh`, `ops/scripts/ensure_uv_environment.sh`, `ops/scripts/tests/test_bootstrap_diagnostic_contract.py`, `ops/scripts/tests/test_bootstrap_invariants.py`, `ops/scripts/tests/test_uv_environment_fingerprint.sh`, `tests/ops/scripts/test_agent_bootstrap_readiness.py`, `ops/scripts/tests/test_session_start_runtime_report.py`, `environment/agents/adapters/claude-code/tests/test_install_mounts.py`, `ops/scripts/tests/test_capability_plane_counts_degraded.py` |
| T2 | Select Manus validator interpreter only after shared bootstrap returns and fail closed if a locked interpreter is absent. Resolve runtime_script_revision from the actual executing script source root independently of --governance; explicit provenance overrides remain truthful inputs and UNKNOWN remains represented. Add two-clone/copied-script/missing-Git tests, retain mismatch and digest semantics and do not rewrite runtime receipt schema. Default writer source provenance requires exact root and tracked ownership of the executing writer. Explicit overrides and UNKNOWN/omit behavior remain truthful inputs. | Cursor Build agent | `medium` | small | `[T1]` | `environment/agents/adapters/manus/install.sh`, `ops/scripts/write_runtime_readiness_receipt.py`, `ops/scripts/tests/test_runtime_readiness_receipt.py`, `environment/agents/adapters/manus/tests/test_manus_adapter.py`, `tests/ops/scripts/test_agent_bootstrap_readiness.py` |
| T3 | Use canonical shared surface detection for explicit hosted Manus classification. In the shared secrets identity owner, Manus takes only sanctioned runtime machine identity inputs and never imports/probes AWS, seeds credentials or falls back to an operator's Infisical profile, including missing/refused/partial identities. Preserve Cursor/operator authorized bootstrap and self-hosted pool precedence; retain names-only failure/status and no credential exposure. Main executor owns this shared change. Complete the shared identity context through capability_bind: optional explicit environment propagated without os.environ writes; identity/value/source/token/failed-login caches invalidated on context changes before cache hits. Real binder tests prepopulate an operator context and prove explicit/ambient-transition Manus cannot reuse it. | Cursor Build agent | `high` | medium | `[T1]` | `ops/secrets/session_start_secrets.py`, `ops/secrets/infisical_cli_login.py`, `ops/secrets/test_session_start_secrets.py`, `tests/ops/secrets/test_manus_identity_plane.py`, `ops/secrets/capability_bind.py` |
| T4 | Consolidate complete canonical identity assurance at the existing shared owner and invoke it from adapter validation/materialization. Require v2 operating bindings, exact actor_ref/surface_refs and active binding/current projected identities; reject legacy agent_id/status fields, foreign identity, missing scope and tampered/stale/unverifiable projection before any materialized file. Do not edit canonical registries or treat registered identities as OAuth admission. Preserve projector provenance-equivalence semantics rather than forcing source-revision churn. Guard the legacy shared assertion exporter so a nonzero mint cannot source a pre-existing output path; failed/refused fresh exports cannot leave stale assertions accepted by a launcher. A skipped legacy mint preserves its existing scoped pre-launch handoff without claiming a fresh mint; native Manus launchers independently refuse and strip every legacy assertion, so this is not a Manus transport fallback. Trusted canonical checker keeps its code ROOT at the source checkout; only artifact paths are rebound. A fresh-process hostile caller-root ops package must never execute. | Cursor Build agent | `high` | medium | `[]` | `tools/assurance/check_canonical_identity_projection.py`, `ops/memory/identity_projection.py`, `ops/memory/export_agent_assertion_env.sh`, `environment/agents/adapters/manus/materialize_memory_authority.py`, `environment/agents/adapters/manus/validate_manus_adapter.py`, `environment/agents/adapters/manus/tests/test_memory_authority.py`, `tests/test_canonical_identity_projection.py`, `environment/agents/adapters/manus/tests/test_manus_adapter.py`, `tests/ops/memory/test_assertion_export_fail_closed.py` |
| T5 | Replace the historical Manus memory stdio/HMAC carrier, renderer and launcher contract with native authenticated MCP Streamable HTTP consumption or explicit UPSTREAM_BLOCKED. The installed owner package is 2.6.0; owner main ae6e2c0d0c29dfe2a3de3fdf5293e4d996164620 leaves hosted OAuth actor admission issue 108 open. Consume only owner-supplied package/client capabilities and a proven host-managed client binding; do not invent an SDK method, issuer, callback, public client id or credential. A candidate descriptor may cite the existing published resource identifier only as owner contract, never a live endpoint admission. Renderer must refuse an executable connector when required native package/client proof is missing and must not render or start stdio/HMAC/legacy maps as fallback. Materializer remains legacy rejection assurance only, not a production Memory 3.0 credential path. Validator must validate the blocked contract without advertising Memory ready. | Cursor Build agent | `high` | medium | `[T4]` | `environment/agents/adapters/manus/memory-mcp-connector.json`, `environment/agents/adapters/manus/render_memory_mcp_connector.py`, `environment/agents/adapters/manus/serve_memory_mcp.sh`, `environment/agents/adapters/manus/validate_manus_adapter.py`, `environment/agents/adapters/manus/tests/test_manus_adapter.py`, `environment/agents/adapters/manus/tests/test_memory_authority.py`, `environment/agents/adapters/manus/tests/test_native_memory_boundary.py` |
| T6 | Make explicit Manus startup health-only and on-demand retrieval separate from startup and repository mutation, using the existing shared health/envelope and canonical close semantics only if a native owner client is available. Otherwise lifecycle tools report UPSTREAM_BLOCKED with names-only evidence and do not invoke historical signed local/operator CLI as an agent transport. Remove launcher minting for the hosted memory lifecycle path; leave unrelated governance bearer protection and apply authorization unchanged. Align the existing manus-session-start envelope to resolve/health/capabilities only and prohibit admin distill emulation. No custom lifecycle authority or fake public Manus hook. | Cursor Build agent | `high` | medium | `[T5]` | `environment/agents/adapters/manus/memory_lifecycle.py`, `environment/agents/adapters/manus/mcp_server.py`, `environment/agents/adapters/manus/serve_mcp.sh`, `environment/agents/adapters/manus/mcp-connector.json`, `ops/config/memory-hook-envelopes.json`, `environment/agents/adapters/manus/tests/test_memory_lifecycle.py`, `environment/agents/adapters/manus/tests/test_mcp_server.py`, `environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md`, `environment/agents/adapters/manus/tests/test_native_memory_boundary.py` |
| T7 | Separate Infisical configuration shape from observed Universal Auth state in native MCP status; a configured descriptor is not live authentication. Keep status observational, record unverified/observed auth without accidental login, emit stage-specific sanitized 401 errors, clear refused/expired cached tokens and enforce truthful bounded expiresIn semantics including absent, invalid, very short and expired lifetime. Tests use offline fake APIs and confirm no request credential, echoed resolved value or auth response reaches output. Do not expand capabilities or add credentials. Main executor owns this change. Anchor token expiry before login so round-trip time cannot extend it, reject already-expired responses, and recursively inspect original decoded response strings/keys so JSON escaping cannot hide credential echoes. | Cursor Build agent | `high` | medium | `[T3]` | `environment/agents/adapters/manus/infisical_mcp_server.py`, `environment/agents/adapters/manus/tests/test_infisical_mcp_server.py`, `environment/agents/adapters/manus/tests/test_render_infisical_mcp_connector.py` |
| T8 | Update Manus README/setup/session-bootstrap/env comments and shared SURFACE_BOOTSTRAP_CONTRACT to current owner law with matched validator/tests: canonical .github identity versus operating binding; check is observational; locked missing Python blocks; Manus no AWS/profile fallback; native Memory-only/UPSTREAM_BLOCKED; startup health-only, hydration on demand and no memory precondition on coding; Infisical configured/auth separation. Remove active stdio/HMAC/cross-chat secret-map and must-start-before-writes instructions. Keep secret-plane runtime identity distinct from connector-only native Infisical credentials, explicit project instruction versus enforced hook, dormant manus-cloud PE provider and parent-owned stacked PR contract. Do not modify protected root docs or skills. Replace shared SessionStart hydrate/prefetch table and active Claude startup compile_and_format prose with health-only startup and explicitly on-demand retrieval. Documentation correction grants no peer runtime hook. | Cursor Build agent | `medium` | medium | `[T2, T3, T4, T5, T6, T7]` | `environment/agents/adapters/manus/README.md`, `environment/agents/adapters/manus/setup.md`, `environment/agents/adapters/manus/session_bootstrap.md`, `environment/agents/adapters/manus/environment.env.example`, `environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md`, `environment/agents/adapters/manus/validate_manus_adapter.py`, `environment/agents/adapters/manus/tests/test_manus_adapter.py` |
| T9 | Run all scoped proofs, broader applicable shared regressions and the unchanged .pre-commit-config.yaml catalog; distinguish structural admission, unit-fixture results and live Unknowns. Inspect diff against 334faa6957e0c2f67eeea4b397019f6a141a30b8, preserve inherited paths and leave failure evidence honest. Re-run the tool-owned plan pipeline/section admission after any plan change; parent then executes only its authorized scoped commit/L4/stacked PR route and displays the PR URL. No planner-side publication or runtime claim. User explicitly selected PR #826 on 2026-11-05 after sibling #827 appeared. Retain PR_STACK=auto with explicit PR_BASE=origin/feat/fail-closed-plan-pipeline; never reinterpret this as permission to merge, bypass gates, or rebase onto #827. | Cursor Build agent | `medium` | medium | `[T8]` | `docs/plans/manus-adapter-bootstrap-alignment.plan.json`, `docs/plans/manus_adapter_bootstrap_alignment_a15b0001.plan.md`, `docs/plans/manus_adapter_bootstrap_alignment_a15b0001.section-receipt.json`, `docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-decision.json`, `docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-run.json` |

**Critical path:** T4 → T5 → T6 → T8 → T9

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | T1/T2/T3 prove observational bootstrap, early locked interpreter and hosted no-AWS semantics. | Reliable local session readiness without vendor duplication or secret writes. |
| M2 | T4/T5/T6 prove canonical identity consumption and blocked native memory interface. | Honest memory-blind coding and future owner admission without compatibility fallback. |
| M3 | T7/T8/T9 prove auth-truth distinction, current docs/contracts and scoped quality evidence. | Parent-owned stacked PR handoff; does not unlock live OAuth, deployments or memory admission. |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | T1 | V1 fixture no-side-effect snapshots and locked-Python failure matrix. | Stop shared bootstrap changes if check mutates or a policy consumer runs on fallback Python; repair at the shared owner. |
| C2 | T4 | V5 canonical projection/legacy materialization/failed-mint negative cases. | Do not produce credential/grant files or launch any memory process after failed identity assurance. |
| C3 | T6 | V6/V7 prove UPSTREAM_BLOCKED without stdio/HMAC/provider fallback and health-only startup. | Keep memory fail-closed and coding usable; never invent upstream APIs, client registration, credentials or a deployment to clear the blocker. |
| C4 | T9 | V1-V10 scoped checks and diff hygiene, current plan/section admission; parent must separately prove publication gates. | Stop publication on failure, overlapping parent changes or sibling PR chains. No force push, merge or silent embedded-mode switch. |

### Leverage

- **Ranked todos:** `T1`, `T3`, `T2`, `T4`, `T5`, `T6`, `T7`, `T8`, `T9`
- **Shared causes:** Fix observational mode and early locked-toolchain admission once in the shared bootstrap instead of per-adapter patches.; Keep one canonical identity assurance owner and remove adapter legacy bypasses rather than copy registries or regenerate equivalent identity projections.; Do not force a single physical cause: hosted secrets classification, runtime provenance and unsupported native Memory are independently evidenced residual work under one owner-alignment intervention.; Separate configuration, source readiness and live auth/admission so failed/unknown observations cannot be reused as permission.
- **Deletions / consolidations:** Remove system-Python governance fallback and eager validator selection.; Remove active historical Memory stdio/HMAC/secret-map carrier generation and launcher expectations; preserve only explicit rejection tests, not a compatibility production path.; Remove legacy identity/status acceptance and stale failed-mint reuse.; Remove automatic startup hydration and memory-before-repository-write claims.; Consume existing assurance/surface/health/close owners; no new scheduler, auth proxy, lifecycle authority or private surface marker list.

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| environment/agents/adapters/manus/README.md, setup.md, session_bootstrap.md, environment.env.example | `update` | `T8` | Remove retired carrier/lifecycle/AWS instructions and explain honest readiness and auth boundaries. |
| environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md | `update` | `T6`, `T8` | Correct shared lifecycle startup semantics to current health-only/on-demand law without changing law. |
| Root CANONICAL_LAW.md, AGENTS.md, CLAUDE.md, README.md, Makefile and .pre-commit-config.yaml | `n_a` | — | Explicitly protected by task scope; existing law/catalog already own desired semantics and are consumed unchanged. |
| skills/, commands/, rules/ and all 32 inherited PR-chain paths | `n_a` | — | Owner changes already inherited at 334faa6957; no skill modification, manual receipt bypass or unrelated overwrite authorized. |
| Quantum-L9/.github registries/projection and Memory owner repository | `n_a` | — | Pinned current registration/provenance already verified; upstream source is read-only and issue108 remains upstream-owned. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01, SP-02 | `quality_gate_evidence` | command | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q tests/ops/scripts/test_agent_bootstrap_readiness.py ops/scripts/tests/test_bootstrap_diagnostic_contract.py ops/scripts/tests/test_bootstrap_invariants.py` | Exit/status/stdout contracts and new fixture snapshots pass; no check-mode mutation or unlocked policy consumer. Tests must isolate HOME/state and never apply against the active shared .venv. The unchanged UV shell-count fixture fails identically at baseline because its stub counts sync --help; retain its independent baseline failure evidence, not a fabricated PASS. | `passed` |
| E-V2 | SP-02 | `quality_gate_evidence` | command | `bash -n ops/scripts/bootstrap_agent_environment.sh ops/scripts/ensure_uv_environment.sh environment/agents/adapters/manus/install.sh; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_manus_adapter.py` | Syntax and updated contract tests pass; late locked validator selection, missing/wrong/import-failing locked Python and thin installer failure behavior are proved without real bootstrap apply. | `passed` |
| E-V3 | SP-03 | `quality_gate_evidence` | command | `.venv/bin/python -B -m pytest -q ops/scripts/tests/test_runtime_readiness_receipt.py tests/ops/scripts/test_claude_bootstrap_receipt_revision.py tests/ops/scripts/test_agent_bootstrap_readiness.py` | Independent executing-source revision, UNKNOWN provenance, two-clone mismatch and existing receipt reader/digest regressions pass. | `passed` |
| E-V4 | SP-04 | `quality_gate_evidence` | command | `.venv/bin/python -B -m pytest -q ops/secrets/test_session_start_secrets.py tests/ops/secrets/test_manus_identity_plane.py` | Hosted Manus absent/partial/refused/present identity cases never import/probe AWS or use operator profile; existing Cursor/operator/self-hosted cases and names-only receipts pass. | `passed` |
| E-V5 | SP-05 | `quality_gate_evidence` | command | `.venv/bin/python -B tools/assurance/check_canonical_identity_projection.py; .venv/bin/python -B tools/authority/project_canonical_identity.py --authority-root /home/ubuntu/L9-Org-Authority --check; .venv/bin/python -B -m pytest -q tests/test_canonical_identity_projection.py environment/agents/adapters/manus/tests/test_memory_authority.py environment/agents/adapters/manus/tests/test_manus_adapter.py tests/ops/memory/test_assertion_export_fail_closed.py` | Shared canonical binding/projection/receipt and currentness pass; legacy identity/status/tamper/non-current and failed-mint file/stale-env negative cases fail closed with no authority production. | `passed` |
| E-V6 | SP-06 | `quality_gate_evidence` | command | `.venv/bin/python -B environment/agents/adapters/manus/validate_manus_adapter.py --repo-root .; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_manus_adapter.py environment/agents/adapters/manus/tests/test_memory_authority.py; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_native_memory_boundary.py` | Native carrier structurally valid while renderer/readiness reports installed2.6.0 UPSTREAM_BLOCKED; no stdio/HMAC/provider fallback, fabricated OAuth input, executable legacy credential carrier, release or auth claim. | `passed` |
| E-V7 | SP-07 | `quality_gate_evidence` | command | `.venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_memory_lifecycle.py environment/agents/adapters/manus/tests/test_mcp_server.py; .venv/bin/python -B ops/scripts/validate_memory_egress_boundary.py --enforce --root .; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_native_memory_boundary.py` | Updated lifecycle health-only/on-demand/no-write-precondition and blocked-native-client tests pass; no startup hydration, local operator agent fallback, admin distill emulation or provider egress introduced. Governance protection unchanged. | `passed` |
| E-V8 | SP-08 | `quality_gate_evidence` | command | `.venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_infisical_mcp_server.py environment/agents/adapters/manus/tests/test_render_infisical_mcp_connector.py` | Configured/auth-unverified and observed auth states are distinct, status does not authenticate, staged401 errors redact all credentials, short/invalid/expired cache lifetime is truthful and response values remain withheld; only offline proof claimed. | `passed` |
| E-V9 | SP-09 | `quality_gate_evidence` | command | `.venv/bin/python -B skills/l9-plan-simple/scripts/run_plan_pipeline.py --plan-json docs/plans/manus-adapter-bootstrap-alignment.plan.json --execute-via cursor-build --workspace . --gar-run docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-run.json --out-md docs/plans/manus_adapter_bootstrap_alignment_a15b0001.plan.md; .venv/bin/python -B skills/l9-plan-simple/scripts/admit_plan.py --all docs/plans/manus_adapter_bootstrap_alignment_a15b0001.plan.md; git diff --check` | Current pipeline validates JSON, verifies real GAR load-order run, fills canonical projection and validates bound section receipt; admission --all PASS without unbound/undeclared/parameter markers. This is plan-structure admission only. Matching adapter/shared docs no longer teach retired behavior. | `passed` |
| E-V10 | SP-09 | `quality_gate_evidence` | command | `PATH="$PWD/.venv/bin:$PATH" L9_GOVERNANCE_SURFACE=manus PYTHONDONTWRITEBYTECODE=1 make precommit-repo; git diff --check; scoped unchanged .pre-commit-config.yaml hook catalog on all repair/new test paths` | Only approved task paths change; no protected root/inherited/skill/upstream/credential mutation, whitespace defect or weakened gate. Applicable unchanged catalog passes and failures remain evidence. Parent alone authorizes release and publishes its scoped stacked PR after all mandatory implementation proofs pass. | `passed` |

## Stress and disconfirm

### Disconfirming cases

- Can --check with uv absent, architecture mismatch, stale receipts and a writable operator HOME perform any filesystem/network mutation or secrets login before a mode guard?
- Can a missing, wrong-version or import-failing .venv reach gate/secrets/namespace code through an unlocked interpreter, or can Manus retain a system validator chosen before bootstrap repair?
- Does a two-clone readiness test produce different actual runtime/source and governance SHAs, or does the writer alias them and falsely report READY?
- Can explicit Manus with absent/refused/partial credentials be scored as operator and load an unrelated machine profile or import/probe AWS?
- Can legacy agent_id/status, a tampered projection, non-current actor/surface or failed mint with an existing file bypass shared assurance?
- Can a structurally valid native descriptor or OAuth public client name be advertised as actor admission, or can missing owner package2.6.0 support cause an executable stdio/HMAC fallback?
- Does lifecycle startup hydrate/read records or become an implicit repository-write gate despite current law, or does close emulate forbidden hosted admin distill?
- Can configured Infisical shape, an absent/invalid TTL or a fake API success be reported as live auth, or can sanitized401 errors still leak echoed credentials?
- Can final scoped diff overwrite any inherited plan-pipeline owner or parent patch; does a current PR-board change invalidate publication eligibility without changing plan handoff mode?

### Assumption failure conditions

- Assumption false if shared owner changes fail any eligible peer adapter regression; restore/repair shared semantics instead of adding a Manus fork.
- Assumption false if native owner APIs cannot be directly verified; choose explicit UPSTREAM_BLOCKED, not local SDK/credential invention.
- Assumption false if historical canonical projection governing bytes change; rerun existing verifier and keep unproved provenance UNKNOWN, never relabel historical bytes.
- Assumption false if parent workspace gains overlapping modifications; stop and reconcile ownership rather than overwriting or broad staging.
- Assumption false if live auth, package release or current PR topology differs later; reverify downstream, no planning receipt claims admission.

### Blast radius notes

- Shared bootstrap, secrets classification and identity assurance serve every adapter; incorrect edits can allow check-mode mutation, operator credential borrowing or false READY/identity/auth claims across surfaces. Memory transport containment is Manus-local and must not disturb unrelated governance/Infisical servers. No database/deployment migration or credential mutation is in scope.

### Rollback constraints

- Use scoped forward repair or a separately authorized scoped revert of this task's exact changed paths; preserve parent edits and the 32 inherited files. Do not use hard reset, force push, blanket git restore or resurrect retired hosted Memory stdio/HMAC as rollback. Before publication compare source/diff to baseline, rerun affected tests and confirm check leaves fixture state unchanged. No data, credential or deployed external state is changed, so no data rollback is required.

### Risks

| risk | mitigation |
|------|------------|
| Shared check/preflight corrections change other adapters' degraded/blocked behavior. | Fixture-first 0/6/1 and peer bootstrap regression matrix; keep optional components fail-soft and required locked interpreter fail-closed. |
| Native Memory adoption cannot be completed from installed package2.6.0 and open owner OAuth actor issue108. | Implement honest native carrier/render/readiness refusal, report UPSTREAM_BLOCKED and leave coding usable; no package upgrade or live admission claim. |
| Hosted surface detection or auth status accidentally borrows operator state or exposes a credential. | Use shared surface owner, forbid hosted operator profile/AWS and use names-only staged results with synthetic secret-negative tests. |
| Structural plan admission is mistaken for completed implementation or live runtime admission. | Keep final checks pending and convergence partial until executor proves them; tool-owned GAR receipt is a load-order artifact, not external orchestration/auth evidence. |
| PR-chain baseline drift or inherited scope leakage. | 334faa6957 baseline and protected inherited-path set; parent alone refreshes chain tip/gates and publishes scoped stack with PR_STACK=auto. |

## Out of scope

- Planning subagent may create only this plan's docs/plans artifacts and bounded owner-script prefetch evidence; no code patches, branches, Git commits, pushes, pull requests, deployments or runtime/credential changes.
- No edits to CANONICAL_LAW.md, AGENTS.md, CLAUDE.md, README.md, Makefile, .pre-commit-config.yaml, any skill, command, rule, generated skill registry or any of the 32 inherited PR-chain files.
- No upstream Quantum-L9/.github or l9-graphiti-memory mutation, release admission, issue closure, deployment or package/uv.lock change.
- No Auth0 tenant issuer/client/callback invention, token/secret writes, OAuth login, live Memory operation, local stdio-to-HTTP bridge, provider client or historical HMAC/bearer fallback.
- No reinterpretation of OAuth subject/client as actor/surface; no claim of live auth, hosted/client/mobile admission, externally executed GAR/Cognitive Runtime, controller transport or effective PR authority from structure.
- No root protected-file edits, skill modification, arbitrary API/shell capability, broad registry refactor, changes to authorized Cursor operator bootstrap or weakening gates/tests for green.
- No Program Execution, Program Lock, Controller lease, campaign execution, autonomous merge or persistent automation. Future publication is parent/executor-owned and requires current stacked-PR/L4 authority.
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.manus_adapter_bootstrap_alignment.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.manus_adapter_bootstrap_alignment.v1` |
| source_ref | `plan.simple.manus_adapter_bootstrap_alignment.v1` |
| current_state | `draft` |
| implementation_ready | `false` |

### Gates

- **executable_when:**
  - baseline locked + reverified
  - blocking capability probes pass
  - DAG acyclic
  - envelope + side-effect matrix complete for mutate todos
  - no blocking unknowns
- **complete_when:**
  - all blocking success-property evidence `passed`
  - rollback contract still valid / unused-or-verified
  - out_of_scope respected (diff hygiene)
- **blocking_conditions:**
  - `preflight_blocked`
  - envelope breach
  - baseline drift
  - failed blocking property

### Evidence

- **required_evidence_refs:** E-V1, E-V2, E-V3, E-V4, E-V5, E-V6, E-V7, E-V8, E-V9, E-V10
- **observed_evidence_refs:** E-V1, E-V2, E-V3, E-V4, E-V5, E-V6, E-V7, E-V8, E-V9, E-V10
- **missing_evidence:** none

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `unknown` | U1 | When will the exact native Memory package/client and hosted OAuth actor admission be accepted by Memory owner issue108? — Blocks live memory capability and executable connector rendering; does not block local adapter repair, structural validation or coding session. | `accept_bounded` |
| `unknown` | U2 | What actual Manus host-managed OAuth public client/callback binding and Auth0 issuer admission will the owner/operator prove? — Remain UNKNOWN; no renderer or document invents these values and registered actor/surface does not prove principal attribution. | `accept_bounded` |
| `unknown` | U3 | Will live Infisical Universal Auth and native hosted-client/mobile proof succeed in a separately authorized runtime campaign? — Offline tests and descriptor shape cannot answer; no live login, token write, capability or readiness claim in this task. | `accept_bounded` |
| `unknown` | U4 | Will parent execution/publication still have a unique compatible open-PR chain tip at handoff? — Reverify downstream before source mutation/publication; sibling chains or overlapping parent dirt require stop, never silent mode switch. | `accept_bounded` |
| `open_blocker` | stop_reason | All in-scope source repairs and seven independent-review closures are implemented. Final integrated offline selection: 780 passed and 43 subtests; reporter suite: 79 passed and 17 subtests; final scoped security closure review PASS; real Manus check returned 6 with stdout empty and 71 observed Git/runtime entries unchanged. Unchanged hook catalog, locked Ruff/format, bash syntax, diff hygiene, canonical identity and required plan pipeline/admission pass. Native Memory remains UPSTREAM_BLOCKED, client UNBOUND, live UNKNOWN; live Infisical auth was not attempted. UV shell-count fixture failure is pre-existing and reproduced at unchanged baseline; Python UV/locking/seal regressions pass. User explicitly approved the existing #826 stack target after sibling #827 appeared. Scoped commit/release publication is the remaining parent ceremony, not a runtime deployment or merge. Release follow-up: first canonical gate security passed, but broad pytest exposed obsolete peer fixture assumptions plus an overbroad skipped-mint compatibility change; exact mandated14-nodeid recheck now passes. Existing peer handoff is preserved only when mint was not attempted; failed/fresh mints clear stale outputs and nonzero helper output files are never sourced. Canonical SSOT local pointer now resolves to a clean-main worktree; feature source remains separate, wired PASS. Follow-up validation/commit and canonical publication are in progress; no gate bypass. | planning convergence `partial` |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `executable_when` |
| minimum_safe_next_action | When law holds and status=`executable`, press **Build**, stack if any open PR exists (`PR_STACK=auto`), then `make pr` and display the PR URL — do not free-form execute |
| execute_via | Cursor Build; stacked PR if any open PR exists; display PR URL |
| next_skill | Build then stacked make pr |
| broader_work_requires_separate_contract | `true` |

---

## Machine stub (optional YAML instance seed)

Projected from PLAN_DOCUMENT; keep in sync with the sections above.

```yaml
schema_id: "canonical.schema.plan_document.v1"
schema_version: "1.0.0"
metadata:
  plan_id: "plan.simple.manus_adapter_bootstrap_alignment.v1"
  name: "Manus adapter bootstrap alignment"
  overview: "Fully align the Manus adapter with current shared bootstrap, identity, secrets and native Memory contracts without inventing authority. Planning is an artifact-only subtask; downstream implementation remains the user's requested outcome. Use the existing shared owners for observational check, locked-Python preflight, independent source-revision readiness and hosted Manus no-AWS/no-operator-profile classification. Replace the historical Manus Memory stdio/HMAC carrier with a fail-closed native Memory 3.0 carrier/render/readiness interface that explicitly reports UPSTREAM_BLOCKED while the owner package/client and OAuth actor admission are unavailable. Keep ordinary coding usable memory-blind. Baseline is Quantum-L9/Cursor-Governance branch fix/manus-bootstrap-alignment at 334faa6957e0c2f67eeea4b397019f6a141a30b8, advanced by the parent before any source edit onto the unique PR chain #824 -> #825 -> #826 (feat/fail-closed-plan-pipeline). Preserve all 32 inherited paths and every existing owner contract. GAR decision and reasoning-owner receipts are docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-decision.json; the tool-owned GAR run and plan pipeline own structural admission only, never runtime or live-auth admission."
  status: "draft"
  is_project: false
  owner: "l9.actor-registry/global@1#manus"
architect_framing:
  planning_ssot: "PLAN_DOCUMENT"
  plan_class: "bounded_execution_contract"
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: "Quantum-L9/Cursor-Governance"
  commit_sha: "8e035cb36bee164adfa74c3354f61a8763561c92"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Fully align the Manus adapter with current shared bootstrap, identity, secrets and native Memory contracts without inventing authority. Planning is an artifact-only subtask; downstream implementation remains the user's requested outcome. Use the existing shared owners for observational check, locked-Python preflight, independent source-revision readiness and hosted Manus no-AWS/no-operator-profile classification. Replace the historical Manus Memory stdio/HMAC carrier with a fail-closed native Memory 3.0 carrier/render/readiness interface that explicitly reports UPSTREAM_BLOCKED while the owner package/client and OAuth actor admission are unavailable. Keep ordinary coding usable memory-blind. Baseline is Quantum-L9/Cursor-Governance branch fix/manus-bootstrap-alignment at 334faa6957e0c2f67eeea4b397019f6a141a30b8, advanced by the parent before any source edit onto the unique PR chain #824 -> #825 -> #826 (feat/fail-closed-plan-pipeline). Preserve all 32 inherited paths and every existing owner contract. GAR decision and reasoning-owner receipts are docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-decision.json; the tool-owned GAR run and plan pipeline own structural admission only, never runtime or live-auth admission."
  success_properties:
    - id: "SP-01"
      property: "V1 proves shared bootstrap --check performs no installation, secrets login/profile mutation, receipt removal/write, Git exclude/prune/ref mutation or scratch restoration; it leaves fixture filesystem snapshots unchanged and reports unsynchronized/missing optional components as exit 6 rather than READY."
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V1 and V2 prove locked .venv absence, wrong pinned version or required import failure exits 1 before any policy/secrets/namespace/readiness consumer and never executes system Python for governance work; Manus install selects the locked validator interpreter after bootstrap."
      evidence_type: "quality_gate"
      proof: ["V1", "V2"]
      blocking: true
    - id: "SP-03"
      property: "V3 proves runtime_script_revision is independently resolved from the executing script owner, not copied from --governance; mismatched two-clone revisions yield NOT_READY/REVISION_MISMATCH and missing provenance remains UNKNOWN."
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-04"
      property: "V4 proves explicit hosted Manus classification uses the shared surface detector, performs no AWS import/probe/seed or operator profile fallback whether the machine identity is present, absent or refused, never exposes values, and preserves authorized Cursor/operator behavior."
      evidence_type: "quality_gate"
      proof: ["V4"]
      blocking: true
    - id: "SP-05"
      property: "V5 proves canonical identity assurance is owned by the shared verifier; Manus materialization rejects legacy agent_id/status shortcuts, foreign/unknown/non-current actor or surface, inactive binding and stale/tampered projection before producing files; failed mint paths never source or reuse an existing assertion file."
      evidence_type: "quality_gate"
      proof: ["V5"]
      blocking: true
    - id: "SP-06"
      property: "V6 proves the committed Memory carrier is native authenticated Streamable HTTP, contains no fabricated issuer/client/callback/credential or stdio/HMAC/provider fallback, and renderer/readiness refuse the installed 2.6.0 package as UPSTREAM_BLOCKED without starting it or changing the lockfile. Canonical actor manus and surface manus-cloud remain registration only, not auth proof."
      evidence_type: "quality_gate"
      proof: ["V6"]
      blocking: true
    - id: "SP-07"
      property: "V7 proves lifecycle startup is bounded health-only, retrieval is explicit/on-demand and not a repository-write precondition; native-client absence or unproved OAuth actor admission is fail-closed for memory while governance remains usable. No lifecycle wrapper emulates admin distill or a local operator agent door."
      evidence_type: "quality_gate"
      proof: ["V7"]
      blocking: true
    - id: "SP-08"
      property: "V8 proves Infisical configured shape is separate from observed auth state, 401 outcomes name the failing stage without leaking request/response credentials, token expiry/invalid expiry never overstates usable lifetime, and offline fixtures cannot be described as live Universal Auth proof."
      evidence_type: "quality_gate"
      proof: ["V8"]
      blocking: true
    - id: "SP-09"
      property: "V9 and V10 prove matching docs/contracts/tests contain no active legacy memory instructions, preserve unrelated governance/Infisical MCP safety, pass scoped quality gates and contain only this plan's allowlisted changes; root protected files, inherited planning owners, upstream .github/Memory and secrets remain untouched."
      evidence_type: "quality_gate"
      proof: ["V9", "V10"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.manus_adapter_bootstrap_alignment.v1"
execution_envelope:
  filesystem:
    write_allow: ["ops/scripts/bootstrap_agent_environment.sh", "ops/scripts/ensure_uv_environment.sh", "ops/scripts/write_runtime_readiness_receipt.py", "ops/scripts/tests/test_bootstrap_diagnostic_contract.py", "ops/scripts/tests/test_bootstrap_invariants.py", "ops/scripts/tests/test_uv_environment_fingerprint.sh", "ops/scripts/tests/test_runtime_readiness_receipt.py", "ops/secrets/session_start_secrets.py", "ops/secrets/infisical_cli_login.py", "ops/secrets/test_session_start_secrets.py", "tools/assurance/check_canonical_identity_projection.py", "ops/memory/identity_projection.py", "ops/memory/export_agent_assertion_env.sh", "ops/config/memory-hook-envelopes.json", "tests/test_canonical_identity_projection.py", "environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md", "environment/agents/adapters/manus/install.sh", "environment/agents/adapters/manus/validate_manus_adapter.py", "environment/agents/adapters/manus/materialize_memory_authority.py", "environment/agents/adapters/manus/memory-mcp-connector.json", "environment/agents/adapters/manus/render_memory_mcp_connector.py", "environment/agents/adapters/manus/serve_memory_mcp.sh", "environment/agents/adapters/manus/memory_lifecycle.py", "environment/agents/adapters/manus/mcp_server.py", "environment/agents/adapters/manus/serve_mcp.sh", "environment/agents/adapters/manus/mcp-connector.json", "environment/agents/adapters/manus/infisical_mcp_server.py", "environment/agents/adapters/manus/README.md", "environment/agents/adapters/manus/setup.md", "environment/agents/adapters/manus/session_bootstrap.md", "environment/agents/adapters/manus/environment.env.example", "environment/agents/adapters/manus/tests/test_manus_adapter.py", "environment/agents/adapters/manus/tests/test_memory_authority.py", "environment/agents/adapters/manus/tests/test_memory_lifecycle.py", "environment/agents/adapters/manus/tests/test_mcp_server.py", "environment/agents/adapters/manus/tests/test_infisical_mcp_server.py", "environment/agents/adapters/manus/tests/test_render_infisical_mcp_connector.py", "docs/plans/manus-adapter-bootstrap-alignment.plan.json", "docs/plans/manus_adapter_bootstrap_alignment_a15b0001.plan.md", "docs/plans/manus_adapter_bootstrap_alignment_a15b0001.section-receipt.json", "docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-decision.json", "docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-run.json", "tests/ops/scripts/test_agent_bootstrap_readiness.py", "tests/ops/secrets/test_manus_identity_plane.py", "tests/ops/memory/test_assertion_export_fail_closed.py", "environment/agents/adapters/manus/tests/test_native_memory_boundary.py", "ops/secrets/capability_bind.py", "ops/scripts/tests/test_session_start_runtime_report.py", "environment/agents/adapters/claude-code/tests/test_install_mounts.py", "ops/scripts/tests/test_capability_plane_counts_degraded.py"]
    write_deny: ["CANONICAL_LAW.md", "AGENTS.md", "CLAUDE.md", "README.md", "Makefile", ".pre-commit-config.yaml", "skills/", "commands/", "rules/", "pyproject.toml", "uv.lock", "generated/governance/canonical_identity.yaml", "generated/governance/canonical_identity.receipt.yaml", "environment/agents/agent_registry.yaml", "governance/authority-bindings/canonical-agent-identity.yaml", "all inherited 061fae50..334faa69 paths", "/home/ubuntu/L9-Org-Authority", "/home/ubuntu/L9-Memory-Owner", "credential/secret stores, deployed services, account configuration and shared live .venv"]
  commands:
    allow: ["Run V1-V10 from /home/ubuntu/Cursor-Governance using .venv/bin/python -B and isolated fixtures; no bootstrap apply or live login against the active shared environment.", "After all proofs pass parent may use its own scoped commit and authorize-release, then PR_STACK=auto PR_REMEDIATE=0 make pr, and must display the opened PR URL. Planning subagent performs none of these external effects.", "PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q tests/ops/scripts/test_agent_bootstrap_readiness.py ops/scripts/tests/test_bootstrap_diagnostic_contract.py ops/scripts/tests/test_bootstrap_invariants.py", "bash -n ops/scripts/bootstrap_agent_environment.sh ops/scripts/ensure_uv_environment.sh environment/agents/adapters/manus/install.sh; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_manus_adapter.py", ".venv/bin/python -B -m pytest -q ops/scripts/tests/test_runtime_readiness_receipt.py tests/ops/scripts/test_claude_bootstrap_receipt_revision.py tests/ops/scripts/test_agent_bootstrap_readiness.py", ".venv/bin/python -B -m pytest -q ops/secrets/test_session_start_secrets.py tests/ops/secrets/test_manus_identity_plane.py", ".venv/bin/python -B tools/assurance/check_canonical_identity_projection.py; .venv/bin/python -B tools/authority/project_canonical_identity.py --authority-root /home/ubuntu/L9-Org-Authority --check; .venv/bin/python -B -m pytest -q tests/test_canonical_identity_projection.py environment/agents/adapters/manus/tests/test_memory_authority.py environment/agents/adapters/manus/tests/test_manus_adapter.py tests/ops/memory/test_assertion_export_fail_closed.py", ".venv/bin/python -B environment/agents/adapters/manus/validate_manus_adapter.py --repo-root .; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_manus_adapter.py environment/agents/adapters/manus/tests/test_memory_authority.py; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_native_memory_boundary.py", ".venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_memory_lifecycle.py environment/agents/adapters/manus/tests/test_mcp_server.py; .venv/bin/python -B ops/scripts/validate_memory_egress_boundary.py --enforce --root .; .venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_native_memory_boundary.py", ".venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests/test_infisical_mcp_server.py environment/agents/adapters/manus/tests/test_render_infisical_mcp_connector.py", ".venv/bin/python -B skills/l9-plan-simple/scripts/run_plan_pipeline.py --plan-json docs/plans/manus-adapter-bootstrap-alignment.plan.json --execute-via cursor-build --workspace . --gar-run docs/plans/manus_adapter_bootstrap_alignment_a15b0001.gar-run.json --out-md docs/plans/manus_adapter_bootstrap_alignment_a15b0001.plan.md; .venv/bin/python -B skills/l9-plan-simple/scripts/admit_plan.py --all docs/plans/manus_adapter_bootstrap_alignment_a15b0001.plan.md; git diff --check", "PATH=\"$PWD/.venv/bin:$PATH\" L9_GOVERNANCE_SURFACE=manus PYTHONDONTWRITEBYTECODE=1 make precommit-repo; git diff --check; scoped unchanged .pre-commit-config.yaml hook catalog on all repair/new test paths"]
  network:
    mode: "bounded_external_write"
  secrets:
    access: "none"
    redaction_required: true
  autonomous_merge: false
side_effects_and_idempotency:
  - todo_id: "T1"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T2"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T3"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T4"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T5"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T6"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T7"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T8"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T9"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
rollback_contract_ref: "rollback.plan.simple.manus_adapter_bootstrap_alignment.v1"
dependency_topology_ref: "dag.plan.simple.manus_adapter_bootstrap_alignment.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4", "E-V5", "E-V6", "E-V7", "E-V8", "E-V9", "E-V10"]
stress_and_disconfirm:
  disconfirming_cases: ["Can --check with uv absent, architecture mismatch, stale receipts and a writable operator HOME perform any filesystem/network mutation or secrets login before a mode guard?", "Can a missing, wrong-version or import-failing .venv reach gate/secrets/namespace code through an unlocked interpreter, or can Manus retain a system validator chosen before bootstrap repair?", "Does a two-clone readiness test produce different actual runtime/source and governance SHAs, or does the writer alias them and falsely report READY?", "Can explicit Manus with absent/refused/partial credentials be scored as operator and load an unrelated machine profile or import/probe AWS?", "Can legacy agent_id/status, a tampered projection, non-current actor/surface or failed mint with an existing file bypass shared assurance?", "Can a structurally valid native descriptor or OAuth public client name be advertised as actor admission, or can missing owner package2.6.0 support cause an executable stdio/HMAC fallback?", "Does lifecycle startup hydrate/read records or become an implicit repository-write gate despite current law, or does close emulate forbidden hosted admin distill?", "Can configured Infisical shape, an absent/invalid TTL or a fake API success be reported as live auth, or can sanitized401 errors still leak echoed credentials?", "Can final scoped diff overwrite any inherited plan-pipeline owner or parent patch; does a current PR-board change invalidate publication eligibility without changing plan handoff mode?"]
  assumption_failure_conditions: ["Assumption false if shared owner changes fail any eligible peer adapter regression; restore/repair shared semantics instead of adding a Manus fork.", "Assumption false if native owner APIs cannot be directly verified; choose explicit UPSTREAM_BLOCKED, not local SDK/credential invention.", "Assumption false if historical canonical projection governing bytes change; rerun existing verifier and keep unproved provenance UNKNOWN, never relabel historical bytes.", "Assumption false if parent workspace gains overlapping modifications; stop and reconcile ownership rather than overwriting or broad staging.", "Assumption false if live auth, package release or current PR topology differs later; reverify downstream, no planning receipt claims admission."]
out_of_scope: ["Planning subagent may create only this plan's docs/plans artifacts and bounded owner-script prefetch evidence; no code patches, branches, Git commits, pushes, pull requests, deployments or runtime/credential changes.", "No edits to CANONICAL_LAW.md, AGENTS.md, CLAUDE.md, README.md, Makefile, .pre-commit-config.yaml, any skill, command, rule, generated skill registry or any of the 32 inherited PR-chain files.", "No upstream Quantum-L9/.github or l9-graphiti-memory mutation, release admission, issue closure, deployment or package/uv.lock change.", "No Auth0 tenant issuer/client/callback invention, token/secret writes, OAuth login, live Memory operation, local stdio-to-HTTP bridge, provider client or historical HMAC/bearer fallback.", "No reinterpretation of OAuth subject/client as actor/surface; no claim of live auth, hosted/client/mobile admission, externally executed GAR/Cognitive Runtime, controller transport or effective PR authority from structure.", "No root protected-file edits, skill modification, arbitrary API/shell capability, broad registry refactor, changes to authorized Cursor operator bootstrap or weakening gates/tests for green.", "No Program Execution, Program Lock, Controller lease, campaign execution, autonomous merge or persistent automation. Future publication is parent/executor-owned and requires current stacked-PR/L4 authority."]
convergence_contract_ref: "conv.plan.simple.manus_adapter_bootstrap_alignment.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Repair the shared bootstrap owner, not a Manus copy: branch check/apply before UV provisioning, secrets removal/login/mkdir, receipt writes and other mutation; count check-mode UV mismatch as DEGRADED. Verify the locked venv version and required pydantic/yaml imports immediately after toolchain resolution before every gate/secrets/identity consumer; missing/wrong/import-failing locked Python is exit 1 with no system-python governance fallback. Preserve exit 0/6/1, stderr diagnostics and stdout machine payload. Make ensure_uv check architecture mismatch observational and prevent fingerprint/lock-state mutation while retaining apply concurrency behavior. Independent review follow-up: apply selects only the verified governance secrets owner, never an older workspace copy. Source revision requires the exact repository root and tracked script ownership, so nested copied code cannot borrow an enclosing HEAD. Broad release-gate peer fixtures are isolated against the same real locked-prefix/version/tracked-source helper; no peer installer runtime changes. Present preflight failure retains actionable declared-pin and locked-sync/pypi.org/astral.sh diagnostics. Local topology keeps canonical SSOT clean on main and execution on the feature checkout; no protected source is modified for freshness."
    status: "pending"
  - id: "T2"
    content: "Select Manus validator interpreter only after shared bootstrap returns and fail closed if a locked interpreter is absent. Resolve runtime_script_revision from the actual executing script source root independently of --governance; explicit provenance overrides remain truthful inputs and UNKNOWN remains represented. Add two-clone/copied-script/missing-Git tests, retain mismatch and digest semantics and do not rewrite runtime receipt schema. Default writer source provenance requires exact root and tracked ownership of the executing writer. Explicit overrides and UNKNOWN/omit behavior remain truthful inputs."
    status: "pending"
  - id: "T3"
    content: "Use canonical shared surface detection for explicit hosted Manus classification. In the shared secrets identity owner, Manus takes only sanctioned runtime machine identity inputs and never imports/probes AWS, seeds credentials or falls back to an operator's Infisical profile, including missing/refused/partial identities. Preserve Cursor/operator authorized bootstrap and self-hosted pool precedence; retain names-only failure/status and no credential exposure. Main executor owns this shared change. Complete the shared identity context through capability_bind: optional explicit environment propagated without os.environ writes; identity/value/source/token/failed-login caches invalidated on context changes before cache hits. Real binder tests prepopulate an operator context and prove explicit/ambient-transition Manus cannot reuse it."
    status: "pending"
  - id: "T4"
    content: "Consolidate complete canonical identity assurance at the existing shared owner and invoke it from adapter validation/materialization. Require v2 operating bindings, exact actor_ref/surface_refs and active binding/current projected identities; reject legacy agent_id/status fields, foreign identity, missing scope and tampered/stale/unverifiable projection before any materialized file. Do not edit canonical registries or treat registered identities as OAuth admission. Preserve projector provenance-equivalence semantics rather than forcing source-revision churn. Guard the legacy shared assertion exporter so a nonzero mint cannot source a pre-existing output path; failed/refused fresh exports cannot leave stale assertions accepted by a launcher. A skipped legacy mint preserves its existing scoped pre-launch handoff without claiming a fresh mint; native Manus launchers independently refuse and strip every legacy assertion, so this is not a Manus transport fallback. Trusted canonical checker keeps its code ROOT at the source checkout; only artifact paths are rebound. A fresh-process hostile caller-root ops package must never execute."
    status: "pending"
  - id: "T5"
    content: "Replace the historical Manus memory stdio/HMAC carrier, renderer and launcher contract with native authenticated MCP Streamable HTTP consumption or explicit UPSTREAM_BLOCKED. The installed owner package is 2.6.0; owner main ae6e2c0d0c29dfe2a3de3fdf5293e4d996164620 leaves hosted OAuth actor admission issue 108 open. Consume only owner-supplied package/client capabilities and a proven host-managed client binding; do not invent an SDK method, issuer, callback, public client id or credential. A candidate descriptor may cite the existing published resource identifier only as owner contract, never a live endpoint admission. Renderer must refuse an executable connector when required native package/client proof is missing and must not render or start stdio/HMAC/legacy maps as fallback. Materializer remains legacy rejection assurance only, not a production Memory 3.0 credential path. Validator must validate the blocked contract without advertising Memory ready."
    status: "pending"
  - id: "T6"
    content: "Make explicit Manus startup health-only and on-demand retrieval separate from startup and repository mutation, using the existing shared health/envelope and canonical close semantics only if a native owner client is available. Otherwise lifecycle tools report UPSTREAM_BLOCKED with names-only evidence and do not invoke historical signed local/operator CLI as an agent transport. Remove launcher minting for the hosted memory lifecycle path; leave unrelated governance bearer protection and apply authorization unchanged. Align the existing manus-session-start envelope to resolve/health/capabilities only and prohibit admin distill emulation. No custom lifecycle authority or fake public Manus hook."
    status: "pending"
  - id: "T7"
    content: "Separate Infisical configuration shape from observed Universal Auth state in native MCP status; a configured descriptor is not live authentication. Keep status observational, record unverified/observed auth without accidental login, emit stage-specific sanitized 401 errors, clear refused/expired cached tokens and enforce truthful bounded expiresIn semantics including absent, invalid, very short and expired lifetime. Tests use offline fake APIs and confirm no request credential, echoed resolved value or auth response reaches output. Do not expand capabilities or add credentials. Main executor owns this change. Anchor token expiry before login so round-trip time cannot extend it, reject already-expired responses, and recursively inspect original decoded response strings/keys so JSON escaping cannot hide credential echoes."
    status: "pending"
  - id: "T8"
    content: "Update Manus README/setup/session-bootstrap/env comments and shared SURFACE_BOOTSTRAP_CONTRACT to current owner law with matched validator/tests: canonical .github identity versus operating binding; check is observational; locked missing Python blocks; Manus no AWS/profile fallback; native Memory-only/UPSTREAM_BLOCKED; startup health-only, hydration on demand and no memory precondition on coding; Infisical configured/auth separation. Remove active stdio/HMAC/cross-chat secret-map and must-start-before-writes instructions. Keep secret-plane runtime identity distinct from connector-only native Infisical credentials, explicit project instruction versus enforced hook, dormant manus-cloud PE provider and parent-owned stacked PR contract. Do not modify protected root docs or skills. Replace shared SessionStart hydrate/prefetch table and active Claude startup compile_and_format prose with health-only startup and explicitly on-demand retrieval. Documentation correction grants no peer runtime hook."
    status: "pending"
  - id: "T9"
    content: "Run all scoped proofs, broader applicable shared regressions and the unchanged .pre-commit-config.yaml catalog; distinguish structural admission, unit-fixture results and live Unknowns. Inspect diff against 334faa6957e0c2f67eeea4b397019f6a141a30b8, preserve inherited paths and leave failure evidence honest. Re-run the tool-owned plan pipeline/section admission after any plan change; parent then executes only its authorized scoped commit/L4/stacked PR route and displays the PR URL. No planner-side publication or runtime claim. User explicitly selected PR #826 on 2026-11-05 after sibling #827 appeared. Retain PR_STACK=auto with explicit PR_BASE=origin/feat/fail-closed-plan-pipeline; never reinterpret this as permission to merge, bypass gates, or rebase onto #827."
    status: "pending"
```
