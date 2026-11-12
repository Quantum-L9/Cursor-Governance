---
name: "Close surface-profile friction: review threads on native routes and profile drift"
overview: "Make the PR review-thread helper usable from every governed repository, including native publish routes, without widening its authority, and remove the drift between ops/autonomy/surface_profile.yaml and the rules and surfaces it governs (findings F1a, F1b, F1c, F2, F3, F4, F5)."
todos:
  - id: T1
    content: "In ops/scripts/lib/pr_thread_routes.py keep load_summary and the receipt branch of require_own_pr unchanged. When the receipt file is absent, prove ownership live: GET repos/{origin}/pulls/{n} through the injectable run (`gh api --method GET`), require state open, head.repo.full_name equal to origin (case-insensitive), head.ref equal to the checkout branch from `git rev-parse --abbrev-ref HEAD` (detached HEAD refuses), and `git merge-base --is-ancestor <head.sha> HEAD` exit 0. Any unreadable fact, non-JSON or failed command refuses through fail(). require_own_pr takes run as a keyword argument. A null head.repo (deleted fork) refuses. A head SHA absent from the local object store makes merge-base exit non-zero and refuses; nothing is fetched to make it pass. Update the module docstring to name the home-relative allowlisted form."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "In ops/scripts/pr_threads.py pass run into require_own_pr so tests and the live call share one transport. Update the module docstring: ownership is the pr-summary receipt when present, otherwise the live head-branch proof."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Extend ops/scripts/tests/test_pr_threads.py: a tmp git repository on branch feat/x whose HEAD is the PR head writes after the live proof (GET then POST); each of closed PR, foreign head repo, other head ref, head SHA not an ancestor of HEAD, detached HEAD and GET failure refuses with no POST; a head SHA behind HEAD (unpushed local fix) is accepted. test_missing_receipt_refuses keeps its intent as no write outside a git checkout and asserts no POST rather than no call. Add an assertion that the template allows the home-relative helper form. The fixture is a real repository from git init -b feat/x with one commit; a null head.repo case refuses with no POST."
    status: pending
    phase: execute
    depends_on: [T1, T2, T4]
  - id: T4
    content: "Add `Bash(python3 ~/.cursor-governance/ops/scripts/pr_threads.py:*)` to permissions.allow in environment/agents/adapters/claude-code/settings.template.json beside the two relative forms; add the same string to surface_profile.yaml review_activity.allow_prefixes; regenerate the committed .claude/settings.json with `reconcile_claude_settings.py --root . --skip-user`."
    status: pending
    phase: execute
    depends_on: []
  - id: T5
    content: "In skills/l9-pr-remediation/references/review-replies.md name the consumer-repository form `python3 ~/.cursor-governance/ops/scripts/pr_threads.py ...` and the live ownership proof used when no pr-summary receipt exists."
    status: pending
    phase: execute
    depends_on: [T1, T4]
  - id: T6
    content: "surface_profile.yaml: add pull_request_review_approval to forbid; add post_push.pr_watch: subscribe_pr_activity_events_only with a comment naming the Send Later ban; set post_push.required_command comment and add post_push.native_routes: ops/config/publish-authority.json; set pr_stacking.github_rest.pat_ref to GITHUB_TOKEN with a legacy-alias comment and drop bare gh from sanctioned_routes; set updated to 2026-11-12. Update review_activity: keep receipt, add ownership_fallback describing the live proof so the profile matches pr_thread_routes.require_own_pr."
    status: pending
    phase: execute
    depends_on: []
  - id: T7
    content: "bootstrap_capability_preflight.sh: make the Send Later line and its header comment cite surface_profile post_push.pr_watch; tests/adapters/claude_code/test_capability_friction_contract.py asserts the profile key value and the citation."
    status: pending
    phase: execute
    depends_on: [T6]
  - id: T8
    content: "Regenerate environment/generated/llm-rules/MANIFEST.json with .venv/bin/python ops/scripts/project_llm_rules.py --root . : the manifest records source_sha256 of the whole surface_profile.yaml, so any profile edit changes it. Never hand-edit the generated tree."
    status: pending
    phase: execute
    depends_on: [T4, T6]
isProject: false
kind: simple
execute_via: cursor-build
status: current
kernel_pass:
  bound_path: docs/plans/surface_profile_friction_7c3e9a14.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-11-12T01:05:00Z
    body_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    deltas: ["T1 bounds two unreadable-fact cases: a null head.repo (deleted fork) and a head SHA missing from the local object store both refuse, and nothing is fetched to make the proof pass", "T3 names a real git-init fixture on feat/x and adds the null head.repo refusal case"]
  recursive_alignment:
    kernel: kernels/Recursive Alignment.md
    ran_at: 2026-11-12T01:07:00Z
    body_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    deltas: ["T6 adds review_activity.ownership_fallback so the profile describes the same ownership rule as pr_thread_routes.require_own_pr instead of naming only the receipt", "T1 and T2 update both module docstrings, which today state the receipt is the only ownership proof and the relative command the only allowlisted form"]
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-11-12T01:41:00Z
    body_sha256: "9a934656e462887129cec6e63eb93b2a4a3249a02da1629e00553a0c31380ae4"
    deltas: ["V3 repaired: validate_claude_env.py has no --root option (it validates the repository it lives in), so the planned command would have failed for a reason unrelated to the change", "V6 added: project_llm_rules.py --root . --check proves the generated rule projection is still current after the profile edit", "T8 added after V6 failed during Build with drift: MANIFEST.json (main at 1d79d50 passes the same check): environment/generated/llm-rules/MANIFEST.json records source_sha256 of the whole surface_profile.yaml, so it must be regenerated in the same change and is now in the modification lock"]
---

# PLAN: Close surface-profile friction: review threads on native routes and profile drift

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift_94415b12.plan.md`
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
| plan_id | `plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1` |
| name | Close surface-profile friction: review threads on native routes and profile drift |
| overview | Make the PR review-thread helper usable from every governed repository, including native publish routes, without widening its authority, and remove the drift between ops/autonomy/surface_profile.yaml and the rules and surfaces it governs (findings F1a, F1b, F1c, F2, F3, F4, F5). |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial`; remaining unknowns: U1 |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-12T00:43:39+00:00 |
| updated_at | 2026-11-12T00:43:39+00:00 |
| depth | `standard` |
| estimate | 1 GMP |

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
| captured_at | `2026-11-12T00:43:39+00:00` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/home/user/cg-surface-profile` |
| branch | `agent/claude/surface-profile-friction` |
| commit_sha | `1d79d50e028935961dd631990a030ba1f22f7afc` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Make the PR review-thread helper usable from every governed repository, including native publish routes, without widening its authority, and remove the drift between ops/autonomy/surface_profile.yaml and the rules and surfaces it governs (findings F1a, F1b, F1c, F2, F3, F4, F5).

### Scope in

- ops/scripts/lib/pr_thread_routes.py ownership gate
- ops/scripts/pr_threads.py wiring of the gate
- ops/scripts/tests/test_pr_threads.py
- ops/autonomy/surface_profile.yaml (forbid, review_activity, post_push, github_rest, updated)
- environment/agents/adapters/claude-code/settings.template.json allow list
- .claude/settings.json regenerated from the template
- environment/agents/adapters/claude-code/hooks/bootstrap_capability_preflight.sh comment and line citing the profile key
- tests/adapters/claude_code/test_capability_friction_contract.py
- skills/l9-pr-remediation/references/review-replies.md consumer-repo invocation

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | S1: with no .l9/pr/pr-summary.json, pr_threads.py writes only when a live REST proof shows the PR is open, its head repo is origin, its head ref is the checkout branch, and its head SHA is an ancestor of or equal to local HEAD; every failed or unreadable fact refuses before any POST (proved by V1) | `quality_gate` | V1: `.venv/bin/python -m pytest -q ops/scripts/tests/test_pr_threads.py tests/adapters/claude_code/test_capability_friction_contract.py ops/scripts/tests/test_user_scope_settings.py ops/scripts/tests/test_project_llm_rules.py ops/scripts/tests/test_claude_projection.py tests/ops/autonomy/test_publish_authority.py` → PASS including the new ownership and allow-list cases | `true` |
| SP-02 | S2: the receipt path is unchanged: a present receipt still decides ownership exactly as before (proved by V1) | `quality_gate` | V1: `.venv/bin/python -m pytest -q ops/scripts/tests/test_pr_threads.py tests/adapters/claude_code/test_capability_friction_contract.py ops/scripts/tests/test_user_scope_settings.py ops/scripts/tests/test_project_llm_rules.py ops/scripts/tests/test_claude_projection.py tests/ops/autonomy/test_publish_authority.py` → PASS including the new ownership and allow-list cases | `true` |
| SP-03 | S3: settings.template.json and the committed .claude/settings.json allow `Bash(python3 ~/.cursor-governance/ops/scripts/pr_threads.py:*)`, still allow the relative form, and still allow no raw `gh api` POST (proved by V1 and V4) | `quality_gate` | V1: `.venv/bin/python -m pytest -q ops/scripts/tests/test_pr_threads.py tests/adapters/claude_code/test_capability_friction_contract.py ops/scripts/tests/test_user_scope_settings.py ops/scripts/tests/test_project_llm_rules.py ops/scripts/tests/test_claude_projection.py tests/ops/autonomy/test_publish_authority.py` → PASS including the new ownership and allow-list cases; V4: `.venv/bin/python ops/scripts/reconcile_claude_settings.py --root . --skip-user --check` → committed .claude/settings.json matches the template | `true` |
| SP-04 | S4: surface_profile.yaml forbids pull_request_review_approval, declares post_push.pr_watch, names native routes in post_push, carries the Infisical GITHUB_TOKEN pat_ref with bare gh removed, and has a current updated date; the preflight hook cites post_push.pr_watch (proved by V1 and V2) | `quality_gate` | V1: `.venv/bin/python -m pytest -q ops/scripts/tests/test_pr_threads.py tests/adapters/claude_code/test_capability_friction_contract.py ops/scripts/tests/test_user_scope_settings.py ops/scripts/tests/test_project_llm_rules.py ops/scripts/tests/test_claude_projection.py tests/ops/autonomy/test_publish_authority.py` → PASS including the new ownership and allow-list cases; V2: `.venv/bin/python ops/scripts/validate_autonomy_contracts.py` → RESULT: PASS | `true` |
| SP-05 | S5: autonomy contracts, Claude settings projection and the Claude adapter validators pass on the changed tree (proved by V2, V3, V4 and V6) | `quality_gate` | V2: `.venv/bin/python ops/scripts/validate_autonomy_contracts.py` → RESULT: PASS; V3: `.venv/bin/python environment/agents/adapters/claude-code/validate_claude_env.py` → no FAIL lines for permissions or profile; V4: `.venv/bin/python ops/scripts/reconcile_claude_settings.py --root . --skip-user --check` → committed .claude/settings.json matches the template; V6: `.venv/bin/python ops/scripts/project_llm_rules.py --root . --check` → generated rule projection is current (profile prose blocks unchanged) | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1` |
| source_ref | `plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `bind worktree /home/user/cg-surface-profile on branch agent/claude/surface-profile-friction at origin/main 1d79d50e, created by ops/scripts/agent_worktree_start.sh` | HEAD equals 1d79d50e and the tracked tree is clean | `true` |
| P1 | pre-validation (status `passed`) | `.venv/bin/python -m pytest -q ops/scripts/tests/test_pr_threads.py tests/adapters/claude_code/test_capability_friction_contract.py ops/scripts/tests/test_user_scope_settings.py ops/scripts/tests/test_project_llm_rules.py ops/scripts/tests/test_claude_projection.py tests/ops/autonomy/test_publish_authority.py` | baseline green before edits | `true` |
| P2 | pre-validation (status `passed`) | `hook catalog for code in scope: .pre-commit-config.yaml; publication gate: make pr` | named | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `ops/scripts/lib/pr_thread_routes.py`, `ops/scripts/pr_threads.py`, `ops/scripts/tests/test_pr_threads.py`, `ops/autonomy/surface_profile.yaml`, `environment/agents/adapters/claude-code/settings.template.json`, `.claude/settings.json`, `environment/agents/adapters/claude-code/hooks/bootstrap_capability_preflight.sh`, `tests/adapters/claude_code/test_capability_friction_contract.py`, `skills/l9-pr-remediation/references/review-replies.md`, `docs/plans/surface_profile_friction_7c3e9a14.json`, `docs/plans/surface_profile_friction_7c3e9a14.plan.md`, `docs/plans/surface_profile_friction_7c3e9a14.gar-decision.json`, `docs/plans/surface_profile_friction_7c3e9a14.gar-run.json`, `docs/plans/surface_profile_friction_7c3e9a14.section-receipt.json`, `environment/generated/llm-rules/MANIFEST.json`
- **write_deny:** `AGENTS.md`, `Makefile`, `Repo.mk`, `CANONICAL_LAW.md`, `ops/scripts/open_pr_after_gate.sh`, `ops/scripts/run_native_publish.sh`, `ops/config/publish-authority.json`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `V1`, `V2`, `V3`, `V4`, `V5`, `V6`, `.venv/bin/python -m pytest -q ops/scripts/tests/test_pr_threads.py tests/adapters/claude_code/test_capability_friction_contract.py ops/scripts/tests/test_user_scope_settings.py ops/scripts/tests/test_project_llm_rules.py ops/scripts/tests/test_claude_projection.py tests/ops/autonomy/test_publish_authority.py`, `.venv/bin/python ops/scripts/validate_autonomy_contracts.py`, `.venv/bin/python environment/agents/adapters/claude-code/validate_claude_env.py`, `.venv/bin/python ops/scripts/reconcile_claude_settings.py --root . --skip-user --check`, `pre-commit run --files <changed files> (hook catalog .pre-commit-config.yaml), run inside make pr's gate`, `.venv/bin/python ops/scripts/project_llm_rules.py --root . --check`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | `api.github.com via gh api (REST, repository-scoped)` |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- make pr is the only publication path
- the helper writes only reply, resolve and issue comment; no merge, approve, unresolve or GraphQL
- raw gh api POST stays off the allow list
- a present pr-summary receipt decides ownership exactly as before
- merge authority and the forbid list only tighten

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/scripts/lib/pr_thread_routes.py` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/scripts/pr_threads.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/scripts/tests/test_pr_threads.py` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- environment/agents/adapters/claude-code/settings.template.json ops/autonomy/surface_profile.yaml .claude/settings.json` | `false` |
| T5 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- skills/l9-pr-remediation/references/review-replies.md` | `false` |
| T6 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/autonomy/surface_profile.yaml` | `false` |
| T7 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- environment/agents/adapters/claude-code/hooks/bootstrap_capability_preflight.sh tests/adapters/claude_code/test_capability_friction_contract.py` | `false` |
| T8 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- environment/generated/llm-rules/MANIFEST.json` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `ops/scripts/lib` | `ops` | `make pr is the only publication path`, `the helper writes only reply, resolve and issue comment; no merge, approve, unresolve or GraphQL`, `raw gh api POST stays off the allow list`, `a present pr-summary receipt decides ownership exactly as before`, `merge authority and the forbid list only tighten` | `AGENTS.md`, `Makefile`, `Repo.mk`, `CANONICAL_LAW.md`, `ops/scripts/open_pr_after_gate.sh`, `ops/scripts/run_native_publish.sh`, `ops/config/publish-authority.json` |
| T2 | `ops/scripts` | `ops` | `make pr is the only publication path`, `the helper writes only reply, resolve and issue comment; no merge, approve, unresolve or GraphQL`, `raw gh api POST stays off the allow list`, `a present pr-summary receipt decides ownership exactly as before`, `merge authority and the forbid list only tighten` | `AGENTS.md`, `Makefile`, `Repo.mk`, `CANONICAL_LAW.md`, `ops/scripts/open_pr_after_gate.sh`, `ops/scripts/run_native_publish.sh`, `ops/config/publish-authority.json` |
| T3 | `ops/scripts/tests` | `assurance` | `make pr is the only publication path`, `the helper writes only reply, resolve and issue comment; no merge, approve, unresolve or GraphQL`, `raw gh api POST stays off the allow list`, `a present pr-summary receipt decides ownership exactly as before`, `merge authority and the forbid list only tighten` | `AGENTS.md`, `Makefile`, `Repo.mk`, `CANONICAL_LAW.md`, `ops/scripts/open_pr_after_gate.sh`, `ops/scripts/run_native_publish.sh`, `ops/config/publish-authority.json` |
| T4 | `repository root` | `policy` | `make pr is the only publication path`, `the helper writes only reply, resolve and issue comment; no merge, approve, unresolve or GraphQL`, `raw gh api POST stays off the allow list`, `a present pr-summary receipt decides ownership exactly as before`, `merge authority and the forbid list only tighten` | `AGENTS.md`, `Makefile`, `Repo.mk`, `CANONICAL_LAW.md`, `ops/scripts/open_pr_after_gate.sh`, `ops/scripts/run_native_publish.sh`, `ops/config/publish-authority.json` |
| T5 | `skills/l9-pr-remediation/references` | `docs` | `make pr is the only publication path`, `the helper writes only reply, resolve and issue comment; no merge, approve, unresolve or GraphQL`, `raw gh api POST stays off the allow list`, `a present pr-summary receipt decides ownership exactly as before`, `merge authority and the forbid list only tighten` | `AGENTS.md`, `Makefile`, `Repo.mk`, `CANONICAL_LAW.md`, `ops/scripts/open_pr_after_gate.sh`, `ops/scripts/run_native_publish.sh`, `ops/config/publish-authority.json` |
| T6 | `ops/autonomy` | `policy` | `make pr is the only publication path`, `the helper writes only reply, resolve and issue comment; no merge, approve, unresolve or GraphQL`, `raw gh api POST stays off the allow list`, `a present pr-summary receipt decides ownership exactly as before`, `merge authority and the forbid list only tighten` | `AGENTS.md`, `Makefile`, `Repo.mk`, `CANONICAL_LAW.md`, `ops/scripts/open_pr_after_gate.sh`, `ops/scripts/run_native_publish.sh`, `ops/config/publish-authority.json` |
| T7 | `repository root` | `assurance` | `make pr is the only publication path`, `the helper writes only reply, resolve and issue comment; no merge, approve, unresolve or GraphQL`, `raw gh api POST stays off the allow list`, `a present pr-summary receipt decides ownership exactly as before`, `merge authority and the forbid list only tighten` | `AGENTS.md`, `Makefile`, `Repo.mk`, `CANONICAL_LAW.md`, `ops/scripts/open_pr_after_gate.sh`, `ops/scripts/run_native_publish.sh`, `ops/config/publish-authority.json` |
| T8 | `environment/generated/llm-rules` | `ops` | `make pr is the only publication path`, `the helper writes only reply, resolve and issue comment; no merge, approve, unresolve or GraphQL`, `raw gh api POST stays off the allow list`, `a present pr-summary receipt decides ownership exactly as before`, `merge authority and the forbid list only tighten` | `AGENTS.md`, `Makefile`, `Repo.mk`, `CANONICAL_LAW.md`, `ops/scripts/open_pr_after_gate.sh`, `ops/scripts/run_native_publish.sh`, `ops/config/publish-authority.json` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1` |
| source_execution_ref | `plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (V1 passes) → stop and repair the ownership gate before profile edits; C2 fails (V2, V3 and V4 pass) → repair the projection or profile before make pr |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | revert the PR; the receipt-only gate and relative allow rule return |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `V1`
- re-run `V2`
- re-run `V3`
- re-run `V4`
- re-run `V5`
- re-run `V6`
- re-run `.venv/bin/python -m pytest -q ops/scripts/tests/test_pr_threads.py tests/adapters/claude_code/test_capability_friction_contract.py ops/scripts/tests/test_user_scope_settings.py ops/scripts/tests/test_project_llm_rules.py ops/scripts/tests/test_claude_projection.py tests/ops/autonomy/test_publish_authority.py`
- re-run `.venv/bin/python ops/scripts/validate_autonomy_contracts.py`
- re-run `.venv/bin/python environment/agents/adapters/claude-code/validate_claude_env.py`
- re-run `.venv/bin/python ops/scripts/reconcile_claude_settings.py --root . --skip-user --check`
- re-run `pre-commit run --files <changed files> (hook catalog .pre-commit-config.yaml), run inside make pr's gate`
- re-run `.venv/bin/python ops/scripts/project_llm_rules.py --root . --check`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` — highest todo risk across 8 todo(s) |
| uncertainty | `medium` — 1 unknown(s), 0 blocking |
| blast_radius | `medium` — review-thread writes from Claude Code sessions in every governed repository; no merge, approve or push path changes |
| architectural_boundaries_crossed | `consumer repository checkout to Cursor-Governance helper` |
| external_systems_touched | `GitHub REST API` |
| migration_required | `false` |
| unknown_dependency_count | `1` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | In ops/scripts/lib/pr_thread_routes.py keep load_summary and the receipt branch of require_own_pr unchanged. When the receipt file is absent, prove ownership live: GET repos/{origin}/pulls/{n} through the injectable run (`gh api --method GET`), require state open, head.repo.full_name equal to origin (case-insensitive), head.ref equal to the checkout branch from `git rev-parse --abbrev-ref HEAD` (detached HEAD refuses), and `git merge-base --is-ancestor <head.sha> HEAD` exit 0. Any unreadable fact, non-JSON or failed command refuses through fail(). require_own_pr takes run as a keyword argument. A null head.repo (deleted fork) refuses. A head SHA absent from the local object store makes merge-base exit non-zero and refuses; nothing is fetched to make it pass. Update the module docstring to name the home-relative allowlisted form. | Cursor Build agent | `medium` | S | `[]` | `ops/scripts/lib/pr_thread_routes.py` |
| T2 | In ops/scripts/pr_threads.py pass run into require_own_pr so tests and the live call share one transport. Update the module docstring: ownership is the pr-summary receipt when present, otherwise the live head-branch proof. | Cursor Build agent | `low` | S | `[T1]` | `ops/scripts/pr_threads.py` |
| T3 | Extend ops/scripts/tests/test_pr_threads.py: a tmp git repository on branch feat/x whose HEAD is the PR head writes after the live proof (GET then POST); each of closed PR, foreign head repo, other head ref, head SHA not an ancestor of HEAD, detached HEAD and GET failure refuses with no POST; a head SHA behind HEAD (unpushed local fix) is accepted. test_missing_receipt_refuses keeps its intent as no write outside a git checkout and asserts no POST rather than no call. Add an assertion that the template allows the home-relative helper form. The fixture is a real repository from git init -b feat/x with one commit; a null head.repo case refuses with no POST. | Cursor Build agent | `low` | M | `[T1, T2, T4]` | `ops/scripts/tests/test_pr_threads.py` |
| T4 | Add `Bash(python3 ~/.cursor-governance/ops/scripts/pr_threads.py:*)` to permissions.allow in environment/agents/adapters/claude-code/settings.template.json beside the two relative forms; add the same string to surface_profile.yaml review_activity.allow_prefixes; regenerate the committed .claude/settings.json with `reconcile_claude_settings.py --root . --skip-user`. | Cursor Build agent | `medium` | S | `[]` | `environment/agents/adapters/claude-code/settings.template.json`, `ops/autonomy/surface_profile.yaml`, `.claude/settings.json` |
| T5 | In skills/l9-pr-remediation/references/review-replies.md name the consumer-repository form `python3 ~/.cursor-governance/ops/scripts/pr_threads.py ...` and the live ownership proof used when no pr-summary receipt exists. | Cursor Build agent | `low` | S | `[T1, T4]` | `skills/l9-pr-remediation/references/review-replies.md` |
| T6 | surface_profile.yaml: add pull_request_review_approval to forbid; add post_push.pr_watch: subscribe_pr_activity_events_only with a comment naming the Send Later ban; set post_push.required_command comment and add post_push.native_routes: ops/config/publish-authority.json; set pr_stacking.github_rest.pat_ref to GITHUB_TOKEN with a legacy-alias comment and drop bare gh from sanctioned_routes; set updated to 2026-11-12. Update review_activity: keep receipt, add ownership_fallback describing the live proof so the profile matches pr_thread_routes.require_own_pr. | Cursor Build agent | `low` | S | `[]` | `ops/autonomy/surface_profile.yaml` |
| T7 | bootstrap_capability_preflight.sh: make the Send Later line and its header comment cite surface_profile post_push.pr_watch; tests/adapters/claude_code/test_capability_friction_contract.py asserts the profile key value and the citation. | Cursor Build agent | `low` | S | `[T6]` | `environment/agents/adapters/claude-code/hooks/bootstrap_capability_preflight.sh`, `tests/adapters/claude_code/test_capability_friction_contract.py` |
| T8 | Regenerate environment/generated/llm-rules/MANIFEST.json with .venv/bin/python ops/scripts/project_llm_rules.py --root . : the manifest records source_sha256 of the whole surface_profile.yaml, so any profile edit changes it. Never hand-edit the generated tree. | Cursor Build agent | `low` | S | `[T4, T6]` | `environment/generated/llm-rules/MANIFEST.json` |

**Critical path:** T1 → T2 → T4 → T3

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | the helper proves ownership on a native route and is reachable from a consumer checkout | profile hygiene and docs |
| M2 | profile, hook and adapter agree | publication |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | V1 passes | stop and repair the ownership gate before profile edits |
| C2 | M2 | V2, V3 and V4 pass | repair the projection or profile before make pr |

### Leverage

- **Ranked todos:** `T1`, `T2`, `T4`, `T3`, `T6`, `T5`, `T7`, `T8`
- **Shared causes:** ownership proven only from a receipt the native route never writes; allow rule only matches inside the governance clone; profile prose drifted from rule 62 and the REST-only rule
- **Deletions / consolidations:** bare gh removed from github_rest.sanctioned_routes; approval denial consolidated into forbid

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `n_a` | — | no operating instruction names the review-thread helper or the profile keys changed; root file is append-only |
| CANONICAL_LAW.md | `n_a` | — | no law changes; approval was already forbidden in the remediation note and merge authority is untouched |
| skills/l9-pr-remediation/references/review-replies.md | `update` | `T5` | names the consumer-repo invocation (T5) |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01, SP-02, SP-03, SP-04 | `quality_gate_evidence` | command | `.venv/bin/python -m pytest -q ops/scripts/tests/test_pr_threads.py tests/adapters/claude_code/test_capability_friction_contract.py ops/scripts/tests/test_user_scope_settings.py ops/scripts/tests/test_project_llm_rules.py ops/scripts/tests/test_claude_projection.py tests/ops/autonomy/test_publish_authority.py` | PASS including the new ownership and allow-list cases | `not_run` |
| E-V2 | SP-04, SP-05 | `quality_gate_evidence` | command | `.venv/bin/python ops/scripts/validate_autonomy_contracts.py` | RESULT: PASS | `not_run` |
| E-V3 | SP-05 | `quality_gate_evidence` | command | `.venv/bin/python environment/agents/adapters/claude-code/validate_claude_env.py` | no FAIL lines for permissions or profile | `not_run` |
| E-V4 | SP-03, SP-05 | `quality_gate_evidence` | command | `.venv/bin/python ops/scripts/reconcile_claude_settings.py --root . --skip-user --check` | committed .claude/settings.json matches the template | `not_run` |
| E-V5 | regression gate (no SP) | `quality_gate_evidence` | command | `pre-commit run --files <changed files> (hook catalog .pre-commit-config.yaml), run inside make pr's gate` | every configured hook passes on the changed files | `not_run` |
| E-V6 | SP-05 | `quality_gate_evidence` | command | `.venv/bin/python ops/scripts/project_llm_rules.py --root . --check` | generated rule projection is current (profile prose blocks unchanged) | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Can the live proof accept a PR this checkout did not publish?
- Does a home-relative allow rule widen what runs without a prompt beyond the helper?
- Does the fallback change behaviour for a checkout that has a receipt?
- Does Claude Code match the literal `~` text, or expand it before matching?

### Assumption failure conditions

- another agent's branch with the same name and an ancestor head could pass - accepted: the same branch name in the same origin at an ancestor head is the published work this checkout carries, and the write set is still reply/resolve/comment only
- if `~` is not matched literally the rule simply does not match and the call prompts or is classified as before - no authority is gained

### Blast radius notes

- review-thread writes from Claude Code sessions in every governed repository; no merge, approve or push path changes

### Rollback constraints

- revert the PR; the receipt-only gate and relative allow rule return

### Risks

| risk | mitigation |
|------|------------|
| the live proof's extra GET is refused by the session gateway | it is a repository-scoped REST GET, already allowed as `gh api --method GET`; a refusal fails closed with the gh error |
| regenerating .claude/settings.json pulls unrelated template drift into the diff | inspect the regenerated diff and keep only the allow-list change; stop if other keys move |

## Out of scope

- P7 SonarCloud silent skip (lives in cryptoxdog/IB-Odoo_19; operator restricted writes to Cursor-Governance)
- P3 Copilot quota and P6 publish-ceremony repetition (repository settings and publish flow, not this profile)
- user-scope ~/.claude/settings.json (reconciled by SessionStart after merge, not by this change)
- open_pr_after_gate.sh and run_native_publish.sh (receipt writers stay as they are)
- AGENTS.md, Makefile, Repo.mk, CANONICAL_LAW.md (root files, append-only)
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1` |
| source_ref | `plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1` |
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

- **required_evidence_refs:** E-V1, E-V2, E-V3, E-V4, E-V5, E-V6
- **observed_evidence_refs:** none
- **missing_evidence:** E-V1, E-V2, E-V3, E-V4, E-V5, E-V6

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `unknown` | U1 | Does a Claude Code allow rule containing `~` approve the matching command text without a prompt at runtime? — if not, F1b stays open on consumer repos and needs the dispatcher route instead | `accept_bounded` |
| `open_blocker` | stop_reason | plan validated; Build not yet run | planning convergence `partial` |

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
  plan_id: "plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1"
  name: "Close surface-profile friction: review threads on native routes and profile drift"
  overview: "Make the PR review-thread helper usable from every governed repository, including native publish routes, without widening its authority, and remove the drift between ops/autonomy/surface_profile.yaml and the rules and surfaces it governs (findings F1a, F1b, F1c, F2, F3, F4, F5)."
  status: "draft"
  is_project: false
  owner: "igor_beylin"
architect_framing:
  planning_ssot: "PLAN_DOCUMENT"
  plan_class: "bounded_execution_contract"
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: "Quantum-L9/Cursor-Governance"
  commit_sha: "1d79d50e028935961dd631990a030ba1f22f7afc"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Make the PR review-thread helper usable from every governed repository, including native publish routes, without widening its authority, and remove the drift between ops/autonomy/surface_profile.yaml and the rules and surfaces it governs (findings F1a, F1b, F1c, F2, F3, F4, F5)."
  success_properties:
    - id: "SP-01"
      property: "S1: with no .l9/pr/pr-summary.json, pr_threads.py writes only when a live REST proof shows the PR is open, its head repo is origin, its head ref is the checkout branch, and its head SHA is an ancestor of or equal to local HEAD; every failed or unreadable fact refuses before any POST (proved by V1)"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "S2: the receipt path is unchanged: a present receipt still decides ownership exactly as before (proved by V1)"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-03"
      property: "S3: settings.template.json and the committed .claude/settings.json allow `Bash(python3 ~/.cursor-governance/ops/scripts/pr_threads.py:*)`, still allow the relative form, and still allow no raw `gh api` POST (proved by V1 and V4)"
      evidence_type: "quality_gate"
      proof: ["V1", "V4"]
      blocking: true
    - id: "SP-04"
      property: "S4: surface_profile.yaml forbids pull_request_review_approval, declares post_push.pr_watch, names native routes in post_push, carries the Infisical GITHUB_TOKEN pat_ref with bare gh removed, and has a current updated date; the preflight hook cites post_push.pr_watch (proved by V1 and V2)"
      evidence_type: "quality_gate"
      proof: ["V1", "V2"]
      blocking: true
    - id: "SP-05"
      property: "S5: autonomy contracts, Claude settings projection and the Claude adapter validators pass on the changed tree (proved by V2, V3, V4 and V6)"
      evidence_type: "quality_gate"
      proof: ["V2", "V3", "V4", "V6"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1"
execution_envelope:
  filesystem:
    write_allow: ["ops/scripts/lib/pr_thread_routes.py", "ops/scripts/pr_threads.py", "ops/scripts/tests/test_pr_threads.py", "ops/autonomy/surface_profile.yaml", "environment/agents/adapters/claude-code/settings.template.json", ".claude/settings.json", "environment/agents/adapters/claude-code/hooks/bootstrap_capability_preflight.sh", "tests/adapters/claude_code/test_capability_friction_contract.py", "skills/l9-pr-remediation/references/review-replies.md", "docs/plans/surface_profile_friction_7c3e9a14.json", "docs/plans/surface_profile_friction_7c3e9a14.plan.md", "docs/plans/surface_profile_friction_7c3e9a14.gar-decision.json", "docs/plans/surface_profile_friction_7c3e9a14.gar-run.json", "docs/plans/surface_profile_friction_7c3e9a14.section-receipt.json", "environment/generated/llm-rules/MANIFEST.json"]
    write_deny: ["AGENTS.md", "Makefile", "Repo.mk", "CANONICAL_LAW.md", "ops/scripts/open_pr_after_gate.sh", "ops/scripts/run_native_publish.sh", "ops/config/publish-authority.json"]
  commands:
    allow: ["V1", "V2", "V3", "V4", "V5", "V6", ".venv/bin/python -m pytest -q ops/scripts/tests/test_pr_threads.py tests/adapters/claude_code/test_capability_friction_contract.py ops/scripts/tests/test_user_scope_settings.py ops/scripts/tests/test_project_llm_rules.py ops/scripts/tests/test_claude_projection.py tests/ops/autonomy/test_publish_authority.py", ".venv/bin/python ops/scripts/validate_autonomy_contracts.py", ".venv/bin/python environment/agents/adapters/claude-code/validate_claude_env.py", ".venv/bin/python ops/scripts/reconcile_claude_settings.py --root . --skip-user --check", "pre-commit run --files <changed files> (hook catalog .pre-commit-config.yaml), run inside make pr's gate", ".venv/bin/python ops/scripts/project_llm_rules.py --root . --check"]
  network:
    mode: "named_services_only"
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
rollback_contract_ref: "rollback.plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1"
dependency_topology_ref: "dag.plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4", "E-V5", "E-V6"]
stress_and_disconfirm:
  disconfirming_cases: ["Can the live proof accept a PR this checkout did not publish?", "Does a home-relative allow rule widen what runs without a prompt beyond the helper?", "Does the fallback change behaviour for a checkout that has a receipt?", "Does Claude Code match the literal `~` text, or expand it before matching?"]
  assumption_failure_conditions: ["another agent's branch with the same name and an ancestor head could pass - accepted: the same branch name in the same origin at an ancestor head is the published work this checkout carries, and the write set is still reply/resolve/comment only", "if `~` is not matched literally the rule simply does not match and the call prompts or is classified as before - no authority is gained"]
out_of_scope: ["P7 SonarCloud silent skip (lives in cryptoxdog/IB-Odoo_19; operator restricted writes to Cursor-Governance)", "P3 Copilot quota and P6 publish-ceremony repetition (repository settings and publish flow, not this profile)", "user-scope ~/.claude/settings.json (reconciled by SessionStart after merge, not by this change)", "open_pr_after_gate.sh and run_native_publish.sh (receipt writers stay as they are)", "AGENTS.md, Makefile, Repo.mk, CANONICAL_LAW.md (root files, append-only)"]
convergence_contract_ref: "conv.plan.simple.close_surface_profile_friction_review_threads_on_native_routes_and_profile_drift.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "In ops/scripts/lib/pr_thread_routes.py keep load_summary and the receipt branch of require_own_pr unchanged. When the receipt file is absent, prove ownership live: GET repos/{origin}/pulls/{n} through the injectable run (`gh api --method GET`), require state open, head.repo.full_name equal to origin (case-insensitive), head.ref equal to the checkout branch from `git rev-parse --abbrev-ref HEAD` (detached HEAD refuses), and `git merge-base --is-ancestor <head.sha> HEAD` exit 0. Any unreadable fact, non-JSON or failed command refuses through fail(). require_own_pr takes run as a keyword argument. A null head.repo (deleted fork) refuses. A head SHA absent from the local object store makes merge-base exit non-zero and refuses; nothing is fetched to make it pass. Update the module docstring to name the home-relative allowlisted form."
    status: "pending"
  - id: "T2"
    content: "In ops/scripts/pr_threads.py pass run into require_own_pr so tests and the live call share one transport. Update the module docstring: ownership is the pr-summary receipt when present, otherwise the live head-branch proof."
    status: "pending"
  - id: "T3"
    content: "Extend ops/scripts/tests/test_pr_threads.py: a tmp git repository on branch feat/x whose HEAD is the PR head writes after the live proof (GET then POST); each of closed PR, foreign head repo, other head ref, head SHA not an ancestor of HEAD, detached HEAD and GET failure refuses with no POST; a head SHA behind HEAD (unpushed local fix) is accepted. test_missing_receipt_refuses keeps its intent as no write outside a git checkout and asserts no POST rather than no call. Add an assertion that the template allows the home-relative helper form. The fixture is a real repository from git init -b feat/x with one commit; a null head.repo case refuses with no POST."
    status: "pending"
  - id: "T4"
    content: "Add `Bash(python3 ~/.cursor-governance/ops/scripts/pr_threads.py:*)` to permissions.allow in environment/agents/adapters/claude-code/settings.template.json beside the two relative forms; add the same string to surface_profile.yaml review_activity.allow_prefixes; regenerate the committed .claude/settings.json with `reconcile_claude_settings.py --root . --skip-user`."
    status: "pending"
  - id: "T5"
    content: "In skills/l9-pr-remediation/references/review-replies.md name the consumer-repository form `python3 ~/.cursor-governance/ops/scripts/pr_threads.py ...` and the live ownership proof used when no pr-summary receipt exists."
    status: "pending"
  - id: "T6"
    content: "surface_profile.yaml: add pull_request_review_approval to forbid; add post_push.pr_watch: subscribe_pr_activity_events_only with a comment naming the Send Later ban; set post_push.required_command comment and add post_push.native_routes: ops/config/publish-authority.json; set pr_stacking.github_rest.pat_ref to GITHUB_TOKEN with a legacy-alias comment and drop bare gh from sanctioned_routes; set updated to 2026-11-12. Update review_activity: keep receipt, add ownership_fallback describing the live proof so the profile matches pr_thread_routes.require_own_pr."
    status: "pending"
  - id: "T7"
    content: "bootstrap_capability_preflight.sh: make the Send Later line and its header comment cite surface_profile post_push.pr_watch; tests/adapters/claude_code/test_capability_friction_contract.py asserts the profile key value and the citation."
    status: "pending"
  - id: "T8"
    content: "Regenerate environment/generated/llm-rules/MANIFEST.json with .venv/bin/python ops/scripts/project_llm_rules.py --root . : the manifest records source_sha256 of the whole surface_profile.yaml, so any profile edit changes it. Never hand-edit the generated tree."
    status: "pending"
```
