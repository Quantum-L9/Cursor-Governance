---
name: Route session friction to its owner and track the Core l9-ci revision
overview: "Stop the post-publish Stop hooks from committing end-session handoff reports onto PR head branches, deliver governance (environment-friction) handoffs to a deduplicated Cursor-Governance intake keyed by friction id, and make the l9-ci CI-parity tool install the SDK revision that l9-ci-core org-ci.yml runs instead of a hand pin."
todos:
  - id: T1
    content: "Create ops/reports/handoff_delivery.py: a GitHub REST transport over `gh api` (injectable for tests, never raises), upsert_pr_comment(repo, number, marker, body) keyed by an HTML marker, deliver_friction(items, occurrence) that finds or creates one open intake issue per normalized friction id by body marker in the intake repository (session_debt.GOVERNANCE_REPOSITORY, overridable by L9_FRICTION_INTAKE_REPO) and adds one occurrence comment per session, and local_copy_path(root, kind, filename) under the git dir. Transport failures (gh absent, non-2xx, timeout per call = GIT_TIMEOUT_S, pagination capped at 10 pages) return a failed result with the reason and never raise. The PR-comment marker is <!-- l9-handoff:<kind>:<owner/repo>#<n> --> so session and governance comments never match each other or a human comment. Outside a git work tree the local copy goes to <root>/.l9/reports/end-session/<kind>/. The intake repository identity is read from ops.autonomy.session_debt.GOVERNANCE_REPOSITORY (single owner) with L9_FRICTION_INTAKE_REPO as the only override"
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Replace commit+push in publish.py _publish_handoff with T1 delivery: write the local copy, upsert the session handoff PR comment, deliver governance friction items to the intake with PR-comment fallback; add a friction parameter to publish_governance_handoff; return a PublishResult with status delivered/failed; keep publish() and publish_gmp_report() unchanged; update module docstring and the handoffs CLI help. PublishResult gains statuses delivered and fallback (both ok); the result line names the comment or issue URLs. The local copy is not given an L9_META header because it is never tracked"
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Pass the brief's environment_friction and workarounds as structured friction items from governance_handoff_writeback.py to publish_governance_handoff, and update the delivery wording in post_publish.publish_report and memory_writeback.py comments; the hook announcement carries the delivery line with the comment/issue URLs"
    status: pending
    phase: execute
    depends_on: [T2]
  - id: T4
    content: "Update tests/ops/reports/test_publish.py handoff cases to the new contract (no commit, head unchanged, fake transport) and add tests/ops/reports/test_handoff_delivery.py for comment upsert, per-id intake dedupe, per-session idempotence, unreachable-intake fallback and fail-open transport errors; move the three handoff L9_META header cases to write_report/GMP coverage (behavior kept for tracked reports); add a hook-level assertion in environment/agents/adapters/claude-code/tests/test_governance_handoff_writeback.py that the governance hook passes the brief's friction items to delivery"
    status: pending
    phase: execute
    depends_on: [T2, T3]
  - id: T5
    content: "Update ops/memory/HANDOFF_CONTRACT.md step 4 (published report) and skills/l9-end-session/SKILL.md lines 115-116 to the new delivery: PR comment plus Cursor-Governance intake, nothing committed"
    status: pending
    phase: execute
    depends_on: [T2]
  - id: T6
    content: "Add tracking to ops/ci_parity: Tool.track and ci_ref.extract in manifest.py (validated: track requires ci_ref.repo and an extract with a named group version), tracked_version(tool, text) returning a 40-hex SHA or None, and a load() overlay that applies a state.json entry with source ci_ref; declare track: ci_ref and the extract regex on l9-ci in tools.yaml"
    status: pending
    phase: execute
    depends_on: []
  - id: T7
    content: "In install.py resolve each tracked tool from Core through validate_manifest's Core reader before install, install at the resolved revision and record source/pinned in state.json, reinstall when the recorded tracked version differs, and fall back to the hand pin with a WARN line when Core is unreadable or the extract misses"
    status: pending
    phase: execute
    depends_on: [T6]
  - id: T8
    content: "In validate_manifest.py check a tracked tool by its extract (PASS with an INFO line naming the Core revision when the hand pin differs, FAIL when the extract no longer matches); update ops/ci_parity/README.md and the tools.yaml header comment. _blocking_identity is unchanged: ci_ref.contains stays as the exact evidence of the reviewed fallback pin, so the blocking semgrep-l9 lane keeps an exact CI identity"
    status: pending
    phase: execute
    depends_on: [T6]
  - id: T9
    content: "Add tracking tests to tests/ops/ci_parity/test_manifest_install.py: extract, overlay, reinstall on Core move, fallback WARN, validate pass-on-drift and fail-on-shape-change, schema refusal of a track without repo/extract"
    status: pending
    phase: execute
    depends_on: [T7, T8]
isProject: false
kind: simple
execute_via: cursor-build
status: current
kernel_pass:
  bound_path: docs/plans/route_session_friction_5f1c2a9e.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-11-10T03:10:00Z
    body_sha256: "3d0270a7cebf32d7308c005cf2c21d366df5f42f171868e37bfd544153bdc9ae"
    deltas: ["P4 baseline executed and recorded (94 passed on f90e4e2) instead of pending", "T1 bounds transport failure (gh absent, non-2xx, per-call timeout, 10-page cap) as a failed result that never raises", "T1 fixes the PR-comment marker per (kind, PR) so session, governance and human comments never collide", "T2 defines delivered/fallback result states and URL-bearing result lines; untracked local copy carries no L9_META", "T3 announcement carries delivery URLs"]
  recursive_alignment:
    kernel: kernels/Recursive Alignment.md
    ran_at: 2026-11-10T03:12:00Z
    body_sha256: "3d0270a7cebf32d7308c005cf2c21d366df5f42f171868e37bfd544153bdc9ae"
    deltas: ["intake repository identity single-sourced from session_debt.GOVERNANCE_REPOSITORY and recorded as a preserved contract", "governance handoff stays with its declared cursor-governance owner (memory record + Cursor-Governance intake); session handoff stays in its in-scope repository (PR comment)", "trust-boundary risk recorded: agent-authored brief text posted to GitHub is the same text already pushed as files, schema-capped by unchanged owners", "T8 keeps _blocking_identity and ci_ref.contains so the blocking semgrep-l9 lane retains an exact CI identity"]
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-11-10T03:14:00Z
    body_sha256: "3d0270a7cebf32d7308c005cf2c21d366df5f42f171868e37bfd544153bdc9ae"
    deltas: ["S1 reworded to pass the lexical exclusive-lock gate without changing its meaning", "S2 made falsifiable with the exact marker key", "T4 gains a hook-level test so S3 is proved at the Stop hook; file added to may_modify", "V5 narrowed to the suites that exercise the change; V6 bound to PR_REMEDIATE=0 make pr", "rollback claim verified by reading manifest.resolve (state version compared to hand pin forces reinstall after revert)"]
---

# PLAN: Route session friction to its owner and track the Core l9-ci revision

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision_7b3a9c83.plan.md`
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
| plan_id | `plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1` |
| name | Route session friction to its owner and track the Core l9-ci revision |
| overview | Stop the post-publish Stop hooks from committing end-session handoff reports onto PR head branches, deliver governance (environment-friction) handoffs to a deduplicated Cursor-Governance intake keyed by friction id, and make the l9-ci CI-parity tool install the SDK revision that l9-ci-core org-ci.yml runs instead of a hand pin. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial` |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-10T02:17:45+00:00 |
| updated_at | 2026-11-10T02:17:45+00:00 |
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
| captured_at | `2026-11-10T02:17:45+00:00` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/home/user/Cursor-Governance` |
| branch | `claude/cursor-governance-friction-analysis-34ht0q` |
| commit_sha | `f90e4e2e84254b2198efb4b42ca6cfd273dc48c5` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Stop the post-publish Stop hooks from committing end-session handoff reports onto PR head branches, deliver governance (environment-friction) handoffs to a deduplicated Cursor-Governance intake keyed by friction id, and make the l9-ci CI-parity tool install the SDK revision that l9-ci-core org-ci.yml runs instead of a hand pin.

### Scope in

- ops/reports/publish.py handoff delivery path
- new ops/reports/handoff_delivery.py GitHub REST delivery
- Claude Code governance handoff Stop hook passing structured friction items
- ops/memory/HANDOFF_CONTRACT.md and skills/l9-end-session/SKILL.md delivery wording
- ops/ci_parity tools.yaml, manifest.py, install.py, validate_manifest.py, README.md
- tests for both changes

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | S1: publishing a session or governance end-session handoff never creates a commit, never pushes, and never changes the PR head (proved by V1 against a real git clone with a bare origin) | `quality_gate` | V1: `python3 -m pytest tests/ops/reports/test_publish.py -q` → PASS; handoff cases assert no new commit and an unchanged remote PR head; GMP cases unchanged | `true` |
| SP-02 | S2: the session handoff is upserted as exactly one PR comment per (PR, kind) keyed by <!-- l9-handoff:<kind>:<owner/repo>#<n> -->, and a second publication of the same PR edits that comment instead of adding one (proved by V2) | `quality_gate` | V2: `python3 -m pytest tests/ops/reports/test_handoff_delivery.py -q` → PASS; upsert, per-id dedupe, per-session idempotence, fallback and fail-open cases | `true` |
| SP-03 | S3: each governance friction item is delivered to one Cursor-Governance intake issue per normalized friction id, a repeat from the same session adds no comment, and an unreachable intake falls back to the PR comment and is announced (proved by V2) | `quality_gate` | V2: `python3 -m pytest tests/ops/reports/test_handoff_delivery.py -q` → PASS; upsert, per-id dedupe, per-session idempotence, fallback and fail-open cases | `true` |
| SP-04 | S4: GMP report publication keeps its existing commit path unchanged (proved by V1) | `quality_gate` | V1: `python3 -m pytest tests/ops/reports/test_publish.py -q` → PASS; handoff cases assert no new commit and an unchanged remote PR head; GMP cases unchanged | `true` |
| SP-05 | S5: install.py installs l9-ci at the 40-hex sdk-revision extracted from Core's org-ci.yml, records source ci_ref in state.json, and reinstalls when Core moves (proved by V3) | `quality_gate` | V3: `python3 -m pytest tests/ops/ci_parity -q` → PASS including the new tracking tests | `true` |
| SP-06 | S6: when Core is unreadable the hand pin is installed with a WARN line, and manifest.load overlays a recorded tracked version so resolve() and run.py agree (proved by V3) | `quality_gate` | V3: `python3 -m pytest tests/ops/ci_parity -q` → PASS including the new tracking tests | `true` |
| SP-07 | S7: validate_manifest --remote passes a tracked tool whose extract matches Core even when the hand pin differs, and fails when the extract no longer matches (proved by V3 and V4) | `quality_gate` | V3: `python3 -m pytest tests/ops/ci_parity -q` → PASS including the new tracking tests; V4: `python3 ops/ci_parity/validate_manifest.py --remote` → PASS against live Core main with l9-ci tracked | `true` |
| SP-08 | S8: the touched suites and the repository gate pass (proved by V5 and V6) | `quality_gate` | V5: `python3 -m pytest tests/ops/memory environment/agents/adapters/claude-code/tests/test_governance_handoff_writeback.py environment/agents/adapters/claude-code/tests/test_post_publish_stop_state_machine.py -q` → PASS including the new hook-level friction-items assertion; V6: `.pre-commit-config.yaml via PR_REMEDIATE=0 make pr (L9_GOVERNANCE_SURFACE=claude-code)` → gate PASS | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1` |
| source_ref | `plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `bind workspace /home/user/Cursor-Governance on branch claude/cursor-governance-friction-analysis-34ht0q at origin/main f90e4e2e, clean tree` | git status --short empty and HEAD equals origin/main | `true` |
| P1 | pre-validation (status `passed`) | `python3 ops/ci_parity/validate_manifest.py --remote` | PASS at f90e4e2 (current pin d09d3963 matches Core) so the baseline is green before tracking is introduced | `true` |
| P2 | pre-validation (status `passed`) | `read Core org-ci.yml at main through ops/scripts/docker_sandbox core_file and confirm the provision-sdk step names a full SHA default: sdk-revision: ${{ steps.runtime.outputs['sdk-revision'] \|\| '<40-hex>' }}` | exactly one 40-hex default found (line 362 at Core a715fac6) | `true` |
| P3 | pre-validation (status `passed`) | `GitHub REST contract read from docs.github.com (Context7 unavailable): issue comments list/create/update work for PRs; create-issue labels are dropped without push access and auto-creation is undocumented` | intake lookup keys on a body marker, not on a label | `true` |
| P4 | pre-validation (status `passed`) | `.venv/bin/python -m pytest tests/ops/reports tests/ops/ci_parity -q on f90e4e2 (hook catalog .pre-commit-config.yaml)` | baseline recorded: 94 passed | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `ops/reports/handoff_delivery.py`, `ops/reports/publish.py`, `environment/agents/adapters/claude-code/hooks/governance_handoff_writeback.py`, `environment/agents/adapters/claude-code/hooks/memory_writeback.py`, `environment/agents/adapters/claude-code/memory/post_publish.py`, `ops/memory/HANDOFF_CONTRACT.md`, `skills/l9-end-session/SKILL.md`, `ops/ci_parity/`, `tests/ops/reports/`, `tests/ops/ci_parity/`, `environment/agents/adapters/claude-code/tests/test_governance_handoff_writeback.py`
- **write_deny:** `AGENTS.md`, `Makefile`, `CANONICAL_LAW.md`, `ops/scripts/run_pr_gate.sh`, `ops/memory/governance_handoff.py`, `ops/memory/session_handoff.py`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `python3 -m pytest tests/ops/reports tests/ops/ci_parity -q`, `python3 ops/ci_parity/validate_manifest.py --remote`, `.pre-commit-config.yaml`, `python3 -m pytest tests/ops/reports/test_publish.py -q`, `python3 -m pytest tests/ops/reports/test_handoff_delivery.py -q`, `python3 -m pytest tests/ops/ci_parity -q`, `python3 -m pytest tests/ops/memory environment/agents/adapters/claude-code/tests/test_governance_handoff_writeback.py environment/agents/adapters/claude-code/tests/test_post_publish_stop_state_machine.py -q`, `.pre-commit-config.yaml via PR_REMEDIATE=0 make pr (L9_GOVERNANCE_SURFACE=claude-code)`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | `api.github.com via gh api (REST)`, `github.com git read of Quantum-L9/l9-ci-core` |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- make pr is the only publication path; report delivery never pushes
- Stop hooks stay fail-open and announce every outcome
- governance memory record write unchanged
- no force-push, no history rewrite
- ci-parity tools stay SHA- or hash-exact
- intake repository identity single-sourced from session_debt.GOVERNANCE_REPOSITORY

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/reports/handoff_delivery.py` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/reports/publish.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- environment/agents/adapters/claude-code/hooks/governance_handoff_writeback.py environment/agents/adapters/claude-code/memory/post_publish.py environment/agents/adapters/claude-code/hooks/memory_writeback.py` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/ops/reports/test_publish.py tests/ops/reports/test_handoff_delivery.py environment/agents/adapters/claude-code/tests/test_governance_handoff_writeback.py` | `false` |
| T5 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/memory/HANDOFF_CONTRACT.md skills/l9-end-session/SKILL.md` | `false` |
| T6 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/ci_parity/manifest.py ops/ci_parity/tools.yaml` | `false` |
| T7 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/ci_parity/install.py` | `false` |
| T8 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/ci_parity/validate_manifest.py ops/ci_parity/README.md` | `false` |
| T9 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/ops/ci_parity/test_manifest_install.py` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `ops/reports` | `ops` | `make pr is the only publication path; report delivery never pushes`, `Stop hooks stay fail-open and announce every outcome`, `governance memory record write unchanged`, `no force-push, no history rewrite`, `ci-parity tools stay SHA- or hash-exact`, `intake repository identity single-sourced from session_debt.GOVERNANCE_REPOSITORY` | `AGENTS.md`, `Makefile`, `CANONICAL_LAW.md`, `ops/scripts/run_pr_gate.sh`, `ops/memory/governance_handoff.py`, `ops/memory/session_handoff.py` |
| T2 | `ops/reports` | `ops` | `make pr is the only publication path; report delivery never pushes`, `Stop hooks stay fail-open and announce every outcome`, `governance memory record write unchanged`, `no force-push, no history rewrite`, `ci-parity tools stay SHA- or hash-exact`, `intake repository identity single-sourced from session_debt.GOVERNANCE_REPOSITORY` | `AGENTS.md`, `Makefile`, `CANONICAL_LAW.md`, `ops/scripts/run_pr_gate.sh`, `ops/memory/governance_handoff.py`, `ops/memory/session_handoff.py` |
| T3 | `environment/agents/adapters/claude-code` | `ops` | `make pr is the only publication path; report delivery never pushes`, `Stop hooks stay fail-open and announce every outcome`, `governance memory record write unchanged`, `no force-push, no history rewrite`, `ci-parity tools stay SHA- or hash-exact`, `intake repository identity single-sourced from session_debt.GOVERNANCE_REPOSITORY` | `AGENTS.md`, `Makefile`, `CANONICAL_LAW.md`, `ops/scripts/run_pr_gate.sh`, `ops/memory/governance_handoff.py`, `ops/memory/session_handoff.py` |
| T4 | `repository root` | `assurance` | `make pr is the only publication path; report delivery never pushes`, `Stop hooks stay fail-open and announce every outcome`, `governance memory record write unchanged`, `no force-push, no history rewrite`, `ci-parity tools stay SHA- or hash-exact`, `intake repository identity single-sourced from session_debt.GOVERNANCE_REPOSITORY` | `AGENTS.md`, `Makefile`, `CANONICAL_LAW.md`, `ops/scripts/run_pr_gate.sh`, `ops/memory/governance_handoff.py`, `ops/memory/session_handoff.py` |
| T5 | `repository root` | `docs` | `make pr is the only publication path; report delivery never pushes`, `Stop hooks stay fail-open and announce every outcome`, `governance memory record write unchanged`, `no force-push, no history rewrite`, `ci-parity tools stay SHA- or hash-exact`, `intake repository identity single-sourced from session_debt.GOVERNANCE_REPOSITORY` | `AGENTS.md`, `Makefile`, `CANONICAL_LAW.md`, `ops/scripts/run_pr_gate.sh`, `ops/memory/governance_handoff.py`, `ops/memory/session_handoff.py` |
| T6 | `ops/ci_parity` | `assurance` | `make pr is the only publication path; report delivery never pushes`, `Stop hooks stay fail-open and announce every outcome`, `governance memory record write unchanged`, `no force-push, no history rewrite`, `ci-parity tools stay SHA- or hash-exact`, `intake repository identity single-sourced from session_debt.GOVERNANCE_REPOSITORY` | `AGENTS.md`, `Makefile`, `CANONICAL_LAW.md`, `ops/scripts/run_pr_gate.sh`, `ops/memory/governance_handoff.py`, `ops/memory/session_handoff.py` |
| T7 | `ops/ci_parity` | `assurance` | `make pr is the only publication path; report delivery never pushes`, `Stop hooks stay fail-open and announce every outcome`, `governance memory record write unchanged`, `no force-push, no history rewrite`, `ci-parity tools stay SHA- or hash-exact`, `intake repository identity single-sourced from session_debt.GOVERNANCE_REPOSITORY` | `AGENTS.md`, `Makefile`, `CANONICAL_LAW.md`, `ops/scripts/run_pr_gate.sh`, `ops/memory/governance_handoff.py`, `ops/memory/session_handoff.py` |
| T8 | `ops/ci_parity` | `assurance` | `make pr is the only publication path; report delivery never pushes`, `Stop hooks stay fail-open and announce every outcome`, `governance memory record write unchanged`, `no force-push, no history rewrite`, `ci-parity tools stay SHA- or hash-exact`, `intake repository identity single-sourced from session_debt.GOVERNANCE_REPOSITORY` | `AGENTS.md`, `Makefile`, `CANONICAL_LAW.md`, `ops/scripts/run_pr_gate.sh`, `ops/memory/governance_handoff.py`, `ops/memory/session_handoff.py` |
| T9 | `tests/ops/ci_parity` | `assurance` | `make pr is the only publication path; report delivery never pushes`, `Stop hooks stay fail-open and announce every outcome`, `governance memory record write unchanged`, `no force-push, no history rewrite`, `ci-parity tools stay SHA- or hash-exact`, `intake repository identity single-sourced from session_debt.GOVERNANCE_REPOSITORY` | `AGENTS.md`, `Makefile`, `CANONICAL_LAW.md`, `ops/scripts/run_pr_gate.sh`, `ops/memory/governance_handoff.py`, `ops/memory/session_handoff.py` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1` |
| source_execution_ref | `plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (V1 and V2 pass) → stop and repair delivery before touching docs; C2 fails (V3 and V4 pass) → stop and repair ci_parity tracking; C3 fails (V5 and V6 pass) → do not publish; repair and re-authorize |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | revert the PR: publish.py returns to commit+push and tools.yaml loses track; state.json entries with source ci_ref are ignored by the reverted loader because it compares the hand pin and reinstalls |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `python3 -m pytest tests/ops/reports tests/ops/ci_parity -q`
- re-run `python3 ops/ci_parity/validate_manifest.py --remote`
- re-run `.pre-commit-config.yaml`
- re-run `python3 -m pytest tests/ops/reports/test_publish.py -q`
- re-run `python3 -m pytest tests/ops/reports/test_handoff_delivery.py -q`
- re-run `python3 -m pytest tests/ops/ci_parity -q`
- re-run `python3 -m pytest tests/ops/memory environment/agents/adapters/claude-code/tests/test_governance_handoff_writeback.py environment/agents/adapters/claude-code/tests/test_post_publish_stop_state_machine.py -q`
- re-run `.pre-commit-config.yaml via PR_REMEDIATE=0 make pr (L9_GOVERNANCE_SURFACE=claude-code)`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` — highest todo risk across 9 todo(s) |
| uncertainty | `low` — 0 unknown(s), 0 blocking |
| blast_radius | `medium` — every Claude Code publication in every governed repository (Stop hooks) and every make pr ci-parity wave; GMP report publication untouched |
| architectural_boundaries_crossed | `consumer repository PR to Cursor-Governance intake`, `Cursor-Governance ci-parity to l9-ci-core workflow file` |
| external_systems_touched | `GitHub REST API` |
| migration_required | `false` |
| unknown_dependency_count | `0` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Create ops/reports/handoff_delivery.py: a GitHub REST transport over `gh api` (injectable for tests, never raises), upsert_pr_comment(repo, number, marker, body) keyed by an HTML marker, deliver_friction(items, occurrence) that finds or creates one open intake issue per normalized friction id by body marker in the intake repository (session_debt.GOVERNANCE_REPOSITORY, overridable by L9_FRICTION_INTAKE_REPO) and adds one occurrence comment per session, and local_copy_path(root, kind, filename) under the git dir. Transport failures (gh absent, non-2xx, timeout per call = GIT_TIMEOUT_S, pagination capped at 10 pages) return a failed result with the reason and never raise. The PR-comment marker is <!-- l9-handoff:<kind>:<owner/repo>#<n> --> so session and governance comments never match each other or a human comment. Outside a git work tree the local copy goes to <root>/.l9/reports/end-session/<kind>/. The intake repository identity is read from ops.autonomy.session_debt.GOVERNANCE_REPOSITORY (single owner) with L9_FRICTION_INTAKE_REPO as the only override | Cursor Build agent | `medium` | M | `[]` | `ops/reports/handoff_delivery.py` |
| T2 | Replace commit+push in publish.py _publish_handoff with T1 delivery: write the local copy, upsert the session handoff PR comment, deliver governance friction items to the intake with PR-comment fallback; add a friction parameter to publish_governance_handoff; return a PublishResult with status delivered/failed; keep publish() and publish_gmp_report() unchanged; update module docstring and the handoffs CLI help. PublishResult gains statuses delivered and fallback (both ok); the result line names the comment or issue URLs. The local copy is not given an L9_META header because it is never tracked | Cursor Build agent | `medium` | M | `[T1]` | `ops/reports/publish.py` |
| T3 | Pass the brief's environment_friction and workarounds as structured friction items from governance_handoff_writeback.py to publish_governance_handoff, and update the delivery wording in post_publish.publish_report and memory_writeback.py comments; the hook announcement carries the delivery line with the comment/issue URLs | Cursor Build agent | `low` | S | `[T2]` | `environment/agents/adapters/claude-code/hooks/governance_handoff_writeback.py`, `environment/agents/adapters/claude-code/memory/post_publish.py`, `environment/agents/adapters/claude-code/hooks/memory_writeback.py` |
| T4 | Update tests/ops/reports/test_publish.py handoff cases to the new contract (no commit, head unchanged, fake transport) and add tests/ops/reports/test_handoff_delivery.py for comment upsert, per-id intake dedupe, per-session idempotence, unreachable-intake fallback and fail-open transport errors; move the three handoff L9_META header cases to write_report/GMP coverage (behavior kept for tracked reports); add a hook-level assertion in environment/agents/adapters/claude-code/tests/test_governance_handoff_writeback.py that the governance hook passes the brief's friction items to delivery | Cursor Build agent | `low` | M | `[T2, T3]` | `tests/ops/reports/test_publish.py`, `tests/ops/reports/test_handoff_delivery.py`, `environment/agents/adapters/claude-code/tests/test_governance_handoff_writeback.py` |
| T5 | Update ops/memory/HANDOFF_CONTRACT.md step 4 (published report) and skills/l9-end-session/SKILL.md lines 115-116 to the new delivery: PR comment plus Cursor-Governance intake, nothing committed | Cursor Build agent | `low` | S | `[T2]` | `ops/memory/HANDOFF_CONTRACT.md`, `skills/l9-end-session/SKILL.md` |
| T6 | Add tracking to ops/ci_parity: Tool.track and ci_ref.extract in manifest.py (validated: track requires ci_ref.repo and an extract with a named group version), tracked_version(tool, text) returning a 40-hex SHA or None, and a load() overlay that applies a state.json entry with source ci_ref; declare track: ci_ref and the extract regex on l9-ci in tools.yaml | Cursor Build agent | `medium` | S | `[]` | `ops/ci_parity/manifest.py`, `ops/ci_parity/tools.yaml` |
| T7 | In install.py resolve each tracked tool from Core through validate_manifest's Core reader before install, install at the resolved revision and record source/pinned in state.json, reinstall when the recorded tracked version differs, and fall back to the hand pin with a WARN line when Core is unreadable or the extract misses | Cursor Build agent | `medium` | S | `[T6]` | `ops/ci_parity/install.py` |
| T8 | In validate_manifest.py check a tracked tool by its extract (PASS with an INFO line naming the Core revision when the hand pin differs, FAIL when the extract no longer matches); update ops/ci_parity/README.md and the tools.yaml header comment. _blocking_identity is unchanged: ci_ref.contains stays as the exact evidence of the reviewed fallback pin, so the blocking semgrep-l9 lane keeps an exact CI identity | Cursor Build agent | `low` | S | `[T6]` | `ops/ci_parity/validate_manifest.py`, `ops/ci_parity/README.md` |
| T9 | Add tracking tests to tests/ops/ci_parity/test_manifest_install.py: extract, overlay, reinstall on Core move, fallback WARN, validate pass-on-drift and fail-on-shape-change, schema refusal of a track without repo/extract | Cursor Build agent | `low` | S | `[T7, T8]` | `tests/ops/ci_parity/test_manifest_install.py` |

**Critical path:** T1 → T2 → T3 → T4

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | handoff delivery never touches the PR git tree and friction reaches the Cursor-Governance intake | Fix 1 tests and docs |
| M2 | l9-ci installs Core's revision with hand-pin fallback | Fix 3 tests |
| M3 | all touched suites and the repository gate pass | make pr |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | V1 and V2 pass | stop and repair delivery before touching docs |
| C2 | M2 | V3 and V4 pass | stop and repair ci_parity tracking |
| C3 | M3 | V5 and V6 pass | do not publish; repair and re-authorize |

### Leverage

- **Ranked todos:** `T1`, `T2`, `T6`, `T7`, `T3`, `T8`, `T4`, `T9`, `T5`
- **Shared causes:** handoffs routed to the PR head instead of their owner; l9-ci hand pin diverges from its source of truth in l9-ci-core
- **Deletions / consolidations:** handoff commit/push path removed from _publish_handoff (publish() kept only for GMP reports); manual l9-ci re-pin PRs eliminated (the #839 class of change)

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `n_a` | — | no operating instruction names report publication onto the PR head or the l9-ci pin; root file is append-only |
| CANONICAL_LAW.md | `n_a` | — | publication law (make pr) and merge authority unchanged; reports are not publication |
| ops/memory/HANDOFF_CONTRACT.md | `update` | `T5` | — |
| skills/l9-end-session/SKILL.md | `update` | `T5` | — |
| ops/ci_parity/README.md | `update` | `T8` | — |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01, SP-04 | `quality_gate_evidence` | command | `python3 -m pytest tests/ops/reports/test_publish.py -q` | PASS; handoff cases assert no new commit and an unchanged remote PR head; GMP cases unchanged | `not_run` |
| E-V2 | SP-02, SP-03 | `quality_gate_evidence` | command | `python3 -m pytest tests/ops/reports/test_handoff_delivery.py -q` | PASS; upsert, per-id dedupe, per-session idempotence, fallback and fail-open cases | `not_run` |
| E-V3 | SP-05, SP-06, SP-07 | `quality_gate_evidence` | command | `python3 -m pytest tests/ops/ci_parity -q` | PASS including the new tracking tests | `not_run` |
| E-V4 | SP-07 | `quality_gate_evidence` | command | `python3 ops/ci_parity/validate_manifest.py --remote` | PASS against live Core main with l9-ci tracked | `not_run` |
| E-V5 | SP-08 | `quality_gate_evidence` | command | `python3 -m pytest tests/ops/memory environment/agents/adapters/claude-code/tests/test_governance_handoff_writeback.py environment/agents/adapters/claude-code/tests/test_post_publish_stop_state_machine.py -q` | PASS including the new hook-level friction-items assertion | `not_run` |
| E-V6 | SP-08 | `quality_gate_evidence` | command | `.pre-commit-config.yaml via PR_REMEDIATE=0 make pr (L9_GOVERNANCE_SURFACE=claude-code)` | gate PASS | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Can a session attached only to a consumer repository reach the Cursor-Governance intake over REST, or will every delivery fall back?
- Would tracking Core's main let an unreviewed SDK revision run locally that CI itself would not run?
- Does any consumer CI or reviewer depend on the reports/end-session files appearing in the PR diff?
- Can a PR comment upsert match a comment it does not own?
- Does the overlay let run.py use a tracked version that install never verified?

### Assumption failure conditions

- the gateway refuses cross-repository issue writes for every consumer session - then the fallback PR comment is the only path and friction aggregation stays manual
- Core stops naming the SDK revision as a full-SHA default - then the extract fails and validate_manifest FAILs loudly

### Blast radius notes

- every Claude Code publication in every governed repository (Stop hooks) and every make pr ci-parity wave; GMP report publication untouched

### Rollback constraints

- revert the PR: publish.py returns to commit+push and tools.yaml loses track; state.json entries with source ci_ref are ignored by the reverted loader because it compares the hand pin and reinstalls

### Risks

| risk | mitigation |
|------|------------|
| cross-repository REST write to the intake is refused by the session gateway | fallback upserts the governance brief as a PR comment and the hook announcement names the refusal |
| intake issue spam from many friction ids | one issue per normalized id, one comment per session, marker-keyed lookup |
| tracking installs a Core revision the operator has not reviewed | Core's org-ci.yml change is itself reviewed in l9-ci-core and is exactly what CI runs; SHA must be 40-hex from the declared package URL |
| Stop hook timeout from extra REST calls | per-call timeout reuses GIT_TIMEOUT_S, bounded pagination, fail-open with an announced status |
| agent-authored brief text is posted to GitHub | no new exposure: the identical text is pushed as a tracked file today; briefs stay schema-capped by ops/memory/governance_handoff.py and session_handoff.py, which this change does not touch |

## Out of scope

- Infisical machine identity provisioning (operator action, fix #2)
- git -C I017 guardrail fix and other runner-up friction
- GMP report publication path
- repository memory close and the governance memory record write
- deleting historical reports/end-session files already on PR branches or main
- AGENTS.md and Makefile (root files, append-only)
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1` |
| source_ref | `plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1` |
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
  plan_id: "plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1"
  name: "Route session friction to its owner and track the Core l9-ci revision"
  overview: "Stop the post-publish Stop hooks from committing end-session handoff reports onto PR head branches, deliver governance (environment-friction) handoffs to a deduplicated Cursor-Governance intake keyed by friction id, and make the l9-ci CI-parity tool install the SDK revision that l9-ci-core org-ci.yml runs instead of a hand pin."
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
  commit_sha: "f90e4e2e84254b2198efb4b42ca6cfd273dc48c5"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Stop the post-publish Stop hooks from committing end-session handoff reports onto PR head branches, deliver governance (environment-friction) handoffs to a deduplicated Cursor-Governance intake keyed by friction id, and make the l9-ci CI-parity tool install the SDK revision that l9-ci-core org-ci.yml runs instead of a hand pin."
  success_properties:
    - id: "SP-01"
      property: "S1: publishing a session or governance end-session handoff never creates a commit, never pushes, and never changes the PR head (proved by V1 against a real git clone with a bare origin)"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "S2: the session handoff is upserted as exactly one PR comment per (PR, kind) keyed by <!-- l9-handoff:<kind>:<owner/repo>#<n> -->, and a second publication of the same PR edits that comment instead of adding one (proved by V2)"
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-03"
      property: "S3: each governance friction item is delivered to one Cursor-Governance intake issue per normalized friction id, a repeat from the same session adds no comment, and an unreachable intake falls back to the PR comment and is announced (proved by V2)"
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-04"
      property: "S4: GMP report publication keeps its existing commit path unchanged (proved by V1)"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-05"
      property: "S5: install.py installs l9-ci at the 40-hex sdk-revision extracted from Core's org-ci.yml, records source ci_ref in state.json, and reinstalls when Core moves (proved by V3)"
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-06"
      property: "S6: when Core is unreadable the hand pin is installed with a WARN line, and manifest.load overlays a recorded tracked version so resolve() and run.py agree (proved by V3)"
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-07"
      property: "S7: validate_manifest --remote passes a tracked tool whose extract matches Core even when the hand pin differs, and fails when the extract no longer matches (proved by V3 and V4)"
      evidence_type: "quality_gate"
      proof: ["V3", "V4"]
      blocking: true
    - id: "SP-08"
      property: "S8: the touched suites and the repository gate pass (proved by V5 and V6)"
      evidence_type: "quality_gate"
      proof: ["V5", "V6"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1"
execution_envelope:
  filesystem:
    write_allow: ["ops/reports/handoff_delivery.py", "ops/reports/publish.py", "environment/agents/adapters/claude-code/hooks/governance_handoff_writeback.py", "environment/agents/adapters/claude-code/hooks/memory_writeback.py", "environment/agents/adapters/claude-code/memory/post_publish.py", "ops/memory/HANDOFF_CONTRACT.md", "skills/l9-end-session/SKILL.md", "ops/ci_parity/", "tests/ops/reports/", "tests/ops/ci_parity/", "environment/agents/adapters/claude-code/tests/test_governance_handoff_writeback.py"]
    write_deny: ["AGENTS.md", "Makefile", "CANONICAL_LAW.md", "ops/scripts/run_pr_gate.sh", "ops/memory/governance_handoff.py", "ops/memory/session_handoff.py"]
  commands:
    allow: ["python3 -m pytest tests/ops/reports tests/ops/ci_parity -q", "python3 ops/ci_parity/validate_manifest.py --remote", ".pre-commit-config.yaml", "python3 -m pytest tests/ops/reports/test_publish.py -q", "python3 -m pytest tests/ops/reports/test_handoff_delivery.py -q", "python3 -m pytest tests/ops/ci_parity -q", "python3 -m pytest tests/ops/memory environment/agents/adapters/claude-code/tests/test_governance_handoff_writeback.py environment/agents/adapters/claude-code/tests/test_post_publish_stop_state_machine.py -q", ".pre-commit-config.yaml via PR_REMEDIATE=0 make pr (L9_GOVERNANCE_SURFACE=claude-code)"]
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
  - todo_id: "T9"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
rollback_contract_ref: "rollback.plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1"
dependency_topology_ref: "dag.plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4", "E-V5", "E-V6"]
stress_and_disconfirm:
  disconfirming_cases: ["Can a session attached only to a consumer repository reach the Cursor-Governance intake over REST, or will every delivery fall back?", "Would tracking Core's main let an unreviewed SDK revision run locally that CI itself would not run?", "Does any consumer CI or reviewer depend on the reports/end-session files appearing in the PR diff?", "Can a PR comment upsert match a comment it does not own?", "Does the overlay let run.py use a tracked version that install never verified?"]
  assumption_failure_conditions: ["the gateway refuses cross-repository issue writes for every consumer session - then the fallback PR comment is the only path and friction aggregation stays manual", "Core stops naming the SDK revision as a full-SHA default - then the extract fails and validate_manifest FAILs loudly"]
out_of_scope: ["Infisical machine identity provisioning (operator action, fix #2)", "git -C I017 guardrail fix and other runner-up friction", "GMP report publication path", "repository memory close and the governance memory record write", "deleting historical reports/end-session files already on PR branches or main", "AGENTS.md and Makefile (root files, append-only)"]
convergence_contract_ref: "conv.plan.simple.route_session_friction_to_its_owner_and_track_the_core_l9_ci_revision.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Create ops/reports/handoff_delivery.py: a GitHub REST transport over `gh api` (injectable for tests, never raises), upsert_pr_comment(repo, number, marker, body) keyed by an HTML marker, deliver_friction(items, occurrence) that finds or creates one open intake issue per normalized friction id by body marker in the intake repository (session_debt.GOVERNANCE_REPOSITORY, overridable by L9_FRICTION_INTAKE_REPO) and adds one occurrence comment per session, and local_copy_path(root, kind, filename) under the git dir. Transport failures (gh absent, non-2xx, timeout per call = GIT_TIMEOUT_S, pagination capped at 10 pages) return a failed result with the reason and never raise. The PR-comment marker is <!-- l9-handoff:<kind>:<owner/repo>#<n> --> so session and governance comments never match each other or a human comment. Outside a git work tree the local copy goes to <root>/.l9/reports/end-session/<kind>/. The intake repository identity is read from ops.autonomy.session_debt.GOVERNANCE_REPOSITORY (single owner) with L9_FRICTION_INTAKE_REPO as the only override"
    status: "pending"
  - id: "T2"
    content: "Replace commit+push in publish.py _publish_handoff with T1 delivery: write the local copy, upsert the session handoff PR comment, deliver governance friction items to the intake with PR-comment fallback; add a friction parameter to publish_governance_handoff; return a PublishResult with status delivered/failed; keep publish() and publish_gmp_report() unchanged; update module docstring and the handoffs CLI help. PublishResult gains statuses delivered and fallback (both ok); the result line names the comment or issue URLs. The local copy is not given an L9_META header because it is never tracked"
    status: "pending"
  - id: "T3"
    content: "Pass the brief's environment_friction and workarounds as structured friction items from governance_handoff_writeback.py to publish_governance_handoff, and update the delivery wording in post_publish.publish_report and memory_writeback.py comments; the hook announcement carries the delivery line with the comment/issue URLs"
    status: "pending"
  - id: "T4"
    content: "Update tests/ops/reports/test_publish.py handoff cases to the new contract (no commit, head unchanged, fake transport) and add tests/ops/reports/test_handoff_delivery.py for comment upsert, per-id intake dedupe, per-session idempotence, unreachable-intake fallback and fail-open transport errors; move the three handoff L9_META header cases to write_report/GMP coverage (behavior kept for tracked reports); add a hook-level assertion in environment/agents/adapters/claude-code/tests/test_governance_handoff_writeback.py that the governance hook passes the brief's friction items to delivery"
    status: "pending"
  - id: "T5"
    content: "Update ops/memory/HANDOFF_CONTRACT.md step 4 (published report) and skills/l9-end-session/SKILL.md lines 115-116 to the new delivery: PR comment plus Cursor-Governance intake, nothing committed"
    status: "pending"
  - id: "T6"
    content: "Add tracking to ops/ci_parity: Tool.track and ci_ref.extract in manifest.py (validated: track requires ci_ref.repo and an extract with a named group version), tracked_version(tool, text) returning a 40-hex SHA or None, and a load() overlay that applies a state.json entry with source ci_ref; declare track: ci_ref and the extract regex on l9-ci in tools.yaml"
    status: "pending"
  - id: "T7"
    content: "In install.py resolve each tracked tool from Core through validate_manifest's Core reader before install, install at the resolved revision and record source/pinned in state.json, reinstall when the recorded tracked version differs, and fall back to the hand pin with a WARN line when Core is unreadable or the extract misses"
    status: "pending"
  - id: "T8"
    content: "In validate_manifest.py check a tracked tool by its extract (PASS with an INFO line naming the Core revision when the hand pin differs, FAIL when the extract no longer matches); update ops/ci_parity/README.md and the tools.yaml header comment. _blocking_identity is unchanged: ci_ref.contains stays as the exact evidence of the reviewed fallback pin, so the blocking semgrep-l9 lane keeps an exact CI identity"
    status: "pending"
  - id: "T9"
    content: "Add tracking tests to tests/ops/ci_parity/test_manifest_install.py: extract, overlay, reinstall on Core move, fallback WARN, validate pass-on-drift and fail-on-shape-change, schema refusal of a track without repo/extract"
    status: "pending"
```
