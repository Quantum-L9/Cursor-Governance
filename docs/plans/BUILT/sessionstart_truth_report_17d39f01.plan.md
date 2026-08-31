---
name: SessionStart truth report
overview: Land a truthful SessionStart reporter on the unique open-PR stack tip, close the Claude-projection side door, and keep hardening plus validation as separate /gmp steps so they cannot be skipped or folded into the mutate todos.
todos:
  - id: todo-01-stack-tip
    content: PR_STACK=auto worktree from unique tip 416; abandon origin/main start-session-truth branch
    status: completed
  - id: todo-02-reporter-load
    content: Land runtime reporter with GC/worktree/override resolve; delete GRANT/ITEST/BOOTSTRAP slogans
    status: completed
  - id: todo-03-timeout
    content: Portable run_with_timeout in Claude SessionStart repair; emit failed-log evidence
    status: completed
  - id: todo-04-side-door
    content: Stop claude_projection from setup_workspace_symlinks SessionStart auto-wire
    status: completed
  - id: todo-05-hydrate-heading
    content: "Single ### Graphiti hydrate heading (packet vs bootstrap wrap)"
    status: completed
  - id: todo-06-harden-gmp
    content: "/gmp ENFORCE: tests that fail on slogans, GNU timeout, projection side door, load-path miss"
    status: completed
  - id: todo-07-validate-gmp
    content: "/gmp VALIDATE: worktree hook JSON + targeted pytest; do not claim SSOT changed"
    status: completed
  - id: todo-08-publish
    content: "After validate: authorize-release + PR_STACK=auto PR_REMEDIATE=0 make pr; show PR URL"
    status: completed
isProject: false
---

# SessionStart truth report

Repair Cursor `/start-session` so the live ceremony reports class + evidence, loads the reporter from the path SessionStart actually uses, and stops scoring healthy-defaults and Claude-only receipts as this-session faults. Hardening and validation are **separate later todos** for `/gmp`, not extra lines inside mutate.

**Planning bind (this workspace):** `/Users/ib-mac/Cursor-Governance` on `main` @ `ad28bd83bfac0eb6a4c05a83b06adec019fdbc5c` (dirty WIP deletes ignored). SSOT `~/.cursor-governance` @ `50c5c70`. Hook catalog: [`.pre-commit-config.yaml`](.pre-commit-config.yaml). **No** `Lock: origin/main = <sha>`.

**Execute bind:** unique stack tip `agent/cursor/skill-close-on-resolve` @ `9538b4a25c40f371135e2f1ca358e056ccba7c48` (PR 416 on PR 415 on `main`). **Never** branch from `origin/main`. Do **not** continue [`agent/cursor/start-session-truth`](/Users/ib-mac/.l9/gov-worktrees/cursor__start-session-truth) (it was cut from `origin/main` @ `50c5c70`). Re-apply useful bytes onto a new `PR_STACK=auto` worktree.

`route_plan.py --risk medium --evidence sufficient` → `depth=standard`, `omit_gates=[]`.

## Execute via Cursor Build

Press **Build**. Plan on the current workspace. Execute on the unique open-PR chain tip.

- If any open PR exists: **never** branch from `origin/main`. Start from the unique chain tip (`PR_STACK=auto`). Use `agent_worktree_start.sh` when this checkout is not already that tip. Sibling open-PR chains fail closed.
- If the board is empty: `origin/main` is allowed.
- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a **planning** requirement.
- After Build mutate todos complete: **stop mutating**. Leave harden + validate pending for `/gmp <this-plan.md>`.
- After `/gmp` harden + validate PASS: scoped-commit (pathspecs), `l4_local.py authorize-release`, then `PR_STACK=auto PR_REMEDIATE=0 make pr`. Do not skip `make pr`.
- The finish reply **must** display the opened PR URL as proof.

## Mission

Live `/start-session` still emits slogans (`no publish-path breakglass`, `itest unavailable`, `claude bootstrap: never_ran`) from [`ops/hooks/session_start_bootstrap.sh`](ops/hooks/session_start_bootstrap.sh). Cursor SessionStart does not run `install.sh`, so `never_ran` is the wrong surface. Local Neo4j `:7687` is optional PlasticOS itest, not Graphiti (`:8100`). A missing publish-path grant is healthy.

The hook comment forbids `claude_projection.py`, but [`ops/scripts/setup_workspace_symlinks.sh`](ops/scripts/setup_workspace_symlinks.sh) still runs it on auto-wire (SessionStart side door). Hydrate markdown is wrapped twice (`compile_session_packet.py` already emits `### Graphiti hydrate`). Claude repair uses GNU `timeout`, which is absent on Darwin (`timeout: command not found` in every `~/.l9/claude/bootstrap-repair-*.log`).

In-progress reporter in the old worktree calls `$GC/ops/scripts/session_start_runtime_report.py`. `$GC` is `~/.cursor-governance`. Until that file is on SSOT, the new hook prints `reporter: failed`. Fix the resolve order in the same mutate as the reporter.

## Success properties

- SP-01: Execute HEAD is the unique stack tip (or its child), never a fresh `origin/main` fork while PRs 415/416 are open.
- SP-02: Runtime lines are `ok | n/a | degraded | failed` with named component + evidence. The three slogans are absent from hook source and from a worktree hook run.
- SP-03: Cursor auto-wire does not invoke `claude_projection.py`. Claude projection stays Claude SessionStart / `make claude-install`.
- SP-04: `/gmp` harden + validate PASS on the changed set (`.pre-commit-config.yaml` catalog + targeted pytest). Then `PR_STACK=auto PR_REMEDIATE=0 make pr` and the PR URL is shown.

## Scope

**In**

- [`ops/hooks/session_start_bootstrap.sh`](ops/hooks/session_start_bootstrap.sh) — classify via reporter; drop `GRANT_NOTE` / `ITEST_NOTE` / `BOOTSTRAP_NOTE` slogans; capture Graphiti/wiring/audit stderr; one hydrate heading.
- New [`ops/scripts/session_start_runtime_report.py`](ops/scripts/session_start_runtime_report.py) + tests (reuse worktree bytes, fix load path).
- New [`ops/scripts/lib/run_with_timeout.sh`](ops/scripts/lib/run_with_timeout.sh).
- [`environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh`](environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh) — portable timeout; on repair fail, emit log line; stop GNU `timeout`.
- [`ops/scripts/setup_workspace_symlinks.sh`](ops/scripts/setup_workspace_symlinks.sh) — do not run `claude_projection.py` from Cursor SessionStart auto-wire.
- [`ops/graphiti/hydration/compile_session_packet.py`](ops/graphiti/hydration/compile_session_packet.py) **or** the bootstrap wrap — exactly one `### Graphiti hydrate`.
- Tests: [`ops/scripts/tests/test_session_start_runtime_report.py`](ops/scripts/tests/test_session_start_runtime_report.py), extend [`ops/scripts/tests/test_cursor_shared_bootstrap_edge.py`](ops/scripts/tests/test_cursor_shared_bootstrap_edge.py), [`tests/environment/adapters/test_session_start_refresh_guard.py`](tests/environment/adapters/test_session_start_refresh_guard.py).

**Out**

- Folding or rewriting [`AGENTS.md`](AGENTS.md) §2.1 (additive_only). Existing fragment `CURSOR_SESSIONSTART_NO_CLAUDE_CLOUD_V1` stays; do not add a second doctrine dump.
- Starting local Neo4j or writing a publish-path breakglass.
- Running `install.sh` from Cursor SessionStart.
- Changing `hooks.json` sibling `code-graph-health.sh` (leave as parallel skip on non-PlasticOS).
- Mutating `~/.cursor-governance` except by merge + activate.
- `make campaign`, Program Lock, merge.

## DAG (Build mutate, then /gmp)

```text
todo-01-stack-tip
    → todo-02-reporter-load
    → todo-03-timeout
    → todo-04-side-door
    → todo-05-hydrate-heading
    → todo-06-harden-gmp          ← /gmp ENFORCE only
    → todo-07-validate-gmp        ← /gmp VALIDATE only
    → todo-08-publish
```

### todo-01-stack-tip (preflight)

`bash "$HOME/.cursor-governance/ops/scripts/agent_worktree_start.sh" --agent-id cursor --task-id session-start-truth` with default `PR_STACK=auto`. Confirm `HEAD` parent is `9538b4a` chain tip, not `50c5c70`/`ad28bd83`. Cherry-pick or copy reporter/timeout files from the abandoned worktree; do not keep that branch as execute HEAD.

### todo-02-reporter-load (mutate)

Land the classifier. Resolve the reporter in this order: `L9_SESSION_RUNTIME_REPORT` override, then `$CURSOR_PROJECT_DIR/ops/scripts/session_start_runtime_report.py` when that file exists (ssot_checkout / feature worktree), then `$GC/ops/scripts/session_start_runtime_report.py`. Delete live slogan assignments. Runtime + `### Degraded` list only `degraded`/`failed` items with evidence (repair log text, errno, health stderr). Cursor: `claude-adapter: n/a`; Claude repair failure is `claude-adapter-repair` in Degraded, not this-surface `never_ran`.

### todo-03-timeout (mutate)

Replace GNU `timeout` in the Claude SessionStart hook with `run_with_timeout`. On installer fail, append `FAILED rc=…` plus the first log lines. Update [`test_session_start_refresh_guard.py`](tests/environment/adapters/test_session_start_refresh_guard.py) so it asserts `run_with_timeout` before `bash "$installer"` before the attempt marker.

### todo-04-side-door (mutate)

Remove or Claude-surface-gate the `claude_projection.py` block at the end of `setup_workspace_symlinks.sh`. SessionStart auto-wire must not write `~/.l9/claude/projection-receipt.json`. Extend `test_cursor_shared_bootstrap_edge.py` (or a sibling test on `setup_workspace_symlinks.sh`) so Cursor SessionStart’s wire path cannot call `claude_projection.py --root`. `make claude-install` / Claude SessionStart remain the owners.

### todo-05-hydrate-heading (mutate)

Keep one `### Graphiti hydrate`. Prefer stripping the heading from the orchestrator payload and letting the bootstrap wrap, or stop wrapping if the packet already has the heading. Do not run hydrate twice.

### todo-06-harden-gmp (/gmp ENFORCE — do not run during Build mutate)

`/gmp` this plan after mutate todos are committed on the stack-tip branch. Add/keep tests that fail if slogans return, if the hook calls GNU `timeout` for repair, if `setup_workspace_symlinks.sh` still invokes projection on the Cursor wire path, if reporter resolve ignores the worktree file, if `scratch_hold.py` / `ensure_uv` leak back into the Cursor hook. No new behavior. Delete leftover comments (“reconcilers: plugins, IDE, cold venv”) only if they are false.

### todo-07-validate-gmp (/gmp VALIDATE — do not run during Build mutate)

`/gmp` continue. Evidence, not exit-0:

1. Worktree hook: `CURSOR_PROJECT_DIR=<wt> bash <wt>/ops/hooks/session_start_bootstrap.sh` stdout is one JSON object; `additional_context` has `### Runtime` / `### Degraded`; lacks the three slogans; `publish-path: ok`; `itest/neo4j: n/a` with `Errno 61` (or live probe text); `claude-adapter: n/a`.
2. `pytest` on `ops/scripts/tests/test_session_start_runtime_report.py`, `ops/scripts/tests/test_cursor_shared_bootstrap_edge.py`, `tests/environment/adapters/test_session_start_refresh_guard.py`.
3. Confirm `make -C "$HOME/.cursor-governance" start` still uses SSOT until this PR merges — do not claim SSOT changed.

### todo-08-publish

Only after todo-07 PASS: `l4_local.py authorize-release` then `PR_STACK=auto PR_REMEDIATE=0 make pr`. Display the PR URL.

## Envelope

- **write_allow:** `ops/hooks/session_start_bootstrap.sh`, `ops/scripts/session_start_runtime_report.py`, `ops/scripts/lib/run_with_timeout.sh`, `ops/scripts/tests/test_session_start_runtime_report.py`, `ops/scripts/tests/test_cursor_shared_bootstrap_edge.py`, `ops/scripts/setup_workspace_symlinks.sh`, `ops/graphiti/hydration/compile_session_packet.py`, `environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh`, `tests/environment/adapters/test_session_start_refresh_guard.py`, `docs/plans/` (this plan + PLAN_DOCUMENT JSON only).
- **write_deny:** `AGENTS.md` body fold, `CANONICAL_LAW.md`, secrets, `hooks.json` sessionStart list, `~/.cursor-governance` live tree, unrelated WIP.
- **deny:** `make campaign`, merge, force-push, `install.sh` from Cursor SessionStart, starting Neo4j, writing a breakglass.

## Stress / leverage

- Disconfirm: Does `make start` still run the SSOT hook and hide the worktree reporter? (Yes until merge — tests must run the worktree hook file.)
- Disconfirm: Does gating projection in `setup_workspace_symlinks.sh` break `make claude-install`? (Must not; only SessionStart/auto-wire.)
- Disconfirm: Do two open PRs make this a sibling? (No — unique chain 415←416.)
- Assumed false if: Darwin gains GNU `timeout`; local Neo4j appears and we still call it n/a without probing.
- Blast radius: SessionStart additional_context; Claude repair on Desktop; consumer auto-wire.
- Rollback: revert the stacked PR; SSOT hook copy heals from previous tip; leave `~/.l9/claude/bootstrap-repair-*.log` on disk.
- Leverage order: load-path + slogans (shared cause: SessionStart scores the wrong surface) → side door → timeout → heading → harden tests → validate live hook.

## Doc / root surface

- `AGENTS.md`: **n_a** fold. Do not rewrite §2.1.
- `CLAUDE.md`: **n_a**.
- `commands/start-session.md`: **n_a** unless the STATE_SYNC table still names the old slogans as required checks (then append-only one line pointing at `### Runtime` / `### Degraded`).

## /gmp handoff

- **may_modify:** files in write_allow.
- **must_not_modify:** `AGENTS.md` existing lines, `CANONICAL_LAW.md`, live SSOT clone, `hooks.json` sessionStart entries.
- **preserved_contracts:** Cursor SessionStart does not run `claude_projection.py` or `install.sh`; scratch_hold/uv stay in `bootstrap_agent_environment.sh`; fail-open SessionStart (exit 0); T-CI007/T-CI015/T-CI021/T-CI022 still *declare* grant/itest/skill-log — they just stop using fault slogans.
- **validation_commands:** worktree hook JSON parse; targeted pytest above; `.pre-commit-config.yaml` on the changed set.

## Convergence

`status: partial`. Implementation not run. Next skill after Build mutate: **`/gmp`** this plan for todo-06 then todo-07. Then publish. Do not chain `/ynp` as a substitute for `/gmp`.
