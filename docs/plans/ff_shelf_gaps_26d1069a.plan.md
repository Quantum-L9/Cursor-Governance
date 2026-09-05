---
name: Close /ff shelf loop gaps
overview: "Stop the /ff shelf loop from being an agent-improvised path, and stop shallow/grafted clones from false-parking unique tips. Own shelf mutate in one script. Compare catch-up tips by SHA first; use rev-list counts only on full history after SHA differs."
todos:
  - id: T1
    content: "Add ff_shelf.py for leftover untracked WIP/, docs/plans/, and campaigns/ only (not the root task-queue file, not dirty-tracked corpus). In-clone path list, rsync --files-from that file, append existing same-author feat/ff-shelf-* worktree or cut one stamp when none is open. Apply corpus kernels to leftover files; write kernel_pass YAML only on *.plan.md. Pathspec-from-file then separate commit, L4 begin+authorize-release. Shelf-script publish uses PR_STACK=auto. This Build's own PR also uses V4 PR_STACK=auto stacked on #499. Then run_ff_post_shelf.sh."
    status: pending
    depends_on: []
  - id: T2
    content: "Extend l9-repo-sync self_test after T7: list lands under clone .l9/; rsync command contains no /tmp and no process substitution; add uses --pathspec-from-file alone; open shelf PR is appended not restamped. Keep the T7 shallow SHA fixtures in the same file."
    status: pending
    depends_on: [T1, T7]
  - id: T3
    content: "Prune untracked leftover *.plan.md when kernel-normalized body matches the open-PR blob at the same path; keep exact-sha256 unlink; never unlink unique leftover bytes"
    status: pending
    depends_on: []
  - id: T4
    content: "Replace agent rsync/add recipes with a single ff_shelf.py call in execute.md, SKILL.md compact shelf step, and commands/ff.md steps 2-3; keep ff.sh push-off; verify always via locked interpreter"
    status: pending
    depends_on: [T1]
  - id: T5
    content: "Require ff_shelf.py in validate_pack_structure; fail if execute.md still has files-from=<( or git add -- ${shelf_paths}; require .l9/ff-shelf-untracked.txt and GOV_PY verify_worktree_clean.py"
    status: pending
    depends_on: [T4]
  - id: T6
    content: "Append AGENTS.md fragment FF_SHELF_SCRIPT_V1 after FF_PAIR_FLAGS_V1 (last live FF_* block). Add a MUST line to rule 55 that leftover-untracked WIP/docs/plans/campaigns shelf mutate is ff_shelf.py. Do not rewrite older FF_* fragments. Do not widen this Build to the root task-queue file or dirty-tracked corpus."
    status: pending
    depends_on: [T4]
  - id: T7
    content: "In ff.sh compare HEAD to origin/${TARGET_BRANCH} by SHA before any rev-list count. Equal: treat as at-tip (AHEAD=0 BEHIND=0) so preserve, reset, maybe_leave, and checkout -f skip. Unequal and shallow/grafted: never create l9/ff-preserve-* from rev-list counts; existing dirty park then reset --keep. Unequal and full history: preserve only when HEAD is not an ancestor of origin/${TARGET_BRANCH}. Never unshallow. Never merge --ff-only. Add the shallow SHA fixture in self_test.py."
    status: pending
    depends_on: []
isProject: false
kind: simple
execute_via: cursor-build
kernel_pass:
  bound_path: ff_shelf_gaps_26d1069a.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-09-05T21:12:00Z
    deltas:
      - "Re-verified bind: PR 497 merged; open board empty; this checkout is behind origin/main 65b94670 — Build from origin/main, not 91daac4"
      - "Locked T7 SHA-first: at-tip zeros AHEAD/BEHIND; shallow never preserves from rev-list; full history preserves only when HEAD is not an ancestor of origin/main"
      - "Removed the contradiction that rollback left ff.sh untouched while T7 edits it"
      - "Sequenced T2 after T7 so both self_test.py writers cannot race; put T3 on the critical path; unique leverage ranks"
      - "Replaced V4 catalog-name with PR_STACK= PR_REMEDIATE=0 make pr"
      - "Filled template sections from PLAN_DOCUMENT so the projection is the binding contract, not an unfilled fill-guide"
  recursive_alignment:
    kernel: kernels/Recursive Alignment.md
    ran_at: 2026-09-05T21:26:00Z
    deltas:
      - "P4 is git fetch + branch/worktree from origin/main + pathspec copy of the three plan files; /ff on this dirty tree is forbidden because it would shelf the plan"
      - "Mutate base re-locked to origin/main 3c45c916 (65b94670 is stale)"
      - "T1 PR_STACK=auto is the later shelf-script publish; this Build V4 stays PR_STACK="
      - "T1 corpus set locked to leftover untracked WIP/docs/plans/campaigns; kernel_pass YAML only on *.plan.md; corpus kernels still apply"
      - "T6 appends after FF_PAIR_FLAGS_V1; rule 55 MUST names the same subset; U3 accepts rule 55 TODO.md/dirty-tracked as follow-on"
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-09-05T21:30:00Z
    body_sha256: "ac295921565527a7bd5c0d5c8f7faf7a8164bc1a673cf7920cb0bb80060d50be"
    deltas:
      - "Re-verified bind: unique open PR #499 at f72042ba; stack this Build there; do not fork origin/main"
      - "P3/P4/V4/SP-08 restacked from empty-board origin/main to PR_STACK=auto on #499"
      - "P4 remains fetch+pathspec copy; /ff on this dirty tree still forbidden"
      - "kernel_pass complete; PLAN_DOCUMENT stop_reason now waits for Build, not another kernel"
---

# PLAN: Close /ff shelf loop gaps

> **Authoritative JSON:** `docs/plans/PLAN_DOCUMENT.ff_shelf_gaps.v1.json`
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** Press **Build**. Unique open PR is **#499**. Start from tip `f72042ba` (`agent/cursor/optB-excludes`). Do not mutate at `91daac4`. Do not fork `origin/main` while #499 is open. Do not `/ff` this dirty tree. After todos: `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do not run `make campaign`.
> **Kernels:** Improve 2026-09-05T21:12:00Z. Recursive Alignment 2026-09-05T21:26:00Z. Validate & Repair 2026-09-05T21:30:00Z.

## Execute via Cursor Build

Press **Build**. Plan on the current workspace. Execute from the unique open-PR tip.

- Unique open PR is **#499** (`agent/cursor/optB-excludes` @ `f72042ba1cfe207d54af8564798327c560f7d885`, base `main`). `#497` remains merged. Never branch from `origin/main` while that unique chain exists.
- This checkout is `main` @ `91daac4a8a026917bfd2ae243827008a83866ce2`. `origin/main` is `3c45c9165cf09475fc962fa829aa617e03f1347a` and is an ancestor of #499. P4: `git fetch`; start the feature branch from #499; copy the three plan files by pathspec. Never `/ff` this dirty tree (leftover untracked `docs/plans/` would enter the shelf loop).
- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- After Build todos complete: scoped-commit (pathspecs), `l4_local.py authorize-release`, then `PR_STACK=auto PR_REMEDIATE=0 make pr`. Do not skip `make pr`.
- The finish reply must display the opened PR URL as proof.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.ops.ff_shelf_gaps.v1` |
| name | Close /ff shelf loop gaps |
| overview | Own shelf mutate in `ff_shelf.py`. SHA-first tip compare in `ff.sh`. |
| schema_version | `1.0.0` |
| status | `draft` |
| is_project | `false` |
| owner | cursor-governance |
| created_at | `2026-09-05` |
| updated_at | `2026-09-05` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | `skills/l9-repo-sync/` + `rules/55-ff-only-ssot-sync.mdc` + AGENTS.md `FF_*` fragments |
| plan_class | `bounded_execution_contract` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Cursor Build stacked on #499. `governance_activate_fresh.sh do_ff` stays a follow-on (U2). |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-09-05T21:30:00Z` (VR re-verify) |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/Users/ib-mac/Cursor-Governance` |
| ssot_clone | `$HOME/.cursor-governance` |
| branch | `main` (stale vs origin; Build must leave this SHA) |
| commit_sha | `91daac4a8a026917bfd2ae243827008a83866ce2` (plan-bind HEAD; not the mutate base) |
| mutate_base_sha | `f72042ba1cfe207d54af8564798327c560f7d885` (PR #499 tip) |
| dirty | `true` (three untracked plan artifacts) |
| artifact_hashes | PLAN_DOCUMENT + this file + section receipt (untracked) |
| allowed_local_dirt | `docs/plans/PLAN_DOCUMENT.ff_shelf_gaps.v1.json`, `docs/plans/ff_shelf_gaps_26d1069a.plan.md`, `docs/plans/ff_shelf_gaps_26d1069a.section-receipt.json` |
| overlap_policy | `explicitly_allow_listed_paths` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Close the `/ff` shelf loop so leftover WIP / plans / campaigns are copied, stamped, committed, and published by one script, and so `ff.sh` catch-up does not false-park shallow grafts. Preserve: `ff.sh` push-off, unique leftover bytes, sacred-WIP isolation, AGENTS.md append-only, full-history unique local commits.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | ff_shelf writes `$CLONE/.l9/ff-shelf-untracked.txt` and rsyncs `--files-from` that path; no process substitution; no `/tmp` files-from | `structural` | `self_test.py` fixture asserts the rsync argv | true |
| SP-02 | `git add --pathspec-from-file` on that list in a command that does not also commit or status | `structural` | `self_test.py` plus `validate_pack_structure.py` needle | true |
| SP-03 | an already-open same-author `feat/ff-shelf-*` PR is appended; a second stamp is not created | `runtime_behavior` | `self_test.py` append-not-restamp fixture | true |
| SP-04 | post-shelf prune unlinks leftover `*.plan.md` whose kernel-normalized body matches the open-PR blob; unique leftover bytes stay | `runtime_behavior` | `pack_self_test.py` donor + unique cases | true |
| SP-05 | slash and `execute.md` name `ff_shelf.py` as the only shelf mutate path; `ff.sh` stays push-off | `structural` | `validate_pack_structure.py` FAIL on `files-from=<(` | true |
| SP-06 | pack validators PASS; `.pre-commit-config.yaml` is the hook catalog | `quality_gate` | V1–V3 then V4 `make pr` | true |
| SP-07 | SHA-first tip compare: equal SHA is at-tip; shallow unequal never writes `l9/ff-preserve-*` from rev-list; full-history unique tip still preserves; no unshallow; no `merge --ff-only` | `runtime_behavior` | `self_test.py` shallow + full-history fixtures | true |
| SP-08 | Build worktree HEAD equals the unique open-PR tip before first mutate; P4 is fetch+copy, not `/ff` | `repository_state` | `git rev-parse HEAD` == `f72042ba1cfe207d54af8564798327c560f7d885` or a newer unique-chain tip | true |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.ops.ff_shelf_gaps.v1` |
| source_ref | `plan.ops.ff_shelf_gaps.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | Immutable baseline above |
| baseline_verified | Improve re-verify passed for P0–P3 |
| drift_detected | this checkout is behind #499 tip (P4 pending) |

### Probes (min 1; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `branch_and_HEAD_resolution` | `git fetch origin && gh pr list --state open` | mutate base is #499 tip `f72042ba`, not `91daac4` and not `origin/main`; `/ff` is not the P4 move | true |
| CP-02 | `command_available` | locked `.venv` python; `gh`; `rsync`; `git` | each resolves on PATH / GOV_PY | true |
| CP-03 | `filesystem_write` | may_modify paths writable | T1–T7 paths exist or are creatable | true |
| CP-04 | `open_pr_board` | `gh pr list --state open --json number` | unique open PR is #499 at VR; re-check at Build start; a second chain fails closed | true |

## Execution envelope

Mutations outside this envelope are forbidden.

### Filesystem

- **write_allow:** `skills/l9-repo-sync/scripts/ff_shelf.py`, `skills/l9-repo-sync/scripts/ff.sh`, `skills/l9-repo-sync/scripts/self_test.py`, `skills/l9-repo-sync/scripts/validate_pack_structure.py`, `skills/l9-repo-sync/references/execute.md`, `skills/l9-repo-sync/SKILL.md`, `commands/ff.md`, `rules/55-ff-only-ssot-sync.mdc`, `AGENTS.md` (append fragment only), `skills/l9-git-work-preserve/scripts/prune_open_pr_copies.py`, `skills/l9-git-work-preserve/scripts/pack_self_test.py`
- **write_deny:** `ops/scripts/governance_activate_fresh.sh`, `ops/autonomy/worktree_isolation_gate.py`, `CANONICAL_LAW.md`, `WIP/Legal Defense/`, `environment/program-execution/core/`, secrets, unrelated trees
- **delete_allow:** none (prune unlinks leftover untracked copies only via the existing prune tool, after T3)

### Commands

- **allow:** `python3 skills/l9-repo-sync/scripts/validate_pack_structure.py`, `python3 skills/l9-repo-sync/scripts/self_test.py`, `python3 skills/l9-git-work-preserve/scripts/pack_self_test.py`, `PR_STACK=auto PR_REMEDIATE=0 make pr` (hook catalog `.pre-commit-config.yaml`), `l4_local.py authorize-release`, scoped `git add` pathspecs
- **deny:** never `git fetch --unshallow`; never `git merge --ff-only` as the `/ff` catch-up move; never `/ff` / `ff.sh` as the P4 catch-up on this dirty tree; never `make campaign`; never force-push, hard-reset, secret exfil, or `make pr` inside `ff.sh`

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | GitHub (`gh` / `make pr` publish) |

### Secrets

| Field | Value |
|-------|-------|
| access | `runtime_injected_only` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false`. This plan does not merge.

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T7 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | revert `ff.sh` + SHA fixtures | false |
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | delete `ff_shelf.py` | false |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | revert prune helpers | false |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | revert `self_test.py` | false |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore execute/SKILL/slash from origin/main | false |
| T5 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | revert validator needles | false |
| T6 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | leave appended fragment; do not rewrite older FF_* | false |
| V4 | `network_write` | `safe_with_dedupe` | `manual_only` | close/abandon PR | false |

T3 prune absorb is `destructive_filesystem_mutation` only against leftover untracked files whose kernel-normalized body matches an open-PR blob. Unique leftover bytes are never unlinked.

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T7 | repo-sync catch-up | `ops` | `skills/l9-repo-sync` + rule 55 | unshallow; `merge --ff-only`; rewrite park/hold/switch |
| T1 | shelf mutate | `ops` | `commands/ff.md` + execute.md | `/tmp` files-from; compound add&&commit; `make pr` inside `ff.sh` |
| T3 | leftover absorb | `ops` | `skills/l9-git-work-preserve` | unlink unique leftover bytes |
| T4 | protocol | `docs` | slash + skill | second mutate recipe |
| T6 | doctrine | `policy` | AGENTS.md additive_only | rewrite older FF_* fragments; append before FF_PAIR_FLAGS_V1; widen MUST to TODO.md/dirty-tracked |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.ops.ff_shelf_gaps.v1` |
| source_execution_ref | `plan.ops.ff_shelf_gaps.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | baseline drift; blocking property fail; envelope breach; prune would unlink unique bytes |

### Strategies (typed)

| domain | mode | notes |
|--------|------|-------|
| code | `revert_commit` | revert the Build-branch commit(s). After revert, `ff.sh` returns to rev-list preserve (known shallow false-park). Isolation gates stay. Restore `execute.md` recipes from `origin/main` only when `ff_shelf.py` is also reverted. |
| data | `none` | no durable datastore |
| external_state | `manual_recovery` | close/abandon the opened PR |
| local_state | `git_restore_scoped_paths` | write_allow only |

### Irreversible operations

- none in the catch-up path
- prune unlink of an absorbed leftover is recoverable from the open-PR blob; unlink of unique leftover bytes is forbidden (SP-04)

### Rollback verification

- `git show origin/main:skills/l9-repo-sync/scripts/ff.sh` still contains the rev-list AHEAD block after revert
- `test ! -f skills/l9-repo-sync/scripts/ff_shelf.py` after a full revert of T1

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` |
| uncertainty | `medium` |
| blast_radius | `high` |
| architectural_boundaries_crossed | `0` |
| external_systems_touched | `1` (GitHub publish) |
| migration_required | `false` |
| unknown_dependency_count | `3` (U1, U2, U3) |

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.ops.ff_shelf_gaps.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | owner | layer | depends_on | outputs |
|----|-------|-------|------------|---------|
| T7 | agent | ops | [] | SHA-first `ff.sh`; shallow SHA fixture in `self_test.py` |
| T1 | agent | ops | [] | `ff_shelf.py` |
| T3 | agent | ops | [] | kernel-normalize prune + pack_self_test |
| T2 | agent | assurance | [T1, T7] | shelf fixtures in the same `self_test.py` |
| T4 | agent | docs | [T1] | thin slash / execute / SKILL |
| T5 | agent | assurance | [T4] | pack-structure needles |
| T6 | agent | policy | [T4] | AGENTS.md fragment after FF_PAIR_FLAGS_V1 + rule 55 leftover-untracked MUST |
| V4 | agent | control_plane | [T2, T3, T5, T6] | PR URL stacked on #499 |

**Critical path:** `T7` → `T1` → `T3` → `T2` → `T4` → `T5` → `T6`

T1 and T3 are independent of T7. Critical path lists ship order so T3 cannot be skipped. T2 must wait for T7 because both write `self_test.py`.

**Forbidden edges:** T2 before T7; T4 before T1; T5/T6 before T4; mutate at `91daac4`; fork `origin/main` while #499 is open

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `structural_evidence` | argv inspect | `python3 skills/l9-repo-sync/scripts/self_test.py` | rsync `--files-from` is `$CLONE/.l9/ff-shelf-untracked.txt` | `not_run` |
| EV-SP-02 | SP-02 | `structural_evidence` | needle | `python3 skills/l9-repo-sync/scripts/validate_pack_structure.py` | no `files-from=<(`; add is `--pathspec-from-file` alone | `not_run` |
| EV-SP-03 | SP-03 | `runtime_behavior_evidence` | fixture | `python3 skills/l9-repo-sync/scripts/self_test.py` | open shelf PR appended | `not_run` |
| EV-SP-04 | SP-04 | `runtime_behavior_evidence` | fixture | `python3 skills/l9-git-work-preserve/scripts/pack_self_test.py` | donor unlinks; unique stays | `not_run` |
| EV-SP-05 | SP-05 | `structural_evidence` | needle | `python3 skills/l9-repo-sync/scripts/validate_pack_structure.py` | `ff_shelf.py` required; `ff.sh` has no `gh pr create` | `not_run` |
| EV-SP-06 | SP-06 | `quality_gate_evidence` | catalog `.pre-commit-config.yaml` | `PR_STACK=auto PR_REMEDIATE=0 make pr` | changed-file hooks PASS; PR stacked on #499; URL printed | `not_run` |
| EV-SP-07 | SP-07 | `runtime_behavior_evidence` | fixture | `python3 skills/l9-repo-sync/scripts/self_test.py` | shallow: no `l9/ff-preserve-*`; full unique: preserve exists | `not_run` |
| EV-SP-08 | SP-08 | `repository_state_evidence` | rev-parse | `git fetch origin && git rev-parse HEAD origin/agent/cursor/optB-excludes` | HEAD equals #499 tip before T7; `/ff` was not the P4 move | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Two same-author `feat/ff-shelf-*` PRs → append newest `updatedAt`; refuse a third stamp (U1 bounded).
- Leftover `*.plan.md` with unique prose and a missing `kernel_pass` → prune must keep the file.
- Agent still reads old `execute.md` → T5 fails the pack if `files-from=<(` remains.
- `FF_SHELF_PUBLISH=0` → script still writes the in-clone list and commits; skips `make pr`.
- Shallow clone, SHA differs, rev-list says ahead 1 behind 1 → no `l9/ff-preserve-*`; `reset --keep`.
- Full-history clone with unique local commits → `l9/ff-preserve-*` still created before `reset --keep`.
- Build starts at `91daac4` or `origin/main` while #499 is open → stop; P4 failed.
- P4 uses `/ff` on this dirty tree → stop; the three plan files would be shelved.

### Assumption failure conditions

- Sacred-WIP isolation no longer denies rsync that names WIP and `/tmp` in one command
- Isolation no longer denies `git add && commit` compounds
- A foreign open PR appears mid-Build → publish restacks on that unique tip; do not open a sibling
- AGENTS.md treated as rewriteable

### Blast radius notes

Wrong prune absorb deletes unique leftover plans. Wrong append lands corpus on a foreign shelf PR. Docs-only patch leaves the next `/ff` hitting `/tmp` and sibling denials. Wrong SHA-first rule drops a full-history unique main commit or keeps false-parking shallow tips. Mutating at `91daac4` or `origin/main` while #499 is open creates a sibling chain.

### Rollback constraints

- No force-push / history rewrite
- After revert, shallow false-park returns; that is accepted rollback, not a new defect to hide

## Out of scope

- Rewriting `ff.sh` park/hold/switch primitives beyond the SHA tip compare
- `git fetch --unshallow` or deepen-by-default inside `/ff`
- Using `merge --ff-only` as the `/ff` catch-up move
- Changing `governance_activate_fresh.sh do_ff` (U2 follow-on)
- Widening `ff_shelf.py` to `TODO.md` or dirty-tracked corpus (U3 / rule 55 remainder)
- Putting `make pr` inside `ff.sh`
- Weakening sacred-WIP isolation to allow WIP via `/tmp`
- Draining Dependabot or other sibling PR chains
- Deleting unused `feat/ff-shelf-20260904T145518Z`
- KERNEL pack or PE overlay landing
- Program Lock and the campaign runner
- `CANONICAL_LAW.md`
- `WIP/Legal Defense` and secret globs

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.ops.ff_shelf_gaps.v1` |
| source_ref | `plan.ops.ff_shelf_gaps.v1` |
| current_state | `partial` |
| implementation_ready | `false` until P4 (HEAD == #499 tip) and Build starts |

### Gates

- **executable_when:**
  - P0–P3 re-verified (done at Improve)
  - P4: Build worktree at #499 tip `f72042ba`
  - DAG acyclic (T2 waits for T7)
  - envelope + side-effect matrix complete
  - U1/U2/U3 remain accept_bounded
- **complete_when:**
  - EV-SP-01..08 `passed`
  - rollback contract still valid
  - write_allow-only diff
- **blocking_conditions:**
  - mutate at `91daac4` or fork `origin/main` while #499 is open
  - prune of unique leftover bytes
  - `unshallow` or `merge --ff-only` in `ff.sh`
  - AGENTS.md rewrite of older FF_* blocks

### Evidence

- **required_evidence_refs:** `EV-SP-01` .. `EV-SP-08`
- **observed_evidence_refs:** P0–P3 VR re-verify (#499 unique)
- **missing_evidence:** P4, V1–V4, EV-SP-01..08

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| open_blocker | P4 | this checkout is behind #499 tip | measure at Build start — fetch and branch from `f72042ba` |
| unknown | U1 | two same-author shelf PRs | accept_bounded — newest updatedAt; no third stamp |
| unknown | U2 | activate_fresh `do_ff` still `merge --ff-only` | accept_bounded — follow-on; out of write_allow |
| unknown | U3 | rule 55 also names `TODO.md` and dirty-tracked corpus | accept_bounded — this Build keeps the slash/FF_CORPUS untracked set |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `execution_ready` → `executing` → `converged` |
| minimum_safe_next_action | Press **Build** from #499 tip `f72042ba`; copy the three plan files by pathspec; never `/ff` this dirty tree |
| execute_via | Cursor Build; PR stacked on #499; display PR URL |
| broader_work_requires_separate_contract | `true` (U2 activate_fresh; U3 rule 55 remainder) |
