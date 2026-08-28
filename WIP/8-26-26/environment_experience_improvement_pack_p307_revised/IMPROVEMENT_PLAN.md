# Improvement Plan — Current Forward Work (revision r2)

Bound to **main@59f03a5d** (`59f03a5d4460b939360bc2fd5dd85239d47416a5`). Only the 27-record active queue is scheduled.
Completed, external-blocked and unverifiable records are retained in `PROGRESS.md` and
`progress.yaml` with full lineage, and are not scheduled again.

> The `**Status:**` line on each entry below is the record's roadmap classification at pack
> generation and is historical. Delivery state lives in `PROGRESS.md` / `progress.yaml` and is
> authoritative. Three records changed status in this revision — **CI-007** and **CI-026** were
> `done` and are not (CI-007 is now scheduled first), and **CI-003** was `not_started` and is
> partial. Read the overlay before scheduling any entry here.

## Execution order — 4 lanes, makespan 11

Weighted DAG list-schedule; supersedes the six wave barrier model. Total effort 42 units over 26 execution units, critical path 6 (`CI-004 → CI-005`), saturating at 7 lanes. Entries below are in start order; `[start-end]` are effort units, not days.

### 1. CI-004 — Regenerate bootstrap receipts on lifecycle/revision changes and re-probe degraded components

**Lane L0** `[0-3]` &nbsp;·&nbsp; **effort 3** &nbsp;·&nbsp; **Priority band:** 0 &nbsp;·&nbsp; **Class:** P0_EXECUTION_UNBLOCKER  
**Blocker:** VALIDATION_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 2 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **partial**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-006, CI-007, CI-009, CI-012, CI-028, CI-102

Bind receipts to container/session lifecycle and governance revision; invalidate stale receipts; re-probe DEGRADED components; retain per-component reason, evidence, log path, and retry/remediation state.

**Remaining at this binding:**

- IMP-03 / I-BF-01: treat a governance_revision mismatch as expiry, distinct from TTL expiry.
- IMP-04 / BOOT-1: re-probe DEGRADED components at session start rather than serving a day-old verdict, under the repo-write lock, fail-soft.
- I-BF-03 / IMP-10 / B5: a reason string and log path per degraded component. The deps stage already has log files; the other five components have nothing.

**Sources:** P1/improvements/IMP-10, P3/improvements/B5, P4/improvements/IMP-03, P4/improvements/IMP-04, P6/improvements/BOOT-1, P7/improvements/IMP-07, P8/improvements/I-BF-01, P8/improvements/I-BF-02, P8/improvements/I-BF-03, P9/improvements/I-BS-04

### 2. CI-012 — Gate rules and MCP config on actual surface capabilities

**Lane L1** `[0-3]` &nbsp;·&nbsp; **effort 3** &nbsp;·&nbsp; **Priority band:** 1 &nbsp;·&nbsp; **Class:** P1_ROOT_REPAIR  
**Blocker:** AUTHORITY_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 6 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **partial**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-004, CI-006, CI-007, CI-009, CI-028, CI-102

Validate MCP config schema before session start and annotate projected rules with capability preconditions when their mechanism is unavailable, while preserving the rule intent.

**Remaining at this binding:**

- IMP-07: extend rule 22 with the server-absent case and name the required fallback, so the obligation stays closable.
- I-BS-12: declare a capability precondition per rule and annotate at projection time when it is unmet.

**Sources:** P4/improvements/IMP-07, P9/improvements/I-BS-03, P9/improvements/I-BS-12

### 3. CI-007 — Replace standing breakglass environment strings with scoped expiring receipts

**Lane L2** `[0-2]` &nbsp;·&nbsp; **effort 2** &nbsp;·&nbsp; **Priority band:** 0 &nbsp;·&nbsp; **Class:** P0_EXECUTION_UNBLOCKER  
**Blocker:** AUTHORITY_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 1 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **partial**  
**Depends on:** none &nbsp;·&nbsp; **Collides with:** CI-015 &nbsp;·&nbsp; **Runs alongside:** CI-004, CI-009, CI-012, CI-028

Represent exceptional publish authority with issuer, reason, scope, issuance time, expiry/consumption semantics, and session-start visibility; do not normalize a one-time grant into silent permanent configuration.

**Remaining at this binding:**

- IMP-04 / ENV-2: remove the standing variable from the account environment, or replace its value with one that describes an actual standing policy.
- I-EL-06: express breakglass as a receipt with issuer, scope and expiry, and report any grant still in force, with its age, in the session-start banner.

**Sources:** P1/improvements/IMP-04, P6/improvements/ENV-2, P9/improvements/I-EL-06

### 4. CI-009 — Establish one project interpreter/toolchain authority and verify importability before READY

**Lane L3** `[0-2]` &nbsp;·&nbsp; **effort 2** &nbsp;·&nbsp; **Priority band:** 0 &nbsp;·&nbsp; **Class:** P1_ROOT_REPAIR  
**Blocker:** VALIDATION_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 3 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **partial**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-004, CI-007, CI-012

Resolve the project interpreter/venv deterministically, pin checker versions to the same authority, export durable PATH/PYTHONPATH only through one loader, and make readiness end with repository import/command smoke tests.

**Remaining at this binding:**

- I-EL-05: end the deps pass with an import smoke on the resolved interpreter; record interpreter path and version in the log.

**Sources:** P2/improvements/IMP-E1, P2/improvements/IMP-E2, P2/improvements/IMP-E3, P3/improvements/A2, P3/improvements/A3, P3/improvements/A4, P3/improvements/A5, P5/improvements/IMP-003, P5/improvements/IMP-008, P7/improvements/IMP-04, P9/improvements/I-EL-05

### 5. CI-028 — Improve dependency provisioning evidence and determinism

**Lane L3** `[0-2]` &nbsp;·&nbsp; **effort 2** &nbsp;·&nbsp; **Priority band:** 2 &nbsp;·&nbsp; **Class:** P1_ROOT_REPAIR  
**Blocker:** VALIDATION_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 4 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **not_started**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-004, CI-007, CI-012

Use constraints or equivalent deterministic dependency resolution, timestamp dependency logs, and make the provisioning step emit a real exit status/readiness result.

**Remaining at this binding:**

- I-EL-03(P8): write the deps step's exit code into the stamp or the log's final line, and timestamp the log.
- BOOT-5 constraints-file half depends on a consumer repo lock export — out of tree at this binding.

**Sources:** P6/improvements/BOOT-5, P8/improvements/I-EL-03

### 6. CI-006 — Resolve authority-sensitive environment drift at the actual source

**Lane L2** `[2-4]` &nbsp;·&nbsp; **effort 2** &nbsp;·&nbsp; **Priority band:** 0 &nbsp;·&nbsp; **Class:** P1_ROOT_REPAIR  
**Blocker:** NONBLOCKING &nbsp;·&nbsp; **Leverage rank:** 8 of 27 &nbsp;·&nbsp; **Status:** OPEN_DECISION → **partial**  
**Depends on:** CI-007 &nbsp;·&nbsp; **Runs alongside:** CI-004, CI-005, CI-010, CI-012, CI-102

Trace each effective value to its source, separate authority-widening drift from cosmetic drift, make repair reachable or explicitly human-only, and record the governing value. The intended AUTONOMOUS_MERGE value remains an open decision.

**Remaining at this binding:**

- I-EL-02: name the file that produced the live value when a variable drifts.
- A1 / I-EL-03: classify authority-widening drift separately from cosmetic drift, and either apply the expected value or state plainly that repair is human-only.
- A1 second clause: have merge_gate record the effective value it read into the merge receipt.

**Closed legs (retained, not scheduled):**

- IMP-03, ENV-1, IMP-03(P7): the instance is closed. Zero drift, one layer.

**Sources:** P1/improvements/IMP-03, P3/improvements/A1, P4/improvements/IMP-08, P6/improvements/ENV-1, P7/improvements/IMP-03, P8/improvements/I-EL-01, P8/improvements/I-EL-02, P9/improvements/I-EL-03

### 7. CI-102 — Valid GH_TOKEN or formal surface exemption from gh-dependent gates

**Lane L3** `[2-4]` &nbsp;·&nbsp; **effort 2** &nbsp;·&nbsp; **Priority band:** 4 &nbsp;·&nbsp; **Class:** P1_ROOT_REPAIR  
**Blocker:** AUTHORITY_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 10 of 27 &nbsp;·&nbsp; **Status:** ACTIVE_CONTEXT_SPECIFIC → **partial**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-004, CI-005, CI-006, CI-010, CI-012

(a) provision openclaw PAT per rule 62 via secret plane; or (b) amend surface_profile + rules 53/62 to sanction MCP path for claude-cloud

**Remaining at this binding:**

- Record the REST route as a sanctioned surface capability in ops/autonomy/surface_profile.yaml and rule 62, or provision the PAT. Until then the next gh-dependent gate reproduces the original block.

**Sources:** P6/improvements/ENV-3

### 8. CI-005 — Make memory health transport-specific and continuity task-bearing

**Lane L0** `[3-6]` &nbsp;·&nbsp; **effort 3** &nbsp;·&nbsp; **Priority band:** 1 &nbsp;·&nbsp; **Class:** P2_INTEGRATION_AND_RELIABILITY  
**Blocker:** USABILITY_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 7 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **not_started**  
**Depends on:** CI-004 &nbsp;·&nbsp; **Runs alongside:** CI-006, CI-008, CI-010, CI-013, CI-023, CI-030, CI-102

Use one authoritative probe per memory transport, distinguish nothing-to-write from failed writes, write a task-bearing completion PICKUP, prioritize the target repo in hydration, and name skipped repos/empty state explicitly.

**Remaining at this binding:**

- I-BS-05: split the receipt's `memory` component into memory.cli and memory.mcp, probed independently, with the CLI verdict based on graphiti_memory_client.py health rather than broker reachability.
- I-BS-06 / IMP-09(P7): count facts that are not self-referential PICKUP restatements and surface that number, so a hydration carrying no task state is visibly empty rather than apparently successful; record a reason code in the writeback receipt so nothing-to-write is distinguishable from failed-to-write.
- BOOT-4: write a task-bearing completion PICKUP at contract end (task, branch, head SHA, next action) instead of re-ingesting the generic resume pointer as a fact.
- IMP-09(P1) / IMP-05(P4) / BOOT-7: order hydration by the session's declared repo scope before applying the cap, and have the banner enumerate every discovered repository as hydrated or skipped, with a per-repo reason.

**Sources:** P1/improvements/IMP-09, P4/improvements/IMP-05, P6/improvements/BOOT-2, P6/improvements/BOOT-4, P6/improvements/BOOT-7, P7/improvements/IMP-09, P9/improvements/I-BS-05, P9/improvements/I-BS-06

### 9. CI-010 — Make broker authentication and reachability diagnosable

**Lane L1** `[3-4]` &nbsp;·&nbsp; **effort 1** &nbsp;·&nbsp; **Priority band:** 0 &nbsp;·&nbsp; **Class:** P2_INTEGRATION_AND_RELIABILITY  
**Blocker:** INTEGRATION_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 9 of 27 &nbsp;·&nbsp; **Status:** ACTIVE_WITH_UNKNOWN → **partial**  
**Depends on:** CI-004 &nbsp;·&nbsp; **Runs alongside:** CI-005, CI-006, CI-102

Ensure CLAUDE_SESSION_JWT is issued or its absence is a hard named prerequisite failure; split broker states into DNS/unreachable, proxy-denied, and upstream-error before deciding allowlist remediation.

**Remaining at this binding:**

- I-EL-02: report proxy-denied and upstream-error as distinct probe states, so an allowlist remediation decision has something to decide on.
- IMP-05 / I-EL-01: identity provisioning is external and tracked in #301/#302.

**Sources:** P1/improvements/IMP-05, P9/improvements/I-EL-01, P9/improvements/I-EL-02

### 10. CI-030 — Improve receipt CLI ergonomics without multiplying state owners

**Lane L1** `[4-5]` &nbsp;·&nbsp; **effort 1** &nbsp;·&nbsp; **Priority band:** 3 &nbsp;·&nbsp; **Class:** P4_NONBLOCKING_CLEANUP  
**Blocker:** USABILITY_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 19 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **not_started**  
**Depends on:** CI-004 &nbsp;·&nbsp; **Runs alongside:** CI-005, CI-008, CI-013

Give receipt CLIs a default/status-style read action while retaining one canonical receipt store and schema.

**Remaining at this binding:**

- LOADER-1: make bare invocation read and print, keep --read accepted, and name the exact command in CLAUDE.md's receipt paragraph.

**Sources:** P6/improvements/LOADER-1

### 11. CI-008 — Reconcile make pr doctrine with consumer-repository command contracts

**Lane L2** `[4-6]` &nbsp;·&nbsp; **effort 2** &nbsp;·&nbsp; **Priority band:** 0 &nbsp;·&nbsp; **Class:** P2_INTEGRATION_AND_RELIABILITY  
**Blocker:** EXECUTION_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 12 of 27 &nbsp;·&nbsp; **Status:** OPEN_DECISION → **partial**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-005, CI-013, CI-023, CI-030

Choose one canonical contract: ship a functioning pr target into every governed consumer or relax the absolute doctrine to a defined supported fallback. Do not retain contradictory absolutes.

**Remaining at this binding:**

- Enable the consumer-workspace path: cwd=$GOV_ROOT so repo-local `entry:` hooks resolve, absolute --files paths, and a governance-only-local-hook skip subset — validated against a real consumer checkout.

**Sources:** P1/improvements/IMP-13, P3/improvements/C4, P6/improvements/BOOT-6, P9/improvements/I-BS-08

### 12. CI-013 — Preserve fail-closed destructive/staging gates while making denials actionable

**Lane L3** `[4-6]` &nbsp;·&nbsp; **effort 2** &nbsp;·&nbsp; **Priority band:** 1 &nbsp;·&nbsp; **Class:** P2_INTEGRATION_AND_RELIABILITY  
**Blocker:** EXECUTION_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 13 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **not_started**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-005, CI-008, CI-023, CI-030

Keep unresolved/empty destructive targets fail-closed. Add literal scoped cleanup paths, reachable authorization where policy permits, hook stderr, and per-stage denial reporting for compound commands. Do not weaken the unresolved-expansion invariant.

**Remaining at this binding:**

- I-BS-10 (in-repo): name the refused stage of a compound command and state that later stages did not run.
- C3 (in-repo): narrow the forced-removal guardrail to allow scratchpad-owned paths while keeping repo paths refused.
- I-BS-07 (in-repo): make the documented escapes reachable, or delete them from rules 49 and 88 so they are not published as usable.

**Sources:** P3/improvements/B4, P3/improvements/C3, P7/improvements/IMP-10, P9/improvements/I-BS-07, P9/improvements/I-BS-10

### 13. CI-023 — Collapse variable-loading authorities into one reproducible loader contract

**Lane L1** `[5-7]` &nbsp;·&nbsp; **effort 2** &nbsp;·&nbsp; **Priority band:** 1 &nbsp;·&nbsp; **Class:** P2_INTEGRATION_AND_RELIABILITY  
**Blocker:** SCHEMA_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 15 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **not_started**  
**Depends on:** none &nbsp;·&nbsp; **Collides with:** CI-015 &nbsp;·&nbsp; **Runs alongside:** CI-002, CI-003, CI-005, CI-008, CI-013, CI-019

Define one loader/precedence contract that works in non-interactive shells, fails fast on missing required configuration, guards source-without-call misuse, and removes inert/documented-but-unused variables.

**Remaining at this binding:**

- IMP-02(P4): amend rule 06 to `source …; resolve_governance_paths_or_exit`.
- LOADER-2: warn on stderr when the resolver is sourced by a shell that never calls either entry point.
- IMP-01(P4): load the session env in non-interactive shells (BASH_ENV, or hoist the source line above the PS1 guard).

**Sources:** P4/improvements/IMP-01, P4/improvements/IMP-02, P5/improvements/IMP-002, P5/improvements/IMP-005, P5/improvements/IMP-006, P6/improvements/LOADER-2

### 14. CI-019 — Coordinate concurrent writers on shared PR branches

**Lane L0** `[6-8]` &nbsp;·&nbsp; **effort 2** &nbsp;·&nbsp; **Priority band:** 2 &nbsp;·&nbsp; **Class:** P2_INTEGRATION_AND_RELIABILITY  
**Blocker:** NONBLOCKING &nbsp;·&nbsp; **Leverage rank:** 22 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **not_started**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-002, CI-003, CI-015, CI-023, CI-036

Detect/serialize or otherwise coordinate cross-machine writers before push so shared head branches do not repeatedly non-fast-forward.

**Remaining at this binding:**

- IMP-06(P7) retry half: bounded fetch/merge --no-edit/regen/re-verify/push loop, N<=2, never rewriting history.
- Lease protocol half touches CANONICAL_LAW and needs review before design.

**Sources:** P7/improvements/IMP-06

### 15. CI-002 — Make bootstrap projection ownership-aware and non-destructive to tracked repo content

**Lane L2** `[6-8]` &nbsp;·&nbsp; **effort 2** &nbsp;·&nbsp; **Priority band:** 0 &nbsp;·&nbsp; **Class:** P4_NONBLOCKING_CLEANUP  
**Blocker:** NONBLOCKING &nbsp;·&nbsp; **Leverage rank:** 23 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **partial**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-003, CI-015, CI-019, CI-023, CI-036

Detect repository-owned tracked paths before projection. Project machine-local rules/hooks/state only to non-repo-owned locations; ignore only genuinely generated/untracked paths. Never blanket-ignore or replace a repository-owned .claude tree.

**Remaining at this binding:**

- Phase 2c (relocate L9_AUTONOMY_STATE_DIR outside the worktree). The only unmitigated leg. Touches l4_local.py + local_execution_gate.py + make pr together.
- Phase 2b (project to a non-owned sibling when the target is tracked) is an ownership-MODEL change, not a defect repair: the hazard it was written against is already mitigated by the four mechanisms above. Re-cost it before scheduling.
- The 8-fixture git-status-clean done_when is satisfied for the 4 repos attachable at this binding; the other 4 remain unverified for want of a session that carries them.

**Invalidated — do not execute as written:**

- IMP-06 (copy four .gitignore lines into 8 consumer repos) is INVALIDATED. The current design deliberately writes .git/info/exclude instead, and says so: 'which is LOCAL and uncommitted, so a consumer's tracked .gitignore is never mutated' (bootstrap_agent_environment.sh:462-464). Executing IMP-06 would mutate consumer tracked files the design exists to avoid. Phase 2d is superseded by the same mechanism.
- The recorded next-slice instruction 'apply is_tracked() before the remaining projection writes' would add a report to four writes that already compose additively. It is not the protection the slice claimed to add.

**Sources:** P1/improvements/IMP-06, P1/improvements/IMP-07, P3/improvements/B1, P3/improvements/B2, P6/improvements/BOOT-3, P9/improvements/I-BS-01

### 16. CI-003 — Make the Stop hook ownership-aware instead of residue-blind

**Lane L3** `[6-7]` &nbsp;·&nbsp; **effort 1** &nbsp;·&nbsp; **Priority band:** 1 &nbsp;·&nbsp; **Class:** P1_ROOT_REPAIR  
**Blocker:** USABILITY_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 5 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **partial**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-002, CI-019, CI-023

Scope stop-hook checks to authored changes in the active repo and explicitly exclude bootstrap-owned paths without masking tracked authored content.

**Remaining at this binding:**

- Add `.mcp.json` to the Claude-specific exclude block in install.sh. One glob; the design decision it belongs to is already made and documented.
- Hook-side ownership classification stays external.

**Sources:** P1/improvements/IMP-08, P3/improvements/B3, P9/improvements/I-BS-02

### 17. CI-015 — Name and enforce the authoritative governance checkout

**Lane L1** `[7-9]` &nbsp;·&nbsp; **effort 2** &nbsp;·&nbsp; **Priority band:** 1 &nbsp;·&nbsp; **Class:** P2_INTEGRATION_AND_RELIABILITY  
**Blocker:** USABILITY_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 17 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **partial**  
**Depends on:** CI-007, CI-023 &nbsp;·&nbsp; **Collides with:** CI-007, CI-023 &nbsp;·&nbsp; **Runs alongside:** CI-002, CI-014, CI-016, CI-019, CI-025, CI-036

When multiple governance trees exist, print both revisions, name the one from which rules resolve, and remove/relabel non-authoritative clones where possible.

**Remaining at this binding:**

- I-BS-13: when a second checkout of the governance repository is present, print both paths with their revisions and state which one rules resolve from.
- I-WT-01: decide whether the workspace clone is an intentional consumer checkout or a leftover, and make resolve_governance_paths.sh assert the answer.

**Sources:** P3/improvements/C2, P8/improvements/I-WT-01, P9/improvements/I-BS-13

### 18. CI-036 — Keep unpushed-commit counts honest across merged-and-deleted branches

**Lane L3** `[7-8]` &nbsp;·&nbsp; **effort 1** &nbsp;·&nbsp; **Priority band:** 2 &nbsp;·&nbsp; **Class:** P2_INTEGRATION_AND_RELIABILITY  
**Blocker:** NONBLOCKING &nbsp;·&nbsp; **Leverage rank:** 11 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **partial**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-002, CI-015, CI-019

Prune remote-tracking refs for branches deleted upstream and keep origin/HEAD resolvable, so unpushed-commit counts neither inflate nor fall silent.

**Remaining at this binding:**

- Consolidate repo_hygiene.py's prune with the session-start prune so a count read mid-session is not served by the session-end pass.
- Harness stop-hook resolution logic stays external.

### 19. CI-025 — Provide sanctioned cleanup of generated/cache residue

**Lane L0** `[8-9]` &nbsp;·&nbsp; **effort 1** &nbsp;·&nbsp; **Priority band:** 2 &nbsp;·&nbsp; **Class:** P2_INTEGRATION_AND_RELIABILITY  
**Blocker:** EXECUTION_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 14 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **not_started**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-014, CI-015, CI-016

Keep generated/cache debris out of gate inputs and provide a permission-safe cleanup path that does not weaken general destructive-command policy.

**Remaining at this binding:**

- IMP-05/IMP-08(P7): add `make clean-pyc` and have the adapters gate pre-clean or ignore cache debris rather than failing on it.

**Sources:** P5/improvements/IMP-010, P7/improvements/IMP-05, P7/improvements/IMP-08

### 20. CI-016 — Make L4/release receipts resolve paths, branch, and head dynamically

**Lane L2** `[8-9]` &nbsp;·&nbsp; **effort 1** &nbsp;·&nbsp; **Priority band:** 1 &nbsp;·&nbsp; **Class:** P2_INTEGRATION_AND_RELIABILITY  
**Blocker:** EXECUTION_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 16 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **partial**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-014, CI-015, CI-025

Bind receipts to the released repository, current branch/head, and actual template path; make stale SHA/branch bindings visible before they block publication.

**Remaining at this binding:**

- IMP-14: resolve pr_template against the released repository across the standard template locations; emit null when none is found.
- I-BS-09: have `status` compare the pinned SHA to current head and report STALE explicitly.

**Sources:** P1/improvements/IMP-14, P3/improvements/B6, P9/improvements/I-BS-09

### 21. CI-014 — Make target repository/cwd explicit for governance CLIs

**Lane L3** `[8-9]` &nbsp;·&nbsp; **effort 1** &nbsp;·&nbsp; **Priority band:** 2 &nbsp;·&nbsp; **Class:** P2_INTEGRATION_AND_RELIABILITY  
**Blocker:** USABILITY_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 18 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **partial**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-015, CI-016, CI-025

Pass the target repository explicitly to governance commands and avoid procedures whose correctness depends on persistent shell cwd.

**Remaining at this binding:**

- Add --workspace to graphiti_memory_client.py, defaulting to current behaviour.
- Make the refusal name the remedy: '…did you mean --workspace <target repo>?'

**Sources:** P4/improvements/IMP-06

### 22. CI-021 — Make session-experience and skill-usage logging observable

**Lane L0** `[9-10]` &nbsp;·&nbsp; **effort 1** &nbsp;·&nbsp; **Priority band:** 2 &nbsp;·&nbsp; **Class:** P3_VALIDATION_AND_CONVERGENCE  
**Blocker:** NONBLOCKING &nbsp;·&nbsp; **Leverage rank:** 20 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **not_started**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-018, CI-022, CI-027

Fix logging matchers/paths and emit enough session-start evidence to distinguish inactivity from a broken collector.

**Remaining at this binding:**

- I-BS-11: narrow the matcher to namespaces this surface exposes, and emit a session-start line naming the log path and its current entry count.

**Sources:** P5/improvements/IMP-011, P9/improvements/I-BS-11

### 23. CI-018 — Make local CI parity and hooks first-class provisioning

**Lane L1** `[9-10]` &nbsp;·&nbsp; **effort 1** &nbsp;·&nbsp; **Priority band:** 1 &nbsp;·&nbsp; **Class:** P3_VALIDATION_AND_CONVERGENCE  
**Blocker:** VALIDATION_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 21 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **not_started**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-021, CI-022, CI-027

Install the actual hooks/gates, define one local CI-parity command, and keep its blocker list aligned with remote CI so local green means something.

**Remaining at this binding:**

- IMP-01(P7): add a make target running the campaign and controller suites with HOME empty and both git config files at /dev/null, and reference it from the pr-check documentation.

**Sources:** P2/improvements/IMP-B2, P2/improvements/IMP-R2, P5/improvements/IMP-001, P7/improvements/IMP-01

### 24. CI-027 — Correct rule rationale that no longer matches container reality

**Lane L2** `[9-10]` &nbsp;·&nbsp; **effort 1** &nbsp;·&nbsp; **Priority band:** 3 &nbsp;·&nbsp; **Class:** P4_NONBLOCKING_CLEANUP  
**Blocker:** NONBLOCKING &nbsp;·&nbsp; **Leverage rank:** 24 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **not_started**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-018, CI-021, CI-022

Preserve the pinned-interpreter requirement but remove or correct stale rationale that system Python lacks PyYAML when that premise is false.

**Remaining at this binding:**

- IMP-17: keep the pinned-interpreter mandate, replace the justification with the true one (version pinning and dependency isolation), and regenerate the projection.

**Sources:** P1/improvements/IMP-17

### 25. CI-022 — Provision or explicitly declare service-backed integration-test dependencies

**Lane L3** `[9-10]` &nbsp;·&nbsp; **effort 1** &nbsp;·&nbsp; **Priority band:** 2 &nbsp;·&nbsp; **Class:** P3_VALIDATION_AND_CONVERGENCE  
**Blocker:** VALIDATION_BLOCKER &nbsp;·&nbsp; **Leverage rank:** 25 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **not_started**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-018, CI-021, CI-027

Provision declared services such as Neo4j when integration proof is expected, otherwise surface the unavailable coverage before tests run.

**Remaining at this binding:**

- I-EL-07, in-repo half: state at session start that service-backed integration tests are unavailable, so the split between runnable and unrunnable coverage is known before a run rather than after.

**Sources:** P9/improvements/I-EL-07

### 26. CI-017 — Validate generated-artifact membership and report all drift in one pass

**Lane L0** `[10-11]` &nbsp;·&nbsp; **effort 1** &nbsp;·&nbsp; **Priority band:** 1 &nbsp;·&nbsp; **Class:** P4_NONBLOCKING_CLEANUP  
**Blocker:** NONBLOCKING &nbsp;·&nbsp; **Leverage rank:** 26 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **partial**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-032

Make validation tolerate legitimate index/worktree states, catch missing manifest membership at file creation, and report every generated artifact out of step in one run.

**Remaining at this binding:**

- IMP-09 (l9-meta-injector): collect manifest staleness and dist divergence in one report, or add `npm run regen`.
- IMP-B1, I-WT-03: unverified at this binding — see queue needs_attachment note.

**Sources:** P2/improvements/IMP-B1, P4/improvements/IMP-09, P8/improvements/I-WT-03

### 27. CI-032 — Give slow validation units explicit headroom without weakening total proof

**Lane L1** `[10-11]` &nbsp;·&nbsp; **effort 1** &nbsp;·&nbsp; **Priority band:** 3 &nbsp;·&nbsp; **Class:** P4_NONBLOCKING_CLEANUP  
**Blocker:** NONBLOCKING &nbsp;·&nbsp; **Leverage rank:** 27 of 27 &nbsp;·&nbsp; **Status:** ACTIVE → **not_started**  
**Depends on:** none &nbsp;·&nbsp; **Runs alongside:** CI-017

Adjust per-file RPC/test ceilings for known slow tests while keeping aggregate validation coverage intact.

**Remaining at this binding:**

- IMP-10(P4): split the five-run incremental chain across two files, or reduce the incremental scale fixture while leaving corpus_scale.test.ts at ten thousand artifacts.

**Sources:** P4/improvements/IMP-10

