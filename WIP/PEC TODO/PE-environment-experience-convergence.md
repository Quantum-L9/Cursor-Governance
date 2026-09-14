# PE — Environment Experience Convergence

Target: Quantum-L9/Cursor-Governance

## Context

The environment-experience improvement pack (`WIP/8-26-26/environment_experience_improvement_pack_p307/`)
was re-assessed on 2026-08-27 against `main@498dcaa`: **3 done · 14 partial · 19 not started** of 36
records. This campaign converges **everything still open** — every not-started record and every named
residual on a partial record.

"Converge" means each record ends in one of exactly two states, and never in ambiguity:

1. **Built** — implemented in this repository, with the record's own `done_when` verified.
2. **Formally classified** — declared `blocked_on: external` or `blocked_on: out_of_session_scope`
   with the owning surface named, via a first-class progress-schema class. A record whose target this
   repository does not own is not "not started"; recording it as such is the defect this campaign
   also fixes.

Fabricating work on an unreachable surface is forbidden. So is silently dropping it.

### Known-unreachable surfaces (classify, never fake)

- **Harness-owned** — `CI-001` IMP-01 (Anthropic session prompt), `CI-003` named target
  (the harness stop hook under `/root/.claude/`), `CI-011` (GitHub MCP server), `CI-013` IMP-10
  (harness tracker), `CI-020` (`ReadNotifications` envelope). Each has an in-repo lever or none;
  where a lever exists it is in scope and named below.
- **Repository not attached to this session** — `Cognitive.Engine.Graphs` is absent from the session
  scope list, so `CI-017` IMP-B1 / I-WT-03, `CI-018` IMP-001, `CI-022`, `CI-023` IMP-002/005/006 and
  `CI-024` cannot be built here.
- **Externally blocked on infrastructure** — `CI-010`'s CONNECT leg has no platform-issued session
  identity (issues #301, #302). Its diagnosability leg is in scope.

## Program ordering

1. Release A — Merge-verb transport, so merge authority survives a GraphQL-restricted session
2. Release B — Ownership-aware writes across every projection write site
3. Release C — Receipt integrity and lifecycle invalidation
4. Release D — One environment and toolchain authority
5. Release E — Capability-gated rules, actionable gate denials, local CI parity
6. Release F — Publish path, checkout authority, and writer coordination
7. Release G — Memory transport truth and continuity
8. Release H — Blocked-record classification and pack self-validation

## Release A — Merge-verb transport

Commit `5612f6b` gave the stack probe in `ops/autonomy/merge_gate.py` a REST transport. The merge
*verb* never got one: `ops/autonomy/stack_safe_merge.py` execs the GraphQL-backed CLI merge
subcommand, which 403s on this session gateway, so an authorized merge cannot execute.
`ops/autonomy/merge_gate.py` recognises a merge only by matching the literal CLI words, so a REST
merge is **not gated at all** — verified: `_command_is_pr_merge` returns False for
`gh api --method PUT repos/{o}/{r}/pulls/{n}/merge`. The transport fix and the gate's recognition of
it must land together or the gate develops a hole exactly where the fix sends traffic.

- Give `stack_safe_merge.py` a REST execution path (`PUT /repos/{owner}/{repo}/pulls/{n}/merge`),
  keeping the CLI subcommand as the fallback, mirroring the probe's two-transport shape.
- Teach `merge_gate.py` to recognise the REST merge form so every merge stays gated. Preserve
  fail-closed behaviour exactly; widen only how the command is recognised.
- Recognition must key on effect, not spelling — and the defect is in the **PreToolUse shell gate**
  (`ops/autonomy/local_execution_gate.py`), not in `merge_gate.py`. Measured: `merge_gate`'s
  `_command_is_pr_merge` correctly returns False for a heredoc body quoting the verb and False for a
  prose mention, and True for real and wrapped invocations. The shell gate fronting it does not strip
  heredocs, so authoring this very brief was denied twice for quoting the command in documentation
  prose. Fix the coarse matcher at the shell-gate layer; do not loosen `merge_gate`.
- Tests: the gate recognises and gates a REST merge; a receipt-less REST merge is denied; transport
  fallback is exercised; merge-method selection is unchanged.

## Release B — Ownership-aware writes

`is_tracked()` guards exactly one write site. Four more replace repository-owned trees.

- Apply the guard before the writes in `claude_projection.py` (`.mcp.json`),
  `reconcile_claude_l9_skills.py`, `reconcile_claude_commands.py`, `reconcile_claude_settings.py`.
- Phase 2b — project to a non-owned sibling when the target is tracked.
- Phase 2d — per-repo gitignore propagation.
- `CI-003` in-repo lever — add `.claude/**` and `.mcp.json` to the `.git/info/exclude` glob list in
  `ops/scripts/bootstrap_agent_environment.sh`, which `--exclude-standard` already honours. Classify
  the harness-owned hook itself.
- `CI-031` — correct the stale pre-commit hook count in `l9-ci-sdk/CLAUDE.md` (states two, config
  declares nine) and add a guard against case-only duplicate tracked paths.
- Verify the pack's 8-fixture `git status` clean acceptance.

## Release C — Receipt integrity

Live defect: `bootstrap-state.json` is pinned to `governance_revision c3081ee` while
`gov-refresh.json` and `readiness-receipt.json` carry `498dcaa`, inside one session, with nothing
invalidating the stale one.

- `CI-004` — regenerate the bootstrap receipt on container/session lifecycle and on governance
  revision change; invalidate stale receipts; re-probe DEGRADED components; retain per-component
  reason, evidence and log path. Deps already has per-component logs; the other components do not.
- `CI-035` — cross-check `governance_revision` across every receipt under `$HOME/.l9/claude` and
  report disagreement as a named readiness dimension.
- `CI-030` — give the receipt CLIs a default read action without multiplying state owners.

## Release D — One environment and toolchain authority

- `CI-006` — trace each effective value to its source, separate authority-widening from cosmetic
  drift, make repair reachable or explicitly human-only, record the governing value. Reach the
  exact-one-layer end state for the stray autonomous-merge environment boolean (present, valued
  `false`).
- `CI-023` — one loader/precedence contract that works in non-interactive shells, fails fast on
  missing required configuration, and guards source-without-call misuse of
  `resolve_governance_paths.sh`. State in rule 06 that the resolver must be *called*, not merely
  sourced.
- `CI-027` — correct rule 03's stale rationale: it claims system `python3` often lacks PyYAML; on
  this container `import yaml` succeeds. Preserve the pinned-interpreter requirement.
- `CI-028` — emit a real exit status for the session-deps stage and timestamp its logs.
- `CI-009` residual — add an import smoke to `session_deps_cloud.sh` so "toolchain ready" means the
  environment imports, matching the readiness dimension already merged.

## Release E — Capability-gated rules and actionable denials

- `CI-012` — reconcile rule 22 with the MCP servers a surface actually exposes (this surface exposes
  no Context7 server), and annotate projected always-on rules with capability preconditions while
  preserving rule intent.
- `CI-013` in-repo legs — surface hook stderr on gate faults, report which stage of a compound
  command was refused, and give the gates an escape channel an agent can actually reach or delete the
  escapes from the rules. Preserve every fail-closed destructive invariant.
- `CI-025` — sanctioned, permission-safe cleanup of generated and cache residue that does not weaken
  general destructive-command policy.
- `CI-018` in-repo legs — install hooks as first-class provisioning and define one local CI-parity
  command whose blocker list matches remote CI.
- `CI-017` in-repo leg — validate generated-artifact membership and report all drift in one pass.

## Release F — Publish path, checkout authority, coordination

- `CI-008` — enable and verify the consumer-workspace leg of the governance pre-commit path, scoped
  in `run_pr_precommit.sh` lines 28-32 but never enabled. Use an attached consumer repo as the proof.
- `CI-014` — make the target repository explicit for governance CLIs instead of depending on
  persistent shell cwd.
- `CI-015` — relabel or remove the non-authoritative governance clone, and name both revisions in the
  session banner when more than one tree is present.
- `CI-016` — resolve the L4 receipt's `pr_template` against the released repository rather than the
  hardcoded root template name, and make stale SHA/branch bindings visible before they block a
  publish.
- `CI-019` — coordinate concurrent writers on shared PR head branches before push.
- `CI-021` — fix the skill-usage logger matcher and prove logging reaches disk; the expected log
  directory under `/root/.claude/l9/` does not exist.

## Release G — Memory transport truth and continuity

- `CI-005` — split the memory component into independently probed transports instead of one collapsed
  verdict; base the CLI verdict on `graphiti_memory_client.py health`; distinguish nothing-to-write
  from failed-to-write; count facts that are not self-referential PICKUP restatements so an empty
  hydration is visibly empty; enumerate skipped repositories with per-repository reasons; write a
  task-bearing completion PICKUP carrying task, branch, head SHA and next action.
- `CI-010` diagnosability leg — split broker states into DNS/unreachable, proxy-denied and
  upstream-error so allowlist remediation is decidable. CONNECT stays externally blocked.

## Release H — Blocked-record classification and pack self-validation

- Add `blocked_on` to the progress schema as a first-class class (`external`,
  `out_of_session_scope`), reported as its own count so "not started" means "startable and not
  started". Classify every record named unreachable above, naming the owning surface.
- `CI-034` — bind the overlay to a governance SHA and report itself stale when read at a different
  revision. The overlay went stale across 47 commits with nothing flagging it.
- Add a validator for the pack: YAML parse, per-record agreement between `improvements.yaml` and
  `progress.yaml`, declared counts equal the recomputed tally, and every artifact stating counts
  agreeing. `.pre-commit-config.yaml` excludes `WIP/`, so a green gate proves nothing about these
  files today.
- `CI-029` — confirm whether `tests/corpus_fixtures.py` is I-WT-04's builder (`build_corpus.mjs` is
  absent; six formats where the record names eight) and close or reclassify.
- `CI-032` — give the slowest validation unit explicit headroom in `l9-meta-injector` without
  weakening aggregate proof.
- `CI-100`, `CI-101`, `CI-102` — resolve or classify. `CI-101` is reproducing live: one branch
  directive is issued identically across all ten in-scope repositories. `CI-102` records that the
  gh-dependent gates now work by a third route (REST-capable probes) that no rule or profile states.

## Final architectural judgment

The pack's 36 records are not 36 unrelated defects. They are a small number of root causes observed
from many angles, and the largest is this: **automation in this environment reports state it did not
measure, and treats content it does not own as its own.** Coarse `READY`/`DEGRADED` verdicts hide
transport-specific truth; receipts outlive the revision they describe; projection replaces tracked
repository trees; a gate recognises a command by its spelling rather than its effect; and a progress
overlay restates counts no validator checks.

It is:

one convergence program that makes ownership and measurement explicit at every write, every
receipt, every gate, and every status claim — and that classifies what this repository cannot reach
instead of leaving it indistinguishable from work nobody has started.
