---
name: Claude Environment pending fixes after p307-r2
overview: "Execute remaining in-repo Claude Code environment-experience repairs on the current checkout via Cursor Build. Land breakglass receipts and honest receipt/deps/memory evidence first. Do not run make campaign, admit a Program Lock, or revive the retired capability broker."
todos:
  - id: T-CI007
    content: "Replace standing L9_PUBLISH_PATH_OVERRIDE session string with a scoped expiring breakglass receipt; report any grant still in force and its age at SessionStart"
    status: pending
    phase: execute
    depends_on: []
  - id: T-CI004
    content: "Re-probe DEGRADED bootstrap components at SessionStart fail-soft under the repo-write lock; attach a reason string and log path per non-READY component; keep revision-mismatch expiry as the stronger binding"
    status: pending
    phase: execute
    depends_on: []
  - id: T-CI012
    content: "Extend rule 22 with the server-absent case and named fallback; annotate projected rules when a capability precondition is unmet"
    status: pending
    phase: execute
    depends_on: []
  - id: T-CI009
    content: "After toolchain_proven, run an import smoke on the resolved interpreter, record path and version, and write exit code plus timestamp into the deps stamp or log final line"
    status: pending
    phase: execute
    depends_on: []
  - id: T-CI006
    content: "Name the file that produced a drifted account-env value; classify authority-widening versus cosmetic drift; record the effective value merge_gate read"
    status: pending
    phase: execute
    depends_on: [T-CI007]
  - id: T-CI102
    content: "Record the REST gh route as a sanctioned surface capability in surface_profile.yaml and rule 62, or keep the openclaw PAT path as the only documented route"
    status: pending
    phase: execute
    depends_on: []
  - id: T-CI005
    content: "Split bootstrap memory into memory.cli and memory.mcp probed independently; count facts that are not self-referential PICKUP restatements; write a task-bearing completion PICKUP at contract end"
    status: pending
    phase: execute
    depends_on: [T-CI004]
  - id: T-CI013
    content: "Name the refused stage of a compound command and state that later stages did not run; allow scratchpad-owned forced removal while refusing repo paths; make documented escapes reachable or delete them from rules 49 and 88"
    status: pending
    phase: execute
    depends_on: []
  - id: T-CI023
    content: "Warn when resolve_governance_paths.sh is sourced without calling an entry point; amend rule 06 to source then resolve_governance_paths_or_exit; load session env in non-interactive shells"
    status: pending
    phase: execute
    depends_on: []
  - id: T-CI016
    content: "Have l4_local status compare the pinned SHA to current head and report STALE as an explicit field a caller can test"
    status: pending
    phase: execute
    depends_on: []
  - id: T-CI015
    content: "When a second governance checkout is present, print both paths with revisions and state which one rules resolve from; assert whether the workspace clone is an intentional consumer checkout or leftover"
    status: pending
    phase: execute
    depends_on: [T-CI007, T-CI023]
  - id: T-CI002
    content: "Relocate L9_AUTONOMY_STATE_DIR outside the worktree in the Claude settings template and account-field docs; keep .l9/autonomy as a gitignored fallback only"
    status: pending
    phase: execute
    depends_on: []
  - id: T-CI019
    content: "Add a bounded fetch/merge --no-edit/regen/re-verify/push retry loop N<=2 on open_pr_after_gate.sh; never rewrite history; leave a CANONICAL_LAW lease protocol out of this plan"
    status: pending
    phase: execute
    depends_on: []
  - id: T-CI021
    content: "Narrow skill-usage logging to namespaces this surface exposes and emit a SessionStart line naming the log path and current entry count"
    status: pending
    phase: execute
    depends_on: []
  - id: T-CI022
    content: "State at SessionStart that service-backed integration tests are unavailable when neo4j is absent or 127.0.0.1:7687 refuses, so the runnable versus unrunnable split is known before a run"
    status: pending
    phase: execute
    depends_on: []
  - id: T-CI008
    content: "Enable the consumer-workspace pre-commit path only after OD-002 decides whether the workspace Makefile or the governance Makefile is publish authority"
    status: pending
    phase: execute
    depends_on: [T-CI007]
isProject: false
kind: simple
execute_via: cursor-build
kernel_pass:
  bound_path: claude_env_pending_fixes_049c5300.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: "2026-08-29T15:31:00-10:00"
    deltas:
      - Dropped CI-010 and broker identity work because CAPABILITY_BROKER_RETIRED_V1 is live
      - Collapsed CI-009 and CI-028 into one deps-evidence todo after toolchain_proven landed
      - Removed the invalidated is_tracked-on-four-writers slice and consumer gitignore copies
      - Kept revision-mismatch expiry as already landed; scoped T-CI004 to re-probe plus per-component reason
  recursive_alignment:
    kernel: kernels/Recursive Alignment.md
    ran_at: "2026-08-29T15:32:00-10:00"
    deltas:
      - Authority remains CANONICAL_LAW then surface_profile then AGENTS.md; pack text cannot revive the broker
      - T-CI008 stays blocked on OD-002 rather than encoding workspace-Makefile-first
      - Execute path is Cursor Build plus PR_STACK=auto PR_REMEDIATE=0 make pr; no Program Lock
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: "2026-08-29T15:33:00-10:00"
    body_sha256: "ba7b8962a848bbbedd5ce04f3f345a0b3cde679511d3efa95c2c7d85c311d810"
    deltas:
      - stress_test is an object matching the PLAN_DOCUMENT schema
      - Archived corpus paths updated after the folder move
      - T-CI008 files point at the archived OPEN_DECISIONS.yaml
---

# PLAN: Claude Environment pending fixes after p307-r2

> **Projected from** `WIP/8-26-26-Claude Environment/PLAN_DOCUMENT.claude-env-pending-fixes.v1.json` (`validate_plan_document.py` PASS).
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** Cursor Build on the unique open-PR chain tip. Do not run `make campaign`.
> **Suggested filename:** `claude_env_pending_fixes_049c5300.plan.md`

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

This checkout is currently `main` at `197563297c600233b4def75f12baf7d87a1885bd` with multiple sibling open PRs (393–403). Build therefore **fails closed** on a unique-tip resolve unless the operator names one parent chain. Do not invent an `origin/main` fork.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.claude-env.pending-fixes.v1` |
| name | Claude Environment pending fixes after p307-r2 |
| schema_version | `1.0.0` |
| status | `draft` |
| is_project | `false` |
| owner | igor_beylin |
| created_at | `2026-08-29` |
| updated_at | `2026-08-29` |
| execute_via | `cursor-build` |
| remaining_work_ssot | `WIP/8-26-26-Claude Environment/PLAN_DOCUMENT.claude-env-pending-fixes.v1.json` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | `WIP/8-26-26-Claude Environment/PLAN_DOCUMENT.claude-env-pending-fixes.v1.json` (live). Archived r2 pack is provenance only. |
| plan_class | `remediation_plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Cursor Build only. No PE overlay, no broker revival, no campaign packet. |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-08-29T15:30:00-10:00` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/Users/ib-mac/Cursor-Governance` |
| ssot_clone | `$HOME/.cursor-governance` |
| branch | `main` (planning checkout; Build must not stay here if a unique chain tip exists) |
| commit_sha | `197563297c600233b4def75f12baf7d87a1885bd` |
| dirty | `true` (WIP remaining-work JSON + archive move; pathspec only) |
| artifact_hashes | `{ "WIP/8-26-26-Claude Environment/PLAN_DOCUMENT.claude-env-pending-fixes.v1.json": "live" }` |
| allowed_local_dirt | `WIP/8-26-26-Claude Environment/**`, `docs/plans/claude_env_pending_fixes_049c5300.plan.md` |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | Record HEAD and continue on this checkout; do not stop-and-replan as a Program Lock |

This SHA is a workspace snapshot, not `Lock: origin/main = <sha>`.

## Objective

### Mission

Close the remaining in-repo Claude Code environment-experience defects after the p307-r2 assessment and PR#360 wave. The live queue is sixteen todos. Coarse READY/DEGRADED and a standing publish-breakglass string are the shared roots. Harness-owned, other-repo, and broker-revival work stay archived.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Breakglass is a receipt; env string alone does not widen publish | `runtime_behavior` | SessionStart names grant age when a receipt is in force; gate ignores bare `L9_PUBLISH_PATH_OVERRIDE` | true |
| SP-02 | DEGRADED components have reason + log path; SessionStart re-probes fail-soft | `proof_receipt` | `python3 ops/scripts/claude_bootstrap_receipt.py --json` | true |
| SP-03 | Deps proven pass records import smoke, interpreter path/version, exit code | `filesystem` | stamp or log final line after `session_deps_cloud.sh` | true |
| SP-04 | Rule 22 is closable when Context7 is absent | `structural` | rule text + `project_llm_rules.py` annotation | true |
| SP-05 | memory.cli and memory.mcp are independent; PICKUP-only hydrate is empty | `proof_receipt` | bootstrap receipt + hydrate stats | true |
| SP-06 | Quality gate on changed files | `quality_gate` | `.pre-commit-config.yaml` catalog via `PR_STACK=auto PR_REMEDIATE=0 make pr` | true |

## Capability preflight

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.claude-env.pending-fixes.v1` |
| source_ref | `plan.claude-env.pending-fixes.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| baseline_verified | `true` (planning) |
| drift_detected | `false` at plan emit |

### Probes

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | workspace identity | `git rev-parse HEAD && git branch --show-current` | HEAD recorded; no origin/main lock written | true |
| CP-02 | remaining-work SSOT | `test -f WIP/8-26-26-Claude Environment/PLAN_DOCUMENT.claude-env-pending-fixes.v1.json` | file present; sources under `_archive` | true |
| CP-03 | depth router | `python3 skills/l9-plan/scripts/route_plan.py --risk high --evidence partial --json` | `depth=deep`; `omit_gates=[]` | true |
| CP-04 | revision-expiry already landed | `claude_bootstrap_receipt.py` compare recorded vs live revision | mismatch yields `unknown`, not stale DEGRADED-as-current | true |
| CP-05 | broker retired | `AGENTS.md` `CAPABILITY_BROKER_RETIRED_V1` | no todo diagnoses broker.quantumaipartners.com | true |

## Execution envelope

### Filesystem

- **write_allow:** `ops/autonomy/`, `ops/scripts/claude_bootstrap_receipt.py`, `ops/scripts/project_llm_rules.py`, `ops/scripts/resolve_governance_paths.sh`, `ops/scripts/open_pr_after_gate.sh`, `ops/graphiti/hydration/`, `environment/agents/adapters/claude-code/`, `rules/22-context7-auto-invoke.mdc`, `rules/06-governance-ssot-paths.mdc`, `rules/62-github-openclaw-authority.mdc`, `rules/49-shared-worktree-isolation.mdc`, `rules/88-l4-local-autonomy.mdc`, `docs/account-fields/ENVIRONMENT_VARIABLES.md`, `WIP/8-26-26-Claude Environment/PLAN_DOCUMENT.claude-env-pending-fixes.v1.json`, matching tests under `tests/` and `environment/agents/adapters/claude-code/tests/`
- **write_deny:** `CANONICAL_LAW.md`, `AGENTS.md`, `Makefile`, `WIP/8-26-26-Claude Environment/_archive/`, `environment/program-execution/core/shared/AUTHORIZATION_MODEL.yaml`, `environment/program-execution/core/shared/EVIDENCE_MODEL.yaml`, `ops/secrets/_archived/capability-broker/`
- **delete_allow:** none

### Commands

- **allow:** scoped git commit, `l4_local.py authorize-release`, `PR_STACK=auto PR_REMEDIATE=0 make pr`, targeted pytest on touched files, receipt CLIs
- **deny:** `make campaign`, `pec.py` bootstrap/claim/render, force-push, hard-reset, admin-merge, `make push`, MCP `create_pull_request` / `push_files`

### Network

| Field | Value |
|-------|-------|
| mode | `existing_tunnel_only` |
| allowed_services | Graphiti tunnel `127.0.0.1:8100`; `gh` via already-resolved PAT |

### Secrets

No new secrets. Do not paste tokens to "fix" a retired broker. T-CI102 documents the existing REST `gh api` route; it does not provision a second PAT.

### Merge

`autonomous_merge: false`. This plan does not merge.

## Side effects + idempotency

| todo | side effect | idempotent |
|------|-------------|------------|
| T-CI007 | New breakglass receipt schema under `~/.l9/` or `.l9/autonomy/` | Yes: second run refuses a standing env string and reads the same receipt |
| T-CI004 | SessionStart may rewrite bootstrap-state.json after re-probe | Yes: revision+TTL evaluate is already idempotent |
| T-CI009 | Non-empty deps stamp/log | Yes: proven repos stay cached |
| T-CI005 | Hydrate receipt fields change | Yes: split keys overwrite the collapsed `memory` word |
| T-CI002 | Settings template default for `L9_AUTONOMY_STATE_DIR` | Yes: rewrite the same key; do not delete the old on-disk receipt in the same commit |
| T-CI019 | Extra fetch/merge attempts on PR open | Yes: N<=2 then fail closed |
| T-CI008 | none until OD-002 | Blocker holds the todo |

## Architecture impact

No new module. Shared autonomy brain stays in `ops/autonomy/`. Claude adapter remains a wrapper. Receipt evaluation stays in `claude_bootstrap_receipt.py`. Memory transports stay Graphiti CLI + MCP; this plan splits the **report**, it does not add a second store.

Collision regions:

- T-CI007 and T-CI015 both touch SessionStart banner authority — T-CI007 first
- T-CI023 and T-CI015 both touch `resolve_governance_paths.sh` — T-CI023 first
- T-CI007 and T-CI013 both touch `local_execution_gate.py` — keep edits in disjoint helpers (breakglass vs compound-stage naming)

## Rollback

`git restore --worktree --staged` scoped to write_allow. Revert local commits on this checkout only. Do not force-push. Leave `~/.l9/claude` receipts in place unless this plan created a malformed new schema file; delete only that new file.

## Complexity and uncertainty

Depth is `deep` (`route_plan.py --risk high --evidence partial`). Material unknowns:

- **U1 (probe):** is `L9_PUBLISH_PATH_OVERRIDE` live on this Cursor session or only on hosted Claude cloud?
- **U2 (probe):** which hook is the live SessionStart caller for re-probe on Cursor after `CURSOR_SESSIONSTART_NO_CLAUDE_CLOUD_V1`?
- **U3 (block):** OD-002 publish-Makefile precedence — T-CI008 stays blocked
- **U4 (accept_bounded):** treat the workspace clone as an intentional consumer checkout of Cursor-Governance unless the operator says leftover

## Execution DAG / Phase-0 table

Rows are Build todos, not Controller `claim`/`render` Task Cards.

| id | wave | depends_on | mutation | isolation_key |
|----|------|------------|----------|---------------|
| T-CI007 | A | [] | true | gate#breakglass |
| T-CI004 | A | [] | true | receipt#reprobe |
| T-CI012 | A | [] | true | rules#22 |
| T-CI009 | A | [] | true | deps#evidence |
| T-CI006 | B | [T-CI007] | true | account-env#source |
| T-CI102 | B | [] | true | profile#gh-rest |
| T-CI005 | B | [T-CI004] | true | receipt#memory-split |
| T-CI013 | C | [] | true | gate#stages |
| T-CI023 | C | [] | true | resolver#guard |
| T-CI016 | C | [] | true | l4#stale |
| T-CI015 | C | [T-CI007, T-CI023] | true | resolver#assert |
| T-CI002 | D | [] | true | settings#statedir |
| T-CI019 | D | [] | true | pr#retry |
| T-CI021 | D | [] | true | session#skill-log |
| T-CI022 | D | [] | true | session#itest-decl |
| T-CI008 | blocked | [T-CI007] | false | precommit#cwd — OD-002 blocker |

**Critical path:** T-CI007 → T-CI004 → T-CI005 → T-CI023 → T-CI015

**Leverage order:** T-CI007, T-CI004, T-CI009, T-CI012, T-CI005, T-CI006, T-CI102, T-CI013, T-CI023, T-CI015, T-CI016, T-CI002, T-CI019, T-CI021, T-CI022, T-CI008

Wave A four lanes match the r2 recommended width. Do not start wave B memory split before CP-receipts. Do not implement T-CI008.

## Property evidence matrix

| id | after | evidence |
|----|-------|----------|
| SP-01 | T-CI007 | gate unit test: env string without receipt does not authorize publish |
| SP-02 | T-CI004 | receipt JSON has per-component reason and log path; re-probe test under a fake lock |
| SP-03 | T-CI009 | stamp or log contains exit code, timestamp, interpreter path, import result |
| SP-04 | T-CI012 | rule 22 server-absent paragraph; projection fixture with Context7 absent |
| SP-05 | T-CI005 | receipt keys `memory.cli` and `memory.mcp`; hydrate test with PICKUP-only facts reports empty task count |
| SP-06 | each wave | `.pre-commit-config.yaml` changed-file hooks; `PR_STACK=auto PR_REMEDIATE=0 make pr` at finish |

## Stress and disconfirm

1. If this Cursor session already has no `L9_PUBLISH_PATH_OVERRIDE` and SessionStart already prints grant age, T-CI007 shrinks to tests.
2. If Cursor SessionStart has no live Claude caller, T-CI004 must attach to the Cursor hook that still runs, not `session_start_claude_governance.sh` alone.
3. If T-CI102 wording invents a second PAT, stop and keep rule 62 on `openclaw-igorbot/github#token` only.
4. If T-CI013 scratchpad allowance matches unresolved expansions, forced removal of a repo path becomes reachable — keep unresolved fail-closed.
5. If T-CI008 is implemented without an OD-002 decision, this plan has encoded unauthorized doctrine.

Assumed still true: revision-mismatch expiry stays landed; broker stays retired; `toolchain_proven` stays the deps gate; PR#360 in-repo closures stay in the tree.

## Out of scope

- `make campaign`, Program Lock, Controller lease
- Broker revival, `CLAUDE_SESSION_JWT`, issues #301/#302, CI-010 probe splits
- CI-001 prompt, CI-011 GitHub MCP pagination, CI-020 notification age, CI-026 add_repo, CI-100 Actions approval, CI-101 branch directive
- CI-024 / CI-029 / CI-031 / CI-017 / CI-032 other-repo work
- CI-003 / CI-036 harness Stop-hook legs
- Invalidated CI-002 `is_tracked` and IMP-06 gitignore copies
- Closed CI-014 / CI-018 / CI-025 / CI-027 / CI-030 / CI-033 / CI-037
- `_archive/` contents
- Merge

## Convergence

| Field | Value |
|-------|-------|
| status | `partial` |
| execute_via | Cursor Build on the current checkout / unique chain tip |
| remaining_unknown_ids | U1, U2, U3, U4 |
| next_skill | Build, then `l9-ynp` only if the next skill is unclear |
| stop_reason | Plan validated for Cursor Build. Implementation not run. T-CI008 blocked on OD-002. |
| finish_proof | Opened PR URL after `PR_STACK=auto PR_REMEDIATE=0 make pr` |

### Checkpoints

- **CP-breakglass** after T-CI007 — do not start T-CI006 / T-CI015 while the standing string still widens publish
- **CP-receipts** after T-CI004 — do not start T-CI005 until per-component reason and log path exist
- **CP-memory** after T-CI005 — do not collapse transports back into one `memory` word
- **CP-od002** — leave T-CI008 blocked

## Doc / Root Surface Impact

CLAUDE.md, AGENTS.md, CANONICAL_LAW.md, ARCHITECTURE.md, INVARIANTS.md: no update required for this plan. Rule 22 and rule 62 update with T-CI012 and T-CI102. Remaining-work JSON updates if a todo disposition changes.
