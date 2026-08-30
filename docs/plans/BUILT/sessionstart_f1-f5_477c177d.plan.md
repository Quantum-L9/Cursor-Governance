---
name: SessionStart F1-F5
overview: Tighten PR 417 SessionStart so Cursor Degraded is this-surface only. Mutate, then revise, harden, and improve in place on the same files. Push onto existing PR 417.
todos:
  - id: todo-01-execute-417
    content: Bind execute to existing 417 worktree (session-start-truth-v2). Do not fork main. Do not land on PR 418.
    status: completed
  - id: todo-02-mutate-f1-f5
    content: "Apply F1–F5 in the 417 tree: drop Cursor claude-adapter-repair; skill-usage absent = n/a; collapse hydrate into graphiti; rewrite hook header; delete Claude no-op timeout fallbacks."
    status: completed
  - id: todo-03-revise
    content: "Revise in place: re-read the five contracts against the diff. Fix drift in write_allow only. No new scope, no new files except tests already listed."
    status: completed
  - id: todo-04-harden
    content: "Harden in place: tests that fail if F1–F5 return (Cursor repair line, skill-usage degraded, double hydrate, GNU/no-op timeout, false header)."
    status: completed
  - id: todo-05-improve
    content: "Improve in place: kernels/Improve.md then Recursive Alignment then Validate & Repair on write_allow paths only. Same files; no follow-on plan."
    status: completed
  - id: todo-06-prove
    content: Targeted pytest on reporter + refresh-guard + bootstrap-edge. Evidence, not exit-0 alone.
    status: completed
  - id: todo-07-publish-417
    content: authorize-release + PR_STACK=auto PR_REMEDIATE=0 make pr on 417. Display PR 417 URL.
    status: completed
isProject: false
kernel_pass:
  bound_path: sessionstart_f1-f5_477c177d.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-30T20:59:50Z
    body_sha256: "4ecf94ed19b1a977cae2cdcc61e5c53a1d4ecea7669bb686051e1007e56c314f"
    deltas:
      - "Kept completed F1-F5 Build receipt; no second plan created"
      - "Corpus shelf of leftover untracked built copy after /ff"
  recursive_alignment:
    kernel: kernels/Recursive Alignment.md
    ran_at: 2026-08-30T20:59:51Z
    body_sha256: "4ecf94ed19b1a977cae2cdcc61e5c53a1d4ecea7669bb686051e1007e56c314f"
    deltas:
      - "Aligned with landed PR 417 SessionStart truth; todos stay completed"
      - "No exclusive lock or second-plan drift"
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-30T20:59:52Z
    body_sha256: "4ecf94ed19b1a977cae2cdcc61e5c53a1d4ecea7669bb686051e1007e56c314f"
    deltas:
      - "Content gates clean; stamped kernel_pass on the same bound path"
      - "No exclusive-list ellipsis and no unresolved exclusive lock"
---

# SessionStart F1–F5 tighten

`route_plan.py --risk medium --evidence sufficient` → `depth=standard`, `omit_gates=[]`.

Revise, harden, and improve run **in this plan, on the same files**, after mutate and before publish. They are not a later `/gmp` and not a second plan.

## Execute via Cursor Build

Press **Build**. Plan on the current workspace. Execute on the existing PR 417 worktree.

- User named **PR 417**. Do **not** branch from `origin/main`. Do **not** land on PR 418.
- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a planning requirement. Use `/Users/ib-mac/.l9/gov-worktrees/cursor__session-start-truth-v2`.
- After todos: scoped-commit (pathspecs), `l4_local.py authorize-release`, `PR_STACK=auto PR_REMEDIATE=0 make pr` from that worktree.
- Finish reply **must** display https://github.com/Quantum-L9/Cursor-Governance/pull/417.

## Metadata

- **plan_id:** `plan.ops.sessionstart-f1-f5.v1`
- **schema_version:** `1.0.0`
- **status:** `executable`
- **owner:** cursor
- **created_at:** `2026-08-30`
- **updated_at:** `2026-08-30`

## Architect framing

- **planning_ssot:** this file + PR 417 reporter (`ops/scripts/session_start_runtime_report.py`)
- **plan_class:** `remediation_plan`
- **redesign_allowed:** `false`
- **follow_on_schema_evolution_separate:** `true`
- **framing_notes:** Cursor Build only. No PE. Classify Degraded as this-surface only.

## Immutable baseline

- **captured_at:** `2026-08-30T20:35:12Z`
- **repository:** `Quantum-L9/Cursor-Governance`
- **workspace (planning):** `/Users/ib-mac/Cursor-Governance` `main` @ `ac5c6d18f558fc994e920b22d6e791e719c8a4d3`
- **ssot_clone:** `~/.cursor-governance` (do not mutate)
- **execute branch:** `agent/cursor/session-start-truth-v2`
- **execute commit_sha:** `476ee4f557f8614ffd1d56d5b3c8e5183b95913f`
- **dirty:** worktree may have projected `.claude/hooks/session_start_claude_governance.sh` — ignore; pathspecs only
- **overlap_policy:** `explicitly_allow_listed_paths`
- **verification_rule:** `reverify_at_execution_start`
- **on_drift:** if 417 HEAD is not a descendant of `476ee4f5`, stop and replan
- **hook catalog:** [`.pre-commit-config.yaml`](.pre-commit-config.yaml)
- Do **not** write `Lock: origin/main = <sha>`.

## Objective

### Mission

PR 417 reports class + evidence instead of slogans, but Cursor `### Degraded` still lists leftover Claude-adapter repair (`never_ran` + `timeout: command not found`), treats a missing Claude skill-usage log as degraded, and can print both `graphiti` and `graphiti-hydrate` for one outage. The Cursor hook header still names plugins and cold venv as SessionStart reconcilers. The Claude hook still substitutes an unbounded `run_with_timeout() { shift; "$@" }` when the lib is missing.

Fix those five leftovers **on the 417 tree**. Then revise, harden, and improve **in place** on the same write_allow paths. Push onto the open PR. Do not fold `AGENTS.md`. Do not change live SSOT except by that merge later.

### Success properties

- **SP-01** (`repository_state`, blocking): Execute HEAD is `agent/cursor/session-start-truth-v2` (descendant of `476ee4f5`), not `origin/main`, not PR 418. Proof: `git rev-parse --abbrev-ref HEAD` + `git merge-base --is-ancestor 476ee4f5 HEAD`.
- **SP-02** (`runtime_behavior`, blocking): Cursor reporter with `never_ran` + timeout log emits only `claude-adapter: n/a`. No `claude-adapter-repair`. Skill-usage absent is `n/a`. Graphiti failed + hydrate degraded is one Degraded row. Claude-code `never_ran` remains this-surface `failed`.
- **SP-03** (`structural`, blocking): Cursor hook header does not say plugins or cold venv. Claude hook has no `run_with_timeout() { shift; "$@" }`. Missing lib skips `install.sh` and emits `SKIPPED`.
- **SP-04** (`quality_gate`, blocking): Targeted pytest on the three test files PASS. Then `PR_STACK=auto PR_REMEDIATE=0 make pr` updates PR 417 and the URL is shown.

## Capability preflight

- **preflight_id:** `preflight.plan.ops.sessionstart-f1-f5.v1`
- **blocking:** `true`

Probes:

- **CP-01** `worktree_on_417`: `git -C /Users/ib-mac/.l9/gov-worktrees/cursor__session-start-truth-v2 rev-parse --abbrev-ref HEAD` equals `agent/cursor/session-start-truth-v2`.
- **CP-02** `gov_python`: `$HOME/.cursor-governance/.venv/bin/python` exists and imports.
- **CP-03** `write_allow_writable`: reporter, both hooks, and the three test files exist in that worktree.

Failed blocking probe → stop. Do not mutate.

## Execution envelope

### Filesystem

- **write_allow:** `ops/scripts/session_start_runtime_report.py`, `ops/scripts/tests/test_session_start_runtime_report.py`, `ops/hooks/session_start_bootstrap.sh`, `environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh`, `ops/scripts/tests/test_cursor_shared_bootstrap_edge.py`, `tests/environment/adapters/test_session_start_refresh_guard.py`, `docs/plans/sessionstart_f1-f5_477c177d.plan.md`
- **write_deny:** `AGENTS.md`, `CANONICAL_LAW.md`, `hooks.json`, live `~/.cursor-governance`, PR 418 paths, unrelated WIP
- **delete_allow:** none (except deleting the two no-op fallback function bodies)

### Commands

- **allow:** scoped git, pytest on the three files, `l4_local.py authorize-release`, `PR_STACK=auto PR_REMEDIATE=0 make pr`
- **deny:** `make campaign`, merge, force-push, hard-reset, `install.sh` from Cursor SessionStart, `make precommit-repo` then `make pr`

### Network

- **mode:** `named_services_only` (GitHub for `make pr` / `gh` only)

### Secrets

- **access:** `runtime_injected_only` (existing `gh` token). Redaction required.

### Autonomous merge

`autonomous_merge: false`

## Side effects and idempotency

- **todo-01-execute-417:** filesystem_read; `safe_to_repeat`
- **todo-02-mutate-f1-f5:** filesystem_mutation; `safe_with_dedupe`; retry_once; compensation = restore write_allow
- **todo-03-revise:** filesystem_mutation; `safe_with_dedupe` (same paths)
- **todo-04-harden:** filesystem_mutation; `safe_with_dedupe` (tests only)
- **todo-05-improve:** filesystem_mutation; `safe_with_dedupe` (kernels on write_allow only)
- **todo-06-prove:** filesystem_read; `safe_to_repeat`
- **todo-07-publish-417:** network_write; `safe_with_dedupe`; compensation = leave PR 417 as prior tip

## Architecture impact

- Mutate/revise/harden/improve stay in `ops` + Claude adapter hook. Owning contract: SessionStart reporter + `CURSOR_SESSIONSTART_NO_CLAUDE_CLOUD_V1`.
- **prohibited:** redesign of Graphiti hydrate; starting Neo4j; writing a breakglass; folding `AGENTS.md` §2.1.

## Rollback

- **rollback_id:** `rollback.plan.ops.sessionstart-f1-f5.v1`
- **supported:** `true`
- **automatic_allowed:** `false`
- **code:** `git_restore_scoped_paths` or revert the follow-up commit on 417
- **data / external_state:** `none`
- Do not force-push. Live SSOT unchanged until 417 merges.

## Complexity and uncertainty

- complexity `low` · uncertainty `low` · blast_radius `medium` (SessionStart Degraded + Claude repair)
- architectural_boundaries_crossed `0` · migration_required `false`

## Execution DAG

```text
todo-01-execute-417
    → todo-02-mutate-f1-f5
    → todo-03-revise          ← in place
    → todo-04-harden          ← in place
    → todo-05-improve         ← in place
    → todo-06-prove
    → todo-07-publish-417
```

Critical path is that sequence. Forbidden: publish before prove; harden/improve on a new branch; skip revise.

### todo-01-execute-417 (preflight)

Confirm worktree HEAD is `agent/cursor/session-start-truth-v2`. Do not create a worktree. Do not check out 418.

### todo-02-mutate-f1-f5 (mutate)

- **F1** — `surface != claude-code`: only `claude-adapter: n/a`. Do not emit `claude-adapter-repair`.
- **F2** — Rewrite [`ops/hooks/session_start_bootstrap.sh`](ops/hooks/session_start_bootstrap.sh) lines 11–12: IDE is the only SessionStart workspace writer; uv already ran in shared bootstrap.
- **F3** — `classify_skill_usage`: absent / “never wrote” → `n/a`, not in Degraded.
- **F4** — If graphiti is already degraded/failed, append hydrate reason; no second line. Emit `graphiti-hydrate` only when graphiti is `ok`.
- **F5** — Delete both `run_with_timeout() { shift; "$@"; }` fallbacks. Source GOV lib then hook-relative lib. If missing: skip `install.sh`; emit `SKIPPED`. `.mcp.json` parse may use bare `python3`.

### todo-03-revise (in place)

Re-read F1–F5 against the diff. If a contract is unmet or a comment still lies, edit the same files. Do not add scope. Do not open a follow-on plan.

### todo-04-harden (in place)

Tests in [`ops/scripts/tests/test_session_start_runtime_report.py`](ops/scripts/tests/test_session_start_runtime_report.py), [`ops/scripts/tests/test_cursor_shared_bootstrap_edge.py`](ops/scripts/tests/test_cursor_shared_bootstrap_edge.py), [`tests/environment/adapters/test_session_start_refresh_guard.py`](tests/environment/adapters/test_session_start_refresh_guard.py):

- Cursor + `never_ran` → no `claude-adapter-repair`
- skill-usage absent → `n/a`
- graphiti failed + hydrate degraded → one Degraded row
- Claude hook has no no-op fallback; missing lib mentions `SKIPPED` before `bash "$installer"`
- Keep slogan / GNU timeout / projection / resolve-order assertions

### todo-05-improve (in place)

Read and apply, in order, on write_allow only:

1. [`kernels/Improve.md`](kernels/Improve.md)
2. [`kernels/Recursive Alignment.md`](kernels/Recursive Alignment.md)
3. [`kernels/Validate & Repair.md`](kernels/Validate & Repair.md)

Stamp `kernel_pass` on this plan (`ran_at` order Improve → RA → V&R). Do not record-kernels as a substitute for this pass. Do not touch files outside write_allow.

### todo-06-prove (validate)

```text
pytest ops/scripts/tests/test_session_start_runtime_report.py \
       ops/scripts/tests/test_cursor_shared_bootstrap_edge.py \
       tests/environment/adapters/test_session_start_refresh_guard.py
```

Plus a reporter invocation that shows Cursor Degraded without `claude-adapter-repair` and without a second hydrate line when graphiti failed. Do not claim SSOT changed.

### todo-07-publish-417

Only after SP-02/SP-03/SP-04 evidence. Scoped-commit, authorize-release, `PR_STACK=auto PR_REMEDIATE=0 make pr`. Show the PR 417 URL. Do not merge.

## Property evidence matrix

- **EV-SP-01:** `git -C <wt> rev-parse --abbrev-ref HEAD` → `agent/cursor/session-start-truth-v2`
- **EV-SP-02:** pytest + reporter stdout markers (`claude-adapter: n/a`, no `claude-adapter-repair`, `itest/neo4j` unchanged, single graphiti Degraded row)
- **EV-SP-03:** hook text has no plugins/venv slogan and no no-op fallback
- **EV-SP-04:** `make pr` output contains `https://github.com/Quantum-L9/Cursor-Governance/pull/417`

## Stress and disconfirm

- Disconfirm: hiding Cursor repair hides a live Claude Desktop fail? No — Claude-code still scores `never_ran`.
- Disconfirm: skip `install.sh` when lib missing leaves `never_ran` on old SSOT? Already true; unbounded installer is worse.
- Disconfirm: collapsing hydrate hides healthy Graphiti + failed compile? No — that path still emits `graphiti-hydrate`.
- Assumed false if: skill-usage.jsonl becomes a required Cursor contract.
- Blast radius: SessionStart `### Degraded`; Claude Desktop/Mobile repair.
- Rollback: revert the 417 follow-up commit.

## Out of scope

- Folding `AGENTS.md` §2.1
- Changing `hooks.json` sibling `code-graph-health.sh`
- Mutating live `~/.cursor-governance`
- Starting Neo4j or writing a publish-path breakglass
- Restacking PR 418
- `make campaign`, Program Lock, merge

## Convergence

- **current_state:** `execution_ready`
- **implementation_ready:** `true` (preflight + DAG + envelope filled)
- **executable_when:** CP-01–03 pass; DAG as written
- **complete_when:** SP-01–04 evidence passed; revise/harden/improve ran on the same files; PR 417 URL shown
- **execute_via:** `cursor-build`
- **next_skill:** none after publish
- **broader_work_requires_separate_contract:** `true` (418 restack; §2.1 fold)
