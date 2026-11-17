# CTO runbook: execute, converge, merge, verify

## Phase 0 — bootstrap and source bind (CTO only)

1. Invoke `/lcto` in the Core workspace. Resolve real `mode: ACTIVE` plus all required projections. If BLOCKED, stop unverified coordination claims. Read current swarm v2 `MODE.yaml` and `/lcto` instructions; this pack is not authority.
2. Bind exact `l9-ci-core/main` HEAD and event SHA, current `.github` registry and protection evidence, existing `l9-ci-sdk` compatibility, exact `Cursor-Governance` publication/merge sources. Compare to `SOURCE_EVIDENCE.md`. GitHub connector has confirmed public visibility of three repositories on 2026-11-17; recheck actual runner access instead of presuming it eliminates every CI secret dependency.
3. Inspect open Core PRs for overlapping work, branch protection and real green required-context names. If overlapping pending changes are material, park/stack them rather than double implementing.
4. Collect **three** representative pre-change required PR run timestamps/costs if accessible; record missing metrics `UNKNOWN`, not a fabricated baseline. Inventory current test-discovery count and critical gate modules. Freeze exact per-job PR-fast case selection, each critical witness, and deep suite discovery. Record why `Unit tests` does not duplicate `Repository contract` unnecessarily. Name genuine overlap explicitly if protective.
5. Decide ordinary choices; if an exact authority-reserved decision remains, batch it once before launch. Lock file ownership and exception list. In particular, Core policy requires any Repo.mk PR to include `tests/repo_execution/`, `AGENTS.md` and `docs/repository-execution-runtime.md` changes; all belong to A. Confirm `MANIFEST.sha256` is retired, never recreate it for this campaign. Do not ask the operator to supervise agent coordination.

## Phase 1 — launch one fixed pool, all lanes active

1. Size pool to current parallel-safe lanes, max five, and launch in the *same bootstrap sitting*. Use the real `cto_mode.py launch-spec` and verbatim `child-prompt`; never handwrite child system prompt.
2. In Claude Code cloud: `.github` is every session's `source_url`; attach Core push and Cursor-Governance read, plus lane-specific read-only repositories, before role registration; do not `add_repo` `.github`. On Cursor, child already has a local checkout and uses host Task continuation. The public visibility change does not override protocol or permission preconditions.
3. Ensure each child registers role and reports `/coding-agent` MODE `ACTIVE` and projection bundle revision in its first `CTO-STATUS`. No GATE if BLOCKED. CTO reads child transcripts for reports and questions; children may not cross-session-message.
4. Dispatch A–E simultaneously. Each brief in `lanes/` is the **task brief**, not the child's system prompt. Every brief has explicit no-overlap paths, a single branch/worktree and authority boundaries.

## Phase 2 — parallel development and PR handoffs

- Read status from each child's transcript. Answer `CTO-QUESTION` yourself when within settled scope. An answer that changes scope is sent as interrupting `CTO DIRECTIVE` to the owning child.
- Each child edits only owned paths and satisfies its own changed-file companion rules **within its own PR** (A includes the mandatory Repo.mk test+docs; B includes workflow tests), runs its local focused checks, commits and opens/updates PR through the current governed publication route once its dependency base is ready. CTO must verify the actual SSOT and current `make pr` transport before issuing an executable instruction; the published artifact is a PR, not a guessed shell transcript.
- Each child monitors **its own** PR to current-head CI green and resolves real review findings, conflicts and comments. Any blocked cross-lane bug is reported, not patched in a second lane.
- When A's branch is available, CTO issues exact-base GATE to B. Once B is available, CTO may GATE **C and D in parallel as siblings** when their implementations depend on B; do not force D to wait for C. If C does not depend on B, CTO may select an earlier proven base. No branch is rebased or force-pushed. No false independence claim if a test assumes its predecessor. A's PR may still incur the old full `Unit tests` workload and must not be advertised as the completed speed optimization.

## Phase 3 — CTO-only combined integration

1. Resolve current heads, each PR diff and dependency graph. Create disposable **CTO-only** integration checkout/worktree; compose the stack using supported merge mechanics that do not force rewrite any agent branch.
2. Personally execute Core's verified current target validation, focused regressions, and **full discovery once on the combined candidate**. Do not delegate integration tests. Confirm expected nonzero exits for failing fixtures and zero for known-good. Verify scheduled workflow YAML triggers and exact main-ref binding, check-name uniqueness and all four make-v1 phases.
3. Inspect `tests/**/test_*.py` census; deep must run full corpus, subject to the actual unittest discovery semantics (not every glob file is automatically discoverable). Keep the existing collectability guard effective. Explicitly map any moved test to fast or deep; no disappearing tests. Benchmark fast vs old measurements; note actual number of runner minutes and wall-clock, not a target as proof.
4. If integration fails, route `CTO REMEDIATE <PR>` to exact file owner, citing failing test and head. CTO does **not** edit or push a lane PR branch. Recompose after correction. Never call an integrated candidate green because four isolated PRs were green.
5. Inspect Core special risk: `main` IS the org-wide CI runtime. Ensure fast mandatory tests still cover CI enforcement and SDK handoffs; ensure Core self-CI context and rulesets are unchanged.

## Phase 4 — authorize and land in dependency order

- For each PR verify current head SHA, blocking check conclusions, review threads, mergeability, code-owner obligations and integrated revision. Collect the exact operator merge grant that the current merge gate requires. The user authorized campaign/PR publication, **not unknown future merges**.
- CTO runs authorized merges personally via the governed, stack-safe mechanism and preserves ancestry under open stacked children. Children never merge. For each landed parent, refresh/retarget/recheck children and refresh exact SHAs before next merge authorization; never reuse a stale grant.
- If operator authority is unavailable, stop merging at `MERGE_PENDING`, with each prepared PR/HEAD coordinate; continue any independent non-merge work. Do not prompt for a generic blanket grant. Do not substitute automation or an agent decision.

## Phase 5 — live proof and closeout

- Once all Core changes land: verify the required PR checks **actually** evaluate fast coverage at a new test PR or representative merged PR (record exact head/run URL), not merely that YAML looks right.
- The new nightly scheduled workflow is only registered once on Core main. Manually dispatch it on Core main if available, confirm that it runs full suite, captures immutable head and fails when an actual test fails; record the run URL and artifact. The **first actual scheduled 07:17 UTC run** separately verifies the clock. Until then leave `PENDING_SCHEDULED_PROOF` and do not label scheduler proven.
- If deep fails after merges, CTO opens a bounded remediation lane and directs an idle pool agent to repair in Core under existing scope/authorization. No direct CTO patches. If full suite is not green, the implementation is not verified. If manual deep passes but the first cron has not fired, report `IMPLEMENTED_AND_MANUAL_DEEP_PROVEN` with `SCHEDULED_PROOF_PENDING`, not a fully observed daily schedule.
- Produce final table of PRs, exact integrated SHA, required checks, fast vs nightly test counts, CI walltime and runner minute delta, unresolved blockers, and admitted/unknown assurance. Archive/transfer the fixed pool under current CTO mode handoff rules.

## Fallback and change control

Do not broaden Core pilot to consumers or redefine `.l9/repo-workflow.json`. The safe rollback, if new Core main causes fleet failure, is a separately authorized Core corrective PR or the control-plane's documented safe revert mechanism, never unauthorized force pushes. An unverified org rule or broken SDK setup is a blocker for claims requiring it, not grounds to weaken enforcement.

## Evidence ledger for every CTO checkpoint

Capture: (1) exact repo baseline SHA and relevant authoritative file blob SHAs, (2) CTO session/child identifiers and ACTIVE-mode receipts, (3) per-PR branch/base/head/file delta and companion tests, (4) selected and full test counts plus commands actually exercised, (5) CI run URLs and check conclusions on each current head, (6) combined temporary integration revision and tests run by CTO, (7) per-merge human grant and resulting main SHA, (8) post-merge manual deep run, (9) first scheduled run or pending marker, (10) measured delta or UNKNOWN.

**Priority of evidence:** a test run on an unmerged PR or a synthetic fixture is not a live default-branch scheduled-run receipt. A checked-in ruleset JSON file is not proof of the installed GitHub ruleset. A public repository flag is not an authenticated runner read test.

**Reconciliation:** for every confirmed deviation, name the exact root cause and owning lane before `CTO REMEDIATE`. Child edits only its paths. The CTO does not patch lane branches, does integration personally, and never claims completion on cross-PR green statuses alone.
